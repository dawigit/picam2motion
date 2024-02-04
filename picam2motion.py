#!/usr/bin/python3
# picam2motion
#

SPATH = "/srv/picam2motion"
#SYSLOGSERVER = "ubu22"
#THMSE = 20
#ZOOM = False
LTIMEM = 6
header = "picam2motion - Picamera2 motion detection     press 'q' to quit"

import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-s', "--save", help="save path", default=".")
parser.add_argument('-H', "--host", help="remote syslog server ip", default="localhost")
parser.add_argument('-p', "--port", help="remove syslog server port", type=int, default=514)
parser.add_argument('-z', "--zoom", help="enable zoom", type=int, default=0)
parser.add_argument('-d', "--diff", help="pixel difference threshold", type=float, default=20.0)

args = parser.parse_args()
import time
import numpy as np
from picamera2 import Picamera2,MappedArray
from picamera2.encoders import H264Encoder,MJPEGEncoder,Quality
from picamera2.outputs import FileOutput,FfmpegOutput
import cv2
import libcamera
import curses
import socket
import logging
import logging.handlers

logger = logging.getLogger('picam2motion')
logger.setLevel(logging.DEBUG)
handler = logging.handlers.SysLogHandler(address = (args.host,args.port))
logger.addHandler(handler)

hostname = socket.gethostname()

colour = (0, 255, 0)
origin = (0, 30)
font = cv2.FONT_HERSHEY_SIMPLEX
scale = 1
thickness = 2

showmse = "0"
doloop = True

def set_showmse(s):
    global showmse
    showmse = s

def get_showmse():
    global showmse
    return showmse

def apply_timestamp(request):
    timestamp = time.strftime("%Y-%m-%d %X")
    mse = get_showmse()
    with MappedArray(request, "main") as m:
        cv2.putText(m.array, timestamp+f" {hostname}  {mse}", origin, font, scale, colour, thickness)

def update_log(onoff,timestamp,mse):
    curses.setsyx(1,0)
    stdscr.addstr(1,0," ")
    stdscr.insertln()
    msg = f"{hostname} motion {onoff}  {timestamp} : {mse}"
    stdscr.addstr(1,1,msg)
    stdscr.addstr(0,0,header)
    logger.info(msg)

osize = (2592,1944)
lsize = (320, 240)
hsize = (1920,1080)
framerate = 60

picam2 = Picamera2()

video_config = picam2.create_video_configuration(main={"size": hsize, "format": "RGB888"},
                                                lores={"size": lsize, "format": "YUV420"})
video_config["transform"] = libcamera.Transform(hflip=1, vflip=1)

picam2.configure(video_config)
picam2.pre_callback = apply_timestamp
picam2.set_controls({"FrameRate": framerate})

encoder = H264Encoder(4000000)
encoder.frame_rate=60
picam2.start()
stdscr = curses.initscr()
stdscr.nodelay(True)

if args.zoom:
    size = picam2.capture_metadata()['ScalerCrop'][2:]
    full_res = picam2.camera_properties['PixelArraySize']
    picam2.capture_metadata()
    size = [int(s * 0.35) for s in size]
    offset = [(r - s) // 2 for r, s in zip(full_res, size)]
    offset[1] -= 10
    picam2.set_controls({"ScalerCrop": offset + size})

w, h = lsize
prev = None
encoding = False
ltime = 0
stdscr.addstr(0,0,header)

while doloop:
    key = stdscr.getch()
    if key == ord('q'):
        doloop = False
        continue

    cur = picam2.capture_buffer("lores")
    cur = cur[:w * h].reshape(h, w)
    if prev is not None:
        # Measure pixels differences between current and
        # previous frame
        mse = np.square(np.subtract(cur, prev)).mean()
        set_showmse(mse)
        if mse > args.diff:
            if not encoding:
                timestamp = time.strftime("%Y%m%d_%H-%M-%S")
                encoder.output = FileOutput(f"{args.save}/{timestamp}_{hostname}.h264")
                picam2.start_encoder(encoder)
                encoding = True
                update_log("ON ",timestamp,mse)
            ltime = time.time()
        else:
            if encoding and time.time() - ltime > LTIMEM:
                timestamp = time.strftime("%Y%m%d_%H-%M-%S")
                picam2.stop_encoder()
                encoding = False
                update_log("OFF",timestamp,mse)
    prev = cur

if encoding:
    timestamp = time.strftime("%Y%m%d_%H-%M-%S")
    picam2.stop_encoder()
    encoding = False
    update_log("OFF",timestamp,0)

curses.nocbreak()
stdscr.keypad(False)
curses.echo()
curses.endwin()
