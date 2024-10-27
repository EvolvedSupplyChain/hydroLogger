#Sensor Loader

import json
import machine
import os

try:
    with open("sensorBOM.json",'r') as f:
        sensorBOM = json.load(f)
except Exception as error:
    print(error)
    

class hardwareLoader:
    def __init__(self,sensorClassList,**kwargs):
        for sensor in sensorClassList