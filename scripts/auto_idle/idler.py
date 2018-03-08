import time
from psp.caget import caget
from psp.caput import caput

# Updated to check that Detector is ON before idling.  
# Avoid turning on detector if is off and also avoid repeatedly idling
# when already set to idle.
while True:
    door_state = caget('PPS:FEH1:45:DOORA')
    if door_state == 0 and caget('DET:MBL:MPD:CH:200:GetVoltageMeasurement') > 30:
        print("Attempting to idle detector ...")
        caput('DET:CSPAD:DETECTOR:IDLE.PROC', 1)
        time.sleep(5)
    time.sleep(1)
