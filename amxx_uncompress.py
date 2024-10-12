import struct
import zlib
import os
import string
import time


class AMX_HEADER:
	def __init__(self):
		self.size = 0
		self.magic = 0
		self.file_version = 0
		self.amx_version = 0
		self.flags = 0
		self.defsize = 0
		self.cod = 0
		self.dat = 0
		self.hea = 0
		self.stp = 0
		self.cip = 0
		self.publics = 0
		self.natives = 0
		self.libraries = 0
		self.pubvars = 0
		self.tags = 0
		self.nametable = 0

class AMX_DBG_HDR:
	def __init__(self, size=None, magic=None, file_version=None, amx_version=None, flags=None, files=None, lines=None, symbols=None, tags=None, automatons=None, states=None):
		self.size = size
		self.magic = magic
		self.file_version = file_version
		self.amx_version = amx_version
		self.flags = flags
		self.files = files
		self.lines = lines
		self.symbols = symbols
		self.tags = tags
		self.automatons = automatons
		self.states = states


class Plugin:
	def __init__(self):
		self.magic = 0
		self.version = 0
		self.sections = 0
		self.cellsize = 0
		self.disksize = 0
		self.imagesize = 0
		self.memsize = 0
		self.offs = 0
		self.data = None
		self.amx_header = None
		self.dbg = None
		
		self.isCOMPACT = None


plugin = Plugin()

MAX_PLUGIN_STRING = 250
AMX_COMPACTMARGIN = 64

g_filename_amxx = None
g_filename_raw = None
g_filename_dump = None
g_filename_memory = None


def read_header(fp):
	global plugin
	plugin = Plugin()
	
	plugin.magic = struct.unpack('I', fp.read(4))[0]
	if plugin.magic != 0x414d5858:
		return False
	plugin.version = struct.unpack('H', fp.read(2))[0]
	plugin.sections = struct.unpack('B', fp.read(1))[0]
	plugin.cellsize = struct.unpack('B', fp.read(1))[0]
	plugin.disksize = struct.unpack('I', fp.read(4))[0]
	plugin.imagesize = struct.unpack('I', fp.read(4))[0]
	plugin.memsize = struct.unpack('I', fp.read(4))[0]
	plugin.offs = struct.unpack('I', fp.read(4))[0]

	return True

def write_header(fp):
	global plugin
	
	fp.write(struct.pack('I', plugin.magic))
	fp.write(struct.pack('H', plugin.version))
	fp.write(struct.pack('B', plugin.sections))
	fp.write(struct.pack('B', plugin.cellsize))
	fp.write(struct.pack('I', plugin.disksize))
	fp.write(struct.pack('I', plugin.imagesize))
	fp.write(struct.pack('I', plugin.memsize))
	fp.write(struct.pack('I', plugin.offs))

def load_uncompress(fp):
	global plugin
    
	uncompressed_size = plugin.imagesize
	uncompressed_data = fp.read(uncompressed_size)
    
	if len(uncompressed_data) != uncompressed_size:
		print(f"ERROR: Read size mismatch. Expected {uncompressed_size}, got {len(uncompressed_data)}")
		return False
    
	plugin.data = bytearray(uncompressed_data)
	
	return True

def amxx_uncompress(fp):
	global plugin
	
	def adjust_bytes_size(byte_obj, desired_size):
		return byte_obj.ljust(desired_size, b'\x00')[:desired_size]
		
	compressed_size = plugin.disksize
	uncompressed_size = plugin.imagesize
	
	fp.seek(plugin.offs)
	compressed_data = fp.read(compressed_size)
	
	try:
		uncompressed_data = zlib.decompress(compressed_data)
	except zlib.error as e:
		print(f"ERROR: Decompression failed - {str(e)}")
		return False
	
	if len(uncompressed_data) != uncompressed_size :
		print(f"ERROR: Uncompressed size mismatch. Expected {uncompressed_size}, got {len(uncompressed_data)}")
		return False

	finalsize = plugin.memsize
	if plugin.imagesize > plugin.memsize :
		finalsize = plugin.imagesize
		
	plugin.sections = 1
	plugin.offs = 24 # Why 24 ?, amxxpc.cpp -> search kEntrySize
	plugin.data = bytearray(adjust_bytes_size(uncompressed_data, finalsize))

	return True

def amxx_compress():
    global plugin
    
    try:
        compressed = zlib.compress(plugin.data)
    except zlib.error as e:
        print(f"ERROR: Compression failed - {str(e)}")
        return False
    
    plugin.disksize = len(compressed)
    
    try:
        with open(g_filename_amxx, "wb") as file:
            write_header(file)
            file.write(compressed)
    except IOError as e:
        print(f"ERROR: Failed to write file - {str(e)}")
        return False
    
    return True

def get_amx_header():
	global plugin
	
	if not plugin.data:
		return False

	plugin.amx_header = AMX_HEADER()
	
	header_data = plugin.data[:struct.calcsize('I'*12 + 'H'*3 + 'BB')]
	
	(plugin.amx_header.size, plugin.amx_header.magic, 
	 plugin.amx_header.file_version, plugin.amx_header.amx_version, 
	 plugin.amx_header.flags, plugin.amx_header.defsize, 
	 plugin.amx_header.cod, plugin.amx_header.dat, 
	 plugin.amx_header.hea, plugin.amx_header.stp, 
	 plugin.amx_header.cip, plugin.amx_header.publics, 
	 plugin.amx_header.natives, plugin.amx_header.libraries, 
	 plugin.amx_header.pubvars, plugin.amx_header.tags, 
	 plugin.amx_header.nametable) = struct.unpack('IHBBHHIIIIIIIIIII', header_data)
	
	if plugin.amx_header.magic != 0xf1e0:
		return False
	
	if plugin.amx_header.flags & 0x02:  # AMX_FLAG_DEBUG

		dbg_hdr_size = plugin.amx_header.size + struct.calcsize('IHBBHHHHHHH')
		dbg_data = plugin.data[plugin.amx_header.size:dbg_hdr_size]
		
		dbg = AMX_DBG_HDR()
		(dbg.size, dbg.magic, dbg.file_version, dbg.amx_version,
		 dbg.flags, dbg.files, dbg.lines, dbg.symbols,
		 dbg.tags, dbg.automatons, dbg.states) = struct.unpack('IHBBHHHHHHH', dbg_data)
		
		plugin.dbg = dbg
		
		if dbg.magic != 0xf1ef:
			return False
	
	
	return True

def update_amx_header():
	global plugin
	
	header_size = struct.calcsize('IHBBHHIIIIIIIIIII')

	header_data = struct.pack(
		'IHBBHHIIIIIIIIIII',
		plugin.amx_header.size,
		plugin.amx_header.magic,
		plugin.amx_header.file_version,
		plugin.amx_header.amx_version,
		plugin.amx_header.flags,
		plugin.amx_header.defsize,
		plugin.amx_header.cod,
		plugin.amx_header.dat,
		plugin.amx_header.hea,
		plugin.amx_header.stp,
		plugin.amx_header.cip,
		plugin.amx_header.publics,
		plugin.amx_header.natives,
		plugin.amx_header.libraries,
		plugin.amx_header.pubvars,
		plugin.amx_header.tags,
		plugin.amx_header.nametable
	)

	plugin.data = header_data + plugin.data[header_size:]
	
def expand(code, codesize, memsize):
	spare = [(None, None)] * AMX_COMPACTMARGIN
	sh, st, sc = 0, 0, 0
	shift = 0
	c = 0
	
	assert memsize % 4 == 0  # sizeof(cell) == 4

	while codesize > 0:
		c = 0
		shift = 0
		
		codesize -= 1
		c |= ((code[codesize] & 0x7f) << shift) & 0xFFFFFFFF
		shift += 7
			
		while codesize > 0 and (code[codesize - 1] & 0x80) != 0:
		
			assert shift < 32  # no input byte should be shifted out completely
			
			codesize -= 1
			c |= ((code[codesize] & 0x7f) << shift) & 0xFFFFFFFF
			shift += 7

		# sign expand
		if code[codesize] & 0x40 != 0:
			while shift < 32:
				c |= (0xff << shift) & 0xFFFFFFFF
				shift += 8
				
		# store
		while sc and spare[sh][0] > codesize:
			memloc, value = spare[sh]
			struct.pack_into("I", code, memloc, value)
				
			sh = (sh + 1) % AMX_COMPACTMARGIN
			sc -= 1

		memsize -= 4
		assert memsize >= 0
		if memsize > codesize or (memsize == codesize and memsize == 0):
			struct.pack_into("I", code, memsize, c)
		else:
			assert sc < AMX_COMPACTMARGIN
			spare[st] = (memsize, c)
			st = (st + 1) % AMX_COMPACTMARGIN
			sc += 1
		
	assert memsize == 0

	return code


VALID_CHARACTERS = set(string.ascii_letters + string.digits + string.whitespace + string.punctuation)
def valid_char(value, prev_value=None):

	if not (0 <= value <= 255) :
		return False
	
	char = chr(value)
	if char in VALID_CHARACTERS or value in {1, 2, 3, 4} :
		return True
	
	if prev_value is None :
		if 194 <= value <= 244 :
			return True
	elif 194 <= prev_value <= 244 :
		return 128 <= value <= 191
	
	return False

def is_string(addr):
	dat = struct.unpack('I', plugin.data[addr:addr+4])[0]
	
	if valid_char(dat) :
		next_dat = struct.unpack('I', plugin.data[addr+4:addr+8])[0]

		if valid_char(next_dat, prev_value=dat) or next_dat == 0 :
			return True

	return False


def string_to_raw(string):
	buffer = []
	ctrl_char = False
	i = 0
	while i < len(string):
		if string[i] == '^':
			if not ctrl_char:
				ctrl_char = True
			else:
				buffer.append('^')
				ctrl_char = False
		elif ctrl_char:
			ctrl_char = False
			if string[i] == 't':
				buffer.append('\t')
			elif string[i] == 'n':
				buffer.append('\n')
			elif string[i] == '"':
				buffer.append('"')
			elif string[i] == 'x':
				hex_val = string[i+1:i+3]
				buffer.append(chr(int(hex_val, 16)))
				i += 2
			else:
				buffer.append(string[i])
		else:
			buffer.append(string[i])
		i += 1
	return ''.join(buffer)


def string_to_format(string):
	buffer = []
	for char in string:
		if char == '\n':
			buffer.extend(['^', 'n'])
		elif char == '\t':
			buffer.extend(['^', 't'])
		elif char == '"':
			buffer.extend(['^', '"'])
		elif char == '^':
			buffer.extend(['^', '^'])
		elif 0 < ord(char) < 32:
			buffer.extend(['^', 'x', f'{ord(char):02x}'])
		else:
			buffer.append(char)
	return ''.join(buffer)

def get_amx_string(buff, offset):

	output = bytearray()
	writed = 0
	while(True):
		cell = struct.unpack('I', buff[offset+writed : offset+writed+4])[0]
		if cell == 0:
			break
		writed += 4
		output.append(cell & 0xFF)

	return ( output.decode('utf-8', 'replace'), writed )


def set_amx_string(buff, offset, string, forced):

	data = string.encode('utf-8', 'replace')
	writed = 0

	while (forced or buff[offset] != 0) and writed < len(data):
		buff[offset] = data[writed]
		offset += 4
		writed += 1

	buff[offset] = 0

	return writed * 4


def set_amx_memory(buff, offset, hex_str):

	cell_written = 0
	hex_list = hex_str.split()

	for hex_value in hex_list:
		value = int(hex_value, 16)
		
		buff[offset] = value & 0xFF
		buff[offset + 1] = (value >> 8) & 0xFF
		buff[offset + 2] = (value >> 16) & 0xFF
		buff[offset + 3] = (value >> 24) & 0xFF
		
		offset += 4
		cell_written += 1

	return cell_written


def generate_memory_file():
	global plugin
	
	with open(g_filename_memory, "w", encoding="utf-8", errors="replace") as fp:
	
		fp.write("; Guide: https://forums.alliedmods.net/showthread.php?t=250748\n\n")
		
		base_addr = plugin.amx_header.dat
		end_addr = plugin.amx_header.hea
		current_addr = base_addr
		count = 0

		while current_addr < end_addr:
			if is_string(current_addr):

				string_buff, string_size = get_amx_string(plugin.data, current_addr)
				formatted_string = string_to_format(string_buff)

				write_buff = f";data:0x{current_addr-base_addr:08X}=\"{formatted_string}\"\n"
				fp.write(write_buff)

				current_addr += string_size
				count += 1
			else:
				current_addr += 4

	return count


def load_memory_file():
	global plugin
	
	try:
		with open(g_filename_memory, "r", encoding="utf-8", errors="replace") as fp :
		
			data_base_addr = plugin.amx_header.dat
			data_end_addr = data_base_addr + (plugin.amx_header.hea - plugin.amx_header.dat)

			code_base_addr = plugin.amx_header.cod
			code_end_addr = code_base_addr + (plugin.amx_header.dat - plugin.amx_header.cod)
			count = 0

			def print_bad(line):
				print(f"ERROR Memory File: Parse error, invalid format at line: [{line}]")
					
			for line in fp :
				line = line.strip()
				if not line or line[0] == ';' :
					continue
					
				if line.startswith("data:"):
					section = 1
				elif line.startswith("code:"):
					section = 2
				else:
					print_bad(line)
					continue

				memory_buff = line[7:15]
				offset_addr = int(memory_buff, 16)

				if line[16] not in ( '"', '[' ) :
					print_bad(line)
					continue

				memory_buff = line[17:]
				memory_len = len(memory_buff)

				if count < 15:
					time.sleep(0.1)

				if section == 1:  # DATA
					offset_addr += data_base_addr
					if offset_addr > data_end_addr:
						print(f"ERROR: Bad Addr: 0x{offset_addr - data_base_addr:08X}")
						continue

					if line[16] == '"':  # String
						forced = 0
						if memory_buff[-1] == 'f' :
							memory_len -= 1
							forced = 1

						if memory_buff[-1 - forced] != '"' :
							print_bad(line)
							continue

						new_string = string_to_raw(memory_buff[:-1 - forced])
						new_len = len(new_string)
						new_size = len(new_string.encode('utf-8', 'replace'))
						
						if ( offset_addr + new_size ) > len(plugin.data):
							print(f"ERROR: Address out of bounds: 0x{offset_addr:08X} + {new_size}")
							continue

						old_string, old_size = get_amx_string(plugin.data, offset_addr)
						old_len = len(old_string)
						
						new_size = set_amx_string(plugin.data, offset_addr, new_string, forced)

						f = " forced" if forced else ""
						print(f"Replace{f}: [{string_to_format(old_string)}] (len {old_len}, read {old_size} bytes) with [{string_to_format(new_string)}] (len {new_len}, write {new_size} bytes)")

					else:  # HEX
						if memory_buff[-1] != ']' :
							print_bad(line)
							continue

						hex_str = memory_buff[:-1]
						writed = set_amx_memory(plugin.data, offset_addr, hex_str)

						print(f"Write memory: DATA addr:[0x{offset_addr:08X}] - hex:[{hex_str}] - len:[{writed}] - size:[{writed*4} bytes]")

				else:  # CODE
					offset_addr += code_base_addr
					if offset_addr > code_end_addr :
						print(f"ERROR: Bad Addr: 0x{offset_addr - code_base_addr:08X}")
						continue

					if line[16] != '[' or memory_buff[-1] != ']' :
						print_bad(line)
						continue

					hex_str = memory_buff[:-1]
					writed = set_amx_memory(plugin.data, offset_addr, hex_str)

					print(f"Write memory: CODE addr:[0x{offset_addr:08X}] - hex:[{hex_str}] - len:[{writed}] - size:[{writed*4} bytes]")

				count += 1

	except FileNotFoundError:
		return 0

	return count

	
class AMX_FUNCSTUB:
	def __init__(self, address, name):
		self.address = address
		self.name = name
		
	def __repr__(self):
		return f'<{type(self).__name__}: name="{self.name}", address={self.address}>'

class Native(AMX_FUNCSTUB):
	pass

class Public(AMX_FUNCSTUB):
	pass
	
def generate_function_list(plugin, hdr):
	def read_uint32(offset):
		return int.from_bytes(plugin.data[offset:offset+4], byteorder='little')

	def read_string(offset):
		end = plugin.data.find(b'\0', offset)
		return plugin.data[offset:end].decode('ascii')

	def get_functions(start_offset, end_offset, func_class):
		functions = []
		num_entries = (end_offset - start_offset) // hdr.defsize
		for i in range(num_entries):
			entry_offset = start_offset + i * hdr.defsize
			address = read_uint32(entry_offset)
			
			if hdr.defsize == 8:  # Using name table
				name_offset = read_uint32(entry_offset + 4)
				name = read_string(name_offset)
			else:
				name = read_string(entry_offset + 4)
			
			functions.append(func_class(address, name))
		return functions

	natives = get_functions(hdr.natives, hdr.libraries, Native)
	publics = get_functions(hdr.publics, hdr.natives, Public)

	return ( natives, publics )

# Diccionario que mapea los opcodes a sus correspondientes nombres y operandos
opcodes = {
	0x00: ("NONE", False),
	0x01: ("LOAD.pri", True),
	0x02: ("LOAD.alt", True),
	0x03: ("LOAD.S.pri", True),
	0x04: ("LOAD.S.alt", True),
	0x05: ("LREF.pri", True),
	0x06: ("LREF.alt", True),
	0x07: ("LREF.S.pri", True),
	0x08: ("LREF.S.alt", True),
	0x09: ("LOAD.I", False),
	0x0A: ("LODB.I", True),
	0x0B: ("CONST.pri", True),
	0x0C: ("CONST.alt", True),
	0x0D: ("ADDR.pri", True),
	0x0E: ("ADDR.alt", True),
	0x0F: ("STOR.pri", True),
	0x10: ("STOR.alt", True),
	0x11: ("STOR.S.pri", True),
	0x12: ("STOR.S.alt", True),
	0x13: ("SREF.pri", True),
	0x14: ("SREF.alt", True),
	0x15: ("SREF.S.pri", True),
	0x16: ("SREF.S.alt", True),
	0x17: ("STOR.I", False),
	0x18: ("STRB.I", True),
	0x19: ("LIDX", False),
	0x1A: ("LIDX.B", True),
	0x1B: ("IDXADDR", False),
	0x1C: ("IDXADDR.B", True),
	0x1D: ("ALIGN.pri", True),
	0x1E: ("ALIGN.alt", True),
	0x1F: ("LCTRL", True),
	0x20: ("SCTRL", True),
	0x21: ("MOVE.pri", False),
	0x22: ("MOVE.alt", False),
	0x23: ("XCHG", False),
	0x24: ("PUSH.pri", False),
	0x25: ("PUSH.alt", False),
	0x26: ("PUSH.R", True),
	0x27: ("PUSH.C", True),
	0x28: ("PUSH", True),
	0x29: ("PUSH.S", True),
	0x2A: ("POP.pri", False),
	0x2B: ("POP.alt", False),
	0x2C: ("STACK", True),
	0x2D: ("HEAP", True),
	0x2E: ("PROC", False),
	0x2F: ("RET", False),
	0x30: ("RETN", False),
	0x31: ("CALL", True),
	0x32: ("CALL.pri", False),
	0x33: ("JUMP", True),
	0x34: ("JREL", True),
	0x35: ("JZER", True),
	0x36: ("JNZ", True),
	0x37: ("JEQ", True),
	0x38: ("JNEQ", True),
	0x39: ("JLESS", True),
	0x3A: ("JLEQ", True),
	0x3B: ("JGRTR", True),
	0x3C: ("JGEQ", True),
	0x3D: ("JSLESS", True),
	0x3E: ("JSLEQ", True),
	0x3F: ("JSGRTR", True),
	0x40: ("JSGEQ", True),
	0x41: ("SHL", False),
	0x42: ("SHR", False),
	0x43: ("SSHR", False),
	0x44: ("SHL.C.pri", True),
	0x45: ("SHL.C.alt", True),
	0x46: ("SHR.C.pri", True),
	0x47: ("SHR.C.alt", True),
	0x48: ("SMUL", False),
	0x49: ("SDIV", False),
	0x4A: ("SDIV.alt", False),
	0x4B: ("UMUL", False),
	0x4C: ("UDIV", False),
	0x4D: ("UDIV.alt", False),
	0x4E: ("ADD", False),
	0x4F: ("SUB", False),
	0x50: ("SUB.alt", False),
	0x51: ("AND", False),
	0x52: ("OR", False),
	0x53: ("XOR", False),
	0x54: ("NOT", False),
	0x55: ("NEG", False),
	0x56: ("INVERT", False),
	0x57: ("ADD.C", True),
	0x58: ("SMUL.C", True),
	0x59: ("ZERO.pri", False),
	0x5A: ("ZERO.alt", False),
	0x5B: ("ZERO", True),
	0x5C: ("ZERO.S", True),
	0x5D: ("SIGN.pri", False),
	0x5E: ("SIGN.alt", False),
	0x5F: ("EQ", False),
	0x60: ("NEQ", False),
	0x61: ("LESS", False),
	0x62: ("LEQ", False),
	0x63: ("GRTR", False),
	0x64: ("GEQ", False),
	0x65: ("SLESS", False),
	0x66: ("SLEQ", False),
	0x67: ("SGRTR", False),
	0x68: ("SGEQ", False),
	0x69: ("EQ.C.pri", True),
	0x6A: ("EQ.C.alt", True),
	0x6B: ("INC.pri", False),
	0x6C: ("INC.alt", False),
	0x6D: ("INC", True),
	0x6E: ("INC.S", True),
	0x6F: ("INC.I", False),
	0x70: ("DEC.pri", False),
	0x71: ("DEC.alt", False),
	0x72: ("DEC", True),
	0x73: ("DEC.S", True),
	0x74: ("DEC.I", False),
	0x75: ("MOVS", True),
	0x76: ("CMPS", True),
	0x77: ("FILL", True),
	0x78: ("HALT", True),
	0x79: ("BOUNDS", True),
	0x7A: ("SYSREQ.pri", False),
	0x7B: ("SYSREQ.C", True),
	0x7C: ("FILE", True),
	0x7D: ("LINE", True),
	# 0x7E: "SYMBOL" obsolete
	0x7F: ("SRANGE", True),
	0x80: ("JUMP.pri", False),
	0x81: ("SWITCH", True),
	0x82: ("CASETBL", False),
	0x83: ("SWAP.pri", False),
	0x84: ("SWAP.alt", False),
	0x85: ("PUSH.ADR", True),
	0x86: ("NOP", False),
	0x87: ("SYSREQ.D", True),
	0x88: ("SYMTAG", True),
	0x89: ("BREAK", False)
}

def simple_disassemble(plugin):
	
	bytecode = plugin.data[plugin.amx_header.cod:plugin.amx_header.dat] # code
	natives, publics = generate_function_list(plugin, plugin.amx_header)

	def find_public(addr):
		for public in publics :
			if public.address == addr :
				return public.name
		return None
		
	def find_native(addr):
		if addr < len(natives) :
			return natives[addr].name
		return "<no found>"
	
	def get_string(offset):
		addr = plugin.amx_header.dat + offset
		try :
			if is_string(addr):
				string_buff, string_size = get_amx_string(plugin.data, addr)
				return f'"{string_to_format(string_buff)}"'
		except :
			pass
		
		v = int.from_bytes(plugin.data[addr:addr+4], byteorder='little', signed=True)
		return v if v else ""

	index = 0
	asm_code = []
	
	for native in natives :
		asm_code.append(f"native: {native.name}()")
		
	for public in publics :
		asm_code.append(f"0x{public.address:08X} public {public.name}()")
	
	asm_code.append("")
	
	while index < len(bytecode):
	
		opcode = bytecode[index]
		index += 4
		
		if not opcode :
			continue
			
		op_hex = f"0x{(index - 4) & 0xFFFFFFFF:X}"
			
		if opcode in opcodes:
		
			op_name, has_param = opcodes[opcode]
			operand_values = []
			
			if has_param :
				# Leer un entero de 4 bytes como un operando
				operand_value = int.from_bytes(bytecode[index:index+4], byteorder='little', signed=True)
					
				hexa = f"0x{operand_value & 0xFFFFFFFF:X}"
					
				if opcode == 0x7b : # OP_SYSREQ_C
					operand_values.append(f"{hexa:<11} ; {find_native(operand_value)}()")
				elif opcode == 0x27 : # PUSH.C
					operand_values.append(f"{hexa:<11} ; {get_string(operand_value)}")
				else :
					operand_values.append(f"{hexa:<11} ; ")
										
				index += 4
						
			if op_name == "CASETBL":
				# Manejo especial para CASETBL
				if index + 7 < len(bytecode):
					num_cases = int.from_bytes(bytecode[index:index+4], byteorder='little', signed=True)
					index += 4
					default_addr = int.from_bytes(bytecode[index:index+4], byteorder='little', signed=True)
					index += 4
					operand_values = [f"cases:{num_cases}", f"default:{default_addr}"]
					for _ in range(num_cases):
						if index + 7 < len(bytecode):
							case_value = int.from_bytes(bytecode[index:index+4], byteorder='little', signed=True)
							index += 4
							case_addr = int.from_bytes(bytecode[index:index+4], byteorder='little', signed=True)
							index += 4
							operand_values.append(f"{case_value}:{case_addr}")
						else:
							operand_values.append("INVALID_CASE")
							break
				else:
					operand_values = ["INVALID_CASETBL"]
					
					
			if opcode == 0x2E :# OP_PROC
				asm_code.append("") # add new line
				
				name = find_public(index - 4)
				if name :
					asm_code.append(f"public {name}():")


			asm_code.append(f"{op_hex:<9} {op_name:>21}  {' '.join(map(str, operand_values))}")
			
		else:
			asm_code.append(f"UNKNOWN_OPCODE 0x{opcode:02X}")
			
	return "\n".join(asm_code)


def run_amxxdump():

	def execute_with_timeout(command, timeout):
		import subprocess
		
		try:
			result = subprocess.run(command,
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				timeout=timeout
			)
			return result.stdout, None
		except subprocess.TimeoutExpired:
			return None, "Error timeout."
		except Exception as e:
			return None, f"Error executing: {str(e)}"
	
	def get_absolute_path(path):
		if os.path.isabs(path) :
			return path
		script_dir = os.path.dirname(os.path.abspath(__file__))
		return os.path.abspath(os.path.join(script_dir, path))
	
	

	# Run AMXXDUMP
	old_cwd = os.getcwd()
	#new_cwd = os.path.join(os.path.dirname(__file__), "amxxdump")
	
	import sublime
	new_cwd = os.path.join(sublime.packages_path(), "AMXXEditorV4", "bin", "amxxdump")
	
	os.chdir(new_cwd)
	
	print("amxxdump path:", new_cwd)
	
	command = [
		"amxxdump",
		"-x", "-n", "-d", "-s", "-m", "-f", "-l", "-j", "-e", "-g", "-E",
		get_absolute_path(g_filename_amxx)
    ]
	
	print("run amxxdump...")
	
	asm, err = execute_with_timeout(command, 5)
	if err :
		print("ERROR AMXXBUMP:", err)
		
	os.chdir(old_cwd)


	# Check is valid ASM
	if not asm or asm.find(b" PROC ") == -1 :
		print("ERROR AMXXBUMP: Invalid ASM")
		# AmxxDump failed, use a basic disassemble
		print("run simple disassemble...")
		asm = simple_disassemble(plugin).encode("utf-8")
	else :
		asm = asm.replace(b"RETN ", b"RETN \n")
	

	# Write dump file
	if asm :
		with open(get_absolute_path(g_filename_dump), "wb") as file:
			file.write(asm)

		print("save .amxxdump file!")

def process(file_path):

	global plugin, g_filename_amxx, g_filename_raw, g_filename_memory, g_filename_dump
	
	
	print(f"AMXXUncompress v2.0 By Destro\n")
	
	amxx_extension = ".amxx"
	raw_extension = ".raw"
	memory_extension = ".amxxmemory"

	# Get the directory, base name, and extension
	dir_name, filename = os.path.split(file_path)
	base_name, ext = os.path.splitext(filename)
	
	isAMXX = False
	
	if ext.lower() == amxx_extension:
		g_filename_amxx = file_path
		g_filename_raw = os.path.join(dir_name, base_name + raw_extension)
		g_filename_memory = os.path.join(dir_name, base_name + memory_extension)
		g_filename_dump = os.path.join(dir_name, base_name + ".amxxdump")
		isAMXX = True
	elif ext.lower() == raw_extension:
	
		g_filename_raw = file_path
		g_filename_amxx = os.path.join(dir_name, base_name + amxx_extension)
		g_filename_memory = os.path.join(dir_name, base_name + memory_extension)
	else :
		print(f"Invalid file extension: {filename}")
		return False
	
	
	if True :
		with open(file_path, 'rb') as fp:
			print(f"Process FILE: '{file_path}'")
			
			if not read_header(fp):
				print(f"Failed to load header from: {filename}")
				return False

			if isAMXX :	# Uncompress AMXX
				if not amxx_uncompress(fp):
					print(f"[Failed to uncompress amxx")
					return False
				
				print(f"Successfully uncompressed amxx")
			else :		# Load uncompress RAW file
				load_uncompress(fp);
				print(f"Successfully load raw")
			
			# Get AMX header
			if not get_amx_header():
				print(f"Failed to get AMX header from uncompressed amxx")
				return False

			assert (plugin.amx_header.flags & 0x04) != 0 or plugin.amx_header.hea == plugin.amx_header.size, "Invalid plugin format"
			

			if (plugin.amx_header.flags & 0x04) != 0 :
				print(f"The code is compressed! Expand the bytes...")
				
				# clear flag
				plugin.amx_header.flags &= ~0x04
				plugin.isCOMPACT = True # Only for Print Flags
				
				# expand(code, codesize, memsize)
				newdata = expand(bytearray(plugin.data[plugin.amx_header.cod:]),
					plugin.amx_header.size - plugin.amx_header.cod,
					plugin.amx_header.hea - plugin.amx_header.cod)
				
				# backup debug data
				debugdata = None
				if plugin.dbg :
					debugdata = plugin.data[plugin.amx_header.size : plugin.amx_header.size+plugin.dbg.size]

				# Rstore expanded bytes
				plugin.data[plugin.amx_header.cod:plugin.amx_header.hea] = newdata

				# Recalculate image size
				plugin.imagesize = plugin.amx_header.size = plugin.amx_header.hea
				if plugin.dbg :
					plugin.imagesize += plugin.dbg.size
					plugin.data[plugin.amx_header.hea:plugin.imagesize] = debugdata
				
				print(f"Code bytes successfully expanded.")


			if isAMXX :
				# Cut bytearray unused memsize
				plugin.data = plugin.data[:plugin.imagesize]
				
				# Update amx header
				update_amx_header()
			
				with open(g_filename_raw, "wb") as raw_file:
					write_header(raw_file)
					raw_file.write(plugin.data)
	
				# Update .amxx witout AMX_FLAG_COMPACT (fix for amxxbump)
				if plugin.isCOMPACT :
					amxx_compress()

				print_plugin()

				print("Searching for strings...")
				string_count = generate_memory_file()
				print(f"found {string_count} strings!\n")
		
				run_amxxdump()
				
				print("save .amxxmemory file!")
				
			else :
				
				print(f"Loading .amxxmemory file")
				
				count = load_memory_file()
				if count :
					if count==1 :
						print(f"A memory address has been modified")
					else:
						print(f"{count} memory addresses have been modified")
				else :
					print(f"No changes in memory")
				
				if not amxx_compress() :
					print(f"Error while compressing")
					return False
					
				print(f"Successfully compressed: '{g_filename_amxx}'")
					
			return True



def print_plugin():
	global plugin
	
	print("")
	print("---------------------------------")
	
	print(f"AMXXPacket Header:")
	print(f"magic:           0x{plugin.magic:x}")
	print(f"version:         0x{plugin.version:x}")
	print(f"sections:        {plugin.sections}")
	print(f"cellsize:        {plugin.cellsize} Bytes")
	print(f"disksize:        {plugin.disksize} Bytes")
	print(f"imagesize:       {plugin.imagesize} Bytes")
	print(f"memsize:         {plugin.memsize} Bytes")
	print(f"offs:            {plugin.offs} Bytes")
	
	print("")
 
	print(f"AMXCode Header:")
	print(f"code size:       {plugin.amx_header.dat - plugin.amx_header.cod} Bytes")
	print(f"data size:       {plugin.amx_header.hea - plugin.amx_header.dat} Bytes")
	print(f"heap size:       {plugin.amx_header.stp - plugin.amx_header.hea} Bytes")
	print(f"public:          {(plugin.amx_header.natives - plugin.amx_header.publics) // plugin.amx_header.defsize }")
	print(f"native:          {(plugin.amx_header.libraries - plugin.amx_header.natives) // plugin.amx_header.defsize }")

	print("Frags:")
	if plugin.amx_header.flags & 0x02:
		print("- AMX_FLAG_DEBUG")
	if plugin.isCOMPACT: #plugin.amx_header.flags & 0x04:
		print("- AMX_FLAG_COMPACT (removed)")
	if plugin.amx_header.flags & 0x08:
		print("- AMX_FLAG_BYTEOPC")
	if plugin.amx_header.flags & 0x10:
		print("- AMX_FLAG_NOCHECKS")
	if plugin.amx_header.flags & 0x1000:
		print("- AMX_FLAG_NTVREG")
	if plugin.amx_header.flags & 0x2000:
		print("- AMX_FLAG_JITC")
	if plugin.amx_header.flags & 0x4000:
		print("- AMX_FLAG_BROWSE")
	if plugin.amx_header.flags & 0x8000:
		print("- AMX_FLAG_RELOC")
		
	if plugin.dbg :
		print("")
		print("DEBUG Header:")
		print(f"size:            {plugin.dbg.size} Bytes")
		print(f"magic:           0x{plugin.dbg.magic:x}")
	
	print("---------------------------------\n")
	

if __name__ == "__main__":
	#process("ask_redirect.amxx")
	#process("ask_redirect.raw")
	print("MAIN()!")
	#process("test.amxx")