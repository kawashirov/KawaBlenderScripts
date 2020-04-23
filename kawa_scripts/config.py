import bpy
import typing

from operator import itemgetter

if typing.TYPE_CHECKING:
	from typing import *
	
	Priority = Optional[float]


class ConfigParameter:
	
	def __init__(self, **kwargs):
		self._values = dict()
		self._priorities = dict()  # type: Dict[Any, float]
		self.validator_key = kwargs.get('validator_key')  # type: Callable[[Any], bool]
		self.validator_value = kwargs.get('validator_value')  # type: Callable[[Any], bool]
		
		default_values = kwargs.get('default_values') or dict()
		default_priorities = kwargs.get('default_priorities') or dict()
		
		default_keys = set()
		default_keys.update(default_values.keys())
		default_keys.update(default_priorities.keys())
		
		for key in default_keys:
			value, priority = default_values.get(key), default_priorities.get(key)
			if value is not None:
				self.set_value(key, value, priority=priority)
	
	def set_value(self, key, value, priority: 'Priority' = None):
		# Если value is None, то это полное удаление ключа.
		if self.validator_key is not None and not self.validator_key(key):
			raise KeyError("Invalid key!", key)
		if value is not None:
			if self.validator_value is not None and not self.validator_value(value):
				raise KeyError("Invalid value!", value)
			self._values[key] = value
			if priority is not None:
				self._priorities[priority] = value
		else:
			self._values.pop(key, None)
			self._priorities.pop(key, None)
	
	def get_value(self, key: 'Hashable', default=None):
		return self._values.get(key, default=default)
	
	def get_priority(self, key: 'Hashable') -> 'Priority':
		return self._priorities.get(key)
	
	def get_both(self, key: 'Hashable') -> 'Tuple[Priority, Any]':
		return self.get_priority(key), self.get_value(key)
	
	def select_value(self, *keys: 'Hashable'):
		# Выбирает значение с наибольшим приоритетом из выбранных ключей.
		# Исключение, если более чем одно значение с макс. приоритетом, даже если значения равны.
		if len(keys) < 1:
			raise ValueError("len(keys) < 1", len(keys))
		items = list((k, self._values.get(k), self._priorities.get(k, 0)) for k in keys if k in self._values)
		if len(items) < 1:
			return None  # неопределено
		if len(items) == 1:
			return items[0]  # однозначно
		items.sort(key=itemgetter(2), reverse=True)
		if items[0][2] == items[1][2]:
			raise RuntimeError("More than one values with same priority!", items)
		return items[0][1]


def is_object_material_tuple(x):
	return isinstance(x, tuple) and isinstance(x[0], bpy.types.Object) and isinstance(x[0], bpy.types.Material)
