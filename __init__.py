import re
import bpy
import numpy

bl_info = {
    'name': 'Taremin Mesh Combiner',
    'category': '3D View',
    'author': 'Taremin',
    'location': 'View 3D > UI > Taremin',
    'description': "combine mesh tool",
    'version': (0, 1, 0),
    'blender': (2, 80, 0),
    'wiki_url': '',
    'tracker_url': '',
    'warning': '',
}


def select(obj, value):
    get_scene_objects().active = obj
    obj.select_set(value)


def get_scene_objects():
    return bpy.context.window.view_layer.objects


def set_active_object(obj):
    bpy.context.window.view_layer.objects.active = obj


def get_active_object():
    return bpy.context.window.view_layer.objects.active


def is_hide(obj):
    return obj.hide_viewport or not obj.visible_get()


def set_hide(obj, value):
    obj.hide_viewport = value


class TAREMIN_MESH_COMBINER_OT_CombineMesh(bpy.types.Operator):
    bl_idname = 'taremin.combine_mesh'
    bl_label = '結合'
    bl_description = 'オブジェクトの結合と不要なオブジェクトの削除を行う'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        props = scene.tmc_props
        meshes = []
        objects = get_scene_objects()
        active = objects.active

        root_layer_collection = bpy.context.view_layer.layer_collection
        dest_col = bpy.data.collections.new(
            props.output_collection)
        root_layer_collection.collection.children.link(dest_col)

        join_meshes = []

        def walkdown_collection(collection, path=[], depth=0):
            path = path + [collection]
            for obj in collection.collection.objects:
                if obj.type == 'ARMATURE':
                    try:
                        dest_col.objects.link(obj)
                    except RuntimeError:
                        pass  # obj is already exists in dest_col
                if obj.type == 'MESH':
                    if not is_hide(obj):
                        print("  " * depth + "[OBJ]" +
                              obj.name + " - " + obj.type)
                        self.apply_all_modifier(obj)
                        join_meshes.append((obj, path))

            for child in collection.children:
                if child.hide_viewport or child.exclude:
                    pass
                else:
                    walkdown_collection(child, path, depth+1)

        walkdown_collection(root_layer_collection)

        # join meshes
        join_dict = {}
        for obj, path in join_meshes:
            match = False
            for group in props.combine_groups:
                name = group.object_name
                if group.group_type == 'COLLECTION':
                    path_names = [collection.name for collection in path]
                    if len(path_names) > 0 and group.collection.name == path_names[-1]:
                        if name not in join_dict:
                            join_dict[name] = []
                        join_dict[name].append(obj)
                        match = True
                        break
                elif group.group_type == 'COLLECTION_RECURSIVE':
                    path_names = [collection.name for collection in path]
                    if group.collection.name in path_names:
                        if name not in join_dict:
                            join_dict[name] = []
                        join_dict[name].append(obj)
                        match = True
                        break
                elif group.group_type == 'REGEXP':
                    pattern = re.compile(group.regexp)
                    if pattern.match(obj.name):
                        name = pattern.sub(name, obj.name)
                        if name not in join_dict:
                            join_dict[name] = []
                        join_dict[name].append(obj)
                        match = True
                        break

            # default
            if not match:
                name = props.output_default_object
                if name not in join_dict:
                    join_dict[name] = []
                join_dict[name].append(obj)

        for dest_name, meshes in join_dict.items():
            mesh = bpy.data.meshes.new(dest_name)
            dest_obj = bpy.data.objects.new(name=dest_name, object_data=mesh)

            # add to scene
            dest_col.objects.link(dest_obj)

            # add armature modifier
            for target in self.get_armature_modifier_targets(meshes):
                modifier = dest_obj.modifiers.new(
                    name='Armature', type='ARMATURE')
                modifier.object = bpy.data.objects[target]

            print("JOIN:", dest_obj, meshes)
            self.join_mesh(dest_obj, meshes)

        # remove all collections without destination collection
        for layer_collection in root_layer_collection.children:
            if layer_collection.collection is not dest_col:
                root_layer_collection.collection.children.unlink(
                    layer_collection.collection)
        for obj in root_layer_collection.collection.objects:
            root_layer_collection.collection.objects.unlink(obj)

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
                    bpy.ops.mesh.remove_doubles(threshold=0.0)

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

                if is_hide(armature):
                    set_hide(armature, False)
                print("Armature: {}".format(armature.name))
                select(armature, True)
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

        if props.remove_empty_collection:
            self.remove_empty_collection(scene)

        # active
        if active in meshes:
            bpy.ops.object.select_all(action='DESELECT')
            #select(active, True)

        return {'FINISHED'}

    def join_mesh(self, active, meshes):
        print("Join all mesh objects")
        bpy.ops.object.select_all(action='DESELECT')
        for obj in meshes:
            print("\t{} - Join".format(obj.name))
            select(obj, True)
        select(active, True)
        bpy.ops.object.join()

    def apply_all_modifier(self, obj):
        bpy.ops.object.select_all(action='DESELECT')
        select(obj, True)
        print("{} - {} ({})".format(obj.name, obj.type, is_hide(obj)))
        if obj.data.shape_keys and hasattr(bpy.types, "OBJECT_OT_apply_all_modifier"):
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

    def get_armature_modifier_targets(self, mesh_objects):
        modifier_targets = set([])
        for obj in mesh_objects:
            for modifier in obj.modifiers:
                if modifier.type in 'ARMATURE':
                    modifier_targets.add(modifier.object.name)
        return modifier_targets

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

    def remove_hidden_collection(self, context, parent):
        print("Delete all hidden collection")
        for collection in parent.children:
            if collection.hide_viewport or collection.exclude:
                print(
                    "\t{} - Delete Collection from {}".format(collection.name, parent.name))
                #print("\t{} - Delete Collection".format(collection.name))
                parent.collection.children.unlink(collection.collection)
            else:
                self.remove_hidden_collection(context, collection)


class TareminMeshCombinerGroupSettings(bpy.types.PropertyGroup):
    group_type: bpy.props.EnumProperty(
        items=[
            ("REGEXP", "Regexp", "", 0),
            ("COLLECTION", "Collection", "", 1),
            ("COLLECTION_RECURSIVE", "Collection(Recursive)", "", 2),
        ])
    regexp: bpy.props.StringProperty()
    collection: bpy.props.PointerProperty(
        type=bpy.types.Collection
    )
    object_name: bpy.props.StringProperty()


class TAREMIN_MESH_COMBINER_OT_GroupSettings_Add(bpy.types.Operator):
    bl_idname = "taremin.mesh_combiner_group_settings_add"
    bl_label = "Remove Entry"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.tmc_props

        props.combine_groups.add()
        props.combine_group_index = len(props.combine_groups) - 1

        return {'FINISHED'}


class TAREMIN_MESH_COMBINER_OT_GroupSettings_Remove(bpy.types.Operator):
    bl_idname = "taremin.mesh_combiner_group_settings_remove"
    bl_label = "Remove Entry"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.tmc_props

        props.combine_groups.remove(props.combine_group_index)
        max_index = len(props.combine_groups) - 1

        if props.combine_group_index > max_index:
            props.combine_group_index = max_index

        return {'FINISHED'}


class TAREMIN_MESH_COMBINER_OT_GroupSettings_Up(bpy.types.Operator):
    bl_idname = "taremin.mesh_combiner_group_settings_up"
    bl_label = "Up Entry"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        settings = context.scene.tmc_props
        return settings.combine_group_index > 0

    def execute(self, context):
        settings = context.scene.tmc_props
        index = settings.combine_group_index
        settings.combine_groups.move(index, index - 1)
        settings.combine_group_index = index - 1
        return {'FINISHED'}


class TAREMIN_MESH_COMBINER_OT_GroupSettings_Down(bpy.types.Operator):
    bl_idname = "taremin.mesh_combiner_group_settings_down"
    bl_label = "Down Entry"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        settings = context.scene.tmc_props
        max_index = len(settings.combine_groups) - 1
        return settings.combine_group_index < max_index

    def execute(self, context):
        settings = context.scene.tmc_props
        index = settings.combine_group_index
        settings.combine_groups.move(index, index + 1)
        settings.combine_group_index = index + 1

        return {'FINISHED'}


class TAREMIN_MESH_COMBINER_UL_GroupSettings(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row()
        col = row.column(align=True)

        col.prop(item, "group_type", text="")

        col = row.column()
        if item.group_type == "REGEXP":
            col.prop(item, "regexp", text="")
        elif item.group_type in ("COLLECTION", "COLLECTION_RECURSIVE"):
            col.prop(item, "collection", text="")
        else:
            raise ValueError(f"wrong group type: {item.group_type}")

        col = row.column()
        col.prop(item, "object_name", text="")


class TareminMeshCombinerProps(bpy.types.PropertyGroup):
    output_collection: bpy.props.StringProperty(
        name="Output Collection", default="Combined Objects")
    output_default_object: bpy.props.StringProperty(
        name="Default Output Object", default="Combined")
    remove_unnecessary_bones: bpy.props.BoolProperty(
        name="非選択アーマチュアレイヤーのボーン削除",
        default=True,
        description="非選択状態のアーマチュアレイヤーにあるボーンの削除を行う")
    remove_empty_collection: bpy.props.BoolProperty(
        name="空のコレクションの削除",
        default=True,
        description="結合などや削除で空になったコレクションを削除する")
    groups_folding: bpy.props.BoolProperty()
    combine_groups: bpy.props.CollectionProperty(
        type=TareminMeshCombinerGroupSettings
    )
    combine_group_index: bpy.props.IntProperty()


class VIEW3D_PT_TareminPanel(bpy.types.Panel):
    bl_label = 'Taremin Mesh Combiner'
    bl_region_type = "UI"
    bl_space_type = 'VIEW_3D'
    bl_category = 'Taremin Mesh Combiner'

    def draw(self, context):
        props = context.scene.tmc_props
        layout = self.layout
        invalid_context = False

        if context.mode != 'OBJECT':
            row = layout.row()
            row.label(text='オブジェクトモードにしてください')
            invalid_context = True

        if invalid_context:
            return

        row = layout.row(align=True)
        row.prop(props, 'output_collection')
        row = layout.row(align=True)
        row.prop(props, 'output_default_object')
        row = layout.row(align=True)
        row.prop(props, 'remove_unnecessary_bones')

        layout.separator()

        row = layout.row()
        row.prop(
            props, "groups_folding",
            icon="TRIA_RIGHT" if props.groups_folding else "TRIA_DOWN",
            icon_only=True
        )
        row.label(text="Groups")

        if not props.groups_folding:
            row = layout.row()
            col = row.column()
            col.template_list(
                "TAREMIN_MESH_COMBINER_UL_GroupSettings",
                "",
                props,
                "combine_groups",
                props,
                "combine_group_index",
                type="DEFAULT"
            )
            col = row.column(align=True)
            col.operator(
                TAREMIN_MESH_COMBINER_OT_GroupSettings_Add.bl_idname, text="", icon="ADD")
            col.operator(
                TAREMIN_MESH_COMBINER_OT_GroupSettings_Remove.bl_idname, text="", icon="REMOVE")
            col.separator()
            col.operator(
                TAREMIN_MESH_COMBINER_OT_GroupSettings_Up.bl_idname, text="", icon="TRIA_UP")
            col.operator(
                TAREMIN_MESH_COMBINER_OT_GroupSettings_Down.bl_idname, text="", icon="TRIA_DOWN")

        layout.separator()

        if not hasattr(bpy.types, "OBJECT_OT_apply_all_modifier"):
            box = layout.box()
            row = box.row()
            row.label(
                text="ApplyModifierアドオンがないためシェイプキーのあるオブジェクトでモディファイアの適用に失敗する可能性があります")

        row = layout.row()
        col = row.row(align=True)
        col.operator(TAREMIN_MESH_COMBINER_OT_CombineMesh.bl_idname)


classesToRegister = [
    VIEW3D_PT_TareminPanel,
    TAREMIN_MESH_COMBINER_OT_GroupSettings_Add,
    TAREMIN_MESH_COMBINER_OT_GroupSettings_Remove,
    TAREMIN_MESH_COMBINER_OT_GroupSettings_Up,
    TAREMIN_MESH_COMBINER_OT_GroupSettings_Down,
    TAREMIN_MESH_COMBINER_OT_CombineMesh,
    TareminMeshCombinerGroupSettings,
    TAREMIN_MESH_COMBINER_UL_GroupSettings,
    TareminMeshCombinerProps
]


def register():
    for value in classesToRegister:
        bpy.utils.register_class(value)
    bpy.types.Scene.tmc_props = bpy.props.PointerProperty(
        type=TareminMeshCombinerProps)


def unregister():
    for value in classesToRegister:
        bpy.utils.unregister_class(value)
    del bpy.types.Scene.tmc_props


if __name__ == '__main__':
    register()
