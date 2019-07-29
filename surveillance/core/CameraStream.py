import logging
import multiprocessing
import platform
import base64
import re
import socket
import time
import sys
import io
import urllib2
from urlparse import urlparse

import worker
import util.draw as draw

if platform.system() == "Linux":
    from dbus import DBusException, Int64, String, ObjectPath
    from util.bus_finder import BusFinder
    from util.dbus_connection import DBusConnection, DBusConnectionError

logger = logging.getLogger('l_default')


class CameraStream:
    """This class makes a camera stream an object"""
    def __init__(self, name, camera_stream):
        self.name = name
        self.worker = None
        self.omxplayer_extra_options = ""
        self.probe_timeout = camera_stream.setdefault("probe_timeout",3)
        self.imageurl = camera_stream.setdefault("imageurl", False)
        self.url = camera_stream["url"]
        #Check if rtsp_over_tcp option exist otherwise default to false
        self.rtsp_over_tcp=camera_stream["rtsp_over_tcp"] if 'rtsp_over_tcp' in camera_stream else False
        #If rtsp over tcp option is true add extra option to omxplayer
        if self.rtsp_over_tcp:
            self.omxplayer_extra_options = self.omxplayer_extra_options + "--avdict rtsp_transport:tcp"
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

        if self.scheme not in ["rtsp", "http", "https"]:
            logger.error("CameraStream: " + self.name + " Scheme " + self.scheme + " in " + self.obfuscated_credentials_url + " is currently not supported, you can make a feature request on https://feathub.com/SvenVD/rpisurv")
            sys.exit()


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

    def _setup_dbus_connection(self):
        """ Setups a dbus connection to the omxplayer instances started during worker processes """
        #These are set to the same name during start of the worker processes
        _dbus_name='org.mpris.MediaPlayer2.'+ self.name
        busfinder = BusFinder()
        triesthreshold=20
        tries = 0
        while tries < triesthreshold:
          logger.debug('CameraStream: ' + self.name + ' DBus connect attempt: {}'.format(tries))
          try:
            self.dbusconnection = DBusConnection( busfinder.get_address(), _dbus_name)
            logger.debug('CameraStream: ' + self.name + ' Connected to omxplayer at dbus address:' + busfinder.get_address() + ' with dbus name: ' + _dbus_name)
            break
          except (DBusConnectionError, IOError):
            logger.debug('CameraStream: ' + self.name + ' Failed to connect to omxplayer at dbus address:' + busfinder.get_address() + ' with dbus name: ' + _dbus_name)
            tries += 1
            if tries == triesthreshold:
              logger.error('CameraStream: ' + self.name + ' CRITICAL Failed to connect to omxplayer at dbus address:' + busfinder.get_address() + ' with dbus name: ' + _dbus_name)
              self.dbusconnection = None
            time.sleep(0.5)

    def set_videopos(self,new_coordinates):
        logger.debug('CameraStream: ' + self.name + ' Set new position for ' + self.name + ' with new coordinates: + ' + str(new_coordinates) + ' on dbus interface')
        if platform.system() == "Linux":
            if self.dbusconnection is not None:
                self.dbusconnection.VideoPosWrapper((ObjectPath('/not/used'), String(" ".join(map(str,new_coordinates)))))
            else:
                logger.error('CameraStream: ' + self.name + ' has no dbus connection, probably because omxplayer crashed because it can not connect to this stream. As a result we could not change its videopos dynamically for this stream at this time.')

    def hide_stream(self):
        logger.debug('CameraStream: Hide stream instruction ' + self.name + ' received from dbus interface')
        if platform.system() == "Linux":
            if self.dbusconnection is not None:
                self.dbusconnection.player_interface.SetAlpha(ObjectPath('/not/used'), Int64(0))
            else:
                logger.error('CameraStream: ' + self.name + ' has no dbus connection, probably because omxplayer crashed because it can not connect to this stream. As a result we could not hide this stream at this time.')

    def unhide_stream(self):
        logger.debug('CameraStream: Unhide stream instruction ' + self.name + ' received from dbus interface')
        if platform.system() == "Linux":
            if self.dbusconnection is not None:
                self.dbusconnection.player_interface.SetAlpha(ObjectPath('/not/used'), Int64(255))
            else:
                logger.error('CameraStream: ' + self.name + ' has no dbus connection, probably because omxplayer crashed because it can not connect to this stream. As a result we could not unhide this stream at this time.')

    def _urllib2open_wrapper(self):
        '''Handles authentication username and password inside URL like following example: "http://test:test@httpbin.org:80/basic-auth/test/test" '''
        if self.parsed.password is not None and self.parsed.username is not None:
            host_info = self.parsed.netloc.rpartition('@')[-1]
            strippedcreds_url = self.parsed._replace(netloc=host_info)
            print strippedcreds_url.geturl()
            request = urllib2.Request(strippedcreds_url.geturl())
            base64string = base64.encodestring('%s:%s' % (self.parsed.username, self.parsed.password)).replace('\n', '')
            request.add_header("Authorization", "Basic %s" % base64string)
            return urllib2.urlopen(request, timeout=self.probe_timeout)
        else:
            return urllib2.urlopen(self.url, timeout=self.probe_timeout)

    def is_connectable(self):
        if self.scheme == "rtsp":
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(self.probe_timeout)
                s.connect((self.hostname, self.port))
                #Use OPTIONS command to check if we are dealing with a real rtsp server
                s.send(self.rtsp_options_cmd)
                rtsp_response=s.recv(4096)
                s.close()
            except Exception as e:
                logger.error("CameraStream: " + self.name + " " + str(self.obfuscated_credentials_url) + " Not Connectable (failed socket connect), configured timeout: " + str(self.probe_timeout) + " " + repr(e))
                return False

            #If we come to this point it means we have some data received, before we return True we need to check if are connected to an RTSP server
            if not rtsp_response:
                logger.error("CameraStream: " + self.name + " " + str(self.obfuscated_credentials_url) + " Not Connectable (failed rtsp validation, no response from rtsp server)")
                return False

            if re.match("RTSP/1.0",rtsp_response.splitlines()[0]):
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
             except urllib2.URLError as e:
                logger.error("CameraStream: " + self.name + " " + str(self.obfuscated_credentials_url) + " Not Connectable (URLerror), " + repr(e))
                return False
             except socket.timeout as e:
                logger.error("CameraStream: " + self.name + " " + str(self.obfuscated_credentials_url) + " Not Connectable (failed socket connect, configured timeout: " + str(self.probe_timeout) + " ), " + repr(e))
                return False
        else:
            logger.error("CameraStream: " + self.name + " Scheme " + str(self.scheme) + " in " + str(self.obfuscated_credentials_url) + " is currently not supported, you can make a feature request on https://community.rpisurv.net")
            sys.exit()

    def calculate_field_geometry(self):
        self.normal_fieldwidth=self.coordinates[2] - self.coordinates[0]
        self.normal_fieldheight=self.coordinates[3] - self.coordinates[1]

    def show_status(self):
        self.calculate_field_geometry()
        draw.placeholder(self.coordinates[0], self.coordinates[1], self.normal_fieldwidth, self.normal_fieldheight, "images/connecting.png", self.pygamescreen)


    def refresh_image_from_url(self):
        if self.imageurl:
            # This is an imageurl instead of a camerastream, do not start omxplayer stuff
            if self.is_connectable():
                try:
                    # image_str = urllib2.urlopen(self.url).read()
                    image_str = self._urllib2open_wrapper().read()
                    # create a file object (stream)
                    self.image_file = io.BytesIO(image_str)
                    self.calculate_field_geometry()
                    draw.placeholder(self.coordinates[0], self.coordinates[1], self.normal_fieldwidth, self.normal_fieldheight, self.image_file, self.pygamescreen)
                except Exception as e:
                    #Do not crash rpisurv if there is something wrong with loading the image at this time
                    logger.error("CameraStream: This stream " + self.name + " refresh_image_from_url " + repr(e))
        else:
            logger.debug("CameraStream: This stream " + self.name + " is not an imageurl, skip refreshing imageurl")

    def start_stream(self, coordinates, pygamescreen, cached):
        self.coordinates=coordinates
        self.pygamescreen=pygamescreen
        logger.debug("CameraStream: Start stream " + self.name)


        if not self.imageurl:
            #Start worker process and dbus connnection only if it isn't running already
            if self.worker and self.worker.is_alive():
                logger.debug("CameraStream: Worker from " + self.name + " is still alive not starting new worker")
            else:
                self.stopworker = multiprocessing.Value('b', False)
                self.worker = multiprocessing.Process(target=worker.worker, args=(self.name,self.url,self.omxplayer_extra_options,self.coordinates,self.stopworker))
                self.worker.daemon = True
                self.worker.start()
                if platform.system() == "Linux":
                    #dbus connection can only be setup once the stream is correctly started
                    self._setup_dbus_connection()

            #Update position
            self.set_videopos(self.coordinates)

        if not cached:
            logger.debug("CameraStream: This stream " + self.name + " is not running in cache")
            self.show_status()

            if self.imageurl:
                self.refresh_image_from_url()


        else:
            logger.debug("CameraStream: This stream " + self.name + " is running in cache")

    def restart_stream(self):
        self.stop_stream()
        self.start_stream(self.coordinates)

    def printcoordinates(self):
        print self.coordinates

    def stop_stream(self):
        logger.debug("CameraStream: Stop stream " + self.name)
        if not self.imageurl:
            #Only stop something if this is not an imageurl, for imageurl nothing has to be stopped
            #Stopworker shared value will stop the while loop in the worker, so the worker will run to end. No need to explicitely terminate the worker
            self.stopworker.value= True
            logger.debug("CameraStream: MAIN Value of stopworker for " + self.name + " is " + str(self.stopworker.value))

            #Wait for the worker to be terminated before continuing https://github.com/SvenVD/rpisurv/issues/84
            logger.debug("CameraStream: Executing join for stream " + self.name)
            self.worker.join()
