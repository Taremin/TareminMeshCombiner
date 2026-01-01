import bpy
import numpy
from . import group_settings, shape_key_split_settings

# for EnumProperty bug
# https://docs.blender.org/api/current/bpy.props.html#bpy.props.EnumProperty
shape_key_split_axis_mode_enum = None


class TareminMeshCombinerProps(bpy.types.PropertyGroup):
    output_collection: bpy.props.StringProperty(
        name="Output Collection", default="Combined Objects"
    )
    output_default_object: bpy.props.StringProperty(
        name="Default Output Object", default="Combined"
    )
    remove_unnecessary_vertex_groups: bpy.props.BoolProperty(
        name="デフォームボーン以外の頂点グループの削除",
        default=True,
        description="デフォームボーン以外の頂点グループの削除を行う",
    )
    remove_unnecessary_bones: bpy.props.BoolProperty(
        name="非選択アーマチュアレイヤーのボーン削除",
        default=True,
        description="非選択状態のアーマチュアレイヤーにあるボーンの削除を行う",
    )
    remove_empty_collection: bpy.props.BoolProperty(
        name="空のコレクションの削除",
        default=True,
        description="結合などや削除で空になったコレクションを削除する",
    )
    make_single_user: bpy.props.BoolProperty(
        name="結合オブジェクトのシングルユーザー化",
        default=True,
        description="モディファイアの適用前にオブジェクトのシングルユーザー化を行う",
    )
    apply_shape_key_vertex_groups: bpy.props.BoolProperty(
        name="シェイプキーの頂点グループを適用",
        default=False,
        description="結合前に、頂点グループが設定されたシェイプキーの変形をBasisに適用します",
    )
    groups_folding: bpy.props.BoolProperty()
    combine_groups: bpy.props.CollectionProperty(
        type=group_settings.TareminMeshCombinerGroupSettings
    )
    combine_group_index: bpy.props.IntProperty()

    shape_key_split_folding: bpy.props.BoolProperty()
    shape_key_split: bpy.props.CollectionProperty(
        type=shape_key_split_settings.TareminMeshCombinerShapeKeySplitSettings
    )
    shape_key_split_index: bpy.props.IntProperty()

    left_right_axis = {
        "Left:+X, Right:-X": lambda basis: [
            x := basis.ravel()[0::3],
            (numpy.where(x > 0.0), numpy.where(x < 0.0)),
        ][-1],
        "Left:-X, Right:+X": lambda basis: [
            x := basis.ravel()[0::3],
            (numpy.where(x < 0.0), numpy.where(x > 0.0)),
        ][-1],
    }

    def get_shape_key_split_axis_mode(self, context):
        global shape_key_split_axis_mode_enum
        shape_key_split_axis_mode_enum = [
            (key, key, key) for key, value in self.left_right_axis.items()
        ]
        return shape_key_split_axis_mode_enum

    shape_key_split_axis_mode: bpy.props.EnumProperty(
        items=get_shape_key_split_axis_mode
    )
