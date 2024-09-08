# Sublime AMXXPawn-Editor 4.0 by Destro

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
import watchdog.events
import watchdog.observers
from watchdog.utils.bricks 	import OrderedSetQueue
from pathtools.path 		import list_files

# Core AMXXPawn-Editor.
from AMXXcore.core 			import *
from AMXXcore.completions 	import *
from AMXXcore.find_replace 	import *
from AMXXcore.pawn_parse 	import pawnParse
import AMXXcore.tooltip 	as tooltip
import AMXXcore.debug 		as debug



#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# Global VARs & Initialize
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	
var.EDITOR_VERSION 		= "4.1"
var.FUNC_TYPES 			= Enum( [ "function", "public", "stock", "forward", "native" ] )

var.nodes 				= dict()
var.constants_list 		= set()

g_style_popup 		= { "list": [ ], "path": { }, "active": "" }
g_style_editor 		= { "list": [ ], "path": { }, "active": "" }
g_style_console 	= { "list": [ ], "path": { }, "active": "" }

g_invalid_settings	= False
g_edit_settings 	= False
g_check_update		= False
g_fix_view			= False


def plugin_loaded() :

	# Log
	debug.log_open( os.path.join(BASE_PATH, "debug.log") )
	
	# MultiThreads start
	var.analyzerQueue			= AnalyzerQueueThread()
	var.monitorScrolled			= MonitorScrolledThread()
	var.incFileEventHandler		= IncludeFileEventHandler()
	var.watchDog 				= watchdog.observers.Observer()
	var.watchDog.start()
	
	# Code Analyzer/Parse
	var.analyzer 				= CodeAnalyzer()
	var.parse 					= pawnParse(var.analyzerQueue)
				
	# Config
	cfg.init(on_config_change)
	
	# NOTA: Mejorar, asegurarse de comprobar el tiempo entre cada chekeo 
	#sublime.set_timeout_async(check_update, 2500)

def plugin_unloaded() :

	# MultiThreads Stop
	var.watchDog.stop()
	var.analyzerQueue.stop()
	var.monitorScrolled.stop()
	
	# Log
	debug.log_close()
	
def on_config_change() :

	# Check package folder
	packages_path = os.path.join(sublime.packages_path(), "amxmodx")
	if not os.path.isdir(packages_path) :
		os.mkdir(packages_path)

		
	# Profiles
	cfg.default_profile		= cfg.get('default_profile', "")
	cfg.profiles 			= cfg.get("build_profiles", None)
	if not cfg.profiles :
		validate_profile("", None)
		print("ERROR: if not cfg.profiles")
		return
		
	cfg.profiles_list = list(cfg.profiles.keys())

	for profile_name in cfg.profiles_list :
		profile = cfg.profiles[profile_name]
		if not validate_profile(profile_name, profile) :
			return
			
		# Fix values
		profile['output_dir'] 		= util.cfg_get_path(profile, 'output_dir')
		profile['includes_dir'] 	= util.cfg_get_path(profile, 'includes_dir')
		profile['amxxpc_path'] 		= util.cfg_get_path(profile, 'amxxpc_path')
		profile['amxxpc_debug'] 	= util.clamp(int(profile['amxxpc_debug']), 0, 2)

	if not cfg.default_profile in cfg.profiles_list :
		cfg.default_profile = cfg.profiles_list[0]
		

	# Cache settings
	cfg.enable_tooltip 			= cfg.get('enable_tooltip', True)
	cfg.enable_buildversion 	= cfg.get('enable_buildversion', True)

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
	cfg.include_dir 			= cfg.profiles[cfg.default_profile]['includes_dir']
	
	# Update Live reflesh delay.
	var.analyzerQueue.delay	= util.clamp(float(cfg.get('live_refresh_delay', 1.5)), 0.5, 5.0)
	
	
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
	
	
	var.watchDog.unschedule_all()

	for profile_name in cfg.profiles_list :
		if list_includes(cfg.profiles[profile_name]):
			var.watchDog.schedule(var.incFileEventHandler, cfg.profiles[profile_name]['includes_dir'], True)
			
	# AutoCompletions.Init()
	ac.init()
	
	
	# temp
	cfg.const_REGEX = None
#}


def list_includes(profile):
	
	bad_files = 0
	profile['includes_list'] = list()
	
	for inc in list_files(profile['includes_dir']) :
		if inc.endswith(".inc") :
			inc = inc.replace(profile['includes_dir'], "").lstrip("\\/").replace("\\", "/").replace(".inc", "")
			profile['includes_list'].append(inc)
		else : # big recursive loop in root folder  (example: C:\\ )
			bad_files += 1
			if bad_files >= 50 :
				debug.warning("Big recursive loop, include_dir: \"%s\"" % profile['includes_dir'])
				return False
				
	profile['includes_list'] = ac.sorted_nicely(profile['includes_list'])
	return True

def update_editor_style():
	if "default" == g_style_editor['active'] :
		newValue = None
	else :
		newValue = g_style_editor['path'][g_style_editor['active']]
		
	s = OpenSettings("AMXX-Pawn.sublime-settings")
	s.set("color_scheme", newValue)
	s.set("extensions",  [ "sma", "inc" ])
	s.save()
	
def update_console_style():
	if "default" == g_style_console['active'] :
		newValue = None
	else :
		newValue = g_style_console['path'][g_style_console['active']]
		
	util.cfg_set_key("AMXX-Console.sublime-settings", "color_scheme", newValue)
	
def update_popup_style():
	var.cache_tooltip_css = sublime.load_resource(g_style_popup['path'][g_style_popup['active']])
	var.cache_tooltip_css  = var.cache_tooltip_css .replace("\r", "") # Fix
	
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

	if not profile or not isinstance(profile, dict) or profile.get('amxxpc_path') == None or profile.get('amxxpc_debug') == None or profile.get('includes_dir') == None or profile.get('output_dir') == None :
		error += "Empty Value\n"
	elif not os.path.isfile(util.cfg_get_path(profile, 'amxxpc_path')) :
		error += "amxxpc_directory :  File does not exist.\n\"%s\"" % util.cfg_get_path(profile, 'amxxpc_path')
	elif not os.path.isdir(util.cfg_get_path(profile, 'includes_dir')) :
		error += "include_directory :  Directory does not exist.\n\"%s\"" % util.cfg_get_path(profile, 'includes_dir')
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
		default = sublime.load_resource("Packages/amxmodx/AMXX-Editor.sublime-settings")
		default = default.replace("Example:", "User Settings:")
		f = open(file_path, "w")
		f.write(default)
		f.close()

	sublime.set_timeout_async(run_edit_settings, 250)
	return False
	
def run_edit_settings() :
	sublime.active_window().run_command("edit_settings", {"base_file": "${packages}/amxmodx/AMXX-Editor.sublime-settings", "default": "{\n\t$0\n}\n"})



class AmxxProfileCommand(sublime_plugin.ApplicationCommand):
#{
	def run(self, index) :
	#{
		if index >= len(cfg.profiles_list) :
			return

		cfg.default_profile = cfg.profiles_list[index]
		
		cfg.set("default_profile", cfg.default_profile)
		cfg.save()
	#}

	def is_visible(self, index) :
		return (index < len(cfg.profiles_list))
		
	def is_checked(self, index) :
		return (index < len(cfg.profiles_list) and cfg.profiles_list[index] == cfg.default_profile)

	def description(self, index) :
		if index < len(cfg.profiles_list) :
			return cfg.profiles_list[index]
		return ""
#}


class AmxxEditorStyleCommand(sublime_plugin.ApplicationCommand):
#{
	def run(self, index) :
	#{
		if index >= len(g_style_editor['list']) :
			return
		
		g_style_editor['active'] = g_style_editor['list'][index]
		
		if g_style_editor['active'] in g_style_popup['list'] :
			cfg.set("style_popup", g_style_editor['active'])
		if g_style_editor['active'] in g_style_console['list'] :
			cfg.set("style_console", g_style_editor['active'])
		cfg.set("style_editor", g_style_editor['active'])
		
		cfg.save(False)
		
	#}

	def is_visible(self, index) :
		return (index < len(g_style_editor['list']))
		
	def is_checked(self, index) :
		return (index < len(g_style_editor['list']) and g_style_editor['list'][index] == g_style_editor['active'])

	def description(self, index) :
		if index < len(g_style_editor['list']) :
			return g_style_editor['list'][index]
		return ""
#}

class AmxxEditorStyleConsoleCommand(sublime_plugin.ApplicationCommand):
#{
	def run(self, index) :
	#{
		if index >= len(g_style_console['list']) :
			return

		g_style_console['active'] = g_style_console['list'][index]
		
		cfg.set("style_console", g_style_console['active'])
		cfg.save()
		
		update_console_style()
	#}

	def is_visible(self, index) :
		return (index < len(g_style_console['list']))
		
	def is_checked(self, index) :
		return (index < len(g_style_console['list']) and g_style_console['list'][index] == g_style_console['active'])

	def description(self, index) :
		if index < len(g_style_console['list']) :
			return g_style_console['list'][index]
		return ""
#}

class AmxxEditorStylePopupCommand(sublime_plugin.ApplicationCommand):
#{
	def run(self, index) :
	#{
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
#}

class AmxxNewIncludeCommand(sublime_plugin.WindowCommand):
	def run(self):
		new_file("inc")
class AmxxNewPluginCommand(sublime_plugin.WindowCommand):
	def run(self):
		new_file("sma")

def new_file(type):
#{
	view = sublime.active_window().new_file()

	view.set_syntax_file("AMXX-Pawn.sublime-syntax")
	view.set_name("untitled."+type)
	
	plugin_template = sublime.load_resource("Packages/amxmodx/default."+type)
	plugin_template = plugin_template.replace("\r", "")
	
	view.run_command("insert_snippet", {"contents": plugin_template})
#}
		
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
		fCurrentVersion = float(var.EDITOR_VERSION)
			
		if fCheckVersion == fCurrentVersion and bycommand:
			sublime.ok_cancel_dialog("AMXX: You are already using the latest version:  v"+ var.EDITOR_VERSION, "OK")
			
		if fCheckVersion > fCurrentVersion :
			msg  = "AMXX: A new version is available:  v"+ data[0]
			if len(data) > 1 :
				msg += "\n\nNews:\n" + data[1]
				
			ok = sublime.ok_cancel_dialog(msg, "Download Update")
			
			if ok :
				webbrowser.open_new_tab("https://amxmodx-es.com/showthread.php?tid=12316")
	#}
#}



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
			<b>ESPECIAL WORDs:</b>
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
			node 		= var.nodes[util.get_filename_by_view(view)]

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
			
			node = var.nodes[util.get_filename_by_view(view)]
			
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

<h1>Sublime AMXX-Editor v""" + var.EDITOR_VERSION + """ by Destro</h1>
<b>CREDITs:</b><br>
ppalex7 <i>(SourcePawn Completions)</i><br>
<br>
<b>- Contributors:</b><br>
sasske <i>(white color scheme)</i><br>
addons_zz <i>(npp color scheme)</i><br>
KliPPy <i>(build version)</i><br>
Mistrick <i>(mistrick color scheme)</i><br>

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

	#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	#:: Util Functions :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	def debug_event(self, *args):
		debug.debug(debug.FLAG_ST3_EVENT, "SublimeEVENT:", *args)
		
	def add_to_queue(self, view):
		if not is_amxmodx_view(view):
			return

		var.analyzerQueue.add_to_queue(None, view.id())

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
	def on_activated_async(self, view):
		# Prevent widget bug
		window = view.window()
		if not window :
			return
			
		fix_view = window.active_view()
		if not is_amxmodx_view(fix_view):
			return
			
		self.debug_event("on_activated_async() -> view:[%d] - fix-view:[%d] - fix-file:[%s]" % (view.id(), fix_view.id(), fix_view.file_name()) )
	
		if not util.get_filename_by_view(fix_view) in var.nodes :
			self.add_to_queue(fix_view)
		
	def on_post_save(self, view):
		self.debug_event("on_post_save() -> view:[%d] - file:[%s]" % (view.id(), view.file_name()))
		self.add_to_queue(view)

	def on_load(self, view):
		self.debug_event("on_load() -> view:[%d] - file:[%s]" % (view.id(), view.file_name()))
		self.add_to_queue(view)
	
	# Delayed
	def on_modified(self, view):
		
		if not is_amxmodx_view(view):
			return
			
		self.debug_event("on_modified() -> view:[%d] - file:[%s]" % (view.id(), view.file_name()))

		var.analyzerQueue.add_to_queue_delayed(view)
		
		mark_clear(view)

	#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	#:: Auto Build-Version :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	def on_window_command(self, window, cmd, args):

		self.debug_event("on_window_command() -> cmd:[%s] - arg:[%s]" % (cmd, args))
		
		if cmd != "build" :
			return
			
		p = cfg.profiles[cfg.default_profile]
		
		build = OpenSettings("AMXX-Compiler.sublime-build")
		build.set('cmd', [ p['amxxpc_path'], "-d"+str(p['amxxpc_debug']), "-i"+p['includes_dir'], "-o"+p['output_dir']+"/${file_base_name}.amxx", "${file}" ])
		build.set('syntax', 'AMXX-Console.sublime-syntax')
		build.set('selector', 'source.sma')
		build.set('working_dir', os.path.dirname(p['amxxpc_path']))
		build.save()
	
		view = window.active_view()
		if not is_amxmodx_view(view) or not cfg.enable_buildversion :
			return
			
		if not view.file_name() :
			view.run_command("save")
			
		view.run_command("amxx_build_ver")
		
	#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	#:: ToolTip ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	def on_hover(self, view, point, hover_zone):
	
		scope = view.scope_name(point)
		self.debug_event("on_hover() -> view:[%d] - scope_name:[%s]" % (view.id(), scope))
		debug.debug(debug.FLAG_SHOW_SCOPE, "on_hover() -> scope_name: [%s]" % scope)
	
		if not is_amxmodx_view(view) or not cfg.enable_tooltip or hover_zone != sublime.HOVER_TEXT:
			return
			
		if not "support.function.pawn" in scope and not "variable.function.pawn" in scope and not "meta.preprocessor.include.path" in scope :
			view.hide_popup()
			return

		if "meta.preprocessor.include.path" in scope :
			self.tooltip_include(view, point)
		else :
			self.tooltip_function(view, point)
		
	def tooltip_include(self, view, point):
	
		line 		= view.substr(view.line(point))
		include 	= CodeAnalyzer.Regex_FIND_INCLUDE.match(line).group(1)


		(file_path, exists) = var.analyzer.get_include_path(util.get_filename_by_view(view), include)
		if not exists :
			return

		link_local = file_path + '##1'
		if not '.' in include :
			link_web = include + '##1'
			include += ".inc"
		else :
			link_web = None
			
		top = ''
		if link_web :
			top += '<a class="include_link" href="'+link_web+'">WebAPI</a> | '
		top += '<a class="include_link" href="'+link_local+'">'+include+'</a>'
	
		content = '<span class="inc">Location:</span><br>'
		content += '<span class="incPath">'+file_path+'</span>'

		tooltip.show_popup(view, point + 1, top, content, "", self.tooltip_on_click)

	def tooltip_function(self, view, point):
		
		word_region = view.word(point)
		search_func = view.substr(word_region)
		found 		= None
		node 		= var.nodes[util.get_filename_by_view(view)]

		funclist = node.generate_list("funclist", set)
		
		for func in funclist :
			if search_func == func.name :
				found = func
				if found.type != var.FUNC_TYPES.public :
					break
				
		if not found :
			return
			
		filename = os.path.basename(found.file_path)
		
		link_local 	= found.file_path + '#' + found.name + '#' + str(found.start_line)
		link_web 	= ''
			
		if found.type != var.FUNC_TYPES.function and cfg.include_dir == os.path.dirname(found.file_path) :
			link_web = filename.rsplit('.', 1)[0] + '#' + found.name + '#'

		top = '<a class="include_link" href="@'+search_func+'">Search All</a>'
		if link_web:
			top += ' | <a class="include_link" href="'+link_web+'">WebAPI</a>'
		top += ' | <a class="include_link" href="'+link_local+'">'+filename+'</a>'
		
		content = ""
		if found.type :
			content += '<span class="pawnConstVar"><b>'+var.FUNC_TYPES[found.type]+'</b></span>&nbsp;&nbsp;'
		if found.return_type :
			content += '<span class="pawnTag">'+found.return_type+':</span>&nbsp;'
		content += '<span class="pawnFunc">'+found.name+'</span>' + '<span class="pawnParams">'+ tooltip.pawn_highlight('('+found.parameters+')') +'</span>'
		content += '<br>'
		
		if found.type != var.FUNC_TYPES.public and found.param_list :
			(row, col) = view.rowcol(point)
			line = view.substr(view.line(point)).rstrip()
			text = line[line.find('(', col):]
			
			arguments = tooltip.parse_current_arguments(text)
			maxlen = len(max(found.param_list, key=len)) + 1
	
			if len(arguments) >= 1 :
				content += '<br>'
				content += '<span class="params">Param-Inspector:</span>'
				content += '<br><code>'
			
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

		tooltip.show_popup(view, point + 1, top, content, "", self.tooltip_on_click)
			
	def tooltip_on_click(self, link):
	
		view = sublime.active_window().active_view()
		view.hide_popup()
		
		if link[0] == '@' :
			global g_fix_view
			g_fix_view = True
			sublime.active_window().run_command("amxx_find_replace", { "find_replace": link[1:] } )
			return
			
		(file, search, line_row) = link.split('#')
		
		if "." in file :
			util.goto_definition(file, search, int(line_row)-1, False)
		else :
			webbrowser.open_new_tab("http://www.amxmodx.org/api/"+file+"/"+search)
		

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
		
		if not is_amxmodx_view(view) or not cfg.ac_enable:
			return None
			
		if view.match_selector(locations[0], 'source.sma string') :
			return ([ ], sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
			
		word = view.substr(view.word(locations[0]))
		self.debug_event("on_selection_modified() -> prefix:[%s] - word:[%s] - location:[%d]" % (prefix, word, locations[0]))
		
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
			
		if fullLine.startswith("new ") or fullLine.startswith("for") :
		
			(row, col) = view.rowcol(locations[0])
			text = view.substr(view.full_line(locations[0]))[0:col]
			
			pos = text.find("new ")
			if pos != -1 and ac.block_on_varname(text[pos+4:]) :
				return ([ ], sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)

	
		#if len(prefix) > 1 :
		#	return None
		
		
		line 		= view.rowcol(locations[0])[0] + 1
		file_path 	= util.get_filename_by_view(view)
		node 		= var.nodes[file_path]
		
		list = ac.generate_autocompletion_list(node)
	
		if cfg.ac_local_var :
			list.extend(ac.generate_local_vars_list(node, line))
		if cfg.ac_keywords :
			list.extend(ac.generate_keywords_list(cfg.ac_keywords))
		if cfg.ac_snippets :
			list.extend(ac.cache_snippets)
		
		
		newlist = [ ]

		if cfg.ac_explicit_mode :
			for item in list :
				if item[0][0] == prefix[0] :
					newlist += [ item ]
		else :
			newlist = list

		if cfg.ac_extra_sorted :
			newlist = ac.sorted_nicely(newlist)
			
		#newlist[0] = ( prefix + ":\t                                                               --- ", "" )
		
		return (newlist, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)

#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::



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
		constants_highlight(view, False)
		invalid_functions_highlight(view, False)

	def stop(self):
		self.stoped = True
	

#:: Analyzer Queue Thread :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
class IncludeFileEventHandler(watchdog.events.FileSystemEventHandler):

	def __init__(self):
		watchdog.events.FileSystemEventHandler.__init__(self)

	# If file is in used, update it.
	def on_created(self, event):
		if event.src_path in var.nodes :
			var.analyzerQueue.add_to_queue(event.src_path)

	def on_modified(self, event):
		if event.src_path in var.nodes :
			var.analyzerQueue.add_to_queue(event.src_path)

	# If file not has a open view, free the memory ( remove children ).
	def on_deleted(self, event):
		if util.get_open_view_by_filename(event.src_path) :
			return

		node = var.nodes.get(event.src_path)
		if node is None :
			return

		node.remove_all_children_and_funcs()


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
			
			var.analyzer.process(view, file_path, buffer)

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

	Regex_FIND_INCLUDE 		= re.compile(r'^[\s]*#include[\s]+[<"]([^>"]+)[>"]', re.M)
	Regex_LOCAL_INCLUDE 	= re.compile(r'\.(sma|inc|inl)$')
	Regex_FIND_FUNC 		= re.compile(r'^(stock |public )?(\w*:)?([A-Za-z_][\w_]*)\s*\(', re.M)

	debug.performance.init("total")
	debug.performance.init("generate_sections")
	
	def __init__(self):
		pass
	
	def process(self, view, file_path, buffer):
		
		(current_node, is_added) = NodeBase.get_or_add(file_path)
	
		base_includes = set()
		error_regions = [ ]

		for match in self.Regex_FIND_INCLUDE.finditer(buffer):
			exists = self.load_include_file(file_path, match.group(1), current_node, current_node, base_includes)
			if view and not exists :
				error_regions.append(sublime.Region(match.start(), match.end()))

		for removed_node in current_node.children.difference(base_includes) :
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

			data = var.parse.process(pFile, node)
			
			node.autocompletion = data.autocompletion
			node.funclist = data.funclist
			node.constants = data.constants
			
			debug.info("(Analizer) Finished: -> Total: %.3fsec\n" % debug.performance.end("total") )
			return
		#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
		
		
		# Separate code in sections
		debug.performance.start("generate_sections", True)
		new_sections = self.generate_sections(view, buffer)
		debug.performance.end("generate_sections")
			
		# Parse new sections
		difference = new_sections - node.old_sections
		for section in difference :
			line = view.rowcol(section.begin)[0] # NOTE: @InsecureThreadBuffer
			node.parse_data[section] = var.parse.process( TextReader( buffer[section.begin:section.end] ), node, line)
				
		# Delete old data
		for old in node.old_sections - new_sections :
			del node.parse_data[old]
		node.old_sections = new_sections
			
		# Crear and Update node data
		node.autocompletion.clear()
		node.funclist.clear()
		node.constants.clear()

		for section in new_sections :
			data = node.parse_data[section]
			base_line = view.rowcol(section.begin)[0] # NOTE: @InsecureThreadBuffer
			
			node.autocompletion.extend(data.autocompletion)
			node.constants.update(data.constants)

			for func in data.funclist :
				func.update_line(base_line) # Update current line position, used for autocompletion and tooltip
			node.funclist.update(data.funclist)
				
			# Mark error lines
			for error in data.error_lines :
				start_line	= base_line + error[0] - 1
				end_line	= base_line + error[1]
				
				begin = view.text_point(start_line, 0)
				end = view.text_point(end_line, 0)
				end = view.line(end).end()

				error_regions.append(sublime.Region(begin, end))
		# Show errors
		mark_show(view, error_regions)
		
	
		
		"""
		# Debug
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
		"""
		
		# Compile regex of constants
		debug.performance.init("const")
		node.Regex_CONST		= self.compile_constants(node.constants)
		node.Regex_CONST_CHILD	= self.compile_constants(node.generate_list("constants", set, skip_self=True))

		debug.performance.end("const")
		
		# Dynamic Highlight
		debug.performance.init("highlight")

		constants_highlight(view, True)
		invalid_functions_highlight(view, True)

		debug.performance.end("highlight")


		#:: Debug performance :::::::::::::::::
		debug.info("(Analizer) Generate %d sections: %.3fsec  -  Region-Highlight: %.3fsec" % (len(new_sections), debug.performance.end("generate_sections"), debug.performance.end("highlight")) )
		debug.info("(Analizer) Parsing %d sections: %.3fsec" % (len(difference), debug.performance.end("pawnparse")) )
		debug.info("(Analizer) Enum: %.3fsec - var: %.3fsec - func: %.3fsec - const: %.3fsec" % (
			debug.performance.end("enum"),
			debug.performance.end("var"),
			debug.performance.end("func"),
			debug.performance.end("const")
		))
		debug.info("(Analizer) Finished: -> Total: %.3fsec\n" % debug.performance.end("total") )
		#::::::::::::::::::::::::::::::::::::::
		
	def compile_constants(self, constlist):
	
		constants = "___test"
		for const in constlist :
			constants += "|" + const

		pattern = "\\b(" + constants + ")\\b"
		
		return re.compile(pattern)
		
		
	#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	# NOTE: @InsecureThreadBuffer
	#   View buffer may change while this function is running. Therefore, view.find_by_selector() is insecure.
	#
	#	"comment" in view.scope_name()    AND    view.rowcol()
	#	- It is not perfect, but less likely to cause failures.
	#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	def generate_sections(self, view, buffer):
	
		sections = set()
		begin_point = 0
		
		for match in self.Regex_FIND_FUNC.finditer(buffer):
		
			point = match.start()

			# If view buffer is changed, usually differs a few characters, so have the half of length match as compensation
			if "comment" in view.scope_name(point + round((match.end() - point) / 2)) :
				continue

			sections.add( SectionData(begin_point, point - 1, buffer) )
			
			begin_point = point
	
		sections.add( SectionData(begin_point, len(buffer), buffer) )

		return sections

	def load_include_file(self, parent_file_path, include, parent_node, base_node, base_includes):
	
		(file_path, exists) = self.get_include_path(parent_file_path, include)
		
		if not exists :
			debug.info("Include File not found: inc:\"%s\",  file:\"%s\",  parent:\"%s\"" % (include, file_path, parent_file_path))

		(node, is_added) = NodeBase.get_or_add(file_path)
		parent_node.add_child(node)

		if parent_node == base_node :
			base_includes.add(node)

		if not is_added or not exists:
			return exists

		with open(file_path, 'r', encoding="utf-8", errors="replace") as file :
			includes = self.Regex_FIND_INCLUDE.findall(file.read())

		for include in includes :
			self.load_include_file(parent_file_path, include, node, base_node, base_includes)

		with open(node.file_path, 'r', encoding="utf-8", errors="replace") as file :
			debug.info("Processing Include File \"%s\"" % file_path)
			self.process_parse(None, None, file, node)
			
		return exists

	def get_include_path(self, parent_file_path, include):
		if self.Regex_LOCAL_INCLUDE.search(include) == None:
			file_path = os.path.join(cfg.include_dir, include + ".inc")
		else:
			file_path = os.path.join(os.path.dirname(parent_file_path), include)

		return (file_path, os.path.exists(file_path))
		

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

	def __init__(self, file_path):
		self.file_path 		= file_path
		self.file_name		= os.path.basename(file_path)
		
		self.children 		= set()
		self.parents 		= set()
		
		self.autocompletion = list()
		self.funclist 		= set()
		self.constants		= set()
		
		self.parse_data		= dict()
		self.old_sections 	= set()
		
		self.Regex_CONST		= None
		self.Regex_CONST_CHILD	= None

	def add_child(self, node) :
		self.children.add(node)
		node.parents.add(self)

	def remove_child(self, node):
		self.children.remove(node)
		node.parents.remove(self)

		if len(node.parents) <= 0 :
			var.nodes.pop(node.file_path)

	def remove_all_children_and_funcs(self):
		for child in self.children :
			self.remove_child(node)
			
		self.autocompletion.clear()
		self.funclist.clear()
		
	### Generate recursive list: ########################
	# @property: Node property name
	# @out_class: 
	# @custom_format: def callback(value, curnode):
	#####################################################
	def generate_list(self, property, out_class=list, custom_format=None, skip_self=False):
	
		assert issubclass(out_class, list) or issubclass(out_class, set), "Invalid Class Type (only support base list/set)"
		
		out 	= out_class()
		visited = set()
		
		def recur_func(curnode) :
			if curnode in visited :
				return

			visited.add(curnode)
			for child in curnode.children :
				recur_func(child)

			value = getattr(curnode, property)
			
			if issubclass(out_class, list):
				out.extend(value if not custom_format else map(lambda v:custom_format(v, curnode), value))
			elif issubclass(out_class, set):
				out.update(value if not custom_format else map(lambda v:custom_format(v, curnode), value))

		if skip_self :
			visited.add(self)
			for child in self.children :
				recur_func(child)
		else :
			recur_func(self)

		return out
		
	@staticmethod
	def get_or_add(file_path):
		node = var.nodes.get(file_path)
		if node is None :
			node = NodeBase(file_path)
			var.nodes[file_path] = node
			return (node, True)

		return (node, False)


def intelli_highlight(view, key, pattern_or_regex, scope, flags=0, check_scope_callback=None, clear=True):

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

	node = var.nodes[util.get_filename_by_view(view)]
	if not node.Regex_CONST :
		return
	

	def check_scope(scope, word):
		return scope == "source.sma "

	intelli_highlight(view, "pawnconst", node.Regex_CONST, "constant.vars.pawn", sublime.HIDE_ON_MINIMAP|sublime.DRAW_NO_OUTLINE, check_scope, clear)
	intelli_highlight(view, "pawnconst", node.Regex_CONST_CHILD, "constant.vars.pawn", sublime.HIDE_ON_MINIMAP|sublime.DRAW_NO_OUTLINE, check_scope, False)


def invalid_functions_highlight(view, clear=True):

	def get_name(func, curnode):
		return func.name
		
	node = var.nodes[util.get_filename_by_view(view)]
	funclist = node.generate_list("funclist", set, get_name)
			
	def check_scope(scope, word):
		if scope != "source.sma variable.function.pawn " :
			return False
			
		if word in funclist :
			return False
			
		return True

	intelli_highlight(view, "invalidfunc", r"\b[A-Za-z_][\w_]*\b", "invalid.illegal", sublime.DRAW_NO_OUTLINE|sublime.DRAW_NO_FILL|sublime.DRAW_SQUIGGLY_UNDERLINE, check_scope, clear)	


def is_amxmodx_view(view) :
	return view.match_selector(0, 'source.sma') and not g_invalid_settings


def mark_show(view, regions):
	view.add_regions("pawnmark", regions, "invalid.illegal", "dot", sublime.DRAW_NO_OUTLINE|sublime.DRAW_NO_FILL|sublime.DRAW_SQUIGGLY_UNDERLINE)

def mark_clear(view):
	view.erase_regions("pawnmark")


