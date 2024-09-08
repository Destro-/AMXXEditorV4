import sys
import re
import time

from AMXXcore.core import cfg, globalvar
import AMXXcore.debug as debug


def debug_instances_info():
	return "Global Instances: ParseData(%d), TagDataStruct(%d), FuncDataStruct(%d)" % (
		ParseData.get_counter(),
		TagDataStruct.get_counter(),
		FuncDataStruct.get_counter()
	)


class ParseData:
	counter = 0
	
	def __init__(self):
		self.autocomplete 		= list()
		self.error_lines 		= list()
		self.funclist 			= set()
		self.constants 			= dict()
		self.tags				= dict()

		type(self).counter += 1

	def __del__(self):
		type(self).counter -= 1

	@classmethod
	def get_counter(cls):
		return cls.counter

class ConstDataStruct:
	def __init__(self, _type, file_path, offset_line, doct1="", doct2=""):
		self.type			= _type
		self.file_path		= file_path
		self.offset_line	= offset_line
		self.doct1			= doct1
		self.doct2			= doct2
		
		self.update_line(0)
		
	def __repr__(self):
		return f"<ConstDataStruct: type({self.type})>"
	
	def update_line(self, baseline):
		self.line = baseline + self.offset_line

class TagDataStruct:
	counter = 0
	
	def __init__(self, name, line_offset, file_path):
		self.name 				= name
		self.file_path 			= file_path
		self.line_offset 		= line_offset
		self.line				= 0
		self.isenum				= False
		self.funclist			= set()
		
		self.doct1			= None
		self.doct2			= None
		
		self.update_line(0)
		
		type(self).counter += 1

	def __del__(self):
		type(self).counter -= 1
		
	def __hash__(self):
		return hash(self.name)

	def __eq__(self, other):
		return self.name == other.name
		
	def __repr__(self):
		return f"<TagDataStruct: name('{self.name}')>"
	
	def update_line(self, baseline):
		self.line = baseline + self.line_offset
		
	def add_func(self, func):
		self.funclist.add(func)
		
	@classmethod
	def get_counter(cls):
		return cls.counter
		
class FuncDataStruct:
	counter = 0
	
	def __init__(self, _type, name, parameters, return_tag, return_array, file_path, start_offset, end_offset, local_vars, param_list):
		self.type 				= _type
		self.name 				= name
		self.parameters 		= parameters
		self.return_tag 		= return_tag
		self.return_array		= return_array
		self.file_path 			= file_path
		self.start_offset 		= start_offset
		self.end_offset 		= end_offset
		self.local_vars 		= local_vars
		self.param_list 		= param_list

		self.update_line(0)
		
		type(self).counter += 1

	def __del__(self):
		type(self).counter -= 1
		
	def __hash__(self):
		return hash(self.name)

	def __eq__(self, other):
		return self.parameters == other.parameters and self.type == other.type
		
	def __repr__(self):
		return f"<FuncDataStruct: name('{self.name}')>"
	
	def update_line(self, baseline):
		self.start_line = baseline + self.start_offset
		self.end_line 	= baseline + self.end_offset
	
	@classmethod
	def get_counter(cls):
		return cls.counter

class pawnParse:

	Regex_VALID_PARAM = re.compile(r"(const\s*)?(\w*}?:)?([A-Za-z_][\w_]*|\.\.\.)(\[\w*\])?")
	DEFINE_regex 		= re.compile(r"#define[\s]+([^\s]+)[\s]+(.+)")
	GET_CONST_regex 	= re.compile(r"(\w*:)?([A-Za-z_][\w_]*)")
	VALID_NAME_regex 	= re.compile(r"^[A-Za-z_][\w_]*$")
		
	INVALID_NAMES = [ "new", "const", "static", "stock", "enum", "public", "native", "forward", "if", "else", "for", "while", "switch", "case", "return", "continue" ]
		
	debug.performance.init("pawnparse")
	debug.performance.init("enum")
	debug.performance.init("var")
	debug.performance.init("func")

	def __init__(self):
		pass

	def process(self, pFile, node, offset_line=0):

		debug.performance.start("pawnparse")

		self.data				= ParseData()
		self.file 				= pFile
		self.node 				= node

		self.offset_line 		= offset_line
		self.line_position 		= offset_line
		self.start_position		= offset_line

		self.mark_regions		= [ ]
		self.restore_buffer 	= ""
		
		self.found_comment		= False
		self.found_string		= False
		
		self.raw_parse_code		= ""
		self.backup_string 		= ""
		self.comment_doct1		= ""
		self.comment_doct2		= ""


		self.start_parse()

		debug.performance.pause("pawnparse")

		return self.data
	
	###################################################################################################################

	def start_parse(self):
	#{
		while True :
		#{
			self.raw_parse_code	= ""
			
			buffer = self.read_clean_line()

			if buffer is None :
				return
				
			self.start_position = self.line_position
			
			# Fix XS include (Temp!)
			buffer = buffer.replace("XS_LIBFUNC_ATTRIB", "stock")
			
			try:
				if buffer.startswith("#pragma deprecated") :
					buffer = self.read_clean_line()
					if buffer and self.startswith(buffer, "stock") :
						self.parse_function(buffer, -1)
				elif buffer.startswith("#define ") :
					buffer = self.parse_define(buffer)
				elif buffer.startswith("enum") :
					self.parse_enum(buffer)
				elif self.startswith(buffer, "const") :
					buffer = self.parse_const(buffer)
				elif self.startswith(buffer, "new") or self.startswith(buffer, "stock const") :
					self.parse_variable(buffer, False)
				elif self.startswith(buffer, "public") :
					self.parse_function(buffer, globalvar.FUNC_TYPES.public)
				elif self.startswith(buffer, "stock") :
					self.parse_function(buffer, globalvar.FUNC_TYPES.stock)
				elif self.startswith(buffer, "forward") :
					self.parse_function(buffer, globalvar.FUNC_TYPES.forward)
				elif self.startswith(buffer, "native") :
					self.parse_function(buffer, globalvar.FUNC_TYPES.native)
				elif buffer[0] == '_' or buffer[0].isalpha() :
					self.parse_function(buffer, globalvar.FUNC_TYPES.function)
			except Exception:
			
				if globalvar.rollbar and cfg.rollbar_report :
					globalvar.rollbar.set_parse_code(self.raw_parse_code.strip())

				sys.excepthook(*sys.exc_info())	
		#}
	#}
	
	def startswith(self, buffer, _with):
	#{
		if not buffer.startswith(_with) :
			return False
			
		if len(_with) == len(buffer) :
			return True
			
		if buffer[len(_with)] == ' ' :
			return True
			
		return False
	#}
	

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

		debug.debug(flag_level, "(Analyzer) %s: >> %s - line:(%s)" % (func, info, line))
		
	def info(self, func, info):
		self.debug(debug.FLAG_PARSE_INFO, "INFO: "+func, info)
	def error(self, func, info):
		self.debug(debug.FLAG_PARSE_ERROR, "ERROR: "+func, info)
		
	def read_line(self):
	#{
		if self.restore_buffer :
			line = self.restore_buffer
			self.restore_buffer = ""
		else :
			self.line_position += 1
			line = self.file.readline()
			
		if line :
			self.raw_parse_code += line # Used for report to rollbar
			return line
		return None
	#}
			
	def read_clean_line(self, recursive=False):
	#{
		buffer = self.read_line()

		if buffer is None:
			return None

		if not recursive :
			self.backup_string = ""
			self.comment_doct1 = ""
			
		cleanbuff = ""
		start_valid = 0
		start_skip = -1
		pos = -1

		while True:
		
			if self.found_string :
				pos = buffer.find('"', start_skip + 1)
				
				if pos == -1:
					break
					
				if pos > 0 and buffer[pos - 1] == '^' :
					start_skip = pos
					continue
				
				start_valid = pos + 1
				
				# used to show partial info (autocomplete/tooltip), single line (issue if '^')
				self.backup_string = buffer[max(start_skip, 0):start_valid]

				start_skip = start_valid
				
				self.found_string = False

			elif self.found_comment:
				pos = buffer.find('*/', start_skip + 1)
				
				if pos == -1:
					start_skip = 0 if start_skip == -1 else start_skip + 2
					self.comment_doct1 += (buffer[start_skip:] + "\n")
					break

				start_skip = 0 if start_skip == -1 else start_skip + 2
				
				self.comment_doct1 += buffer[max(start_skip, 0):pos]

				start_skip = start_valid = pos + 2
				
				self.found_comment = False
			else:
				comment = buffer.find('/*', start_skip + 1)
				string = buffer.find('"', start_skip + 1)
				if comment == -1 and string == -1 :
					break
					
				if string == -1 or ( -1 < comment < string ) :
					start_skip = comment
					self.found_comment = True
					self.comment_doct1 = ""
					cleanbuff += buffer[start_valid:start_skip]
				elif comment == -1 or ( -1 < string < comment ) :
					start_skip = string
					self.found_string = True
					cleanbuff += buffer[start_valid:start_skip] + '""'
				

		if not self.found_string and not self.found_comment :
			cleanbuff = cleanbuff + buffer[start_valid:] if start_valid else buffer # op

		if cleanbuff :
			pos = cleanbuff.find("//")
			if pos != -1 :
				self.comment_doct2 = cleanbuff[pos + 2:].strip()
				cleanbuff = cleanbuff[0:pos]
			else :
				self.comment_doct2 = ""
			
			cleanbuff = cleanbuff.replace('\t', ' ')
			cleanbuff = ' '.join(cleanbuff.split())
		
		if not cleanbuff:
			cleanbuff = self.read_clean_line(True)

		return cleanbuff
	#}
	
	def skip_function_block(self, buffer):
	#{
		num_brace = 0
		localvars = []
		invalidKeywords = [ "stock", "public", "native", "forward" ]

		if not buffer :
			buffer = self.read_clean_line()
			
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
		
					buffer = self.read_clean_line()
					if not buffer :
						return self.function_block_finish(localvars)
				#}
			
			# SKIP #else ... #end
			# very simple, it does not make sense to make it so complex when it is hardly ever used
			if buffer.startswith("#else") :
				while not buffer.startswith("#end") :
					buffer = self.read_clean_line()
				buffer = self.read_clean_line()
			###############################################
			
			pos = buffer.find('{')
			while pos != -1 :
			#{
				if pos == 0 or buffer[pos - 1] != "'" :
					num_brace += 1
					
				pos = buffer.find('{', (pos + 1))
			#}
				
			pos = buffer.find('}')
			while pos != -1 :
			#{
				if pos == 0 or buffer[pos - 1] != "'" :
					num_brace -= 1
					
				pos = buffer.find('}', (pos + 1))
			#}	
			
			if num_brace <= 0 :
			#{
				self.restore_buffer = buffer[pos:]
				return localvars
			#}
			
			buffer = self.read_clean_line()
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
	
	def clear_doct(self, text):

		text = text.replace("\r", "")
		text = text.replace("\n\n", "\n")
		text = text.replace("*\n", "")
		
		lines = text.splitlines()
		text = '\n'.join([ line.strip() for line in lines ])
		
		return text.strip()
		
	def add_constant(self, name, _type):
	#{
		fixname = self.GET_CONST_regex.search(name)
		if fixname :
			name = fixname.group(2)
			
			doct1 = self.comment_doct1
			doct2 = self.comment_doct2
			
			if doct1 :
				doct1 = self.clear_doct(doct1)
			if doct2 :
				doct2 =  self.clear_doct(doct2)
				
			self.data.constants[name] = ConstDataStruct(_type, self.node.file_path, self.start_position - self.offset_line, doct1, doct2)
	#}
	
	def add_enumtag(self, tagname):
		
		fixname = self.GET_CONST_regex.search(tagname)
		if fixname :
			tagname = fixname.group(2)
			self.add_tag(tagname)
			self.info("parse_enum", "addTag -> [%s]" % tagname)

	def add_tag(self, tagname, func=None):
		
		if tagname in [ "Float", "_", "bool", "any" ] :
			return
		
		tag = self.data.tags.get(tagname)
		if not tag :
			tag = TagDataStruct(tagname, self.start_position - self.offset_line, self.node.file_path)
			self.data.tags[tagname] = tag
		
		if func :
			tag.add_func(func)
		else : # without func it is only called from add_enumtag(), this data is used to `goto_definition`.
			tag.line_offset = self.start_position - self.offset_line
			tag.file_path = self.node.file_path
			tag.isenum = True
			
			if self.comment_doct1 :
				tag.doct1 = self.clear_doct(self.comment_doct1)
			if self.comment_doct2 :
				tag.doct2 =  self.clear_doct(self.comment_doct2)

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

		self.add_autocomplete(buffer, split[0], "enum")
		self.add_constant(split[0], globalvar.CONST_TYPES.ENUM)
		
		self.info("parse_enum", "add -> [%s]" % split[0])
	#}
	
	def add_autocomplete(self, name, autocomplete, type, info=""):
	#{
		
		def strcut(s, maxlen):
			return s[:maxlen-1] + "‥" if len(s) >= maxlen else s
		
		name	= strcut(name, 30).ljust(30)
		
		if not info :
			info = type
		
		info	= strcut(info, 20).ljust(20, " ")

		include = strcut(self.node.file_name, 19).rjust(19, " ")
		
		format_info = "%s\t%s %s" % (name, info, include)
	
		self.data.autocomplete.append( ( format_info, autocomplete  ) )
		
		
		
		# Alternative style
		"""
		name = strcut(name, 30).ljust(30)
		info = strcut(info, 25).ljust(25, " ")
		
		filename = self.node.file_name.replace(".inc", "").replace(".sma", "")
		filename = strcut(filename, 16).rjust(16, " ")
	
		line = "("+ str(self.start_position) +")"
		line = line.rjust(8)
		
		format_info = "%s\t%s  %s  ->%s …" % (name, info, filename, line)
	
		self.node.autocomplete.append( ( format_info, autocomplete  ) )
		"""
	#}
	
	def parse_define(self, buffer):
	#{
		define = self.DEFINE_regex.search(buffer)
		if define :
		#{
			name = define.group(1)
			value = define.group(2).strip()
			
			if value[-1] == '\\' :
				value = "define blockcode"
			elif value[0] != '"' :
				value = value.replace(" ", "")
			else :
				value = self.backup_string
			
			self.add_autocomplete(name, name, "define", value)
			self.add_constant(name, globalvar.CONST_TYPES.DEFINE)
			
			self.info("parse_define", "add -> [%s]" % name)
		#}
		
		# Skip multiline
		while buffer[-1] == '\\' :
			buffer = self.read_clean_line()
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
		
		self.add_autocomplete(name, name, "const", value)
		self.add_constant(name, globalvar.CONST_TYPES.CONST)
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
		num_paren		= 0
		num_brace 		= 0
		checkMissComma	= False
		emptyValue		= True
		multiLines 		= True
		skipSpaces 		= False
		skipValue 		= False
		parseName 		= True
		inBrackets 		= False
		inParens		= False
		inBraces 		= False
		inString 		= False
		found_line 		= self.line_position
		localvars		= [ ]
		
		buffer = buffer.replace("new ", "", 1).replace("static ", "", 1).replace("stock ", "", 1).strip()
		if not buffer or buffer == "new" or buffer == "static" or buffer == "stock" :
		#{
			buffer = self.read_clean_line()
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
				
				#print("A:: varName[%s] buff[%s] c[%s] - inString %d inBrackets %d inBraces %d inParens %d skipValue %d skipSpaces %d parseName %d" % (varName, buffer, c, inString, inBrackets, inBraces, inParens, skipValue, skipSpaces, parseName ))

				
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
						num_paren += 1
						inParens = True
					elif c == ')' :
						num_paren -= 1
						if num_paren == 0 :
							inParens = False
				#}
				
				if inString or inBrackets or inBraces or inParens :
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
							return self.vars_force_finish(found_line, localvars, "x01 - empty value")
						emptyValue = True
						skipValue = False
					else :
						if c != ' ' :
							emptyValue = False
						continue
				#}
				
				if checkMissComma and c.isalpha() :
					return self.vars_force_finish(found_line, localvars, "x02 - missing comma")
				
		
				#print("B:: varName[%s] buff[%s] c[%s] - inString %d inBrackets %d inBraces %d inParens %d skipValue %d skipSpaces %d parseName %d" % (varName, buffer, c, inString, inBrackets, inBraces, inParens, skipValue, skipSpaces, parseName ))
				
				
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
								return self.vars_force_finish(found_line, localvars, "x03 - using multi 'const'")
								
							varName = ""
						#}
						else :
							checkMissComma = True
					#}
					elif c == '=' or c == ';' or c == ',' :
					#{
						varName = varName.strip()
						
						if varName != "" :
						#{
							if not self.valid_name(varName) :
								return self.vars_force_finish(found_line, localvars, "x04 - invalid name2")
							else :
							#{
								if local :
									localvars += [ varName ]
									found_line = self.line_position
								else :
									self.add_autocomplete(varName, varName, "var")
									self.info("parse_variable", "addA -> [%s]" % varName)
									
								checkMissComma = False
								classChecked = False
							#}
						#}
						else :
							return self.vars_force_finish(found_line, localvars, "x05 - empty varname")
							
						varName = ""
						parseName = False
						skipSpaces = True

						if c == '=' :
							skipValue = True
					#}
					elif c != ']' :
						varName += c
				#}
				
				
				#print("C:: varName[%s] buff[%s] c[%s] - inString %d inBrackets %d inBraces %d inParens %d skipValue %d skipSpaces %d parseName %d" % (varName, buffer, c, inString, inBrackets, inBraces, inParens, skipValue, skipSpaces, parseName ))

				
				if not inString and not inBrackets and not inBraces and not inParens :
				#{
					if not parseName :
						if c == ';' :
							self.restore_buffer = buffer[i:].strip()
							debug.performance.pause("var")
							return localvars
						elif not skipSpaces and not skipValue and c != ' ' and c != ',' :
							return self.vars_force_finish(found_line, localvars, "x06")
	
				
					if c == ',' :
						skipSpaces = True
				#}

			#}
			
			if not inString and not inBrackets and not inBraces and not inParens and c != '=':
				skipValue = False
					
			if inString or inBrackets or inBraces or inParens or skipValue :
				multiLines = True
				
			#print("D:: varName[%s] buff[%s] c[%s] - inString %d inBrackets %d inBraces %d inParens %d skipValue %d skipSpaces %d parseName %d multiLines %d" % (varName, buffer, c, inString, inBrackets, inBraces, inParens, skipValue, skipSpaces, parseName, multiLines ))
			
			if inString and c != '\\' :
				return self.vars_force_finish(found_line, localvars, "x07 - bad string finish")

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
							return self.vars_force_finish(found_line, localvars, "x08 - using multi 'const'")
								
						varName = ""
						parseName = True
						multiLines = True
					#}
					elif not self.valid_name(varName) :
						return self.vars_force_finish(found_line, localvars, "x09 - invalid name")
					else :
					#{
						if local :
							localvars += [ varName ]
							found_line = self.line_position
						else :
							self.add_autocomplete(varName, varName, "var")
							self.info("parse_variable", "addB -> [%s]" % varName)
							
						checkMissComma = False
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

			buffer = self.read_clean_line()
			if not buffer :
				debug.performance.pause("var")
				return localvars
				
			if skipValue or inBrackets or inBraces or inParens :
				if buffer[0] == '#' or buffer.split(' ', 1)[0] in self.INVALID_NAMES or buffer.split('(', 1)[0] in self.INVALID_NAMES :
					self.restore_buffer = buffer
					return self.vars_force_finish(found_line, localvars, "x0A - detected bad brace clasp")
			
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
					return self.vars_force_finish(found_line, localvars, "x0B - detected a block-end brace")
				
			#print("E:: varName[%s] buff[%s] c[%s] - inString %d inBrackets %d inBraces %d inParens %d skipValue %d skipSpaces %d parseName %d multiLines %d" % (varName, buffer, c, inString, inBrackets, inBraces, inParens, skipValue, skipSpaces, parseName, multiLines ))
			
		#}
		
		debug.performance.pause("var")

		return localvars
	#}
	
	def vars_force_finish(self, found_line, localvars, code=""):
		self.mark_error(found_line)
		self.error("parse_vars", "invalid sintax - code: " + code)
		
		debug.performance.pause("var")
		
		return localvars
	
	def parse_enum(self, buffer):
	#{
		debug.performance.start("enum")
		
		if len(buffer) != 4 and buffer[4] != '{' and buffer[4] != ' ' :
			return
	
		if len(buffer) > 4 and buffer[4] == ' ' :
			s = buffer[5:].split('(')
			s = s[0].split(':')
			self.add_enumtag(s[0])
			if len(s) > 1 :
				s = s[1].strip("{ ")
				self.add_enum(s, 0)
			
		content = ""
		enum = ""
		ignore = True
		enums = 0
		
		doct1 = self.comment_doct1
		doct2 = [ ]
		
		self.comment_doct1 = ""
		
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
				content = "%s\n%s" % (content, buffer)
				buffer = self.read_clean_line()
				if len(buffer) > 1 :
					doct2 += [ self.comment_doct2 if self.comment_doct2 else self.comment_doct1  ]
			else :
				content = "%s\n%s" % (content, buffer[0:pos])
				self.restore_buffer = buffer[pos+1:].strip("; ")
				break
		#}

		pos = content.find('{')
		line = content[0:pos].count('\n')
		content = content[pos + 1:]
		
		# Cut head comment
		pos = doct1.find("\n", 64)
		if pos != -1 : 
			doct1 = doct1[:pos] + "..."	
			
		self.comment_doct1 = doct1
		
		for c in content :
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
				self.comment_doct2 = doct2[enums] if enums < len(doct2) else ""
				enums += 1
				
				self.add_enum(enum, line)
				
				enum = ""
					
				ignore = False
				continue

			if not ignore :
				enum += c
		#}

		self.comment_doct2 = doct2[enums] if enums < len(doct2) else ""
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

			buffer = self.read_clean_line()
		#}

		if full_func_str :
			self.parse_function_params(buffer, full_func_str, type)
			
		debug.performance.pause("func")
	#}
	
	def parse_function_params(self, buffer, func, functype):
	#{
		if functype == globalvar.FUNC_TYPES.function :
			remaining = func
		else :
			split = func.split(' ', 1)
			remaining = split[1]
		
		split = remaining.split('(', 1)
		if len(split) < 2 :
			self.error("parse_function_params", "return1 [%s]" % split)
			return
			
		remaining = split[1]
		return_tag = ''
		return_array = ''
		funcname_and_return = split[0].strip()
		split_funcname_and_return = funcname_and_return.split(':')
		if len(split_funcname_and_return) > 1 :
			funcname = split_funcname_and_return[1].strip()
			return_tag = split_funcname_and_return[0].strip()
		else :
			funcname = split_funcname_and_return[0].strip()
		
		if funcname[0] == '[' :
			bracket_end = funcname.find(']') + 1
			return_array = funcname[0:bracket_end]
			funcname = funcname[bracket_end:].strip()
		
		# Fix float.inc
		if funcname.startswith("operator") :
			self.skip_function_block(buffer)
			return
			
		if not self.valid_name(funcname) :
			self.error("parse_function_params", "invalid name: [%s]  -  buffer: [%s]" % (funcname, buffer))
			return
	
		if functype == -1 : # Deprecated !
			self.skip_function_block(buffer)
			return 
	
		param_localvar 	= list()
		param_tags 		= set()
		autocomplete 	= funcname + '('
	
		full_parameters = remaining.strip()[:-1]

		if full_parameters :
		#{	
			params = remaining[:-1].split(',')
				
			num = 1
			skip = False
			inTags = False
			
			valid_params = [ ]

			for param in params :
			#{
				param = param.strip("& \t")
				
				if inTags :
					pos = param.find('}')
					if pos != -1 :
						inTags = False
						param_tags.add(param[0:pos])
						param = param[pos+2:]
					else :
						param_tags.add(param)
						continue
				elif param.startswith('{') :
					inTags = True
					param_tags.add(param[1:])
					continue

				result = self.Regex_VALID_PARAM.match(param)
				if not result :
					continue
					
				valid_param = result.group(3)
				if result.group(4) :
					param_localvar += [ valid_param + "[]" ]
					valid_param += result.group(4)
				else :
					param_localvar += [ valid_param ]
				
				tagname = result.group(2)
				if tagname :
					tagname = tagname.strip(" }:")
					if self.valid_name(tagname) :
						param_tags.add(tagname)
						valid_param = tagname + ":" + valid_param
						
				if cfg.ac_add_parameters and not skip:
	
					if cfg.ac_add_parameters == 1 and "=" in param :
						skip = True
					else :
						if num > 1 :
							autocomplete += ', '
						autocomplete += '${%d:%s}' % (num, valid_param)
						num += 1
			#}
		#}
		autocomplete += ')'
			
		# Find local vars
		endline = startline = self.start_position

		localvars = set()
			
		if functype <= globalvar.FUNC_TYPES.stock :
			localvars.update(param_localvar)
			localvars.update(self.skip_function_block(buffer))
			endline = self.line_position
				
		self.add_autocomplete(funcname, autocomplete, globalvar.FUNC_TYPES[functype])
		self.info("parse_function_params", "add -> [%s]" % func)

		objFuncData = FuncDataStruct(functype, funcname, full_parameters, return_tag, return_array, self.node.file_path, startline - self.offset_line, endline - self.offset_line, localvars, param_localvar)
		
		if return_tag :
			self.add_tag(return_tag, objFuncData)
			
		for tagname in param_tags :
			self.add_tag(tagname, objFuncData)

		self.data.funclist.add(objFuncData)
	#}
#}

