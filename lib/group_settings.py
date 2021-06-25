import bpy
from . import util


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
        props = util.get_settings(context)

        props.combine_groups.add()
        props.combine_group_index = len(props.combine_groups) - 1

        return {'FINISHED'}


class TAREMIN_MESH_COMBINER_OT_GroupSettings_Remove(bpy.types.Operator):
    bl_idname = "taremin.mesh_combiner_group_settings_remove"
    bl_label = "Remove Entry"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = util.get_settings(context)

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
        props = util.get_settings(context)
        return props.combine_group_index > 0

    def execute(self, context):
        props = util.get_settings(context)
        index = props.combine_group_index
        props.combine_groups.move(index, index - 1)
        props.combine_group_index = index - 1
        return {'FINISHED'}


class TAREMIN_MESH_COMBINER_OT_GroupSettings_Down(bpy.types.Operator):
    bl_idname = "taremin.mesh_combiner_group_settings_down"
    bl_label = "Down Entry"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        props = util.get_settings(context)
        max_index = len(props.combine_groups) - 1
        return props.combine_group_index < max_index

    def execute(self, context):
        props = util.get_settings(context)
        index = props.combine_group_index
        props.combine_groups.move(index, index + 1)
        props.combine_group_index = index + 1

        return {'FINISHED'}
