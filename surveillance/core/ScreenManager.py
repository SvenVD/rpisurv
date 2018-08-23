import logging

from Screen import Screen
import util.draw as draw

logger = logging.getLogger('l_default')

class ScreenManager:
    """This class creates and handles screens objects  and rotation"""
    def __init__(self,screen_manager_name,resolution,screens_cfg,fixed_width_per_screen, fixed_height_per_screen, cache_next_screen):
        self.name = screen_manager_name
        self.resolution = resolution
        self.screens_cfg=screens_cfg
        self.fixed_width_per_screen=fixed_width_per_screen
        self.fixed_height_per_screen=fixed_height_per_screen
        self.firstrun = True
        self.activeindex = 0
        self.cache_next_screen = cache_next_screen
        self.futurecacheindex = 1
        self.currentcacheindex = -1

        self._init_pygame()
        self._init_screens()


    def _create_cached_screen(self):

        logger.debug("ScreenManager: _create_cached_screen with index " + str(self.futurecacheindex) + " updating screen: " + self.all_screens[self.futurecacheindex].name + " in cache")
        #Check what streams are connectable for the cached screens and update this cached screens instance with the information
        if self.get_future_cached_screen_disable_probing_for_all_streams():
            #Do not check for connectable cameras when disable_probing_for_all_streams is set to true, just try to draw all of them, and fail for the ones that are not connectable
            self.all_screens[self.futurecacheindex].update_connectable_camera_streams(skip=True)
        else:
            self.all_screens[self.futurecacheindex].update_connectable_camera_streams(skip=False)


        if self.cache_next_screen:
            #Update the screen for a cached screen means: start all omxplayer instances for this screen in offscreen
            #If self.cache_next_screen is False then the _create_cached_screen does not really create a cached screen, it only updates internal counters
            self.all_screens[self.futurecacheindex].update_screen()
        else:
            logger.debug("ScreenManager: not starting omxplayer instances offscreen for screen " + self.all_screens[self.futurecacheindex].name + " since cache_next_screen option was set to False")

        self.currentcacheindex = self.futurecacheindex
        self.futurecacheindex = self.futurecacheindex + 1
        if self.futurecacheindex > self.max_index:
            logger.debug("ScreenManager: futurecacheindex (" + str(self.futurecacheindex) + ") >= (" + str(
                self.max_index) + "), resetting futurecacheindex ")
            self.futurecacheindex = 0

    def get_active_screen_run_time(self):
        return self.all_screens[self.activeindex].get_active_run_time()

    def get_active_screen_duration(self):
        return self.all_screens[self.activeindex].duration

    def get_active_screen_disable_probing_for_all_streams(self):
        return self.all_screens[self.activeindex].disable_probing_for_all_streams

    def get_future_cached_screen_disable_probing_for_all_streams(self):
        return self.all_screens[self.futurecacheindex].disable_probing_for_all_streams

    def force_show_screen(self, requested_index):
        '''this method force a particular screen to be shown on-screen'''
        logger.debug("ScreenManager:  activeindex = " + str(self.activeindex) + ", futurecacheindex = " + str(self.futurecacheindex))
        if requested_index > self.max_index:
            #Note name of screens start with 1 but list of screens index start at 0
            logger.debug("ScreenManager:  Force screen" + str(requested_index + 1) + " requested, but this screen does not exist")
        elif requested_index == self.activeindex:
            #Note name of screens start with 1 but list of screens index start at 0
            logger.debug("ScreenManager:  Force screen" + str(requested_index + 1) + " requested, but this screen is already active")
        elif requested_index == self.currentcacheindex:
            #Note name of screens start with 1 but list of screens index start at 0
            logger.debug("ScreenManager:  Force screen" + str(requested_index + 1) + " requested, this screen is already in cache, do a normal rotate")
            self.rotate_next()
        else:
            #Note name of screens start with 1 but list of screens index start at 0
            logger.debug("ScreenManager:  Force screen" + str(requested_index + 1) + " requested")

            #Destroy current active and cached screens
            self.all_screens[self.activeindex].destroy()
            self.all_screens[self.currentcacheindex].destroy()

            #Show new requested screen
            self.activeindex = requested_index
            self.all_screens[requested_index].make_active()
            #For faster drawing skip probing(we are optimistic and assume all screens are connectable)
            self.all_screens[requested_index].update_connectable_camera_streams(skip=True)
            self.all_screens[requested_index].update_screen()

            #Cache a new screen for next normal rotation.
            self.futurecacheindex = requested_index + 1
            if self.futurecacheindex > self.max_index:
                logger.debug("ScreenManager: force screen futurecacheindex (" + str(self.futurecacheindex) + ") >= (" + str(
                    self.max_index) + "), resetting futurecacheindex ")
                self.futurecacheindex = 0
            self._create_cached_screen()

    def rotate_next(self):
        ''' this methods contains logic to move the cached screen on screen, destroy the current screen and to make a new cached screen'''

        if self.max_index == 0:
            logger.debug("ScreenManager: only one screen configured, do not rotate")
            #Screen are default started in cache/offscreen, make_active to show onscreen
            self.all_screens[self.activeindex].make_active()
            return

        logger.debug("ScreenManager: rotate event, indexes BEFORE rotate: futurecacheindex: " + str(self.futurecacheindex) + " activeindex: " + str(self.activeindex) + " max index is " + str(self.max_index))
        #Delete current active screen
        if self.firstrun:
            #During firstrun we need to start an active screen and a cached/offscreen screen
            logger.debug("ScreenManager: starting first run active screen " + self.all_screens[self.activeindex].name)
            self.all_screens[self.activeindex].make_active()
            self._create_cached_screen()
            self.firstrun = False

        else:
            #During normal rotate event we need to do 3 things
            #- Destroy the current screen
            #- Swap the currently cached offscreen screen to onscreen
            #- Start a new cached offscreen screen
            logger.debug("ScreenManager: destroying previous screen " + self.all_screens[self.activeindex].name)
            self.all_screens[self.activeindex].destroy()
            #Now it's time to display the cached screen
            logger.debug("ScreenManager: make cached screen: " + self.all_screens[ self.currentcacheindex].name + " active")
            self.all_screens[self.currentcacheindex].make_active()
            self.all_screens[self.currentcacheindex].update_screen()

            self.activeindex = self.currentcacheindex

            #We also need to create a new cache for the next rotate
            self._create_cached_screen()

            logger.debug("ScreenManager: rotate event, indexes AFTER rotate: futurecacheindex: " + str(self.futurecacheindex) + " activeindex: " + str(self.activeindex) + " max index is " + str(self.max_index))


    def _init_screens(self):
        '''This method initiates all screen instances'''
        counter = 1
        self.all_screens=[]
        # -1 because list start at zero
        self.max_index = len(self.screens_cfg) - 1
        for screen_cfg in self.screens_cfg:
            logger.debug("ScreenManager: Initialising screen with config " + str(screen_cfg))
            self.all_screens.append(Screen("screen" + str(counter), screen_cfg, self.resolution, self.pygamescreen, self.fixed_width_per_screen, self.fixed_height_per_screen))
            counter = counter + 1

        #Show a connecting screen on first run, so that in case of many streams = long initial startup, the user knows what is happening.
        draw.placeholder(0, 0, int(self.resolution[0]), int(self.resolution[1]), "images/connecting.png", self.pygamescreen)
        draw.refresh()


    def update_active_screen(self,skip_update_connectable_camera = False):
        '''To be used in main loop and is used to update connectable and unconnectable camera streams on the current displayed screen'''
        logger.debug("ScreenManager: update_active_screen " + self.all_screens[self.activeindex].name)
        if self.get_active_screen_disable_probing_for_all_streams():
            #disable_probing_for_all_streams has been requested, skip all smart logic
            self.all_screens[self.activeindex].update_connectable_camera_streams(skip=True)
            logger.debug("ScreenManager: SKIPPING update_connectable_camera_streams, because disable_probing_for_all_streams for this screen " + self.all_screens[self.activeindex].name + " was set")
        else:
            self.all_screens[self.activeindex].update_connectable_camera_streams(skip=False)
            logger.debug("ScreenManager:  update_connectable_camera_streams, disable_probing_for_all_streams is off for this screen, so using probes " + self.all_screens[self.activeindex].name)

        self.all_screens[self.activeindex].update_screen()

    def _init_pygame(self):
        self.pygamescreen = draw.init(self.resolution)

    def destroy(self):
        logger.debug("ScreenManager: THIS IS THE END, DESTROYING screenmanager: " + self.name)
        for screen in self.all_screens:
            screen.destroy()
        draw.destroy()
