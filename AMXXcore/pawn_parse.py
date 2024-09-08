import re
import time
import sublime
import threading
from AMXXcore.core 			import *
import AMXXcore.debug 		as debug



class ParseData:
	counter = 0
	
	def __init__(self):
		self.autocompletion 	= list()
		self.error_lines 		= list()
		self.funclist 			= set()
		self.constants 			= set()

		ParseData.counter += 1

	def __del__(self):
		ParseData.counter -= 1


class FuncDataStruct:
	def __init__(self, type, name, parameters, return_type, file_path, start_offset, end_offset, local_vars, param_list):
		self.type 				= type
		self.name 				= name
		self.parameters 		= parameters
		self.return_type 		= return_type
		self.file_path 			= file_path
		self.start_offset 		= start_offset
		self.end_offset 		= end_offset
		self.local_vars 		= local_vars
		self.param_list 		= param_list
		
		self.update_line(0)

	def __hash__(self):
		return hash(self.name)

	def __eq__(self, other):
		return self.parameters == other.parameters and self.type == other.type
	
	def update_line(self, base_line):
		self.start_line = base_line + self.start_offset
		self.end_line 	= base_line + self.end_offset
	
	
class pawnParse:

	PARAMS_regex 		= re.compile(r"(const\s*)?(\w*:)?([A-Za-z_][\w_]*|\.\.\.)(\[)?")
	DEFINE_regex 		= re.compile(r"#define[\s]+([^\s]+)[\s]+(.+)")
	GET_CONST_regex 	= re.compile(r"(\w*:)?([A-Za-z_][\w_]*)")
	VALID_NAME_regex 	= re.compile(r"^[A-Za-z_][\w_]*$")
		
	INVALID_NAMES = [ "new", "const", "static", "stock", "enum", "public", "native", "forward", "if", "else", "for", "while", "switch", "case", "return", "continue" ]
		
	debug.performance.init("pawnparse")
	debug.performance.init("enum")
	debug.performance.init("var")
	debug.performance.init("func")

	def __init__(self, worker_thread=None):
		self.thread = worker_thread
		
	def process(self, pFile, node, offset_line=0):

		debug.performance.start("pawnparse")
		
		if self.thread and self.thread.ident != threading.current_thread().ident :
			raise Exception("Instance only work in thread %s, The current thread is %s" % ( self.thread, threading.current_thread() ))
		
		self.data				= ParseData()
		self.file 				= pFile
		self.node 				= node
		self.found_comment 		= False
		self.found_enum 		= False
		self.enum_contents 		= ""
		
		self.offset_line 		= offset_line
		self.line_position 		= offset_line
		self.start_position		= 0

		self.region_multiline	= False
		self.region_fix_skip	= False
		self.string_regions		= [ ]
		self.mark_regions		= [ ]
		self.restore_buffer 	= ""


		self.start_parse()

		debug.performance.pause("pawnparse")

		return self.data
	
	###################################################################################################################

	def mark_error(self, offset_start, offset_end=None):

		offset_start -= self.offset_line
		if offset_end == None :
			offset_end = self.line_position - self.offset_line
		
		self.data.error_lines.append( (offset_start,offset_end) )

	# Debug/Print
	def debug(self, flag_level, func, info):
		line = str(self.start_position)
		
		if self.start_position != self.line_position :
			 line += "-%d" % self.line_position

		debug.debug(flag_level, "(Analizer) %s: >> %s - line:(%s)" % (func, info, line))
		
	def info(self, func, info):
		self.debug(debug.FLAG_INFO_PARSE, "INFO: "+func, info)
	def error(self, func, info):
		self.debug(debug.FLAG_INFO_PARSE, "ERROR: "+func, info)
		
	def read_line(self):
	#{
		if self.restore_buffer :
			line = self.restore_buffer
			self.restore_buffer = ""
		else :
			self.line_position += 1
			line = self.file.readline()
			self.raw_line = line
			
		if line :
			return line
		return None
	#}
			
	def read_string(self):
	#{
		buffer = self.read_line()
		
		if buffer is None :
			return None
		
		buffer = buffer.replace('\t', ' ')
		while '  ' in buffer :
			buffer = buffer.replace("  ", ' ')
			
		result = ""
		
		pos = -1
		total = 0
		start_valid = 0
		start_coment = -1
			
		self.region_fix_skip = self.region_multiline
		self.calculate_regions(buffer)
		
		# REMOVE Coments
		while True :
		#{
			if self.found_comment :
			#{
				pos = buffer.find("*/", pos+1)
				if pos != -1 :
					if not self.intersect_regions(pos) :
						start_valid = (pos + 2)
						total += start_valid - start_coment
						self.found_comment = False
				else :
					break
			#}
			else :
			#{
				start_coment = buffer.find("/*", start_coment+1)
				if start_coment != -1 :
					if not self.intersect_regions(start_coment) :
						result += buffer[start_valid:start_coment]
						self.found_comment = True
				else :
					break
			#}
		#}
		
		if not self.found_comment :
			result += buffer[start_valid:]
		
		pos = -1
		while True :
		#{
			pos = result.find("//", pos+1)
			if pos != -1 :
				if not self.intersect_regions(pos+total) :
					start_coment = pos+total
					result = result[0:pos]
					break
			else :
				break
		#}
		
		result = result.strip()

		if not result :
			result = self.read_string()

		return result
	#}
	
	def calculate_regions(self, buffer):
	#{
		start = -1
		if self.region_multiline :
			self.region_multiline = False
			start = 0
	
		self.string_regions = []
		
		pos = buffer.find('"')

		while pos != -1 :
		#{
			if not pos or buffer[pos - 1] != '^' :
			#{
				if start == -1 :
					start = pos
				else :
					self.string_regions += [ [ start, pos ] ]
					start = -1
			#}

			pos = buffer.find('"', (pos + 1))
		#}

		if start != -1 and buffer[len(buffer)-1] == '\\':
			self.string_regions += [ [ start, len(buffer)-1 ] ]
			self.region_multiline = True
	#}
	
	def intersect_regions(self, pos):
	#{
		if not self.string_regions :
			return False
			
		for r in self.string_regions :
			if r[0] <= pos and pos <= r[1] :
				return True
			
		return False
	#}
		
	def skip_function_block(self, buffer):
	#{
		num_brace = 0
		inString = False
		localvars = []
		invalidKeywords = [ "stock", "public", "native", "forward" ]

		if not buffer :
			buffer = self.read_string()
			
		if not buffer or buffer[0] != '{' :
			return localvars
				
		while buffer :
		#{
			if buffer.split(' ', 1)[0] in invalidKeywords :
				self.restore_buffer = buffer
				return self.function_block_finish(localvars)
			
			if cfg.ac_local_var :
				while buffer.startswith("new ") or buffer.startswith("static ") or buffer.startswith("for") :
				#{
					pos = 0
					if buffer.startswith("for") :
						pos = buffer.find("new ")
		
					if pos == -1 :
						break
						
					localvars += self.parse_variable(buffer[pos:], True)
		
					buffer = self.read_string()
					if not buffer :
						return self.function_block_finish(localvars)
				#}
			
			old = self.region_multiline
			self.region_multiline = self.region_fix_skip
			self.calculate_regions(buffer)
			self.region_multiline = old
			
			pos = buffer.find('{')
			while pos != -1 :
			#{
				if not self.intersect_regions(pos) and (not pos or buffer[pos - 1] != "'") :
					num_brace += 1
					
				pos = buffer.find('{', (pos + 1))
			#}
				
			pos = buffer.find('}')
			while pos != -1 :
			#{
				if not self.intersect_regions(pos) and (not pos or buffer[pos - 1] != "'") :
					num_brace -= 1
					
				pos = buffer.find('}', (pos + 1))
			#}
				
			
			if num_brace <= 0 :
			#{
				self.restore_buffer = buffer[pos:]
				return localvars
			#}
			
			buffer = self.read_string()
		#}
		
		return self.function_block_finish(localvars)
	#}
	
	def function_block_finish(self, localvars):
		self.mark_error(self.start_position)
		
		self.error("parse_function", "bad function closed detected, misses '}'")
		
		return localvars
	
	def valid_name(self, name):
	#{
		if not name :
			return False
			
		if name in self.INVALID_NAMES :
			return False
			
		return self.VALID_NAME_regex.search(name) is not None
	#}
	
	def add_constant(self, name):
	#{
		fixname = self.GET_CONST_regex.search(name)
		if fixname :
			name = fixname.group(2)
			self.data.constants.add(name)
	#}
	
	def add_enum(self, buffer, line):
	#{
		buffer = buffer.strip()
		if not buffer :
			return
			
		split = buffer.split('[')
		
		if not self.valid_name(split[0]) :
			self.mark_error(self.start_position+line-1, self.start_position+line)
			self.error("parse_enum", "invalid enum name [%s]" % split[0])
			return

		self.add_autocompletion(buffer, split[0], "enum")
		self.add_constant(split[0])
		
		self.info("parse_enum", "add -> [%s]" % split[0])
	#}
	
	def add_autocompletion(self, name, autocompletion, type, info=""):
	#{
		
		def strcut(s, maxlen):
			return s[:maxlen-1] + "‥" if len(s) >= maxlen else s
		

		name	= strcut(name, 30).ljust(30)
		type	= strcut(type, 10).title().rjust(10, " ")
		
		info	= strcut(info, 16).ljust(16, " ")

		include = strcut(self.node.file_name, 25).ljust(25, " ")
		
		format_info = "%s\t%s  %s %s …" % (name, info, include, type)
	
		self.data.autocompletion.append( ( format_info, autocompletion  ) )
		
		
		
		# Alternative style
		"""
		name = strcut(name, 30).ljust(30)
		info = strcut(info, 25).ljust(25, " ")
		
		filename = self.node.file_name.replace(".inc", "").replace(".sma", "")
		filename = strcut(filename, 16).rjust(16, " ")
	
		line = "("+ str(self.start_position) +")"
		line = line.rjust(8)
		
		format_info = "%s\t%s  %s  ->%s …" % (name, info, filename, line)
	
		self.node.autocompletion.append( ( format_info, autocompletion  ) )
		"""
	#}
		
	def start_parse(self):
	#{
		while True :
		#{
			buffer = self.read_string()

			if buffer is None :
				return
				
			self.start_position = self.line_position
			
			# Fix XS include (Temp!)
			buffer = buffer.replace("XS_LIBFUNC_ATTRIB", "stock")
			
			if buffer.startswith("#pragma deprecated") :
				buffer = self.read_string()
				if buffer and self.startswith(buffer, "stock") :
					self.parse_function(buffer, -1)
			elif buffer.startswith("#define ") :
				buffer = self.parse_define(buffer)
			elif buffer.startswith("enum") :
				self.parse_enum(buffer)
			elif self.startswith(buffer, "const") :
				buffer = self.parse_const(buffer)
			elif self.startswith(buffer, "new") :
				self.parse_variable(buffer, False)
			elif self.startswith(buffer, "public") :
				self.parse_function(buffer, var.FUNC_TYPES.public)
			elif self.startswith(buffer, "stock") :
				self.parse_function(buffer, var.FUNC_TYPES.stock)
			elif self.startswith(buffer, "forward") :
				self.parse_function(buffer, var.FUNC_TYPES.forward)
			elif self.startswith(buffer, "native") :
				self.parse_function(buffer, var.FUNC_TYPES.native)
			elif buffer[0] == '_' or buffer[0].isalpha() :
				self.parse_function(buffer, var.FUNC_TYPES.function)
		#}
	#}
	
	def startswith(self, buffer, str):
	#{
		if not buffer.startswith(str) :
			return False
			
		if len(str) == len(buffer) :
			return True
			
		if buffer[len(str)] == ' ' :
			return True
			
		return False
	#}
	
	def parse_define(self, buffer):
	#{
		define = self.DEFINE_regex.search(buffer)
		if define :
		#{
			name = define.group(1)
			value = define.group(2).strip()
			if value[0] != '"' :
				value = value.replace(" ", "")
				
			
			self.add_autocompletion(name, name, "define", value)
			self.add_constant(name)
			
			self.info("parse_define", "add -> [%s]" % name)
		#}
	#}
	
	def parse_const(self, buffer):
	#{
		buffer = buffer[6:]
		
		split 	= buffer.split('=', 1)
		if len(split) < 2 :
			return
			
		name 	= split[0].strip()
		value 	= split[1].strip()
		
		newline = value.find(';')
		if (newline != -1) :
		#{
			self.restore_buffer = value[newline+1:].strip()
			value = value[0:newline]
		#}
		
		fixname = self.GET_CONST_regex.search(name)
		if not fixname :
			return
			
		name = fixname.group(2)
		
		self.add_autocompletion(name, name, "const", value)
		self.add_constant(name)
		self.info("parse_const", "add -> [%s]" % name)
	#}

	def parse_variable(self, buffer, local):
	#{
		debug.performance.start("var")
		
		classChecked	= False
		varName 		= ""
		
		oldChar 		= ''
		i 				= 0
		pos 			= 0
		
		num_bracket		= 0
		num_parent		= 0
		num_brace 		= 0
		checkMissComa	= False
		emptyValue		= True
		multiLines 		= True
		skipSpaces 		= False
		skipValue 		= False
		parseName 		= True
		inBrackets 		= False
		inParents		= False
		inBraces 		= False
		inString 		= False
		found_line 		= self.line_position
		localvars		= [ ]
		
		buffer = buffer.replace("new", "", 1).replace("static", "", 1).strip()
		if not buffer :
		#{
			buffer = self.read_string()
			if not buffer :
				return self.vars_force_finish(found_line, localvars)
		#}
		
		while multiLines :
		#{
			multiLines = False
			
			for c in buffer :
			#{
				i += 1
				
				if c == '"' :
				#{
					if inString and oldChar != '^' :
						inString = False
					else :
						inString = True
				#}
				
				oldChar = c
				
				#print("A:: varName[%s] buff[%s] c[%s] - inString %d inBrackets %d inBraces %d inParents %d skipValue %d skipSpaces %d parseName %d" % (varName, buffer, c, inString, inBrackets, inBraces, inParents, skipValue, skipSpaces, parseName ))

				
				if not inString :
				#{
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
						num_parent += 1
						inParents = True
					elif c == ')' :
						num_parent -= 1
						if num_parent == 0 :
							inParents = False
				#}
				
				if inString or inBrackets or inBraces or inParents :
					continue
					
				if skipSpaces :
				#{
					if c.isspace() :
						continue
					else :
						skipSpaces = False
						if c == '=' :
							skipValue = True
						elif not skipValue :
							parseName = True
				#}
				
				if skipValue :
				#{
					if c == ',' or c == ';' :
						if emptyValue :
							return self.vars_force_finish(found_line, localvars)
						emptyValue = True
						skipValue = False
					else :
						if c != ' ' :
							emptyValue = False
						continue
				#}
				
				if checkMissComa and c.isalpha() :
					return self.vars_force_finish(found_line, localvars)
				
		
				#print("B:: varName[%s] buff[%s] c[%s] - inString %d inBrackets %d inBraces %d inParents %d skipValue %d skipSpaces %d parseName %d" % (varName, buffer, c, inString, inBrackets, inBraces, inParents, skipValue, skipSpaces, parseName ))
				
				
				if parseName :
				#{
					if c == ':' :
						skipSpaces = True
						varName = ""
					elif c == ' ' :
					#{
						varName = varName.strip()
						if varName == "const" :
						#{
							if not classChecked :
								skipSpaces = True
								classChecked = True
							else :
								return self.vars_force_finish(found_line, localvars)
								
							varName = ""
						#}
						else :
							checkMissComa = True
					#}
					elif c == '=' or c == ';' or c == ',' :
					#{
						varName = varName.strip()
						
						if varName != "" :
						#{
							if not self.valid_name(varName) :
								return self.vars_force_finish(found_line, localvars)
							else :
							#{
								if local :
									localvars += [ varName ]
									found_line = self.line_position
								else :
									self.add_autocompletion(varName, varName, "var")
									self.info("parse_variable", "add1 -> [%s]" % varName)
									
								checkMissComa = False
								classChecked = False
							#}
						#}
						else :
							return self.vars_force_finish(found_line, localvars)
							
						varName = ""
						parseName = False
						skipSpaces = True

						if c == '=' :
							skipValue = True
					#}
					elif c != ']' :
						varName += c
				#}
				
				
				#print("C:: varName[%s] buff[%s] c[%s] - inString %d inBrackets %d inBraces %d inParents %d skipValue %d skipSpaces %d parseName %d" % (varName, buffer, c, inString, inBrackets, inBraces, inParents, skipValue, skipSpaces, parseName ))

				
				if not inString and not inBrackets and not inBraces and not inParents :
				#{
					if not parseName :
						if c == ';' :
							self.restore_buffer = buffer[i:].strip()
							debug.performance.pause("var")
							return localvars
						elif not skipSpaces and not skipValue and c != ' ' and c != ',' :
							return self.vars_force_finish(found_line, localvars)
	
				
					if c == ',' :
						skipSpaces = True
				#}

			#}
			
			if not inString and not inBrackets and not inBraces and not inParents and c != '=':
				skipValue = False
					
			if inString or inBrackets or inBraces or inParents or skipValue :
				multiLines = True
				
			if inString and c != '\\' :
				return self.vars_force_finish(found_line, localvars)
				
			#print("D:: varName[%s] buff[%s] c[%s] - inString %d inBrackets %d inBraces %d inParents %d skipValue %d skipSpaces %d parseName %d multiLines %d" % (varName, buffer, c, inString, inBrackets, inBraces, inParents, skipValue, skipSpaces, parseName, multiLines ))
			

			if c != ',' :
			#{
				varName = varName.strip()
				
				if varName != "" :
				#{
					if varName == "const" :
					#{
						if not classChecked :
							skipSpaces = True
							classChecked = True
						else :
							return self.vars_force_finish(found_line, localvars)
								
						varName = ""
						parseName = True
						multiLines = True
					#}
					elif not self.valid_name(varName) :
						return self.vars_force_finish(found_line, localvars)
					else :
					#{
						if local :
							localvars += [ varName ]
							found_line = self.line_position
						else :
							self.add_autocompletion(varName, varName, "var")
							self.info("parse_variable", "add2 -> [%s]" % varName)
							
						checkMissComa = False
						classChecked = False
						parseName = False
					#}
				#}
				
			#}
			else :
				multiLines = True
			
			c = None
			i = 0
			varName = ""

			buffer = self.read_string()
			if not buffer :
				debug.performance.pause("var")
				return localvars
				
			if (skipValue or inBrackets or inBraces or inParents) :
				if buffer[0] == '#' or buffer.split(' ', 1)[0] in self.INVALID_NAMES or buffer.split('(', 1)[0] in self.INVALID_NAMES :
					self.restore_buffer = buffer
					return self.vars_force_finish(found_line, localvars)
			
			if not multiLines :
				if buffer[0] == '=' or  buffer[0] == ',' or  buffer[0] == '[' or  buffer[0] == '{' :
					if buffer[0] == ',' :
						skipSpaces = True
						skipValue = False
					if buffer[0] == '=' :
						skipValue = True						
						
					multiLines = True
				else :
					self.restore_buffer = buffer
			elif not inBraces and buffer[0] == '}' :
					self.restore_buffer = buffer
					return self.vars_force_finish(found_line, localvars)
				
			#print("E:: varName[%s] buff[%s] c[%s] - inString %d inBrackets %d inBraces %d inParents %d skipValue %d skipSpaces %d parseName %d multiLines %d" % (varName, buffer, c, inString, inBrackets, inBraces, inParents, skipValue, skipSpaces, parseName, multiLines ))
			
		#}
		
		debug.performance.pause("var")

		return localvars
	#}
	
	def vars_force_finish(self, found_line, localvars):
		self.mark_error(found_line)
		self.error("parse_vars", "invalid sintax")
		
		debug.performance.pause("var")
		
		return localvars
	
	def parse_enum(self, buffer):
	#{
		debug.performance.start("enum")
		
		if len(buffer) != 4 and buffer[4] != '{' and buffer[4] != ' ' :
			return
	
		contents = ""
		enum = ""
		ignore = True

		while buffer :
		#{
			if not ignore and buffer.split(' ', 1)[0] in self.INVALID_NAMES :
				self.restore_buffer = buffer
				self.mark_error(self.start_position)
				self.error("parse_enum", "bad enum closed detected, misses '}'")
				debug.performance.pause("enum")
				return
			
			ignore = False
			
			pos = buffer.find('}')
			
			if pos == -1 :
				contents = "%s\n%s" % (contents, buffer)
				buffer = self.read_string()
			else :
				contents = "%s\n%s" % (contents, buffer[0:pos])
				self.restore_buffer = buffer[pos+1:].strip("; ")
				break
		#}

		pos = contents.find('{')
		line = contents[0:pos].count('\n')
		contents = contents[pos + 1:]

		for c in contents :
		#{
			if c == '=' or c == '#' :
				ignore = True
			elif c == '\n':
				line += 1
				ignore = False
			elif c == ':' :
				enum = ""
				continue
			elif c == ',' :
				self.add_enum(enum, line)
				enum = ""
					
				ignore = False
				continue

			if not ignore :
				enum += c
		#}

		self.add_enum(enum, line-1)
		
		debug.performance.pause("enum")
	#}
	
	def parse_function(self, buffer, type):
	#{
		debug.performance.start("func")
		
		multi_line = False
		temp = ""
		full_func_str = ""
		open_paren_found = False
		
		while buffer :
		#{

			if not open_paren_found :
			#{
				parenpos = buffer.find('(')
			
				if parenpos == -1 :
					return
				
				open_paren_found = True
			#}
			
			if open_paren_found :
			#{
				pos = buffer.find(')')
				if pos != -1 :
					full_func_str = buffer[0:pos + 1]
					buffer = buffer[pos+1:].strip()
					
					if multi_line :
						full_func_str = '%s%s' % (temp, full_func_str)

					break

				multi_line = True
				temp = '%s%s' % (temp, buffer)
			#}

			buffer = self.read_string()
		#}

		if full_func_str :
			self.parse_function_params(buffer, full_func_str, type)
			
		debug.performance.pause("func")
	#}
	
	def parse_function_params(self, buffer, func, type):
	#{
		if type == var.FUNC_TYPES.function :
			remaining = func
		else :
			split = func.split(' ', 1)
			remaining = split[1]
		
		split = remaining.split('(', 1)
		if len(split) < 2 :
			self.error("parse_function_params", "return1 [%s]" % split)
			return
			
		remaining = split[1]
		returntype = ''
		funcname_and_return = split[0].strip()
		split_funcname_and_return = funcname_and_return.split(':')
		if len(split_funcname_and_return) > 1 :
			funcname = split_funcname_and_return[1].strip()
			returntype = split_funcname_and_return[0].strip()
		else :
			funcname = split_funcname_and_return[0].strip()
			
		# Fix float.inc
		if funcname.startswith("operator") :
			self.skip_function_block(buffer)
			return
			
		if not self.valid_name(funcname) :
			self.error("parse_function_params", "invalid name: [ %s ]  -  buffer: [ %s ]" % (funcname, buffer))
			return
	
		if type == -1 : # Deprecated !
			self.skip_function_block(buffer)
		else :
		#{
			remaining = remaining.strip()
			if remaining == ')' :
				params = []
			else :
				params = remaining[:-1].split(',')

			num = 1
			skip = False
			
			parameters 			= [ ]
			full_parameters 	= func[func.find("(")+1:-1]
			autocompletion 		= funcname + '('
			
			for param in params :
				param = param.strip()
				
				if cfg.ac_add_parameters and not skip:
	
					if cfg.ac_add_parameters == 1 and "=" in param :
						skip = True
					else :
						if num > 1 :
							autocompletion += ', '
						autocompletion += '${%d:%s}' % (num, param)
						num += 1

				result = self.PARAMS_regex.match(param)
				if result :
					if result.group(4) :
						parameters += [ result.group(3) + "[]" ]
					else :
						parameters += [ result.group(3) ]
					
			autocompletion += ')'
			
			# Find local vars
			endline = startline = self.start_position

			localvars = set()
			
			if type <= var.FUNC_TYPES.stock :
				localvars.update(parameters)
				localvars.update(self.skip_function_block(buffer))
				endline = self.line_position
				
			self.add_autocompletion(funcname, autocompletion, var.FUNC_TYPES[type])
			self.info("parse_function_params", "add -> [%s]" % func)

			self.data.funclist.add( FuncDataStruct(type, funcname, full_parameters, returntype, self.node.file_path, startline - self.offset_line, endline - self.offset_line, localvars, parameters) )
		#}
	#}
#}

