import logging
import multiprocessing
import base64
import re
import socket
import os
import sys
import io
import urllib.request, urllib.error, urllib.parse
from urllib.parse import urlparse

from . import worker

logger = logging.getLogger('l_default')


class CameraStream:
    """This class makes a camera stream an object"""
    def __init__(self, name, camera_stream, drawinstance, display_hdmi_id):
        self.name = name
        self.worker = None
        self.display_hdmi_id = display_hdmi_id
        self.drawinstance = drawinstance
        self.stopworker = None
        self.cvlc_extra_options = ""
        #This option overrides any other coordinates passed to this stream
        self.force_coordinates=camera_stream.setdefault("force_coordinates", False)
        self.network_caching_ms=camera_stream.setdefault("network_caching_ms", 500)
        self.freeform_advanced_vlc_options = camera_stream.setdefault("freeform_advanced_vlc_options","")
        self.probe_timeout = camera_stream.setdefault("probe_timeout",3)
        self.imageurl = camera_stream.setdefault("imageurl", False)
        self.url = camera_stream["url"]
        self.enableaudio = camera_stream.setdefault("enableaudio", False)
        self.showontop = camera_stream.setdefault("showontop", False)
        if self.imageurl and self.showontop:
            logger.error(f"CameraStream: {self.name} is an imageurl which does not support showontop" )
        #Check if rtsp_over_tcp option exist otherwise default to false
        self.rtsp_over_tcp=camera_stream["rtsp_over_tcp"] if 'rtsp_over_tcp' in camera_stream else False
        #If rtsp over tcp option is true add extra option to omxplayer
        if self.rtsp_over_tcp:
            self.cvlc_extra_options = self.cvlc_extra_options + "--rtsp-tcp"
        self.cvlc_extra_options = self.cvlc_extra_options + ' ' + self.freeform_advanced_vlc_options
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

        if self.scheme not in ["rtsp", "http", "https", "file"]:
            logger.error("CameraStream: " + self.name + " Scheme " + self.scheme + " in " + self.obfuscated_credentials_url + " is currently not supported, you can make a feature request on https://community.rpisurv.net")
            sys.exit()

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
            base64string = base64.encodestring('%s:%s' % (self.parsed.username, self.parsed.password)).replace('\n', '')
            request.add_header("Authorization", "Basic %s" % base64string)
            return urllib.request.urlopen(request, timeout=self.probe_timeout)
        else:
            request = urllib.request.Request(self.url, None, headers )
            return urllib.request.urlopen(request, timeout=self.probe_timeout)

    def is_connectable(self):
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
                logger.error("CameraStream: " + self.name + " " + str(self.obfuscated_credentials_url) + " Not Connectable (failed socket connect), configured timeout: " + str(self.probe_timeout) + " " + repr(e))
                return False

            #If we come to this point it means we have some data received, before we return True we need to check if are connected to an RTSP server
            if not rtsp_response:
                logger.error("CameraStream: " + self.name + " " + str(self.obfuscated_credentials_url) + " Not Connectable (failed rtsp validation, no response from rtsp server)")
                return False

            if re.match("RTSP/1.0",rtsp_response.decode('utf-8').splitlines()[0]):
                logger.debug("CameraStream: " + self.name + " " + str(self.obfuscated_credentials_url) + " Connectable")
                return True
            else:
                logger.error("CameraStream: " + self.name + " " + str(self.obfuscated_credentials_url) + " Not Connectable (failed rtsp validation, is this an rtsp stream?)")
                return False
        elif self.scheme in ["http","https"]:
             try:
                connection = self._urllib2open_wrapper()
                if connection.getcode() == 200:
                    logger.debug("CameraStream: " + self.name + " " + str(self.obfuscated_credentials_url) + " Connectable")
                    return True
                else:
                    logger.error("CameraStream: " + self.name + " " + str(self.obfuscated_credentials_url) + " Not Connectable (http response code: " + str(connection.getcode()) + ")")
                    return False
                connection.close()
             except urllib.error.URLError as e:
                logger.error("CameraStream: " + self.name + " " + str(self.obfuscated_credentials_url) + " Not Connectable (URLerror), " + repr(e))
                return False
             except socket.timeout as e:
                logger.error("CameraStream: " + self.name + " " + str(self.obfuscated_credentials_url) + " Not Connectable (failed socket connect, configured timeout: " + str(self.probe_timeout) + " ), " + repr(e))
                return False
             except Exception as e:
                 logger.error("CameraStream: " + self.name + " " + str(self.obfuscated_credentials_url) + " Not Connectable (" + repr(e) + " )")
                 return False
        elif self.scheme == "file":
            if os.path.isfile(self.parsed.path):
                logger.debug(f"CameraStream: {self.name} {self.parsed.path} file found" )
                return True
            else:
                logger.error(f"CameraStream: {self.name} {self.parsed.path} file not found")
                return False
        else:
            logger.error("CameraStream: " + self.name + " Scheme " + str(self.scheme) + " in " + str(self.obfuscated_credentials_url) + " is currently not supported, you can make a feature request on https://community.rpisurv.net")
            sys.exit()

    def calculate_field_geometry(self):
        self.normal_fieldwidth=int(self.coordinates[2] - self.coordinates[0])
        self.normal_fieldheight=int(self.coordinates[3] - self.coordinates[1])

    def show_status(self):
        self.calculate_field_geometry()
        self.drawinstance.placeholder(self.coordinates[0], self.coordinates[1], self.normal_fieldwidth, self.normal_fieldheight, "images/connecting.png")


    def refresh_image_from_url(self):
        if self.imageurl:
            # This is an imageurl instead of a camerastream, do not start cvlc stuff
            if self.is_connectable():
                try:
                    # image_str = urllib2.urlopen(self.url).read()
                    image_str = self._urllib2open_wrapper().read()
                    # create a file object (stream)
                    self.image_file = io.BytesIO(image_str)
                    self.calculate_field_geometry()
                    self.drawinstance.placeholder(self.coordinates[0], self.coordinates[1], self.normal_fieldwidth, self.normal_fieldheight, self.image_file)
                except Exception as e:
                    #Do not crash rpisurv if there is something wrong with loading the image at this time
                    logger.error("CameraStream: This stream " + self.name + " refresh_image_from_url " + repr(e))
        else:
            logger.debug("CameraStream: This stream " + self.name + " is not an imageurl, skip refreshing imageurl")

    def start_stream(self, coordinates, layer):
        if self.force_coordinates:
            logger.debug("CameraStream: This stream " + self.name + " uses force_coordinates " + str(self.force_coordinates) + " which will override pre-calculated coordinates of " + str(coordinates) )
            self.coordinates = self.force_coordinates
        else:
            self.coordinates=coordinates

        if self.showontop:
            logger.debug(f"CameraStream: Start stream on top  of the other streams {self.name}")
            self.layer = layer + 1
        else:
            self.layer=layer
        logger.debug("CameraStream: Start stream " + self.name + " on layer " + str(self.layer))

        if not self.imageurl:
            #Stop existing stream, if any, before drawing new
            self.stop_stream()
            # Start stream
            self.stopworker = multiprocessing.Value('b', False)
            self.worker = multiprocessing.Process(target=worker.worker, args=(
                self.name,
                self.url,
                self.cvlc_extra_options,
                self.coordinates,
                self.stopworker,
                self.enableaudio,
                self.layer,
                self.display_hdmi_id,
                self.network_caching_ms
            ))
            self.worker.daemon = True
            self.worker.start()

        self.show_status()

        if self.imageurl:
            self.refresh_image_from_url()


    def restart_stream(self):
        self.stop_stream()
        self.start_stream(self.coordinates)

    def stop_stream(self):
        logger.debug("CameraStream: Stop stream " + self.name)
        # Only stop something if this is not an imageurl, for imageurl nothing has to be stopped
        # Stopworker shared value will stop the while loop in the worker, so the worker will run to end. No need to explicitely terminate the worker
        if not self.imageurl:
            #On first instantiation there will be no stopworker and there is nothing to be stopped
            if self.stopworker is not None:
                self.stopworker.value= True
                logger.debug("CameraStream: MAIN Value of stopworker for " + self.name + " is " + str(self.stopworker.value))

                #Wait for the worker to be terminated before continuing https://github.com/SvenVD/rpisurv/issues/84
                logger.debug("CameraStream: Executing join for stream " + self.name)
                self.worker.join()
