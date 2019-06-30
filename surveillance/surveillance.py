#!/usr/bin/python
import re
import signal
import subprocess
import sys
import time
import core.util.draw as draw

from core.util.config import cfg
from core.util.setuplogging import setup_logging
from core.util import stats
from core.ScreenManager import ScreenManager



def get_free_gpumem():
    '''Returns free gpu memory'''
    free_gpumem=None
    try:
        gpumemresult=subprocess.check_output(['/usr/bin/vcdbg','reloc'])
    except OSError as e:
        logger.error("Can not find or run the vcdbg binary to get free gpu mem")
    else:
        try:
            regex_result=re.search("(\d+[a-zA-Z]?) free memory .*",gpumemresult)
            free_gpumem=str(regex_result.group(1))
        except AttributeError as parseerror:
            logger.debug("Got " + str(parseerror) + " error when parsing free memory")
        else:
            logger.debug("Free gpu memory value is " + str(free_gpumem))

    return free_gpumem


def check_free_gpumem():
    '''Returns 0 if enough mem is available, returns 1 if not enough mem is available'''
    threshold_bytes = 80000000
    free_gpumem = get_free_gpumem()
    if free_gpumem is not None:
        conversions = {'K': 1024, 'M': 1024 ** 2, 'G': 1024 ** 3, 'T': 1024 ** 4}
        free_gpumem_bytes = float(re.sub('[A-Za-z]+','', free_gpumem))*conversions.get(re.sub('\d+','', free_gpumem),1)
        logger.debug("Free memory in bytes: " + str(free_gpumem_bytes))
        if int(free_gpumem_bytes) < int(threshold_bytes):
            logger.error("Free gpu mem is " + str(free_gpumem_bytes) + " bytes which is less than " + str(threshold_bytes) + " bytes. Streams might fail to start. Consider assigning more memory to gpu in /boot/config.txt with the gpu_mem option")
            return 1
        else:
            return 0
    else:
        logger.error("Could not determine free gpu memory, you need to check for yourself")
        return None



def handle_stats( stats_counter ):
    stats_counter_thresh=3600
    # Updating stats for rpisurv community every 1800 loops
    if stats_counter % stats_counter_thresh == 0:
        stats.update_stats(version, uniqid, str(stats.get_runtime(start_time)), update_stats_enabled)

def get_resolution():
    '''autodetects resolution if possible otherwise fallback to fallback defaults'''
    try:
        fbsetresult = subprocess.check_output(['/bin/fbset', '-s'])
    except OSError as e:
        logger.error("Can not find or run the fbset binary to autodetect the resolution")
        autodetect_resolution = None
    else:
        regex_result = re.search("geometry (\d+) (\d+)", fbsetresult)
        autodetect_resolution = [regex_result.group(1), regex_result.group(2)]
        logger.debug("autodetected resolution of" + str(autodetect_resolution))

    if autodetect_resolution is None:
        resolution = [cfg['fallbacks']['resolution']['width'], cfg['fallbacks']['resolution']['height']]
    else:
        resolution = autodetect_resolution
    return resolution


def sigterm_handler(_signo, _stack_frame):
    draw.destroy()
    sys.exit(0)


def handle_keypresses():
    global disable_autorotation
    event = draw.check_keypress()
    if event == "next_event":
        logger.debug("Main: force next screen keyboard event detected, start rotate_next event")
        screen_manager_main.rotate_next()
        # This can do not harm, but is not really needed in this case, since the screen was already updated in cache and we merely swap it on screen as is.
        # We do not check update_connectable_cameras this time as this is to slow for the user to wait for and we live with the fact if there is one unavailable or one became available since cache time,
        # it is not updated until next regular update of the screen
        # logger.debug("MAIN: after keyboard next_event start update_active_screen with skip_update_connectable_camera true")
        # screen_manager_main.update_active_screen(skip_update_connectable_camera = True)
    if event == "end_event":
        logger.debug("Main:  quit_on_keyboard event detected")
        screen_manager_main.destroy()
    if event == "resume_rotation":
        logger.debug("Main: resume_rotation event detected")
        disable_autorotation = False
    if event == "pause_rotation":
        logger.debug("Main: pause_rotation event detected")
        disable_autorotation = True
    if event in range(0,11):
        logger.debug("Main: force screen:" + str(event) + " request detected")
        screen_manager_main.force_show_screen(event)

if __name__ == '__main__':

    signal.signal(signal.SIGTERM, sigterm_handler)

    #Setup logger
    logger = setup_logging()

    fullversion_for_installer = "2.1.2"

    version = fullversion_for_installer
    logger.info("Starting rpisurv " + version)

    #Read in config

    disable_autorotation = cfg['essentials'].setdefault('disable_autorotation', False)

    if type(cfg["advanced"]) is dict:
        fixed_width=cfg['advanced']['fixed_width'] if 'fixed_width' in cfg["advanced"] else None #Override of autocalculation width if set
        fixed_height=cfg['advanced']['fixed_height'] if 'fixed_height' in cfg["advanced"] else None #Override of autocalculation height if set
        update_stats_enabled=cfg['advanced']['update_stats'] if 'update_stats' in cfg["advanced"] else False #Override of update_stats if set
        interval_check_status=cfg['advanced']['interval_check_status'] if 'interval_check_status' in cfg["advanced"] else 19 #Override of interval_check_status if set
        memory_usage_check=cfg['advanced']['memory_usage_check'] if 'memory_usage_check' in cfg["advanced"] else True #Override of memory_usage_check if set
        cache_next_screen=cfg['advanced']['cache_next_screen'] if 'cache_next_screen' in cfg["advanced"] else True #Override of cache_next_screen if set
    else:
        fixed_width=None
        fixed_height=None
        update_stats_enabled=False
        interval_check_status=19
        memory_usage_check=True
        cache_next_screen=True

    #Detect resolution
    resolution=get_resolution()

    screens_cfg=cfg['essentials']['screens']

    #Timers for statistics
    uniqid = stats.generate_uniqid()
    start_time = stats.start_timer()
    loop_counter=0


    screen_manager_main=ScreenManager('screen_manager_main', resolution, screens_cfg, fixed_width, fixed_height, cache_next_screen)
    #First rotate to init first run
    screen_manager_main.rotate_next()
    logger.debug("MAIN: bootstrap update_active_screen")
    screen_manager_main.update_active_screen()

    while True:
        #Handle stats
        handle_stats(loop_counter)
        loop_counter += 1

        #Handle keypresses
        handle_keypresses()

        #Check free mem and log warning
        if memory_usage_check:
            check_free_gpumem()

        #Check if we need to rotate:
        if not disable_autorotation:
            if screen_manager_main.get_active_screen_run_time() >= screen_manager_main.get_active_screen_duration():
                screen_manager_main.rotate_next()
                #In case the screen in cache had disconnected or reconnectable streams, check and update it once it becomes active
                logger.debug("MAIN: after rotate_next start update_active_screen")
                screen_manager_main.update_active_screen()

        else:
            logger.debug("MAIN: disable_autorotation is True, use keyboard only to rotate between screens")

        #Only update the screen/check connectable cameras every interval_check_status seconds
        if loop_counter % int(interval_check_status) == 0:
            # Only try to redraw the screen when disable_probing_for_all_streams option is false, but keep the loop
            logger.debug("MAIN: regular start update_active_screen (every " + str(interval_check_status) + " seconds since start of rpisurv)")
            screen_manager_main.update_active_screen()



        time.sleep(1)
