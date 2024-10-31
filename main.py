import json

with open("config.json", 'r') as f:
    config = json.load(f)

if config["LAUNCHREPL"]:
    config["LAUNCHREPL"] = False
    with open("config.json",'w') as f:
        json.dump(config, f)
    
    #connect to wifi
    import network
    import time
    import webrepl
    import machine
    #import _thread
    #import neopixel
    
    station = network.WLAN(network.STA_IF)
    station.active(True)
    
    
    while not station.isconnected():
        station.connect(config["SSID"], config["WIPASS"])
        time.sleep(5)
    
    
    print(station.ifconfig()[0])
    #displayIP()
    #open a VPN connection so that webREPL will be local to azure network
    webrepl.start(password="2075012")
    #TODO: quite webrepl and reset if button pushed
    #this doesn't work, need to find how to check for connection; os.dupterm()?
    #while not webrepl.connected():
    #displayIP()
    
    
    #launch webrepl
else:
    import hydroLogger
