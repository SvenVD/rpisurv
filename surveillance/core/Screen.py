import logging
import math
import time
import collections

from .Stream import Stream

#We do not need exact floating point numbers, use builtin "float" instead
#from decimal import getcontext, Decimals


logger = logging.getLogger('l_default')

class Screen:
    """This class creates and handles camerastreams objects and their position"""
    def __init__(self, screenname, screen_cfg, monitor, background_drawinstance):
        ## Init vars
        self.xdisplay_id = monitor["xdisplay_id"]
        self.monitor_number = monitor["monitor_number"]
        #Offsets for when on extended monitor
        self.monitor_x_offset = monitor["x_offset"]
        self.monitor_y_offset = monitor["y_offset"]
        #Screens by default start hidden
        self.hidden_state = True
        self.disable_probing_for_all_streams = screen_cfg.setdefault('disable_probing_for_all_streams', False)
        self.nr_of_columns = screen_cfg.setdefault('nr_of_columns', 2)
        self.name = screenname
        self.screen_cfg = screen_cfg
        self.streams_cfg = screen_cfg["streams"]
        self.duration = self.screen_cfg.setdefault('duration', 30)
        logger.debug("Screen: " + self.name + " duration from config is: " + str(self.duration))
        self.background_drawinstance = background_drawinstance
        self.first_run = True
        self.start_of_active_time = -1
        self.previous_connectable_streams = []
        self.placeholders_metadata = []

        ## Init functions
        # Sets internal variable resolution
        self.resolution_width = int(monitor["resolution"]["width"])
        self.resolution_height = int(monitor["resolution"]["height"])
        self._init_streams()


    def has_image_url(self):
        """Returns True if this screen has at least one stream that is an imageurl"""

        for stream in self.all_streams:
            if stream.is_imageurl():
                logger.debug(
                    "Screen: " + self.name + " has_image_url: detected at least one imageurl: " + stream.name )
                return True
        return False

    def _init_streams(self):
        '''Instantiate camera instances and put them in a list'''
        self.all_streams = []
        counter = 0
        for stream in self.streams_cfg:
            counter = counter + 1
            stream_name = self.name + "_stream" + str(counter)
            stream = Stream(stream_name, stream, self.background_drawinstance, self.xdisplay_id, self.monitor_number ,self.monitor_x_offset,self.monitor_y_offset)
            self.all_streams.append(stream)


    def update_connectable_streams(self, skip = False):
        '''Filters a list of camerastream instances into a new list of connectable streams'''
        if skip:
            logger.debug("Screen: " + self.name + " Skipping checking connectable cameras, skip value is: " + str(skip))
            # Sometimes we do not want to wait on checking connectable camera streams, so this shortcut is taken (essentially skip checking)
            if self.first_run:
                # We need the camera stream to be initialised with something in the beginning if we decide to skip the checking of connectivity
                logger.debug("Screen: " + self.name + " first run")
                self.connectable_streams = self.all_streams
                self.first_run = False
            else:
                self.connectable_streams = self.previous_connectable_streams
        else:
            logger.debug("Screen: Start polling connectivity for the streams part of screen: " + self.name)
            self.connectable_streams=[]
            for stream in self.all_streams:
                    if stream.is_connectable():
                        self.connectable_streams.append(stream)

        self.streams_to_draw = self.connectable_streams
        self.streams_to_stop = self.previous_connectable_streams

    def run_screen_watchdogs(self):
        logger.debug(f"Screen: {self.name}: run_screen_watchdogs")
        for stream in self.connectable_streams:
            stream.run_stream_watchdog()

    def hide_all_streams(self):
        logger.debug(f"Screen: {self.name}: hide_all_streams")
        for stream in self.connectable_streams:
            stream.hide()
        self.hidden_state= True

    def unhide_all_streams(self):
        logger.debug(f"Screen: {self.name}: unhide_all_streams")
        for stream in self.connectable_streams:
            stream.unhide()
        self.hidden_state = False
        self.draw_all_placeholders()
    def draw_all_placeholders(self):
        logger.debug(f"Screen: {self.name}: draw_all_placeholders")
        for i in self.placeholders_metadata:
            self.background_drawinstance.placeholder(i['absposx'], i['absposy'], i['width'],i['height'],i['background_img_path'])
        self.background_drawinstance.refresh()

    def destroy(self):
        logger.debug(f"Screen: { self.name }: Destroying screen")

        for stream_to_stop in self.previous_connectable_streams:
            stream_to_stop.stop_stream()

        # Reset vars for next iteration of this screen, object stays in memory
        self.previous_connectable_streams = []
        self.first_run = True
        self.start_of_active_time = -1
    def reset_active_timer(self):
        logger.debug(f"Screen: { self.name }: reset_active_timer")
        #Set start time
        self.start_of_active_time = time.time()
        logger.debug(f"Screen: { self.name }: start_of_active_time: {str(self.start_of_active_time)}")

    def get_active_run_time(self):
        '''Returns how long the screen is in active mode'''
        active_run_time = int(round((time.time() - self.start_of_active_time)))
        logger.debug("Screen: " + self.name + " active_run_time: " + str(active_run_time) + " / " + str(self.duration))
        return active_run_time

    def _is_connectable_streams_changed(self):
        """Returns True if previous_connectable_streams list has different items from connectable_streams regardless of order"""
        #logger.debug(f"connectable_streams {collections.Counter(self.connectable_streams)} previous_connectable_streams {collections.Counter(self.previous_connectable_streams)}")
        if collections.Counter(self.connectable_streams) == collections.Counter(self.previous_connectable_streams):
            return False
        else:
            return True

    def update_screen(self):
        # Other option to compare could be with to convert the list into a set: print set(connectable_streams) == set(previous_connectable_streams)
        # Only re-draw screen if something is changed or try redrawing if there is no camerastream that is connectable OR if we change the screen
        if self._is_connectable_streams_changed() or len(self.previous_connectable_streams) == 0:
            logger.debug(f"Screen: {self.name}: needs update/redraw: changes in connectable camera streams detected.( previous: {len(self.previous_connectable_streams)} / now: {len(self.connectable_streams)} or different connectable streams then before )")
            #Resetting all placeholders since they can be different after calculation
            self.placeholders_metadata = []

            #Stop all running streams before redrawing
            for stream_to_stop in self.streams_to_stop:
                stream_to_stop.stop_stream()

            #Remove all that was drawn on background screen as we need to update it
            if not self.hidden_state:
                self.background_drawinstance.blank()

            nr_of_columns=int(self.nr_of_columns)

            # Start algorithm to start new streams
            fields = len(self.streams_to_draw)
            logger.debug( "Screen: " + self.name + " number of fields= " + str(fields))

            if fields == 0:
                if not self.hidden_state:
                    #Draw no connectable placeholder but only is screen is not hidden
                    self.background_drawinstance.placeholder(0, 0, self.resolution_width, self.resolution_height, "images/noconnectable.png")
                    self.previous_connectable_streams = self.connectable_streams
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

            for stream in self.streams_to_draw:

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
                        logger.debug("Screen: We have " + str(free_horizontal_pixels) + " free_horizontal_pixels unused screen. Start calculating placeholders to fill the free space")
                        nr_of_placeholders=free_horizontal_pixels/normal_fieldwidth
                        count_placeholders = 0
                        placeholder_x = x1 + normal_fieldwidth
                        placeholder_y = y1
                        while count_placeholders < nr_of_placeholders:
                            self.placeholders_metadata.append({
                                "absposx": placeholder_x,
                                "absposy": placeholder_y,
                                "width": normal_fieldwidth,
                                "height": normal_fieldheight,
                                "background_img_path": "images/placeholder.png"
                            })
                            count_placeholders = count_placeholders + 1
                            placeholder_x = placeholder_x + normal_fieldwidth


                # x1 #x coordinate upper left corner
                # y1 #y coordinate upper left corner
                # x2 #x coordinate absolute where window should end, count from left to right
                # y2 #y coordinate from where window should end, count from top to bottom of screen
                #Stop any existing stream before starting new one
                logger.debug(f"Screen: {self.name} Stop {stream.name}")
                stream.stop_stream()
                logger.debug(f"Screen: {self.name} Starting {stream.name}" )
                stream.start_stream([x1,y1,x2,y2], self.hidden_state)
                if not self.hidden_state:
                    self.draw_all_placeholders()
                currentwindow = currentwindow + 1
        else:
            logger.debug("Screen:" + self.name + ": Connectable camera streams stayed the same, from " + str(
                len(self.previous_connectable_streams)) + " to " + str(
                len(self.connectable_streams)) + ", screen: " + self.name + " does not need full redraw")

        self.previous_connectable_streams = self.connectable_streams

