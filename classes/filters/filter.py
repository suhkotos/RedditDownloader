"""
	Filter class and static methods to access all available filters.
"""
import pkgutil
import os
import re
from enum import Enum
from classes import filters


class Operators(Enum):
	""" Enum for porting around operators. """
	EQUALS = '.equals'
	MINIMUM = '.min'
	MAXIMUM = '.max'
	MATCH = '.match'


class Filter:
	"""
	The generic Filter class. Also used as the base for any custom filters.
	Filters are used by Sources to weed out RedditElements the user doesn't want.
	OVERRIDES:
		init() !- To set the field value
		check() - If this Filter needs to use custom logic to check values
		_convert_imported_limit() - If the user-supplied limit value needs converting.
	"""
	def __init__(self, field, description):
		""" Creates a new Filter with the given field name/operator/limit. """
		self.field = field
		self.operator = None
		self._limit = None
		self.description = description
		self.accepts_operator = True

	def set_operator(self, op):  # !cover
		""" Sets this Filter's Operator. """
		if self._lookup_operator(op):
			self.operator = op
			return True
		return False

	def set_limit(self, limit):
		""" Sets the limit of this Filter. Autocasts as needed. """
		self._limit = self._cast(limit)

	def get_limit(self):
		return self._limit

	def get_description(self):
		return self.description

	def check(self, obj):
		"""  Checks the given object to verify if this Filter's field - within the object - is within parameters.
			Automatically casts numeric values if possible, then compares.
		"""
		if not hasattr(obj, self.field):
			raise Exception('No field: %s' % self.field)  # !cover
		val = self._cast(getattr(obj, self.field))
		lim = self.get_limit()
		if isinstance(val, str) or isinstance(lim, str):  # Case doesn't matter for the basic comparisons.
			val = str(val).lower()
			lim = str(lim).lower()
		if self.operator == Operators.MAXIMUM:
			return val <= lim
		if self.operator == Operators.MINIMUM:
			return val >= lim
		if self.operator == Operators.EQUALS:
			return val == lim
		if self.operator == Operators.MATCH:
			regexp = re.compile(str(self.get_limit()), re.IGNORECASE)
			if regexp.search(str(val)):
				return True
			return False
		raise Exception("Invalid comparator for Filter!")  # !cover

	def _cast(self, val):
		"""  Attempt to cast to integer, or just return the value as a string.  """
		try:
			return int(float(val))
		except ValueError:
			return str(val)

	def _convert_imported_limit(self, val):
		""" Returns unchanged val by default.
			Exists to allow easy overriding to convert input limit values.
			Return None to signify invalid value, and cancel from_obj() build.
		"""
		return val

	def from_obj(self, key, value):
		"""
			Expects key, value pair from Settings. Parses this setting into a Filter object.
			Returns False if this Filter doesn't match the given key.
		"""
		ret = self._parse_str(key)
		if not ret:
			return False
		conv = self._convert_imported_limit(value)
		if conv is None:
			return False
		self.set_limit(conv)
		return ret

	def to_js_obj(self):
		""" Build an object that represents this Filter. Used by WebUI. """
		return {
			'field': self.field,
			'operator': self.operator.value if self.operator else None,
			'accepts_operator': self.accepts_operator,
			'limit': self._limit,
			'description': self.description
		}

	def to_keyval(self):
		""" Convert this source into a data model that can be saved/loaded from Settings.
			Returns: key, val -> This represents the way this is stored within the "Filters" JSON Object.
		"""
		op = self._lookup_operator(self.operator, True)
		if not op:
			op = ''
		return self.field+op, self._limit

	def _parse_str(self, str_key):
		"""  Parses the given filter string into this filter, setting its values.  """
		if self.field not in str_key:
			return False
		op = None
		for k in Operators:
			v = k.value
			if v in str_key.lower():
				op = k
		if '.' not in str_key:
			op = Operators.EQUALS  # !cover
		if self._lookup_operator(op):
			self.operator = op
		else:
			raise Exception('Unable to parse operator for Filter: %s' % self.field)  # !cover
		return True

	def _lookup_operator(self, op, return_value=False):
		"""  Returns if this operator is a valid operator string or not. If set, returns mapped value. """
		if op in Operators:
			if return_value:
				return op.value
			return True
		return False

	def __str__(self):  # !cover
		lim = self._limit
		if isinstance(lim, str):
			lim = '"%s"' % lim
		if self.operator is None or lim is None:
			return "Filter: %s (%s)" % (self.field, self.description)
		return "Filter: %s %s %s (%s)" % (
			self.field,
			self.operator.value.replace('.', ''),
			lim,
			self.description
		)


def get_filters(filter_dict=None):
	""" Get a list of all availale Filter objects.
		If passed a dict of {'field.operator':val} - as specified by the filter settings syntax -
			it will return loaded filter objects.
	"""
	pkg_path = os.path.dirname(filters.__file__)
	loaded = []
	used = []
	# Load packaged classes first, as they need to be treated specially in the event of custom data.
	for _, name, _ in pkgutil.iter_modules([pkg_path]):
		if '_filter' not in name:
			continue
		fi = __import__('classes.filters.%s' % name, fromlist=[''])
		for clazz in _module_classes(fi):
			if filter_dict is not None:
				for k, v in filter_dict.items():
					cl = clazz()
					if cl.from_obj(k, v):
						loaded.append(cl)
						used.append(cl.field)
			else:
				cl = clazz()
				loaded.append(cl)
				used.append(cl.field)
	# Append default field filters, if not already handled by special ones above.
	for k, v in get_filter_fields().items():
		if k in used:
			continue
		if filter_dict is not None:
			for loaded_field, loaded_val in filter_dict.items():
				cl = Filter(field=k, description=v)  # New filter for default values.
				if cl.from_obj(loaded_field, loaded_val):
					loaded.append(cl)
		else:
			cl = Filter(field=k, description=v)  # New filter for default values.
			loaded.append(cl)

	return loaded


def _module_classes(module_trg):
	"""  Pull the classes from the given module.  """
	md = module_trg.__dict__
	return [
		md[c] for c in md if (
			isinstance(md[c], type) and md[c].__module__ == module_trg.__name__
		)
	]


def get_filter_fields():
	""" Builds a list of acceptable fields to filter Elements by. """
	return {
		'link_count': 'The amount of links found for this element. (#)',
		'type': 'The type of post this is. ("Submission" or "Comment")',
		'title':  'The title of the submission containing this post. (Text)',
		'author': 'The author of this element. (Text)',
		'body':  'The text in this element. Blank if this post is a submission without selftext. (Text)',
		'subreddit': 'The subreddit this element is from. (Text)',
		'over_18': 'If this post is age-limited, AKA "NSFW". (True/False)',
		'created_utc': 'The timestamp, in UTC seconds, that this element was posted. (#)',
		'num_comments': 'The number of comments on this post. (#)',
		'score': 'The number of net upvotes on this post. (#)',
	}


if __name__ == '__main__':
	print('All available:')
	for f in get_filters():
		print(f)
	print()
	print("Loading...")

	class TestPost:  # Dummy Post object.
		def __init__(self):
			self.created_utc = 99
			self.title = 'Test Title'

	test_post = TestPost()
	all_filters = get_filters({
		'created_utc.min': 0,
		'created_utc.max': 100,
		'created_utc': 99,
		'created_utc.match': '99',
		'title.match': 'Test'
	})
	print('Loaded Filters:')
	for f in all_filters:
		print('\t', f.to_keyval())

	print('\nRunning checks on test:', test_post)
	for f in all_filters:
		print(f.check(test_post), '|', f)
