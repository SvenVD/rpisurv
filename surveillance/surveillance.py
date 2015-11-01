#!/usr/bin/python
import math
import worker
import socket
import time
import re
import subprocess
import os
import base64
from urlparse import urlparse
import multiprocessing
from config import cfg
from setuplogging import setup_logging

#We do not need exact floating point numbers, use builtin "float" instead
#from decimal import getcontext, Decimals

class CameraStream:
    """This class defines makes a camera stream an object"""
    def __init__(self, name, rtsp_url = "dummy" ):
        self.name = name
        self.rtsp_url = rtsp_url
        self.parsed=urlparse(rtsp_url)
        self.port = self.parsed.port
        self.hostname = self.parsed.hostname
        self.rtsp_options_cmd = "OPTIONS rtsp:// " + self.hostname + ":" + str(self.port) + " RTSP/1.0\r\nCSeq: 1\r\nUser-Agent: python\r\nAccept: application/sdp\r\n\r\n"

    def is_connectable(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((self.hostname, self.port))
            #Use OPTIONS command to check if we are dealing with a real rtps server
            s.send(self.rtsp_options_cmd)
            rtsp_response=s.recv(4096)
            s.close()
        except:
            logger.error(self.hostname + " : " + str(self.port) +" Not Connectable (failed socket connect)")
            return False

        #If we come to this point it means we have some data received, before we return True we need to check if are connected to an RTSP server
        if not rtsp_response:
            logger.error(self.hostname + " : " + str(self.port) +" Not Connectable (failed rtsp validation, no response from rtsp server)")
            return False

        if re.match("RTSP/1.0",rtsp_response.splitlines()[0]):
            logger.debug(self.hostname + " : " + str(self.port) +" Connectable")
            return True
        else:
            logger.error(self.hostname + " : " + str(self.port) +" Not Connectable (failed rtsp validation, is this an rtsp stream?)")
            return False


    def start_stream(self, coordinates):
        self.coordinates=coordinates
        logger.debug("start stream " + self.name)

        self.stopworker= multiprocessing.Value('b', False)

        #Start worker process
        self.worker = multiprocessing.Process(target=worker.worker, args=(self.name,self.rtsp_url,self.coordinates,self.stopworker))
        self.worker.daemon = True
        self.worker.start()

    def restart_stream(self):
        self.stop_stream()
        self.start_stream(self.coordinates)

    def printcoordinates(self):
        print self.coordinates

    def stop_stream(self):
        logger.debug("Stop stream " + self.name)
        #Stopworker shared value will stop the while loop in the worker, so the worker will run to end. No need to explicitely terminate the worker
        self.stopworker.value= True
        logger.debug("MAIN Value of stopworker for " + self.name + " is " + str(self.stopworker.value))
        self.worker.join()



def draw_screen(cam_streams_to_stop,cam_streams_to_draw,resolution,nr_of_columns):

    resolution_width=int(resolution[0])
    resolution_height=int(resolution[1])
    nr_of_columns=int(nr_of_columns)

    #First stop all running streams
    for cam_stream_to_stop in cam_streams_to_stop:
        cam_stream_to_stop.stop_stream()

    #Start algorithm to start new streams
    fields=len(cam_streams_to_draw)
    if fields == 0:
        logger.error("No connectable streams detected")
        return

    logger.debug( "number of fields= " + str(fields))

    #If you have less fields than columns then only set fields amount columns
    if fields <= nr_of_columns:
        nr_of_columns=fields

    #We calculate needed numbers of rows based on how many fields we have and how many columns per row we want
    nr_of_rows=math.ceil(float(fields)/nr_of_columns)

    normal_fieldwidth=resolution_width/nr_of_columns
    normal_fieldheight=int(resolution_height/nr_of_rows)

    currentrow=1
    currentwindow=1
    currentrowlength=nr_of_columns

    x1=0
    y1=0
    x2=normal_fieldwidth
    y2=normal_fieldheight

    for cam_stream in cam_streams_to_draw:

        if currentwindow > currentrowlength:
            #This is a new row event
            x1=0
            x2=normal_fieldwidth
            y1=y1 + normal_fieldheight
            y2=y2 + normal_fieldheight

            currentrow = currentrow + 1
            #Next row ends when we are at following currentwindow index number
            currentrowlength = currentrowlength + nr_of_columns
        else:
            #This is a window in the same row
            x1=x1 + normal_fieldwidth
            x2=x2 + normal_fieldwidth

        #If this is the first field/window override some settings
        if currentwindow == 1:
            x1=0
            x2=normal_fieldwidth

        #If this is the last field and we still have some screen space left, horizontally stretch it to use all space
        if currentwindow == fields:
            #Sometimes this will override to the same value if the window end was already at the end of the screen
            #Other times it will really override to the end of the screen
            x2= resolution_width

        logger.debug("cam stream name =" + cam_stream.name)
        cam_stream_name = "cam_stream" + str(currentwindow)
        # x1 #x coordinate upper left corner
        # y1 #y coordinate upper left corner
        # x2 #x coordinate absolute where window should end, count from left to right
        # y2 #y coordinate from where window should end, count from top to bottom of screen
        cam_stream.start_stream([x1,y1,x2,y2])
        cam_stream.printcoordinates()

        currentwindow = currentwindow + 1


def setup_camera_streams(rtsp_urls):
    '''Instantiate camera instances and put them in a list'''
    cam_streams=[]
    counter=0
    for rtsp_url in rtsp_urls:
        counter = counter +1
        cam_stream_name = "cam_stream" + str(counter)
        cam_stream=CameraStream(cam_stream_name,rtsp_url)
        cam_streams.append(cam_stream)

    return cam_streams


def check_camera_streams(cam_streams):
    '''Filters a list of camerastream instances into a new list of connectable camera_streams'''
    connectable_cam_streams=[]
    for cam_stream in cam_streams:
        if cam_stream.is_connectable():
            connectable_cam_streams.append(cam_stream)

    return connectable_cam_streams

def set_resolution():
    '''autodetects resolution if possible otherwise fallback to fallback defaults'''
    try:
        fbsetresult=subprocess.check_output(['/bin/fbset','-s'])
    except OSError as e:
        logger.error("Can not find or run the fbset binary to autodetect the resolution")
        autodetect_resolution=None
    else:
        regex_result=re.search("geometry (\d+) (\d+)",fbsetresult)
        autodetect_resolution=[regex_result.group(1),regex_result.group(2)]
        logger.debug("autodetected resolution of" + str(autodetect_resolution))

    if autodetect_resolution is None:
        resolution=[cfg['fallbacks']['resolution']['width'],cfg['fallbacks']['resolution']['height']]
    else:
        resolution=autodetect_resolution
    return resolution

if __name__ == '__main__':

    logger = setup_logging()

    #Read in config
    rtsp_urls=cfg['essentials']['rtsp_urls']
    resolution=set_resolution()
    nr_of_columns=cfg['essentials']['nr_of_columns'] #Max amount of columns per row

    #Setup logger
    logger.debug("nr_of_columns = " + nr_of_columns)

    #Setup all camerastream instances
    all_camera_streams=setup_camera_streams(rtsp_urls)

    #Start main
    previous_connectable_camera_streams=[]
    while True:
        #Detect when new cameras come online or others go offline
        connectable_camera_streams=check_camera_streams(all_camera_streams)

        #Other option to compare could be with to convert the list into a set: print set(connectable_camera_streams) == set(previous_connectable_camera_streams)
        #Only re-draw screen if something is changed or try redrawing if there is no camerastream that is connectable
        if cmp(connectable_camera_streams,previous_connectable_camera_streams) != 0 or len(previous_connectable_camera_streams) == 0:
            draw_screen(previous_connectable_camera_streams,connectable_camera_streams,resolution,nr_of_columns)

        time.sleep(10)



        previous_connectable_camera_streams=connectable_camera_streams



