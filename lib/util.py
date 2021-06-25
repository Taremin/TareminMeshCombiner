import bpy


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


def get_settings(context):
    return context.scene.taremin_mc
