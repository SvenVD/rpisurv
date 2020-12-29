import logging
import math
import time
import collections

from .CameraStream import CameraStream

#We do not need exact floating point numbers, use builtin "float" instead
#from decimal import getcontext, Decimals


logger = logging.getLogger('l_default')

class Screen:
    """This class creates and handles camerastreams objects and their position"""
    def __init__(self, screenname, screen_cfg, display, drawinstance):
        ## Init vars
        #Use vcgencmd dispmanx_list to see on which layer framebuffer is located
        #Highest observed was 2147483647 on a rpi4, start high with some tolerance,so caching has a long way to count down before it needs to reset the layer
        self.layer_init_value=2000000000
        self.layer=self.layer_init_value
        self.display_vlc_hdmi_id=str(int(display["hdmi"]) + 1)
        self.disable_probing_for_all_streams = screen_cfg.setdefault('disable_probing_for_all_streams', False)
        self.nr_of_columns = screen_cfg.setdefault('nr_of_columns', 2)
        self.name = screenname
        self.screen_cfg = screen_cfg
        self.camera_streams_cfg = screen_cfg["camera_streams"]
        self.duration = self.screen_cfg.setdefault('duration', 30)
        logger.debug("Screen: " + self.name + " duration from config is: " + str(self.duration))
        self.drawinstance = drawinstance
        self.first_run = True
        self.start_of_active_time = -1
        self.previous_connectable_camera_streams = []


        ## Init functions
        # Sets internal variable resolution
        self.resolution_width = int(display["resolution"]["width"])
        self.resolution_height = int(display["resolution"]["height"])
        self._init_camera_streams()


    def has_image_url(self):
        """Returns True if this screen has at least one stream that is an imageurl"""

        for camera_stream in self.all_camera_streams:
            if camera_stream.is_imageurl():
                logger.debug(
                    "Screen: " + self.name + " has_image_url: detected at least one imageurl: " + camera_stream.name )
                return True
        return False

    def _init_camera_streams(self):
        '''Instantiate camera instances and put them in a list'''
        self.all_camera_streams = []
        counter = 0
        for camera_stream in self.camera_streams_cfg:
            counter = counter + 1
            cam_stream_name = self.name + "_cam_stream" + str(counter)
            cam_stream = CameraStream(cam_stream_name, camera_stream, self.drawinstance, self.display_vlc_hdmi_id)
            self.all_camera_streams.append(cam_stream)

    def update_connectable_camera_streams(self, skip = False):
        '''Filters a list of camerastream instances into a new list of connectable camera_streams'''
        if skip:
            logger.debug("Screen: " + self.name + " Skipping checking connectable cameras, skip value is: " + str(skip))
            # Sometimes we do not want to wait on checking connectable camera streams, so this shortcut is taken (essentially skip checking)
            if self.first_run:
                # We need the camera stream to be initialised with something in the beginning if we decide to skip the checking of connectivity
                logger.debug("Screen: " + self.name + " first run")
                self.connectable_camera_streams = self.all_camera_streams
                self.first_run = False
            else:
                self.connectable_camera_streams = self.previous_connectable_camera_streams
        else:
            logger.debug("Screen: Start polling connectivity for the camera_streams part of screen: " + self.name)
            self.connectable_camera_streams=[]
            for cam_stream in self.all_camera_streams:
                    if cam_stream.is_connectable():
                        self.connectable_camera_streams.append(cam_stream)

        self.cam_streams_to_draw = self.connectable_camera_streams
        self.cam_streams_to_stop = self.previous_connectable_camera_streams


    def destroy(self):
        logger.debug("Screen: Destroying screen: " + self.name)

        for cam_stream_to_stop in self.previous_connectable_camera_streams:
            cam_stream_to_stop.stop_stream()

        # Reset vars for next iteration of this screen, object stays in memory
        self.previous_connectable_camera_streams = []
        self.first_run = True
        self.start_of_active_time = -1

    def set_layer(self,layer):
        self.layer = layer
        logger.debug("Screen: layer for screen " + self.name + " has been set to " + str(self.layer))

    def get_layer(self):
        return self.layer

    def reset_layer(self):
        logger.debug("Screen: layer for screen " + self.name + " will be reset to " + str(self.layer_init_value) + " coming from " + str(self.layer))
        self.layer=self.layer_init_value

    def reset_active_timer(self):
        logger.debug("Screen: reset_active_timer " + self.name)
        #Set start time
        self.start_of_active_time = time.time()
        logger.debug("Screen: " + self.name + " start_of_active_time: " + str(self.start_of_active_time))

    def get_active_run_time(self):
        '''Returns how long the screen is in active mode'''
        active_run_time = int(round((time.time() - self.start_of_active_time)))
        logger.debug("Screen: " + self.name + " active_run_time: " + str(active_run_time) + " / " + str(self.duration))
        return active_run_time

    def _is_connectable_streams_changed(self):
        """Returns True if previous_connectable_camera_streams list has different items from connectable_camera_streams regardless of order"""
        #logger.debug(f"connectable_camera_streams {collections.Counter(self.connectable_camera_streams)} previous_connectable_camera_streams {collections.Counter(self.previous_connectable_camera_streams)}")
        if collections.Counter(self.connectable_camera_streams) == collections.Counter(self.previous_connectable_camera_streams):
            return False
        else:
            return True

    def update_screen(self):
        # Other option to compare could be with to convert the list into a set: print set(connectable_camera_streams) == set(previous_connectable_camera_streams)
        # Only re-draw screen if something is changed or try redrawing if there is no camerastream that is connectable OR if we change the screen
        if self._is_connectable_streams_changed() or len(self.previous_connectable_camera_streams) == 0:
            logger.debug(f"Screen {self.name} needs update/redraw: changes in connectable camera streams detected.( previous: {len(self.previous_connectable_camera_streams)} / now: {len(self.connectable_camera_streams)} or different connectable streams then before )")
            #Stop all running streams before redrawing
            for cam_stream_to_stop in self.cam_streams_to_stop:
                cam_stream_to_stop.stop_stream()


            nr_of_columns=int(self.nr_of_columns)

            # Start algorithm to start new streams
            fields = len(self.cam_streams_to_draw)
            logger.debug( "Screen: " + self.name + " number of fields= " + str(fields))

            if fields == 0:
                #Draw no connectable placeholder
                self.drawinstance.placeholder(0, 0, self.resolution_width, self.resolution_height, "images/noconnectable.png")
                self.previous_connectable_camera_streams = self.connectable_camera_streams
                return


            #If you have less fields than columns then only set fields amount columns
            if fields <= nr_of_columns:
                nr_of_columns=fields

            #We calculate needed numbers of rows based on how many fields we have and how many columns per row we want
            nr_of_rows=math.ceil(float(fields)/nr_of_columns)

            default_fieldwidth=int(self.resolution_width/nr_of_columns)
            default_fieldheight=int(self.resolution_height/nr_of_rows)

            normal_fieldwidth=default_fieldwidth
            normal_fieldheight=default_fieldheight

            currentrow=1
            currentwindow=1
            currentrowlength=nr_of_columns

            x1=0
            y1=0
            x2=normal_fieldwidth
            y2=normal_fieldheight

            for cam_stream in self.cam_streams_to_draw:

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

                if currentwindow == fields:
                    #Start calculation to display placeholders
                    free_horizontal_pixels = self.resolution_width - x2
                    #If we have some unused screen space. Start drawing placeholders to fill the free space
                    if free_horizontal_pixels > 0:
                        logger.debug("Screen: We have " + str(free_horizontal_pixels) + " free_horizontal_pixels unused screen. Start drawing placeholders to fill the free space")
                        nr_of_placeholders=free_horizontal_pixels/normal_fieldwidth
                        count_placeholders = 0
                        placeholder_x = x1 + normal_fieldwidth
                        placeholder_y = y1
                        while count_placeholders < nr_of_placeholders:
                            self.drawinstance.placeholder(placeholder_x, placeholder_y, normal_fieldwidth, normal_fieldheight, "images/placeholder.png")
                            count_placeholders = count_placeholders + 1
                            placeholder_x = placeholder_x + normal_fieldwidth

                logger.debug("Screen: cam stream name =" + cam_stream.name)
                cam_stream_name = "cam_stream" + str(currentwindow)
                # x1 #x coordinate upper left corner
                # y1 #y coordinate upper left corner
                # x2 #x coordinate absolute where window should end, count from left to right
                # y2 #y coordinate from where window should end, count from top to bottom of screen
                cam_stream.start_stream([x1,y1,x2,y2], self.layer)
                #Debug test
                #cam_stream.set_videopos([x1 + 50 ,y1 +50 ,x2 +50 ,y2 +50])

                currentwindow = currentwindow + 1
        else:
            logger.debug("Screen: Connectable camera streams stayed the same, from " + str(
                len(self.previous_connectable_camera_streams)) + " to " + str(
                len(self.connectable_camera_streams)) + ", screen: " + self.name + " does not need full redraw")

        self.previous_connectable_camera_streams = self.connectable_camera_streams

        #refresh all placeholders that were created on the screen itself.
        #If there are imageurls then now is the time to refresh them all
        for cam_stream in self.cam_streams_to_draw:
            cam_stream.refresh_image_from_url()

        self.drawinstance.refresh()

