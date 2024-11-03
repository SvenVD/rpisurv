import logging
import yaml
import subprocess

from .Screen import Screen
from core.util.draw import Draw


logger = logging.getLogger('l_default')

class ScreenManager:
    """This class creates and handles screens objects and rotation"""
    def __init__(self,screen_manager_name, monitor, enable_caching_next_screen, disable_pygame):
        self.name = screen_manager_name
        self.firstrun = True
        self.monitor = monitor
        self.activeindex = 0
        self.disable_pygame = disable_pygame
        self._init_background_drawinstance()
        self._fetch_display_config()

        self.enable_caching_next_screen = enable_caching_next_screen

        self.futurecacheindex = 1
        self.currentcacheindex = -1


        self._init_screens()


    def _fetch_display_config(self):
        #xdisplay_id is in the form of :0.0 we need last one to know which display
        configpath=f"../etc/monitor{int(self.monitor['monitor_number'])+1}.yml"
        logger.debug(f"ScreenManager: {self.name}: Looking for config file {configpath}")
        with open(configpath, 'r') as ymlfile:
            cfg = yaml.safe_load(ymlfile)
            self.screens_cfg=cfg['essentials']['screens']
            self.disable_autorotation = cfg['essentials'].setdefault('disable_autorotation', False)

    def _create_cached_screen(self):

        # Check what streams are connectable for the next screen and update this next screens= instance with the information
        if self.get_future_cached_screen_disable_probing_for_all_streams():
            # Do not check for connectable cameras when disable_probing_for_all_streams is set to true, just try to draw all of them, and hard fail for the ones that are not connectable
            self.all_screens[self.futurecacheindex].update_connectable_streams(skip=True)
        else:
            self.all_screens[self.futurecacheindex].update_connectable_streams(skip=False)


        if self.enable_caching_next_screen:
            logger.debug(
                f"ScreenManager: {self.name}: _create_cached_screen with index {self.futurecacheindex} updating screen: {self.all_screens[self.futurecacheindex].name} in cache")

            #Update the screen for a cached screen means: start all stream instances for this screen in the background
            #Screen defaults are to start with hidden_state = True, so next step will not shown anything visible on screen which is what we want for a cached screen
            self.all_screens[self.futurecacheindex].update_screen()
        else:
            #If self.enable_caching_next_screen is False then the _create_cached_screen does not really create a cached screen, it only updates internal counters
            logger.debug(f"ScreenManager: {self.name}: Skip caching screen {self.all_screens[self.futurecacheindex].name} because of parameters enable_caching_next_screen: {self.enable_caching_next_screen}")

        self.currentcacheindex = self.futurecacheindex
        self.futurecacheindex = self.futurecacheindex + 1
        if self.futurecacheindex > self.max_index:
            logger.debug(f"ScreenManager: {self.name}: futurecacheindex ({self.futurecacheindex} >= {self.max_index}), resetting futurecacheindex")
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
        logger.debug(f"ScreenManager: {self.name}: activeindex = {self.activeindex}, futurecacheindex = {self.futurecacheindex}")
        if requested_index > self.max_index:
            #Note name of screens start with 1 but list of screens index start at 0
            logger.debug(f"ScreenManager: {self.name}: Force screen {requested_index + 1} requested, but this screen does not exist")
        elif requested_index == self.activeindex:
            #Note name of screens start with 1 but list of screens index start at 0
            logger.debug(f"ScreenManager: {self.name}: Force screen {requested_index + 1} requested, but this screen is already active")
        elif requested_index == self.currentcacheindex:
            #Note name of screens start with 1 but list of screens index start at 0
            logger.debug(f"ScreenManager: {self.name}: Force screen {requested_index + 1} requested, this screen is already in cache, do a normal rotate")
            self.rotate_next()
        else:
            #Note name of screens start with 1 but list of screens index start at 0
            logger.debug(f"ScreenManager: {self.name}: Force screen {requested_index + 1} requested")

            # Show loading screen
            self.background_drawinstance.placeholder(0, 0, int(self.monitor["resolution"]["width"]),int(self.monitor["resolution"]["height"]), "images/loading.png")
            self.background_drawinstance.refresh()
            #Destroy current active and cached screens
            self.all_screens[self.activeindex].hide_all_streams()
            self.all_screens[self.activeindex].destroy()
            self.all_screens[self.currentcacheindex].hide_all_streams()
            self.all_screens[self.currentcacheindex].destroy()

            #Show new requested screen
            self.activeindex = requested_index
            self.all_screens[requested_index].reset_active_timer()
            #For faster drawing skip probing(we are optimistic and assume all screens are connectable)
            self.all_screens[requested_index].update_connectable_streams(skip=True)
            self.all_screens[requested_index].update_screen()
            self.all_screens[requested_index].unhide_all_streams()

            #Cache a new screen for next normal rotation.
            self.futurecacheindex = requested_index + 1
            if self.futurecacheindex > self.max_index:
                logger.debug(f"ScreenManager: {self.name}: Force screen futurecacheindex ({self.futurecacheindex} >= {self.max_index}), resetting futurecacheindex ")
                self.futurecacheindex = 0
            self._create_cached_screen()
            #We need to refocus focus_background_pygame otherwise X will not send keypresses to this window and our keyhandling would not work anymore
            self.focus_background_pygame()

    def bootstrap(self):
        ''' This method bootstraps the screen carroussel, we need to run this method once on start of every screenmanager '''
        # During firstrun we need to start an active screen and the next screen hidden
        # We do this, so that on a rotate event the next screen can be shown without delay as all streams are already connected
        logger.debug(f"ScreenManager: {self.name}: bootstrap: bootstrapping")
        logger.debug(f"ScreenManager: {self.name}: bootstrap: starting first run active screen {self.all_screens[self.activeindex].name}")
        #Create cached screen on bootstrap if more than one screen is defined
        if self.max_index != 0:
            self._create_cached_screen()
        self.update_active_screen()
        self.all_screens[self.activeindex].unhide_all_streams()
        self.all_screens[self.activeindex].reset_active_timer()

        # We need to refocus focus_background_pygame otherwise X will not send keypresses to this window and our keyhandling would not work anymore
        self.focus_background_pygame()

    def rotate_next(self):
        ''' this methods contains logic destroy the current screen so that the next screen which was started behind it is shown'''

        if self.max_index == 0:
            logger.debug(f"ScreenManager: {self.name}: rotate_next: only one screen configured, do not rotate")
            return

        logger.debug(f"ScreenManager: {self.name}: rotate_next: indexes BEFORE rotate: futurecacheindex: {self.futurecacheindex} activeindex: {self.activeindex} max index is {self.max_index}")

        #During normal rotate event we need to do 3 things
        #- Destroy the current screen (cached screen in lower layer (if any) becomes visible)
        #- Start a new cached offscreen screen
        logger.debug(f"ScreenManager: {self.name}: rotate_next: destroying previous active screen {self.all_screens[self.activeindex].name}")
        # Show loading screen
        self.background_drawinstance.placeholder(0, 0, int(self.monitor["resolution"]["width"]), int(self.monitor["resolution"]["height"]), "images/loading.png")
        self.background_drawinstance.refresh()

        self.all_screens[self.activeindex].hide_all_streams()
        self.all_screens[self.activeindex].destroy()
        #Now the cached screen should be made visible
        logger.debug(f"ScreenManager: {self.name}: rotate_next: next screen: {self.all_screens[ self.currentcacheindex].name} active")
        self.all_screens[self.currentcacheindex].reset_active_timer()
        self.all_screens[self.currentcacheindex].update_screen()
        logger.debug(f"ScreenManager: {self.name}: rotate_next: unhide cached screen: {self.all_screens[self.currentcacheindex].name}")
        self.all_screens[self.currentcacheindex].unhide_all_streams()

        self.activeindex = self.currentcacheindex

        #We also need to create a new cache for the next rotate
        self._create_cached_screen()
        #We need to refocus focus_background_pygame otherwise X will not send keypresses to this window and our keyhandling would not work anymore
        self.focus_background_pygame()
        logger.debug(f"ScreenManager: {self.name}: rotate_next: indexes AFTER rotate: futurecacheindex: {self.futurecacheindex} activeindex: {self.activeindex} max index is {self.max_index}")

    def focus_background_pygame(self):
        try:
            # Get the list of windows using wmctrl
            wmctrl_output = subprocess.check_output(['wmctrl', '-l']).decode('utf-8')
            # Split the output into lines and search for the window name
            for line in wmctrl_output.splitlines():
                if "pygame window" in line:
                    # Extract the window ID (first column)
                    window_id = line.split()[0]
                    # Focus the window using xdotool
                    subprocess.run(['xdotool', 'windowfocus', '--sync', window_id])
                    logger.debug(
                        f"ScreenManager: {self.name}: focus_background_pygame: Focused window: {line.strip()}")
                    return
            logger.debug(
                f"ScreenManager: {self.name}: focus_background_pygame: pygame window not found can not focus")
        except subprocess.CalledProcessError as e:
            logger.debug(
                f"ScreenManager: {self.name}: focus_background_pygame: An error occurred: {e}")
    def _init_screens(self):
        '''This method initiates all screen instances'''
        counter = 1
        self.all_screens=[]
        # -1 because list start at zero
        self.max_index = len(self.screens_cfg) - 1
        for screen_cfg in self.screens_cfg:
            logger.debug(f"ScreenManager: {self.name}: _init_screens: Initialising screen with config {screen_cfg}")
            self.all_screens.append(Screen(str(self.name) + "_screen" + str(counter), screen_cfg, self.monitor, self.background_drawinstance))
            counter = counter + 1

        #Show a connecting screen on first run, so that in case of many streams = long initial startup, the user knows what is happening.
        self.background_drawinstance.placeholder(0, 0, int(self.monitor["resolution"]["width"]), int(self.monitor["resolution"]["height"]), "images/connecting.png")
        self.background_drawinstance.refresh()

    def get_disable_autorotation(self):
        if self.disable_autorotation:
            logger.debug(
                f"ScreenManager: {self.name}: disable_autorotation is True, use input keyboard/mouse/touch only to rotate between screens")
        return self.disable_autorotation

    def _init_background_drawinstance(self):
        self.background_drawinstance = Draw([int(self.monitor["resolution"]["width"]), int(self.monitor["resolution"]["height"])], self.disable_pygame, self.name, self.monitor['xdisplay_id'],self.monitor['x_offset'],self.monitor['y_offset'])

    def get_background_drawinstance(self):
        return self.background_drawinstance

    def update_active_screen(self,skip_update_connectable_camera = False):
        '''To be used in main loop and is used to update connectable and unconnectable camera streams on the current displayed screen'''
        logger.debug(f"ScreenManager: {self.name}: update_active_screen {self.all_screens[self.activeindex].name}")
        if self.get_active_screen_disable_probing_for_all_streams():
            #disable_probing_for_all_streams has been requested, skip all smart logic
            logger.debug(f"ScreenManager: {self.name}: update_active_screen: SKIPPING update_connectable_streams, because disable_probing_for_all_streams for this screen {self.all_screens[self.activeindex].name} was set")
            self.all_screens[self.activeindex].update_connectable_streams(skip=True)
        else:
            logger.debug(f"ScreenManager: {self.name}: update_active_screen: update_connectable_streams because disable_probing_for_all_streams is off for this screen, so using probes {self.all_screens[self.activeindex].name}")
            self.all_screens[self.activeindex].update_connectable_streams(skip=False)
        self.all_screens[self.activeindex].update_screen()

    def run_watchdogs_active_screen(self):
        logger.debug(f"ScreenManager: {self.name}: run_watchdogs_active_screen for {self.all_screens[self.activeindex].name}")
        self.all_screens[self.activeindex].run_screen_watchdogs()

    def destroy(self):
        logger.debug(f"ScreenManager: {self.name}: THIS IS THE END, DESTROYING")
        for screen in self.all_screens:
            screen.destroy()
        self.background_drawinstance.destroy()
