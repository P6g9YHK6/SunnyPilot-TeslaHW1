#!/usr/bin/env python3
"""Diagnostic tool for Tesla CAN ignition detection.
Monitors panda health, CAN messages (0x348 GTW_status),
and device state to debug ignition detection issues."""

import os
import sys
import time

os.environ["PYTHONPATH"] = "/data/openpilot"
sys.path.insert(0, "/data/openpilot")

import cereal.messaging as messaging

def main():
    sm = messaging.SubMaster(["pandaStates", "deviceState", "can"])
    
    prev_counter = -1
    print("Monitoring Tesla CAN ignition detection...")
    print("Shift to Drive to test.\n")
    
    start = time.monotonic()
    while time.monotonic() - start < 120:
        sm.update(1000)
        
        # pandaStates
        for i, ps in enumerate(sm["pandaStates"]):
            print(f"  panda[{i}]: type={ps.pandaType} ignLine={ps.ignitionLine} ignCan={ps.ignitionCan} "
                  f"safetyModel={ps.safetyModel} safetyParam={ps.safetyParam}")
        
        # deviceState
        if sm.updated["deviceState"]:
            ds = sm["deviceState"]
            print(f"  deviceState: started={ds.started}")
        
        # CAN 0x348
        if sm.updated["can"]:
            for msg in sm["can"]:
                if msg.address == 0x348 and len(msg.dat) >= 7:
                    dat = bytes(msg.dat).hex()
                    counter = msg.dat[6] & 0x0F
                    bit0 = msg.dat[0] & 0x01
                    alive = prev_counter != -1 and counter == ((prev_counter + 1) & 0x0F)
                    prev_counter = counter
                    print(f"  0x348 bus={msg.bus} dat={dat} counter={counter} bit0={bit0} alive={alive}")
                    break
        
        elapsed = int(time.monotonic() - start)
        print(f"[{elapsed}s] ---")
        time.sleep(0.5)

if __name__ == "__main__":
    main()
