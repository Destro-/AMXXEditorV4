import os
import re
import sublime, sublime_plugin

from AMXXcore.core import cfg, globalvar


Regex_RemoveComments = re.compile(r'//.*?$|/\*.*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])\'', re.DOTALL | re.MULTILINE)
	
def parse_current_arguments(text):

	num_bracket		= 0
	num_parent		= 0
	num_brace 		= 0
	inBrackets 		= False
	inParents		= False
	inBraces 		= False
	inString 		= False
	
	params = [ ]
	
	i = start = end = 0
	
	def remove_comments(text):
		return re.sub(Regex_RemoveComments, lambda m: "" if m.group(0).startswith('/') else m.group(0), text)
	
	text = remove_comments(text)
	
	def add_param(param):
		param = param.strip()
		if param :
			params.append(param.strip())


	for c in text :
	#{
		i += 1

		if c == '"' :
			if inString and oldChar != '^' :
				inString = False
			else :
				inString = True

		oldChar = c

		if not inString :
			if c == '{' :
				num_brace += 1
				inBraces = True
			elif c == '}' :
				num_brace -= 1
				if num_brace == 0 :
					inBraces = False
			elif c == '[' :
				num_bracket += 1
				inBrackets = True
			elif c == ']' :
				num_bracket -= 1
				if num_bracket == 0 :
					inBrackets = False
			elif c == '(' :
				if not start :
					start = i
				else :
					num_parent += 1
					inParents = True
			elif c == ')' :
				num_parent -= 1
				if num_parent == 0 :
					inParents = False
				elif num_parent == -1 :
					add_param(text[start:i-1])
					break

		if inString or inBrackets or inBraces or inParents or not start:
			continue

		if c == ',' :
			end = i - 1
			add_param(text[start:end])
			start = i
	#}

	return params
	


def format_doct(text, _class=""):

	def replace_tabs_with_spaces(text, tab_size=4):
		lines = text.splitlines()
		def expand_tabs(line, tab_size):
			"""Reemplaza los tabs por espacios en una sola línea, manteniendo la alineación."""
			result = []
			column = 0
			for char in line:
				if char == '\t':
					space_count = tab_size - (column % tab_size)
					result.append(' ' * space_count)
					column += space_count
				else:
					result.append(char)
					column += 1
			return ''.join(result)
		return '\n'.join([expand_tabs(line, tab_size) for line in lines])


	# Tabs
	text = replace_tabs_with_spaces(text)
	
	# Remove '* '.
	lines = text.splitlines()
	text = '\n'.join([ line.replace("* ", "") for line in lines ])
	
	# To HTML1
	text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
	
	# Blod special words
	text = re.sub(r'^[\w ]+:', lambda m: '<b>{0}</b>'.format(m.group(0)), text, 0, flags=re.M)
	
	# To HTML2
	text = text.replace(" ", "&nbsp;")
	text = text.replace("\n", "<br>")
	
	return tag_code(text, _class)
	
def tag_code(text, _class=""):
	return '<div class="code %s">%s</div>' % (_class, text)

def func_to_html(func, skipType=False) :

	content = ""
	
	if func.type and not skipType:
		content += f'<span class="pawnType"><b>{globalvar.FUNC_TYPES[func.type]}</b></span>&nbsp;&nbsp;'
	if func.return_tag :
		content += f'<a class="pawnTag" href="showtag:{func.return_tag}">{func.return_tag}:</a>'
	if func.return_array :
		content += func.return_array
		
	content += f'<span class="pawnFunction">{func.name}</span>' + pawn_highlight(f'({func.parameters})')
	
	return f'<span class="pawnDefaultColor">{content}</span>'


def pawn_highlight(code):

	slist = [ ]
	def get_string(m):
		slist.append(m.group(0))
		return '<STR>'
			
	code = re.sub(r'(("[^"]*")|(\'[^\']*\'))', get_string, code)

	code = code.replace(' = ', '=')
	code = code.replace('=', '<EQUAL>')
	
	code = re.sub(r',(\w)', r', \1', code)
	code = re.sub(r'([A-Za-z_][\w_]*)\(', r'<span class="pawnFunction">\1</span>(', code)
	code = re.sub(r'([a-zA-Z_]\w*):', r'<a class="pawnTag" href="showtag:\1">\1:</a>', code)
	code = re.sub(r'([\(\)\[\]\{\}&]|\.\.\.)', r'<span class="pawnOperator">\1</span>', code)
	code = re.sub(r'\b(\d+(.\d+)?)\b', r'<span class="pawnNumber">\1</span>', code)

	code = code.replace('const ', '<span class="pawnType">const </span>')
	code = code.replace('sizeof ', '<span class="pawnType">sizeof </span>')
	code = code.replace('charsmax', '<span class="pawnType">charsmax</span>')
	code = code.replace('<EQUAL>', '<span class="pawnOperator">=</span>')
	
	for s in slist :
		code = code.replace('<STR>', f'<span class="pawnString">{s}</span>', 1)
	slist.clear()
	
	def get_tags(m):
		r = '<span class="pawnTag">{'
		for tag in m.group(1).split(',') :
			tag = tag.strip()
			r += f'<a class="pawnTag" href="showtag:{tag}">{tag}</a>, '
			
		return r[0:-2] + '}:</span>'
	
	code = re.sub(r'\{([^\}]*)\}:', get_tags, code)
	
	code = code.replace('&', '&amp;')
	
	return code

	
	
	
	