import re
import collections


class ColorUtil:

	HEX_COLOR_RE 	= re.compile(r'^#([a-fA-F0-9]{3}|[a-fA-F0-9]{6})$')
	RGB 			= collections.namedtuple('ColorRGB', ['r', 'g', 'b'])
	
	def normalize_hex(hex_value):
		"""
		Normalize a hexadecimal color value to 6 digits, lowercase.
		"""
		match = ColorUtil.HEX_COLOR_RE.match(hex_value)
		if match is None:
			raise ValueError("'{}' is not a valid hexadecimal color value.".format(hex_value))

		hex_digits = match.group(1)
		if len(hex_digits) == 3:
			hex_digits = "".join(2 * s for s in hex_digits)
			
		return "#{}".format(hex_digits.lower())

	def hex_to_rgb(hex_value):
		"""
		Convert a hexadecimal color value to a 3-tuple of integers
		suitable for use in an ``rgb()`` triplet specifying that color.
		"""
		hex_value = ColorUtil.normalize_hex(hex_value)
		hex_value = int(hex_value[1:], 16)
		return ColorUtil.RGB(
			hex_value >> 16,
			hex_value >> 8 & 0xff,
			hex_value & 0xff
		)
		
	def normalize_rgb(color):
		if isinstance(color, str) :
			return ColorUtil.hex_to_rgb(color)
		
		if isinstance(color, tuple) or isinstance(color, list) :
			return ColorUtil.RGB._make(color)
			
		return color
	
	def get_brightness(color):
		color = ColorUtil.normalize_rgb(color)
		return round((0.299 * color.r) + (0.587 * color.g) + (0.114 * color.b))
	
	def is_dark(color):
		return ColorUtil.get_brightness(color) < 128

	def is_light(color):
        return not ColorUtil.is_dark(color)
	
	