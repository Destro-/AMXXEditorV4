# Sublime AMXX-Editor by Destro

import os
import re
import string
import sys
import sublime, sublime_plugin
import webbrowser
import time
import urllib.request
from collections import defaultdict
from queue import *
from threading import Timer, Thread

sys.path.append(os.path.dirname(__file__))
import watchdog.events
import watchdog.observers
import watchdog.utils
from watchdog.utils.bricks import OrderedSetQueue

from pathtools.path import list_files



def plugin_loaded() :
#{
	from string import Template
	
	l = dict()
	l['lang_my2'] 	= "cuatro"
	l['lang_your']	= "seiex"
	
	t = Template("test lang: ${lang_my} + ${lang_your} = 10")
	print(t.safe_substitute(l))

	
	settings_modified(True)
	sublime.set_timeout_async(check_update, 2500)
#}

def unload_handler() :
#{
	gWatchdogObserver.stop()
	gProcessQueueThread.stop()
	g_to_process.put(("", ""))
	sublime.load_settings("AMXX-Editor.sublime-settings").clear_on_change("amxx")
#}

class AmxxEditorStyleCommand(sublime_plugin.ApplicationCommand):
#{
	def run(self, index) :
	#{
		if index >= g_style_editor['count'] :
			return
		
		g_style_editor['active'] = g_style_editor['list'][index]
		
		global g_ignore_settings
		g_ignore_settings = True
		
		setting = sublime.load_settings("AMXX-Editor.sublime-settings")
		
		if g_style_editor['active'] in g_style_popup['list'] :
			setting.set("style_popup", g_style_editor['active'])
		if g_style_editor['active'] in g_style_console['list'] :
			setting.set("style_console", g_style_editor['active'])
		setting.set("style_editor", g_style_editor['active'])

		g_ignore_settings = False
		sublime.save_settings("AMXX-Editor.sublime-settings")
	#}

	def is_visible(self, index) :
		return (index < g_style_editor['count'])
		
	def is_checked(self, index) :
		return (index < g_style_editor['count'] and g_style_editor['list'][index] == g_style_editor['active'])

	def description(self, index) :
		if index < g_style_editor['count'] :
			return g_style_editor['list'][index]
		return ""
#}

class AmxxEditorStyleConsoleCommand(sublime_plugin.ApplicationCommand):
#{
	def run(self, index) :
	#{
		if index >= g_style_console['count'] :
			return

		g_style_console['active'] = g_style_console['list'][index]
		oneset_setting("AMXX-Editor.sublime-settings", "style_console", g_style_console['list'][index])
	#}

	def is_visible(self, index) :
		return (index < g_style_console['count'])
		
	def is_checked(self, index) :
		return (index < g_style_console['count'] and g_style_console['list'][index] == g_style_console['active'])

	def description(self, index) :
		if index < g_style_console['count'] :
			return g_style_console['list'][index]
		return ""
#}
class AmxxEditorStylePopupCommand(sublime_plugin.ApplicationCommand):
#{
	def run(self, index) :
	#{
		if index >= g_style_popup['count'] :
			return

		g_style_popup['active'] = g_style_popup['list'][index]
		oneset_setting("AMXX-Editor.sublime-settings", "style_popup", g_style_popup['list'][index])
	#}

	def is_visible(self, index) :
		return (index < g_style_popup['count'])
		
	def is_checked(self, index) :
		return (index < g_style_popup['count'] and g_style_popup['list'][index] == g_style_popup['active'])

	def description(self, index) :
		if index < g_style_popup['count'] :
			return g_style_popup['list'][index]
		return ""
#}

class NewAmxxIncludeCommand(sublime_plugin.WindowCommand):
	def run(self):
		new_file("inc")
class NewAmxxPluginCommand(sublime_plugin.WindowCommand):
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
		
class AboutAmxxEditorCommand(sublime_plugin.WindowCommand):
#{
	def run(self):
	#{
		about = """
Sublime AMXX-Editor v""" + EDITOR_VERSION + """ by Destro
		
CREDITs:
- Great:
   ppalex7     (SourcePawn Completions)
		
- Contributors:
   sasske        (white color scheme)
   addons_zz (npp color scheme)
   KliPPy        (build version)
   Mistrick     (mistrick color scheme)
"""
		sublime.message_dialog(about)
	#}
#}
		
class UpdateAmxxEditorCommand(sublime_plugin.WindowCommand):
#{
	def run(self) :
		global g_check_update
		g_check_update = True
		sublime.set_timeout_async(self.check_update_async, 100)

	def is_enabled(self) :
		if g_check_update :
			return False
		return True
		
	def description(self) :
		if g_check_update :
			return "Get info..."
		return "Check for Updates"
		
	def check_update_async(self) :
		check_update(True)
#}
		
def check_update(bycommand=0) :
#{
	global g_check_update
	
	g_check_update = True
	
	try:
		c = urllib.request.urlopen("https://amxmodx-es.com/st.php")
	except:
		if bycommand :
			sublime.error_message("Error 'urlopen' in check_update()")
		else :
			print_debug(0, "Error 'urlopen' in check_update()")
		c = None
		
	g_check_update = False
	
	if not c :
		return
		
	data = c.read().decode("utf-8", "replace")

	if data :
	#{
		data = data.split("\n", 1)
		
		fCheckVersion = float(data[0])
		fCurrentVersion = float(EDITOR_VERSION)
			
		if fCheckVersion == fCurrentVersion and bycommand :
			msg = "AMXX: You are using the latest version v"+ EDITOR_VERSION
			sublime.ok_cancel_dialog(msg, "OK")

		if fCheckVersion > fCurrentVersion :
		#{
			msg  = "AMXX: A new version available v"+ data[0]
			msg += "\n\nNews:\n" + data[1]
			ok = sublime.ok_cancel_dialog(msg, "Update")
			
			if ok :
				webbrowser.open_new_tab("https://amxmodx-es.com/showthread.php?tid=12316")
		#}
	#}
#}

class FindAllAmxxEditorCommand(sublime_plugin.WindowCommand):
	def __init__(self, a) :
		self.quickpanel	= False
		self.replace 	= None
		self.input 		= "help::"
		self.type 		= 0
		self.org_view 	= [ ]
		self.result 	= [ ]
		self.quicklist	= [ ]
		
	def run(self):
		window = sublime.active_window()
		view = window.active_view()
		
		if self.quickpanel :
			self.quickpanel = False
			window.run_command("hide_overlay")
			
		window.show_input_panel("Find/Replace : ", self.input, self.on_done, self.on_change, self.on_cancel)

	def is_enabled(self) :
		window = sublime.active_window()
		view = window.active_view()
		
		if not is_amxmodx_file(view) :
			return False
		
		return True
		
	def on_change(self, find):
		pass
		
	def on_cancel(self):
		pass
		
	def on_done(self, input):
		self.window = sublime.active_window()
		view = self.window.active_view()
		
		if not is_amxmodx_file(view) or not input :
			return
		
		flags = re.MULTILINE
		search = ""
		search_pattern = ""
		self.replace = None
		self.type = 0
			
		if input == "help::" :
			self.help()
			self.run(1)
			return
				
		r = input.split("::replace::", 1)
		search = r[0]
		if len(r) == 2 :
			self.replace = r[1]
			
		if search.startswith("word::") :
			search = search[6:]
			if len(search) > 1 :
				self.type = 2
				search_pattern = r"\b" +re.escape(search)+ r"\b"
				
		elif search.startswith("re::") :
			self.type = 1
			search_pattern = search = search[4:]
		else :
			if len(search) > 1 :
				search_pattern = r"([a-zA-Z_]*)(" +re.escape(search)+ r")(\w*)"
				if not self.replace == None :
					self.replace = r"\1" +self.replace+ r"\3"
				flags |= re.IGNORECASE
					
		if len(search) < 2 :
			self.window.status_message(" Find min chars is 2")
			self.run(1)
			return
				
		self.input = input
			
		try:
			self.regex = re.compile(search_pattern, flags)
		except Exception as e:
			self.window.status_message(" Regex ERROR: %s" % str(e).title())
			self.run(1)
			return

		self.result 	= [ ]
		includes 		= self.get_includes(view)

		for inc in includes :
			text = self.read_text(inc)
			self.result += self.search_all(text, inc)
			
		if not self.result :
			self.window.status_message(" Unable to find: %s" % self.input)
			self.run(1)
			return
			
		if self.replace == None :
			self.quicklist = [ [ "- Total Results:  %d" % len(self.result), "Find: %s" % search ] ]
		
			for result in self.result :
				self.quicklist += [ [ result[0], os.path.basename(result[3]) ] ]
			
		else :
			self.quicklist = [ [ "Replace All? :  NO" , ""] ]
			self.quicklist += [ [ "Replace All? :  YES" , "" ] ]
			self.quicklist += [ [ "- Total Results:  %d" % len(self.result), "Find: %s  -  Replace: %s" % (search, r[1]) ] ]
			
			if self.type == 1 :
				for result in self.result :
					preview = self.regex.sub(self.replace, result[0])
					self.quicklist += [ [ "", result[0] + "  ->  " + preview ] ]
			else :
				for result in self.result :
					self.quicklist += [ [ "", result[0] + "  -  " + os.path.basename(result[3]) ] ]
					
			
		self.window.run_command("hide_overlay")
			
		region = view.sel()[0]
		scroll = view.viewport_position()
		self.org_view = [ view, region, scroll ]
		
		self.show_panel(-1)

	def show_panel(self, index) :
		self.quickpanel = True
		self.window.show_quick_panel(self.quicklist, self.on_select, sublime.KEEP_OPEN_ON_FOCUS_LOST, index, self.on_highlight)
		
	def on_select(self, index):
		self.quickpanel = False
		
		if self.replace == None :
			if index == -1 :
				self.restore_org(True)
				return
				
			if index == 0 :
				self.show_panel(0)
				return
				
			index -= 1
				
			id = goto_definition(self.result[index][3], "", (self.result[index][1], self.result[index][2]), False)
			
			if id != self.org_view[0].id() :
				self.restore_org(False)
		else :
			if index == 0 :
				self.window.status_message(" Cancel Replace All")
			elif index == 1 :
				self.window.status_message(" Replace All")
				self.confirm_replace()
			elif index > 1 :
				self.show_panel(index)
		
	def on_highlight(self, index):
		if not index or not self.replace == None :
			return
			
		index -= 1
		
		goto_definition(self.result[index][3], "", (self.result[index][1], self.result[index][2]), True)
		
	def restore_org(self, focus=False):
		if self.org_view :
			view 	= self.org_view[0]
			region 	= self.org_view[1]
			scroll 	= self.org_view[2]
				
			if focus :
				self.window.focus_view(view)
				
			view.sel().clear()
			view.sel().add(region)
			view.set_viewport_position(scroll, False)
				
			self.org_view = []
	
	def help(self):
		help = """
AMXX-Editor :  Find/Replace in all local Includes

  ESPECIAL WORDs:
    re::
    word::
    help::
    ::replace::


  REPLACE EXAMPLEs:
    source = "new g_menu, g_menu_select, g_menu_id"
   

    input  = "word::g_menu::replace::menu2"
    result = "new menu2, g_menu_select, g_menu_id"
   
    input  = "re::(\\w*)_(\\w*)_(\\w*)::replace::\\3_\\2_\\1"
    result = "new g_menu, select_menu_g, id_menu_g"
   
    input  = "g_menu_::replace::menu2_"
    result = "new g_menu, g_menu2_select, g_menu2_id"
 
"""
		sublime.message_dialog(help)
		
	def confirm_replace(self):
	
		view = self.window.active_view()
		
		includes = self.get_includes(view)

		for inc in includes :
			text = self.read_text(inc)
			text = self.regex.sub(self.replace, text)
			self.write_text(text, inc)
			
			
	def search_all(self, text, file):
		
		result = [ ]
		count = 0
		
		for match in self.regex.finditer(text) :
			if self.type == 0 :
				result += [ [ match.group(0), match.start(2), match.end(2), file ] ]
			else :
				result += [ [ match.group(0), match.start(), match.end(), file ] ]
			count += 1
			if count > 200 :
				self.window.status_message(" ALERT! (%s) Find stopet at 200 results" % file)
				break

		return result
		
	def read_text(self, file_path):
	
		view = self.window.find_open_file(file_path)
		if view :
			return view.substr(sublime.Region(0, view.size()))
		
		fopen = open(file_path, encoding="utf-8", errors="replace")
		if not fopen :
			return ""
			
		content = fopen.read()
		fopen.close()
		
		return content
		
	def write_text(self, text, file_path):
	
		view = self.window.find_open_file(file_path)
		if view :
			scroll = view.viewport_position()
			
			view.run_command("select_all")
			view.run_command("left_delete")
			view.run_command('append', {'characters': text, 'force': True, 'scroll_to_end': False})
			
			view.set_viewport_position(scroll, False)
		else :
			fopen = open(file_path, mode='w', encoding="utf-8", errors="replace")
			if not fopen :
				return
			
			content = fopen.write(text)
			fopen.close()
			
		
	def get_includes(self, view):
		includes 	= [ ]
		visited 	= [ ]
		node 		= g_nodes[view.file_name()]

		self.includes_recur(node, includes, visited)
		
		return includes
		
	def includes_recur(self, node, includes, visited) :
		if node.file_name in visited :
			return

		visited += [ node.file_name ]

		if g_include_dir != os.path.dirname(node.file_name) :
			includes += [ node.file_name ]

		for child in node.children :
			self.includes_recur(child, includes, visited)

	
class IncTreeAmxxEditorCommand(sublime_plugin.WindowCommand):
	def __init__(self, a) :
		self.quickpanel = False
		
	def run(self):
		window = sublime.active_window()
		view = window.active_view()
		
		window.run_command("hide_overlay")
		
		if self.quickpanel :
			self.quickpanel = False
		else :
			includes 	= dict()
			visited 	= dict()
			self.tree	= [ ]
			node 		= g_nodes[view.file_name()]

			self.nodes_tree(node, includes, visited, 0)
			self.generate_tree(self.tree, includes, visited, 0)

			quicklist = []
			for inc in self.tree :
				quicklist += [ inc[0] ]
			
			window.show_quick_panel(quicklist, self.on_select, 0, -1, None)
			self.quickpanel = True
			
	def is_enabled(self) :
		window = sublime.active_window()
		view = window.active_view()
		
		if not is_amxmodx_file(view) :
			return False
		
		return True
		
	def on_select(self, index):
		self.quickpanel = False
		
		if index == -1 :
			return

		goto_definition(self.tree[index][1], "", None, False)
	
	def nodes_tree(self, node, includes, visited, level):

		keys = visited.keys()
		if node.file_name in keys :
			if visited[node.file_name] < level :
				return

		visited[node.file_name] = level
		includes[node.file_name] = { 'level': level, 'ignore': 0 }
		
		for child in node.children :
			self.nodes_tree(child, includes[node.file_name], visited, level+1)

	def generate_tree(self, tree, include, visited, level):

		keys = include.keys()
		keys = list(keys)
		keys.sort()
		
		a = ""
		if level >= 2 :
			a += "     "
			if level >= 3 :
				a += "  |   " * (level - 2)
				
		if level >= 1 :
			a += " +-- "
		
		for key in keys:
			if key == 'level' or key == 'ignore' :
				continue
				
			if include[key]['ignore'] or include[key]['level'] > visited[key] :
				continue
				
			if include[key]['level'] > 2 :
				include[key]['ignore'] = 1
			
			tree += [ [ "%s%s" % (a, os.path.basename(key)), key ] ]
			
			self.generate_tree(tree, include[key], visited, level+1)
		
	
class FuncListAmxxEditorCommand(sublime_plugin.WindowCommand):
	def __init__(self, a) :
		self.quickpanel = False
		self.org_view 	= [ ]
		
	def run(self):
		window = sublime.active_window()
		view = window.active_view()
		
		window.run_command("hide_overlay")
		
		if self.quickpanel :
			self.quickpanel = False
		else :
			region = view.sel()[0]
			scroll = view.viewport_position()
			
			self.org_view = [ window, view, region, scroll ]
			
			doctset 	= set()
			visited 	= set()
			node 		= g_nodes[view.file_name()]

			generate_functions_recur(node, doctset, visited)
			
			self.list = []
			for func in doctset :
				if not g_include_dir in func[2] :
					self.list += [ [ func[0], func[2], func[5] ] ]

			self.list = sorted_nicely(self.list)
			
			quicklist = []
			for list in self.list :
				quicklist += [ [ list[0], os.path.basename(list[1]) + " : " + str(list[2]) ] ]

			window.show_quick_panel(quicklist, self.on_select, sublime.KEEP_OPEN_ON_FOCUS_LOST, -1, self.on_highlight)
			self.quickpanel = True

	def is_enabled(self) :

		window = sublime.active_window()
		view = window.active_view()
		
		if not is_amxmodx_file(view) :
			return False
		
		return True
		
	def on_select(self, index):
		self.quickpanel = False
		
		if index == -1 :
			self.restore_org(True)
			return
		
		id = goto_definition(self.list[index][1], self.list[index][0], self.list[index][2] - 1, False)
		
		if id != self.org_view[1].id() :
			self.restore_org(False)
		
	def on_highlight(self, index):

		goto_definition(self.list[index][1], self.list[index][0], self.list[index][2] - 1, True)
		
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
			
		
def goto_definition(file, search="", position=None, transient=False):
	
	flags = sublime.FORCE_GROUP
	if transient :
		flags |= sublime.TRANSIENT
	
	window = sublime.active_window()
	view = window.open_file(file, group=window.active_group(), flags=flags)
		
	def do_position():
		if view.is_loading() :
			sublime.set_timeout(do_position, 50)
		else :
			if isinstance(position, tuple) or isinstance(position, list) :
				region = sublime.Region(position[0], position[1])
			elif search :
				row = 0
				if position :
					row = position
					
				region = view.find(search, view.text_point(row, 0), sublime.IGNORECASE)
			else :
				return view.id()
				
			view.sel().clear()
			view.sel().add(region)

			view.show(region)
				
			xy = view.viewport_position()
			view.set_viewport_position((xy[0] , xy[1]+1), True)
			view.show(region)
				
	if search or position :
		do_position()
	
	return view.id()

		
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
				
class SublimeEvents(sublime_plugin.EventListener):
	def __init__(self) :
		gProcessQueueThread.start()
		self.delay_queue = None
		gWatchdogObserver.start()

	def on_window_command(self, window, cmd, args) :

		#print("cmd [%s] [%s]" % (cmd, args))
		if cmd != "build" :
			return
			
		view = window.active_view()
		if not is_amxmodx_file(view) or not g_enable_buildversion :
			return
			
		view.run_command("amxx_build_ver")
		
	def on_hover(self, view, point, hover_zone):
		if hover_zone != sublime.HOVER_TEXT:
			return
			
		if not is_amxmodx_file(view) or not g_enable_inteltip :
			return
			
		scope = view.scope_name(point)
		print_debug(1, "scope_name: [%s]" % scope)
		
		if not "support.function.pawn" in scope and not "variable.function.pawn" in scope and not "meta.preprocessor.include.path" in scope :
			view.hide_popup()
			return

		if "meta.preprocessor.include.path" in scope :
			self.inteltip_include(view, point)
		else :
			self.inteltip_function(view, point)
		
	def inteltip_include(self, view, point):
		location 	= point + 1
		line 		= view.substr(view.line(point))
		include 	= INC_regex.match(line).group(1)

		(file_name, exists) = get_file_name(view.file_name(), include)
		if not exists :
			return

		fontSize = view.settings().get("font_size", 10) + 1
		
		link_local = file_name + '##1'
		if not '.' in include :
			link_web = include + '##1'
			include += ".inc"
		else :
			link_web = None
			
		html  = '<body><style> html { font-size: '+ str(fontSize)  +'px; }\n'+ g_popupCSS +'</style>'
		html += '<div class="top">'
		html += '<a class="include_link" href="'+link_local+'">'+include+'</a>'
		if link_web :
			html += ' | <a class="include_link" href="'+link_web+'">WebAPI</a>'
			
		html += '</div><div class="content">'
		
		html += '<span class="inc">Location:</span><br>'
		html += '<span class="incPath">'+file_name+'</span>'
		html += '</div><div class="bottom"></div></body>'
			
		view.show_popup(html, sublime.HIDE_ON_MOUSE_MOVE_AWAY, location, max_width=800, on_navigate=self.on_navigate)
	
	def inteltip_function(self, view, point):
		
		word_region = view.word(point)
		
		location 	= point + 1
		search_func = view.substr(word_region)
		doctset 	= set()
		visited 	= set()
		found 		= None
		node 		= g_nodes[view.file_name()]

		generate_functions_recur(node, doctset, visited)
		
		for func in doctset :
			if search_func == func[0] :
				found = func
				if found[3] != 1 :
					break
				
		if not found :
			return
			
		filename = os.path.basename(found[2])
		
		fontSize = view.settings().get("font_size", 10) + 1

		link_local 	= found[2] + '#' + found[0] + '#' + str(found[5])
		link_web 	= ''
			
		if found[3] and os.path.dirname(g_include_dir) == os.path.dirname(found[2]) :
			link_web = filename.rsplit('.', 1)[0] + '#' + found[0] + '#'
			
		html  = '<body><style> html { font-size: '+ str(fontSize)  +'px; }\n'+ g_popupCSS +'</style>'
		html += '<div class="top">'
			
		html += '<a class="include_link" href="'+link_local+'">'+os.path.basename(found[2])+'</a>'
		if link_web:
			html += ' | <a class="include_link" href="'+link_web+'">WebAPI</a>'
			
		html += '</div><div class="content">'
			
		html += '<span class="function">'+FUNC_TYPES[found[3]]+'&nbsp;:</span>&nbsp;&nbsp;<span class="pawnFunc">'+found[0]+'</span>'
		html += '<br>'
		html += '<span class="params">Params&nbsp;:</span>&nbsp;&nbsp;<span class="pawnParams">'+ self.pawn_highlight('('+found[1]+')') +'</span>'
		html += '<br>'
			
		if found[4] :
			html += '<span class="return">Return&nbsp;:</span>&nbsp;&nbsp;<span class="pawnTag">'+found[4]+'</span>'
			
		html += '</div>'
		html += '<div class="bottom"></div></body>           '
		
		view.show_popup(html, sublime.HIDE_ON_MOUSE_MOVE_AWAY, location, max_width=800, on_navigate=self.on_navigate)
			
	def on_navigate(self, link) :
		(file, search, line_row) = link.split('#')
		
		if "." in file :

			view = sublime.active_window().active_view()
			view.hide_popup()
			view.add_regions("inteltip", [ ])
			
			goto_definition(file, search, int(line_row)-1, False)
		else :
			webbrowser.open_new_tab("http://www.amxmodx.org/api/"+file+"/"+search)

	def pawn_highlight(self, str):

		str = str.replace('=', '<hack>')
		
		str = re.sub(r',(\w)', r', \1', str)
		str = re.sub(r'(("[^"]*")|(\'[^\']*\'))', r'<span class="pawnString">\1</span>', str)
		str = re.sub(r'([\(\)\[\]&]|\.\.\.)', r'<span class="pawnKeyword">\1</span>', str)
		str = re.sub(r'\b(\d+(.\d+)?)\b', r'<span class="pawnNumber">\1</span>', str)
		str = re.sub(r'([a-zA-Z_]\w*:)', r'<span class="pawnTag">\1</span>', str)

		str = str.replace('const ', '<span class="pawnConstVar">const </span>')
		str = str.replace('<hack>', '<span class="pawnKeyword">=</span>')
		str = str.replace('&', '&amp;')
	
		return str
		
	def on_activated(self, view) :
		if not is_amxmodx_file(view):
			return
		if not view.file_name() :
			return
		if not view.file_name() in g_nodes :
			add_to_queue(view)

	def on_modified(self, view) :
		self.add_to_queue_delayed(view)
		pawnparse.mark_clear()

	def on_post_save(self, view) :
		self.add_to_queue_now(view)

	def on_load(self, view) :
		self.add_to_queue_now(view)

	def add_to_queue_now(self, view) :
		if not is_amxmodx_file(view):
			return
		add_to_queue(view)

	def add_to_queue_delayed(self, view) :
		if not is_amxmodx_file(view):
			return

		if self.delay_queue is not None :
			self.delay_queue.cancel()

		self.delay_queue = Timer(float(g_delay_time), add_to_queue_forward, [ view ])
		self.delay_queue.start()

	def autocomplete_preprocessor(self):
		list = [ ]
		
		def add(value):
			list.append(( "#" + value + "\t preprocessor", value ))
			
		list.append(( "#include\t preprocessor", 		"#include <${1}>" ))
		list.append(( "#tryinclude\t preprocessor", 		"#tryinclude <${1}>" ))
		
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
		
		list = sorted_nicely(list)
			
		return (list, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
		
	def autocomplete_emit(self):
		list = [ ]
			
		def addemit(opcode, valuetype, info):
			if valuetype :
				list.append(( opcode + "\t emit opcode", opcode + " ${1:<" + valuetype + ">}\t\t// " + info))
			else:
				list.append(( opcode + "\t emit opcode", opcode + "\t\t\t// " + info))
				
		addemit("LOAD.pri", "address", "PRI   =  [address]")
		addemit("LOAD.alt", "address", "ALT   =  [address]")
		addemit("LOAD.S.pri", "offset", "PRI   =  [FRM + offset]")
		addemit("LOAD.S.alt", "offset", "ALT   =  [FRM + offset]")
		addemit("LREF.pri", "address", "PRI   =  [ [address] ]")
		addemit("LREF.alt", "address", "ALT   =  [ [address] ]")
		addemit("LREF.S.pri", "offset", "PRI   =  [ [FRM + offset] ]")
		addemit("LREF.S.alt", "offset", "ALT   =  [ [FRM + offset] ]")
		addemit("LOAD.I", "", "PRI   =  [PRI] (full cell)")
		addemit("LODB.I", "number", "PRI   =  'number' bytes from [PRI] (read 1/2/4 bytes)")
		addemit("CONST.pri", "value", "PRI   =  value")
		addemit("CONST.alt", "value", "ALT   =  value")
		addemit("ADDR.pri", "offset", "PRI   =  FRM + offset")
		addemit("ADDR.alt", "offset", "ALT   =  FRM + offset")
		addemit("STOR.pri", "address", "[address]   =  PRI")
		addemit("STOR.alt", "address", "[address]   =  ALT")
		addemit("STOR.S.pri", "offset", "[FRM + offset]   =  PRI")
		addemit("STOR.S.alt", "offset", "[FRM + offset]   =  ALT")
		addemit("SREF.pri", "address", "[ [address] ]   =  PRI")
		addemit("SREF.alt", "address", "[ [address] ]   =  ALT")
		addemit("SREF.S.pri", "offset", "[ [FRM + offset] ]   =  PRI")
		addemit("SREF.S.alt", "offset", "[ [FRM + offset] ]   =  ALT")
		addemit("STOR.I", "", "[ALT]   =  PRI (full cell)")
		addemit("STRB.I", "number", "'number' bytes at [ALT]   =  PRI (write 1/2/4 bytes)")
		addemit("LIDX", "", "PRI   =  [ ALT + (PRI * cell size) ]")
		addemit("LIDX.B", "shift", "PRI   =  [ ALT + (PRI << shift) ]")
		addemit("IDXADDR", "", "PRI   =  ALT + (PRI * cell size) (calculate indexed address)")
		addemit("IDXADDR.B", "shift", "PRI   =  ALT + (PRI << shift) (calculate indexed address)")
		addemit("ALIGN.pri", "number", "Little Endian: PRI ^   =  cell size")
		addemit("ALIGN.alt", "number", "Little Endian: ALT ^   =  cell size")
		addemit("LCTRL", "index, PRI is set to the current value of any of the special registers. The index parameter must be: 0  = COD, 1  = DAT, 2  = HEA,3  = STP, 4  = STK, 5  = FRM", "6  = CIP (of the next instruction)")
		addemit("SCTRL", "index, set the indexed special registers to the value in PRI. The index parameter must be: 2  = HEA, 4  = STK, 5  = FRM", "6  = CIP")
		addemit("MOVE.pri", "", "PRI  = ALT")
		addemit("MOVE.alt", "", "ALT  = PRI")
		addemit("XCHG", "", "Exchange PRI and ALT")
		addemit("PUSH.pri", ", [STK]   =  PRI", "STK   =  STK ")
		addemit("PUSH.alt", ", [STK]   =  ALT", "STK   =  STK ")
		addemit("PUSH.R", "value, Repeat value: [STK]   =  PRI", "STK   =  STK ")
		addemit("PUSH.C", "value, [STK]   =  value", "STK   =  STK ")
		addemit("PUSH", "address, [STK]   =  [address]", "STK   =  STK ")
		addemit("PUSH.S", "offset, [STK]   =  [FRM + offset]", "STK   =  STK ")
		addemit("POP.pri", ", STK   =  STK + cell size", "PRI   =  [STK]")
		addemit("POP.alt", ", STK   =  STK + cell size", "ALT   =  [STK]")
		addemit("STACK", "value, ALT   =  STK", "STK   =  STK + value")
		addemit("HEAP", "value, ALT   =  HEA", "HEA   =  HEA + value")
		addemit("PROC", ", [STK]   =  FRM", "STK   =  STK ")
		addemit("RET", ", STK   =  STK + cell size, FRM   =  [STK], STK   =  STK + cell size, CIP   =  [STK]", "The RET instruction cleans up the stack frame and returns from the function to the instruction after the call.")
		addemit("RETN", ", STK   =  STK + cell size, FRM   =  [STK], STK   =  STK + cell size, CIP   =  [STK]", "STK   =  STK + [STK] The RETN instruction removes a specifed number of bytes from the stack. The value to adjust STK with must be pushed prior to the call.")
		addemit("CALL", "address, [STK]   =  CIP + 5", "STK   =  STK The CALL instruction jumps to an address after storing the address of the next sequential instruction on the stack.")
		addemit("CALL.pri", ", [STK]   =  CIP + 1", "STK   =  STK ")
		addemit("JUMP", "address", "CIP   =  address (jump to the address)")
		addemit("JREL", "offset", "CIP   =  CIP + offset (jump offset bytes from currentposition)")
		addemit("JZER", "address", "if PRI   =   =  0 then CIP   =  [CIP + 1]")
		addemit("JNZ", "address", "if PRI !  =  0 then CIP   =  [CIP + 1]")
		addemit("JEQ", "address", "if PRI   =   =  ALT then CIP   =  [CIP + 1]")
		addemit("JNEQ", "address", "if PRI !  =  ALT then CIP   =  [CIP + 1]")
		addemit("JLESS", "address", "if PRI < ALT then CIP   =  [CIP + 1] (unsigned)")
		addemit("JLEQ", "address", "if PRI <   =  ALT then CIP   =  [CIP + 1] (unsigned)")
		addemit("JGRTR", "address", "if PRI > ALT then CIP   =  [CIP + 1] (unsigned)")
		addemit("JGEQ", "address", "if PRI >   =  ALT then CIP   =  [CIP + 1] (unsigned)")
		addemit("JSLESS", "address", "if PRI < ALT then CIP   =  [CIP + 1] (signed)")
		addemit("JSLEQ", "address", "if PRI <   =  ALT then CIP   =  [CIP + 1] (signed)")
		addemit("JSGRTR", "address", "if PRI > ALT then CIP   =  [CIP + 1] (signed)")
		addemit("JSGEQ", "address", "if PRI >   =  ALT then CIP   =  [CIP + 1] (signed)")
		addemit("SHL", "", "PRI   =  PRI << ALT")
		addemit("SHR", "", "PRI   =  PRI >> ALT (without sign extension)")
		addemit("SSHR", "", "PRI   =  PRI >> ALT with sign extension")
		addemit("SHL.C.pri", "value", "PRI   =  PRI << value")
		addemit("SHL.C.alt", "value", "ALT   =  ALT << value")
		addemit("SHR.C.pri", "value", "PRI   =  PRI >> value (without sign extension)")
		addemit("SHR.C.alt", "value", "ALT   =  ALT >> value (without sign extension)")
		addemit("SMUL", "", "PRI   =  PRI * ALT (signed multiply)")
		addemit("SDIV", ", PRI   =  PRI / ALT (signed divide)", "ALT   =  PRI mod ALT")
		addemit("SDIV.alt", ", PRI   =  ALT / PRI (signed divide)", "ALT   =  ALT mod PRI")
		addemit("UMUL", "", "PRI   =  PRI * ALT (unsigned multiply)")
		addemit("UDIV", ", PRI   =  PRI / ALT (unsigned divide)", "ALT   =  PRI mod ALT")
		addemit("UDIV.alt", ", PRI   =  ALT / PRI (unsigned divide)", "ALT   =  ALT mod PRI")
		addemit("ADD", "", "PRI   =  PRI + ALT")
		addemit("SUB", "", "PRI   =  PRI - ALT")
		addemit("SUB.alt", "", "PRI   =  ALT - PRI")
		addemit("AND", "", "PRI   =  PRI & ALT")
		addemit("OR", "", "PRI   =  PRI | ALT")
		addemit("XOR", "", "PRI   =  PRI ^ ALT")
		addemit("NOT", "", "PRI   =  !PRI")
		addemit("NEG", "", "PRI   =  PRI   =  --PRI")
		addemit("INVERT", "", "PRI   =  ~ PRI")
		addemit("ADD.C", "value", "PRI   =  PRI + value")
		addemit("SMUL.C", "value", "PRI   =  PRI * value")
		addemit("ZERO.pri", "", "PRI   =  0")
		addemit("ZERO.alt", "", "ALT   =  0")
		addemit("ZERO", "address", "[address]   =  0")
		addemit("ZERO.S", "offset", "[FRM + offset]   =  0")
		addemit("SIGN.pri", "", "sign extent the byte in PRI to a cell")
		addemit("SIGN.alt", "", "sign extent the byte in ALT to a cell")
		addemit("EQ", "", "PRI   =  PRI   =   =  ALT ? 1 : 0")
		addemit("NEQ", "", "PRI   =  PRI !  =  ALT ? 1 : 0")
		addemit("LESS", "", "PRI   =  PRI < ALT ? 1 : 0 (unsigned)")
		addemit("LEQ", "", "PRI   =  PRI <   =  ALT ? 1 : 0 (unsigned)")
		addemit("GRTR", "", "PRI   =  PRI > ALT ? 1 : 0 (unsigned)")
		addemit("GEQ", "", "PRI   =  PRI >   =  ALT ? 1 : 0 (unsigned)")
		addemit("SLESS", "", "PRI   =  PRI < ALT ? 1 : 0 (signed)")
		addemit("SLEQ", "", "PRI   =  PRI <   =  ALT ? 1 : 0 (signed)")
		addemit("SGRTR", "", "PRI   =  PRI > ALT ? 1 : 0 (signed)")
		addemit("SGEQ", "", "PRI   =  PRI >   =  ALT ? 1 : 0 (signed)")
		addemit("EQ.C.pri", "value", "PRI   =  PRI   =   =  value ? 1 : 0")
		addemit("EQ.C.alt", "value", "PRI   =  ALT   =   =  value ? 1 : 0")
		addemit("INC.pri", "", "PRI   =  PRI + 1")
		addemit("INC.alt", "", "ALT   =  ALT + 1")
		addemit("INC", "address", "[address]   =  [address] + 1")
		addemit("INC.S", "offset", "[FRM + offset]   =  [FRM + offset] + 1")
		addemit("INC.I", "", "[PRI]   =  [PRI] + 1")
		addemit("DEC.pri", "", "PRI   =  PRI - 1")
		addemit("DEC.alt", "", "PRI   =  PRI - 1")
		addemit("DEC", "address", "[address]   =  [address]  - 1")
		addemit("DEC.S", "offset", "[FRM + offset]   =  [FRM + offset]  - 1")
		addemit("DEC.I", "", "[PRI]   =  [PRI] - 1")
		addemit("MOVS", "number", "Copy memory from [PRI] to [ALT]. The parameter specifes the number of bytes. The blocks should not overlap.")
		addemit("CMPS", "number", "Compare memory blocks at [PRI] and [ALT]. The parameter specifes the number of bytes. The blocks should not overlap.")
		addemit("FILL", "number, Fill memory at [ALT] with value in [PRI]. The parameter specifes the number of bytes", "which must be a multiple of the cell size.")
		addemit("HALT", "0, Abort execution (exit value in PRI)", "parameters other than 0 have a special meaning.")
		addemit("BOUNDS", "value", "Abort execution if PRI > value or if PRI < 0")
		addemit("SYSREQ.pri", ", call system service", "service number in PRI")
		addemit("SYSREQ.C", "value", "call system service")
		addemit("FILE", "size ord name...", "source file information pair: name and ordinal (see below)")
		addemit("LINE", "line ord", "source line number and file ordinal (see below)")
		addemit("SYMBOL", "sze off flg name...", "symbol information (see below)")
		addemit("SRANGE", "lvl size", "symbol range and dimensions (see below)")
		addemit("JUMP.pri", "", "CIP   =  PRI (indirect jump)")
		addemit("SWITCH", "address", "Compare PRI to the values in the case table (whose address is passed) and jump to the associated address.")
		addemit("CASETBL", "... ", "casetbl num default num*[case jump]")
		addemit("SWAP.pri", "", "[STK]   =  PRI and PRI   =  [STK]")
		addemit("SWAP.alt", "", "[STK]   =  ALT and ALT   =  [STK]")
		addemit("PUSHADDR", "offset, [STK]   =  FRM + offset", "STK   =  STK ")
		addemit("NOP", ", no-operation", "for code alignment")
		addemit("SYSREQ.D", "address", "call system service directly (by address)")
		addemit("SYMTAG", "value", "symbol tag")
		addemit("BREAK", "", "invokes  optional debugger")
		
		return (list, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
		
	def autocomplete_includes(self, text):
		list = [ ]
		op = "<"
		cl = ">"
		
		if text.find("<") != -1 :
			op = ""
		if text.find(">") != -1 :
			cl = ""
			
		for inc in g_includes_list :
			list.append(( inc + "\t inc", op + inc + cl ))
			
		return (list, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
		
	def on_query_completions(self, view, prefix, locations):
		if not is_amxmodx_file(view) or not g_AC_enable:
			return None
			
		if view.match_selector(locations[0], 'source.sma string') :
			return ([ ], sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
			
		word = view.substr(view.word(locations[0]))
		print("debug: [%s][%s][%s]" % (view.substr(locations[0]-1), prefix, word))
				
		fullLine 	= view.substr(view.full_line(locations[0])).strip()
		if fullLine[0] == '#' :

			if fullLine.startswith("#include") or fullLine.startswith("#tryinclude"):
				return self.autocomplete_includes(fullLine)

			if fullLine.startswith("#emit"):
				return self.autocomplete_emit()
				
			pos = fullLine.rfind(prefix)
			if pos != -1 and fullLine.find(" ", 0, pos) == -1:
				return self.autocomplete_preprocessor()
				
			return ([ ], sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
			
		if len(prefix) > 1 :
			return None

		line 		= view.rowcol(locations[0])[0] + 1
		file_name 	= view.file_name()
		funcset 	= set()
		visited 	= set()
		node 		= g_nodes[file_name]
		
		self.generate_autocompletion_recur(node, funcset, visited)
		
		if g_AC_keywords :
		#{
			if g_AC_keywords == 1 :
				funcset.add(( "if\t if conditional", 			"if" ))
				funcset.add(( "for\t for loop", 				"for" ))
				funcset.add(( "while\t while loop", 			"while" ))
				funcset.add(( "switch\t switch conditional", 	"switch" ))
				funcset.add(( "case\t switch case", 			"case" ))
			else :
				funcset.add(( "if()\t if conditional", 			"if(${1})" ))
				funcset.add(( "for()\t for loop", 				"for(${1}; ${2}; ${3})\n{\n\t${4}\n}" ))
				funcset.add(( "while()\t while loop", 			"while(${1})" ))
				funcset.add(( "switch()\t switch conditional", 	"switch(${1})" ))
				funcset.add(( "case\t switch case", 			"case ${1}:" ))
				
			funcset.add(( "return\t return keywords", 			"return" ))
			funcset.add(( "break\t loop break ", 				"break" ))
			funcset.add(( "default\t switch default", 			"default:" ))
			funcset.add(( "continue\t loop continue", 			"continue" ))
			funcset.add(( "forward\t external pre-declaration", "forward" ))
			funcset.add(( "native\t external pre-declaration", 	"native" ))
		#}	
		
		if g_AC_local_var :
		#{
			for func in node.functions :
			#{
				if func[5] <= line and line <= func[6] :
				#{
					for var in func[7] :
					#{
						funcset.add(( var + "\t local var", var ))
					#}
					break
				#}
			#}
		#}
		
		funclist = []
		
		if g_AC_begin_explicit :
			for func in funcset :
			#{
				if func[0][0] == prefix[0] :
					funclist += [ func ]
			#}
		else :
			funclist = funcset
		
		funclist = sorted_nicely(funclist)
		return (funclist, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)

	def generate_autocompletion_recur(self, node, funcset, visited) :
		if node in visited :
			return

		visited.add(node)
		for child in node.children :
			self.generate_autocompletion_recur(child, funcset, visited)

		funcset.update(node.autocompletion)
		
def generate_functions_recur(node, doctset, visited) :
	if node in visited :
		return

	visited.add(node)
	for child in node.children :
		generate_functions_recur(child, doctset, visited)

	doctset.update(node.functions)

def is_amxmodx_file(view) :
	return view.file_name() is not None and view.match_selector(0, 'source.sma') and not g_invalid_settings
		
def on_settings_modified() :
	settings_modified()

def settings_modified(register_callback = False) :
#{
	global g_invalid_settings, g_ignore_settings, g_edit_settings
	
	if g_ignore_settings :
		return
		
	print("on_settings_modified:")

	settings = sublime.load_settings("AMXX-Editor.sublime-settings")
	if register_callback :
		settings.add_on_change('amxx', on_settings_modified)

	# check package path
	packages_path = sublime.packages_path() + "/amxmodx"
	if not os.path.isdir(packages_path) :
		os.mkdir(packages_path)

	# fix-path
	g_ignore_settings = True
	fix_path(settings, 'amxxpc_directory')
	fix_path(settings, 'include_directory')
	fix_path(settings, 'output_directory')
	g_ignore_settings = False
	
	g_invalid_settings = False
	
	invalid = is_invalid_settings(settings)
	if invalid :
	#{
		g_invalid_settings = True
		
		sublime.message_dialog("AMXX-Editor:\n\n" + invalid)

		if g_edit_settings :
			return

		g_edit_settings = True
		
		file_name = sublime.packages_path() + "/User/AMXX-Editor.sublime-settings"
		
		if not os.path.isfile(file_name):
			default = sublime.load_resource("Packages/amxmodx/AMXX-Editor.sublime-settings")
			default = default.replace("Example:", "User Setting:")
			f = open(file_name, "w")
			f.write(default)
			f.close()

		sublime.set_timeout_async(run_edit_settings, 250)
		return
	#}
		
	# Cache Settings
	global g_enable_inteltip, g_enable_buildversion, g_AC_enable, g_AC_keywords, g_AC_local_var, g_AC_begin_explicit, g_debug_level, g_delay_time, g_include_dir, g_popupCSS
	
	g_enable_inteltip 		= settings.get('enable_inteltip', True)
	g_enable_buildversion 	= settings.get('enable_buildversion', False)
	g_AC_enable 			= settings.get('ac_enable', True)
	g_AC_keywords 			= settings.get('ac_keywords', 2)
	g_AC_local_var			= settings.get('ac_local_var', True)
	g_AC_begin_explicit 	= settings.get('ac_begin_explicit', False)
	g_debug_level 			= settings.get('debug_level', 0)
	g_delay_time			= settings.get('live_refresh_delay', 1.5)
	g_include_dir 			= settings.get('include_directory')

	# Generate list of styles
	global g_style_popup, g_style_editor, g_style_console
	
	g_style_popup['list']		= STYLES_POPUP[:]
	g_style_editor['list']		= STYLES_EDITOR[:]
	g_style_console['list']		= STYLES_CONSOLE[:]
	
	g_style_popup['active']		= settings.get("style_popup")
	g_style_editor['active']	= settings.get("style_editor")
	g_style_console['active']	= settings.get("style_console")
	
	print("color active: popup(%s) editor(%s) console(%s)" % (g_style_popup['active'], g_style_editor['active'], g_style_console['active']))

	load_styles(g_style_popup,	"-popup.css")
	load_styles(g_style_editor,	"-pawn.sublime-color-scheme")
	load_styles(g_style_console,"-console.sublime-color-scheme")
	
	# Popup CSS
	g_popupCSS = sublime.load_resource("Packages/amxmodx/style/"+ g_style_popup['active'] + "-popup.css")
	g_popupCSS = g_popupCSS.replace("\r", "") # Fix Newlines
	
	
	# build-system
	build_filename = 'AMXX-Compiler.sublime-build'
	build = sublime.load_settings(build_filename)
	build.set('cmd', [ settings.get('amxxpc_directory'), "-d"+str(settings.get('amxxpc_debug')), "-i"+settings.get('include_directory'), "-o"+settings.get('output_directory')+"/${file_base_name}.amxx", "${file}" ])
	build.set('syntax', 'AMXX-Console.sublime-syntax')
	build.set('selector', 'source.sma')
	build.set('working_dir', os.path.dirname(settings.get('amxxpc_directory')))
	sublime.save_settings(build_filename)
	
	
	# AMXX-Pawn.sublime-settings ( Syntax Settings )
	if "default" == g_style_editor['active'] :
		newValue = None
	else :
		newValue = "Packages/amxmodx/style/"+ g_style_editor['active'] +"-pawn.sublime-color-scheme"
	oneset_setting("AMXX-Pawn.sublime-settings", "color_scheme", newValue)
	oneset_setting("AMXX-Pawn.sublime-settings", "extensions",  [ "sma", "inc" ])
	
	# AMXX-Console.sublime-settings ( Syntax Settings )
	if "default" == g_style_console['active'] :
		newValue = None
	else :
		newValue = "Packages/amxmodx/style/"+ g_style_console['active'] +"-console.sublime-color-scheme"
	oneset_setting("AMXX-Console.sublime-settings", "color_scheme", newValue)

	gWatchdogObserver.unschedule_all()
	gWatchdogObserver.schedule(gObserverHandler, g_include_dir, True)
	
	global g_includes_list
	g_includes_list.clear()
	for inc in list_files(g_include_dir) :
		if inc.endswith(".inc") :
			inc = inc.replace(g_include_dir, "").lstrip("\\/").replace("\\", "/").replace(".inc", "")
			g_includes_list.append(inc)
			
	g_includes_list = sorted_nicely(g_includes_list)
#}

def load_styles(style, endswith) :
#{
	for file in os.listdir(sublime.packages_path()+"/amxmodx/style") :
	#{
		if file.endswith(endswith) :
			name = file.replace(endswith, "")
			if not name in style['list'] :
				style['list'] += [ name ]
	#}
	
	if not style['active'] in style['list'] :
		style['active'] = style['list'][0]
	
	style['count'] = len(style['list'])
#}

def oneset_setting(settingfile, key, value=None) :
#{
	setting = sublime.load_settings(settingfile)
	
	if value == None :
		setting.erase(key)
	else :
		setting.set(key, value)
		
	sublime.save_settings(settingfile)
#}

def is_invalid_settings(settings) :
#{
	if settings.get('amxxpc_directory') is None or settings.get('amxxpc_debug') is None or settings.get('include_directory') is None or settings.get('output_directory') is None :
		return "You are not set correctly settings for AMXX-Editor.\n\nNo has configurado correctamente el AMXX-Editor."
		
	temp = settings.get('amxxpc_directory')
	if not os.path.isfile(temp) :
		return "amxxpc_directory :  File not exist. \n\"%s\"" % temp
		
	temp = settings.get('include_directory')
	if not os.path.isdir(temp) :
		return "include_directory :  Directory not exist. \n\"%s\"" % temp
		
	temp = settings.get('output_directory')
	if temp is "${file_path}" and not os.path.isdir(temp) :
		return "output_directory :  Directory not exist. \n\"%s\"" % temp
		
	return None
#}
	
def fix_path(settings, key) :
#{
	org_path = settings.get(key)
	
	if org_path is "${file_path}" :
		return

	org_path = org_path.replace("${packages}", sublime.packages_path())
	if sublime.platform() != "windows" :
		org_path = org_path.replace(".exe", "")
	
	path = os.path.normpath(org_path)
		
	settings.set(key, path)
#}

def run_edit_settings() :
	sublime.active_window().run_command("edit_settings", {"base_file": "${packages}/amxmodx/AMXX-Editor.sublime-settings", "default": "{\n\t$0\n}\n"})

	
def sorted_nicely( l ):
	""" Sort the given iterable in the way that humans expect."""
	convert = lambda text: int(text) if text.isdigit() else text
	alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key[0]) ]
	return sorted(l, key = alphanum_key)

def add_to_queue_forward(view) :
	sublime.set_timeout(lambda: add_to_queue(view), 0)

def add_to_queue(view) :
	# The view can only be accessed from the main thread, so run the regex
	# now and process the results later
	g_to_process.put((view.file_name(), view.substr(sublime.Region(0, view.size()))))

def add_include_to_queue(file_name) :
	g_to_process.put((file_name, None))

class IncludeFileEventHandler(watchdog.events.FileSystemEventHandler) :
	def __init__(self) :
		watchdog.events.FileSystemEventHandler.__init__(self)

	def on_created(self, event) :
		sublime.set_timeout(lambda: on_modified_main_thread(event.src_path), 0)

	def on_modified(self, event) :
		sublime.set_timeout(lambda: on_modified_main_thread(event.src_path), 0)

	def on_deleted(self, event) :
		sublime.set_timeout(lambda: on_deleted_main_thread(event.src_path), 0)

def on_modified_main_thread(file_path) :
	if not is_active(file_path) :
		add_include_to_queue(file_path)

def on_deleted_main_thread(file_path) :
	if is_active(file_path) :
			return

	node = g_nodes.get(file_path)
	if node is None :
		return

	node.remove_all_children_and_funcs()

def is_active(file_name) :
	return sublime.active_window().active_view().file_name() == file_name

class ProcessQueueThread(watchdog.utils.DaemonThread) :
	def run(self) :
		while self.should_keep_running() :
			(file_name, view_buffer) = g_to_process.get()
			if view_buffer is None :
				self.process_existing_include(file_name)
			else :
				self.process(file_name, view_buffer)

	def process(self, view_file_name, view_buffer) :
		(current_node, node_added) = get_or_add_node(view_file_name)

		base_includes = set()

		includes = INC_regex.findall(view_buffer)

		for include in includes:
			self.load_from_file(view_file_name, include, current_node, current_node, base_includes)

		for removed_node in current_node.children.difference(base_includes) :
			current_node.remove_child(removed_node)

		process_buffer(view_buffer, current_node)

	def process_existing_include(self, file_name) :
		current_node = g_nodes.get(file_name)
		if current_node is None :
			return

		base_includes = set()

		with open(file_name, 'r', encoding="utf-8", errors="replace") as f :
			print_debug(0, "(analyzer) ProcessingB Include File %s" % file_name)
			includes = INC_regex.findall(f.read())

		for include in includes:
			self.load_from_file(file_name, include, current_node, current_node, base_includes)

		for removed_node in current_node.children.difference(base_includes) :
			current_node.remove_child(removed_node)

		process_include_file(current_node)


	def load_from_file(self, view_file_name, base_file_name, parent_node, base_node, base_includes) :
		(file_name, exists) = get_file_name(view_file_name, base_file_name)
		if not exists :
			print_debug(0, "(analyzer) Include File Not Found: %s - %s - %s" % (base_file_name, file_name, view_file_name))

		(node, node_added) = get_or_add_node(file_name)
		parent_node.add_child(node)

		if parent_node == base_node :
			base_includes.add(node)

		if not node_added or not exists:
			return
			

		with open(file_name, 'r', encoding="utf-8", errors="replace") as f :
			print_debug(0, "(analyzer) Processing Include File %s" % file_name)
			includes = INC_regex.findall(f.read())

		for include in includes :
			self.load_from_file(view_file_name, include, node, base_node, base_includes)

		process_include_file(node)


def get_file_name(view_file_name, base_file_name) :
	if INC_LOCAL_regex.search(base_file_name) == None:
		file_name = os.path.join(g_include_dir, base_file_name + '.inc')
	else:
		file_name = os.path.join(os.path.dirname(view_file_name), base_file_name)

	return (file_name, os.path.exists(file_name))

def get_or_add_node( file_name) :
	node = g_nodes.get(file_name)
	if node is None :
		node = NodeIncData(file_name)
		g_nodes[file_name] = node
		return (node, True)

	return (node, False)

# ============= NEW CODE ------------------------------------------------------------------------------------------------------------
class NodeIncData :
#{
	def __init__(self, file_name):
		self.file_name 		= file_name
		self.children 		= set()
		self.parents 		= set()
		self.autocompletion = set()
		self.functions 		= set()

	def add_child(self, node) :
		self.children.add(node)
		node.parents.add(self)

	def remove_child(self, node):
		self.children.remove(node)
		node.parents.remove(self)

		if len(node.parents) <= 0 :
			g_nodes.pop(node.file_name)

	def remove_all_children_and_funcs(self):
		for child in self.children :
			self.remove_child(node)
			
		self.autocompletion.clear()
		self.functions.clear()
#}

class TextReader:
#{
	def __init__(self, text) :
		self.text = text.splitlines()
		self.position = -1

	def readline(self) :
	#{
		self.position += 1

		if self.position < len(self.text) :
			retval = self.text[self.position]
			if retval == '' :
				return '\n'
			else :
				return retval
		else :
			return ''
	#}
#}

class pawnParse:
#{
	def __init__(self):
		self.save_const_timer = None
		self.constants_count = 0
		
		self.DEBUG_PERF_ENUM = 0
		self.DEBUG_PERF_VARS = 1
		self.DEBUG_PERF_FUNC = 2
		
		self.PARAMS_regex 		= re.compile("(const\s*)?([A-Za-z_][\w_]*)")
		self.DEFINE_regex 		= re.compile("#define[\s]+([^\s]+)[\s]+(.+)")
		self.GET_NAME_regex 	= re.compile("([A-Za-z_][\w_]*)")
		self.VALID_NAME_regex 	= re.compile("^[A-Za-z_][\w_]*$")
		
		self.invalidNames = [ "new", "const", "static", "stock", "enum", "public", "native", "forward", "if", "else", "for", "while", "switch", "case", "return", "continue" ]
		
	def start(self, pFile, node):
	#{
		# Debug performance
		self.total_perf			= time.perf_counter()
		self.start_perf			= [ 0.0, 0.0, 0.0]
		self.performance		= [ 0.0, 0.0, 0.0]
		###############################################
		
		self.file 				= pFile
		self.file_name			= os.path.basename(node.file_name)
		self.node 				= node
		self.found_comment 		= False
		self.found_enum 		= False
		self.enum_contents 		= ""
		self.line_position 		= 0
		self.start_position		= 0
		self.line_org_len		= 0
		self.region_multiline	= False
		self.region_fix_skip	= False
		self.string_regions		= [ ]
		self.mark_regions		= [ ]
		self.restore_buffer 	= ""
		self.view				= None

		view = sublime.active_window().active_view()
		if view.file_name() == self.node.file_name :
			self.view = view
		
		self.node.autocompletion.clear()
		self.node.functions.clear()
		self.mark_clear()
		
		if self.constants_count != len(g_constants_list) :
		#{
			if self.save_const_timer :
				self.save_const_timer.cancel()
			
			self.save_const_timer = Timer(4.0, self.save_constants)
			self.save_const_timer.start()
		#}

		
		print_debug(1, "(analyzer) CODE PARSE  Start! \t-  \"%s\" ->" % self.file_name)
		
		self.start_parse()
		
		print_debug(1,
		"(analyzer) CODE PARSE  End! \t\t-  total:(%.3fsec), enum:(%.3fsec), vars:(%.3fsec), func:(%.3fsec)" % (
		(time.perf_counter() - self.total_perf),
		self.performance[self.DEBUG_PERF_ENUM],
		self.performance[self.DEBUG_PERF_VARS],
		self.performance[self.DEBUG_PERF_FUNC]
		))
	#}
	
	def debug_performance(self, start, type):
	#{
		if start :
			self.start_perf[type] = time.perf_counter()
		else :
			self.performance[type] += (time.perf_counter() - self.start_perf[type])
	#}
	
	def debug_print(self, level, func, info):
		print_debug(level, "(analyzer) %s:  < %s >  -  line:(%d-%d)" % (func, info, self.start_position, self.line_position))
	
	def save_constants(self):
	#{
		self.save_const_timer 	= None
		self.constants_count 	= len(g_constants_list)
		
		constants = "___test"
		for const in g_constants_list :
			constants += "|" + const
			
		syntax = "%YAML 1.2\n---\nscope: source.sma\ncontexts:\n  main:\n    - match: \\b(" + constants + ")\\b\n      scope: constant.vars.pawn"
		
		file_name = sublime.packages_path() + "/amxmodx/const.sublime-syntax"
		
		f = open(file_name, 'w')
		f.write(syntax)
		f.close()
		
		print_debug(2, "(analyzer) call save_constants()")
	#}

	def mark_add(self, line_start, line_end=None):
	#{
		if not self.view :
			return
			
		if line_end == None :
			line_end = self.line_position
		
		begin = self.view.text_point(line_start-1, 0)
		if line_end > line_start :
			end = self.view.text_point(line_end-1, 0)
		else :
			end = begin + self.line_org_len + 1
			
		r = sublime.Region(begin, end)
		
		self.mark_regions += [ r ]
		self.view.add_regions("pawnmark", self.mark_regions, "invalid.illegal", "dot", sublime.PERSISTENT)
	#}
		
	def mark_clear(self):
	#{
		if not self.view :
			return
			
		self.view.erase_regions("pawnmark")
		self.mark_regions = [ ]
	#}
		
	def read_line(self):
	#{
		if self.restore_buffer :
			line = self.restore_buffer
			self.restore_buffer = ""
		else :
			self.line_position += 1
			line = self.file.readline()
			
		self.line_org_len = len(line)
		if self.line_org_len > 0 :
			return line
		else :
			return None
	#}
			
	def read_string(self):
	#{
		buffer = self.read_line()
		
		if buffer is None :
			return None
		
		buffer = buffer.replace('\t', ' ')
		while '  ' in buffer :
			buffer = buffer.replace("  ", ' ')
			
		result = ""
		
		pos = -1
		total = 0
		start_valid = 0
		start_coment = -1
			
		self.region_fix_skip = self.region_multiline
		self.calculate_regions(buffer)
		
		# REMOVE Coments
		while True :
		#{
			if self.found_comment :
			#{
				pos = buffer.find("*/", pos+1)
				if pos != -1 :
					if not self.intersect_regions(pos) :
						start_valid = (pos + 2)
						total += start_valid - start_coment
						self.found_comment = False
				else :
					break
			#}
			else :
			#{
				start_coment = buffer.find("/*", start_coment+1)
				if start_coment != -1 :
					if not self.intersect_regions(start_coment) :
						result += buffer[start_valid:start_coment]
						self.found_comment = True
				else :
					break
			#}
		#}
		
		if not self.found_comment :
			result += buffer[start_valid:]
		
		pos = -1
		while True :
		#{
			pos = result.find("//", pos+1)
			if pos != -1 :
				if not self.intersect_regions(pos+total) :
					start_coment = pos+total
					result = result[0:pos]
					break
			else :
				break
		#}
		
		result = result.strip()
		
		#print("org: [%s] vs [%s]" % (org , result))

		if not result :
			result = self.read_string()

		return result
	#}
	
	def calculate_regions(self, buffer):
	#{
		start = -1
		if self.region_multiline :
			self.region_multiline = False
			start = 0
	
		self.string_regions = []
		
		pos = buffer.find('"')

		while pos != -1 :
		#{
			if not pos or buffer[pos - 1] != '^' :
			#{
				if start == -1 :
					start = pos
				else :
					self.string_regions += [ [ start, pos ] ]
					start = -1
			#}

			pos = buffer.find('"', (pos + 1))
		#}

		if start != -1 and buffer[len(buffer)-1] == '\\':
			self.string_regions += [ [ start, len(buffer)-1 ] ]
			self.region_multiline = True
	#}
	
	def intersect_regions(self, pos):
	#{
		if not self.string_regions :
			return False
			
		for r in self.string_regions :
			if r[0] <= pos and pos <= r[1] :
				return True
			
		return False
	#}
		
	def skip_function_block(self, buffer):
	#{
		num_brace = 0
		inString = False
		localvars = []
		invalidKeywords = [ "stock", "public", "native", "forward" ]

		if not buffer :
			buffer = self.read_string()
			
		if not buffer or buffer[0] != '{' :
			return localvars
				
		while buffer :
		#{
			if buffer.split(' ', 1)[0] in invalidKeywords :
				self.restore_buffer = buffer
				return self.function_block_finish(localvars)
			
			if g_AC_local_var :
				while buffer.startswith("new ") or buffer.startswith("static ") or buffer.startswith("for") :
				#{
					pos = 0
					if buffer.startswith("for") :
						pos = buffer.find("new ")
		
					if pos == -1 :
						break
						
					localvars += self.parse_variable(buffer[pos:], True)
		
					buffer = self.read_string()
					if not buffer :
						return self.function_block_finish(localvars)
				#}
			
			#print("buff: [%s]" % buffer)
			
			old = self.region_multiline
			self.region_multiline = self.region_fix_skip
			self.calculate_regions(buffer)
			self.region_multiline = old
			
			pos = buffer.find('{')
			while pos != -1 :
			#{
				if not self.intersect_regions(pos) and (not pos or buffer[pos - 1] != "'") :
					num_brace += 1
					
				pos = buffer.find('{', (pos + 1))
			#}
				
			pos = buffer.find('}')
			while pos != -1 :
			#{
				if not self.intersect_regions(pos) and (not pos or buffer[pos - 1] != "'") :
					num_brace -= 1
					
				pos = buffer.find('}', (pos + 1))
			#}
				
			
			if num_brace <= 0 :
			#{
				self.restore_buffer = buffer[pos:]
				return localvars
			#}
			
			buffer = self.read_string()
		#}
		
		return self.function_block_finish(localvars)
	#}
	
	def function_block_finish(self, localvars):
		self.mark_add(self.start_position)
		
		self.debug_print(1, "ERROR: parse_function", "bad function closed detected, misses '}'")
		
		return localvars
	
	def valid_name(self, name):
	#{
		if not name :
			return False
			
		if name in self.invalidNames :
			return False
			
		return self.VALID_NAME_regex.search(name) is not None
	#}
	
	def add_constant(self, name):
	#{
		fixname = self.GET_NAME_regex.search(name)
		if fixname :
			name = fixname.group(1)
			g_constants_list.add(name)
	#}
	
	def add_enum(self, buffer, line):
	#{
		buffer = buffer.strip()
		if not buffer :
			return
			
		split = buffer.split('[')
		
		if not self.valid_name(split[0]) :
			self.mark_add(self.start_position+line-1, self.start_position+line)
			self.debug_print(1, "ERROR: parse_enum", "invalid enum name [%s]" % split[0])
			return

		self.add_autocompletion(buffer, "enum", split[0])
		self.add_constant(split[0])
		
		self.debug_print(2, "INFO: parse_enum", "add -> [%s]" % split[0])
	#}
	
	def add_autocompletion(self, name, info, autocompletion):
	#{
		self.node.autocompletion.add((name +"\t "+  self.file_name +" - "+ info + " ", autocompletion))
	#}
		
	def start_parse(self):
	#{
		while True :
		#{
			buffer = self.read_string()

			if buffer is None :
				return
				
			#if "sma" in self.node.file_name :
			#	print("read: [%s]" % (buffer))

				
			self.start_position = self.line_position
			
			# Fix XS include (Temp!)
			buffer = buffer.replace("XS_LIBFUNC_ATTRIB", "stock")
			
			if buffer.startswith("#pragma deprecated") :
				buffer = self.read_string()
				if buffer and self.startswith(buffer, "stock") :
					self.parse_function(buffer, -1)
			elif buffer.startswith("#define ") :
				buffer = self.parse_define(buffer)
			elif buffer.startswith("enum") :
				self.parse_enum(buffer)
			elif self.startswith(buffer, "const") :
				buffer = self.parse_const(buffer)
			elif self.startswith(buffer, "new") :
				self.parse_variable(buffer, False)
			elif self.startswith(buffer, "public") :
				self.parse_function(buffer, 1)
			elif self.startswith(buffer, "stock") :
				self.parse_function(buffer, 2)
			elif self.startswith(buffer, "forward") :
				self.parse_function(buffer, 3)
			elif self.startswith(buffer, "native") :
				self.parse_function(buffer, 4)
			elif buffer[0] == '_' or buffer[0].isalpha() :
				self.parse_function(buffer, 0)
		#}
	#}
	
	def startswith(self, buffer, str):
	#{
		if not buffer.startswith(str) :
			return False
			
		if len(str) == len(buffer) :
			return True
			
		if buffer[len(str)] == ' ' :
			return True
			
		return False
	#}
	
	def parse_define(self, buffer):
	#{
		define = self.DEFINE_regex.search(buffer)
		if define :
		#{
			name = define.group(1)
			value = define.group(2).strip()
			self.add_autocompletion(name, "define: "+value, name)
			self.add_constant(name)
			
			self.debug_print(2, "INFO: parse_define", "add -> [%s]" % name)
		#}
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
		
		self.add_autocompletion(name, "const: "+value, name)
		self.add_constant(name)
		self.debug_print(2, "INFO: parse_const", "add -> [%s]" % name)
	#}

	def parse_variable(self, buffer, local):
	#{
		self.debug_performance(True, self.DEBUG_PERF_VARS)
		
		classChecked	= False
		varName 		= ""
		
		oldChar 		= ''
		i 				= 0
		pos 			= 0
		
		num_bracket		= 0
		num_parent		= 0
		num_brace 		= 0
		checkMissComa	= False
		emptyValue		= True
		multiLines 		= True
		skipSpaces 		= False
		skipValue 		= False
		parseName 		= True
		inBrackets 		= False
		inParents		= False
		inBraces 		= False
		inString 		= False
		found_line 		= self.line_position
		localvars		= [ ]
		
		buffer = buffer.replace("new", "", 1).replace("static", "", 1).strip()
		if not buffer :
		#{
			buffer = self.read_string()
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
				
				#print("A:: varName[%s] buff[%s] c[%s] - inString %d inBrackets %d inBraces %d inParents %d skipValue %d skipSpaces %d parseName %d" % (varName, buffer, c, inString, inBrackets, inBraces, inParents, skipValue, skipSpaces, parseName ))

				
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
						num_parent += 1
						inParents = True
					elif c == ')' :
						num_parent -= 1
						if num_parent == 0 :
							inParents = False
				#}
				
				if inString or inBrackets or inBraces or inParents :
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
							return self.vars_force_finish(found_line, localvars)
						emptyValue = True
						skipValue = False
					else :
						if c != ' ' :
							emptyValue = False
						continue
				#}
				
				if checkMissComa and c.isalpha() :
					return self.vars_force_finish(found_line, localvars)
				
		
				#print("B:: varName[%s] buff[%s] c[%s] - inString %d inBrackets %d inBraces %d inParents %d skipValue %d skipSpaces %d parseName %d" % (varName, buffer, c, inString, inBrackets, inBraces, inParents, skipValue, skipSpaces, parseName ))
				
				
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
								return self.vars_force_finish(found_line, localvars)
								
							varName = ""
						#}
						else :
							checkMissComa = True
					#}
					elif c == '=' or c == ';' or c == ',' :
					#{
						varName = varName.strip()
						
						if varName != "" :
						#{
							if not self.valid_name(varName) :
								return self.vars_force_finish(found_line, localvars)
							else :
							#{
								if local :
									localvars += [ varName ]
									found_line = self.line_position
								else :
									self.add_autocompletion(varName, "var", varName)
									self.debug_print(2, "INFO: parse_variable", "add1 -> [%s]" % varName)
									
								checkMissComa = False
								classChecked = False
							#}
						#}
						else :
							return self.vars_force_finish(found_line, localvars)
							
						varName = ""
						parseName = False
						skipSpaces = True

						if c == '=' :
							skipValue = True
					#}
					elif c != ']' :
						varName += c
				#}
				
				
				#print("C:: varName[%s] buff[%s] c[%s] - inString %d inBrackets %d inBraces %d inParents %d skipValue %d skipSpaces %d parseName %d" % (varName, buffer, c, inString, inBrackets, inBraces, inParents, skipValue, skipSpaces, parseName ))

				
				if not inString and not inBrackets and not inBraces and not inParents :
				#{
					if not parseName :
						if c == ';' :
							self.restore_buffer = buffer[i:].strip()
							self.debug_performance(False, self.DEBUG_PERF_VARS)
							return localvars
						elif not skipSpaces and not skipValue and c != ' ' and c != ',' :
							return self.vars_force_finish(found_line, localvars)
	
				
					if c == ',' :
						skipSpaces = True
				#}

			#}
			
			if not inString and not inBrackets and not inBraces and not inParents and c != '=':
				skipValue = False
					
			if inString or inBrackets or inBraces or inParents or skipValue :
				multiLines = True
				
			if inString and c != '\\' :
				return self.vars_force_finish(found_line, localvars)
				
			#print("D:: varName[%s] buff[%s] c[%s] - inString %d inBrackets %d inBraces %d inParents %d skipValue %d skipSpaces %d parseName %d multiLines %d" % (varName, buffer, c, inString, inBrackets, inBraces, inParents, skipValue, skipSpaces, parseName, multiLines ))
			

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
							return self.vars_force_finish(found_line, localvars)
								
						varName = ""
						parseName = True
						multiLines = True
					#}
					elif not self.valid_name(varName) :
						return self.vars_force_finish(found_line, localvars)
					else :
					#{
						if local :
							localvars += [ varName ]
							found_line = self.line_position
						else :
							self.add_autocompletion(varName, "var", varName)
							self.debug_print(2, "INFO: parse_variable", "add2 -> [%s]" % varName)
							
						checkMissComa = False
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

			buffer = self.read_string()
			if not buffer :
				self.debug_performance(False, self.DEBUG_PERF_VARS)
				return localvars
				
			if (skipValue or inBrackets or inBraces or inParents) :
				if buffer[0] == '#' or buffer.split(' ', 1)[0] in self.invalidNames or buffer.split('(', 1)[0] in self.invalidNames :
					self.restore_buffer = buffer
					return self.vars_force_finish(found_line, localvars)
			
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
					return self.vars_force_finish(found_line, localvars)
				
			#print("E:: varName[%s] buff[%s] c[%s] - inString %d inBrackets %d inBraces %d inParents %d skipValue %d skipSpaces %d parseName %d multiLines %d" % (varName, buffer, c, inString, inBrackets, inBraces, inParents, skipValue, skipSpaces, parseName, multiLines ))
			
		#}
		
		self.debug_performance(False, self.DEBUG_PERF_VARS)
		
		return localvars
	#}
	
	def vars_force_finish(self, found_line, localvars):
		self.mark_add(found_line)
		self.debug_print(1, "ERROR: parse_vars", "invalid sintax")
		
		self.debug_performance(False, self.DEBUG_PERF_VARS)
		
		return localvars
	
	def parse_enum(self, buffer):
	#{
		self.debug_performance(True, self.DEBUG_PERF_ENUM)
		
		if len(buffer) != 4 and buffer[4] != '{' and buffer[4] != ' ' :
			return
	
		contents = ""
		enum = ""
		ignore = True
	
		while buffer :
		#{
			if not ignore and buffer.split(' ', 1)[0] in self.invalidNames :
				self.restore_buffer = buffer
				self.mark_add(self.start_position)
				self.debug_print(1, "ERROR: parse_enum", "bad enum closed detected, misses '}'")
				self.debug_performance(False, self.DEBUG_PERF_ENUM)
				return
			
			pos = buffer.find('}')
			
			if pos == -1 :
				contents = "%s\n%s" % (contents, buffer)
				buffer = self.read_string()
			else :
				contents = "%s\n%s" % (contents, buffer[0:pos])
				self.restore_buffer = buffer[pos+1:].strip("; ")
				break
				
			ignore = False
		#}

		pos = contents.find('{')
		line = contents[0:pos].count('\n')
		contents = contents[pos + 1:]
		
		for c in contents :
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
				self.add_enum(enum, line)
				enum = ""
					
				ignore = False
				continue

			if not ignore :
				enum += c
		#}

		self.add_enum(enum, line-1)
		
		self.debug_performance(False, self.DEBUG_PERF_ENUM)
	#}
	
	def parse_function(self, buffer, type):
	#{
		self.debug_performance(True, self.DEBUG_PERF_FUNC)
		
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

			buffer = self.read_string()
		#}

		if full_func_str :
			self.parse_function_params(buffer, full_func_str, type)
			
		self.debug_performance(False, self.DEBUG_PERF_FUNC)
	#}
	
	def parse_function_params(self, buffer, func, type):
	#{
		if type == 0 :
			remaining = func
		else :
			split = func.split(' ', 1)
			remaining = split[1]
		
		split = remaining.split('(', 1)
		if len(split) < 2 :
			self.debug_print(1, "ERROR: parse_function_params", "return1 [%s]" % split)
			return
			
		remaining = split[1]
		returntype = ''
		funcname_and_return = split[0].strip()
		split_funcname_and_return = funcname_and_return.split(':')
		if len(split_funcname_and_return) > 1 :
			funcname = split_funcname_and_return[1].strip()
			returntype = split_funcname_and_return[0].strip()
		else :
			funcname = split_funcname_and_return[0].strip()
			
		# Fix float.inc
		if funcname.startswith("operator") :
			self.skip_function_block(buffer)
			return
			
		if not self.valid_name(funcname) :
			self.debug_print(1, "ERROR: parse_function_params", "invalid name: [%s] - buffer[%s]" % (funcname, buffer))
			return
	
		if type == -1 : # Deprecated !
			self.skip_function_block(buffer)
		else :
		#{
			remaining = remaining.strip()
			if remaining == ')' :
				params = []
			else :
				params = remaining[:-1].split(',')

			params_list = [ ]
				
			autocompletion = funcname + '('
			i = 1
			for param in params :
				param_var = param.strip()
				
				if i > 1 :
					autocompletion += ', '
				autocompletion += '${%d:%s}' % (i, param_var)
				i += 1

				result = self.PARAMS_regex.match(param_var)
				if result :
					params_list += [ result.group(2) ]

			autocompletion += ')'
			funcparams = func[func.find("(")+1:-1]
			
			self.add_autocompletion(funcname, FUNC_TYPES[type].lower(), autocompletion)
			self.debug_print(2, "INFO: parse_function_params", "add -> [%s]" % func)
			
			# Function Block&Local vars #############
			endline = startline = self.start_position
			
			localvars = [ ]
			
			if type <= 2 :
				localvars 	= self.skip_function_block(buffer)
				endline 	= self.line_position
				
			localvars += params_list

			self.node.functions.add((funcname, funcparams, self.node.file_name, type, returntype, startline, endline, tuple(localvars)))
		#}
	#}
#}

def process_buffer(text, node):
#{
	text_reader = TextReader(text)
	pawnparse.start(text_reader, node)
#}

def process_include_file(node):
#{
	with open(node.file_name, 'r', encoding="utf-8", errors="replace") as file :
		pawnparse.start(file, node)
#}

def print_debug(level, msg):
#{
	if g_debug_level >= level :
		print("[AMXX-Editor - %s]: %s" % (time.strftime("%H:%M:%S"), msg))
#}

EDITOR_VERSION 		= "3.0"
FUNC_TYPES 			= [ "Function", "Public", "Stock", "Forward", "Native" ]

STYLES_POPUP		= [ "white", "dark" ]
STYLES_EDITOR		= [ "default", "dark", "npp" ]
STYLES_CONSOLE		= [ "default", "dark" ]

g_style_popup 		= { "list": [ ], "count": 0, "active": "" }
g_style_editor 		= { "list": [ ], "count": 0, "active": "" }
g_style_console 	= { "list": [ ], "count": 0, "active": "" }


g_constants_list 	= set()
g_includes_list		= list()
g_popupCSS 			= ""
g_AC_enable				= False
g_AC_keywords			= 2
g_AC_local_var 			= False
g_AC_begin_explicit 	= False
g_enable_inteltip 		= False
g_enable_buildversion 	= False
g_debug_level 		= 0
g_delay_time 		= 1.5
g_include_dir 		= "."
g_invalid_settings	= False
g_ignore_settings 	= False
g_edit_settings 	= False
g_check_update		= False

g_to_process 		= OrderedSetQueue()
g_nodes 			= dict()
gWatchdogObserver 	= watchdog.observers.Observer()
gProcessQueueThread = ProcessQueueThread()
gObserverHandler 	= IncludeFileEventHandler()
INC_regex 			= re.compile('^[\\s]*#include[\\s]+[<"]([^>"]+)[>"]', re.M)
INC_LOCAL_regex 	= re.compile('\\.(sma|inc)$')
pawnparse 			= pawnParse()


