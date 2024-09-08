import os
import time
import threading
import sublime, sublime_plugin
import jstyleson
import hashlib

#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# Global VARs 
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
class globalvar:
	pass
	
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# Config/Settings
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
class cfg:
	filename = "AMXX-Editor.sublime-settings"
	settings = None
	on_change_callback = None
	silent = False
	
	
	# Support reloading module
	def init(on_change_callback=None):
	
		cfg.on_change_callback = on_change_callback

		if cfg.settings :
			cfg.on_change()
			return
			
		cfg.settings = sublime.load_settings(cfg.filename)
		cfg.settings.add_on_change("hellokey", cfg.on_change)
		cfg.on_change()
		
	def on_change():
		if cfg.silent :
			cfg.silent = False
			return
		
		if cfg.on_change_callback :
			cfg.on_change_callback()
		
	def set(key, value):
		cfg.silent = True
		if value == None:
			cfg.settings.erase(key)
		else :
			cfg.settings.set(key, value)
		
	def get(key, default=None):
		return cfg.settings.get(key, default)
	
	def save(silent=True):
		cfg.silent = silent
		sublime.save_settings(cfg.filename)
		
	def get_path(key) :
		return util.cfg_get_path(cfg.settings, key)
	
	
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# Functions Utility
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
class util:

	def hash_sha1(value):
		hasher = hashlib.sha1()

		if isinstance(value, (list, tuple)):
			# Itera sobre cada elemento en la lista o tupla
			for item in value:
				if not isinstance(item, str):
					raise TypeError("All elements in the list or tuple must be strings.")
				hasher.update(item.encode('utf-8'))
		elif isinstance(value, str):
			hasher.update(value.encode('utf-8'))
		else:
			raise TypeError("simple_hash_sha1 only supports strings, lists, or tuples of strings.")
    
		return hasher.hexdigest()
			
	def clamp(value, minv, maxv):
		return max(min(value, maxv), minv)
	
	def cfg_set_key(filename, key, value):
		s = SublimeSettings(filename)
		s.set(key, value)
		s.save()
		
	def cfg_get_path(_dict, key) :
		path = _dict.get(key, None)
		
		if not path or path == "${file_path}" :
			return path

		path = path.replace("${packages}", sublime.packages_path())

		return os.path.normpath(path)
	
	def unix_normpath(path):
		return os.path.normpath(path).replace('\\', '/')
		
	def get_open_view_by_filename(filename, window=None):
		# From Buffer
		if filename.startswith("View->"):
			return sublime.View(int(filename[6:]))

		if not window :
			window = sublime.active_window()
			
		return window.find_open_file(filename)
		
	def get_filename_by_view(view):
		if view.file_name() :
			return view.file_name()
			
		# From Buffer
		return "View->" + str(view.id())

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

	def safe_json_load(path):
		try :
			json = sublime.load_binary_resource(path).decode("utf-8", "replace")
			return jstyleson.loads(json)
		except:
			pass
		return None
		
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# Others Class/Utility
#::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

class Enum(tuple): 
	def __getattr__(self, name):
		try:
			return self.index(name)
		except:
			return None

			
class SublimeSettings:
	def __init__(self, filename):
		self.filename = filename
		self.settings = sublime.load_settings(filename)
			
	def set(self, key, value):
		if value == None:
			self.settings.erase(key)
		else :
			self.settings.set(key, value)
		
	def get(self, key, default=None):
		return self.settings.get(key, default)
	
	def save(self):
		sublime.save_settings(self.filename)
		
class CustomSettings:
	def __init__(self, filename, clear=False):
		self.path = os.path.join(sublime.packages_path(), "User", filename)
		
		if not clear :
			try:
				with open(self.path) as f:
					self.data = jstyleson.load(f)
			except:
				self.data = dict()
		else :
			self.data = dict()

	def save(self):
		with open(self.path, 'w', encoding='utf-8') as f:
			jstyleson.dump(self.data, f, ensure_ascii=False, indent=4)
		
	def clear(self):
		self.data.clear()
		
	def set(self, key, value):
		if value == None:
			try:
				del self.data[key]
			except:
				pass
		else :
			self.data[key] = value

	def get(self, key, default=None):
		return self.data.get(key, default)
		
class DelayedTimer(threading.Thread):
	def __init__(self, delay_time, function, *args, **kwargs):
		threading.Thread.__init__(self)
		
		self.event = threading.Event()
		self.daemon=True
		self.stoped=False
		self.next_time=0
	
		self.delay_time = delay_time
		self.function = function
		self.args = args
		self.kwargs = kwargs
		
		self.start()
		
	def update_args(self, *args, **kwargs):
		self.args = args
		self.kwargs = kwargs
			
	def touch(self, reset=True):
	
		if reset or not self.next_time:
			self.next_time = time.time() + self.delay_time

		self.event.set()
		
	def cancel(self):
		self.next_time = 0
		self.event.clear()
		
	def stop(self):
		self.stoped = True
		self.event.set()
		
	def run(self):
	
		while not self.stoped :
		
			self.event.wait()
	
			if self.stoped :
				return
				
			while (self.next_time - time.time()) > 0.05 :
				time.sleep(self.next_time - time.time())

			self.next_time = 0
	
			if not self.event.is_set() or self.stoped :
				continue

			self.event.clear()
			self.function(*self.args, **self.kwargs)
	
