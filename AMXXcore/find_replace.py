import os
import re
import sublime, sublime_plugin

from AMXXcore.core import *

class AmxxFindReplace:
	def __init__(self, window):
		self.window 		= window
		self.view 			= None
		self.quickpanel 	= False
		self.last_error		= ""
		self.search 		= ""
		self.search_pattern = ""
		self.search_type 	= 0
		self.replace 		= None
		self.initial_text 	= ""
		self.original_view 	= [ ]
		self.result 		= [ ]
		self.quicklist		= [ ]


	def process(self, input, errorcheck=False):
	
		self.search 		= ""
		self.search_pattern = ""
		self.search_type 	= 0
		self.replace 		= None

		if not input:
			return None
		
		
		search_flags = re.MULTILINE
		
		r = input.split("::replace::", 1)
		self.search = r[0]
		if len(r) == 2 :
			self.replace = r[1]
			
		if self.search.startswith("word::") :
			self.search = self.search[6:]
			self.search_type = 2
			self.search_pattern = r"\b" +re.escape(self.search)+ r"\b"
				
		elif self.search.startswith("re::") :
			self.search_type = 1
			self.search_pattern = self.search = self.search[4:]
		else :
			self.search_pattern = r"([a-zA-Z_]*)(" +re.escape(self.search)+ r")(\w*)"
			if not self.replace == None :
				self.replace = r"\1" +self.replace+ r"\3"
			search_flags |= re.IGNORECASE
		
		if len(self.search) < 2 :
			return "minimum 2 characters"
			
		self.initial_text = input
			
		try:
			self.regex = re.compile(self.search_pattern, search_flags)
		except Exception as e:
			return "Regex -> " + str(e).title()
			
		if errorcheck :
			return None # high CPU usage if is tested the down code in preview

		self.result 	= [ ]
		includes 		= self.get_includes(self.view, True)

		for inc in includes :
			text = self.read_text(inc)
			self.result += self.search_all(text, inc)
			if len(self.result) >= 512 :
				break
				
		if not self.result :
			self.last_error = "Search not found"
			return self.last_error
			
		if self.replace == None :
			self.quicklist = [ [ "- Total Results:  %d" % len(self.result), "Search: %s" % self.search ] ]
		
			for result in self.result :
				self.quicklist += [ [ result[0], os.path.basename(result[3]) ] ]
			
		else :
			self.quicklist = [ [ "Replace All? :  NO" , ""] ]
			self.quicklist += [ [ "Replace All? :  YES" , "" ] ]
			self.quicklist += [ [ "- Total Results:  %d" % len(self.result), "Search: %s  -  Replace: %s" % (self.search, r[1]) ] ]
			
			if self.search_type == 1 :
				for result in self.result :
					try:
						preview = self.regex.sub(self.replace, result[0])
					except Exception as e:
						self.last_error = "RegexReplace -> " + str(e).title()
						return self.last_error
						
					self.quicklist += [ [ "", result[0] + "  ->  " + preview ] ]
			else :
				for result in self.result :
					self.quicklist += [ [ "", result[0] + "  -  " + os.path.basename(result[3]) ] ]
					
		sublime.set_timeout(self.show_delayed_fix, 100) # Fix bug
		return None

	def show_delayed_fix(self):
		self.window.run_command("hide_overlay")
		region = self.view.sel()[0]
		scroll = self.view.viewport_position()
		self.original_view = [ self.view, region, scroll ]
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
				
			id = util.goto_definition(self.result[index][3], "", (self.result[index][1], self.result[index][2]), False)
			
			if id != self.original_view[0].id() :
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
		
		util.goto_definition(self.result[index][3], "", (self.result[index][1], self.result[index][2]), True)
		
	def restore_org(self, focus=False):
		if self.original_view :
			view 	= self.original_view[0]
			region 	= self.original_view[1]
			scroll 	= self.original_view[2]
				
			if focus :
				self.window.focus_view(view)
				
			view.sel().clear()
			view.sel().add(region)
			view.set_viewport_position(scroll, False)
				
			self.original_view = []
	
	def confirm_replace(self):
	
		includes = self.get_includes(self.view)
		
		for inc in includes :
			text = self.read_text(inc)
			try:
				text = self.regex.sub(self.replace, text)
				self.write_text(text, inc)
			except Exception as e:
				self.last_error = "RegexReplace -> " + str(e).title()
				self.window.run_command("amxx_find_replace")
				return
			
	def search_all(self, text, file):
		
		result = [ ]
		count = 0

		for match in self.regex.finditer(text) :
			if self.search_type == 0 :
				result += [ [ match.group(0), match.start(2), match.end(2), file ] ]
			else :
				result += [ [ match.group(0), match.start(), match.end(), file ] ]
			count += 1
			if count > 256 :
				self.window.status_message(" ALERT! (%s) Find stopet at 256 results" % file)
				break

		return result
		
	def read_text(self, file_path):
	
		view = util.get_open_view_by_filename(file_path, self.window)
		if view  :
			return view.substr(sublime.Region(0, view.size()))
		
		try:
			with open(file_path, encoding="utf-8", errors="replace") as f :
				return f.read()
		except:
			pass
	
		return ""
		
	def write_text(self, text, file_path):
	
		view = util.get_open_view_by_filename(file_path, self.window)
		if view :
			scroll = view.viewport_position()
			
			view.run_command("select_all")
			view.run_command("left_delete")
			view.run_command('append', {'characters': text, 'force': True, 'scroll_to_end': False})
			
			view.set_viewport_position(scroll, False)
		else :
			try:
				with open(file_path, encoding="utf-8", errors="replace") as f :
					f.write(text)
			except:
				pass
		
	def get_includes(self, view, includedir=False):
		includes 	= [ ]
		visited 	= [ ]
		node 		= globalvar.nodes[util.get_filename_by_view(view)]

		self.includes_recur(node, includes, visited, includedir)
		
		return includes
		
	def includes_recur(self, node, includes, visited, includedir) :
		if node.file_path in visited :
			return

		visited += [ node.file_path ]

		if includedir or cfg.include_dir != os.path.dirname(node.file_path) :
			includes += [ node.file_path ]

		for child in node.children :
			self.includes_recur(child, includes, visited, includedir)

######################################################################○





