"""Virtual Xbox 360-style pad named "Virtual Test Pad" that stays connected and runs vstick-style steps read from a FIFO.

Usage: vpadd.py <fifo>
Write lines of steps to the FIFO, e.g. `echo "press:a wait:1 left:0.5" > <fifo>`.
Steps: wait:<s>, press:<button> (a b x y start select ps), left:<s> / right:<s> / up:<s> / down:<s> (left stick held fully for s seconds), dpad:<left|right|up|down> (tapped).
Each step prints a monotonic timestamp.
"""
import os
import sys
import time

from evdev import AbsInfo, UInput, ecodes as e

BUTTONS = {"a": e.BTN_SOUTH, "b": e.BTN_EAST, "x": e.BTN_NORTH, "y": e.BTN_WEST,
           "start": e.BTN_START, "select": e.BTN_SELECT, "ps": e.BTN_MODE}
stick = AbsInfo(value=0, min=-32768, max=32767, fuzz=16, flat=128, resolution=0)
trigger = AbsInfo(value=0, min=0, max=255, fuzz=0, flat=0, resolution=0)
hat = AbsInfo(value=0, min=-1, max=1, fuzz=0, flat=0, resolution=0)
caps = {
    e.EV_KEY: [e.BTN_SOUTH, e.BTN_EAST, e.BTN_NORTH, e.BTN_WEST, e.BTN_TL, e.BTN_TR,
               e.BTN_SELECT, e.BTN_START, e.BTN_MODE, e.BTN_THUMBL, e.BTN_THUMBR],
    e.EV_ABS: [(e.ABS_X, stick), (e.ABS_Y, stick), (e.ABS_RX, stick), (e.ABS_RY, stick),
               (e.ABS_Z, trigger), (e.ABS_RZ, trigger), (e.ABS_HAT0X, hat), (e.ABS_HAT0Y, hat)],
}

fifo = sys.argv[1]
if not os.path.exists(fifo):
    os.mkfifo(fifo)

with UInput(caps, name="Virtual Test Pad",vendor=0x045E, product=0x028E, version=0x110, bustype=e.BUS_USB) as ui:
    t0 = time.monotonic()
    while True:
        with open(fifo) as f:
            for line in f:
                for step in line.split():
                    kind, arg = step.split(":", 1)
                    print("%.3f start %s" % (time.monotonic() - t0, step), flush=True)
                    if kind == "wait":
                        time.sleep(float(arg))
                    elif kind == "press":
                        ui.write(e.EV_KEY, BUTTONS[arg], 1)
                        ui.syn()
                        time.sleep(0.12)
                        ui.write(e.EV_KEY, BUTTONS[arg], 0)
                        ui.syn()
                    elif kind == "dpad":
                        axis = e.ABS_HAT0X if arg in ("left", "right") else e.ABS_HAT0Y
                        ui.write(e.EV_ABS, axis, -1 if arg in ("left", "up") else 1)
                        ui.syn()
                        time.sleep(0.12)
                        ui.write(e.EV_ABS, axis, 0)
                        ui.syn()
                    elif kind in ("left", "right", "up", "down"):
                        axis = e.ABS_X if kind in ("left", "right") else e.ABS_Y
                        ui.write(e.EV_ABS, axis, -32767 if kind in ("left", "up") else 32767)
                        ui.syn()
                        time.sleep(float(arg))
                        ui.write(e.EV_ABS, axis, 0)
                        ui.syn()
                    print("%.3f end %s" % (time.monotonic() - t0, step), flush=True)
