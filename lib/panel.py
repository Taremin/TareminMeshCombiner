import bpy
from . import combine_mesh, group_settings, util


class TAREMIN_MESH_COMBINER_PT_Panel(bpy.types.Panel):
    bl_label = 'Taremin Mesh Combiner'
    bl_region_type = "UI"
    bl_space_type = 'VIEW_3D'
    bl_category = 'Taremin'

    def draw(self, context):
        props = util.get_settings(context)
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
        row = layout.row(align=True)
        row.prop(props, 'make_single_user')

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
                operator=group_settings.TAREMIN_MESH_COMBINER_OT_GroupSettings_Add.bl_idname,
                text="",
                icon="ADD"
            )
            col.operator(
                operator=group_settings.TAREMIN_MESH_COMBINER_OT_GroupSettings_Remove.bl_idname,
                text="",
                icon="REMOVE"
            )
            col.separator()
            col.operator(
                operator=group_settings.TAREMIN_MESH_COMBINER_OT_GroupSettings_Up.bl_idname,
                text="",
                icon="TRIA_UP"
            )
            col.operator(
                operator=group_settings.TAREMIN_MESH_COMBINER_OT_GroupSettings_Down.bl_idname,
                text="",
                icon="TRIA_DOWN"
            )

        layout.separator()

        if not hasattr(bpy.types, "OBJECT_OT_apply_all_modifier"):
            box = layout.box()
            row = box.row()
            row.label(
                text="ApplyModifierアドオンがないためシェイプキーのあるオブジェクトでモディファイアの適用に失敗する可能性があります")

        row = layout.row()
        col = row.row(align=True)
        col.operator(
            operator=combine_mesh.TAREMIN_MESH_COMBINER_OT_CombineMesh.bl_idname
        )
