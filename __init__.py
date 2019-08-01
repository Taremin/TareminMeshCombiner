import re
import bpy
import numpy

bl_info = {
    'name': 'Taremin Mesh Combiner',
    'category': '3D View',
    'author': 'Taremin',
    'location': 'View 3D > Tool Shelf > Taremin',
    'description': "mesh combine tool for my vrchat avatar",
    'version': [0, 0, 7],
    'blender': (2, 80, 0),
    'wiki_url': '',
    'tracker_url': '',
    'warning': '',
}

IS_LEGACY = (bpy.app.version < (2, 80, 0))
REGION = "TOOLS" if IS_LEGACY else "UI"


def select(obj, value):
    get_scene_objects().active = obj
    if IS_LEGACY:
        obj.select = value
    else:
        obj.select_set(value)


def get_scene_objects():
    if IS_LEGACY:
        return bpy.context.scene.objects
    else:
        return bpy.context.window.view_layer.objects


def set_active_object(obj):
    if IS_LEGACY:
        bpy.context.scene.objects.active = obj
    else:
        bpy.context.window.view_layer.objects.active = obj


def get_active_object():
    if IS_LEGACY:
        return bpy.context.scene.objects.active
    else:
        return bpy.context.window.view_layer.objects.active


def is_hide(obj):
    if IS_LEGACY:
        return obj.hide
    else:
        return obj.hide_viewport or not obj.visible_get()


def set_hide(obj, value):
    if IS_LEGACY:
        obj.hide = value
    else:
        obj.hide_viewport = value


class OBJECT_OT_OptimizeButton(bpy.types.Operator):
    bl_idname = 'taremin.optimize'
    bl_label = '最適化'
    bl_description = 'FBXエクスポートのためにオブジェクトの整理を行う。'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        props = scene.tmc_props
        prev = None
        meshes = []
        deletes = []
        objects = get_scene_objects()
        active = objects.active

        if not active:
            return

        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:
            # アーマチュアはスキップ
            if obj.type in 'ARMATURE':
                print("{} - Skip".format(obj.name))
                continue

            if prev:
                select(prev, False)
            select(obj, True)
            prev = obj

            # メッシュとアーマチュア以外か不可視状態のオブジェクトは削除
            if obj.type != 'MESH' or is_hide(obj):
                print("{} - Skip (Remove)".format(obj.name))
                deletes.append(obj)
                continue

            meshes.append(obj)
            self.apply_all_modifier(obj)

        # UVマップのリネーム
        if props.rename_uvmaps:
            self.rename_uvmaps()

        # メッシュオブジェクトの結合
        self.join_mesh(active, meshes)

        #
        # 不可視状態になってる or メッシュ以外のオブジェクトの削除
        # オブジェクトは不可視状態のままだと削除できてないので解除する必要がある
        # (Pythonコンソールだと不可視のまま削除できる)
        #
        if props.remove_unnecessary_objects:
            print("Delete all hide objects")
            bpy.ops.object.select_all(action='DESELECT')
            for obj in deletes:
                print("\t{} - Delete".format(obj.name))
                if not IS_LEGACY:
                    obj.hide_select = False
                set_hide(obj, False)
                select(obj, True)
            bpy.ops.object.hide_view_clear()
            bpy.ops.object.delete()

        #
        # 非選択レイヤー/コレクションのオブジェクトを削除
        #
        if props.remove_unselected_layer:
            if IS_LEGACY:
                self.remove_unselected_leyer(scene)
            else:
                self.remove_hidden_collection(context)

        #
        # "Merge." から始まる頂点グループの重複頂点の削除で結合する
        #
        print("Merge vertex group")
        bpy.ops.object.select_all(action='DESELECT')
        vg_pattern = re.compile(r'^Merge\.')
        for obj in get_scene_objects():
            print("Mesh: {} ({})".format(obj.name, obj.type))
            if obj.type not in 'MESH':
                continue
            for idx in range(0, len(obj.vertex_groups)):
                vg = obj.vertex_groups[idx]
                if vg_pattern.search(vg.name):
                    select(obj, True)
                    bpy.ops.object.mode_set(mode='EDIT')

                    print("Merge mesh: {}".format(vg.name))
                    bpy.ops.mesh.select_all(action='DESELECT')
                    obj.vertex_groups.active_index = vg.index
                    bpy.ops.object.vertex_group_select()
                    bpy.ops.mesh.remove_doubles()

                    bpy.ops.object.mode_set(mode='OBJECT')

        #
        # 非選択アーマチュアレイヤーのボーンを削除
        #
        if props.remove_unnecessary_bones:
            print("Delete all unselected armature layer bones")
            removed_bones = []
            for armature in bpy.data.objects:
                if armature.type != "ARMATURE":
                    continue

                select(armature, True)
                if is_hide(armature):
                    set_hide(armature, False)
                bpy.ops.object.mode_set(mode='EDIT')

                # 非選択アーマチュアレイヤーのボーンを削除
                for bone in armature.data.edit_bones:
                    selected = False
                    for layer_index in range(len(bone.layers)):
                        if armature.data.layers[layer_index] and bone.layers[
                                layer_index]:
                            selected = True
                            break
                    if not selected:
                        print("\t{} - Delete Bone".format(bone.name))
                        for bone_layer_index in range(len(bone.layers)):
                            bone.layers[bone_layer_index] = True
                        bone.hide = False
                        bone.select = True

                        if bone.parent:
                            removed_bones.append([bone.name, bone.parent.name])

                        armature.data.edit_bones.remove(bone)
                bpy.ops.object.mode_set(mode='OBJECT')

            # 削除したボーンの頂点ウェイトを親に加算していく
            for obj in scene.objects:
                if obj.type not in 'MESH':
                    continue

                for (child, parent) in removed_bones:
                    if obj.vertex_groups.get(child) and obj.vertex_groups.get(parent):
                        print("Dissolve: {} -> {}".format(child, parent))
                        set_active_object(obj)
                        self.dissolve(obj, obj.vertex_groups.get(child),
                                      obj.vertex_groups.get(parent))

        if not IS_LEGACY and props.remove_empty_collection:
            self.remove_empty_collection(scene)

        # active
        if active in meshes:
            bpy.ops.object.select_all(action='DESELECT')
            select(active, True)

        return {'FINISHED'}

    def join_mesh(self, active, meshes):
        print("Join all mesh objects")
        bpy.ops.object.select_all(action='DESELECT')
        mesh_pattern = re.compile(r'\.NoMerge$')
        for obj in meshes:
            if mesh_pattern.search(obj.name):
                continue
            print("\t{} - Join".format(obj.name))
            select(obj, True)
        if active in meshes:
            select(active, True)
        bpy.ops.object.join()

    def apply_all_modifier(self, obj):
        print("{} - {} ({})".format(obj.name, obj.type, is_hide(obj)))
        if obj.data.shape_keys and hasattr(bpy.ops.object, "apply_all_modifier"):
            for mod in obj.modifiers:
                if mod.type in 'ARMATURE':
                    mod.show_viewport = False
            print("\t{} - All apply".format(obj.name))
            bpy.ops.object.apply_all_modifier()
            for mod in obj.modifiers:
                if mod.type in 'ARMATURE':
                    mod.show_viewport = True
        else:
            for mod in obj.modifiers:
                if mod.type not in 'ARMATURE':
                    print("\t{} - Apply".format(mod.type))
                    bpy.ops.object.modifier_apply(modifier=mod.name)
                else:
                    print("\t{} - Skip".format(mod.type))

    def remove_empty_collection(self, scene):
        print("Delete all empty collection")
        for collection in scene.collection.children:
            if not collection.objects:
                scene.collection.children.unlink(collection)

    def dissolve(self, obj, child_vertex_group, parent_vertex_group):
        selected = numpy.zeros(len(obj.data.vertices), dtype=numpy.bool)

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.vertex_group_set_active(group=child_vertex_group.name)
        bpy.ops.object.vertex_group_select()
        bpy.ops.object.mode_set(mode='OBJECT')

        obj.data.vertices.foreach_get('select', selected)

        for v in numpy.array(obj.data.vertices)[selected]:
            vi = [v.index]
            parent_vertex_group.add(vi, child_vertex_group.weight(v.index),
                                    'ADD')
            child_vertex_group.remove(vi)

    # for Blender 2.8
    def remove_hidden_collection(self, context):
        print("Delete all hidden collection")
        for collection in bpy.context.view_layer.layer_collection.children:
            if collection.hide_viewport or collection.exclude:
                print("\t{} - Delete Collection".format(collection.name))
                context.scene.collection.children.unlink(collection.collection)

    # for Blender 2.7x
    def remove_unselected_leyer(self, scene):
        print("Delete all unselected layer objects")
        bpy.ops.object.select_all(action='DESELECT')
        for obj in get_scene_objects():
            selected = False
            for layer_index in range(len(scene.layers)):
                if scene.layers[layer_index] and obj.layers[layer_index]:
                    selected = True
                    break
            if not selected:
                print("\t{} - Delete".format(obj.name))
                for object_layer_index in range(len(obj.layers)):
                    obj.layers[object_layer_index] = True
                set_hide(obj, False)
                select(obj, True)
        bpy.ops.object.delete()

    # for Blender 2.7x
    def rename_uvmaps(self):
        print("Rename UVMaps")
        for obj in get_scene_objects():
            if obj.type not in 'MESH':
                continue
            for uvmap in obj.data.uv_layers:
                print("\tRename {} - {} -> {}".format(
                    obj.name, uvmap.name, 'UVMap'))
                uvmap.name = 'UVMap'

        if IS_LEGACY:
            for material in bpy.data.materials:
                for texture_slot in material.texture_slots:
                    if texture_slot is None:
                        continue
                    texture_slot.uv_layer = 'UVMap'


class TareminMeshCombinerProps(bpy.types.PropertyGroup):
    remove_unnecessary_objects = bpy.props.BoolProperty(
        name="余計なオブジェクトの削除",
        default=True,
        description="メッシュ、アーマチュア以外のオブジェクトと非表示状態になってるオブジェクトの削除を行う。")
    rename_uvmaps = bpy.props.BoolProperty(
        name="UVMapのリネーム",
        default=True,
        description=""
        "ユーザ設定の翻訳で「新しいデータ」にチェックが入っている場合、英語(UVMap)と日本語(UVマップ)のUVマップがそれぞれ存在する場合がある。\n"
        "メッシュオブジェクトの結合を行った時、このUVMapが混在していると日本語か英語のUVマップどちらか片方が反映できなくなる場合がある。\n"
        "UVMapのリネームをオンにしているとオブジェクトの結合を行う前にすべてのUVMapを 'UVMap' にリネームする。")
    remove_unselected_layer = bpy.props.BoolProperty(
        name="非アクティブレイヤーのオブジェクト削除",
        default=True,
        description="非アクティブレイヤーのオブジェクトを削除する。")
    remove_unnecessary_bones = bpy.props.BoolProperty(
        name="非選択アーマチュアレイヤーのボーン削除",
        default=True,
        description="非選択状態のアーマチュアレイヤーにあるボーンの削除を行う。")
    remove_empty_collection = bpy.props.BoolProperty(
        name="空のコレクションの削除",
        default=True,
        description="結合などや削除で空になったコレクションを削除する。")


class VIEW3D_PT_TareminPanel(bpy.types.Panel):
    bl_label = 'Taremin Mesh Combiner'
    bl_region_type = REGION
    bl_space_type = 'VIEW_3D'
    bl_category = 'Taremin Mesh Combiner'

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        col = box.column(align=True)
        invalid_context = False
        props = context.scene.tmc_props

        if context.mode != 'OBJECT':
            row = col.row(align=True)
            row.label(text='オブジェクトモードにしてください')
            invalid_context = True

        if get_active_object().type != 'MESH':
            row = col.row(align=True)
            row.label(text='結合先のメッシュオブジェクトをアクティブにしてください')
            invalid_context = True

        if invalid_context:
            return

        row = col.row(align=True)
        row.label(text='最適化')
        row = col.row(align=True)
        row.prop(props, 'remove_unnecessary_objects')
        row = col.row(align=True)
        row.prop(props, 'remove_unselected_layer')
        row = col.row(align=True)
        row.prop(props, 'rename_uvmaps')
        row = col.row(align=True)
        row.prop(props, 'remove_unnecessary_bones')
        row = col.row(align=True)
        if not IS_LEGACY:
            row.prop(props, 'remove_empty_collection')
            row = col.row(align=True)
        row.label(text='結合先のオブジェクトをアクティブにしてから最適化を行ってください。')
        row = col.row(align=True)
        row.operator(OBJECT_OT_OptimizeButton.bl_idname)


classesToRegister = [
    VIEW3D_PT_TareminPanel,
    OBJECT_OT_OptimizeButton,
    TareminMeshCombinerProps
]


def register():
    for value in classesToRegister:
        bpy.utils.register_class(value)
    bpy.types.Scene.tmc_props = bpy.props.PointerProperty(type=TareminMeshCombinerProps)


def unregister():
    for value in classesToRegister:
        bpy.utils.unregister_class(value)
    del bpy.types.Scene.tmc_props


if __name__ == '__main__':
    register()
