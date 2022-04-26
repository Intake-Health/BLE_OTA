import bluetooth
import socket
import time

addr = ""#'4C:75:25:A4:F0:9E'

port = 1
done = False
lena = 0

nearby_devices = bluetooth.discover_devices(duration=4,lookup_names=True,flush_cache=True,lookup_class=False)


for device in nearby_devices:
	if device[1] == "InFlow":
		addr = device[0]

if addr == "":
	print("couldn't find device")
	exit()
else:
	print("Found Inflow, attempting connection")

s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)

try:
	s.connect((addr,port))
	print("Connected")
except:
	print("failed to connect")
	exit()


while(1):
	bytesWritten = 0
	otaFile = open("firmware.bin", "rb")
	fileLen = len(otaFile.read())
	otaFile.seek(0)
	while(not done):
		if (fileLen - bytesWritten) > 256:
			chunk = otaFile.read(256)
		else:
			print("last chunk")
			chunk = otaFile.read(fileLen - bytesWritten)
			done = True
		bytesWritten = bytesWritten + len(chunk)
		print("total bytes sent: " + str(bytesWritten))
		s.send(chunk)
	print("update finished")
	exit()
	

