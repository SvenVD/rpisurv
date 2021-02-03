#!/usr/bin/python3
import re
import signal
import subprocess
import sys
import time

#from core.util import draw

from core.util.config import cfg
from core.util.setuplogging import setup_logging
from core.util import stats
from core.ScreenManager import ScreenManager


def convert_gpumem_string_to_bytes(inputmem):
    """ Converts the memory related string returned by command line tools into bytes"""
    conversions = {'K': 1024, 'M': 1024 ** 2, 'G': 1024 ** 3, 'T': 1024 ** 4}
    outputmem_bytes = float(re.sub('[A-Za-z]+', '', inputmem)) * conversions.get(re.sub('\d+', '', inputmem), 1)
    logger.debug("convert_gpumem_string_to_bytes: inputmem:" + str(inputmem) + " outputmem_bytes:" + str(outputmem_bytes))
    return outputmem_bytes


def log_free_gpumem(logtype="reloc"):
    '''Returns free gpu memory'''
    freekeyword=logtype
    totalkeyword=logtype + "_total"
    try:
        free_raw=subprocess.check_output(['/usr/bin/vcgencmd', 'get_mem', freekeyword], text=True, timeout=1 )
        total_raw=subprocess.check_output(['/usr/bin/vcgencmd','get_mem', totalkeyword], text=True, timeout=1 )
    except Exception as e:
        logger.error(f"Skipping calculating free {freekeyword} memory because of {repr(e)}")
    else:
        try:
            regex_result=re.search(freekeyword + "=(\d+[a-zA-Z]?)", free_raw)
            free=str(regex_result.group(1))
            regex_result=re.search(totalkeyword + "=(\d+[a-zA-Z]?)",total_raw)
            total=str(regex_result.group(1))
        except AttributeError as parseerror:
            logger.debug("Got " + str(parseerror) + " error when parsing free memory")
        else:
            logger.debug("free " + str(freekeyword) + " gpu mem value is " + str(free))
            logger.debug("total available " + str(freekeyword) + " gpu mem value is " + str(total))

        free_bytes=convert_gpumem_string_to_bytes(free)
        total_bytes=convert_gpumem_string_to_bytes(total)
        pctfree=free_bytes/total_bytes

        pctfree_threshold=0.05
        if pctfree < pctfree_threshold:
            logger.error("Less than " + str(pctfree_threshold*100) + "% free" + str(freekeyword) + " gpu memory (" + str(free_bytes) + "/" + str(total_bytes) + "=" + str(pctfree*100) + "%" + ") Streams might fail to start. Consider assigning more memory to gpu in /boot/config.txt with the gpu_mem option")
            return 1
        return 0


def fix_vlc_executed_as_root():
    logger.debug("Make sure vlc binary can be executed as root")
    subprocess.check_call(["/bin/sed -i 's/geteuid/getppid/' /usr/bin/vlc" ], shell=True)

def handle_stats( stats_counter ):
    stats_counter_thresh=3600
    # Updating stats for rpisurv community every 1800 loops
    if stats_counter % stats_counter_thresh == 0:
        stats.update_stats(version, uniqid, str(stats.get_runtime(start_time)), update_stats_enabled)

def parse_tvservice():
    autodetected_displays=[]
    try:
        tvserviceresult_l = subprocess.check_output(['/usr/bin/tvservice', '-l'], text=True )
    except OSError as e:
        logger.error("Can not find or run the /usr/bin/tvservice binary to autodetect attached displays")
        use_fallback_config = True
    else:
        use_fallback_config = False
        regex_results = re.findall("Display Number (\d+), type HDMI (\d+)", tvserviceresult_l)
        if len(regex_results) == 0:
            use_fallback_config = True
        else:
            for regex_result in regex_results:
                autodetected_display = {}
                autodetected_display["display_number"]=regex_result[0]
                autodetected_display["hdmi"]=regex_result[1]
                autodetected_displays.append(autodetected_display)
                #Get more details
                tvserviceresult_detail_display = subprocess.check_output(['/usr/bin/tvservice', '-snv', autodetected_display["display_number"]], text=True)
                regex_result = re.search("state .*, (\d+)x(\d+) .*", tvserviceresult_detail_display)
                if regex_result is None:
                    logger.error(f"Could not retrieve resolution for display {autodetected_display['display_number']}")
                    use_fallback_config = True
                    break
                autodetected_display["resolution"] = {}
                autodetected_display["resolution"]["width"] = regex_result.group(1)
                autodetected_display["resolution"]["height"] = regex_result.group(2)
                regex_result = re.search("device_name=(.*)", tvserviceresult_detail_display)
                if regex_result is None:
                    logger.error(f"Could not retrieve devicename for display {autodetected_display['display_number']}")
                    use_fallback_config = True
                    break
                autodetected_display["device_name"] = regex_result.group(1)

    if use_fallback_config:
        fallback_displays = cfg['fallbacks']['displays']

        logger.error(f"Could not autodetect displays, use values from fallback config")
        for display in fallback_displays:
            logger.error(f"Using config display {display['device_name']} at HDMI {display['hdmi']} with display number {display['display_number']} {display['resolution']['width']} x {display['resolution']['height']}")

        displays = fallback_displays
    else:
        for display in autodetected_displays:
            logger.info(f"Auto detected display {display['device_name']} at HDMI {display['hdmi']} with display number {display['display_number']} {display['resolution']['width']} x {display['resolution']['height']}")

        displays = autodetected_displays

    return displays

def handle_input(drawinstance):
    event = drawinstance.check_input()
    for screenmanager in screenmanagers:
        if event == "next_event":
            logger.debug(f"MAIN: force next screen input event detected, start rotate_next event")
            screenmanager.rotate_next()
            # This can do no harm, but is not really needed in this case, since the screen was already updated in cache and we merely swap it on screen as is.
            # We do not check update_connectable_cameras this time as this is too slow for the user to wait for and we live with the fact if there is one unavailable or one became available since cache time,
            # it is not updated until next regular update of the screen
        if event == "end_event":
            logger.debug(f"MAIN: quit input event detected")
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
        screenmanager.destroy()
    sys.exit(0)


if __name__ == '__main__':


    signal.signal(signal.SIGTERM, sigterm_handler)

    #Setup logger
    logger = setup_logging()

    fullversion_for_installer = "3.0.0-beta6"

    version = fullversion_for_installer
    logger.info("Starting rpisurv " + version)

    fix_vlc_executed_as_root()

    #Read in config
    update_stats_enabled=cfg['advanced']['update_stats'] if 'update_stats' in cfg["advanced"] else False #Override of update_stats if set
    interval_check_status=cfg['advanced']['interval_check_status'] if 'interval_check_status' in cfg["advanced"] else 19 #Override of interval_check_status if set
    memory_usage_check=cfg['advanced']['memory_usage_check'] if 'memory_usage_check' in cfg["advanced"] else True #Override of memory_usage_check if set
    enable_opportunistic_caching_next_screen=cfg['advanced']['enable_opportunistic_caching_next_screen'] if 'enable_opportunistic_caching_next_screen' in cfg["advanced"] else True #Override of enable_opportunistic_caching_next_screen if set


    #Detect displays attached and their config
    displays=parse_tvservice()

    #Timers for statistics
    uniqid = stats.generate_uniqid()
    start_time = stats.start_timer()
    loop_counter=0

    if len(displays) > 1:
        logger.info("Globally force disable caching screen if more than one display is detected, since this takes too much resources for the pi on dual hdmi screen")
        enable_opportunistic_caching_next_screen = False

    screenmanagers=[]
    count=0
    for display in displays:
        disable_pygame = True
        # Only one screenmanager may be the master of the pygame in the case we have multiple instances. choose the first screen detected
        if count == 0:
            disable_pygame = False
        screen_manager=ScreenManager(f'screen_manager_{count}', display, enable_opportunistic_caching_next_screen, disable_pygame)
        screenmanagers.append(screen_manager)
        count= count + 1
        
        
    #First rotate to init first run
    for screenmanager in screenmanagers:
        screenmanager.rotate_next()
        logger.debug(f"MAIN {screenmanager.name}: bootstrap update_active_screen")
        screenmanager.update_active_screen()


    while True:
        #Handle stats
        handle_stats(loop_counter)
        loop_counter += 1

        #Handle keypresses
        #Only the first screenmanager is the controller of pygame
        handle_input(screenmanagers[0].get_drawinstance())

        #Check free mem and log warning
        if memory_usage_check:
            log_free_gpumem(logtype="malloc")
            log_free_gpumem(logtype="reloc")

        #Check if we need to rotate:
        for screenmanager in screenmanagers:
            if not screenmanager.get_disable_autorotation():
                if screenmanager.get_active_screen_run_time() >= screenmanager.get_active_screen_duration():
                    screenmanager.rotate_next()
                    #In case the screen in cache had disconnected or reconnectable streams, check and update it once it becomes active
                    logger.debug(f"MAIN {screenmanager.name}: after rotate_next start update_active_screen")
                    screenmanager.update_active_screen()

            #Only update the screen/check connectable cameras every interval_check_status seconds
            if loop_counter % int(interval_check_status) == 0:
                # Only try to redraw the screen when disable_probing_for_all_streams option is false, but keep the loop
                logger.debug(f"MAIN {screenmanager.name}: regular start update_active_screen (every " + str(interval_check_status) + " seconds since start of rpisurv)")
                screenmanager.update_active_screen()

        time.sleep(1)
