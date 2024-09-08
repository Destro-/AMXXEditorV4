import time
import os
from AMXXcore.core import cfg


#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# Permormance Tool
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
class performance:
	
	data = dict()

	def init(key):
		performance.data[key] = { 'total': 0, 'start_time': 0, 'samples': [ ] }
		performance.start(key)
	
	def clear(key):
		performance.data[key]['total'] = 0
		performance.data[key]['samples'].clear()
		
	def start(key, clear=False):
		if clear :
			performance.clear(key)
		performance.data[key]['start_time'] = time.perf_counter()
			
	def pause(key):
		if performance.data[key]['start_time'] :
			s = (time.perf_counter() - performance.data[key]['start_time'])
			
			performance.data[key]['start_time']	= 0
			performance.data[key]['total'] += s
			
			performance.data[key]['samples'].append(s)
			
			return s
			
		return None
	
	def end(key):
		performance.pause(key)
		return performance.data[key]['total']

	def result(key, onlyTotal=False):
		performance.end(key)

		if onlyTotal or len(performance.data[key]['samples']) <= 1 :
			return "Total: %.3fsec" % performance.data[key]['total']
			
		return "Total: %.3fsec (min=%.3fsec, max=%.3fsec, avg=%.3fsec, samples=%d)" % (
			performance.data[key]['total'],
			min(performance.data[key]['samples']),
			max(performance.data[key]['samples']),
			performance.data[key]['total'] / len(performance.data[key]['samples']),
			len(performance.data[key]['samples'])
		)
		
	def run_test(repeat, func, *args, **kwargs):
		performance.init("_run_test")

		for _ in range(repeat) :
		
			performance.start("_run_test")
			func(*args, **kwargs)
			performance.pause("_run_test")
		
		return "%s() -> %s" % (func.__name__, performance.result("_run_test"))
		

#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# DEBUG/PRINT
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

# Enable editor debug messages:
# ""   - Disabled debugging.
# "a"  - Errors messages.
# "b"  - Warnings messages.
# "c"  - Info messages.
# "d"  - Dev messages.
# "e"  - Dev PawnParser.
# "f"  - Sublime EventListener.
# "g"  - Show scope on hover (tool for syntax dev).
# "z"  - Enable ViewDebugMode, show sections region (the code in view is parsed into small sections).
# "*"  - All debugging levels at the same time.
	
# 'CHAR in STRING' is most faster that bitwise (and most easy)
FLAG_ERROR		= "a"
FLAG_WARNING	= "b"
FLAG_INFO		= "c"
FLAG_INFO_DEV	= "d"
FLAG_INFO_PARSE	= "e"
FLAG_ST3_EVENT	= "f"
FLAG_SHOW_SCOPE	= "g"
FLAG_ALL		= "*"


def check_flags(flags):
	if FLAG_ALL in flags :
		from string import ascii_lowercase
		return ascii_lowercase
	return flags

	
def console(*args):
	print(__get_time(), *args)
	
def debug(flag_level, *args):
	if not flag_level or flag_level in cfg.debug_flags :
		console(*args)
		log(*args)

def error(*args):
	debug(FLAG_ERROR, "ERROR:", *args)
	
def warning(*args):
	debug(FLAG_WARNING, "WARNING:", *args)
	
def info(*args):
	debug(FLAG_INFO, "INFO:", *args)

def dev(*args):
	debug(FLAG_INFO_DEV, "DEV:", *args)


#:: Simple LOG
log_file = None

def log(*args):
	log_file.write(__get_time() + " " + " ".join(map(str, args)) + "\n")
	log_file.flush()
	
def log_open(file_path):
	global log_file
	log_file = open(file_path, mode='wt', encoding="utf-8")
	
def log_close():
	log_file.close()
	
def __get_time():
	return "[AMXX-Editor - %s]" % time.strftime("%H:%M:%S")