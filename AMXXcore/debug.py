import time
import os

from AMXXcore.core import cfg, globalvar


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
		

#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# DEBUG PRINT/LOG
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::


# Debug message/log flags:
# ""   - Set default: "a".
# "a"  - Errors messages.
# "b"  - Warnings messages.
# "c"  - Info messages (e.g., timings, start & end analysis).
# "d"  - Dev messages (verbose info).
# "e"  - Error Analyzer parser.
# "f"  - Info Analyzer.
# "s"  - Sublime EventListener (dev).
# "z"  - Enable ViewDebugMode (colorize code sections).
# "*"  - All debugging flags at the same time.
FLAG_ERROR		= "a"
FLAG_WARNING	= "b"
FLAG_INFO		= "c"
FLAG_DEV		= "d"
FLAG_PARSE_ERROR= "e"
FLAG_PARSE_INFO	= "f"
FLAG_ST3_EVENT	= "s"
FLAG_ALL		= "*"

# Set default cfg values:
cfg.debug_flags = "ab"
cfg.debug_log_flags = "abcd"


def check_flags(flags):
	if not flags :
		return "a"
	if FLAG_ALL in flags :
		return "abcdef"
	return flags

def console(*args):
	print(__get_time(), *args)
	
def debug(flag_level, *args):
	if flag_level in cfg.debug_flags:
		console(*args)
	if flag_level in cfg.debug_log_flags:
		log(*args)

def error(*args):
	debug(FLAG_ERROR, "ERROR:", *args)

def warning(*args):
	debug(FLAG_WARNING, "WARNING:", *args)

def info(*args):
	debug(FLAG_INFO, "INFO:", *args)

def dev(*args):
	debug(FLAG_DEV, "DEV:", *args)

#:: Simple LOG
log_file = None

def log(*args):
	if not log_file :
		return
		
	log_file.write(__get_time() + " " + " ".join(map(str, args)) + "\n")
	log_file.flush()
	
def log_open(file_path):
	global log_file
	log_file = open(file_path, mode='wt', encoding="utf-8")
	
def log_close():
	log_file.close()
	
def __get_time():
	return "[AMXX: %s]" % time.strftime("%H:%M:%S")