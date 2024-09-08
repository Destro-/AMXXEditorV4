import os
import sys
import urllib.request
import json
import threading
import queue
import traceback
import platform

class RollbarAPI:
	def __init__(self, access_token, environment="testenv"):
		self.access_token = access_token
		self.environment = environment
		self.endpoint = "https://api.rollbar.com/api/1/item/"
		
		self.parse_code = None
		self.device_person = None
		
		self.request_queue = queue.Queue()
		
		self.thread = threading.Thread(target=self._process_queue)
		self.thread.start()

	def _process_queue(self):
		while True:
			# Obtener la solicitud de la cola
			req = self.request_queue.get()
			if req is None:
				break  # Salir del loop si se recibe un indicador de fin

			try:
				# Procesar la solicitud
				with urllib.request.urlopen(req) as response:
					data = response.read()
					print("RollbarAPI: Response: %s..." % data[:60])  # Procesar la respuesta como sea necesario
			except Exception as e:
				print("Failed to process request:", e)
				pass
			finally:
				self.request_queue.task_done()
	
	def _send_payload(self, payload):

		headers = {
			"Content-Type": "application/json",
			"X-Rollbar-Access-Token": self.access_token
		}
		data = json.dumps(payload).encode("utf-8")
		
		req = urllib.request.Request(self.endpoint, data=data, headers=headers)
		
		self.request_queue.put(req)

	def close(self):
		self.request_queue.put(None)  # Añadir un indicador de finalización a la cola
		self.thread.join()
	
	#-------------------------------------------------------------------------------------------
	def report_message(self, message, level="info", extra_data=None):
		"""
		Envía un mensaje a Rollbar.

		:param message: El mensaje a enviar.
		:param level: Nivel de severidad ("critical", "error", "warning", "info", "debug").
		:param extra_data: Datos adicionales opcionales para enviar con el mensaje.
		"""
		payload = {
			"data": {
				"environment": self.environment,
				"body": {
					"message": {
						"body": message
					}
				},
				"level": level,
				"platform": platform.system(),
				"language": "python"
			}
		}

		if self.device_person :
			payload["data"].update(self.device_person)
			
		if extra_data:
			payload["data"].update(extra_data)

		self._send_payload(payload)

	def report_exception(self, exc, extra_data=None):
		"""
		Envía una excepción a Rollbar.

		:param exc: La excepción a enviar.
		:param extra_data: Datos adicionales opcionales para enviar con la excepción.
		"""
		
		tb = traceback.extract_tb(exc.__traceback__)
		frames = []
		for frame in tb:
			frames.append({
				"filename": os.path.basename(frame.filename),
				"lineno": frame.lineno,
				"method": frame.name,
				"code": frame.line
			})
		
		if frames and self.parse_code:
			frames[-1]["context"] = { "post": [ self.parse_code ] }
			self.parse_code = None
		
		payload = {
			"data": {
				"environment": self.environment,
				"body": {
					"trace": {
						"frames": frames,
						"exception": {
							"class": exc.__class__.__name__,
							"message": str(exc)
						}
					}
				},
				"level": "error",
				"platform": platform.platform(True, True),
				"language": "python"
			}
		}

		if self.device_person :
			payload["data"].update(self.device_person)
			
		if extra_data :
			payload["data"].update(extra_data)
			
		import pprint
		print("send:")
		pprint.pprint(payload)
		print("")
		
		self._send_payload(payload)

	def register_device(self, uid, username=None, extra_data=None):
		
		if not username:
			username = platform.node()

		self.device_person = { "person": {
				"id": str(uid),
				"username": username
			}
		}
		
		if extra_data :
			self.device_person.update(extra_data)
	
	def set_parse_code(self, text):
		self.parse_code = f"\n# PARSE CODE:\n'''\n{text}\n'''"
