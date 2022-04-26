"""
  
MIT License

Copyright (c) 2021 Felix Biego

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from __future__ import print_function
import os.path
from os import path
import asyncio
import platform
import math
import sys
import re

from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

header = """#####################################################################
    ------------------------BLE OTA update---------------------
    Arduino code @ https://github.com/fbiego/ESP32_BLE_OTA_Arduino
#####################################################################"""

UART_SERVICE_UUID = "c78cfcf9-cdb1-4962-b69d-ac1c380c0001"
UART_RX_CHAR_UUID = "eac38323-5642-48ca-9d34-a316c2dc0002"
UART_TX_CHAR_UUID = "eac38323-5642-48ca-9d34-a316c2dc0003"

PART = 16000
MTU = 250

end = True
clt = None
fileBytes = None
total = 0
sent = 0
#device = None

def get_bytes_from_file(filename):
    print("Reading from: ", filename)
    return open(filename, "rb").read()

async def start_ota():
    device = None
    while device == None:
        devices = await BleakScanner.discover()
        for d in devices:       
            if d.name == "InFlow":
                print("Connecting to InFlow")
                device = d

    #device = await BleakScanner.find_device_by_address(ble_address, timeout=20.0)
    disconnected_event = asyncio.Event()

    def handle_disconnect(_: BleakClient):
        global disconnect
        disconnect = False
        print(": Device disconnected")
        exit()
        disconnected_event.set()
            
    async def handle_rx(_: int, data: bytearray):
        print("handle rx: " + str(data))
        if (data[0] == 0xAA):
            print("Transfer mode:", data[1])
            printProgressBar(0, total, prefix = 'Progress:', suffix = 'Complete', length = 50)
            if data[1] == 1:
                for x in range(0, fileParts):
                    await send_part(x, fileBytes, clt)
                    printProgressBar(x + 1, total, prefix = 'Progress:', suffix = 'Complete', length = 50)
            else:
                await send_part(0, fileBytes, clt)
                
        if (data[0] == 0xF1):
            nxt = int.from_bytes(bytearray([data[1], data[2]]), "big")  
            await send_part(nxt, fileBytes, clt)
            printProgressBar(nxt + 1, total, prefix = 'Progress:', suffix = 'Complete', length = 50)
        if (data[0] == 0xF2):
            ins = 'Installing firmware'
            #print("Installing firmware")
        if (data[0] == 0x0F):
            result = bytearray([])
            for s in range(1, len(data)):
                result.append(data[s])
            print("OTA result: ", str(result, 'utf-8'))
            global end
            end = False
        #print("received:", data)


    async def send_part(position: int, data: bytearray, client: BleakClient):
        start = (position * PART)
        end = (position + 1) * PART
        if len(data) < end:
            end = len(data)
        parts = (end - start) / MTU
        for i in range(0, int(parts)):
            toSend = bytearray()
            for y in range(0, MTU):
                toSend.append(data[(position*PART)+(MTU * i) + y])
            await send_data(client, toSend, False)
        if (end - start)%MTU != 0:
            rem = (end - start)%MTU
            toSend = bytearray()#([int(parts)])
            for y in range(0, rem):
                toSend.append(data[(position*PART)+(MTU * int(parts)) + y])
            await send_data(client, toSend, False)
        #update = bytearray([int((end - start)/256), int((end - start) % 256), int(position/256), int(position % 256) ])
        #await send_data(client, update, True)


    async def send_data(client: BleakClient, data: bytearray, response: bool):
        global sent
        print("sending " + str(len(data)))
        sent = sent + len(data)
        print("sent " + str(sent) + " total")
        await client.write_gatt_char(UART_TX_CHAR_UUID, data, response)
        await asyncio.sleep(0.2)
        
    if not device:
        print("-----------Failed--------------")
        print(f"Device with address {ble_address} could not be found.")
        return
        #raise BleakError(f"A device with address {ble_address} could not be found.")
    async with BleakClient(device, disconnected_callback=handle_disconnect) as client:
        #await client.start_notify(UART_RX_CHAR_UUID, handle_rx)
        await asyncio.sleep(1.0)
        
        #await send_data(client, bytearray([0xFD]), False)
        
        global fileBytes
        fileBytes = get_bytes_from_file("firmware.bin")
        global clt
        clt = client
        fileParts = math.ceil(len(fileBytes) / PART)
        fileLen = len(fileBytes)
        fileSize = bytearray([fileLen >>  24 & 0xFF, fileLen >>  16 & 0xFF, fileLen >>  8 & 0xFF, fileLen & 0xFF])
        #await send_data(client, fileSize, False)
        print("file size: " + str(fileLen))
        global total
        total = fileParts
        otaInfo = bytearray([int(fileParts/256), int(fileParts%256), int(MTU / 256), int(MTU%256) ])
        #await send_data(client, otaInfo, False)
        print("file parts: " + str(fileParts))
        for x in range(0, fileParts):
            await send_part(x, fileBytes, clt)
        
        print("All data sent")
        while end:
            await asyncio.sleep(1.0)
        print("Waiting for disconnect... ", end="")
        await disconnected_event.wait()
        print("-----------Complete--------------")

"""
ble_address = (
    "98:CD:AC:D3:6B:E2"
    if platform.system() != "Darwin"
    else "B9EA5233-37EF-4DD6-87A8-2A875E821C46"
)
"""

def isValidAddress(str):
 
    # Regex to check valid
    # MAC address
    regex = ("^([0-9A-Fa-f]{2}[:-])" +
             "{5}([0-9A-Fa-f]{2})|" +
             "([0-9a-fA-F]{4}\\." +
             "[0-9a-fA-F]{4}\\." +
             "[0-9a-fA-F]{4}){17}$")
    regex2 = "^[{]?[0-9a-fA-F]{8}" + "-([0-9a-fA-F]{4}-)" + "{3}[0-9a-fA-F]{12}[}]?$"
 
    # Compile the ReGex
    p = re.compile(regex)
    q = re.compile(regex2)
 
    # If the string is empty
    # return false
    if (str == None):
        return False
 
    # Return if the string
    # matched the ReGex
    if(re.search(p, str) and len(str) == 17):
        return True
    else:
        if (re.search(q, str) and len(str) == 36):
            return True
        else:
            return False


if __name__ == "__main__":
    print(header)
    print("Trying to start OTA update")
    asyncio.run(start_ota())
