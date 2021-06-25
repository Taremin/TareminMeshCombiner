import bpy
import sys
import importlib
import inspect
from pathlib import Path


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

# モジュール読み込み
module_names = [
    "util",
    "group_settings",
    "props",
    "combine_mesh",
    "panel",
]
namespace = globals()
for name in module_names:
    fullname = '{}.{}.{}'.format(__package__, "lib", name)
    if fullname in sys.modules:
        namespace[name] = importlib.reload(sys.modules[fullname])
    else:
        namespace[name] = importlib.import_module(fullname)

# クラスの登録
classes = [
    # このファイル内のBlenderクラス
]
for module in module_names:
    for module_class in [obj for name, obj in inspect.getmembers(namespace[module], inspect.isclass) if hasattr(obj, "bl_rna")]:
        classes.append(module_class)


def register():
    for value in classes:
        retry = 0
        while True:
            try:
                bpy.utils.register_class(value)
                break
            except ValueError:
                bpy.utils.unregister_class(value)
                retry += 1
                if retry > 1:
                    break
    props = namespace["props"]
    bpy.types.Scene.taremin_mc = bpy.props.PointerProperty(
        type=props.TareminMeshCombinerProps)


def unregister():
    for value in classes:
        print("Unregister:", value)
        try:
            bpy.utils.unregister_class(value)
        except RuntimeError:
            pass

    del bpy.types.Scene.taremin_mc
    Path(__file__).touch()


if __name__ == '__main__':
    register()
