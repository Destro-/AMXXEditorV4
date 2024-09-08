# Sublime AMXXPawn-Editor 4.3 by Destro

import os
import re
import sys
import sublime, sublime_plugin
import webbrowser
import time
import urllib.request
import threading


BASE_PATH = os.path.dirname(__file__)

sys.path.append(BASE_PATH)
sys.path.append( os.path.join(BASE_PATH, "AMXXcore", "3rdparty") )

# 3rdparty dependencies.
import jstyleson
import watchdog.events
import watchdog.observers
from watchdog.utils.bricks 	import OrderedSetQueue
from pathtools.path 		import list_files

# Core AMXXPawn-Editor.
from AMXXcore.core 			import *
from AMXXcore.autocomplete 	import *
from AMXXcore.find_replace 	import *
from AMXXcore.pawn_parse 	import *
import AMXXcore.tooltip 	as tooltip
import AMXXcore.debug 		as debug

"""
import string
import random

def get_random_string(length):
	letters = string.ascii_lowercase
	result_str = ''.join(random.choice(letters) for i in range(length))
	return result_str
	
class PopupListener(sublime_plugin.EventListener):

	def on_selection_modified(self, view):
		view.show_popup(get_random_string(20), location=0)
"""
   
# import multiprocessing
#        return multiprocessing.cpu_count()


#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# Global VARs & Initialize
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
globalvar.EDITOR_VERSION 		= "4.3"
globalvar.PACKAGE_NAME			= "PawnAMXXEditor"
globalvar.FUNC_TYPES 			= Enum( [ "function", "public", "stock", "forward", "native" ] )

globalvar.nodes 				= dict()
globalvar.include_dirs			= list()

g_style_popup 		= { "list": [ ], "path": { }, "active": "" }
g_style_editor 		= { "list": [ ], "path": { }, "active": "" }
g_style_console 	= { "list": [ ], "path": { }, "active": "" }

g_invalid_settings	= False
g_edit_settings 	= False
g_check_update		= False
g_fix_view			= False


def plugin_loaded() :

	# Check package folder
	def createIfNotExists(path):
		if not os.path.isdir(path) :
			os.mkdir(path)
		
	packages_path = os.path.join(sublime.packages_path(), globalvar.PACKAGE_NAME)
	
	# Create custom folders
	createIfNotExists(packages_path)
	createIfNotExists(os.path.join(packages_path, "styles"))
	createIfNotExists(os.path.join(packages_path, "styles", "editor"))
	createIfNotExists(os.path.join(packages_path, "styles", "console"))
	createIfNotExists(os.path.join(packages_path, "styles", "popup"))
		
	# Logs
	debug.log_open(os.path.join(packages_path, "debug.log"))
	
	# MultiThreads start
	globalvar.analyzerQueue			= AnalyzerQueueThread()
	globalvar.monitorScrolled		= MonitorScrolledThread()
	globalvar.incFileEventHandler	= IncludeFileEventHandler()
	globalvar.popupFileEventHandler	= PopupFileEventHandler()
	globalvar.watchDog 				= watchdog.observers.Observer()
	globalvar.watchDog.start()
	
	# Code Analyzer/Parse
	globalvar.analyzer 				= CodeAnalyzer()
	globalvar.parse 				= pawnParse()
				
	# Config
	cfg.init(on_config_change)
	
	# NOTA: Mejorar, asegurarse de comprobar el tiempo entre cada comprobacion
	#sublime.set_timeout_async(check_update, 2500)

def plugin_unloaded() :

	# MultiThreads Stop
	globalvar.watchDog.stop()
	globalvar.analyzerQueue.stop()
	globalvar.monitorScrolled.stop()
	
	# Log
	debug.log_close()
	
def on_config_change() :

	# Profiles
	cfg.default_profile		= cfg.get('default_profile', "")
	cfg.profiles 			= cfg.get("build_profiles", None)
	if not cfg.profiles :
		validate_profile("", None)
		print("ERROR: if not cfg.profiles")
		return
		
	globalvar.profiles_list = list(cfg.profiles.keys())
	globalvar.include_dirs.clear()
	
	for profile_name in globalvar.profiles_list :
		profile = cfg.profiles[profile_name]
		
		# Fix values
		profile['output_dir'] 		= util.cfg_get_path(profile, 'output_dir')
		profile['include_dir'] 		= util.cfg_get_path(profile, 'include_dir')
		profile['amxxpc_path'] 		= util.cfg_get_path(profile, 'amxxpc_path')
		
		if not validate_profile(profile_name, profile) :
			return
		
		if 'amxxpc_debug' in profile :
			profile['amxxpc_debug'] = util.clamp(int(profile['amxxpc_debug']), 0, 2)
		else :
			profile['amxxpc_debug'] = 2
			
		globalvar.include_dirs.append(profile['include_dir'])

	if not cfg.default_profile in globalvar.profiles_list :
		cfg.default_profile = globalvar.profiles_list[0]


	# Cache settings
	cfg.enable_tooltip 			= cfg.get('enable_tooltip', True)
	cfg.enable_buildversion 	= cfg.get('enable_buildversion', True)
	cfg.enable_marking_error 	= cfg.get('enable_marking_error', True)
	cfg.enable_const_highlight 	= cfg.get('enable_const_highlight', True)
	
	cfg.style_popup_mode		= cfg.get('style_popup_mode', 0)
	
	cfg.ac_enable 				= cfg.get('ac_enable', True)
	cfg.ac_keywords 			= cfg.get('ac_keywords', 2)
	cfg.ac_snippets 			= cfg.get('ac_snippets', True)
	cfg.ac_preprocessor 		= cfg.get('ac_preprocessor', True)
	cfg.ac_emit_info	 		= cfg.get('ac_emit_info', True)
	cfg.ac_local_var			= cfg.get('ac_local_var', True)
	cfg.ac_extra_sorted			= cfg.get('ac_extra_sorted', True)
	cfg.ac_explicit_mode 		= cfg.get('ac_explicit_mode', False)
	cfg.ac_add_parameters		= cfg.get('ac_add_parameters', 1)
	
	cfg.debug_flags 			= debug.check_flags(cfg.get('debug_flags', ""))
	cfg.include_dir 			= cfg.profiles[cfg.default_profile]['include_dir']
	
	# Update Live reflesh delay.
	globalvar.analyzerQueue.delay	= util.clamp(float(cfg.get('live_refresh_delay', 1.5)), 0.5, 5.0)
	
	
	# Generate list of styles
	global g_style_popup, g_style_editor, g_style_console
	
	g_style_popup['list'].clear()
	g_style_editor['list'].clear()
	g_style_console['list'].clear()
	
	g_style_editor['list'].append("default")
	g_style_console['list'].append("default")
	
	list_styles(g_style_popup,		".pawn-popup.css")
	list_styles(g_style_editor,		".pawn-editor.sublime-color-scheme")
	list_styles(g_style_console,	".pawn-console.sublime-color-scheme")
	
	validate_active_style(g_style_popup, "style_popup")
	validate_active_style(g_style_editor, "style_editor")
	validate_active_style(g_style_console, "style_console")

	# Update style
	update_editor_style()
	update_console_style()
	update_popup_style()
	
	
	if cfg.style_popup_mode == 1:
		globalvar.cacheSyntaxCSS = self.generate_highlightCSS(view)
	else :
		globalvar.cacheSyntaxCSS = ''
	
	
	globalvar.watchDog.unschedule_all()

	for profile_name in globalvar.profiles_list :
		if list_includes(cfg.profiles[profile_name]):
			globalvar.watchDog.schedule(globalvar.incFileEventHandler, cfg.profiles[profile_name]['include_dir'], True)

	# Popup style autoload on changed
	path = os.path.join(sublime.packages_path(), globalvar.PACKAGE_NAME, "styles", "popup")
	if os.path.isdir(path) :
		globalvar.watchDog.schedule(globalvar.popupFileEventHandler, path)
	
	# Autocompletion keyword cache
	ac.init()
	

def list_includes(profile):
	
	bad_files = 0
	profile['includes_list'] = list()
	
	for inc in list_files(profile['include_dir']) :
		if inc.endswith(".inc") :
			inc = inc.replace(profile['include_dir'], "").lstrip("\\/").replace("\\", "/").replace(".inc", "")
			profile['includes_list'].append(inc)
		else : # big recursive loop in root folder  (example: 'C:\\')
			bad_files += 1
			if bad_files >= 50 :
				debug.warning("Big recursive loop, include_dir: \"%s\"" % profile['include_dir'])
				return False
				
	profile['includes_list'] = ac.sorted_nicely(profile['includes_list'])
	return True

def update_editor_style():
	if "default" == g_style_editor['active'] :
		newValue = None
	else :
		newValue = g_style_editor['path'][g_style_editor['active']]
		
	s = CustomSettings("AMXX-Pawn.sublime-settings", True)
	s.set("color_scheme", newValue)
	s.set("show_errors_inline", False)
	s.set("word_separators", "./\\()\"'-:,.;<>~!$%^&*|+=[]{}`~?")
	s.set("extensions", [ "sma", "inc" ])
	
	if newValue :
		data = util.safe_json_load(newValue).get("amxxeditor")
		if data :
			extra_settings = data.get('syntax_settings')
			for key in extra_settings :
				s.set(key, extra_settings[key])
	s.save()
	
def update_console_style():
	if "default" == g_style_console['active'] :
		newValue = None
	else :
		newValue = g_style_console['path'][g_style_console['active']]
		
	s = CustomSettings("AMXX-Console.sublime-settings", True)
	s.set('color_scheme', newValue)
	
	if newValue :
		data = util.safe_json_load(newValue).get("amxxeditor")
		if data :
			extra_settings = data.get('syntax_settings')
			for key in extra_settings :
				s.set(key, extra_settings[key])	
	s.save()
	
def update_popup_style():
	globalvar.cachePopupCSS = sublime.load_resource(g_style_popup['path'][g_style_popup['active']])
	globalvar.cachePopupCSS = globalvar.cachePopupCSS.replace('\r', '') # Fix endline
	
	# Remove comments
	globalvar.cachePopupCSS = re.sub(r'/\*.*?\*/', '', globalvar.cachePopupCSS, 0, re.DOTALL)
	globalvar.cachePopupCSS = globalvar.cachePopupCSS.replace('\n\n', '\n')


def list_styles(style, endext):
	for file in sublime.find_resources("*" + endext) :
		name = os.path.basename(file).replace(endext, "")
	
		if not name in style['list'] :
			style['list'].append(name)
			
		style['path'][name] = file
		
def validate_active_style(style, key):
	style['active']	= cfg.get(key)
	if not style['active'] in style['list'] :
		style['active'] = style['list'][0]

def validate_profile(profile_name, profile) :

	error = "Invalid profile configuration :  %s\n\n" % profile_name

	if not profile or not isinstance(profile, dict) or profile.get('amxxpc_path') == None or profile.get('include_dir') == None or profile.get('output_dir') == None :
		error += "Empty Value\n"
	elif not os.path.isfile(util.cfg_get_path(profile, 'amxxpc_path')) :
		error += "amxxpc_directory :  File does not exist.\n\"%s\"" % util.cfg_get_path(profile, 'amxxpc_path')
	elif not os.path.isdir(util.cfg_get_path(profile, 'include_dir')) :
		error += "include_directory :  Directory does not exist.\n\"%s\"" % util.cfg_get_path(profile, 'include_dir')
	elif profile.get('output_dir') != "${file_path}" and not os.path.isdir(util.cfg_get_path(profile, 'output_dir')) :
		error += "output_dir :  Directory does not exist.\n\"%s\"" % util.cfg_get_path(profile, 'output_dir')
	else :
		return True
		
	global g_invalid_settings, g_edit_settings
		
	g_invalid_settings = True
		
	sublime.message_dialog("AMXX-Editor:\n\n" + error)

	if g_edit_settings :
		return False

	g_edit_settings = True
		
	file_path = sublime.packages_path() + "/User/AMXX-Editor.sublime-settings"
		
	if not os.path.isfile(file_path):
		default = sublime.load_resource("Packages/"+globalvar.PACKAGE_NAME+"/AMXX-Editor.sublime-settings")
		default = default.replace("Example:", "User Settings:")
		f = open(file_path, "w")
		f.write(default)
		f.close()

	sublime.set_timeout_async(run_edit_settings, 250)
	return False
	
def run_edit_settings() :
	sublime.active_window().run_command("edit_settings", {"base_file": "${packages}/"+globalvar.PACKAGE_NAME+"/AMXX-Editor.sublime-settings", "default": "{\n\t$0\n}\n"})


class AmxxProfileCommand(sublime_plugin.ApplicationCommand):

	def run(self, index) :
		if index >= len(globalvar.profiles_list) :
			return

		cfg.default_profile = globalvar.profiles_list[index]
		
		cfg.set("default_profile", cfg.default_profile)
		cfg.save()

	def is_visible(self, index) :
		return (index < len(globalvar.profiles_list))
		
	def is_checked(self, index) :
		return (index < len(globalvar.profiles_list) and globalvar.profiles_list[index] == cfg.default_profile)

	def description(self, index) :
		if index < len(globalvar.profiles_list) :
			return globalvar.profiles_list[index]
		return ""
		
class AmxxEditorStyleCommand(sublime_plugin.ApplicationCommand):

	def run(self, index) :
		if index >= len(g_style_editor['list']) :
			return
		
		g_style_editor['active'] = g_style_editor['list'][index]
		
		cfg.set("style_editor", g_style_editor['active'])
		
		if not index :
			cfg.save(False)
			return
			
		path = g_style_editor['path'][g_style_editor['active']]
		
		data = util.safe_json_load(path).get("amxxeditor")
		if data :

			if data.get('default_popup', 'default') in g_style_popup['list'] :
				cfg.set("style_popup", data['default_popup'])
			if data.get('default_console', 'default') in g_style_console['list'] :
				cfg.set("style_console", data['default_console'])
			
		cfg.save(False)

	def is_visible(self, index) :
		return (index < len(g_style_editor['list']))
		
	def is_checked(self, index) :
		return (index < len(g_style_editor['list']) and g_style_editor['list'][index] == g_style_editor['active'])

	def description(self, index) :
		if index < len(g_style_editor['list']) :
			return g_style_editor['list'][index]
		return ""

class AmxxEditorStyleConsoleCommand(sublime_plugin.ApplicationCommand):

	def run(self, index) :
		if index >= len(g_style_console['list']) :
			return

		g_style_console['active'] = g_style_console['list'][index]
		
		cfg.set("style_console", g_style_console['active'])
		cfg.save()
		
		update_console_style()

	def is_visible(self, index) :
		return (index < len(g_style_console['list']))
		
	def is_checked(self, index) :
		return (index < len(g_style_console['list']) and g_style_console['list'][index] == g_style_console['active'])

	def description(self, index) :
		if index < len(g_style_console['list']) :
			return g_style_console['list'][index]
		return ""

class AmxxEditorStylePopupCommand(sublime_plugin.ApplicationCommand):

	def run(self, index) :
		if index >= len(g_style_popup['list']) :
			return

		g_style_popup['active'] = g_style_popup['list'][index]
		
		cfg.set("style_popup", g_style_popup['active'])
		cfg.save()
		
		update_popup_style()
	#}

	def is_visible(self, index) :
		return (index < len(g_style_popup['list']))
		
	def is_checked(self, index) :
		return (index < len(g_style_popup['list']) and g_style_popup['list'][index] == g_style_popup['active'])

	def description(self, index) :
		if index < len(g_style_popup['list']) :
			return g_style_popup['list'][index]
		return ""

class AmxxNewIncludeCommand(sublime_plugin.WindowCommand):
	def run(self):
		new_file("inc")
		
class AmxxNewPluginCommand(sublime_plugin.WindowCommand):
	def run(self):
		new_file("sma")

def new_file(type):
	view = sublime.active_window().new_file()

	view.set_syntax_file("AMXX-Pawn.sublime-syntax")
	view.set_name("untitled."+type)
	
	plugin_template = sublime.load_resource("Packages/"+globalvar.PACKAGE_NAME+"/default."+type)
	plugin_template = plugin_template.replace("\r", "")
	
	view.run_command("insert_snippet", {"contents": plugin_template})
	
def updating_message():

	global g_check_update
	
	if not g_check_update :
		return
	
	progess = "." * (g_check_update % 4)
	g_check_update += 1
	
	sublime.active_window().status_message("AMXX Check update: " + progess)
	sublime.set_timeout(updating_message, 300)
	
def check_update(bycommand=0) :
#{
	global g_check_update
	
	g_check_update = True
	updating_message()

	try:
		c = urllib.request.urlopen("https://amxmodx-es.com/st.php")
	except:
		if bycommand :
			sublime.error_message("ERROR: timeout 'urlopen' in check_update()")
	
		debug.error("timeout 'urlopen' in check_update()")
		sublime.active_window().status_message("AMXX Check update: failed")
		c = None
		
	g_check_update = False
	
	if not c :
		return
		
	data = c.read().decode("utf-8", "replace")

	if data :
	#{
		sublime.active_window().status_message("AMXX Check update: successful")
		
		data = data.split("\n", 1)
		
		fCheckVersion = float(data[0])
		fCurrentVersion = float(globalvar.EDITOR_VERSION)
			
		if fCheckVersion == fCurrentVersion and bycommand:
			sublime.ok_cancel_dialog("AMXX: You are already using the latest version:  v"+ globalvar.EDITOR_VERSION, "OK")
			
		if fCheckVersion > fCurrentVersion :
			msg  = "AMXX: A new version is available:  v"+ data[0]
			if len(data) > 1 :
				msg += "\n\nNews:\n" + data[1]
				
			ok = sublime.ok_cancel_dialog(msg, "Download Update")
			
			if ok :
				webbrowser.open_new_tab("https://amxmodx-es.com/showthread.php?tid=12316")
	#}
#}


# https://codereview.stackexchange.com/questions/185509/sublime-text-plugin-to-modify-text-before-its-pasted
class AmxxEscapeAndPasteCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		# Get the clipboard text
		originalText = textToPaste = sublime.get_clipboard() 
		
		if not '^n' in textToPaste and not '^"' in textToPaste and not '^^' in textToPaste :
			textToPaste = textToPaste.replace('^', '^^')
			textToPaste = textToPaste.replace('"', '^"')
			
		textToPaste = textToPaste.replace('\r', '')
		textToPaste = textToPaste.replace('\n', '^n')
		textToPaste = textToPaste.replace('\t', '^t')

		# Place the text back into the clipboard and paste in place
		sublime.set_clipboard(textToPaste)
		self.view.run_command("paste")
		
		# Restore the original text to the clipboard
		sublime.set_clipboard(originalText)

class FindReplaceInputHandler(sublime_plugin.TextInputHandler):
	def __init__(self, core):
		self.core = core
		self.is_valid = False

	def preview(self, text):
	
		print("preview()", self.core.window.active_view().id())
		
		if self.core.last_error :
			error = self.core.last_error
			self.core.last_error = ""
		else : # current error
			error = self.core.process(text, True)
		
		if error or not text :
			self.is_valid = False
		else:
			self.is_valid = True

		if text == "help_replace::" :
			body = """
			<b>REPLACE EXAMPLEs:</b>
			<br>
			source = "new g_menu, g_menu_select, g_menu_id"
			<br>
			<br>
			input  = "word::g_menu::replace::menu2"
			<br>
			result = "new menu2, g_menu_select, g_menu_id"
			<br>
			<br>
			input  = "re::(\\w*)_(\\w*)_(\\w*)::replace::\\3_\\2_\\1"
			<br>
			result = "new g_menu, select_menu_g, id_menu_g"
			<br>
			<br>
			input  = "g_menu_::replace::menu2_"
			<br>
			result = "new g_menu, g_menu2_select, g_menu2_id"
			"""
		elif not text :
			body = """
			<b>Keywords:</b>
			<br>
			re::
			<br>
			word::
			<br>
			::replace::
			<br>
			help_replace::
			"""
		else :
			
			if not self.core.search_type :
				body = "<b>Search:</b> %s" % self.core.search
			else :
				body = "<b>Pattern:</b> %s" % self.core.search_pattern

			if not self.core.replace == None :
				body += "<br><b>Replace:</b> %s" % self.core.replace
				
			
		###################################################################
		if error :
			body += "<br><br><span><b>Error:</b> %s</span>" % error


		content = """
		<html>
		<style>
		body {
			color: #000;
			margin-top: 0px;
			margin-bottom: 2px;
			font-size: 13px;
		}

		h1 { 
			font-size: 16px;
			color: #ff9933;
		}

		b {
			font-size: 13px;
		}

		i {
			font-size: 12px;
		}

		span {
			font-size: 13px;
			color: #f00;
		}

		</style>
		<body>
		""" + body + """
		</body>
		</html>
		"""

		return sublime.Html(content)

	def placeholder(self):
		return "Search"
		
	def initial_text(self):
		return self.core.initial_text
	
	def validate(self, value):
		return self.is_valid
		
	def confirm(self, value):
		pass

	def cancel(self):
		self.core.initial_text = ""

class AmxxFindReplaceCommand(sublime_plugin.WindowCommand):
	def __init__(self, window):
		self.window = window
		self.core 	= AmxxFindReplace(window)
	
	def run(self, find_replace):

		global g_fix_view
		if g_fix_view :
			g_fix_view = False
			self.core.view = self.window.active_view()
		
		error = self.core.process(find_replace)
		if error :
			self.window.run_command("amxx_find_replace")

	def is_enabled(self):
		return is_amxmodx_view(self.window.active_view())
	
	def input(self, args):
		self.core.view = self.window.active_view()
		return FindReplaceInputHandler(self.core)
		
	def input_description(self):
		#return "Search:"
		return "🔍"

		
class AmxxTreeCommand(sublime_plugin.WindowCommand):
	def __init__(self, window):
		self.window = window
		self.quickpanel = False
		
	def run(self):
		view = self.window.active_view()
		
		self.window.run_command("hide_overlay")
		
		if self.quickpanel :
			self.quickpanel = False
		else :
			includes 	= dict()
			visited 	= dict()
			self.tree	= [ ]
			node 		= get_view_node(view)
			
			if not node :
				return

			self.nodes_tree(node, includes, visited, 0)
			self.generate_tree(self.tree, includes, visited, 0)

			quicklist = []
			for inc in self.tree :
				quicklist += [ inc[0] ]
			
			self.window.show_quick_panel(quicklist, self.on_select, 0, -1, None)
			self.quickpanel = True
			
	def is_enabled(self) :
		view = self.window.active_view()
		
		if not is_amxmodx_view(view) :
			return False
		
		return True
		
	def on_select(self, index):
		self.quickpanel = False
		
		if index == -1 :
			return

		util.goto_definition(self.tree[index][1], "", None, False)
	
	def nodes_tree(self, node, includes, visited, level):

		keys = visited.keys()
		if node.file_path in keys :
			if visited[node.file_path] < level :
				return

		visited[node.file_path] = level
		includes[node.file_path] = { 'level': level, 'ignore': 0 }
		
		for child in node.children :
			self.nodes_tree(child, includes[node.file_path], visited, level+1)

	def generate_tree(self, tree, include, visited, level):

		keys = include.keys()
		keys = list(keys)
		keys.sort()
		
		
		
		a = ""
			
		if level >= 2 :
				a += "ˑˑˑˑ" * (level - 1)
				
		open = True
		
		for key in keys:
			if key == 'level' or key == 'ignore' :
				continue
				
			if include[key]['ignore'] or include[key]['level'] > visited[key] :
				continue
				
			if include[key]['level'] > 2 :
				include[key]['ignore'] = 1
			
			if open :
				open = False
				if level >= 1 :
					tree += [ [ "%s└─̵▸%s" % (a, os.path.basename(key)), key ] ]
				else:
					tree += [ [ "%s%s" % (a, os.path.basename(key)), key ] ]
			else :
				tree += [ [ "%sˑˑˑˑ▸%s" % (a, os.path.basename(key)), key ] ]
		
			self.generate_tree(tree, include[key], visited, level+1)
		
	
class AmxxFuncListCommand(sublime_plugin.WindowCommand):
	def __init__(self,  window):
		self.window = window
		self.quickpanel = False
		self.org_view 	= [ ]
		
	def run(self):
		view = self.window.active_view()
		
		self.window.run_command("hide_overlay")
		
		if self.quickpanel :
			self.quickpanel = False
		else :
			region = view.sel()[0]
			scroll = view.viewport_position()
			
			self.org_view = [ self.window, view, region, scroll ]
			
			node = get_view_node(view)
			if not node :
				return
			
			funclist = node.generate_list("funclist", set)
			
			self.list = []
			for func in funclist :
				if not cfg.include_dir in func.file_path :
					self.list += [ [ func.name, func.file_path, func.start_line ] ]

			self.list = ac.sorted_nicely(self.list)
			
			quicklist = []
			for list in self.list :
				quicklist += [ [ list[0], os.path.basename(list[1]) + " : " + str(list[2]) ] ]

			self.window.show_quick_panel(quicklist, self.on_select, sublime.KEEP_OPEN_ON_FOCUS_LOST, -1, self.on_highlight)
			self.quickpanel = True

	def is_enabled(self) :
		view = self.window.active_view()
		
		if not is_amxmodx_view(view) :
			return False
		
		return True
		
	def on_select(self, index):
		self.quickpanel = False
		
		if index == -1 :
			self.restore_org(True)
			return
		
		id = util.goto_definition(self.list[index][1], self.list[index][0], self.list[index][2] - 1, False)
		
		if id != self.org_view[1].id() :
			self.restore_org(False)
		
	def on_highlight(self, index):

		util.goto_definition(self.list[index][1], self.list[index][0], self.list[index][2] - 1, True)
		
	def restore_org(self, focus=False):
		if self.org_view :
			window 	= self.org_view[0]
			view 	= self.org_view[1]
			region 	= self.org_view[2]
			scroll 	= self.org_view[3]
				
			if focus :
				window.focus_view(view)
				
			view.sel().clear()
			view.sel().add(region)
			view.set_viewport_position(scroll, False)
				
			self.org_view = []
			
class AmxxBuildVerCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		region = self.view.find("^#define\s+(?:PLUGIN_)?VERSION\s+\".+\"", 0, sublime.IGNORECASE)
		if region == None :
			region = self.view.find("new\s+const\s+(?:PLUGIN_)?VERSION\s*\[\s*\]\s*=\s*\".+\"", 0, sublime.IGNORECASE)
			if region == None :
				return
		
		line = self.view.substr(region)
		result = re.match("(.*\"(?:v)?\d{1,2}\.\d{1,2}\.(?:\d{1,2}-)?)(\d+)(b(?:eta)?)?\"", line)
		if not result :
			return

		build = int(result.group(2))
		build += 1
		
		beta = result.group(3)
		if not beta :
			beta = ""
		
		self.view.replace(edit, region, result.group(1) + str(build) + beta + '\"')
			

class AboutInputHandler(sublime_plugin.ListInputHandler):
	def preview(self, text):
		content = """
<html>
<style>
html {
	background-color: #fff2;
}

body {
	color: #000;
	margin-top: 0px;
}

h1 { 
	font-size: 20px;
	color: #000;
}

b {
	font-size: 11px;
}

i {
	font-size: 9px;
}

img {
	height: 80px;
	width: 200px;
}
</style>
<body>

<h1>Sublime AMXX-Editor v""" + globalvar.EDITOR_VERSION + """ by Destro</h1>
<b>CREDITs:</b><br>
ppalex7 <i>(SourcePawn Completions)</i><br>
<br>
<b>- Contributors:</b><br>
sasske <i>(white color scheme)</i><br>
addons_zz <i>(npp color scheme)</i><br>
KliPPy <i>(build version)</i><br>
Mistrick <i>(mistrick color scheme)</i><br>
Matt <i>(StringEscapeAndPaste)</i><br>

<div style="background-color: #f00; position: relative; left: 360px; top: -65px; height: 0px; width: 0px;">
<img src="file://C:/Users/Emanue/Desktop 4/subime pawn logo/logo_pawneditor.png">
</div>


</body>
</html>
"""

		return sublime.Html(content)

	def list_items(self):
		return [ ( "Exit", 0 ), ( "Donate", 1 ), ( "Visit Web", 2 ), ( "Check Updates", 3 ) ]

	def confirm(self, value):
		if not value :
			return
		
		if value == 1 :
			webbrowser.open_new_tab("https://amxmodx-es.com/donaciones.php")
		elif value == 2 :
			webbrowser.open_new_tab("https://amxmodx-es.com/showthread.php?tid=12316")
		else :
			sublime.set_timeout_async( lambda:check_update(True), 10)
	
	
class AmxxAboutCommand(sublime_plugin.WindowCommand):
	def run(self, about):
		pass
	
	def input(self, args):
		return AboutInputHandler()
		

#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#:: END Cmd / START Sublime EventListener ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
"""
class HolaMundo(sublime_plugin.ViewEventListener):
	def __init__(self, view):
		self.view = view
		self.data = 1
	#	print("__init__", view.id())
	
	
	#def __del__(self):
	#	print("__del__", self.view.id())
		
	def on_deactivated(self):
		print("on_deactivated3:", self.view.id(), "Mydata:", self.data)
	
	def on_activated(self) :

		self.data += 1
		
		print("on_activated3:", self.view.id(), "Mydata:", self.data)
"""
class SublimeEvents(sublime_plugin.EventListener):

	originalText = ""
	
	#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	#:: Util Functions :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	def debug_event(self, *args):
		debug.debug(debug.FLAG_ST3_EVENT, "SublimeEVENT:", *args)
		
	def add_to_queue(self, view):
		if not is_amxmodx_view(view):
			return

		globalvar.analyzerQueue.add_to_queue(None, view.id())

	def generate_highlightCSS(self, view):
	
		def scope_to_css(scope, classCSS):
			style = view.style_for_scope(scope)
			
			css = ".%s {" % classCSS
			if 'foreground' in style :
				css += " color: " + style['foreground'] + ";"
			if 'background' in style :
				css += " background-color: " + style['background'] + ";"
			if style['bold'] :
				css += " font-weight: bold;"
			if style['italic'] :
				css += " font-style: italic;"
			return css + " }\n"

		highlightCSS  = scope_to_css("", "pawnDefaultColor")
		highlightCSS += scope_to_css("variable.function", "pawnFunction")
		highlightCSS += scope_to_css("string", "pawnString")
		highlightCSS += scope_to_css("keyword", "pawnKeyword")
		highlightCSS += scope_to_css("storage.type.vars", "pawnConstant")
		highlightCSS += scope_to_css("constant.numeric", "pawnNumber")
		highlightCSS += scope_to_css("storage.modifier.tag", "pawnTag")

		return highlightCSS

	#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	#:: Unused, Dev-Only :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	def on_new(self, view):
		self.debug_event("on_new() -> view:[%d] - file:[%s]" % (view.id(), view.file_name()))

	def on_close(self, view):
		self.debug_event("on_close() -> view:[%d] - file:[%s]" % (view.id(), view.file_name()))

	def on_deactivated(self, view):
		self.debug_event("on_deactivated() -> view:[%d] - file:[%s]" % (view.id(), view.file_name()))

	#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	#:: Add to Queue :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	def on_activated(self, view):
		self.debug_event("on_activated() -> view:[%d] - file:[%s]" % (view.id(), view.file_name()))
		
		if not is_amxmodx_view(view):
			return
	
		node = get_view_node(view)
		if node :
			node.organize_and_cache()
		else :
			self.add_to_queue(view)

	def on_post_save(self, view):
		self.debug_event("on_post_save() -> view:[%d] - file:[%s]" % (view.id(), view.file_name()))
		self.add_to_queue(view)

	def on_load(self, view):
		self.debug_event("on_load() -> view:[%d] - file:[%s]" % (view.id(), view.file_name()))
		self.add_to_queue(view)
		
		"""
		>>> sublime.active_window().active_view().settings().erase('syntax')
		>>> sublime.active_window().active_view().settings().get('syntax')
		"""
	
	# Delayed queue
	def on_modified(self, view):
		
		if not is_amxmodx_view(view):
			return
			
		self.debug_event("on_modified() -> view:[%d] - file:[%s]" % (view.id(), view.file_name()))

		globalvar.analyzerQueue.add_to_queue_delayed(view)
		
		clear_error_lines(view)

	#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	#:: Auto build version - Auto Tag - Auto string escape and paste :::::::::::::::::::::::::::::::::::::
	#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	def on_text_command(self, view, cmd, args):
		
		self.debug_event("on_text_command() -> cmd:[%s] - arg:[%s]" % (cmd, args))
		#print("on_text_command() -> cmd:[%s] - arg:[%s]" % (cmd, args))

		if not is_amxmodx_view(view) :
			return
			
		if cmd != "paste" :
			return
			
		sel = view.sel()
		if len(sel) != 1 : # skip multi-selections
			return
			
		scope = view.scope_name(sel[0].begin())
		
		if not "string.quoted.double.pawn" in scope :
			return
		
		self.originalText = textToPaste = sublime.get_clipboard() 
		
		if not '^n' in textToPaste and not '^"' in textToPaste and not '^^' in textToPaste :
			textToPaste = textToPaste.replace('^', '^^')
			textToPaste = textToPaste.replace('"', '^"')
			
		textToPaste = textToPaste.replace('\r', '')
		textToPaste = textToPaste.replace('\n', '^n')
		textToPaste = textToPaste.replace('\t', '^t')

		# Place the text back into the clipboard and paste in place
		sublime.set_clipboard(textToPaste)
		
	def on_post_text_command(self, view, cmd, args):
		
		if cmd != "paste" or not self.originalText :
			return
			
		# Restore the original text to the clipboard
		sublime.set_clipboard(self.originalText)
		
		self.originalText = ""
	
	def on_window_command(self, window, cmd, args):

		self.debug_event("on_window_command() -> cmd:[%s] - arg:[%s]" % (cmd, args))
		
		if cmd != "build" :
			return
			
		p = cfg.profiles[cfg.default_profile]
		
		build = SublimeSettings("AMXX-Compiler.sublime-build")
		build.set("cmd", [ p['amxxpc_path'], "-d"+str(p['amxxpc_debug']), "-i"+p['include_dir'], "-o"+p['output_dir']+"/${file_base_name}.amxx", "${file}" ])
		build.set("syntax", "AMXX-Console.sublime-syntax")
		build.set("selector", "source.sma")
		build.set("working_dir", os.path.dirname(p['amxxpc_path']))
		build.set("file_regex", "(.*)\\((\\d+)")
		build.set("quiet", True)
		build.save()
	
		view = window.active_view()
		if not is_amxmodx_view(view) :
			return
			
		if not view.file_name() :
			view.run_command("save")
			
		self.amxx_auto_tag(window, view)
			
		if cfg.enable_buildversion :
			view.run_command("amxx_build_ver")
		
	def amxx_auto_tag(self, window, view):
		
		node = get_view_node(view)
		if not node :
			return

		findreplace = AmxxFindReplace(window)
		
		funclist = node.generate_list("funclist", set)
		includes = findreplace.get_includes(view)
		
		def replace_autotag(text):
			def search_vartag(varname, text):
				m = re.search(varname+r'\s*=\s*([a-zA-Z_]\w*)\s*\(', text, re.MULTILINE)
				if not m :
					return None
					
				search_func = m.group(1)
				
				found = None
				for func in funclist :
					if search_func == func.name :
						found = func
						if found.type != globalvar.FUNC_TYPES.public :
							break
							
				if not found :
					return None
					
				return found.return_tag
			
			def replace_func(match):
				varname = match.group(2)
				tag = search_vartag(varname, text)
				
				if tag :
					return tag+':'+match.group(2)
					
				return match.group(2)

			return re.sub(r'\s+(auto|:):([a-zA-Z_]\w*)', replace_func, text)
			
		
		for inc in includes :
			text = findreplace.read_text(inc)
			
			newtext = replace_autotag(text)
			
			if newtext != text :
				try:
					findreplace.write_text(newtext, inc)
				except Exception as e:
					print("autotag error:", e)

	#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	#:: ToolTip ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	def on_hover(self, view, point, hover_zone):
	
		scope = view.scope_name(point)
		self.debug_event("on_hover() -> view:[%d] - scope_name:[%s]" % (view.id(), scope))
		debug.debug(debug.FLAG_SHOW_SCOPE, "on_hover() -> scope_name: [%s]" % scope)
	
		if not is_amxmodx_view(view) or not cfg.enable_tooltip or hover_zone != sublime.HOVER_TEXT:
			return
			
		if not "support.function.pawn" in scope and not "variable.function.pawn" in scope and not "meta.preprocessor.include.path" in scope and not "storage.modifier.tag" in scope:
			view.hide_popup()
			return

		if "meta.preprocessor.include.path" in scope :
			self.tooltip_include(view, point)
			
		elif "storage.modifier.tag" in scope :
			self.tooltip_tag(view, point)
		elif "variable.function.pawn" in scope :
			self.tooltip_function(view, point, True)
		else :
			self.tooltip_function(view, point, False)
		
	def tooltip_include(self, view, point):
	
		line 		= view.substr(view.line(point))
		include 	= CodeAnalyzer.Regex_FIND_INCLUDE.match(line).group(2).strip()


		(file_path, exists) = globalvar.analyzer.get_include_path(util.get_filename_by_view(view), include)
		if not exists :
			return

		location_data = file_path + "##1"
		if not '.' in include :
			webapi_data = include + "#"
			include += ".inc"
		else :
			webapi_data = None
			
		header = ""
		if webapi_data :
			header += '<a href="webapi:'+webapi_data+'">WebAPI</a><span class="separator">|</span>'
		header += '<a href="goto:'+location_data+'">'+include+'</a>'
	
		content =  '<h3 class="heading">Location:</h3>'
		content += '<b class="path">%s</b>' % file_path

		self.tooltip_show_popup(view, point + 1, "tooltip-include", header, content)

	def tooltip_tag(self, view, point, search_tag=None):
		
		if not search_tag :
			word_region = view.word(point)
			search_tag  = view.substr(word_region)
			
		found 		= None
		node 		= get_view_node(view)
		
		if not node :
			return

		references = node.cache_all_tags.get(search_tag)
		if not references :
			return
			
		content =  ""
		header = '<a href="find_all:'+search_tag+'">Search All</a>'
			
		enumtag = references.get("enum")
		if enumtag :
			location_data = enumtag.file_path + '#' + search_tag + '#' + str(enumtag.line)
			header += '<span class="separator">|</span><a href="goto:'+location_data+'">Go to Enum</a>'
	
		includes = sorted(references)
		for inc in includes :
			if inc == "enum":
				continue
				
			content += '<b>%s:</b><br>' % inc
			
			funclist = sorted(references[inc], key=lambda func: func.start_line)
			for func in funclist :
				# <a class="btn copy" href="copy:{funcname}">copy</a>
				
				content += '<div class="itemrow"><a class="btn insert" href="snippet:{autocomplete}">insert</a> <a class="funcname" href="goto:{location}">{funcname}</a></div>'.format(
					funcname=func.name,
					autocomplete=func.autocomplete,
					location= "%s#%s#%d" % (func.file_path, func.name, func.start_line)
				)
			
		self.tooltip_show_popup(view, point + 1, "tooltip-tag", header, content)
		
	def tooltip_function(self, view, point, funcCall):
		
		word_region = view.word(point)
		search_func = view.substr(word_region)
		found 		= None
		node 		= get_view_node(view)
		
		if not node :
			return

		funclist = node.generate_list("funclist", set)
		
		for func in funclist :
			if search_func == func.name :
				found = func
				if found.type != globalvar.FUNC_TYPES.public :
					break
				
		if not found :
			return
			
		filename = os.path.basename(found.file_path)
		
		location_data = found.file_path + '#' + found.name + '#' + str(found.start_line)
		webapi_data = ""
			
		if found.type != globalvar.FUNC_TYPES.function and cfg.include_dir == os.path.dirname(found.file_path) :
			webapi_data = filename.rsplit('.', 1)[0] + '#' + found.name

		header = '<a href="find_all:'+search_func+'">Search All</a>'
		if webapi_data:
			header += '<span class="separator">|</span><a href="webapi:'+webapi_data+'">WebAPI</a>'
		header += '<span class="separator">|</span><a href="goto:'+location_data+'">'+filename+'</a>'
		
		return_tag = found.return_tag
		return_array = found.return_array

		content = ''
		if found.type :
			content += '<span class="pawnKeyword"><b>'+globalvar.FUNC_TYPES[found.type]+'</b></span>&nbsp;&nbsp;'
		if return_tag :
			content += '<a class="pawnTag" href="showtag:'+return_tag+'">'+return_tag+':</a>'
		if return_array :
			content += return_array
		content += '<span class="pawnFunction">'+found.name+'</span>' + tooltip.pawn_highlight('('+found.parameters+')')
		content += '<br>'
	
		if funcCall and found.param_list :
			(row, col) = view.rowcol(point)
			line = view.substr(view.line(point)).rstrip()
			text = line[line.find('(', col):]
			
			arguments = tooltip.parse_current_arguments(text)
			maxlen = len(max(found.param_list, key=len)) + 1
	
			if len(arguments) >= 1 :
				content += '<br>'
				content += '<span class="inspecTitle">Parameters:</span>'
				content += '<br><code class="inspecBlock">'
			
				i = 0
				for value in arguments :
				
					if i < len(found.param_list) :
						param = found.param_list[i]
					else :
						param = "..."
				
					param = param.ljust(maxlen).replace(" ", "&nbsp;")
		
					content += '- '+ param +':&nbsp;'+ tooltip.pawn_highlight( value )
					content += '<br>'
					
					i += 1
					
				content += '</code>'
			elif len(found.parameters) > 90 :
				content += '<br><br>'
			
		self.tooltip_show_popup(view, point + 1, "tooltip-function", header, content)
			
	def tooltip_on_click(self, src):
	
		view = sublime.active_window().active_view()

		print("on_url_click:", src)
		
		(cmd, data) = src.split(':', 1)

		if cmd == "find_all" :
			global g_fix_view
			g_fix_view = True
			sublime.active_window().run_command("amxx_find_replace", { "find_replace": data } )
			
		elif cmd == "webapi" :
			(include, function) = data.split('#')
			webbrowser.open_new_tab("http://www.amxmodx.org/api/%s/%s" % (include, function)) 
		
		elif cmd == "goto" :
			(file, search, line_row) = data.split('#')
			util.goto_definition(file, search, int(line_row)-1, False)
		
		elif cmd == "copy" :
			sublime.set_clipboard(data)
		
		elif cmd == "insert" :
			view.run_command("reindent")
			view.run_command("insert", {"characters": data, 'scroll_to_end': True })
			
		elif cmd == "snippet" :
			view.run_command("reindent")
			view.run_command('insert_snippet', {"contents": data})

		elif cmd == "showtag" :
			self.tooltip_tag(view, -1, data)
			return

		view.hide_popup()
			
	def tooltip_show_popup(self, view, location, classname, header="", content="", bottom=""):


		import math
		normal_size = view.settings().get("font_size", 9) + 1
		micro_size = math.floor(normal_size * 0.7)
		small_size = math.floor(normal_size * 0.85)
		large_size = math.ceil(normal_size * 1.25)
		
		print("font size: micro(%d) small(%d) normal(%d) large(%d)" % (micro_size, small_size, normal_size, large_size) )
		
		html  = """<body id="amxx-editor" class="%(classname)s">
<style>
html {
	--micro-size: %(micro_size)spx;
	--small-size: %(small_size)spx;
	--normal-size: %(normal_size)spx;
	--large-size: %(large_size)spx;
}
%(popupcss)s
%(syntaxcss)s
</style>
<div class="header">%(header)s</div>
<div class="content">%(content)s</div>
<div class="bottom">%(bottom)s</div>
</body>
""" % {
			"micro_size": micro_size,
			"small_size": small_size,
			"normal_size": normal_size,
			"large_size": large_size,
			"popupcss": globalvar.cachePopupCSS,
			"syntaxcss": globalvar.cacheSyntaxCSS,
			"classname": classname,
			"header": header,
			"content": content,
			"bottom": bottom
		}
		
		if location < 1 and view.is_popup_visible() :
			view.show_popup(html, 0, self.last_popup_location, max_width=800, on_navigate=self.tooltip_on_click)
		else :
			self.last_popup_location = location
			view.show_popup(html, sublime.HIDE_ON_MOUSE_MOVE_AWAY, location, max_width=800, on_navigate=self.tooltip_on_click)


	#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	#:: Fix Bug on Selection :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	def on_selection_modified(self, view):
		
		if not is_amxmodx_view(view) :
			return

		regions = [ ]

		for sel_region in view.sel() :
			for r in view.get_regions("pawnconst") :
				intersect = sel_region.intersection(r)
				if not intersect.empty() :
					regions.append(intersect)

		view.add_regions("fix_selection", regions, "fixselection", "", sublime.HIDE_ON_MINIMAP|sublime.DRAW_NO_OUTLINE)


	"""
		return
			
		region = view.sel()[0]
		if region.size() > 1 :
			return
			
		return
			
		print("on_selection_modified:", view.id())
		
		point = region.begin()
		
		(row, col) = view.rowcol(point)
		line = view.substr(view.line(point)).rstrip()
		

		left = line[0:col]
		rigth = line[col:]
		

		print("line: [%s]" % line)
		print("left:[%s], rigth:[%s]" % (left, rigth))
		
		
		print(line.rfind("(", 0, col))
		
		# rigth
		
		#print("character:[%s]" % view.substr(point).strip())
		#print("word:[%s]" % view.substr( view.word(point - 1) ) )
		

		
		if view.is_popup_visible() :
			return
			
		view.show_popup("(...param2=-1, const param3[]='')", 0, point, 800, 800, None, self.on_hide_popup)
		 
	def on_hide(self):
		print("on_hide() popup")
		
	--------------------------------------------------
	
			if view.style_for_scope("")['source_line'] == -1 :
			
			
			
			p = sublime.Phantom(sublime.Region(1, 2), 'we <b>hola</b> <br> asd', sublime.LAYOUT_INLINE, on_navigate=self.on_navigate)

			updater = sublime.PhantomSet(view, "daa")
			
			updater.update([ p ])
		
			
			
			view.erase_phantoms("mytest")
			view.add_phantom("mytest", sublime.Region(0, 0), "<b>B</b>", sublime.LAYOUT_INLINE, on_navigate=None)
			
			view.show_popup("<b>Popup xd</b>", sublime.COOPERATE_WITH_AUTO_COMPLETE, 15, max_width=800)
			
			#view.add_phantom("mytest", sublime.Region(0, 0), "<b>B</b>", sublime.LAYOUT_INLINE, on_navigate=None)
			
			print("add Phantom")

	
	"""
	

	#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	#:: Auto-Completions :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	def on_query_completions(self, view, prefix, locations):
		
		if not is_amxmodx_view(view) or not cfg.ac_enable or len(locations) > 1:
			return None
			
		if view.match_selector(locations[0], 'source.sma string') and prefix[0] != '@' :
			return ([ ], sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
				
		word_location = view.word(locations[0])
		word = view.substr(word_location)
		self.debug_event("on_query_completions() -> prefix:[%s] - word:[%s] - location:[%d]" % (prefix, word, locations[0]))
		
		#print("on_query_completions() -> prefix:[%s] - word:[%s] - location:[%d]" % (prefix, word, locations[0]))
		
		fullLine = view.substr(view.full_line(locations[0])).strip()
		if fullLine[0] == '#' :

			if fullLine.startswith("#include") or fullLine.startswith("#tryinclude"):
				return ( ac.generate_includes_list(cfg.profiles[cfg.default_profile]['includes_list'], fullLine), sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)

			if fullLine.startswith("#emit"):
				return ( ac.cache_emit, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
				
			pos = fullLine.rfind(prefix)
			if pos != -1 and fullLine.find(" ", 0, pos) == -1:
				return ( ac.cache_preprocessor, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
				
			return ([ ], sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)

		#if len(prefix) > 1 :
		#	return None
		
		line 		= view.rowcol(locations[0])[0] + 1
		file_path 	= util.get_filename_by_view(view)
		node 		= globalvar.nodes.get(file_path)
		if not node :
			return None
			
		#firstChar = view.substr(sublime.Region(word_location.begin()-1, word_location.begin()))
		if prefix[0] == '@' :
		
			if view.match_selector(locations[0], 'source.sma string') :
				def format_autocomplete(func, curnode, outObj, valueObj):
					if func.type == globalvar.FUNC_TYPES.public :
						return ( ac.format_autocomplete(curnode, "@ " + func.name, "public"), func.name )
					return ( None, None )

				funclist = node.generate_list("funclist", set, format_autocomplete)
	
				return (funclist, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
				
			else :
				def format_autocomplete(value, curnode, outObj, valueObj):
					return ( ac.format_autocomplete(curnode, "@ %s:" % value, "tag"), "%s:" % value )
		
				tags = node.generate_list("tags", set, format_autocomplete)
				tags.add(("@ auto:", "auto:"))
				tags.add(("@ bool:", "bool:"))
				tags.add(("@ Float:", "Float:"))
				
				return (tags, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
		
		if fullLine.startswith("new ") or fullLine.startswith("static ") or fullLine.startswith("for") :
		
			(row, col) = view.rowcol(locations[0])
			text = view.substr(view.full_line(locations[0]))[0:col]
			
			pos = text.find("new ")
			if pos == -1 :
				pos = text.find("static ")
			if pos != -1 and ac.block_on_varname(text[pos+4:]) :
				return ([ ], sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)

		debug.performance.init("total2")

		completions = []
	
		completions.extend(node.cache_autocomplete)
		
		if cfg.ac_local_var :
			completions.extend(ac.generate_local_vars_list(node, line))
		if cfg.ac_keywords :
			completions.extend(ac.cache_keywords)
		if cfg.ac_snippets :
			completions.extend(ac.cache_snippets)
		
		final_list = [ ]

		if cfg.ac_explicit_mode :
			for item in completions :
				if item[0][0] == prefix[0] :
					final_list += [ item ]
		else :
			final_list = completions

		if cfg.ac_extra_sorted :
			final_list = ac.sorted_nicely(final_list)
			
		return (final_list, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)

#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

#:: Update Popup CSS on active style modified :::::::::::::::::::::::::::::::::::::::::
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
class PopupFileEventHandler(watchdog.events.FileSystemEventHandler):

	def __init__(self):
		watchdog.events.FileSystemEventHandler.__init__(self)

	def on_modified(self, event):
		if os.path.basename(event.src_path) == os.path.basename(g_style_popup['path'][g_style_popup['active']]) :
			update_popup_style()


#:: Analyzer Queue Thread :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
class IncludeFileEventHandler(watchdog.events.FileSystemEventHandler):

	def __init__(self):
		watchdog.events.FileSystemEventHandler.__init__(self)

	# If file is in used, update it.
	def on_created(self, event):
		if event.src_path in globalvar.nodes :
			globalvar.analyzerQueue.add_to_queue(event.src_path)
			
		# Add to Autocomplete
		profile = cfg.profiles[cfg.default_profile]
		if profile['include_dir'] in event.src_path and event.src_path.endswith(".inc") :
			inc = event.src_path.replace(profile['include_dir'], "").lstrip("\\/").replace("\\", "/").replace(".inc", "")
			profile['includes_list'].append(inc)
			print("Add include:", inc, " -> ", event.src_path)
		

	def on_modified(self, event):
		if event.src_path in globalvar.nodes :
			globalvar.analyzerQueue.add_to_queue(event.src_path)

	# If file not has a open view, free the memory ( remove children ).
	def on_deleted(self, event):
		if util.get_open_view_by_filename(event.src_path) :
			return

		node = globalvar.nodes.get(event.src_path)
		if not node :
			return

		node.remove_all_children_and_clear()
		
#:: Monitor on Scrolled Thread ::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
class MonitorScrolledThread(threading.Thread):

	viewport_oldpos = { }

	def __init__(self):
		threading.Thread.__init__(self)

		self.daemon = True
		self.stoped = False
	
		self.start()
		
	def run(self):
		while not self.stoped:
			self.monitor_scrolled()
			time.sleep(1.0)

	def monitor_scrolled(self):
		view = sublime.active_window().active_view()
		if not view or not is_amxmodx_view(view) :
			return
			
		viewid = view.id()
		pos = view.viewport_position()[1]
		
		if self.viewport_oldpos.get(viewid) == None :
			self.viewport_oldpos[viewid] = pos
		elif self.viewport_oldpos[viewid] != pos :
			self.viewport_oldpos[viewid] = pos
			self.on_scrolled(view)
			
	def on_scrolled(self, view):
		if cfg.enable_const_highlight :
			constants_highlight(view, False)
			invalid_functions_highlight(view, False)

	def stop(self):
		self.stoped = True

#:: Analyzer Queue Thread :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
class AnalyzerQueueThread(threading.Thread):

	def __init__(self):
		threading.Thread.__init__(self)
		
		self.daemon = True
		self.stoped = False
		
		self.queue = OrderedSetQueue()
		self.delayed = DelayedTimer(2, self.add_to_queue)

		self.start()
		
	def run(self):
	
		while not self.stoped :

			(file_path, view_id) = self.queue.get()

			if self.stoped :
				return
			
			view = None
			
			if view_id :
				view = sublime.View(view_id)
				if not view.is_valid() :
					continue
		
			if view :
				buffer = view.substr(sublime.Region(0, view.size()))
				file_path = util.get_filename_by_view(view)
			else :
				with open(file_path, 'r', encoding="utf-8", errors="replace") as f :
					buffer = f.read()
			
			globalvar.analyzer.process(view, file_path, buffer)
			"""try :
				globalvar.analyzer.process(view, file_path, buffer)
			except Exception as e:
				debug.error("analyzer.process() -> Exception:", e)
			"""
				
	def stop(self):
		self.delayed.stop()
		self.stoped = True
		self.queue.put( (None,None) )

	def add_to_queue(self, file_path, view_id=None):
		self.queue.put(( file_path, view_id ))
		
	def add_to_queue_delayed(self, view):
		self.delayed.update_args(None, view.id())
		self.delayed.touch(False)

	@property
	def delay(self):
		return self.delayed.delay_time
			
	@delay.setter
	def delay(self, value):
		self.delayed.delay_time = value


#:: Code Analyzer ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class  CodeAnalyzer:

	Regex_FIND_INCLUDE 		= re.compile(r'^[\t ]*(#include\s+[<"]([^>"]+)[>"])', re.M)
	Regex_LOCAL_INCLUDE 	= re.compile(r'\.(sma|inc|inl)$')
	Regex_FIND_FUNC 		= re.compile(r'^(stock |public )?(\w*:)?([A-Za-z_][\w_]*)\s*\(', re.M)

	debug.performance.init("total")
	debug.performance.init("generate_sections")
	
	def __init__(self):
		pass
	
	def process(self, view, file_path, buffer):
		
		(current_node, is_added) = NodeBase.get_or_add(file_path)
	
		includes_used = set()
		error_regions = [ ]

		for match in self.Regex_FIND_INCLUDE.finditer(buffer):
			exists = self.load_include_file(file_path, match.group(2).strip(), current_node, current_node, includes_used)
			if view and not exists :
				error_regions.append(sublime.Region(match.start(1), match.end(1)))

		for removed_node in current_node.children.difference(includes_used) :
			current_node.remove_child(removed_node)

		self.process_parse(view, buffer, None, current_node, error_regions)
	
	def process_parse(self, view, buffer, pFile, node, error_regions=[]):
		
		#:: Debug Performance :::::::::::::::::
		debug.performance.start("total", True)
		debug.performance.clear("pawnparse")
		debug.performance.clear("enum")
		debug.performance.clear("var")
		debug.performance.clear("func")
		#::::::::::::::::::::::::::::::::::::::

		debug.info("(Analizer) Starting parser: -> \"%s\"" % node.file_name)
		
		#:: Parse include file ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
		if pFile :
			data = globalvar.parse.process(pFile, node)
			
			node.autocomplete = data.autocomplete
			node.funclist = data.funclist
			node.constants = data.constants
			node.tags = data.tags
			
			debug.info("(Analizer) Finished: -> Total: %.3fsec\n" % debug.performance.end("total") )
			return
		#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
		
		# MultiThreads problem :S ( view was closed while it is processed )
		if not view or not view.is_valid() :
			return
				
		# Code separated into sections
		debug.performance.start("generate_sections", True)
		new_sections = self.generate_sections(view, buffer)
		debug.performance.end("generate_sections")
		
		# Parse new sections
		difference = new_sections - node.old_sections
		for section in difference :
		
			# MultiThreads problem :S ( view was closed while it is processed )
			if not view or not view.is_valid() :
				return
			
			line = view.rowcol(section.begin)[0] # Insecure thread buffer
			node.parse_data[section] = globalvar.parse.process( TextReader( buffer[section.begin:section.end] ), node, line)


		# Delete old data
		for old in node.old_sections - new_sections :
			del node.parse_data[old]
		node.old_sections = new_sections
			
		# Crear and Update node data
		node.autocomplete.clear()
		node.funclist.clear()
		node.constants.clear()
		node.tags.clear()


		for section in new_sections :
		
			# MultiThreads problem :S ( view was closed while it is processed )
			if not view or not view.is_valid() :
				return
				
			data = node.parse_data[section]
			baseline = view.rowcol(section.begin)[0] # Insecure thread buffer
			
			node.autocomplete.extend(data.autocomplete)
			node.constants.update(data.constants)

			for func in data.funclist :
				func.update_line(baseline) # Update current line position, used for autocomplete and tooltip
			node.funclist.update(data.funclist)
			
			for tagname in data.tags :
				data.tags[tagname].update_line(baseline)
				
			for tagname in data.tags :
				tagA = node.tags.get(tagname)
				tagB = data.tags[tagname]

				if not tagA :
					node.tags[tagname] = tagB
					continue
					
				if tagB.funclist :
					tagA.funclist.update(tagB.funclist)
					
				if tagB.isenum :
					tagA.file_path 		= tagB.file_path
					tagA.line_offset 	= tagB.line_offset
					tagA.line			= tagB.line
				
			# Mark error lines
			for error in data.error_lines :
				start_line	= baseline + error[0] - 1
				end_line	= baseline + error[1]
				
				begin = view.text_point(start_line, 0)
				end = view.text_point(end_line, 0)
				end = view.line(end).end()

				error_regions.append(sublime.Region(begin, end))
			
		
		# Organize and Cache data
		debug.performance.init("organize_and_cache")
		node.organize_and_cache()
		debug.performance.end("organize_and_cache")

		# Show errors
		if cfg.enable_marking_error :
			marking_error_lines(view, error_regions)
		
		
		#:: View Debug Mode :::::::::::::::::::::::::
		if "z" in cfg.debug_flags :
			r_color1 = [ ]
			r_color2 = [ ]
			color = False
			
			for section in sorted(new_sections, key=lambda o: o.begin) :
				color = not color
				if color :
					r_color1.append(sublime.Region(section.begin, section.end))
				else:
					r_color2.append(sublime.Region(section.begin, section.end))
					
			view.add_regions("color1", r_color1, "region.greenish", "", 0)
			view.add_regions("color2", r_color2, "region.pinkish", "", 0)
			
			cfg.view_debug_mode = True
			
		elif cfg.view_debug_mode :
			view.erase_regions("color1")
			view.erase_regions("color2")
			
			cfg.view_debug_mode = False
		#::::::::::::::::::::::::::::::::::::::
			
		# Compile regex of constants
		debug.performance.init("const")
		node.Regex_CONST		= self.compile_constants(node.constants)
		node.Regex_CONST_CHILD	= self.compile_constants(node.generate_list("constants", set, skip_self=True))
		debug.performance.end("const")
		
		# MultiThreads problem :S ( view was closed while it is processed )
		if not view or not view.is_valid() :
			return
				
		# Dynamic Highlight
		debug.performance.init("highlight")
		if cfg.enable_const_highlight :
			constants_highlight(view, True)
			invalid_functions_highlight(view, True)
		debug.performance.end("highlight")


		#:: Debug performance :::::::::::::::::
		debug.dev(" (Analizer) Generate %d sections: %.3fsec  -  Region-Highlight: %.3fsec" % (len(new_sections), debug.performance.end("generate_sections"), debug.performance.end("highlight")) )
		debug.dev(" (Analizer) Parsing %d sections: %.3fsec" % (len(difference), debug.performance.end("pawnparse")) )
		debug.info("(Analizer) Enum: %.3fsec - Vars: %.3fsec - Func: %.3fsec - Constant: %.3fsec" % (
			debug.performance.end("enum"),
			debug.performance.end("var"),
			debug.performance.end("func"),
			debug.performance.end("const")
		))
		debug.dev(" (Analizer) Organize And Cache data: %.3fsec" % debug.performance.end("organize_and_cache"))
		debug.dev(" (Analizer) %s" % debug_instances_info())
		debug.info("(Analizer) Finished: -> Total: %.3fsec\n" % debug.performance.end("total") )
		#::::::::::::::::::::::::::::::::::::::
		

		
	def compile_constants(self, constlist):
	
		constants = "___test"
		for const in constlist :
			constants += "|" + const

		pattern = "\\b(" + constants + ")\\b"
		
		return re.compile(pattern)
	
	def generate_sections(self, view, buffer):
	
		sections = set()
		begin_point = 0
		
		# View buffer may change while this function is running. Therefore, view.find_by_selector() is insecure.
		for match in self.Regex_FIND_FUNC.finditer(buffer):
		
			point = match.start()
			scope = view.scope_name(point + round((match.end() - point) / 2))
			# If view buffer is changed, usually differs a few characters, so have the half of length match as compensation.
			if "comment" in scope or "string" in scope :
				continue

			sections.add( SectionData(begin_point, point - 1, buffer) )
			
			begin_point = point
	
		sections.add( SectionData(begin_point, len(buffer), buffer) )

		return sections

	def load_include_file(self, parent_file_path, include, parent_node, base_node, includes_used):
	
		(file_path, exists) = self.get_include_path(parent_file_path, include)
		
		if not exists :
			debug.info("Include File not found: inc[\"%s\"],  file[\"%s\"] - parent[\"%s\"]" % (include, file_path, parent_file_path))
			return
			
		(node, is_added) = NodeBase.get_or_add(file_path)
		parent_node.add_child(node)

		if parent_node == base_node :
			includes_used.add(node)

		if not is_added:
			return exists

		with open(file_path, 'r', encoding="utf-8", errors="replace") as file :
			includes = self.Regex_FIND_INCLUDE.findall(file.read())

		for include in includes :
			self.load_include_file(parent_file_path, include[1].strip(), node, base_node, includes_used)

		with open(node.file_path, 'r', encoding="utf-8", errors="replace") as file :
			debug.info("Processing Include File \"%s\"" % file_path)
			self.process_parse(None, None, file, node)
			
		return exists

	def get_include_path(self, parent_file_path, include):
	
		exists = False

		if self.Regex_LOCAL_INCLUDE.search(include) :
			file_path	= os.path.join(os.path.dirname(parent_file_path), include)
			exists		= os.path.exists(file_path)
		
		if not exists :
			if '.' in include :
				file_path	= os.path.join(cfg.include_dir, include)
			else :
				file_path	= os.path.join(cfg.include_dir, include + ".inc")
			exists		= os.path.exists(file_path)

		return (file_path, exists)
		

class TextReader:

	def __init__(self, text):
		self.text = text.splitlines()
		self.position = -1

	def readline(self) :
		self.position += 1

		if self.position < len(self.text) :
			retval = self.text[self.position]
			if retval == '' :
				return '\n'
			else :
				return retval
		else :
			return ''

class SectionData:
	def __init__(self, begin, end, buffer):
		s = buffer[begin:end]
		
		self.begin 	= begin
		self.end 	= end
		self.hash 	= hash(s)
		self.len 	= len(s)
		
	def __hash__(self):
		return self.hash

	def __eq__(self, other):
		return self.hash == other.hash and self.len == other.len
		
	def __repr__(self):
		return "<SectionData: begin=%d, end=%d, hash=%d, len=%d>" % ( self.begin, self.end, self.hash, self.len )
	
class NodeBase:

	def __init__(self, file_path, readonly=False):
	
		self.file_path 		= file_path
		self.file_name		= os.path.basename(file_path)
		self.readonly		= readonly
		
		self.children 		= set()
		self.parents 		= set()
		
		self.autocomplete 	= list()
		self.funclist 		= set()
		self.constants		= set()
		self.tags			= dict()
		
		self.parse_data		= dict()
		self.old_sections 	= set()
		
		self.Regex_CONST		= None
		self.Regex_CONST_CHILD	= None
		
		self.cache_all_tags	= None
		self.cache_autocomplete = None

	def add_child(self, node) :
		self.children.add(node)
		node.parents.add(self)

	def remove_child(self, node):
	
		self.children.remove(node)
		node.parents.remove(self)

		if len(node.parents) <= 0 :
			node.clear()
			globalvar.nodes.pop(node.file_path)

	def remove_all_children_and_clear(self):
	
		for child in self.children :
			self.remove_child(node)
		
	# unnecessary code ??? apparently python does it automatically
	def clear(self):
	
		self.autocomplete.clear()
		self.funclist.clear()
		self.constants.clear()
		self.tags.clear()
		
		self.parse_data.clear()
		self.old_sections.clear()
		
		self.cache_all_tags.clear()
		self.cache_autocomplete.clear()
		
		self.Regex_CONST = None
		self.Regex_CONST_CHILD = None
	
		
	### Generate recursive list: ########################
	# @property: Node property name.
	# @outclass: Out Class.
	# @custom_format: Custom format callback.   // def callback(value/key, curnode, outObj, valueObj):
	#####################################################
	def generate_list(self, property, outclass=list, custom_format=None, skip_self=False):
	
		assert issubclass(outclass, list) or issubclass(outclass, set) or issubclass(outclass, dict), "Invalid Class Type (only support base list/set)"
		
		out 	= outclass()
		visited = set()
		
		def recur_func(curnode) :
			if curnode in visited :
				return

			visited.add(curnode)
			for child in curnode.children :
				recur_func(child)

			value = getattr(curnode, property)
			
			if issubclass(outclass, list):
				out.extend(value if not custom_format else map(lambda v:custom_format(v, curnode, out, value), value))
			elif issubclass(outclass, set) :
				out.update(value if not custom_format else map(lambda v:custom_format(v, curnode, out, value), value))
			elif custom_format :
				for key in value :
					custom_format(key, curnode, out, value)
			else :
				assert issubclass(outclass, dict) and custom_format, "`dict` only work using a custom format callback"
				
		if skip_self :
			visited.add(self)
			for child in self.children :
				recur_func(child)
		else :
			recur_func(self)

		return out
		
	def organize_and_cache(self):
	
		# Auto-complete
		if self.cache_autocomplete :
			self.cache_autocomplete.clear()
		
		self.cache_autocomplete = ac.generate_autocomplete_list(self)
		
		# Tags
		if self.cache_all_tags :
			self.cache_all_tags.clear()
		
		def organize_tags_data(key, curnode, outObj, valueObj):

			a = outObj.get(key)
			b = valueObj[key]
			
			if not a :
				a = dict()
				outObj[key] = a
				
			if b.funclist :
				a[curnode.file_name] = b.funclist

			if b.isenum :
				a['enum'] = b

		self.cache_all_tags = self.generate_list("tags", dict, organize_tags_data)

	@staticmethod
	def get_or_add(file_path):
	
		node = globalvar.nodes.get(file_path)
		
		if node is None :
		
			readonly = False
			for d in globalvar.include_dirs :
				if d in file_path :
					readonly = True
					break
			
			node = NodeBase(file_path, readonly)
			globalvar.nodes[file_path] = node
			return (node, True)

		return (node, False)


def get_view_node(view):
	return globalvar.nodes.get(util.get_filename_by_view(view))

def generate_highlight(view, key, pattern_or_regex, scope, flags=0, check_scope_callback=None, clear=True):

	visible_region = view.visible_region()

	line_start 	= view.rowcol(visible_region.begin())[0]
	line_end 	= view.rowcol(visible_region.end())[0]
		
	extra_lines = round((line_end - line_start) / 2)
		
	line_start 	-= extra_lines
	line_end 	+= extra_lines
		
	visible_region = sublime.Region(view.text_point(line_start, 0), view.text_point(line_end, 0))
		
	buff = view.substr(visible_region)
		
	regions = [ ]
	
	if isinstance(pattern_or_regex, str) :
		iterator = re.finditer(pattern_or_regex, buff)
	else :
		iterator = pattern_or_regex.finditer(buff)
	
	for match in iterator:
	
		s = match.start() + visible_region.begin()
		e = match.end() + visible_region.begin()
		
		if not check_scope_callback or check_scope_callback(view.scope_name(s), match.group(0)) :
			regions.append(sublime.Region(s, e))

	if not clear :
		regions.extend(view.get_regions(key))
		
	view.add_regions(key, regions, scope, "", flags)


def constants_highlight(view, clear=True):

	node = get_view_node(view)
	if not node or not node.Regex_CONST or not node.Regex_CONST_CHILD :
		return
	

	def check_scope(scope, word):
		return scope == "source.sma "

	generate_highlight(view, "pawnconst", node.Regex_CONST, "constant.vars.pawn", sublime.HIDE_ON_MINIMAP|sublime.DRAW_NO_OUTLINE, check_scope, clear)
	generate_highlight(view, "pawnconst", node.Regex_CONST_CHILD, "constant.vars.pawn", sublime.HIDE_ON_MINIMAP|sublime.DRAW_NO_OUTLINE, check_scope, False)


def invalid_functions_highlight(view, clear=True):

	if not cfg.enable_marking_error :
		return
		
	node = get_view_node(view)
	if not node :
		return
		
	def get_name(func, curnode, outObj, valueObj):
		return func.name

	funclist = node.generate_list("funclist", set, get_name)
			
	def check_scope(scope, word):
		if scope != "source.sma variable.function.pawn " :
			return False
			
		if word in funclist :
			return False
			
		return True

	generate_highlight(view, "invalidfunc", r"\b[A-Za-z_][\w_]*\b", "invalid.illegal", sublime.DRAW_NO_OUTLINE|sublime.DRAW_NO_FILL|sublime.DRAW_SQUIGGLY_UNDERLINE, check_scope, clear)	

def is_amxmodx_view(view) :
	return view.match_selector(0, 'source.sma') and not g_invalid_settings

def marking_error_lines(view, regions):
	view.add_regions("pawnerror", regions, "invalid.illegal", "dot", sublime.DRAW_NO_OUTLINE|sublime.DRAW_NO_FILL|sublime.DRAW_SQUIGGLY_UNDERLINE)

def clear_error_lines(view):
	view.erase_regions("pawnerror")


