import copy
import bpy.utils.previews

bl_info = {
    'name': 'Taremin Blender Plugin',
    'category': '3D View',
    'author': 'Taremin',
    'location': 'View 3D > Tool Shelf > Taremin',
    'description': "Taremin's private plugin",
    'version': [0, 0, 3],
    'blender': (2, 79, 0),
    'wiki_url': '',
    'tracker_url': '',
    'warning': '',
}

version = copy.deepcopy(bl_info.get('version'))

bpy.types.Scene.remove_unnecessary_objects = bpy.props.BoolProperty(
    name="余計なオブジェクトの削除",
    default=True,
    description="メッシュ、アーマチュア以外のオブジェクトと非表示状態になってるオブジェクトの削除を行う。"
)
bpy.types.Scene.rename_uvmaps = bpy.props.BoolProperty(
    name="UVMapのリネーム",
    default=True,
    description="ユーザ設定の翻訳で「新しいデータ」にチェックが入っている場合、英語(UVMap)と日本語(UVマップ)のUVマップがそれぞれ存在する場合がある。\n"
        "メッシュオブジェクトの結合を行った時、このUVMapが混在していると日本語か英語のUVマップどちらか片方が反映できなくなる場合がある。\n"
        "UVMapのリネームをオンにしているとオブジェクトの結合を行う前にすべてのUVMapを 'UVMap' にリネームする。"
)
bpy.types.Scene.remove_unselected_layer = bpy.props.BoolProperty(
    name="非アクティブレイヤーのオブジェクト削除",
    default=True,
    description="非アクティブレイヤーのオブジェクトを削除する。"
)
bpy.types.Scene.remove_unnecessary_bones = bpy.props.BoolProperty(
    name="非選択アーマチュアレイヤーのボーン削除",
    default=True,
    description="非選択状態のアーマチュアレイヤーにあるボーンの削除を行う。"
)

class OptimizeButton(bpy.types.Operator):
    bl_idname = 'taremin.optimize'
    bl_label = '最適化'
    bl_description = 'FBXエクスポートのためにオブジェクトの整理を行う。'
    bl_options = {'REGISTER', 'UNDO'}

    def select(self, obj):
        bpy.context.scene.objects.active = obj
        obj.select = True

    def execute(self, context):
        scene = context.scene
        prev = None
        meshes = []
        deletes = []
        active = bpy.context.scene.objects.active

        if not active:
            return

        bpy.ops.object.select_all(action='DESELECT')
        for obj in scene.objects:
            # アーマチュアはスキップ
            if (obj.type in ('ARMATURE')):
                print("{} - Skip".format(obj.name))
                continue
            
            if (prev):
                prev.select = False
            self.select(obj)
            prev = obj

            # メッシュとアーマチュア以外か不可視状態のオブジェクトは削除
            if (obj.type != 'MESH' or obj.hide):
                print("{} - Skip (Remove)".format(obj.name))
                deletes.append(obj)
                continue

            meshes.append(obj)
            print("{} - {} ({})".format(obj.name, obj.type, obj.hide))
            if obj.data.shape_keys and bpy.ops.object.apply_selected_modifier:
                for mod in obj.modifiers:
                    if (mod.type in ('ARMATURE')):
                        mod.show_viewport = False
                print("\t{} - All apply".format(mod.type))
                bpy.ops.object.apply_all_modifier()
                for mod in obj.modifiers:
                    if (mod.type in ('ARMATURE')):
                        mod.show_viewport = True
            else:
                for mod in obj.modifiers:
                    if (mod.type not in ('ARMATURE')):
                        print("\t{} - Apply".format(mod.type))
                        bpy.ops.object.modifier_apply(modifier=mod.name)
                    else:
                        print("\t{} - Skip".format(mod.type))

        #
        # UVマップのリネーム
        #
        if scene.rename_uvmaps:
            print("Rename UVMaps")
            for obj in scene.objects:
                if (obj.type not in ('MESH')):
                    continue
                for uvmap in obj.data.uv_layers:
                    print("\tRename {} - {} -> {}".format(obj.name, uvmap.name, 'UVMap'))
                    uvmap.name = 'UVMap'
            for material in bpy.data.materials:
                for texture_slot in material.texture_slots:
                    if texture_slot == None:
                        continue
                    texture_slot.uv_layer = 'UVMap'

        #
        # メッシュオブジェクトの結合
        #
        print("Join all mesh objects")
        bpy.ops.object.select_all(action='DESELECT')
        for obj in meshes:
            print("\t{} - Join".format(obj.name))
            self.select(obj)
        if active in meshes:
            bpy.context.scene.objects.active = active
        bpy.ops.object.join()

        #
        # 不可視状態になってる or メッシュ以外のオブジェクトの削除
        # オブジェクトは不可視状態のままだと削除できてないので解除する必要がある
        # (Pythonコンソールだと不可視のまま削除できる)
        #
        if scene.remove_unnecessary_objects:
            print("Delete all hide objects")
            bpy.ops.object.select_all(action='DESELECT')
            for obj in deletes:
                print("\t{} - Delete".format(obj.name))
                obj.hide = False
                self.select(obj)
            bpy.ops.object.delete()

        #
        # 非選択レイヤーのオブジェクトを削除
        #
        if scene.remove_unselected_layer:
            print("Delete all unselected layer objects")
            bpy.ops.object.select_all(action='DESELECT')
            for obj in scene.objects:
                selected = False
                for layer_index in range(len(scene.layers)):
                    if scene.layers[layer_index] and obj.layers[layer_index]:
                        selected = True
                        break
                if not selected:
                    print("\t{} - Delete".format(obj.name))
                    for object_layer_index in range(len(obj.layers)):
                        obj.layers[object_layer_index] = True
                    obj.hide = False
                    self.select(obj)
            bpy.ops.object.delete()

        #
        # 非選択アーマチュアレイヤーのボーンを削除
        #
        if scene.remove_unnecessary_bones:
            print("Delete all unselected armature layer bones")
            for armature in bpy.data.objects:
                if armature.type != "ARMATURE":
                    continue
                
                bpy.ops.object.select_all(action='DESELECT')
                self.select(armature)
                bpy.ops.object.mode_set(mode='EDIT')

                for bone in armature.data.edit_bones:
                    selected = False
                    for layer_index in range(len(bone.layers)):
                        if armature.data.layers[layer_index] and bone.layers[layer_index]:
                            selected = True
                            break
                    if not selected:
                        print("\t{} - Delete Bone".format(bone.name))
                        for bone_layer_index in range(len(bone.layers)):
                            bone.layers[object_layer_index] = True
                        bone.hide = False
                        bone.select = True
                        armature.data.edit_bones.remove(bone)
                bpy.ops.object.mode_set(mode='OBJECT')

        # active
        if active in meshes:
            bpy.ops.object.select_all(action='DESELECT')
            self.select(active)
            bpy.context.scene.objects.active = active

        return {'FINISHED'}

class TareminPanel(bpy.types.Panel):
    bl_label = 'Taremin Blender Plugin'
    bl_idname = 'VIEW3D_PT_taremin_v1'
    bl_label = 'Taremin'
    bl_region_type = 'TOOLS'
    bl_space_type = 'VIEW_3D'
    bl_category = 'Taremin'

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        col = box.column(align=True)

        row = col.row(align=True)
        row.label('最適化')
        row = col.row(align=True)
        row.prop(context.scene, 'remove_unnecessary_objects')
        row = col.row(align=True)
        row.prop(context.scene, 'remove_unselected_layer')
        row = col.row(align=True)
        row.prop(context.scene, 'rename_uvmaps')
        row = col.row(align=True)
        row.prop(context.scene, 'remove_unnecessary_bones')
        row = col.row(align=True)
        row.label('結合先のオブジェクトをアクティブにしてから最適化を行ってください。')
        row = col.row(align=True)
        row.operator('taremin.optimize')

classesToRegister = [
    TareminPanel,
    OptimizeButton,
]

def register():
    for value in classesToRegister:
        bpy.utils.register_class(value)


def unregister():
    for value in classesToRegister:
        bpy.utils.unregister_class(value)

if __name__ == '__main__':
    register()
