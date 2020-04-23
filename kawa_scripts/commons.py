# Kawashirov's Scripts (c) 2019 by Sergey V. Kawashirov
#
# Kawashirov's Scripts is licensed under a
# Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
#
# You should have received a copy of the license along with this
# work.  If not, see <http://creativecommons.org/licenses/by-nc-sa/3.0/>.
#
#

import bpy
import bmesh
import mathutils
import logging

import typing

if typing.TYPE_CHECKING:
	from typing import *
	
	SizeInt = Tuple[int, int]
	UVLayerIndex = Union[str, bool, None]  # valid string (layer layer_name) or False (ignore) or None (undefined)

log = logging.getLogger('kawa.commons')
logging.basicConfig(level=logging.INFO, format='%(asctime)-15s %(levelname)8s %(layer_name)s %(message)s')


class ConfigurationError(RuntimeError):
	# Ошибка конфигурации
	pass


def poly2_area2(ps: 'Sequence[mathutils.Vector]'):
	# Площадь полигона, примерно, без учёта вогнутостей
	length = len(ps)
	if length < 3:
		return 0
	elif length == 3:
		# Частый случай, оптимизация для треугольника
		return mathutils.geometry.area_tri(ps[0], ps[1], ps[2])
	elif length == 4:
		# Частый случай, оптимизация для квада
		return mathutils.geometry.area_tri(ps[0], ps[1], ps[2]) + mathutils.geometry.area_tri(ps[0], ps[2], ps[3])
	else:
		# Для пентагона и выше - Формула Гаусса
		s = ps[length - 1].x * ps[0].y - ps[0].x * ps[length - 1].y
		for i in range(length - 1):
			s += ps[i].x * ps[i + 1].y
			s -= ps[i + 1].x * ps[i].y
		return 0.5 * abs(s)


def uv_area(poly: bpy.types.MeshPolygon, uv_layer_data: 'Sequence[bpy.types.MeshUVLoop]'):
	# tuple чуть-чуть быстрее на малых длинах, тестил через timeit
	return poly2_area2(tuple(uv_layer_data[loop].uv for loop in poly.loop_indices))


def is_none_or_bool(value: 'Optional[bool]') -> 'bool':
	return value is None or isinstance(value, bool)


def is_positive_int(pint: 'int') -> 'bool':
	return isinstance(pint, int) and pint > 0


def is_positive_float(pfloat: 'float') -> 'bool':
	return (isinstance(pfloat, int) or isinstance(pfloat, float)) and pfloat > 0


def is_none_or_positive_float(pfloat: 'float') -> 'bool':
	return pfloat is None or ((isinstance(pfloat, int) or isinstance(pfloat, float)) and pfloat > 0)


def is_positive_or_zero_float(pfloat: 'float') -> 'bool':
	return (isinstance(pfloat, int) or isinstance(pfloat, float)) and pfloat >= 0


def is_none_or_positive_or_zero_float(pfloat: 'float') -> 'bool':
	return pfloat is None or ((isinstance(pfloat, int) or isinstance(pfloat, float)) and pfloat >= 0)


def is_valid_size_int(size: 'Tuple[int, int]') -> 'bool':
	return isinstance(size, tuple) and len(size) == 2 and is_positive_int(size[0]) and is_positive_int(size[1])


def is_valid_size_float(size: 'Tuple[float, float]') -> 'bool':
	return isinstance(size, tuple) and len(size) == 2 and is_positive_float(size[0]) and is_positive_float(size[1])


def is_valid_string(string: 'str') -> 'bool':
	return isinstance(string, str) and len(string) > 0


def is_none_or_valid_string(string: 'str') -> 'bool':
	return string is None or (isinstance(string, str) and len(string) > 0)


def ensure_op_result(result: 'Iterable[str]', allowed_results: 'Iterable[str]', **kwargs):
	if set(result) >= set(allowed_results):
		raise RuntimeError('Operator has invalid result:', result, allowed_results, list(bpy.context.selected_objects), kwargs)


def ensure_op_finished(result, **kwargs):
	if 'FINISHED' not in result:
		raise RuntimeError('Operator is not FINISHED: ', result, list(bpy.context.selected_objects), kwargs)


def ensure_deselect_all_objects():
	# ensure_op_finished(bpy.ops.object.select_all(action='DESELECT'), name="bpy.ops.object.select_all(action='DESELECT')")
	# Это быстрее, чем оператор, и позволяет отжать скрытые объекты
	while len(bpy.context.selected_objects) > 0:
		bpy.context.selected_objects[0].select = False


def ensure_selected_single(selected_object, *args):
	if len(bpy.context.selected_objects) != 1:
		raise AssertionError(
			"len(bpy.context.selected_objects) != 1 or selected_object not in bpy.context.selected_objects",
			len(bpy.context.selected_objects), bpy.context.selected_objects, selected_object, args
		)
	if selected_object is not None and selected_object not in bpy.context.selected_objects:
		raise AssertionError(
			"selected_object not in bpy.context.selected_objects",
			bpy.context.selected_objects, selected_object, args
		)


def ensure_single_material_slot(_object: 'bpy.types.Object', *args) -> 'bpy.types.Material':
	if len(_object.material_slots) != 1:
		raise AssertionError("len(object.material_slots) != 1", _object, *args)
	return _object.material_slots[0].material


def repack_lightmap_uv(
		obj: 'bpy.types.Object', uv_name: 'str', rotate=None, margin=None,
):
	try:
		ensure_deselect_all_objects()
		obj.hide, obj.hide_select, obj.hide_render = False, False, False
		obj.select = True
		bpy.context.scene.objects.active = obj
		tobj_mesh = get_mesh_safe(obj)
		uv1_target = tobj_mesh.uv_textures.get(uv_name)  # type: bpy.types.MeshTexturePolyLayer
		if uv1_target is None:
			log.warning("Target Object=%s does not have target uv1: %s, %s", obj.name, uv_name, tobj_mesh.uv_textures.keys())
			return
		uv1_target.active = True
		try:
			ensure_op_finished(bpy.ops.object.mode_set(mode='EDIT'), name="bpy.ops.object.mode_set")
			bpy.context.tool_settings.mesh_select_mode = (True, True, True)  # all selection
			ensure_op_finished(bpy.ops.mesh.reveal())
			ensure_op_finished(bpy.ops.mesh.select_all(action='SELECT'))
			ensure_op_finished(bpy.ops.uv.reveal())
			ensure_op_finished(bpy.ops.uv.select_all(action='SELECT'))
			ensure_op_finished(bpy.ops.uv.average_islands_scale())
			kwargs_pack_islands = dict()
			if rotate is not None: kwargs_pack_islands['rotate'] = rotate
			if margin is not None: kwargs_pack_islands['margin'] = margin
			ensure_op_finished(bpy.ops.uv.pack_islands(**kwargs_pack_islands))
		finally:
			ensure_op_finished(bpy.ops.object.mode_set(mode='OBJECT'), name="bpy.ops.object.mode_set")
	except Exception as exec:
		raise RuntimeError("Error repack_lightmap_uv", obj, uv_name, rotate, margin) from exec


def any_not_none(*args):
	# Первый не-None, или None
	for v in args:
		if v is not None:
			return v
	return None


def get_mesh_safe(obj: 'bpy.types.Object') -> 'bpy.types.Mesh':
	mesh = obj.data
	if not isinstance(mesh, bpy.types.Mesh):
		raise ValueError("Object.data is not Mesh!", obj, mesh)
	return mesh


def remove_all_geometry(obj: 'bpy.types.Object'):
	# Очистка геометрии
	bm = bmesh.new()
	try:
		mesh = get_mesh_safe(obj)
		# Дегенеративные уебки, почему в Mesh нет API для удаления геометрии?
		bm.from_mesh(mesh)
		bm.clear()  # TODO optimize?
		bm.to_mesh(mesh)
	finally:
		bm.free()


def apply_all_modifiers(obj: 'bpy.types.Object'):
	prev_active = bpy.context.scene.objects.active
	while len(obj.modifiers) > 0:
		modifier = next(iter(obj.modifiers))
		log.info("Applying Modifier='%s' on Object='%s'", modifier.name, obj.name)
		bpy.context.scene.objects.active = obj
		bpy.ops.object.modifier_apply(modifier=modifier.name)
	bpy.context.scene.objects.active = prev_active


def remove_all_shape_keys(obj: 'bpy.types.Object'):
	mesh = get_mesh_safe(obj)
	while mesh.shape_keys is not None and len(mesh.shape_keys.key_blocks) > 0:
		sk = mesh.shape_keys.key_blocks[0]
		# Я ебал в рот того, кто придумал удалять шейпкеи из меши через интерфейс объекта
		obj.shape_key_remove(sk)


def remove_all_uv_layers(obj: 'bpy.types.Object'):
	mesh = get_mesh_safe(obj)
	while len(mesh.uv_textures) > 0:
		mesh.uv_textures.remove(mesh.uv_textures[0])


def remove_all_vertex_colors(obj: 'bpy.types.Object'):
	mesh = get_mesh_safe(obj)
	while len(mesh.vertex_colors) > 0:
		mesh.vertex_colors.remove(mesh.vertex_colors[0])


def remove_all_material_slots(obj: 'bpy.types.Object', slots=0):
	while len(obj.material_slots) > slots:
		bpy.context.scene.objects.active = obj
		ensure_op_finished(bpy.ops.object.material_slot_remove(), name='bpy.ops.object.material_slot_remove')


def remove_uv_layer_by_condition(
		mesh: 'bpy.types.Mesh',
		func_should_delete: 'Callable[[str, bpy.types.MeshTexturePolyLayer], bool]',
		func_on_delete: 'Callable[[str, bpy.types.MeshTexturePolyLayer], None]'
):
	while True:
		# Удаление таким нелепым образом, потому что после вызова remove()
		# все MeshTexturePolyLayer взятые из uv_textures становтся сломанными и крешат скрипт
		# По этому, после удаления обход начинается заново, до тех пор, пока не кончатся объекты к удалению
		# Блендер сосёт жопу
		to_delete_name = None
		to_delete = None
		for uv_layer_name, uv_layer in mesh.uv_textures.items():
			if func_should_delete(uv_layer_name, uv_layer):
				to_delete_name, to_delete = uv_layer_name, uv_layer
				break
		if to_delete is None: return
		if func_on_delete is not None: func_on_delete(to_delete_name, to_delete)
		mesh.uv_textures.remove(to_delete)


def copy_uv_layer(mesh_obj: 'bpy.types.Object', original_name: 'str', new_name: 'str', **kwargs) -> 'str':
	# Создаёт копию указанного UV слоя с указанным именем
	# возвращает новоё имя (может отличаться, например, иметь .001 на конце)
	mesh = get_mesh_safe(mesh_obj)
	bpy.context.scene.objects.active = mesh_obj
	# Копия для цели
	mesh.uv_textures[original_name].active = True
	ensure_op_finished(bpy.ops.mesh.uv_texture_add(), name='bpy.ops.mesh.uv_texture_add', object=mesh_obj, **kwargs)
	mesh.uv_textures.active.name = new_name
	return mesh.uv_textures.active.name


def copy_uv_layer_exact_name(mesh_obj: 'bpy.types.Object', original_name: 'str', new_name: 'str', **kwargs):
	# Тоже, что и copy_uv_layer, но крешит, если не получилось задать укаанное имя.
	mesh = get_mesh_safe(mesh_obj)
	new_layer = mesh.uv_textures.get(new_name)
	if new_layer is not None:
		raise RuntimeError('UV layer already exists!', new_layer, new_name, original_name, mesh_obj, kwargs)
	actual_name = copy_uv_layer(mesh_obj, original_name, new_name, **kwargs)
	if actual_name != new_name:
		raise RuntimeError('actual_name != new_name', actual_name, new_name, original_name, mesh_obj, kwargs)


def find_objects_with_material(material: 'bpy.types.Material', where: 'Iterable[bpy.types.Object]' = None) -> 'Set[bpy.types.Object]':
	objects = set()
	if where is None:
		where = bpy.context.scene.objects
	for obj in where:
		if not isinstance(obj.data, bpy.types.Mesh):
			continue
		for slot in obj.material_slots:
			if slot.material == material:
				objects.add(obj)
	return objects


def is_parent(parent_object: 'bpy.types.Object', child_object: 'bpy.types.Object') -> 'bool':
	obj = child_object
	while obj is not None:
		if parent_object == obj:
			return True
		obj = obj.parent
	return False


def find_all_child_objects(parent_object: 'bpy.types.Object', where: 'Iterable[bpy.types.Object]' = None) -> 'Set[bpy.types.Object]':
	child_objects = set()
	if where is None:
		where = bpy.context.scene.objects
	for child_object in where:
		if not isinstance(child_object.data, bpy.types.Mesh):
			continue
		if is_parent(parent_object, child_object):
			child_objects.add(child_object)
	return child_objects


def ensure_no_empty_material_slots(_object: 'bpy.types.Object'):
	for slot in _object.material_slots:
		if slot.material is None:
			raise RuntimeError("Material is not set!", _object, slot)


def switch_material_slots_from_object_to_data(_object: 'bpy.types.Object'):
	# Переключение материала с OBJECT на DATA.
	for slot in _object.material_slots:
		if slot.link == 'OBJECT':
			objec_mat = slot.material
			log.info("Object='%s': Switching Material='%s' from OBJECT to DATA...", _object.name, objec_mat.name)
			slot.link = 'DATA'
			slot.material = objec_mat


def separate_object_by_materials(
		_object: 'bpy.types.Object', new_objs: 'Optional[Set[bpy.types.Object]]' = None
) -> 'Set[bpy.types.Object]':
	# Разбивает меш по материалам.
	# В отличии от просто bpy.ops.mesh.separate(...) делаем всякие проверкии и возвращаем новые объекты
	# Возвращает new_objs или новое множество
	if new_objs is None:
		new_objs = set()  # type: Set[bpy.types.Object]
	ensure_deselect_all_objects()
	_object.select = True
	_object.hide = False
	bpy.context.scene.objects.active = _object
	ensure_op_result(
		bpy.ops.mesh.separate(type='MATERIAL'), ('FINISHED', 'CANCELLED'), name="bpy.ops.mesh.separate", object=_object
		# 'CANCELLED' если на меши один слот и разбивка не нужна
	)
	for sobj in bpy.context.selected_objects:
		new_objs.add(sobj)
	return new_objs
