'''
player.py [2023.01.06]

Main script for the player
'''

import os; os.system('cls' if os.name == 'nt' else 'clear')
import subprocess
import time
import pprint
from types import SimpleNamespace
import socket
import json
from enum import Enum

from zeroconf import ServiceBrowser, ServiceListener, Zeroconf

# CONFIG =================================================================

cfg = SimpleNamespace(**{
	"playerName": "Raspi-1",
	"testingMode": True,

	"service": {
		"name": "LanCast._http._tcp.local.",
		"type": "_http._tcp.local.",
	}
})

# VARS ===================================================================

class Code(Enum):
	AUTH = 0
	STREAM = 1
	MISADDR = -1

# FUNCTIONS ==============================================================

iife = lambda f: f()

class G:
	# Given a directory path (string), returns a list of filenames (strings) (with extensions)
	def listFiles(dir):
		full_list = os.listdir(dir)
		return full_list

	# Returns a files extension, including the dot
	def extension(fileName):
		for ch in range(len(fileName)-1, -1, -1):
			if fileName[ch] == "." : return fileName[ch:]
		return ""

	# Returns a file title (filename without the extension)
	def basename(filename):
		for ch in range(len(filename)-1, -1, -1):
			if filename[ch] == "." : return filename[:ch]
		return filename

	def catchErr(situation = "Error", reason = ""):
		if reason == "": print(situation)
		else: print(situation + ":", reason)
		input("Press <ENTER> to exit")
		raise SystemExit

	def wrap(root, affix, closeBrackets=True):
		pairs = { "(": ")", "[": "]", "{": "}", "<": ">" }
		return affix + root + (pairs[affix] if (closeBrackets and (affix in pairs.keys())) else affix)

	def dict_toStr(dictionary, indent=2): return pprint.pformat(dictionary, sort_dicts=False, indent=indent)

# CLASSES ===============================================================

# All methods in this class are called automatically by the listener. Dont call the methods manually
class ServiceHandler(ServiceListener):
	def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
		print(f"Service {name} updated")

	def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
		print(f"Service {name} removed")

	def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
		info = zc.get_service_info(type_, name)

		if name == cfg.service["name"]:
			print(f"[mDNS] Service {name} found")
			services.append(info)

# MAIN ===================================================================

services = list()

zeroconf = Zeroconf()
my_ServiceHandler = ServiceHandler()

try:
	# Start browsing for services
	my_ServiceBrowser = ServiceBrowser(zc=zeroconf, type_="_http._tcp.local.", handlers=my_ServiceHandler)
		# https://python-zeroconf.readthedocs.io/en/latest/api.html#zeroconf.ServiceBrowser
		# A bit more info about the handlers: https://python-zeroconf.readthedocs.io/en/latest/api.html#zeroconf.asyncio.AsyncServiceBrowser

	# Check continuously for available services
	while True:
		socket.getaddrinfo(host='localhost', port=0)
			# if `port=0`, then all ports are served

		if len(services) > 0: break

		time.sleep(0.500)

finally: zeroconf.close()

# Decode bytes into string
server_ip = services[0].properties[b"ip"].decode("utf-8")
print(f'[mDNS] Server IP: {server_ip}')
# Decode bytes into int
server_port = int(services[0].properties[b"port"])

# Create a socket instance, and connect to the server
my_socket = socket.socket()
my_socket.connect((server_ip, server_port))

# Form
form = {
	"code": 0,
	"playerName": cfg.playerName,
	"videoURL": None,
	"port_stream": None
}

# Verify if the service was intended for this player {
my_socket.sendall(json.dumps(form).encode());

incomingMessage = my_socket.recv(1024)
form = json.loads(incomingMessage.decode())

if form["code"] == 1:
	my_socket.close()
	print('[socket] Device name match')
	command = ['mpv', f'http://{server_ip}:{form["port_stream"]}/{form["videoURL"].replace(" ", "%20")}']
	print(command)
	time.sleep(3)
	result=subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	if cfg.testingMode: print(result.returncode, result.stdout, result.stderr)

elif form["code"] == -1: print("[socket] Connection refused")
else: print("[socket] Very bad error")
# }



