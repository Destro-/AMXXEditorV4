import os
import re
import sublime, sublime_plugin


from AMXXcore.core import globalvar

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
	
	def add_param(param):
		param = param.strip()
		if param :
			params.append(param.strip())
	####################
	

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
					print("end params")
					break

		if inString or inBrackets or inBraces or inParents or not start:
			continue

		if c == ',' :
			end = i - 1
			add_param(text[start:end])
			start = i
	#}

	return params

def pawn_highlight(str):

	slist = [ ]
	def get_string(m):
		slist.append(m.group(0))
		return '<STR>'
			
	str = re.sub(r'(("[^"]*")|(\'[^\']*\'))', get_string, str)

	str = str.replace(' = ', '=')
	str = str.replace('=', '<EQUAL>')
	
	str = re.sub(r',(\w)', r', \1', str)
	str = re.sub(r'([A-Za-z_][\w_]*)\(', r'<span class="pawnFunction">\1</span>(', str)
	str = re.sub(r'([a-zA-Z_]\w*):', r'<a class="pawnTag" href="showtag:\1">\1:</a>', str)
	str = re.sub(r'([\(\)\[\]&]|\.\.\.)', r'<span class="pawnKeyword">\1</span>', str)
	str = re.sub(r'\b(\d+(.\d+)?)\b', r'<span class="pawnNumber">\1</span>', str)

	str = str.replace('const ', '<span class="pawnConstant">const </span>')
	str = str.replace('sizeof ', '<span class="pawnConstant">sizeof </span>')
	str = str.replace('charsmax', '<span class="pawnConstant">charsmax</span>')
	str = str.replace('<EQUAL>', '<span class="pawnKeyword">=</span>')
	
	for s in slist :
		str = str.replace('<STR>', '<span class="pawnString">'+s+'</span>', 1)
	slist.clear()
	
	def get_tags(m):
		r = '<span class="pawnTag">{'
		for tag in m.group(1).split(',') :
			tag = tag.strip()
			r += '<a class="pawnTag" href="showtag:%s">%s</a>, ' % (tag, tag)
			
		return r[0:-2] + '}:</span>'
	
	str = re.sub(r'\{([^\}]*)\}:', get_tags, str)
	
	str = str.replace('&', '&amp;')
	
	return '<span class="pawnDefaultColor">' + str + '</span>'

	
	
	
	