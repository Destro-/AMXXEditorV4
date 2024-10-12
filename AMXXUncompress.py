import sublime
import sublime_plugin
import subprocess
import io
import sys
import os
import time

BASE_PATH = os.path.dirname(__file__)
sys.path.append(BASE_PATH)

class AmxxUncompressCommand(sublime_plugin.WindowCommand):
	def run(self):
		sublime.open_dialog(self.on_file_selected, [( "AMX Mod X", [ "amxx" ] )], "%HOMEPATH%")

	def on_file_selected(self, file_path):
	
		if not file_path:
			return

		if not file_path.endswith(".amxx"):
			sublime.message_dialog("Error: Invalid file extension, only .amxx")
			return

		process_file(file_path)

class EventListener(sublime_plugin.EventListener):
	view1 = None
	view2 = None
	layout = None

	@classmethod
	def register_views(cls, v1, v2, layout):
		cls.view1 = v1
		cls.view2 = v2
		
		if not cls.layout :
			cls.layout

	def on_close(self, view):


		if view == self.__class__.view1 or view == self.__class__.view2:
			remaining_view = self.__class__.view2 if view == self.__class__.view1 else self.__class__.view1
			window = remaining_view.window()

			if window:
			
				# Restore layout
				window.run_command("set_layout", self.__class__.layout)

				# Move the remaining view to the single pane
				window.set_view_index(remaining_view, 0, -1)
			
			# Clear the references
			self.__class__.view1 = None
			self.__class__.view2 = None
			self.__class__.layout = None
			
	def on_post_window_command(self, window, cmd, args):

		if cmd != "build" :
			return
			
		view = window.active_view()
		
		if not view.match_selector(0, 'source.amxx') :
			print("no match")
			return
			
		file_name = view.file_name()
		if not file_name :
			return
			
		base = os.path.splitext(file_name)[0]
		process_file(f"{base}.raw")
		
		print("BUILD!")
		

def process_file(file_path):

	try:
		import amxx_uncompress
	except ImportError:
		sublime.error_message("Failed to import: amxx_uncompress.py ")
		return

	# Preparar para capturar stdout
	old_stdout = sys.stdout
	sys.stdout = io.StringIO()
		
	try:
		# Llamar a la función process
		amxx_uncompress.process(file_path)
	except Exception as e:
		sublime.error_message(f"Error durante el procesamiento: {e}")
	finally:
		# Restaurar stdout y capturar la salida
		output = sys.stdout.getvalue()
		sys.stdout = old_stdout
		
	output += f'[{time.strftime("%H:%M:%S")}]'

	if file_path.endswith(".raw") :
		show_output(sublime.active_window(), output)
		return
		
	# New window
	sublime.run_command("new_window")
	window = sublime.active_window()
		
	# Hide Minimap
	window.set_minimap_visible(False)

	# Mostrar la salida en la consola de Sublime Text
	show_output(window, output)

	# Abrir los archivos .dump y .memory
	open_files(window, file_path)

def show_output(window, output):
	# Crear un nuevo panel y mostrar la salida
	panel = window.create_output_panel("amxx_uncompress_output")
	panel.set_read_only(False)
	panel.run_command("append", {"characters": output})
	panel.settings().set('gutter', False)
	panel.set_syntax_file("AMXX-Console.sublime-syntax")
	panel.set_read_only(True)
	window.run_command("show_panel", {"panel": "output.amxx_uncompress_output"})

def open_files(window, file_path):
	# Crear los nombres de los archivos .dump y .memory
	base, _ = os.path.splitext(file_path)
	dump_file = base + ".amxxdump"
	memory_file = base + ".amxxmemory"

	# Abrir los archivos en dos paneles divididos
	if os.path.exists(dump_file) and os.path.exists(memory_file):
		window.run_command("set_layout", {
			"cols": [0.0, 0.5, 1.0],
			"rows": [0.0, 1.0],
			"cells": [[0, 0, 1, 1], [1, 0, 2, 1]]
		})
			
		view1 = window.open_file(dump_file)
		window.set_view_index(view1, 0, -1)
			
		view1.settings().set('gutter', False)
		view1.set_read_only(True)
			
		view2 = window.open_file(memory_file)
		window.set_view_index(view2, 1, 0)
			
		layout = window.get_layout()
			
		# Register on the event listener
		EventListener.register_views(view1, view2, layout)
	else:
		sublime.error_message("Unable to find the generated .amxxdump and .amxxmemory files.")
