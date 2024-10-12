import sublime
import sublime_plugin
import os
import shutil
import re


base_html = """\
<style>
html {
    background-color: var(--background);
    margin: 16px;
}
body {
    color: var(--foreground);
    font-family: "Open Sans", "Helvetica Neue", "Segoe UI", Helvetica, Arial, sans-serif;
}
ul {
    padding-left: 1.2rem;
}
li { margin: 2px; }
li ul {
    margin: 2px 0 4px;
}
ul.topic {
    margin-top: 0;
    padding-left: 1.5rem;
}
ul.topic ul {
    margin: 0.2em 0;
}
h1 {
    color: color(var(--foreground) l(- 10%));
    font-size: 2.0rem;
    margin: 0;
}
html.dark h1 {
    color: color(var(--foreground) l(+ 10%));
}
h2 {
    color: color(var(--foreground) a(0.9));
    font-size: 1.4rem;
    margin: 1em 0 0.1em 0;
}
a {
    color: var(--bluish);
}
article { display: block; }
.release-date, .forum-link {
    font-size: 0.9rem;
    font-style: italic;
    color: color(var(--foreground) a(0.7));
}
tt {
    font-size: 0.9em;
    border-radius: 2px;
    background-color: rgba(0, 0, 0, 0.08);
    padding: 0 4px;
}
html.dark tt {
    background-color: rgba(255, 255, 255, 0.1);
}
</style>

<h1>Changelog</h1>
"""

def show_changelog(resource_path):

	# Asegurarnos de que el resource_path comience con "Packages/"
	if not resource_path.startswith("Packages/"):
		print(f"Error: El resource_path debe comenzar con 'Packages/', recibido: {resource_path}")
		return
	
	try:
		# Cargar el contenido del changelog personalizado
		#custom_content = sublime.load_binary_resource(resource_path)
		custom_content = sublime.load_resource(resource_path)
	except Exception as e:
		print(f"Error al cargar el recurso {resource_path}: {str(e)}")
		return

	# Format html
	custom_content = re.sub(r'^(\w+:)', r'<b>\1</b>', custom_content, flags=re.MULTILINE)
	custom_content = re.sub(r"`([^`]*)`", r"<tt>`\1`</tt>", custom_content)
	
	html_content = ""
	tag_open = False
	for line in custom_content.splitlines() :
		if not line :
			if tag_open :
				html_content += "</ul>\n</article>\n\n"
				tag_open = False
		elif line.startswith("v") :
			html_content += f"<article>\n<h2>{line}</h2>\n<ul>\n"
			tag_open = True
		else :
			html_content += f"<li>{line}</li>\n"
			
	if tag_open :
		html_content += "</ul></article>"
	

	html_content = base_html + html_content

	# Definir la ruta del changelog original de Sublime
	original_changelog = os.path.join(os.path.dirname(sublime.executable_path()), "changelog.txt")
	backup_changelog = original_changelog + '.backup'
	
	try:
		# Hacer backup del changelog original si existe
		if os.path.exists(original_changelog):
			shutil.copy2(original_changelog, backup_changelog)
		
		# Escribir el nuevo contenido al archivo changelog.txt
		with open(original_changelog, "w", encoding="utf-8", errors="replace") as f:
			f.write(html_content)
		
		# Mostrar el changelog
		sublime.active_window().run_command('show_changelog')
		
	finally:
		# Restaurar el changelog original
		if os.path.exists(backup_changelog):
			shutil.move(backup_changelog, original_changelog)


class ShowAmxxChangelogCommand(sublime_plugin.WindowCommand):
	def run(self, file):
		show_changelog(file)

		# sublime.active_window().run_command("show_amxx_changelog", { "file": "Packages/AMXXEditorV4/changelog.txt"})
		# sublime.active_window().run_command("show_amxx_changelog", { "file": "Packages/AMXXEditorV4/changelog_es.txt"})
		