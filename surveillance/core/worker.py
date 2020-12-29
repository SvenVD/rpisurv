import time
import subprocess
import platform
import os
import shlex
import signal
from .util.setuplogging import setup_logging

def worker(name, url, cvlc_extra_options, coordinates, stopworker, enableaudio, layer, display_hdmi_id, network_caching_ms):

    def convert_to_vlc_coordinates(coordinates):
        """convert omxplayer like coordinates in the form of an array [x1,y1,x2,y2] to cvlc coordinates in the form of string <width>x<height>+<x upper right corner window>+<y upper right corner window>"""
        # omxplayer coordinates in form of an array[x1, y1, x2, y2]
        # x1 #x coordinate upper left corner
        # y1 #y coordinate upper left corner
        # x2 #x coordinate absolute where window should end, count from left to right
        # y2 #y coordinate from where window should end, count from top to bottom of screen

        width = int(coordinates[2] - coordinates[0])
        height = int(coordinates[3] - coordinates[1])
        x = (int(coordinates[0]))
        y = (int(coordinates[1]))
        return str(width) + "x" + str(height) + "+" + str(x) + "+" + str(y)

    def get_aspect_ratio_from_coordinates(coordinates):
        '''
            You need to tell vlc the aspect ratio of the source, so it can fill the complete window (i.e. remove any black bars)
            This function returns the aspect ratio which is extracted from the coordinates
        '''
        width = coordinates[2] - coordinates[0]
        height = coordinates[3] - coordinates[1]
        return str(int(width)) + ':' + str(int(height))


    def construct_audio_argument(enableaudio):
        """convert omxplayer like coordinates in the form of an array [x1,y1,x2,y2] to cvlc coordinates in the form of string <width>x<height>+<x upper right corner window>+<y upper right corner window>"""
        if enableaudio:
            return "--audio --gain=1"
        else:
            return "--no-audio"


    def start_subprocess():
        command_line='/usr/bin/cvlc \
                    --aspect-ratio=' + get_aspect_ratio_from_coordinates(coordinates) + ' \
                    --vout mmal_vout \
                    --network-caching ' + str(network_caching_ms) + ' \
                    --no-video-title-show \
                    --mmal-display=hdmi-' + str(display_hdmi_id) + ' \
                    --input-timeshift-granularity=0 \
                    --repeat \
                    --mmal-vout-transparent \
                    --mmal-vout-window ' + convert_to_vlc_coordinates(coordinates) + ' \
                    --mmal-layer ' + str(layer) + ' ' \
                    + cvlc_extra_options + ' ' \
                    + construct_audio_argument(enableaudio) + ' ' \
                    + url

        command_line_shlex=shlex.split(command_line)
        logger.debug("Starting stream " + name + " with commandline " + str(command_line_shlex))
        proc=subprocess.Popen(command_line_shlex,preexec_fn=os.setsid,stdin=subprocess.PIPE)
        return proc

    def stop_subprocess(proc):
        #This kill the process group so including all children
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        proc.wait()


    #Logger setup
    logger = setup_logging( "logs/" + name + ".log",__name__)
    logger.debug("logger from " + name)

    #Ctrl-C handling
    def signal_sigint_handler(signum,frame):
        logger.info("Ctrl C was pressed")
        stopworker.value = True
    def signal_sigterm_handler(signum,frame):
        logger.info("This process was sigtermed")
        stopworker.value = True

    signal.signal(signal.SIGINT, signal_sigint_handler)
    signal.signal(signal.SIGTERM, signal_sigterm_handler)



    #Start stream and watchdog
    attempts=0
    proc=start_subprocess()
    logger.debug("stopworker.value = " + name + " " + str(stopworker.value))
    while attempts < 100000 and stopworker.value == False:
        #logger.debug("stopworker.value in loop = " + name + " " + str(stopworker.value))
        #logger.debug(f"proc.poll = {proc.poll}, proc.pid = {proc.pid}")
        if proc.poll() != None:
            proc.communicate(input="\n".encode())
            proc=start_subprocess()
            attempts = attempts + 1
            #Wait for omxplayer to crash, or not
            time.sleep(10)
            logger.info("Trying to restart " + name +" attempts:" + str(attempts))
        else:
            attempts=0
        time.sleep(0.1)

    #If we come to this point, we are instructed to kill this stream
    logger.debug("This stream " + name + " is about to be stopped")
    stop_subprocess(proc)
    logger.info("This stream " + name + " has been stopped")
