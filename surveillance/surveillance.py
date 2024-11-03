#!/usr/bin/python3
import signal
import sys
import time
import Xlib.display

from core.util.config import cfg
from core.util.setuplogging import setup_logging
from core.ScreenManager import ScreenManager

def get_monitors():
    display = Xlib.display.Display()
    root = display.screen().root

    monitor_list = []
    monitor_counter = 0
    # Iterate over the monitors and create dictionaries
    for m in root.xrandr_get_monitors().monitors:
        connector = display.get_atom_name(m.name)
        monitor_dict = {
            "xdisplay_id": ":0.0",
            "monitor_id": connector,  # or use m.name if you want the name directly
            "monitor_number": monitor_counter,
            "resolution": {
                "width": str(m.width_in_pixels),  # Convert to string as per your structure
                "height": str(m.height_in_pixels)  # Convert to string as per your structure
            },
            "x_offset": str(m.x),  # Convert to string
            "y_offset": str(m.y)  # Convert to string
        }
        monitor_list.append(monitor_dict)
        monitor_counter += 1
    logger.debug(f"MAIN: get_monitors: detected {monitor_list}")
    return monitor_list

def handle_input(background_drawinstance):
    event = background_drawinstance.check_input()
    for screenmanager in screenmanagers:
        if event == "next_event":
            logger.debug(f"MAIN: force next screen input event detected, start rotate_next event")
            screenmanager.rotate_next()
            # This can do no harm, but is not really needed in this case, since the screen was already updated in cache and we merely swap it on screen as is.
            # We do not check update_connectable_cameras this time as this is too slow for the user to wait for and we live with the fact if there is one unavailable or one became available since cache time,
            # it is not updated until next regular update of the screen
        if event == "end_event":
            logger.debug(f"MAIN: quit input event detected")
            for screenmanager in screenmanagers:
                logger.debug(f"MAIN: instruct {screenmanager.name} to be destroyed")
                screenmanager.destroy()
            sys.exit(0)
        if event == "resume_rotation":
            logger.debug(f"MAIN: resume_rotation event detected")
            screenmanager.disable_autorotation = False
        if event == "pause_rotation":
            logger.debug(f"MAIN: pause_rotation event detected")
            screenmanager.disable_autorotation = True
        if event in range(0, 11):
            logger.debug(f"MAIN: force screen:{event} request detected")
            screenmanager.force_show_screen(event)


def sigterm_handler(_signo, _stack_frame):
    for screenmanager in screenmanagers:
        logger.debug(f"MAIN: instruct {screenmanager.name} to be destroyed")
        screenmanager.destroy()
    sys.exit(0)


if __name__ == '__main__':


    signal.signal(signal.SIGTERM, sigterm_handler)

    #Setup logger
    logger = setup_logging()

    fullversion_for_installer = "4.0.0beta2"

    version = fullversion_for_installer
    logger.info("Starting rpisurv " + version)

    #Read in config
    interval_check_status=cfg['advanced']['interval_check_status'] if 'interval_check_status' in cfg["advanced"] else 19 #Override of interval_check_status if set
    enable_caching_next_screen=cfg['advanced']['enable_caching_next_screen'] if 'enable_caching_next_screen' in cfg["advanced"] else True #Override of enable_caching_next_screen if set

    #Detect displays attached and their config
    monitors=get_monitors()

    screenmanagers=[]
    count=0
    for monitor in monitors:
        disable_pygame = True
        # Only one screenmanager may be the master of the pygame in the case we have multiple instances. choose the first screen detected
        if count == 0:
            disable_pygame = False
        screen_manager=ScreenManager(f'screen_manager_{count}', monitor, enable_caching_next_screen, disable_pygame)
        screenmanagers.append(screen_manager)
        count= count + 1


    #Bootstrap all screenmanagers
    for screenmanager in screenmanagers:
        logger.debug(f"MAIN {screenmanager.name}: START bootstrap")
        screenmanager.bootstrap()
        logger.debug(f"MAIN {screenmanager.name}: END bootstrap")
    loop_counter=0
    while True:
        loop_counter += 1

        #Handle keypresses
        #Only the first screenmanager is the controller of pygame
        handle_input(screenmanagers[0].get_background_drawinstance())

        #Check if we need to rotate:
        for screenmanager in screenmanagers:
            if not screenmanager.get_disable_autorotation():
                if screenmanager.get_active_screen_run_time() >= screenmanager.get_active_screen_duration():
                    screenmanager.rotate_next()
                    #In case the screen in cache had disconnected or reconnectable streams, check and update it once it becomes active
                    logger.debug(f"MAIN {screenmanager.name}: after rotate_next start update_active_screen")
                    screenmanager.update_active_screen()

            #Only update the screen/check connectable cameras and repair every interval_check_status seconds
            if loop_counter % int(interval_check_status) == 0:
                # Only try to redraw the screen when disable_probing_for_all_streams option is false, but keep the loop
                logger.debug(f"MAIN {screenmanager.name}: regular start update_active_screen (every " + str(interval_check_status) + " seconds since start of rpisurv)")
                screenmanager.update_active_screen()
                # Call the watchdogs to check and try to repair for crashed instances
                screenmanager.run_watchdogs_active_screen()

            #Reset focus pygame for keyhandling
            screenmanager.focus_background_pygame()

        time.sleep(1)
