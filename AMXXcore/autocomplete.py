import os
import re
import sublime, sublime_plugin

from AMXXcore.core import cfg


class ac:

	def init():
	
		# Re-generate on settings change
		ac.cache_emit			= ac.generate_emit_list()
		ac.cache_preprocessor 	= ac.generate_preprocessors_list()
		ac.cache_snippets 		= ac.generate_snippets_list()

	####################################################

		
	####################################################
	# Generate const list:
	####################################################
	def generate_preprocessors_list():
	
		list = [ ]
		
		def add(value):
			if value.endswith(" ") : # Fix bug
				list.append(( "#" + value + "\t preprocessor", value ))
			else :
				list.append(( "#" + value + "\t preprocessor", "#" + value )) 
			
			
		list.append(( "#include\t preprocessor", 		"#include <${1}>" ))
		list.append(( "#tryinclude\t preprocessor", 	"#tryinclude <${1}>" ))
		
		add("define ")
		add("if ")
		add("elseif ")
		add("else")
		add("endif")
		add("endinput")
		add("undef ")
		add("endscript")
		add("error")
		add("file ")
		add("line ")
		add("emit ")
		add("assert ")
		
		add("pragma amxlimit ")
		add("pragma codepage ")
		add("pragma compress ")
		add("pragma ctrlchar ")
		add("pragma dynamic ")
		add("pragma library ")
		add("pragma reqlib ")
		add("pragma reqclass ")
		add("pragma loadlib ")
		add("pragma explib ")
		add("pragma expclass ")
		add("pragma defclasslib ")
		add("pragma pack ")
		add("pragma rational ")
		add("pragma semicolon ")
		add("pragma tabsize ")
		add("pragma align")
		add("pragma unused ")
		
		return ac.sorted_nicely(list)
		
	def generate_emit_list():
	
		list = [ ]
			
		def add(opcode, valuetype, info):
		
			if cfg.ac_emit_info :
				if valuetype :
					list.append(( opcode + "\t emit opcode", opcode + " ${1:<" + valuetype + ">}\t\t// " + info))
				else:
					list.append(( opcode + "\t emit opcode", opcode + "\t\t\t// " + info))
					
			else :
				if valuetype :
					list.append(( opcode + "\t emit opcode", opcode + " ${1:<" + valuetype + ">}"))
				else:
					list.append(( opcode + "\t emit opcode", opcode))
		
		
		add("LOAD.pri", 		"address", 		"PRI   =  [address]")
		add("LOAD.alt", 		"address", 		"ALT   =  [address]")
		add("LOAD.S.pri", 		"offset", 		"PRI   =  [FRM + offset]")
		add("LOAD.S.alt", 		"offset", 		"ALT   =  [FRM + offset]")
		add("LREF.pri", 		"address", 		"PRI   =  [ [address] ]")
		add("LREF.alt", 		"address", 		"ALT   =  [ [address] ]")
		add("LREF.S.pri", 		"offset", 		"PRI   =  [ [FRM + offset] ]")
		add("LREF.S.alt", 		"offset", 		"ALT   =  [ [FRM + offset] ]")
		add("LOAD.I", 			"", 			"PRI   =  [PRI] (full cell)")
		add("LODB.I", 			"number", 		"PRI   =  'number' bytes from [PRI] (read 1/2/4 bytes)")
		add("CONST.pri", 		"value", 		"PRI   =  value")
		add("CONST.alt", 		"value", 		"ALT   =  value")
		add("ADDR.pri", 		"offset", 		"PRI   =  FRM + offset")
		add("ADDR.alt", 		"offset", 		"ALT   =  FRM + offset")
		add("STOR.pri", 		"address", 		"[address]   =  PRI")
		add("STOR.alt", 		"address", 		"[address]   =  ALT")
		add("STOR.S.pri", 		"offset", 		"[FRM + offset]   =  PRI")
		add("STOR.S.alt", 		"offset", 		"[FRM + offset]   =  ALT")
		add("SREF.pri", 		"address", 		"[ [address] ]   =  PRI")
		add("SREF.alt", 		"address", 		"[ [address] ]   =  ALT")
		add("SREF.S.pri", 		"offset", 		"[ [FRM + offset] ]   =  PRI")
		add("SREF.S.alt", 		"offset", 		"[ [FRM + offset] ]   =  ALT")
		add("STOR.I", 			"", 			"[ALT]   =  PRI (full cell)")
		add("STRB.I", 			"number", 		"'number' bytes at [ALT]   =  PRI (write 1/2/4 bytes)")
		add("LIDX", 			"", 			"PRI   =  [ ALT + (PRI * cell size) ]")
		add("LIDX.B", 			"shift", 		"PRI   =  [ ALT + (PRI << shift) ]")
		add("IDXADDR", 			"", 			"PRI   =  ALT + (PRI * cell size) (calculate indexed address)")
		add("IDXADDR.B", 		"shift", 		"PRI   =  ALT + (PRI << shift) (calculate indexed address)")
		add("ALIGN.pri", 		"number", 		"Little Endian: PRI ^   =  cell size")
		add("ALIGN.alt", 		"number", 		"Little Endian: ALT ^   =  cell size")
		add("LCTRL", 			"index", 		"PRI is set to the current value of any of the special registers. The index parameter must be: 0  = COD, 1  = DAT, 2  = HEA,3  = STP, 4  = STK, 5  = FRM, 6  = CIP (of the next instruction)")
		add("SCTRL", 			"index", 		"set the indexed special registers to the value in PRI. The index parameter must be: 2  = HEA, 4  = STK, 5  = FRM, 6  = CIP")
		add("MOVE.pri", 		"", 			"PRI  = ALT")
		add("MOVE.alt", 		"", 			"ALT  = PRI")
		add("XCHG", 			"", 			"Exchange PRI and ALT")
		add("PUSH.pri", 		"", 			"[STK]   =  PRI, STK   =  STK")
		add("PUSH.alt", 		"", 			"[STK]   =  ALT, STK   =  STK")
		add("PUSH.R", 			"value", 		"Repeat value: [STK]   =  PRI, STK   =  STK")
		add("PUSH.C", 			"value", 		"[STK]   =  value, STK   =  STK")
		add("PUSH", 			"address", 		"[STK]   =  [address], STK   =  STK")
		add("PUSH.S", 			"offset", 		"[STK]   =  [FRM + offset], STK   =  STK")
		add("POP.pri", 			"", 			"STK   =  STK + cell size, PRI   =  [STK]")
		add("POP.alt", 			"", 			"STK   =  STK + cell size, ALT   =  [STK]")
		add("STACK", 			"value", 		"ALT   =  STK, STK   =  STK + value")
		add("HEAP", 			"value", 		"ALT   =  HEA, HEA   =  HEA + value")
		add("PROC", 			"", 			"[STK]   =  FRM, STK   =  STK")
		add("RET", 				"", 			"STK   =  STK + cell size, FRM   =  [STK], STK   =  STK + cell size, CIP   =  [STK], The RET instruction cleans up the stack frame and returns from the function to the instruction after the call.")
		add("RETN", 			"", 			"STK   =  STK + cell size, FRM   =  [STK], STK   =  STK + cell size, CIP   =  [STK], STK   =  STK + [STK] The RETN instruction removes a specifed number of bytes from the stack. The value to adjust STK with must be pushed prior to the call.")
		add("CALL", 			"address", 		"[STK]   =  CIP + 5, STK   =  STK The CALL instruction jumps to an address after storing the address of the next sequential instruction on the stack.")
		add("CALL.pri", 		"", 			"[STK]   =  CIP + 1, STK   =  STK")
		add("JUMP", 			"address", 		"CIP   =  address (jump to the address)")
		add("JREL", 			"offset", 		"CIP   =  CIP + offset (jump offset bytes from currentposition)")
		add("JZER", 			"address", 		"if PRI   =   =  0 then CIP   =  [CIP + 1]")
		add("JNZ", 				"address", 		"if PRI !  =  0 then CIP   =  [CIP + 1]")
		add("JEQ", 				"address", 		"if PRI   =   =  ALT then CIP   =  [CIP + 1]")
		add("JNEQ", 			"address", 		"if PRI !  =  ALT then CIP   =  [CIP + 1]")
		add("JLESS", 			"address", 		"if PRI < ALT then CIP   =  [CIP + 1] (unsigned)")
		add("JLEQ", 			"address", 		"if PRI <   =  ALT then CIP   =  [CIP + 1] (unsigned)")
		add("JGRTR", 			"address", 		"if PRI > ALT then CIP   =  [CIP + 1] (unsigned)")
		add("JGEQ", 			"address", 		"if PRI >   =  ALT then CIP   =  [CIP + 1] (unsigned)")
		add("JSLESS", 			"address", 		"if PRI < ALT then CIP   =  [CIP + 1] (signed)")
		add("JSLEQ", 			"address", 		"if PRI <   =  ALT then CIP   =  [CIP + 1] (signed)")
		add("JSGRTR", 			"address", 		"if PRI > ALT then CIP   =  [CIP + 1] (signed)")
		add("JSGEQ", 			"address", 		"if PRI >   =  ALT then CIP   =  [CIP + 1] (signed)")
		add("SHL", 				"", 			"PRI   =  PRI << ALT")
		add("SHR", 				"", 			"PRI   =  PRI >> ALT (without sign extension)")
		add("SSHR", 			"", 			"PRI   =  PRI >> ALT with sign extension")
		add("SHL.C.pri", 		"value", 		"PRI   =  PRI << value")
		add("SHL.C.alt", 		"value", 		"ALT   =  ALT << value")
		add("SHR.C.pri", 		"value", 		"PRI   =  PRI >> value (without sign extension)")
		add("SHR.C.alt", 		"value", 		"ALT   =  ALT >> value (without sign extension)")
		add("SMUL", 			"", 			"PRI   =  PRI * ALT (signed multiply)")
		add("SDIV", 			"", 			"PRI   =  PRI / ALT (signed divide), ALT   =  PRI mod ALT")
		add("SDIV.alt", 		"", 			"PRI   =  ALT / PRI (signed divide), ALT   =  ALT mod PRI")
		add("UMUL", 			"", 			"PRI   =  PRI * ALT (unsigned multiply)")
		add("UDIV", 			"", 			"PRI   =  PRI / ALT (unsigned divide), ALT   =  PRI mod ALT")
		add("UDIV.alt", 		"", 			"PRI   =  ALT / PRI (unsigned divide), ALT   =  ALT mod PRI")
		add("ADD", 				"", 			"PRI   =  PRI + ALT")
		add("SUB", 				"", 			"PRI   =  PRI - ALT")
		add("SUB.alt", 			"", 			"PRI   =  ALT - PRI")
		add("AND", 				"", 			"PRI   =  PRI & ALT")
		add("OR", 				"", 			"PRI   =  PRI | ALT")
		add("XOR", 				"", 			"PRI   =  PRI ^ ALT")
		add("NOT", 				"", 			"PRI   =  !PRI")
		add("NEG", 				"", 			"PRI   =  PRI   =  --PRI")
		add("INVERT", 			"", 			"PRI   =  ~ PRI")
		add("ADD.C", 			"value", 		"PRI   =  PRI + value")
		add("SMUL.C", 			"value", 		"PRI   =  PRI * value")
		add("ZERO.pri", 		"", 			"PRI   =  0")
		add("ZERO.alt", 		"", 			"ALT   =  0")
		add("ZERO", 			"address", 		"[address]   =  0")
		add("ZERO.S", 			"offset", 		"[FRM + offset]   =  0")
		add("SIGN.pri", 		"", 			"sign extent the byte in PRI to a cell")
		add("SIGN.alt", 		"", 			"sign extent the byte in ALT to a cell")
		add("EQ", 				"", 			"PRI   =  PRI   =   =  ALT ? 1 : 0")
		add("NEQ", 				"", 			"PRI   =  PRI !  =  ALT ? 1 : 0")
		add("LESS", 			"", 			"PRI   =  PRI < ALT ? 1 : 0 (unsigned)")
		add("LEQ", 				"", 			"PRI   =  PRI <   =  ALT ? 1 : 0 (unsigned)")
		add("GRTR", 			"", 			"PRI   =  PRI > ALT ? 1 : 0 (unsigned)")
		add("GEQ", 				"", 			"PRI   =  PRI >   =  ALT ? 1 : 0 (unsigned)")
		add("SLESS", 			"", 			"PRI   =  PRI < ALT ? 1 : 0 (signed)")
		add("SLEQ", 			"", 			"PRI   =  PRI <   =  ALT ? 1 : 0 (signed)")
		add("SGRTR", 			"", 			"PRI   =  PRI > ALT ? 1 : 0 (signed)")
		add("SGEQ", 			"", 			"PRI   =  PRI >   =  ALT ? 1 : 0 (signed)")
		add("EQ.C.pri", 		"value", 		"PRI   =  PRI   =   =  value ? 1 : 0")
		add("EQ.C.alt", 		"value", 		"PRI   =  ALT   =   =  value ? 1 : 0")
		add("INC.pri", 			"", 			"PRI   =  PRI + 1")
		add("INC.alt", 			"", 			"ALT   =  ALT + 1")
		add("INC", 				"address", 		"[address]   =  [address] + 1")
		add("INC.S", 			"offset", 		"[FRM + offset]   =  [FRM + offset] + 1")
		add("INC.I", 			"", 			"[PRI]   =  [PRI] + 1")
		add("DEC.pri", 			"", 			"PRI   =  PRI - 1")
		add("DEC.alt", 			"", 			"PRI   =  PRI - 1")
		add("DEC", 				"address", 		"[address]   =  [address]  - 1")
		add("DEC.S", 			"offset", 		"[FRM + offset]   =  [FRM + offset]  - 1")
		add("DEC.I", 			"", 			"[PRI]   =  [PRI] - 1")
		add("MOVS", 			"number", 		"Copy memory from [PRI] to [ALT]. The parameter specifes the number of bytes. The blocks should not overlap.")
		add("CMPS", 			"number", 		"Compare memory blocks at [PRI] and [ALT]. The parameter specifes the number of bytes. The blocks should not overlap.")
		add("FILL", 			"number", 		"Fill memory at [ALT] with value in [PRI]. The parameter specifes the number of bytes, which must be a multiple of the cell size.")
		add("HALT", 			"", 			"Abort execution (exit value in PRI), parameters other than 0 have a special meaning.")
		add("BOUNDS",			"value", 		"Abort execution if PRI > value or if PRI < 0")
		add("SYSREQ.pri", 		"", 			"call system service, service number in PRI")
		add("SYSREQ.C", 		"value", 		"call system service")
		add("FILE", 			"", 			"size ord name..., source file information pair: name and ordinal (see below)")
		add("LINE", 			"", 			"line ord, source line number and file ordinal (see below)")
		add("SYMBOL",			"", 			"sze off flg name..., symbol information (see below)")
		add("SRANGE", 			"", 			"lvl size, symbol range and dimensions (see below)")
		add("JUMP.pri", 		"", 			"CIP   =  PRI (indirect jump)")
		add("SWITCH", 			"address", 		"Compare PRI to the values in the case table (whose address is passed) and jump to the associated address.")
		add("CASETBL", 			"", 			"casetbl num default num*[case jump]")
		add("SWAP.pri", 		"", 			"[STK]   =  PRI and PRI   =  [STK]")
		add("SWAP.alt", 		"", 			"[STK]   =  ALT and ALT   =  [STK]")
		add("PUSHADDR", 		"offset", 		"[STK]   =  FRM + offset, STK   =  STK ")
		add("NOP", 				"", 			"no-operation, for code alignment")
		add("SYSREQ.D", 		"address", 		"call system service directly (by address)")
		add("SYMTAG", 			"value", 		"symbol tag")
		add("BREAK", 			"", 			"invokes  optional debugger")

		return list
		
	def generate_snippets_list():
	
		list = [ ]
				
		def add(name, insert):
			list.append(( name + "\t snippet", insert ))
				

		add("if-else()", 		"if(${1})\n{\n\t${2}\n}\nelse {\n\t${3}\n}")
		add("for()", 			"for(${1}; ${2}; ${3})\n{\n\t${4}\n}")
		add("for-i()", 			"for(new i=${1:0}; i ${2:<= }; i++)\n{\n\t${3}\n}")
		add("for-players()", 	"for(new ${1:id}=1; ${2:id} <= ${3:g_maxplayers}; ${4:id}++)\n{\n\t${5}\n}")
		add("while()", 			"while(${1})\n{\n\t${2}\n}")
		add("do-while()", 		"do {\n\t${2}\n} while(${1})")
		add("switch()", 		"switch(${1})\n{\n\t${2}\n}")
		add("switch-case()", 	"switch(${1})\n{\n\tcase ${2:1}:\n\t{\n\t\t${3}\n\t}\n\tcase ${4:2}:\n\t{\n\t\t${5}\n\t}\n\tdefault:\n\t{\n\t\t${6}\n\t}\n}")
		add("case :", 			"case ${1:value}:\n{\n\t${2}\n}")
		add("enum _:", 			"enum _:${1:MyEnumSizeof}\n{\n\t${2:item1}=0,\n\t${3:item2}\n}")
		add("new-const", 		"new const ")

		return ac.sorted_nicely(list)
		
		
	####################################################
	# Generate dynamic list:
	####################################################
	def generate_keywords_list(mode):
	
		list = [ ]
				
		def add(value, allowparens=False):
			if mode == 2 and allowparens :
				list.append(( value + "\t keyword", value + "(${1})" ))
			else :
				list.append(( value + "\t keyword", value ))
				
		add("if", True)
		add("else")
		add("for", True)
		add("while", True)
		add("switch", True)
		add("case")
		add("return")
		add("break")
		add("default")
		add("continue")
		add("forward ")
		add("native ")
		add("public ")
		add("stock ")
		add("sizeof")
		add("tagof")
		add("true")
		add("false")
		add("new ")
		add("const ")
		add("enum")
		
		return list
		
	def generate_includes_list(includes_list, text):
	
		list = [ ]
		op = "<"
		cl = ">"
		
		if text.find("<") != -1 :
			op = ""
		if text.find(">") != -1 :
			cl = ""
			
		for inc in includes_list :
			list.append(( inc + "\t inc", op + inc + cl ))
			
		return list
		
	def generate_local_vars_list(node, line):
	
		list = [ ]
		
		for func in node.funclist :
			if func.start_line <= line and line <= func.end_line :
				for var in func.local_vars :
					list.append(( var + "\t local var", var ))

				return list

		return list
		
	def generate_autocomplete_list(node):
	
		what = node.file_name+" - "
		
		def remove_filename(value, this_node):
			#if node.file_name == this_node.file_name :
			#	return (value[0].replace(what, ""), value[1])

			return value
		
		return node.generate_list("autocomplete", list, remove_filename)

		
	def block_on_varname(text):
	#{
	
		num_bracket		= 0
		num_paren		= 0
		num_brace 		= 0
		inBrackets 		= False
		inParens		= False
		inBraces 		= False
		inString 		= False
		
		blockState = True
		
		for c in text :
		#{
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
					num_paren += 1
					inParens = True
				elif c == ')' :
					num_paren -= 1
					if num_paren == 0 :
						inParens = False

			if inString or inBrackets or inBraces or inParens:
				blockState = False
				continue

			if c == ';' :
				return False
			
			if c == ',' :
				blockState = True
			elif c == '=' :
				blockState = False
		#}
		
		return blockState
	#}
	
	####################################################
	
	"""
	Another code
	def sorted_nicely(list):
		def alphanum_key(key):
			r = []

			for c in re.split('([0-9]+)', key[0]) :
				if c.isdigit() :
					r += [ int(c) ]
				else :
					r += [ str.lower(c) ]
					
			return r
		
		return sorted(list, key=alphanum_key)
	"""

	def sorted_nicely(l):
		""" Sort the given iterable in the way that humans expect."""
		convert = lambda text: int(text) if text.isdigit() else text
		alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key[0]) ]
		return sorted(l, key = alphanum_key)
	
########################################################



