import sublime
import sublime_plugin
import urllib.request
import uuid
import os
import threading
import re

LYSIS_URL = "https://headlinedev.xyz/lysis/upload.php"

# ── Helpers ────────────────────────────────────────────────────────────────────

def _build_multipart(file_path):
	boundary = uuid.uuid4().hex
	filename  = os.path.basename(file_path)

	with open(file_path, "rb") as fh:
		file_data = fh.read()

	CRLF = b"\r\n"

	body = (
		f"--{boundary}".encode() + CRLF +
		f'Content-Disposition: form-data; name="fileToUpload"; filename="{filename}"'.encode() + CRLF +
		b"Content-Type: application/octet-stream" + CRLF +
		CRLF +
		file_data + CRLF +
		f"--{boundary}".encode() + CRLF +
		b'Content-Disposition: form-data; name="submit"' + CRLF +
		CRLF +
		b"Decompile" + CRLF +
		f"--{boundary}--".encode() + CRLF
	)
	content_type = f"multipart/form-data; boundary={boundary}"
	return body, content_type


def _strip_html(html):
	pre = re.search(r"<pre[^>]*>(.*?)</pre>", html, re.DOTALL | re.IGNORECASE)
	text = pre.group(1) if pre else re.sub(r"<[^>]+>", "", html)
	return (text
			.replace("&lt;", "<").replace("&gt;", ">")
			.replace("&amp;", "&").replace("&#039;", "'")
			.replace("&quot;", '"').strip())


def _upload(file_path):
	body, content_type = _build_multipart(file_path)
	req = urllib.request.Request(
		LYSIS_URL, data=body,
		headers={"Content-Type": content_type, "User-Agent": "SublimeText-LysisPlugin/1.0"},
		method="POST",
	)
	with urllib.request.urlopen(req, timeout=60) as resp:
		return _strip_html(resp.read().decode("utf-8", errors="replace"))


# ── Comando principal ──────────────────────────────────────────────────────────

class AmxxLysisDecompileCommand(sublime_plugin.WindowCommand):

	def run(self):
		# Directorio inicial: el del archivo activo (si existe)
		start_dir = None
		av = self.window.active_view()
		if av and av.file_name():
			start_dir = os.path.dirname(av.file_name())

		# Diálogo nativo del sistema (requiere ST build >= 4075)
		sublime.open_dialog(
			callback=self._on_file_selected,
			file_types=[("AMXX / SMX plugins", ["amxx", "smx"])],
			directory=start_dir,
			multi_select=False,
			allow_folders=False,
		)

	def _on_file_selected(self, path):
		if path is None:		  # usuario canceló
			return

		status_key = "lysis_status"
		self.window.active_view().set_status(status_key, "⏳ Lysis: Uploading and decompiling…")

		def worker():
			try:
				result = _upload(path)
				sublime.set_timeout(lambda: self._show_result(path, result, status_key), 0)
			except Exception as exc:
				sublime.set_timeout(lambda: self._show_error(path, exc, status_key), 0)

		threading.Thread(target=worker, daemon=True).start()

	def _show_result(self, path, code, status_key):
		self.window.active_view().erase_status(status_key)

		view = self.window.new_file()
		view.set_name(f"[Lysis] {os.path.basename(path)}.sma")
		view.set_scratch(True)

		view.set_syntax_file("AMXX-Pawn.sublime-syntax")

		view.run_command("lysis_insert_text", {"text": code})
		view.sel().clear()
		view.sel().add(sublime.Region(0, 0))
		view.show(0)

		sublime.status_message("✅ Lysis: Decompilation completed.")

	def _show_error(self, path, exc, status_key):
		self.window.active_view().erase_status(status_key)
		sublime.error_message(f"Error while decompiling '{os.path.basename(path)}':\n\n{exc}")


# ── Comando auxiliar (inserta texto, debe ejecutarse en el hilo principal) ─────

class LysisInsertTextCommand(sublime_plugin.TextCommand):
	def run(self, edit, text=""):
		self.view.insert(edit, 0, text)