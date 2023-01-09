'''
server.py [2023.01.06]

Main script for the server
'''

import os; os.system('cls' if os.name == 'nt' else 'clear')
import subprocess
import time
import pprint
from types import SimpleNamespace
import socket
import json
from enum import Enum

from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf # `pip install zeroconf`
import nginx # `pip install python-nginx`

# CONFIG =================================================================

cfg = SimpleNamespace(**{
	# Intended name of player (can be any string, which matches the name in player.py)
	"target_playerName": "Raspi-1",

	# Absolute path to video file, including video, using double-backslashes
	"videoPath": 'C:\\Users\\AK\\Desktop\\LanCast\\VideoDemo\\10 Things I Hate About You (1999) (1080p BluRay x265).mkv',
	
	# Port used for mDNS, and socket communication
	"port_comm": 8400,
	# Port used by video stream
	"port_stream": 8080,

	# The service name and type must match those in player.py
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

class SocketProp:
	my_socket = None
	client_socket = None
	locaIP = None
	clientIP = None

# Zeroconf properties
class zcProp:
	zc = None
	serviceInfo = None

form = dict()

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

# MAIN ===================================================================

# Re-write nginx .conf file
	# https://github.com/peakwinter/python-nginx
@iife
def writeNginxConf():
	videoDirpath = cfg.videoPath[:cfg.videoPath.rfind('\\')]

	# nginxConf = nginx.loadf(f'{os.path.abspath(os.path.dirname(__file__))}/nginx/conf/sites-enabled/lancast.conf') # to load the file
	nginxConf = nginx.Conf()
	nginxServer = nginx.Server()
	nginxServer.add(
		nginx.Key('listen', cfg.port_stream),
		nginx.Key('server_name', 'lancast_server'),
		nginx.Location('/',
			nginx.Key('root', videoDirpath),
			nginx.Key('index', 'index.html')
		)
	)

	nginxConf.add(nginxServer)
	nginx.dumpf(nginxConf, f'{os.path.abspath(os.path.dirname(__file__))}/nginx/conf/sites-enabled/lancast.conf')

# Launch NGINX server
print('[nginx] Starting NGINX server')
subprocess.Popen(['nginx.exe'], cwd=f'{os.path.abspath(os.path.dirname(__file__))}\\nginx', shell=True)

@iife
def getLocalIP():
	SocketProp.my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	SocketProp.my_socket.connect(("8.8.8.8", 80))
	localIP = SocketProp.my_socket.getsockname()[0]
	SocketProp.my_socket.close()
	SocketProp.localIP = localIP

@iife
def _():
	properties = {
		"ip": SocketProp.localIP,
		"port": cfg.port_comm
	}
	zcProp.zc = Zeroconf()
	zcProp.serviceInfo = ServiceInfo(cfg.service["type"], cfg.service["name"], addresses=socket.inet_aton(SocketProp.localIP), port=cfg.port_comm, properties=properties)

# Start listening for messages through the socket
SocketProp.my_socket = socket.socket()
SocketProp.my_socket.bind((socket.gethostname(), cfg.port_comm))
SocketProp.my_socket.listen(5)
print("[socket] Listening for messages")

# Register service
zcProp.zc.register_service(zcProp.serviceInfo)
print("[mDNS] Starting service")

try:
	# Accept the first incoming socket message
	connection, SocketProp.clientIP = SocketProp.my_socket.accept()

	while True:
		socket.getaddrinfo(host='localhost', port=0) # if `port=0`, then all ports are served
		
		try: incomingMessage = connection.recv(1024)
		except ConnectionResetError: break # The socket was closed by the client
		if incomingMessage:
			form = json.loads(incomingMessage.decode())
			print(f"[socket] Incoming message from: {form['playerName']}")

			# Verify that the player is intended target
			if form["code"] == 0:
				if form["playerName"] == cfg.target_playerName: # "if it is the correct player"
					print(f"[socket] Accepted {form['playerName']}")
					form["code"] = 1
					print(cfg.videoPath[cfg.videoPath.rfind('\\')+1:])
					form["videoURL"] = cfg.videoPath[cfg.videoPath.rfind('\\')+1:]
					form["port_stream"] = cfg.port_stream
					connection.sendall(json.dumps(form).encode())
					print(f"[socket] Sent video URL and port to {form['playerName']} for streaming")
					connection.close()
					print("[socket] Socket closed")
					break

				else:
					form["code"] = -1
					break

		time.sleep(0.5)

	# Results of the verification
	if form['code'] == 1: pass
	elif form['code'] == -1: print(f"[socket] Rejected form['playerName']")
	else: print("[socket] Connection was closed by the client unexpectedly")

finally:
	print("[mDNS] Unregistering service")
	zcProp.zc.unregister_service(zcProp.serviceInfo)
	zcProp.zc.close()

input('Press <ENTER> to stop NGINX server and quit')
# Stop NGINX server
subprocess.call(['nginx.exe', '-s', 'quit'], cwd=f'{os.path.abspath(os.path.dirname(__file__))}\\nginx', shell=True)
print('[nginx] Stopping nginx server')

''' Sources ===============================================================

https://python-zeroconf.readthedocs.io/en/latest/api.html
[Python Flask Tutorial: Full-Featured Web App Part 1 - Getting Started](https://www.youtube.com/watch?v=MwZwr5Tvyxo)
https://realpython.com/python-sockets/
'''