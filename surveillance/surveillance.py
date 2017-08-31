#!/usr/bin/python
import math
import worker
import socket
import time
import subprocess
import re
from urlparse import urlparse
import multiprocessing
from config import cfg
from setuplogging import setup_logging
import stats
import draw
import sys
import signal

#We do not need exact floating point numbers, use builtin "float" instead
#from decimal import getcontext, Decimals

class CameraStream:
    """This class defines makes a camera stream an object"""
    def __init__(self, name, camera_stream):
        self.name = name
        self.omxplayer_extra_options = ""
        #Backwards compatible logic for rtsp_urls
        #New option every camera_stream is a dictionary
        if type(camera_stream) == dict:
            #Handle the new options
            self.rtsp_url = camera_stream["rtsp_url"]
            #Check if rtsp_over_tcp option exist otherwise default to false
            self.rtsp_over_tcp=camera_stream["rtsp_over_tcp"] if 'rtsp_over_tcp' in camera_stream else False
            #If rtsp over tcp option is true add extra option to omxplayer
            if self.rtsp_over_tcp:
                self.omxplayer_extra_options = self.omxplayer_extra_options + "--avdict rtsp_transport:tcp"

        #Old option every camera_stream is a string with one option the rtsp_url
        elif type(camera_stream) == str:
            self.rtsp_url = camera_stream
            self.omxplayer_extra_options = ""
        else:
            logger.error("Rtsp_urls config option should be a list or camera_streams config option should be a list of dictionaries")


        self.parsed=urlparse(self.rtsp_url)
        self.port = self.parsed.port
        self.hostname = self.parsed.hostname
        self.rtsp_options_cmd = "OPTIONS rtsp://" + self.hostname + ":" + str(self.port) + " RTSP/1.0\r\nCSeq: 1\r\nUser-Agent: python\r\nAccept: application/sdp\r\n\r\n"

    def is_connectable(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((self.hostname, self.port))
            #Use OPTIONS command to check if we are dealing with a real rtsp server
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


    def show_status(self):
        self.normal_fieldwidth=self.coordinates[2] - self.coordinates[0]
        self.normal_fieldheight=self.coordinates[3] - self.coordinates[1]
        draw.placeholder(self.coordinates[0], self.coordinates[1], self.normal_fieldwidth, self.normal_fieldheight, "images/connecting.png", self.pygamescreen)

    def start_stream(self, coordinates,pygamescreen):
        self.coordinates=coordinates
        self.pygamescreen=pygamescreen
        logger.debug("start stream " + self.name)
        self.show_status()

        self.stopworker= multiprocessing.Value('b', False)

        #Start worker process
        self.worker = multiprocessing.Process(target=worker.worker, args=(self.name,self.rtsp_url,self.omxplayer_extra_options,self.coordinates,self.stopworker))
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



def draw_screen(cam_streams_to_stop,cam_streams_to_draw,resolution,nr_of_columns,fixed_width,fixed_height,autostretch):

    resolution_width=int(resolution[0])
    resolution_height=int(resolution[1])
    nr_of_columns=int(nr_of_columns)


    #First stop all running streams
    for cam_stream_to_stop in cam_streams_to_stop:
        cam_stream_to_stop.stop_stream()

    #Setup global pygame_noconnectable_surface
    global pygame_noconnectable_surface

    #Start algorithm to start new streams
    fields=len(cam_streams_to_draw)
    if fields == 0:
        logger.error("No connectable streams detected")
        #Check if pygame_noconnectable_surface already exists before redrawing
        try:
            pygame_noconnectable_surface.get_parent()
        except:
            logger.debug("pygame_noconnectable_surface does not exist, draw it")
            draw.destroy()
            pygamescreen = draw.init(resolution)
            pygame_noconnectable_surface = draw.placeholder(0, 0, resolution_width, resolution_height, "images/noconnectable.png", pygamescreen)
        return
    else:
        draw.destroy()
        #Reset pygame_noconnectable_surface
        pygame_noconnectable_surface=0
        pygamescreen = draw.init(resolution)


    logger.debug( "number of fields= " + str(fields))

    #If you have less fields than columns then only set fields amount columns
    if fields <= nr_of_columns:
        nr_of_columns=fields

    #We calculate needed numbers of rows based on how many fields we have and how many columns per row we want
    nr_of_rows=math.ceil(float(fields)/nr_of_columns)

    default_fieldwidth=resolution_width/nr_of_columns
    default_fieldheight=int(resolution_height/nr_of_rows)

    normal_fieldwidth=default_fieldwidth
    normal_fieldheight=default_fieldheight

    if fixed_width is not None:
        total_actual_width=  nr_of_columns * fixed_width
        if not total_actual_width > resolution_width:
            normal_fieldwidth=fixed_width
            logger.debug("Detected advanced fixed_width config option, setting normal_fieldwidth to " + str(normal_fieldwidth))
        else:
            logger.error("Total sum of advanced fixed_width (nr_columns * fixed_width) option (" + str(total_actual_width) + ") is more then available width (" + str(resolution_width) + "), falling back to autocalculated width: " + str(normal_fieldwidth))


    if fixed_height is not None:
       total_actual_height=  nr_of_rows * fixed_height
       if not total_actual_height > resolution_height:
           normal_fieldheight=fixed_height
           logger.debug("Detected advanced fixed_height config option, setting normal_fieldheight to " + str(normal_fieldheight))
       else:
           logger.error("Total sum of advanced fixed_height (nr rows * fixed_height) option (" + str(total_actual_height) + ") is more then available height (" + str(resolution_height) + "), falling back to autocalculated height: " + str(normal_fieldheight))

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
            if fixed_width is None and autostretch is True:
                #Sometimes this will override to the same value if the window end was already at the end of the screen
                #Other times it will really override to the end of the screen
                x2= resolution_width
            else:
                #Start calculation to display placeholders
                free_horizontal_pixels = resolution_width - x2
                if free_horizontal_pixels > 0:
                    logger.debug("We have some unused screen and autostretch is disabled. Start drawing placeholders")
                    nr_of_placeholders=free_horizontal_pixels/normal_fieldwidth
                    count_placeholders = 0
                    placeholder_x = x1 + normal_fieldwidth
                    placeholder_y = y1
                    while count_placeholders < nr_of_placeholders:
                        draw.placeholder(placeholder_x, placeholder_y, normal_fieldwidth, normal_fieldheight, "images/placeholder.png", pygamescreen)
                        count_placeholders = count_placeholders + 1
                        placeholder_x = placeholder_x + normal_fieldwidth

        logger.debug("cam stream name =" + cam_stream.name)
        cam_stream_name = "cam_stream" + str(currentwindow)
        # x1 #x coordinate upper left corner
        # y1 #y coordinate upper left corner
        # x2 #x coordinate absolute where window should end, count from left to right
        # y2 #y coordinate from where window should end, count from top to bottom of screen
        cam_stream.start_stream([x1,y1,x2,y2],pygamescreen)
        cam_stream.printcoordinates()

        currentwindow = currentwindow + 1


def setup_camera_streams(camera_streams):
    '''Instantiate camera instances and put them in a list'''
    cam_streams=[]
    counter=0
    for camera_stream in camera_streams:
        #camera_stream is a string in the old deprecated behaviour and is a dictionary in the new behaviour
        #CameraStream instantiation handles both
        counter = counter +1
        cam_stream_name = "cam_stream" + str(counter)
        cam_stream=CameraStream(cam_stream_name,camera_stream)
        cam_streams.append(cam_stream)
    return cam_streams

def get_free_gpumem():
    '''Returns free gpu memory'''
    free_gpumem=None
    try:
        gpumemresult=subprocess.check_output(['/usr/bin/vcdbg','reloc'])
    except OSError as e:
        logger.error("Can not find or run the vcdbg binary to get free gpu mem")
    else:
        try:
            regex_result=re.search("(\d+[a-zA-Z]?) free memory .*",gpumemresult)
            free_gpumem=str(regex_result.group(1))
        except AttributeError as parseerror:
            logger.debug("Got " + str(parseerror) + " error when parsing free memory")
        else:
            logger.debug("Free gpu memory value is " + str(free_gpumem))

    return free_gpumem


def check_free_gpumem():
    '''Returns 0 if enough mem is available, returns 1 if not enough mem is available'''
    threshold_bytes = 80000000
    free_gpumem = get_free_gpumem()
    if free_gpumem is not None:
        conversions = {'K': 1024, 'M': 1024 ** 2, 'G': 1024 ** 3, 'T': 1024 ** 4}
        free_gpumem_bytes = float(re.sub('[A-Za-z]+','', free_gpumem))*conversions.get(re.sub('\d+','', free_gpumem),1)
        logger.debug("Free memory in bytes: " + str(free_gpumem_bytes))
        if int(free_gpumem_bytes) < int(threshold_bytes):
            logger.error("Free gpu mem is " + str(free_gpumem_bytes) + " bytes which is less than " + str(threshold_bytes) + " bytes. Streams might fail to start. Consider assigning more memory to gpu in /boot/config.txt with the gpu_mem option")
            return 1
        else:
            return 0
    else:
        logger.error("Could not determine free gpu memory, you need to check for yourself")
        return None


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

def handle_stats( stats_counter ):
    stats_counter_thresh=40
    # Updating stats for rpisurv community every 40 loops
    if stats_counter % stats_counter_thresh == 0:
        stats.update_stats(uniqid, str(stats.get_runtime(start_time)), update_stats_enabled)
    else:
        logger.debug("stats_counter is " + str(stats_counter) + ". Only sending every " + str(stats_counter_thresh))

def quit_on_keyboard(cam_streams_to_stop):
    if draw.check_keypress_end():
        draw.destroy()
        for cam_stream_to_stop in cam_streams_to_stop:
            cam_stream_to_stop.stop_stream()
        sys.exit(0)


def sigterm_handler(_signo, _stack_frame):
    draw.destroy()
    sys.exit(0)

if __name__ == '__main__':

    signal.signal(signal.SIGTERM, sigterm_handler)

    #Setup logger
    logger = setup_logging()

    #Read in config
    resolution=set_resolution()
    nr_of_columns=cfg['essentials']['nr_of_columns'] #Max amount of columns per row
    keep_first_screen_layout=cfg['essentials']['keep_first_screen_layout'] if 'keep_first_screen_layout' in cfg["essentials"] else False
    autostretch=cfg['essentials']['autostretch'] if 'autostretch' in cfg["essentials"] else False

    if type(cfg["advanced"]) is dict:
        fixed_width=cfg['advanced']['fixed_width'] if 'fixed_width' in cfg["advanced"] else None #Override of autocalculation width if set
        fixed_height=cfg['advanced']['fixed_height'] if 'fixed_height' in cfg["advanced"] else None #Override of autocalculation height if set
        update_stats_enabled=cfg['advanced']['update_stats'] if 'update_stats' in cfg["advanced"] else True #Override of update_stats if set
        interval_check_status=cfg['advanced']['interval_check_status'] if 'interval_check_status' in cfg["advanced"] else 25 #Override of interval_check_status if set
        memory_usage_check=cfg['advanced']['memory_usage_check'] if 'memory_usage_check' in cfg["advanced"] else True #Override of memory_usage_check if set
    else:
        fixed_width=None
        fixed_height=None
        update_stats_enabled=True
        interval_check_status=25
        memory_usage_check=True

    logger.debug("nr_of_columns = " + nr_of_columns)
    logger.debug("interval_check_status = " + str(interval_check_status))
    #rtsp_urls option is obsolete but for backwards compatibility still used if the new option camera_streams is not set
    if 'camera_streams' in cfg["essentials"]:
        logger.debug("camera_streams config option exist, using this one")
        camera_streams=cfg['essentials']['camera_streams']
    else:
        logger.error("rtsp_urls config option is deprecated, please use the new camera_streams option")
        camera_streams=cfg['essentials']['rtsp_urls']

    #Setup all camerastream instances, pass an array of dictionaries in case of the new option, in the old option pass a list of rtsp_urls
    all_camera_streams=setup_camera_streams(camera_streams)

    #Start main
    previous_connectable_camera_streams=[]

    #Only draw the screen once on startup when keep_first_screen_layout option is true
    if keep_first_screen_layout:
        logger.debug("keep_first_screen_layout option is True, not changing the layout when camerastreams go down or come up over time")
        connectable_camera_streams=check_camera_streams(all_camera_streams)
        draw_screen(previous_connectable_camera_streams,connectable_camera_streams,resolution,nr_of_columns,fixed_width,fixed_height,autostretch)


    #Timers for statistics
    uniqid = stats.generate_uniqid()
    start_time = stats.start_timer()
    stats_counter=0


    while True:
        #Handle stats
        handle_stats(stats_counter)
        stats_counter += 1

        #Check free mem and log warning
        if memory_usage_check:
            check_free_gpumem()

        #Only try to redraw the screen when keep_first_screen_layout option is false, but keep the loop
        if not keep_first_screen_layout:
            #Detect when new cameras come online or others go offline
            connectable_camera_streams=check_camera_streams(all_camera_streams)

            #Other option to compare could be with to convert the list into a set: print set(connectable_camera_streams) == set(previous_connectable_camera_streams)
            #Only re-draw screen if something is changed or try redrawing if there is no camerastream that is connectable
            if cmp(connectable_camera_streams,previous_connectable_camera_streams) != 0 or len(previous_connectable_camera_streams) == 0:
                draw_screen(previous_connectable_camera_streams,connectable_camera_streams,resolution,nr_of_columns,fixed_width,fixed_height,autostretch)

            previous_connectable_camera_streams=connectable_camera_streams

        quit_on_keyboard(previous_connectable_camera_streams)

        #Draw placeholders
        draw.refresh()

        time.sleep(interval_check_status)









