
import os
import sys
import time
import pprint

import urllib.request
import json



try:
	# To run this file, run on the Sublime Text console:
	# import imp; import AMXXEditorV4.tests.test as amxxtest; imp.reload(amxxtest); amxxtest.test("test.sma")
	import sublime_api

except (ImportError):
	assert_path( os.path.dirname( os.path.dirname( os.path.dirname( os.path.realpath( __file__ ) ) ) ) )


current_dir = os.path.dirname(os.path.abspath(__file__))
amxxeditor_dir = os.path.abspath(os.path.join(current_dir, '..'))
testing_dir = os.path.join(current_dir, 'testing')

sys.path.insert(0, amxxeditor_dir)
sys.path.append(os.path.join(amxxeditor_dir, "AMXXcore", "3rdparty") )

from AMXXEditorV4.AMXXEditor import NodeBase
from AMXXEditorV4.AMXXcore.core import *

import imp
import AMXXEditorV4.AMXXcore.pawn_parse
imp.reload(AMXXEditorV4.AMXXcore.pawn_parse)
from AMXXEditorV4.AMXXcore.pawn_parse import *


import AMXXcore.debug as debug

cfg.ac_local_var = True
cfg.ac_add_parameters = 1
cfg.debug_log_flags = cfg.debug_flags = "abcdef"


def test(file_name):

	debug.log_open(os.path.join(current_dir, "debug_test.log"))
	
	def start_test(file_path):
		
		node = NodeBase(file_path)
		parse = pawnParse()
		
		data = None

		with open(file_path) as file:
			data = parse.process(file, node)

		print("")
		print("- Funclist:")
		pprint.pprint(data.funclist)
		print("-" * 150)
		
		print("- Autocomplete:")
		pprint.pprint(data.autocomplete)
		print("-" * 150)

		print("- Constants:")
		pprint.pprint(data.constants)
		print("-" * 150)
		
		print("- Tags:")
		pprint.pprint(data.tags)
		print("-" * 150)

	file_path = os.path.join(testing_dir, file_name)
	
	print("\n\n[%s]" % time.strftime("%H:%M:%S"))
	print("#" * 150)
	print("- Test file:", file_path)
	print()

	start_test(file_path)
	
	print("#" * 150)
	
	debug.log_close()
	