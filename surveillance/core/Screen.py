import logging
import math
import time

from CameraStream import CameraStream
import util.draw as draw

#We do not need exact floating point numbers, use builtin "float" instead
#from decimal import getcontext, Decimals


logger = logging.getLogger('l_default')

class Screen:
    """This class creates and handles camerastreams objects and their position"""
    def __init__(self, screenname, screen_cfg, resolution, pygamescreen, fixed_width, fixed_height):
        ## Init vars
        self.disable_probing_for_all_streams = screen_cfg.setdefault('disable_probing_for_all_streams', False)
        self.nr_of_columns = screen_cfg.setdefault('nr_of_columns', 2)
        self.autostretch = screen_cfg.setdefault('autostretch', False)
        self.name = screenname
        self.screen_cfg = screen_cfg
        self.camera_streams_cfg = screen_cfg["camera_streams"]
        self.duration = self.screen_cfg.setdefault('duration', 30)
        logger.debug("Screen: " + self.name + " duration from config is: " + str(self.duration))
        self.resolution = resolution
        self.pygamescreen = pygamescreen
        self.fixed_width = fixed_width
        self.fixed_height = fixed_height
        self.first_run = True
        self.start_of_active_time = -1
        self.previous_connectable_camera_streams = []
        #Init these two the same otherwise, code will detect a cache event on first run of the screen
        self.previous_cached = True
        self.cached = True
        if self.cached:
            logger.debug("Screen: This screen: " + self.name + " will be started in cache")
        else:
            logger.debug("Screen: This screen: " + self.name + " will not be started in cache")


        ## Init functions
        # Sets internal variable resolution
        self.resolution_width = int(self.resolution[0])
        self.resolution_height = int(self.resolution[1])
        self._init_camera_streams()

    def _init_camera_streams(self):
        '''Instantiate camera instances and put them in a list'''
        self.all_camera_streams = []
        counter = 0
        for camera_stream in self.camera_streams_cfg:
            counter = counter + 1
            cam_stream_name = self.name + "_cam_stream" + str(counter)
            cam_stream = CameraStream(cam_stream_name, camera_stream)
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

        self.destroy_all_placeholder()
        for cam_stream_to_stop in self.previous_connectable_camera_streams:
            cam_stream_to_stop.stop_stream()

        # Reset vars for next iteration of this screen, object stays in memory
        self.previous_connectable_camera_streams = []
        # Init these two the same otherwise, code will detect a cache event on first run of the screen
        self.previous_cached = True
        self.cached = True
        self.first_run = True
        self.start_of_active_time = -1

    def destroy_all_placeholder(self):
        # TODO This can be done more elegant if we collect all placeholders when they are drawn to a list and then kill each of them individually here?
        # Instead of drawing over them
        if not self.cached:
            draw.blank_screen(0, 0, self.resolution_width, self.resolution_height, self.pygamescreen)
            draw.refresh()

    def make_active(self):
        logger.debug("Screen: Make screen " + self.name + " active")
        #Set start time
        self.start_of_active_time = time.time()
        logger.debug("Screen: " + self.name + " start_of_active_time: " + str(self.start_of_active_time))
        self.cached = False

    def get_active_run_time(self):
        '''Returns -1 if cached and how long the screen is in active mode if not cached'''
        if not self.cached:
            active_run_time = long(round((time.time() - self.start_of_active_time)))
        else:
            active_run_time = -1
        logger.debug("Screen: " + self.name + " active_run_time: " + str(active_run_time) + " / " + str(self.duration))
        return active_run_time

    def update_screen(self):

        # Other option to compare could be with to convert the list into a set: print set(connectable_camera_streams) == set(previous_connectable_camera_streams)
        # Only re-draw screen if something is changed or try redrawing if there is no camerastream that is connectable OR if we change the screen from cached to not cached or vice versa
        if cmp(self.connectable_camera_streams, self.previous_connectable_camera_streams) != 0 or len(self.previous_connectable_camera_streams) == 0 or self.previous_cached != self.cached:
            logger.debug("Screen: " + self.name + " Connectable camera streams changed from " + str(len(self.previous_connectable_camera_streams)) + " to " + str(len(self.connectable_camera_streams)) + " or we change from previous_cached value: " + str(self.previous_cached) + " to current cached value: " + str(self.cached) + ", screen: " + self.name + " needs update/redraw")

            #Stop all running streams only when some streams are not connectable
            if cmp(self.connectable_camera_streams, self.previous_connectable_camera_streams) != 0 or len( self.previous_connectable_camera_streams) == 0:
                for cam_stream_to_stop in self.cam_streams_to_stop:
                    cam_stream_to_stop.stop_stream()


            nr_of_columns=int(self.nr_of_columns)

            # Start algorithm to start new streams
            fields = len(self.cam_streams_to_draw)
            logger.debug( "Screen: " + self.name + " number of fields= " + str(fields))

            if fields == 0:
                if not self.cached:
                    #Draw no connectable placeholder
                    draw.placeholder(0, 0, self.resolution_width, self.resolution_height, "images/noconnectable.png", self.pygamescreen)
                    self.previous_connectable_camera_streams = self.connectable_camera_streams
                    self.previous_cached = self.cached
                return
            else:
                # Only destroy all placeholders when fields are not 0, this to prevent showing black screen flapping when noconnectable is shown fullscreen
                self.destroy_all_placeholder()


            #If you have less fields than columns then only set fields amount columns
            if fields <= nr_of_columns:
                nr_of_columns=fields

            #We calculate needed numbers of rows based on how many fields we have and how many columns per row we want
            nr_of_rows=math.ceil(float(fields)/nr_of_columns)

            default_fieldwidth=self.resolution_width/nr_of_columns
            default_fieldheight=int(self.resolution_height/nr_of_rows)

            normal_fieldwidth=default_fieldwidth
            normal_fieldheight=default_fieldheight

            if self.fixed_width is not None:
                total_actual_width=  nr_of_columns * self.fixed_width
                if not total_actual_width > self.resolution_width:
                    normal_fieldwidth=self.fixed_width
                    logger.debug("Screen: Detected advanced fixed_width config option, setting normal_fieldwidth to " + str(normal_fieldwidth))
                else:
                    logger.error("Screen: Total sum of advanced fixed_width (nr_columns * fixed_width) option (" + str(total_actual_width) + ") is more then available width (" + str(self.resolution_width) + "), falling back to autocalculated width: " + str(normal_fieldwidth))


            if self.fixed_height is not None:
               total_actual_height=  nr_of_rows * self.fixed_height
               if not total_actual_height > self.resolution_height:
                   normal_fieldheight=self.fixed_height
                   logger.debug("Screen: Detected advanced fixed_height config option, setting normal_fieldheight to " + str(normal_fieldheight))
               else:
                   logger.error("Screen: Total sum of advanced fixed_height (nr rows * fixed_height) option (" + str(total_actual_height) + ") is more then available height (" + str(self.resolution_height) + "), falling back to autocalculated height: " + str(normal_fieldheight))

            currentrow=1
            currentwindow=1
            currentrowlength=nr_of_columns

            if self.cached:
                #cached means, warm the camerastreams offscreen, so they can be swapped onscreen when rotate is called
                offset = self.resolution_width
                logger.debug("Screen: This screen: " + self.name + " is updated in cache with offset:" + str(offset))
            else:
                offset = 0

            x1=0 + offset
            y1=0
            x2=normal_fieldwidth + offset
            y2=normal_fieldheight

            for cam_stream in self.cam_streams_to_draw:

                if currentwindow > currentrowlength:
                    #This is a new row event
                    x1=0 + offset
                    x2=normal_fieldwidth + offset
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
                    x1=0 + offset
                    x2=normal_fieldwidth + offset

                #If this is the last field and we still have some screen space left, horizontally stretch it to use all space
                if currentwindow == fields:
                    if self.fixed_width is None and self.autostretch is True:
                        #Sometimes this will override to the same value if the window end was already at the end of the screen
                        #Other times it will really override to the end of the screen
                        x2= self.resolution_width + offset
                    else:
                        #Start calculation to display placeholders
                        free_horizontal_pixels = self.resolution_width - x2
                        #If we have some unused screen space and this Screen is not a cached screen then start drawing placeholders
                        if free_horizontal_pixels > 0 and not self.cached:
                            logger.debug("Screen: We have " + str(free_horizontal_pixels) + " free_horizontal_pixels unused screen and autostretch is disabled. Start drawing placeholders")
                            nr_of_placeholders=free_horizontal_pixels/normal_fieldwidth
                            count_placeholders = 0
                            placeholder_x = x1 + normal_fieldwidth
                            placeholder_y = y1
                            while count_placeholders < nr_of_placeholders:
                                draw.placeholder(placeholder_x, placeholder_y, normal_fieldwidth, normal_fieldheight, "images/placeholder.png", self.pygamescreen)
                                count_placeholders = count_placeholders + 1
                                placeholder_x = placeholder_x + normal_fieldwidth

                logger.debug("Screen: cam stream name =" + cam_stream.name)
                cam_stream_name = "cam_stream" + str(currentwindow)
                # x1 #x coordinate upper left corner
                # y1 #y coordinate upper left corner
                # x2 #x coordinate absolute where window should end, count from left to right
                # y2 #y coordinate from where window should end, count from top to bottom of screen
                cam_stream.start_stream([x1,y1,x2,y2], self.pygamescreen, self.cached)
                #Debug test
                #cam_stream.set_videopos([x1 + 50 ,y1 +50 ,x2 +50 ,y2 +50])
                cam_stream.printcoordinates()

                currentwindow = currentwindow + 1
        else:
            logger.debug("Screen: Connectable camera streams stayed the same, from " + str(
                len(self.previous_connectable_camera_streams)) + " to " + str(
                len(self.connectable_camera_streams)) + ", screen: " + self.name + " does not need full redraw")

        self.previous_connectable_camera_streams = self.connectable_camera_streams
        self.previous_cached = self.cached

        #refresh all placeholders that were created on the screen itself, but do not do this if we are running in cache
        if not self.cached:
            #If there are imageurls then now is the time to refresh them all
            for cam_stream in self.cam_streams_to_draw:
                cam_stream.refresh_image_from_url()
            draw.refresh()

