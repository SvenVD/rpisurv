import logging
import yaml
from vcgencmd import Vcgencmd
from .Screen import Screen
from core.util.draw import Draw



logger = logging.getLogger('l_default')

class ScreenManager:
    """This class creates and handles screens objects and rotation"""
    def __init__(self,screen_manager_name, display, enable_opportunistic_caching_next_screen, disable_pygame):
        self.name = screen_manager_name
        self.want_to_be_destroyed = False
        self.firstrun = True
        self.display = display
        self.activeindex = 0
        self.disable_pygame = disable_pygame
        self._init_drawinstance()
        self._fetch_display_config()

        if self.disable_pygame:
            # Since pygame is disabled we need something else to hide console and other background noise, use pngview for this
            self.drawinstance.insert_black_background(int(self.display["resolution"]["width"]), int(self.display["resolution"]["height"]),self.display["display_number"])

        self.enable_opportunistic_caching_next_screen = enable_opportunistic_caching_next_screen

        self.futurecacheindex = 1
        self.currentcacheindex = -1


        self._init_screens()    
    

    def _fetch_display_config(self):
        configpath=f"conf/display{int(self.display['hdmi']) + 1 }.yml"
        logger.debug(f"{self.name}: Looking for config file {configpath}")
        with open(configpath, 'r') as ymlfile:
            cfg = yaml.load(ymlfile)
            self.screens_cfg=cfg['essentials']['screens']
            self.disable_autorotation = cfg['essentials'].setdefault('disable_autorotation', False)

    def _create_cached_screen(self):

        #Remove any previous black layer, if any. _create_cached_screen is called in any scenario even when no real cache needs to be drawn
        self.drawinstance.kill_black_layer()

        #We need to draw the cached screen behind the current active screen, but we need to leave extra free layers between the cached screen and the current active screen
        # - one layer is needed for a black background so that the cached screen is hidden at all times
        # - another layer is needed for caching "showontop" streams, these need to go behind the black background but before the normal cached screens
        #Summary layers (optional) "showontop" stream > normal active streams > pngview black screen > (optional) "showontop" cached streams > normal cached streams
        self.futurelayer=self.all_screens[self.activeindex].get_layer() - 3
        self.all_screens[self.futurecacheindex].set_layer(self.futurelayer)

        self.skip_cache_once = False
        self.lowerthreshold_layer = 2000
        #We may not go in the lower layers since that is where pygame and the console buffer resides
        #If we go to low the latter will be drawn over our videos
        if self.all_screens[self.futurecacheindex].get_layer() < self.lowerthreshold_layer:
            logger.debug(f"{self.name}: skip caching next screen: {self.all_screens[self.futurecacheindex].name} once, because we need to reset the layer counter")
            self.all_screens[self.futurecacheindex].reset_layer()
            # We need to skip caching once when resetting the counter, otherwise the future screen thats needs to be cached will be shown over the activescreen
            self.skip_cache_once = True

        if self.all_screens[self.activeindex].has_image_url():
            #TL;DR: If the CURRENT ACTIVE screen has imageurl then do not cache next screen as the next screen is not guaranteed to have gaps where the imageurl should be displayed
            #   The current and the next screen video camerastreams positions are always drawn on layers above the pygame layer.
            #   For the active screen this is no problem as it knows where to leaves gaps. Through these gaps we can view the lower pygame layer (where the image urls are displayed).
            #   However, if the next screen (cached) is drawn on a gap of the current screen then we can not peak through to the lowest layers where pygame lives anymore
            #   Note that we can not make this more dynamic by explicitely checking for connectable image url, because then a screen starting with imageurl that will become connected later during the same run
            #   can not be displayed because the cached screen was already drawn on top of the pygame layer
            logger.info(
                f"{self.name}: skip caching next screen: {self.all_screens[self.futurecacheindex].name} (pygame, used to display image, is not compatible with dispmanx layers caching mechanism)")
            self.skip_cache_once = True

        # Check what streams are connectable for the next screen and update this next screens= instance with the information
        if self.get_future_cached_screen_disable_probing_for_all_streams():
            # Do not check for connectable cameras when disable_probing_for_all_streams is set to true, just try to draw all of them, and hard fail for the ones that are not connectable
            self.all_screens[self.futurecacheindex].update_connectable_camera_streams(skip=True)
        else:
            self.all_screens[self.futurecacheindex].update_connectable_camera_streams(skip=False)


        if self.enable_opportunistic_caching_next_screen and not self.skip_cache_once:
            logger.debug(
                f"{self.name}: _create_cached_screen with index {self.futurecacheindex} updating screen: {self.all_screens[self.futurecacheindex].name} in cache")

            #Insert black screen on top of cached layer, so that it does not bleed through in some cases (like when active screen is still building up or on redrawing active screen)
            #We can not use pygame for this, like we do when caching is disabled, since pygame will always draw on the same low layer and will thus be drawn over by both the active and the cached screen
            #We do not insert a black screen if there is no cache needed
            self.drawinstance.insert_black_layer(int(self.display["resolution"]["width"]), int(self.display["resolution"]["height"]),
                                    str(self.all_screens[self.futurecacheindex].get_layer() + 2), self.display["display_number"])

            #Update the screen for a cached screen means: start all cvlc instances for this screen in the background
            self.all_screens[self.futurecacheindex].update_screen()
        else:
            #If self.enable_opportunistic_caching_next_screen is False then the _create_cached_screen does not really create a cached screen, it only updates internal counters
            logger.debug(f"{self.name}: Skip caching screen {self.all_screens[self.futurecacheindex].name} because of parameters enable_opportunistic_caching_next_screen: {self.enable_opportunistic_caching_next_screen} / skip_cache_once: {self.skip_cache_once}")

        self.currentcacheindex = self.futurecacheindex
        self.futurecacheindex = self.futurecacheindex + 1
        if self.futurecacheindex > self.max_index:
            logger.debug(f"{self.name}: futurecacheindex ({self.futurecacheindex} >= {self.max_index}), resetting futurecacheindex")
            self.futurecacheindex = 0

    def get_active_screen_run_time(self):
        return self.all_screens[self.activeindex].get_active_run_time()

    def turn_screen_on_off(self):
        vcgm = Vcgencmd()
        current_state = vcgm.display_power_state(2)
        if current_state == 'on':
            vcgm.display_power_off(2)
        else:
            vcgm.display_power_on(2)   
    
    def get_active_screen_duration(self):
        return self.all_screens[self.activeindex].duration

    def get_active_screen_disable_probing_for_all_streams(self):
        return self.all_screens[self.activeindex].disable_probing_for_all_streams

    def get_future_cached_screen_disable_probing_for_all_streams(self):
        return self.all_screens[self.futurecacheindex].disable_probing_for_all_streams

    def force_show_screen(self, requested_index):
        '''this method force a particular screen to be shown on-screen'''
        logger.debug(f"{self.name}: activeindex = {self.activeindex}, futurecacheindex = {self.futurecacheindex}")
        if requested_index > self.max_index:
            #Note name of screens start with 1 but list of screens index start at 0
            logger.debug(f"{self.name}: Force screen {requested_index + 1} requested, but this screen does not exist")
        elif requested_index == self.activeindex:
            #Note name of screens start with 1 but list of screens index start at 0
            logger.debug(f"{self.name}: Force screen {requested_index + 1} requested, but this screen is already active")
        elif requested_index == self.currentcacheindex:
            #Note name of screens start with 1 but list of screens index start at 0
            logger.debug(f"{self.name}: Force screen {requested_index + 1} requested, this screen is already in cache, do a normal rotate")
            self.rotate_next()
        else:
            #Note name of screens start with 1 but list of screens index start at 0
            logger.debug(f"{self.name}: Force screen {requested_index + 1} requested")

            #Destroy current active and cached screens
            self.all_screens[self.activeindex].destroy()
            self.all_screens[self.currentcacheindex].destroy()

            #Show new requested screen
            self.activeindex = requested_index
            self.all_screens[requested_index].reset_active_timer()
            #For faster drawing skip probing(we are optimistic and assume all screens are connectable)
            self.all_screens[requested_index].update_connectable_camera_streams(skip=True)
            self.all_screens[requested_index].update_screen()

            #Cache a new screen for next normal rotation.
            self.futurecacheindex = requested_index + 1
            if self.futurecacheindex > self.max_index:
                logger.debug(f"{self.name} force screen futurecacheindex ({self.futurecacheindex} >= {self.max_index}), resetting futurecacheindex ")
                self.futurecacheindex = 0
            self._create_cached_screen()

    def rotate_next(self):
        ''' this methods contains logic destroy the current screen so that the next screen which was started behind it is shown'''

        if self.max_index == 0:
            logger.debug(f"{self.name}: only one screen configured, do not rotate")
            #Screen are default started in cache/offscreen, reset_active_timer to show onscreen
            self.all_screens[self.activeindex].reset_active_timer()
            return

        logger.debug(f"{self.name}: rotate event, indexes BEFORE rotate: futurecacheindex: {self.futurecacheindex} activeindex: {self.activeindex} max index is {self.max_index}")
        #Delete current active screen
        if self.firstrun:
            #During firstrun we need to start an active screen and the next screen hidden on a layer lower then the active screen
            #We do this, so that on a rotate event the next screen can be shown without delay as all streams are already connected
            logger.debug(f"{self.name} starting first run active screen {self.all_screens[self.activeindex].name}")
            self.all_screens[self.activeindex].reset_active_timer()
            self._create_cached_screen()
            self.firstrun = False

        else:
            #During normal rotate event we need to do 3 things
            #- Destroy the current screen (cached screen in lower layer (if any) becomes visible)
            #- Start a new cached offscreen screen
            logger.debug(f"{self.name}: destroying previous screen {self.all_screens[self.activeindex].name}")
            self.all_screens[self.activeindex].destroy()
            #Now the cached screen should already be displayed because the active on top was destroyed
            logger.debug(f"{self.name}: next screen: {self.all_screens[ self.currentcacheindex].name} active")
            self.all_screens[self.currentcacheindex].reset_active_timer()
            self.all_screens[self.currentcacheindex].update_screen()

            self.activeindex = self.currentcacheindex

            #We also need to create a new cache for the next rotate
            self._create_cached_screen()

            logger.debug(f"{self.name}: rotate event, indexes AFTER rotate: futurecacheindex: {self.futurecacheindex} activeindex: {self.activeindex} max index is {self.max_index}")


    def _init_screens(self):
        '''This method initiates all screen instances'''
        counter = 1
        self.all_screens=[]
        # -1 because list start at zero
        self.max_index = len(self.screens_cfg) - 1
        for screen_cfg in self.screens_cfg:
            logger.debug(f"{self.name}: Initialising screen with config {screen_cfg}")
            self.all_screens.append(Screen(str(self.name) + "_screen" + str(counter), screen_cfg, self.display, self.drawinstance))
            counter = counter + 1

        #Show a connecting screen on first run, so that in case of many streams = long initial startup, the user knows what is happening.
        self.drawinstance.placeholder(0, 0, int(self.display["resolution"]["width"]), int(self.display["resolution"]["height"]), "images/connecting.png")
        self.drawinstance.refresh()

    def get_disable_autorotation(self):
        if self.disable_autorotation:
            logger.debug(
                f"{self.name}: disable_autorotation is True, use input keyboard/mouse/touch only to rotate between screens")
        return self.disable_autorotation

    def _init_drawinstance(self):
        self.drawinstance = Draw([int(self.display["resolution"]["width"]), int(self.display["resolution"]["height"])], self.disable_pygame, self.name)

    def get_drawinstance(self):
        return self.drawinstance

    def update_active_screen(self,skip_update_connectable_camera = False):
        '''To be used in main loop and is used to update connectable and unconnectable camera streams on the current displayed screen'''
        logger.debug(f"{self.name}: update_active_screen {self.all_screens[self.activeindex].name}")
        if self.get_active_screen_disable_probing_for_all_streams():
            #disable_probing_for_all_streams has been requested, skip all smart logic
            self.all_screens[self.activeindex].update_connectable_camera_streams(skip=True)
            logger.debug(f"{self.name}: SKIPPING update_connectable_camera_streams, because disable_probing_for_all_streams for this screen {self.all_screens[self.activeindex].name} was set")
        else:
            self.all_screens[self.activeindex].update_connectable_camera_streams(skip=False)
            logger.debug(f"{self.name}: update_connectable_camera_streams, disable_probing_for_all_streams is off for this screen, so using probes {self.all_screens[self.activeindex].name}")

        self.all_screens[self.activeindex].update_screen()

    def destroy(self):
        logger.debug(f"{self.name}: THIS IS THE END, DESTROYING")
        for screen in self.all_screens:
            screen.destroy()
        self.drawinstance.destroy()
