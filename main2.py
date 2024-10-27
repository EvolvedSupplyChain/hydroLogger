#Hydroponic Data Acquisition and Control Unit Software
#A Liebig for PHR&D
#9/29/24

import json
import network
import socket
import time
import machine
import onewire
import gc
import ds18x20
import scd40
import ssd1306
import os
import espnow
import ubinascii
import TSL2591
import I2C_bus_device
import struct
from umqttsimple import MQTTClient

with open("config.json",'r') as f:
    config = json.load(f)

UID = ubinascii.hexlify(machine.unique_id())

telemTopic = config["TELEMTOPIC"].format(config["TENANT"],UID.decode())
ccTopic = config["CCTOPIC"].format(config["TENANT"],UID.decode())
logTopic = config["LOGTOPIC"].format(config["TENANT"],UID.decode())
statusTopic = config["STATUSTOPIC"].format(config["TENANT"],UID.decode())

fanEnabled = True

#set up display:

#make a network connection

#set the real time clock
    
#connect to mqtt

#if no internet/mqtt, use ESPNow


#dose pins: 3-6 pwm
#TDS 1 ADC
#pH 2 ADC
#relays 16-18 digital out
#i2c default
#temp bus 9 digital in
#define pins
fanControlPin = machine.Pin(37,machine.Pin.OUT)

waterSolenoidPin = machine.Pin(13,machine.Pin.OUT)

dosingOneControl = machine.Pin(38,machine.Pin.OUT) 
dosingTwoControl = machine.Pin(39,machine.Pin.OUT)

tempBusPin = machine.Pin(12,machine.Pin.IN) #12
tempProbeBus = ds18x20.DS18X20(onewire.OneWire(tempBusPin))
probeTemps = tempProbeBus.scan()

phProbePowerPin = machine.Pin(4) #4
phProbeDataPin = machine.ADC(6) #6
phTempProbePin = machine.Pin(14)

tdsProbePowerPin = machine.Pin(16,machine.Pin.OUT)  #16
tdsProbeDataPin = machine.ADC(6) #7

acRelayOnePin = machine.Pin(1,machine.Pin.OUT)
acRelayTwoPin = machine.Pin(2,machine.Pin.OUT)
acRelayThreePin = machine.Pin(21,machine.Pin.OUT)

#lowWaterSensorPin = machine.ADC(10)
lowWaterSensorPin = machine.Pin(5,machine.Pin.IN,machine.Pin.PULL_DOWN) #5

highWaterSensorPin = machine.Pin(3,machine.Pin.IN) #3

#I2C bus for SCD40 and/or AHT10
sensorBus = machine.I2C(0,scl=machine.Pin(9),sda=machine.Pin(8),freq=100000) #9,8
    
    
scd40CO2 = scd40.SCD4X(sensorBus)
time.sleep(1)
scd40CO2.start_periodic_measurement()
time.sleep(1)

totalLuxSense = TSL2591.TSL2591(sensorBus)
time.sleep(1)
totalLuxSense.gain = TSL2591.GAIN_LOW

station = network.WLAN(network.STA_IF)
station.active(True)
time.sleep(1)

connAttempt = 0
while not station.isconnected():
    station.connect(config["SSID"], config["WIPASS"])
    connAttempt +=1
    time.sleep(1)
    if connAttempt > 10:
        print("wifi error")
        break

time.sleep(1)
if station.isconnected():
    print("wifi working")
#display:
oledDisplay = ssd1306.SSD1306_I2C(64,32,sensorBus)


#Helper Functions:
def displayStatus(messageType,message):
    if messageType == "status":
        oledDisplay.show()
        oledDisplay.text(message,0,0,1)
        oledDisplay.show()
    else:
        pass
    
#setup the RTC
NTP_DELTA = 3155673600 + 25200   #Adjust this for time zone
timeHost = "pool.ntp.org"
rtClock = machine.RTC()

def set_time():
    # Get the external time reference
    NTP_QUERY = bytearray(48)
    NTP_QUERY[0] = 0x1B
    addr = socket.getaddrinfo(timeHost, 123)[0][-1]
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.settimeout(1)
        res = s.sendto(NTP_QUERY, addr)
        msg = s.recv(48)
    except Exception as error:
        #errorHandler("NTP error", error, traceback.print_stack())
        print("NTP error")
    finally:
        s.close()

    #Set our internal time
    val = struct.unpack("!I", msg[40:44])[0]
    tm = val - NTP_DELTA    
    t = time.gmtime(tm)
    rtClock.datetime((t[0],t[1],t[2],t[6]+1,t[3],t[4],t[5],0))

if station.isconnected():
    set_time()
else:
    ntpFail = True

def main():
    while True:
        
        luxData = {"TOTAL":0,
           "IR":0,
           "VIS":0,
           "FULLSPEC":0}
        
        atmosphericData = {
                   "SCD40":
                       {
                        "TEMP":0.0,
                        "HUMIDITY":0.0,
                        "CO2":0.0
                        }
                   }
        
        tempProbeValues = []
        
        #tempProbeData = {
                        
        
        co2Wait = 0
        while not scd40CO2.data_ready:
            print("waiting on CO2 sensor")
            if co2Wait < 20:
                co2Wait += 1
                time.sleep_ms(500)
            else:
                break
            
        try:
            atmosphericData["SCD40"]["TEMP"] = scd40CO2.temperature
            atmosphericData["SCD40"]["HUMIDITY"] = scd40CO2.relative_humidity
            atmosphericData["SCD40"]["CO2"] = scd40CO2.co2
        except Exception as error:
            #errorHandler("SCD40 reading", error, traceback.print_stack())
            atmosphericData["SCD40"]["TEMP"] = 0
            atmosphericData["SCD40"]["HUMIDITY"] = 0
            atmosphericData["SCD40"]["CO2"] = 0


        try:
            luxData["TOTAL"] = totalLuxSense.lux
            luxData["IR"] = totalLuxSense.infrared
            luxData["VIS"] = totalLuxSense.visible
            luxData["FULLSPEC"] = totalLuxSense.full_spectrum
        except Exeption as error:
            print(error)
            luxData["TOTAL"] = 0
            luxData["IR"] = 0
            luxData["VIS"] = 0
            luxData["FULLSPEC"] = 0
            #errorHandler("lux reading", error, traceback.print_stack())
        
        #get temp:
        tempProbeBus.convert_temp()
        time.sleep(1)
        
        for i in probeTemps:
            tempProbeValues.append(tempProbeBus.read_temp(i))
            
        #for index,temp in enumerate(tempProbeValues)
        #    tempProbeData[index] = temp
        
        #get pH:
        tdsProbePowerPin.value(0)
        phProbePowerPin.value(1)
        time.sleep(5)
        phData["PH"] = phProbeDataPin.read_uv() * 3.3 / 100000
        #change this to read ph temp probe
        phData["TEMP"] = 0
        time.sleep(1)
        phProbePowerPin.value(0)
        time.sleep(1)
            #make sure TDS probe is switched off
            #switch on pH probe, 30 seconds to stabilize
            #take reading
            #switch off pH probe
            
        #get EC/TDS:
        tdsProbePowerPin.value(1)
        time.sleep(5)
        tdsData["TDS"] = tdsProbeDataPin.read_uv() * 3.3 / 100000
        tdsData["EC"] = 0  #calculated value
        time.sleep(1)
        tdsProbePowerPin.value(0)
        time.sleep(1)
            #make sure pH probe is switched off
            #switch on TDS probe, wait 30 seconds to stabilize
            #take reading, do conversion to get EC
            #switch off TDS probe
            
        #AC relay control:
            #poll settings and check schedule
            #match AC 1-3 with purpose and enabled
            
            
        #interrupts for low water sensor, AC control, and dosing
            
        #if dosePumpControlEnabled:
            #check scheduling and manual input
        
        mqttPayload = {
                        "node": config["NAME"],
                        "UID": UID,
                        "CONTEXT": config["CONTEXT"],
                        "LUX": luxData,
                        "ATMOSPHERIC": atmosphericData,
                        "PROBE": tempProbeValues,
                        "PH": phData,
                        "TDS": tdsData,
                        "RTCLOCK": rtClock.datetime(),
                        "MEMFREE": gc.mem_free(),
                        "MEMUSED": gc.mem_alloc()
                       }
        
        print(json.dumps(mqttPayload))
        displayStatus("status","Running...")