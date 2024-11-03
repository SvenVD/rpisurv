import logging
import base64
import re
import socket
import os
import sys
import subprocess
import shlex
import signal
import time
import urllib.request, urllib.error, urllib.parse
from urllib.parse import urlparse

logger = logging.getLogger('l_default')


class Stream:
    """This class makes a stream an object"""
    def __init__(self, name, stream, background_drawinstance, xdisplay_id,monitor_number,monitor_x_offset,monitor_y_offset):
        self.name = name
        self.worker = None
        self.stream_started = False
        self.xdisplay_id = xdisplay_id
        self.monitor_number = monitor_number
        self.monitor_x_offset = monitor_x_offset
        self.monitor_y_offset = monitor_y_offset
        self.background_drawinstance = background_drawinstance
        self.streamprocess = None
        self.mpv_extra_options = ""
        #This option overrides any other coordinates passed to this stream
        self.force_coordinates=stream.setdefault("force_coordinates", False)
        self.freeform_advanced_mpv_options = stream.setdefault("freeform_advanced_mpv_options","")
        self.timeout_waiting_for_init_stream = stream.setdefault("timeout_waiting_for_init_stream", 7)
        self.probe_timeout = stream.setdefault("probe_timeout",3)
        self.imageurl = stream.setdefault("imageurl", False)
        self.url = stream["url"]
        self.enableaudio = stream.setdefault("enableaudio", False)
        self.showontop = stream.setdefault("showontop", False)
        if self.imageurl and self.showontop:
            logger.error(f"Stream: {self.name} is an imageurl which does not support showontop" )
        self.mpv_extra_options = self.mpv_extra_options + ' ' + self.freeform_advanced_mpv_options
        self.parsed=urlparse(self.url)
        self.port = self.parsed.port
        self.scheme = self.parsed.scheme
        self.hostname = self.parsed.hostname
        self.obfuscated_credentials_url = '{}://{}'.format(self.scheme, self.hostname)
        #Handle no port given
        if self.scheme == "rtsp":
            #handle if no port is given
            if self.port == None:
                # Default to default rtsp port, if no port is given in the url
                self.port = 554

            #Command used for rtsp probing
            self.rtsp_options_cmd = "OPTIONS " + self._manipulate_credentials_in_url("remove")  + " RTSP/1.0\r\nCSeq: 1\r\nUser-Agent: rpisurv\r\nAccept: application/sdp\r\n\r\n"

        self.obfuscated_credentials_url = self._manipulate_credentials_in_url("obfuscate")

        if self.scheme not in ["rtsp", "http", "https", "file", "rtmp"]:
            logger.error("Stream: " + self.name + " Scheme " + self.scheme + " in " + self.obfuscated_credentials_url + " is currently not supported, you can make a feature request on https://community.rpisurv.net")
            sys.exit()
        logger.debug(f'Stream: {self.name} object initialised with {stream}, {self.background_drawinstance}, {self.xdisplay_id}')

    def is_imageurl(self):
        """Returns true if this stream is an imageurl"""
        return self.imageurl

    def _manipulate_credentials_in_url(self,action):
        '''
        Depending on action:
        "obfuscate" :  is used to not log the credentials in plain text in the logfile for error messages
        "remove" : is used for the rtsp options probe
        '''
        if self.parsed.password is not None or self.parsed.username is not None:
            host_info = self.parsed.netloc.rpartition('@')[-1]
            if action == "obfuscate":
                obfuscated = self.parsed._replace(netloc='<hidden_username>:<hidden_password>@{}'.format(host_info))
                return obfuscated.geturl()
            elif action == "remove":
                no_credentials = self.parsed._replace(netloc='{}'.format(host_info))
                return no_credentials.geturl()
        else:
            return self.url

    def _urllib2open_wrapper(self):
        '''Handles authentication username and password inside URL like following example: "http://test:test@httpbin.org:80/basic-auth/test/test" '''
        headers = {'User-Agent': 'Mozilla/5.0'}
        if self.parsed.password is not None and self.parsed.username is not None:
            host_info = self.parsed.netloc.rpartition('@')[-1]
            strippedcreds_url = self.parsed._replace(netloc=host_info)
            request = urllib.request.Request(strippedcreds_url.geturl(), None, headers)
            cred='%s:%s' % (self.parsed.username, self.parsed.password)
            base64string = base64.b64encode(cred.encode()).decode()
            request.add_header("Authorization", "Basic %s" % base64string)
            return urllib.request.urlopen(request, timeout=self.probe_timeout)
        else:
            request = urllib.request.Request(self.url, None, headers )
            return urllib.request.urlopen(request, timeout=self.probe_timeout)

    def is_connectable(self):
        if self.scheme == "rtmp":
            try:
                ffprobeoutput = subprocess.check_output(['/usr/bin/ffprobe', '-v', 'quiet', "-print_format", "flat", "-show_error", self.url], text=True, timeout=self.probe_timeout)
                return True
            except subprocess.TimeoutExpired as e:
                logger.error(f"Stream: is_connectable: {self.name} {self.obfuscated_credentials_url} Not Connectable (ffprobe timed out, try increasing probe_timeout for this stream), configured timeout: {self.probe_timeout}")
                return False
            except Exception as e:
                erroroutput_newlinesremoved=e.output.replace('\n', ' ')
                logger.error(f"Stream: is_connectable: {self.name} {self.obfuscated_credentials_url} Not Connectable ({erroroutput_newlinesremoved}), configured timeout: {self.probe_timeout}")
                return False
        if self.scheme == "rtsp":
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(self.probe_timeout)
                s.connect((self.hostname, self.port))
                #Use OPTIONS command to check if we are dealing with a real rtsp server
                s.send(self.rtsp_options_cmd.encode())
                rtsp_response=s.recv(4096)
                s.close()
            except Exception as e:
                logger.error("Stream: is_connectable: " + self.name + " " + str(self.obfuscated_credentials_url) + " Not Connectable (failed socket connect), configured timeout: " + str(self.probe_timeout) + " " + repr(e))
                return False

            #If we come to this point it means we have some data received, before we return True we need to check if are connected to an RTSP server
            if not rtsp_response:
                logger.error("Stream: is_connectable: " + self.name + " " + str(self.obfuscated_credentials_url) + " Not Connectable (failed rtsp validation, no response from rtsp server)")
                return False

            if re.match("RTSP/1.0",rtsp_response.decode('utf-8').splitlines()[0]):
                logger.debug("Stream: is_connectable: " + self.name + " " + str(self.obfuscated_credentials_url) + " Connectable")
                return True
            else:
                logger.error("Stream: is_connectable: " + self.name + " " + str(self.obfuscated_credentials_url) + " Not Connectable (failed rtsp validation, is this an rtsp stream?)")
                return False
        elif self.scheme in ["http","https"]:
            try:
                connection = self._urllib2open_wrapper()
                if connection.getcode() == 200:
                    logger.debug("Stream: is_connectable: " + self.name + " " + str(self.obfuscated_credentials_url) + " Connectable")
                    return True
                else:
                    logger.error("Stream: is_connectable: " + self.name + " " + str(self.obfuscated_credentials_url) + " Not Connectable (http response code: " + str(connection.getcode()) + ")")
                    return False
                connection.close()
            except urllib.error.URLError as e:
                logger.error("Stream: is_connectable: " + self.name + " " + str(self.obfuscated_credentials_url) + " Not Connectable (URLerror), " + repr(e))
                return False
            except socket.timeout as e:
                logger.error("Stream: is_connectable: " + self.name + " " + str(self.obfuscated_credentials_url) + " Not Connectable (failed socket connect, configured timeout: " + str(self.probe_timeout) + " ), " + repr(e))
                return False
            except Exception as e:
                logger.error("Stream: is_connectable: " + self.name + " " + str(self.obfuscated_credentials_url) + " Not Connectable (" + repr(e) + " )")
                return False
        elif self.scheme == "file":
            if os.path.isfile(self.parsed.path):
                logger.debug(f"Stream: is_connectable: {self.name} {self.parsed.path} file found" )
                return True
            else:
                logger.error(f"Stream: is_connectable: {self.name} {self.parsed.path} file not found")
                return False
        else:
            logger.error("Stream: is_connectable: " + self.name + " Scheme " + str(self.scheme) + " in " + str(self.obfuscated_credentials_url) + " is currently not supported, you can make a feature request on https://community.rpisurv.net")
            sys.exit()

    def calculate_field_geometry(self):
        self.normal_fieldwidth=int(self.coordinates[2] - self.coordinates[0])
        self.normal_fieldheight=int(self.coordinates[3] - self.coordinates[1])

    def show_status(self):
        if not self.hidden:
            self.calculate_field_geometry()
            self.background_drawinstance.placeholder(self.coordinates[0], self.coordinates[1], self.normal_fieldwidth, self.normal_fieldheight, "images/connecting.png")


    def hide(self):
        """This function is needed for internal caching handling"""
        logger.debug(f"Stream: {self.name}: hide stream")
        #Saving this state for as watchdog needs to restart stream
        self.hidden = True
        subprocess.run(['wmctrl', '-r', self.name, '-b', 'add,hidden'])
    def unhide(self):
        """This function is needed for internal caching handling"""
        logger.debug(f"Stream: {self.name}: unhide stream")
        #Saving this state for as watchdog needs to restart stream
        self.hidden = False
        self.show_status()
        subprocess.run(['wmctrl', '-r', self.name, '-b', 'remove,hidden'])
    def _show_on_top(self):
        """This is toggle set by user config"""
        logger.debug(f"Stream: {self.name}: show stream on top")
        self.unhide()
        subprocess.run(['wmctrl', '-r', self.name, '-b', 'add,above'])
    def _get_aspect_ratio_from_coordinates(self):
        '''
            You need to tell vlc the aspect ratio of the source, so it can fill the complete window (i.e. remove any black bars)
            This function returns the aspect ratio which is extracted from the coordinates
        '''
        width = self.coordinates[2] - self.coordinates[0]
        height = self.coordinates[3] - self.coordinates[1]
        return str(int(width)) + ':' + str(int(height))

    def _convert_to_mpv_coordinates(self):
        """convert omxplayer like coordinates in the form of an array [x1,y1,x2,y2] to cvlc coordinates in the form of string <width>x<height>+<x upper right corner window>+<y upper right corner window>"""
        # omxplayer coordinates in form of an array[x1, y1, x2, y2]
        # x1 #x coordinate upper left corner
        # y1 #y coordinate upper left corner
        # x2 #x coordinate absolute where window should end, count from left to right
        # y2 #y coordinate from where window should end, count from top to bottom of screen
        width = int(self.coordinates[2] - self.coordinates[0])
        height = int(self.coordinates[3] - self.coordinates[1])
        x = (int(self.coordinates[0]))
        y = (int(self.coordinates[1]))
        return str(width) + "x" + str(height) + "+" + str(x) + "+" + str(y)
    def _construct_audio_argument(self):
        if not self.enableaudio:
            return "--no-audio"
    def _wait_for_window_to_be_initialized(self):
      """
      This functions waits until wmctrl sees the window, this is needed so following up wmctrl commands succeed"
      """
      logger.debug(f"Stream: {self.name}: _wait_for_window_to_be_initialized")
      window_found = False
      attempts = 0
      #This is the timeout in seconds
      max_attempts = self.timeout_waiting_for_init_stream * 2
      time.sleep(0.5)
      while not window_found and attempts < max_attempts:
        result = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True)
        if self.name in result.stdout:
          window_found = True
          logger.debug(f"Stream: {self.name}: _wait_for_window_to_be_initialized, window found ({attempts}/{max_attempts})")
        else:
          logger.debug(f"Stream: {self.name}: _wait_for_window_to_be_initialized, window not present ({attempts}/{max_attempts})")
          time.sleep(0.5)  # Wait for 500ms before checking again
          attempts += 1

      if not window_found:
        logger.error(f"Stream: {self.name}: _wait_for_window_to_be_initialized, window not found ({attempts}/{max_attempts}. Stopping attempt")

    def run_stream_watchdog(self):
      """
      This function watches if the process is still alive and if not attempts to restart it
      """
      logger.debug(f"Stream: {self.name}: run_stream_watchdog: Starting watchdog")
      if self.stream_started:
        if self.streamprocess.poll() != None:
          self.streamprocess.communicate(input="\n".encode())
          logger.error(f"Stream: {self.name}: run_stream_watchdog: is not responding trying to restart")
          self.restart_stream()
        else:
          logger.debug(f"Stream: {self.name}: run_stream_watchdog: OK is responding ")
      else:
          logger.debug(f"Stream: {self.name}: run_stream_watchdog: was instructed to be stopped, not running watchdog")
    def start_stream(self, coordinates, hidden):
        self.hidden = hidden
        if self.force_coordinates:
            logger.debug(f"Stream: {self.name}: start_stream: uses force_coordinates { str(self.force_coordinates) } which will override pre-calculated coordinates of { str(coordinates) }")
            self.coordinates = self.force_coordinates
        else:
            self.coordinates=coordinates

        logger.debug(f"Stream: {self.name}: start_stream")

        self.show_status()
        if self.imageurl:
            # Start stream
            # We need --loop for when streaming finite video file on disk
            self.command_line = f'core/util/image_viewer.py \
                        { self.coordinates[0] } \
                        { self.coordinates[1] } \
                        { self.coordinates[2] } \
                        { self.coordinates[3] } \
                        {self.monitor_x_offset} \
                        {self.monitor_y_offset} \
                        {self.url} \
                        {self.name}'

        else:
            self.command_line = f'/usr/bin/mpv \
                        --msg-level=all=warn \
                        --loop \
                        --video-aspect-override=\'{self._get_aspect_ratio_from_coordinates()}\' \
                        --title=\'{self.name}\' \
                        --no-border \
                        --window-minimized=yes \
                        --no-input-default-bindings \
                        --no-input-builtin-bindings \
                        --cursor-autohide=always \
                        --screen=\'{self.monitor_number}\' \
                        --geometry=\'{self._convert_to_mpv_coordinates()}\' \
                        {self.mpv_extra_options} \
                        {self._construct_audio_argument()} \
                        {self.url}'

        # Split into list so subprocess can process all arguments
        self.command_line_shlex = shlex.split(self.command_line)
        logger.debug(f"Stream: {self.name}: start_stream: with commandline {str(self.command_line_shlex)}")
        self.env_with_display = os.environ.copy()
        self.env_with_display['DISPLAY'] = str(self.xdisplay_id)
        self.streamprocess = subprocess.Popen(self.command_line_shlex, preexec_fn=os.setsid, stdin=subprocess.PIPE,env=self.env_with_display)

        self._wait_for_window_to_be_initialized()


        if self.showontop and not self.hidden:
            logger.debug(f"Stream: {self.name}: start_stream on top of the other streams")
            self._show_on_top()

        if not self.hidden:
            logger.debug(f"Stream: {self.name}: start_stream and showing on screen")
            self.unhide()
        else:
            logger.debug(f"Stream: {self.name}: start_stream and NOT showing on screen")
            self.hide()
        self.stream_started = True

    def restart_stream(self):
        self.stop_stream()
        self.start_stream(self.coordinates, self.hidden)

    def stop_stream(self):
        logger.debug(f"Stream: {self.name}: stop_stream")
        #At startup streamprocess is not known yet
        if self.streamprocess != None:
          # This kill the process group so including all children
          try:
            os.killpg(os.getpgid(self.streamprocess.pid), signal.SIGKILL)
          except ProcessLookupError:
            logger.debug(f"Stream: {self.name}: stop_stream: The process group or process is already gone")
            # The process group or process is already gone
            pass
          self.streamprocess.wait()
        self.stream_started= False
