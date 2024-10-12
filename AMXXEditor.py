# Sublime AMXX-Editor v4.4 by Destro

import os
import re
import sys
import sublime, sublime_plugin
import webbrowser
import time
import urllib.request
import threading
import platform
import subprocess
import zipfile

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
from AMXXcore.autocomplete 	import ac
from AMXXcore.search_all 	import SearchAllTool
from AMXXcore.pawn_parse 	import *
from AMXXcore.rollbar_api 	import RollbarAPI

import AMXXcore.tooltip 	as tooltip
import AMXXcore.debug 		as debug


#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# Global VARs & Initialize
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
globalvar.EDITOR_VERSION 		= "4.4"
globalvar.EDITOR_BUILD 			= "4410"
globalvar.EDITOR_DATE 			= "11 Oct 2024"
globalvar.PACKAGE_NAME			= "AMXXEditorV4"

globalvar.ROLLBAR_API_TOKEN		= "abe32dcc89f647398b096cd63aa964a9"
globalvar.ROLLBAR_API_ENV		= "dev"

globalvar.CONST_TYPES 			= Enum( [ "TAG", "DEFINE", "CONST", "ENUM" ] )
globalvar.FUNC_TYPES 			= Enum( [ "function", "public", "stock", "forward", "native" ] )
globalvar.KIND_FUCTION = [
	( 10, "f", "" ),
	( 3,  "p", "" ),
	( 15, "s", "" ),
	( 12, "F", "" ),
	( 12, "N", "" )
]

globalvar.nodes 			= dict()
globalvar.profiles_list 	= list()
globalvar.rollbar			= None

globalvar.search_fix_view	= False
globalvar.checking_update	= False

globalvar.style_popup 		= Style("style_popup", ".pawn-popup.css")
globalvar.style_editor 		= Style("style_editor", ".pawn-editor.sublime-color-scheme")
globalvar.style_console 	= Style("style_console", ".pawn-console.sublime-color-scheme")
	
	
# Default configuration values
cfg.rollbar_report = True
cfg.lang = "en"
# Initialize configuration attributes ( to prevent cascading errors if an error occurs during plugin_loaded() )
cfg.profiles = None
cfg.active_profile =  None
cfg.enable_tooltip =  None
cfg.enable_buildversion =  None
cfg.enable_marking_error =  None
cfg.enable_dynamic_highlight =  None
cfg.tooltip_style_mode =  None
cfg.tooltip_font_size =  None
cfg.ac_enable =  None
cfg.ac_keywords =  None
cfg.ac_snippets =  None
cfg.ac_preprocessor =  None
cfg.ac_emit_info =  None
cfg.ac_local_var =  None
cfg.ac_extra_sorted =  None
cfg.ac_add_parameters =  None
cfg.profile_include_dir =  None
cfg.view_debug_mode = None



# Exception ERROR hook, report to rollbar.
import traceback
def global_exception_handler(exctype, value, tb):
	sys.__excepthook__(exctype, value, tb)
	
	def is_package_related_exception(tb) :
		while tb is not None :
			filename = tb.tb_frame.f_code.co_filename
			
			if globalvar.PACKAGE_NAME in filename :
				return True

			tb = tb.tb_next

		return False

	if not is_package_related_exception(tb) :
		return
		
	if debug.log_file :
		debug.log("ERROR:", "".join(traceback.format_exception(exctype, value, tb)))
		
	if globalvar.rollbar and cfg.rollbar_report :
		# Create a new instance of the exception
		e = exctype(value)
		e.__traceback__ = tb
		
		# Report the exception using Rollbar
		globalvar.rollbar.report_exception(e)

# Hook exception handler
sys.excepthook = global_exception_handler



# Package loaded
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
	
	# ROLLBAR.com simple REST API ######################################################################
	globalvar.rollbar = RollbarAPI(globalvar.ROLLBAR_API_TOKEN, globalvar.ROLLBAR_API_ENV)

	DEVICE_ID = util.hash_sha1( sublime.version() + sublime.executable_path() + platform.node() )
	
	globalvar.rollbar.register_device(
		DEVICE_ID,
		None, # Device name, default: this pc name.
		{ "sublime_version": sublime.version(), "AMXXEditor": globalvar.EDITOR_BUILD } # Extra data
	)
	####################################################################################################
	
	# Extract bin tools
	if is_installed_package() :
		extract_package_directory(globalvar.PACKAGE_NAME, "bin")
	
	
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
	sublime.set_timeout_async(check_update, 2500)
	
	try:
		import locale
		lang = locale.getdefaultlocale()[0].split("_")[0]
		if lang == "es" :
			cfg.lang = "es"
	except:
		pass

def plugin_unloaded() :

	# MultiThreads Stop
	globalvar.watchDog.stop()
	globalvar.analyzerQueue.stop()
	globalvar.monitorScrolled.stop()
	
	# Log
	debug.log_close()
	
	# RollbarAPI
	globalvar.rollbar.close()

def is_installed_package():
	return __file__.startswith( sublime.installed_packages_path() )

def extract_package_directory(package_name, target_directory):

	installed_package_path = os.path.join(sublime.installed_packages_path(), f"{package_name}.sublime-package")
	extracted_path = os.path.join(sublime.packages_path(), package_name)
	
	if os.path.exists( os.path.join(extracted_path, target_directory) ):
		return False
		
	if not os.path.isfile(installed_package_path):
		debug.error(f"El paquete {package_name} no existe en installed_packages")
		return False

	try:
		os.makedirs(extracted_path, exist_ok=True)

		with zipfile.ZipFile(installed_package_path, 'r') as zip_ref:
			for file in zip_ref.namelist():
				if file.startswith(target_directory):
					zip_ref.extract(file, extracted_path)

		return True
	except Exception as e:
		debug.error(f"Error al extraer el paquete: {e}")
		return False


def on_config_change() :

	# Debug
	cfg.debug_flags 		= debug.check_flags(cfg.get("debug_flags", "a"))
	cfg.debug_log_flags 	= debug.check_flags(cfg.get("debug_log_flags", "abcd"))
	
	# Default Profile
	default_profile = "default (AMXX 1.9)"
	default_compiler = os.path.join(sublime.packages_path(), globalvar.PACKAGE_NAME, "bin", "compiler")
	cfg.profiles = {
		default_profile: {
			"amxxpc_debug": 2,
			"amxxpc_path": os.path.join(default_compiler, "amxxpc.exe" if os.name == 'nt' else "amxxpc"),
			"include_dir": os.path.join(default_compiler, "include"),
			"output_dir": "${file_path}"
		}
	}

	def profile_normpath(_dict, key) :
		path = _dict.get(key, "")
		if not path or path == "${file_path}" :
			return path
		path = path.replace("${packages}", sublime.packages_path())
		return os.path.normpath(path)
		
	# List Profiles and Validate
	profiles = cfg.get("build_profiles", None)
	if isinstance(profiles, dict) :
		for profile_name, profile in profiles.items() :
		
			if not profile or not isinstance(profile, dict) :
				continue
		
			# Fix values
			profile['output_dir'] 		= profile_normpath(profile, 'output_dir')
			profile['include_dir'] 		= profile_normpath(profile, 'include_dir')
			profile['amxxpc_path'] 		= profile_normpath(profile, 'amxxpc_path')
			
			if 'amxxpc_debug' in profile and isinstance(profile['amxxpc_debug'], int) :
				profile['amxxpc_debug'] = util.clamp(profile['amxxpc_debug'], 0, 2)
			else :
				profile['amxxpc_debug'] = 2
				
			if validate_profile(profile_name, profile) :
				cfg.profiles.setdefault(profile_name, profile)
		
	globalvar.profiles_list = list(cfg.profiles.keys())
	
	cfg.active_profile = cfg.get("active_profile", default_profile)
	if not cfg.active_profile in globalvar.profiles_list :
		cfg.active_profile = default_profile
		
		

	# Cache settings
	cfg.enable_tooltip 				= cfg.get('enable_tooltip', True)
	cfg.enable_buildversion 		= cfg.get('enable_buildversion', True)
	cfg.enable_marking_error 		= cfg.get('enable_marking_error', True)
	cfg.enable_dynamic_highlight 	= cfg.get('enable_dynamic_highlight', True)
	
	cfg.tooltip_style_mode			= cfg.get('tooltip_style_mode', 0)
	cfg.tooltip_font_size			= cfg.get('tooltip_font_size', 1)
	
	cfg.ac_enable 					= cfg.get('ac_enable', True)
	cfg.ac_keywords 				= cfg.get('ac_keywords', 2)
	cfg.ac_snippets 				= cfg.get('ac_snippets', True)
	cfg.ac_preprocessor 			= cfg.get('ac_preprocessor', True)
	cfg.ac_emit_info	 			= cfg.get('ac_emit_info', True)
	cfg.ac_local_var				= cfg.get('ac_local_var', True)
	cfg.ac_extra_sorted				= cfg.get('ac_extra_sorted', True)
	cfg.ac_add_parameters			= cfg.get('ac_add_parameters', 1)
	
	cfg.profile_include_dir 		= cfg.profiles[cfg.active_profile]['include_dir']
	
	# Update Live reflesh delay.
	globalvar.analyzerQueue.delay	= util.clamp(float(cfg.get('live_refresh_delay', 1.5)), 0.5, 5.0)
	
	# Generate list of styles
	globalvar.style_popup.initialize()
	globalvar.style_editor.initialize()
	globalvar.style_console.initialize()

	# Update style
	update_editor_style()
	update_console_style()
	update_popup_style()
	
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
				debug.warning(f"Big recursive loop, include_dir: {profile['include_dir']}")
				return False
				
	profile['includes_list'] = ac.sorted_nicely(profile['includes_list'])
	return True

def update_editor_style():

	color_scheme = None
	if "default" != globalvar.style_editor.get_active() :
		color_scheme = globalvar.style_editor.get_path()
		
	s = CustomSettings("AMXX-Pawn.sublime-settings")
	s.set("color_scheme", color_scheme)
	s.set("show_errors_inline", False)
	s.set("word_separators", "./\\()\"'-:,.;<>~!$%^&*|+=[]{}`~?")
	s.set("extensions", [ "sma", "inc" ])
	s.save()
	
	# AMXX Uncompress
	s = CustomSettings("AMXX-ASM.sublime-settings")
	s.set("color_scheme", color_scheme)
	s.save()
	
def update_console_style():

	color_scheme = None
	if "default" != globalvar.style_console.get_active() :
		color_scheme = globalvar.style_console.get_path()
		
	s = CustomSettings("AMXX-Console.sublime-settings", True)
	s.set('color_scheme', color_scheme)
	
	if color_scheme :
		data = util.safe_json_load(color_scheme).get("amxxeditor")
		if data :
			extra_settings = data.get('syntax_settings')
			for key in extra_settings :
				s.set(key, extra_settings[key])	
	s.save()
	
def update_popup_style():
	globalvar.cacheSyntaxCSS = ""
	
	globalvar.cachePopupCSS = sublime.load_resource(globalvar.style_popup.get_path())
	globalvar.cachePopupCSS = globalvar.cachePopupCSS.replace('\r', '') # Fix
	
	# Remove comments
	globalvar.cachePopupCSS = re.sub(r'/\*.*?\*/', '', globalvar.cachePopupCSS, 0, re.DOTALL)
	globalvar.cachePopupCSS = globalvar.cachePopupCSS.replace('\n\n', '\n')


def validate_profile(profile_name, profile) :

	error = f"Invalid profile configuration \"{profile_name}\"\n\n"

	# Check required fields
	if not profile['amxxpc_path'] or not profile['include_dir'] or not profile['output_dir'] :
		error += "Missing required fields. All of these must be set:\n"
		error += "- 'amxxpc_path'\n"
		error += "- 'include_dir'\n"
		error += "- 'output_dir'"

	# Validate amxxpc path
	elif not os.path.isfile(profile['amxxpc_path']) :
		error += f"amxxpc_path: File does not exist\n- amxxpc_path :  \"{profile['amxxpc_path']}\""
    
	# Validate include directory
	elif not os.path.isdir(profile['include_dir']) :
		error += f"Directory does not exist\n- include_dir :  \"{profile['include_dir']}\""
    
	# Validate output directory
	elif profile['output_dir'] != "${file_path}" and not os.path.isdir(profile['output_dir']) :
		error += f"Directory does not exist:\n- output_dir :  \"{profile['output_dir']}\""
    
	# All Ok!
	else:
		return True
	
	if not sublime.ok_cancel_dialog(error, "Edit Settings", "ERROR: AMXX-Editor")  :
		return False


	file_path = f"{sublime.packages_path()}/User/AMXX-Editor.sublime-settings"
	if not os.path.isfile(file_path):
		default = sublime.load_resource(f"Packages/{globalvar.PACKAGE_NAME}/AMXX-Editor.sublime-settings")
		default = default.replace("Example:", "User Settings:")
		f = open(file_path, "w")
		f.write(default)
		f.close()

	sublime.set_timeout_async(run_edit_settings, 250)
	return False
	
def run_edit_settings() :
	sublime.active_window().run_command("edit_settings", {
		"base_file": f"${{packages}}/{globalvar.PACKAGE_NAME}/AMXX-Editor.sublime-settings",
		"default": "{\n\t$0\n}\n"
	})

class AmxxProfileCommand(sublime_plugin.ApplicationCommand):

	def run(self, index) :
		if index >= len(globalvar.profiles_list) :
			return

		cfg.active_profile = globalvar.profiles_list[index]
		
		cfg.set("active_profile", cfg.active_profile)
		cfg.save()

	def is_visible(self, index) :
		return (index < len(globalvar.profiles_list))
		
	def is_checked(self, index) :
		return (index < len(globalvar.profiles_list) and globalvar.profiles_list[index] == cfg.active_profile)

	def description(self, index) :
		if index < len(globalvar.profiles_list) :
			return globalvar.profiles_list[index]
		return ""
		
class AmxxEditorStyleCommand(sublime_plugin.ApplicationCommand):

	def run(self, index) :
		if index >= globalvar.style_editor.count() :
			return
		
		globalvar.style_editor.set_active(index)

		cfg.set("style_editor", globalvar.style_editor.get_active())
		
		if not index :
			cfg.save(False)
			return
			
		path = globalvar.style_editor.get_path()
		data = util.safe_json_load(path).get("amxxeditor")
		if data :
			cfg.set("style_popup", data.get('default_popup', 'default'))
			cfg.set("style_console", data.get('default_console', 'default'))
			
		cfg.save(False)

	def is_visible(self, index) :
		return index < globalvar.style_editor.count()
		
	def is_checked(self, index) :
		return globalvar.style_editor.is_active(index)

	def description(self, index) :
		if index < globalvar.style_editor.count() :
			return globalvar.style_editor.list[index]
		return ""

class AmxxConsoleStyleCommand(sublime_plugin.ApplicationCommand):

	def run(self, index) :
		if index >= globalvar.style_console.count() :
			return

		globalvar.style_console.set_active(index)

		cfg.set("style_console", globalvar.style_console.get_active())
		cfg.save()
		
		update_console_style()

	def is_visible(self, index) :
		return index < globalvar.style_console.count()
		
	def is_checked(self, index) :
		return globalvar.style_console.is_active(index)

	def description(self, index) :
		if index < globalvar.style_console.count() :
			return globalvar.style_console.list[index]
		return ""

class AmxxPopupStyleCommand(sublime_plugin.ApplicationCommand):

	def run(self, index) :
		if index >= globalvar.style_popup.count() :
			return

		globalvar.style_popup.set_active(index)
		
		cfg.set("style_popup", globalvar.style_popup.get_active())
		cfg.save()
		
		update_popup_style()
	#}

	def is_visible(self, index) :
		return index < globalvar.style_popup.count()
		
	def is_checked(self, index) :
		return globalvar.style_popup.is_active(index)

	def description(self, index) :
		if index < globalvar.style_popup.count() :
			return globalvar.style_popup.list[index]
		return ""

class AmxxNewIncludeCommand(sublime_plugin.WindowCommand):
	def run(self):
		new_file("inc")
		
class AmxxNewPluginCommand(sublime_plugin.WindowCommand):
	def run(self):
		new_file("sma")

def new_file(extension):
	view = sublime.active_window().new_file()

	view.set_syntax_file("AMXX-Pawn.sublime-syntax")
	view.set_name(f"untitled.{extension}")
	
	plugin_template = sublime.load_resource(f"Packages/{globalvar.PACKAGE_NAME}/default.{extension}").replace("\r", "")

	view.run_command("insert_snippet", {"contents": plugin_template})
	


def check_update(bycommand=False) :
#{
	globalvar.checking_update = True
	
	sublime.active_window().status_message("AMXX-Editor: Checking update...")
	
	data = None
	try:
		with urllib.request.urlopen("https://raw.githubusercontent.com/Destro-/AMXXEditorV4/main/check_version.txt") as response:
			data = response.read()
	except Exception as e:
		if bycommand :
			sublime.error_message(f"ERROR: urlopen()' in check_update() -> {e}")
	
		debug.warning(f"'urlopen()' in check_update() -> {e}")
		sublime.active_window().status_message("AMXX-Editor: Check update failed")

	if not data :
		globalvar.checking_update = False
		return
		
	data = data.decode("utf-8", "replace")
	if data :
	#{
		sublime.active_window().status_message("AMXX-Editor: Check update successful")
		
		version, news = data.split("\n", 1)
		version, build = version.split("-")
		
		build = int(build)
		current_build = int(globalvar.EDITOR_BUILD)

		title =  f"AMXX-Editor: v{globalvar.EDITOR_VERSION} (build: {globalvar.EDITOR_BUILD})"

		if current_build >= build and bycommand:
			sublime.ok_cancel_dialog(f"You are already using the latest version!", "OK", title)
			
		if current_build < build :
			
			updateType = 'version' if version != globalvar.EDITOR_VERSION else 'build' 
			
			msg = f"A new {updateType} is available: v{version} (build: {build})\n\n{news}"

			ok = sublime.ok_cancel_dialog(msg, "Download Update", title)
			
			if ok :
				webbrowser.open_new_tab("https://github.com/Destro-/AMXXEditorV4/")
	#}
	
	globalvar.checking_update = False
#}


class AmxxCheckUpdateCommand(sublime_plugin.WindowCommand):
	def run(self):
		if not globalvar.checking_update :
			globalvar.checking_update = True
			sublime.set_timeout_async(lambda: check_update(True), 50)


class SearchAllInputHandler(sublime_plugin.TextInputHandler):
	def __init__(self, tool):
		self.tool = tool
		self.is_valid = False

	def preview(self, search_all):
	
		if self.tool.last_error :
			error = self.tool.last_error
			self.tool.last_error = ""
		else : # current error
			error = self.tool.searchAll(search_all, True)
		
		if error or not search_all :
			self.is_valid = False
		else:
			self.is_valid = True

		if not search_all :
			body = """
			<b>Search in All #includes files</b>
			<br><br>
			<b>Prefix:</b>
			<br>
			<b class="prefix">R::</b> - Regular expression.<br>
			<b class="prefix">E::</b> - Exact word match.<br>
			<b class="prefix">I::</b> - Word match, ignorecase.<br>
			"""
		else :
			search_type = SearchAllTool.search_type_msg[self.tool.search_type]
			body = f'<b>{search_type}:</b> {self.tool.search}'

		###################################################################
		if error :
			body += f'<br><br><span class="error"><b>Error:</b> {error}</span>'


		content = """
		<style>
		body {
			margin-top: 2px;
			margin-bottom: 2px;
		}

		.prefix {
			font-family: monospace;
			color: #DC143C;
		}
	
		.error {
			color: #f00;
		}
		
		</style>
		<body>
		""" + body + """
		</body>
		"""

		return sublime.Html(content)

	def placeholder(self):
		return "Search"
		
	def initial_text(self):
		return self.tool.initial_text
	
	def validate(self, value):
		return self.is_valid
		
	def confirm(self, value):
		pass
		
	def cancel(self):
		self.tool.initial_text = ""

class AmxxSearchAllCommand(sublime_plugin.WindowCommand):
	def __init__(self, window):
		self.window = window
		self.tool = SearchAllTool(window)
	
	def run(self, search_all):

		if globalvar.search_fix_view :
			globalvar.search_fix_view = False
			self.tool.view = self.window.active_view()
		
		error = self.tool.searchAll(search_all)
		if error :
			self.window.run_command("amxx_search_all")

	def is_enabled(self):
		return is_amxmodx_view(self.window.active_view())
	
	def input(self, args):
		self.tool.view = self.window.active_view()
		return SearchAllInputHandler(self.tool)
		
	def input_description(self):
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
			#a += "   " * (level - 1)
				
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
				if not cfg.profile_include_dir in func.file_path and func.type < globalvar.FUNC_TYPES.forward :
					self.list += [ [ func.name, func.file_path, func.start_line, func.type ] ]

			self.list = ac.sorted_nicely(self.list)
			
			quicklist = []
			for list in self.list :
				location = os.path.basename(list[1]) + " : " + str(list[2])
				quicklist += [ sublime.QuickPanelItem( list[0], "", location, globalvar.KIND_FUCTION[list[3]] ) ]

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
	
class AboutInputHandler(sublime_plugin.TextInputHandler):
	def preview(self, text):
	
		body = f'<span class="title">Sublime AMXX-Editor v{globalvar.EDITOR_VERSION}</span>'
		body += '<span class="author"> By <a href="https://forums.alliedmods.net/member.php?u=81617">Destro</a></span>'
		body += '<div class="info">'
		body += f'Build: {globalvar.EDITOR_BUILD}<br>'
		body += f'Release Date: {globalvar.EDITOR_DATE}'
		body += '<br><br><a href="https://github.com/Destro-/AMXXEditorV4/">AMXXEditorV4 on GitHub</a>'
		body += '</div>'
		
		body += "<br><br>"
		
		body += '<a class="btn" href="subl:amxx_check_update">Check Update</a> '
		body += '<a class="btn" href=\'subl:show_amxx_changelog {"file":"Packages/AMXXEditorV4/changelog%s.txt"}\'>Changelog</a> ' % ( "_es" if cfg.lang == "es" else "" )
		body += '<a class="btn" href="https://destro-.github.io/donar.htm">Donate</a>'
		
		content = """
<html>
<style>
html {
	background-color: #000;
	padding: 8px;
}

body {
	color: var(--yellowish);
	margin-top: 0px;
}

.title {
	font-size: 20px;
	font-weight: bold;
}

.author a {
	color: var(--yellowish);
}

.info {
	padding-left: 8px;
}

.info a {
	color: var(--cyanish);
}

.btn {
	font-size: 14;
	text-decoration: none;
	border-radius: 5px;
	padding: 0.4em 0.8em;
	
	background-color: #0078D7;
	color: #fff;
}

</style>
<body>
%s
</body>
</html>
""" % body

		"""
		<h1>Sublime AMXX-Editor v Destro</h1>
<b>CREDITs:</b><br>
ppalex7 <i>(SourcePawn Completions)</i><br>
<br>
<b>- Contributors:</b><br>
sasske <i>(white color scheme)</i><br>
addons_zz <i>(npp color scheme)</i><br>
KliPPy <i>(build version)</i><br>
Mistrick <i>(mistrick color scheme)</i><br>

		
		"""

		return sublime.Html(content)


	
class AmxxAboutCommand(sublime_plugin.WindowCommand):
	def run(self, about):
		pass
	
	def input(self, args):
		return AboutInputHandler()
		

from Default.exec import ExecCommand
class AmxxExecCommand(ExecCommand):

	def run(self, *args, **kwargs):
		super().run(*args, **kwargs)
		
		view = self.output_view
		view.erase_phantoms("button")
		
		self.outfile = ""
		for s in kwargs['cmd'] :
			if s.startswith("-o") :
				self.outfile = util.unix_normpath(s[2:])
				
				try:
					os.remove(self.outfile)
				except:
					pass
					
				break
				
	"""def update_annotations(self):
		print("update_annotations()")
		super().update_annotations()
	"""
	
	def on_finished(self, proc):
	
		self.window.run_command("next_result")
		
		super().on_finished(proc)
		
		elapsed = time.time() - proc.start_time
		if elapsed < 1:
			elapsed_str = "%.0fms" % (elapsed * 1000)
		else:
			elapsed_str = "%.1fs" % (elapsed)
		self.write("\n[Finished in %s]" % elapsed_str)
		
		if not os.path.exists(self.outfile) :
			return
			
		
		view = self.output_view
		
		contents = """\
<style>
html.light {

	color: #fff;
}

html.dark {

	color: #fff;
}

a {
	color: #fff;
}

a.btn {
	padding: 0.4em 0.8em;
	background-color: #0078D7;
	color: white;
	text-decoration: none;
	border-radius: 2em;
	font-size: 1em;
}

</style>

<body>
<a href="#open" class="btn">Open in Folder</a>
<a href="#copy" class="btn">Copyfile to Clip</a>
</body>

"""
		
		
		view.erase_phantoms("button")
		view.add_phantom("button", sublime.Region(view.size(), view.size()), contents, sublime.LAYOUT_BLOCK, on_navigate=self.on_navigate)
			
	def on_navigate(self, src):
		
		view = self.output_view
		
		if src == "#open" :
			subprocess.Popen(f'explorer /select,"{os.path.normpath(self.outfile)}"')
		elif src == "#copy" :
			def copy_file_to_clipboard(file_path):
				powershell_path = os.path.join(os.environ['SystemRoot'], 'system32', 'WindowsPowerShell', 'v1.0', 'powershell.exe')
				if not os.path.exists(powershell_path):
					return

				command = f'"{powershell_path}" Set-Clipboard -Path "{file_path}"'
				subprocess.Popen(command, shell=True)

			copy_file_to_clipboard(os.path.normpath(self.outfile))
			
			view.window().status_message(f"Copy {self.outfile}")
			
		elif src == "#upload" :
			pass
			
		
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#:: END Cmd / START Sublime EventListener ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class SublimeEvents(sublime_plugin.EventListener):

	#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	#:: Util Functions :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	def debug_event(self, *args):
		debug.debug(debug.FLAG_ST3_EVENT, "EVENT:", *args)
		
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
				
			css += " text-decoration: none;"
			return css + " }\n"

		highlightCSS  = scope_to_css("", "pawnDefaultColor")
		highlightCSS += scope_to_css("variable.function", "pawnFunction")
		highlightCSS += scope_to_css("string", "pawnString")
		highlightCSS += scope_to_css("keyword.operator", "pawnOperator")
		highlightCSS += scope_to_css("storage.type.vars", "pawnType")
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
			
		self.originalText = None # Reset (and create)
		
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
		
		if not is_amxmodx_view(view) :
			return

		if cmd != "paste" or not self.originalText :
			return
			
		# Restore the original text to the clipboard
		sublime.set_clipboard(self.originalText)
		
		self.originalText = None # Reset, unnecessary.
	
	#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	#:: Auto Build-Version :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	def on_window_command(self, window, cmd, args):

		self.debug_event("on_window_command() -> cmd:[%s] - arg:[%s]" % (cmd, args))
		
		if cmd != "build" :
			return
			
		view = window.active_view()
		if not is_amxmodx_view(view) :
			return
			
		profile = cfg.profiles[cfg.active_profile]
		
		build = SublimeSettings("AMXX-Compiler.sublime-build")
		
		build.set("cmd", [
			profile['amxxpc_path'],
			"-d" + str(profile['amxxpc_debug']),
			"-i" + profile['include_dir'],
			"-o" + util.unix_normpath(profile['output_dir'] + "/${file_base_name}.amxx"),
			"${file}"
		])
		
		build.set("syntax", "AMXX-Console.sublime-syntax")
		build.set("selector", "source.sma")
		build.set("working_dir", os.path.dirname(profile['amxxpc_path']))
		build.set("file_regex", "(.*)\\((\\d+)().*?:( error.*)") # read error line (file) (line) (colum) (error msg)
		build.set("quiet", True) # Disable extra messages
		build.set("target", "amxx_exec") # Hook default build command "exec"
		build.save()
		
		if not view.file_name() :
			view.run_command("save")
		
		self.amxx_auto_tag(window, view)
			
		if cfg.enable_buildversion :
			view.run_command("amxx_build_ver")
	
	def amxx_auto_tag(self, window, view):
		
		node = get_view_node(view)
		if not node :
			return

		searchTool = SearchAllTool(window)
		
		funclist = node.generate_list("funclist", set)
		includes = searchTool.get_includes(view)
		
		def replace_autotag(text):
			def search_vartag(varname, text):
				m = re.search(varname+r'\s*=\s*([a-zA-Z_]\w*\s*)\(', text, re.MULTILINE)
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
				varname = match.group(3)
				tag = search_vartag(varname, text[match.start():])
				
				if tag :
					return match.group(1) + tag + ':' + match.group(3)
					
				return match.group(1) + match.group(3)

			return re.sub(r'([\s;]+)(auto|:):([a-zA-Z_]\w*)', replace_func, text)
			
		
		for file in includes :
			text = searchTool.read_text(file)
			
			newtext = replace_autotag(text)

			if newtext and newtext != text:
				searchTool.write_text(newtext, file)
		
	#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	#:: ToolTip ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
	def on_hover(self, view, point, hover_zone):
	
		scope = view.scope_name(point)
		self.debug_event("on_hover() -> view:[%d] - scope_name:[%s]" % (view.id(), scope))

		if not is_amxmodx_view(view) or not cfg.enable_tooltip or hover_zone != sublime.HOVER_TEXT:
			return
			
		if cfg.tooltip_style_mode == 1 and not globalvar.cacheSyntaxCSS :
			globalvar.cacheSyntaxCSS = self.generate_highlightCSS(view)

		if "meta.preprocessor.include.path" in scope :
			self.tooltip_include(view, point)
		elif "storage.modifier.tag" in scope :
			self.tooltip_tag(view, point)
		elif "variable.function.pawn" in scope :
			self.tooltip_function(view, point, True)
		elif "support.function.pawn" in scope :
			self.tooltip_function(view, point, False)
		elif "source.sma " == scope or "entity.name.constant.preprocessor" in scope:
			self.tooltip_constant(view, point)
		else :
			view.hide_popup()
		
	def tooltip_include(self, view, point):
	
		line 	= view.substr(view.line(point))
		include = CodeAnalyzer.Regex_FIND_INCLUDE.match(line).group(2).strip()


		(file_path, exists) = globalvar.analyzer.get_include_path(util.get_filename_by_view(view), include)
		if not exists :
			return

		location_data = file_path + "##1"
		if not '.' in include :
			webapi_data = include + "#"
			include += ".inc"
		else :
			webapi_data = None
			
		top = ""
		if webapi_data :
			top += f'<a href="webapi:{webapi_data}">WebAPI</a><span class="separator">|</span>'
		top += f'<a href="goto:{location_data}">{include}</a>'
	
		content =  '<span class="info">Location:</span><br>'
		content += f'<span class="path">{file_path}</span>'

		self.tooltip_show_popup(view, point + 1, "tooltip-include", top, content)

	def tooltip_tag(self, view, point, search_tag=None):
		
		if not search_tag :
			word_region = view.word(point)
			search_tag  = view.substr(word_region)
			
		node = get_view_node(view)
		if not node :
			return

		references = node.cache_all_tags.get(search_tag)
		if not references :
			return
			
		content =  ""
		top = f'<a href="find_all:{search_tag}">Search All</a>'
		
		enumtag = references.get("enum")
		if enumtag :
			location_data = enumtag.file_path + '#' + search_tag + '#' + str(enumtag.line)
			top += f'<span class="separator">|</span><a href="goto:{location_data}">Go to Enum</a>'
			
			if enumtag.doc2 :
				content += tooltip.format_doct(enumtag.doc2, "doc2")
			if enumtag.doc1 :
				content += tooltip.format_doct(enumtag.doc1, "doc1")
	
		includes = sorted(references)
		for inc in includes :
			if inc == "enum":
				continue
				
			content += f'<b>{inc}:</b><br>'
			
			funclist = sorted(references[inc], key=lambda func: func.start_line)
			
			for func in funclist :
				location = "%s#%s#%d" % (func.file_path, func.name, func.start_line)
				content += f'<div class="itemrow">{tooltip.func_to_html(func, True)} <a class="btn go" href="goto:{location}">Go</a></div>'

		self.tooltip_show_popup(view, point + 1, "tooltip-tag", top, content)
		
	def tooltip_constant(self, view, point):
	
		word_region = view.word(point)
		search  = view.substr(word_region)
		node 		= get_view_node(view)
		
		if not node :
			return
			
		constans = node.generate_list("constants", dict)
		if not constans :
			return
		
		const = constans.get(search)
		if not const :
			return
			
		top = f'<a class="customLink" href="find_all:{search}">Search All</a>'
		
		link_goto = f"{const.file_path}#{search}#{const.line}"
		filename = os.path.basename(const.file_path)
		
		top += f'<span class="separator">|</span><a class="customLink" href="goto:{link_goto}">{filename}</a>'
		
		content = '<b>%s</b>:' % (search)
		
		if search.startswith("SVC_") :
			content = f'<b>{search}</b> <a class="btn go" href="https://wiki.alliedmods.net/Half-Life_1_Engine_Messages#{search}">☛ WIKI</a>'
		else :
			content = f'<b>{search}</b>:'

		if const.doc2 :
			content += tooltip.format_doct(const.doc2, "doc2")
		if const.doc1 :
			content += tooltip.format_doct(const.doc1, "doc1")

		self.tooltip_show_popup(view, point + 1, "tooltip-constant", top, content)

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
			
		if found.type != globalvar.FUNC_TYPES.function and cfg.profile_include_dir == os.path.dirname(found.file_path) :
			webapi_data = filename.rsplit('.', 1)[0] + '#' + found.name

		top = f'<a href="find_all:{search_func}">Search All</a>'
		if webapi_data:
			top += f'<span class="separator">|</span><a href="webapi:{webapi_data}">WebAPI</a>'
		top += f'<span class="separator">|</span><a href="goto:{location_data}">{filename}</a>'
		
		content = f"<div>{tooltip.func_to_html(found)}</div>"

		if funcCall and found.param_list :
	
			region = view.find(r'\((?:[^()]+|(?R))*\)', point)
			if not region :
				return
			
			text = view.substr(region)
			
			arguments = tooltip.parse_current_arguments(text)
			longest_param = len(max(found.param_list, key=len)) + 1
			
			is_get_user_msgid = found.name == "get_user_msgid" # Add wiki button
			
			if len(arguments) >= 1 :
				content += '<div class="inspectorTitle">Params-Inspector:</div>'
				content += '<code class="inspectorBlock">'
			
				i = 0
				for value in arguments :
				
					if value.startswith('.') :
						eq = value.find('=')
						param = value[1:eq]
						param = next((p for p in found.param_list if param in p), param)
						
						value = value[eq+1:]
					elif i < len(found.param_list) :
						param = found.param_list[i]
					else :
						param = "..."
				
					param = param.ljust(longest_param).replace(" ", "&nbsp;")
		
					content += '- '+ param +':&nbsp;'+ tooltip.pawn_highlight( value )
					
					if is_get_user_msgid :
						value = value.strip('"')
						content += f' <a class="btn go" href="https://wiki.alliedmods.net/Half-Life_1_Game_Events#{value}">☛ WIKI</a>'
					
					content += '<br>'
					
					i += 1
					
				content += '</code>'

		self.tooltip_show_popup(view, point + 1, "tooltip-function", top, content)
			
	def tooltip_on_click(self, src):
	
		view = sublime.active_window().active_view()
		
		(cmd, data) = src.split(':', 1)
		
		if cmd == "find_all" :
			globalvar.search_fix_view = True
			sublime.active_window().run_command("amxx_search_all", { "search_all": data } )
			
		elif cmd == "webapi" :
			(include, function) = data.split('#')
			webbrowser.open_new_tab(f"http://www.amxmodx.org/api/{include}/{function}") 
		
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
		else : # Default
			webbrowser.open_new_tab(src)

		view.hide_popup()
			
	def tooltip_show_popup(self, view, location, classname, top="", content="", bottom=""):
		
		import math
		normal_size = view.settings().get("font_size", 9) + cfg.tooltip_font_size
		micro_size = math.floor(normal_size * 0.7)
		small_size = math.floor(normal_size * 0.85)
		large_size = math.ceil(normal_size * 1.25)
		
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
<div class="top">%(top)s</div>
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
			"top": top,
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
		
		contents = """\
<style>
html.light {
	background-color: #000;
	color: #fff;
}

html.dark {
	background-color: #0f0;
	color: #f00;
}

</style>
<b>Test:</b>
<br>
<b>Test2:</b>
"""
		
		
		view.erase_phantoms("mytest")
		#view.add_phantom("mytest", sublime.Region(-1, -1), contents, sublime.LAYOUT_BLOCK, on_navigate=None)
			
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
		
		in_string = view.match_selector(locations[0], 'source.sma string')
		word_location = view.word(locations[0])
		word = view.substr(word_location).strip()
		
		if not word :
			return None
			
		if in_string and word[0] != '@' :
			return ([ ], sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
		
		self.debug_event("on_query_completions() -> prefix:[%s] - word:[%s] - location:[%d]" % (prefix, word, locations[0]))
		
		fullLine = view.substr(view.full_line(locations[0])).strip()
		if fullLine[0] == '#' :

			if fullLine.startswith("#include") or fullLine.startswith("#tryinclude"):
				return ( ac.generate_includes_list(cfg.profiles[cfg.active_profile]['includes_list'], fullLine), sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)

			if fullLine.startswith("#emit"):
				return ( ac.cache_emit, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
				
			pos = fullLine.rfind(prefix)
			if pos != -1 and fullLine.find(" ", 0, pos) == -1:
				return ( ac.cache_preprocessor, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
				
			return ([ ], sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)

		line 		= view.rowcol(locations[0])[0] + 1
		file_path 	= util.get_filename_by_view(view)
		node 		= globalvar.nodes.get(file_path)
		if not node :
			return None
		
		#firstChar = view.substr(sublime.Region(word_location.begin()-1, word_location.begin()))
		if word[0] == '@' :
		
			if in_string :
				def format_autocomplete(func, curnode, outObj, valueObj):
					if func.type == globalvar.FUNC_TYPES.public :
						return ( ac.format_autocomplete(curnode, "@" + func.name, "public"), func.name )
					return ( "", "" )

				funclist = node.generate_list("funclist", set, format_autocomplete)
				
				return (funclist, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
				
			else :
				def format_autocomplete(value, curnode, outObj, valueObj):
					return ( ac.format_autocomplete(curnode, "@%s:" % value, "tag"), "%s:" % value )
		
				tags = node.generate_list("tags", set, format_autocomplete)
				tags.add(("@auto:", "auto:"))
				tags.add(("@bool:", "bool:"))
				tags.add(("@Float:", "Float:"))
				
				return (tags, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
		
		if fullLine.startswith("new ") or fullLine.startswith("static ") or fullLine.startswith("for") :
		
			(row, col) = view.rowcol(locations[0])
			text = view.substr(view.full_line(locations[0]))[0:col]
			
			pos = text.find("new ")
			if pos == -1 :
				pos = text.find("static ")
				
			if pos != -1 and ac.is_code_on_varname(text[pos+4:]) :
				# return ([ prefix ], sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
				return ([ ], sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)

		completions = []
		completions.extend(node.cache_autocomplete)
		
		if cfg.ac_local_var :
			completions.extend(ac.generate_local_vars_list(node, line))
		if cfg.ac_keywords :
			completions.extend(ac.cache_keywords)
		if cfg.ac_snippets :
			completions.extend(ac.cache_snippets)
		
		if cfg.ac_extra_sorted :
			completions = ac.sorted_nicely(completions)
			
		return (completions, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)

#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

#:: Update Popup CSS on active style modified :::::::::::::::::::::::::::::::::::::::::
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
class PopupFileEventHandler(watchdog.events.FileSystemEventHandler):

	def __init__(self):
		watchdog.events.FileSystemEventHandler.__init__(self)

	def on_modified(self, event):
		if os.path.basename(event.src_path) == os.path.basename(globalvar.style_popup.get_path()) :
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
		profile = cfg.profiles[cfg.active_profile]
		if profile['include_dir'] in event.src_path and event.src_path.endswith(".inc") :
			inc = event.src_path.replace(profile['include_dir'], "").lstrip("\\/").replace("\\", "/").replace(".inc", "")
			profile['includes_list'].append(inc)
			debug.info("Add include:", inc, " -> ", event.src_path)
		

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
		super().__init__(self)

		self.daemon = True
		self.stoped = False
	
		self.start()
		
	def run(self):
		while not self.stoped:
			try:
				self.monitor_scrolled()
			except Exception:
				sys.excepthook(*sys.exc_info())
			
			time.sleep(1.0)

	def monitor_scrolled(self):
	
		view = sublime.active_window().active_view()
		if not view or not is_amxmodx_view(view) :
			return
			
		viewid = view.id()
		pos = view.viewport_position()[1]
		
		if self.viewport_oldpos.get(viewid) != pos :
			self.viewport_oldpos[viewid] = pos
			self.on_scrolled(view)
			
	def on_scrolled(self, view):
		if cfg.enable_dynamic_highlight :
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
		
			try :
				if view :
					buffer = view.substr(sublime.Region(0, view.size()))
					file_path = util.get_filename_by_view(view)
				else :
					with open(file_path, 'r', encoding="utf-8", errors="replace") as f :
						buffer = f.read()

				globalvar.analyzer.process(view, file_path, buffer)
			except Exception as e:
				sys.excepthook(*sys.exc_info())
				
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
		
		#:: Parse include file ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
		if pFile :
			debug.info("(Analyzer) Starting parser: -> \"%s\"" % node.file_name)
			
			data = globalvar.parse.process(pFile, node)
			
			node.autocomplete = data.autocomplete
			node.funclist = data.funclist
			node.constants = data.constants
			node.tags = data.tags
			
			debug.info("(Analyzer) Finished: -> Total: %.3fsec\n" % debug.performance.end("total") )
			return
		#:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
		
		# MultiThreads problem :S ( view was closed while it is processed )
		if not view or not view.is_valid() :
			return
		
		debug.info("(Analyzer) Starting parser: -> \"%s\"" % node.file_name)
		
		# Code separated into sections
		debug.performance.start("generate_sections", True)
		new_sections = self.generate_sections(view, buffer)
		debug.performance.end("generate_sections")
		
		# Parse new sections
		difference = new_sections - node.old_sections
		for section in difference :
		
			# MultiThreads ( view was closed while it is processed )
			if not view or not view.is_valid() :
				return
			
			line = view.rowcol(section.begin)[0] # NOTE: Go to @InsecureThreadBuffer
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
		
			# MultiThreads ( view was closed while it is processed )
			if not view or not view.is_valid() :
				return
				
			data = node.parse_data[section]
			baseline = view.rowcol(section.begin)[0] # NOTE: Go to @InsecureThreadBuffer
			
			# Update autocomplete items
			node.autocomplete.extend(data.autocomplete)

			# Update current line position, used for autocomplete and tooltip
			for func in data.funclist :
				func.update_line(baseline)
			node.funclist.update(data.funclist)
			
			for const in data.constants.values() :
				const.update_line(baseline)
			node.constants.update(data.constants)
			
			# Update tags.
			for tagname in data.tags :
				tagA = node.tags.get(tagname)
				tagB = data.tags[tagname]

				tagB.update_line(baseline)
				
				if not tagA :
					node.tags[tagname] = tagB
					continue
					
				if tagB.funclist :
					tagA.funclist.update(tagB.funclist)
					
				# Update tag enum data.
				if tagB.isenum :
					tagA.file_path 		= tagB.file_path
					tagA.line_offset 	= tagB.line_offset
					tagA.line			= tagB.line
					
					tagA.doc1			= tagB.doc1
					tagA.doc2			= tagB.doc2
			
			
			# Mark error lines
			for error in data.error_lines :
				start_line	= baseline + error[0] - 1
				end_line	= baseline + error[1]
				
				begin = view.text_point(start_line, 0)
				end = view.text_point(end_line, 0)
				end = view.line(end).end()

				error_regions.append(sublime.Region(begin, end))
			
		# Show errors
		if cfg.enable_marking_error :
			marking_error_lines(view, error_regions)
		
		# Organize and Cache data
		debug.performance.init("organize_and_cache")
		node.organize_and_cache()
		debug.performance.end("organize_and_cache")
		
		
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
		
		# Compile regex of constants,  separate to optimize compilation
		debug.performance.init("const")
		node.Regex_CONST		= self.compile_constants(node.constants.keys())
		node.Regex_CONST_ALL	= self.compile_constants(node.generate_list("constants", dict, skip_self=True).keys())
		debug.performance.end("const")
		
		# MultiThreads problem :S ( view was closed while it is processed )
		if not view or not view.is_valid() :
			return
				
		# Dynamic Highlight
		debug.performance.init("highlight")
		if cfg.enable_dynamic_highlight :
			constants_highlight(view, True)
			invalid_functions_highlight(view, True)
		debug.performance.end("highlight")


		#:: Debug performance :::::::::::::::::
		debug.dev(" (Analyzer) Generating sections: %d sections in %.3fsec  -  Region-Highlight: %.3fsec" % (len(new_sections), debug.performance.end("generate_sections"), debug.performance.end("highlight")) )
		debug.dev(" (Analyzer) Parsing sections: %d sections in %.3fsec" % (len(difference), debug.performance.end("pawnparse")) )
		debug.info("(Analyzer) <parse enum: %.3fsec>, <parse var: %.3fsec>, <parse func: %.3fsec>, <compile constants: %.3fsec>" % (
			debug.performance.end("enum"),
			debug.performance.end("var"),
			debug.performance.end("func"),
			debug.performance.end("const")
		))
		debug.dev(" (Analyzer) Organize And Cache data: %.3fsec" % debug.performance.end("organize_and_cache"))
		debug.dev(" (Analyzer) %s" % debug_instances_info())
		debug.info("(Analyzer) Finished: -> Total: %.3fsec\n" % debug.performance.end("total") )
		#::::::::::::::::::::::::::::::::::::::
		
	def compile_constants(self, constlist):
		constants = "__test|" + "|".join(constlist)
		return re.compile(r"\b(%s)\b" % constants)
	

	# NOTE: @InsecureThreadBuffer
	# Initially, view.find_by_selector() was used, but the view buffer can change while processing multithreaded.
	# So now a combination of Regex, view.scope_name() and view.rowcol() is used.
	def generate_sections(self, view, buffer):
	
		sections = set()
		begin_point = 0
		
		for match in self.Regex_FIND_FUNC.finditer(buffer):
		
			point = match.start()

			# If the view buffer changes, it usually differs by very few characters
			# So it checks from the middle of the length as compensation
			scope = view.scope_name(point + round((match.end() - point) / 2))
			if "comment" in scope or "string" in scope :
				continue

			sections.add( SectionData(begin_point, point - 1, buffer) )
			
			begin_point = point
	
		sections.add( SectionData(begin_point, len(buffer), buffer) )

		return sections

	def load_include_file(self, parent_file_path, include, parent_node, base_node, includes_used):
	
		(file_path, exists) = self.get_include_path(parent_file_path, include)
		
		if not exists :
			debug.warning("Include File not found: include:\"%s\",  file:\"%s\",  parent:\"%s\"" % (include, file_path, parent_file_path))
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
			file_path = os.path.join(os.path.dirname(parent_file_path), include)
			exists = os.path.exists(file_path)
		
		if not exists :
			if '.' in include :
				file_path = os.path.join(cfg.profile_include_dir, include)
			else :
				file_path = os.path.join(cfg.profile_include_dir, include + ".inc")
			exists = os.path.exists(file_path)

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
		self.constants		= dict()
		self.tags			= dict()
		
		self.parse_data		= dict()
		self.old_sections 	= set()
		
		self.Regex_CONST		= None
		self.Regex_CONST_ALL	= None
		
		self.cache_all_tags		= dict()
		self.cache_autocomplete = list()

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
		self.Regex_CONST_ALL = None
	
	
	# Generate recursive list:
	#  @property: Node property name.
	#  @outclass: Output class type (list, set, or dict).
	#  @custom_format: Custom format callback.
	#   - def callback(value or [key for dict], curnode, outObj, valueObj):
	#
	#  @ returns: An instance of outclass containing the aggregated properties.
	def generate_list(self, _property, outclass=list, custom_format=None, skip_self=False):
	
		assert issubclass(outclass, list) or issubclass(outclass, set) or issubclass(outclass, dict), "Invalid Class Type (only support base list/set)"
		
		out 	= outclass()
		visited = set()
		
		def recur_func(curnode) :
			if curnode in visited :
				return

			visited.add(curnode)
			for child in curnode.children :
				recur_func(child)

			value = getattr(curnode, _property)
			
			if issubclass(outclass, list):
				out.extend(value if not custom_format else map(lambda v:custom_format(v, curnode, out, value), value))
			elif issubclass(outclass, set) :
				out.update(value if not custom_format else map(lambda v:custom_format(v, curnode, out, value), value))
			elif custom_format :
				for key in value :
					custom_format(key, curnode, out, value)
			else:
				out.update(value)
				
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
			node = NodeBase(file_path)
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
	if not node or not node.Regex_CONST or not node.Regex_CONST_ALL :
		return
	

	def check_scope(scope, word):
		return scope == "source.sma "

	generate_highlight(view, "pawnconst", node.Regex_CONST, "constant.vars.pawn", sublime.HIDE_ON_MINIMAP|sublime.DRAW_NO_OUTLINE, check_scope, clear)
	generate_highlight(view, "pawnconst", node.Regex_CONST_ALL, "constant.vars.pawn", sublime.HIDE_ON_MINIMAP|sublime.DRAW_NO_OUTLINE, check_scope, False)


def invalid_functions_highlight(view, clear=True):

	if not cfg.enable_marking_error :
		return
		
	node = get_view_node(view)
	if not node :
		return
		
	def get_name(func, curnode, outObj, valueObj):
		return func.name

	funclist = node.generate_list("funclist", set, get_name)
	if not funclist :
		return
			
	def check_scope(scope, funcname):
		if scope != "source.sma variable.function.pawn " :
			return False
			
		if funcname in funclist :
			return False
			
		return True

	generate_highlight(view, "invalidfunc", r"\b[A-Za-z_][\w_]*\b", "invalid.illegal", sublime.DRAW_NO_OUTLINE|sublime.DRAW_NO_FILL|sublime.DRAW_SQUIGGLY_UNDERLINE, check_scope, clear)	

def is_amxmodx_view(view) :
	return view.match_selector(0, 'source.sma')

def marking_error_lines(view, regions):
	view.add_regions("pawnerror", regions, "invalid.illegal", "dot", sublime.DRAW_NO_OUTLINE|sublime.DRAW_NO_FILL|sublime.DRAW_SQUIGGLY_UNDERLINE)

def clear_error_lines(view):
	view.erase_regions("pawnerror")


