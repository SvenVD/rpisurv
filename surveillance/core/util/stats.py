import urllib2
import hashlib
import time
import ssl
import logging
from uuid import getnode as get_mac
from setuplogging import setup_logging
import multiprocessing

logger = logging.getLogger('l_default')

def start_timer():
    start_time = time.time()
    logger.debug("Start_time is " + str(start_time))
    return start_time

def get_runtime(start_time):
    '''get runtime in seconds'''
    currentime=time.time()
    runtime=long(round((currentime - start_time)))
    logger.debug("Current time detected is " + str(currentime) + " runtime calculated is " + str(runtime))

    return runtime

def generate_uniqid():
    mac=str(get_mac())

    #Hash the mac address to ensure anonymity
    m = hashlib.new('sha256')
    m.update(mac)
    mac_hash=m.hexdigest()
    logger.info("Unique id of this installation is " + mac_hash)
    return str(mac_hash)


def update_stats(version, uniqid, runtime, update_stats_enabled):
    if update_stats_enabled:
        # Run stats in separate short lived process to not interfere main program
        multiprocessing.Process(target=send_stats, args=(version, uniqid, runtime)).start()
    else:
        logger.info("Sending stats is disabled, not sending stats")

def send_stats(version, uniqid, runtime):
    #Because this is run as a subprocess we need to start logging again
    logger_send_stats = setup_logging(logfilepath="logs/send_stats.log",loggername="send_stats")

    destination="https://statscollector.rpisurv.net"

    #SSL options
    context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH, cafile="core/util/statscollector.rpisurv.net.pem")
    #Force TLS higher then 1.1
    context.options |= ssl.OP_NO_SSLv2
    context.options |= ssl.OP_NO_SSLv3
    context.options |= ssl.OP_NO_TLSv1
    context.options |= ssl.OP_NO_TLSv1_1
    #Normally this has been set by ssl.Purpose.SERVER_AUTH but for safety in future explicitly set CERT_REQUIRED
    context.verify_mode = ssl.CERT_REQUIRED
    httpshandler = urllib2.HTTPSHandler(context=context)

    opener = urllib2.build_opener(httpshandler)
    opener.addheaders=[
        ('User-Agent', uniqid),
        ('Pragma', 'no-cache'),
        ('Cache-Control', 'no-cache')
    ]
    #Extra info will be send via cookie headers
    #opener.addheaders.append(('Cookie', 'runtime='+ runtime + ';reservedkey=reservedvalue'))
    opener.addheaders.append(('Cookie', 'runtime='+ runtime + ';version='+ str(version)  ))

    urllib2.install_opener(opener)

    #f = opener.open("http://httpbin.org/cookies")
    logger_send_stats.debug("Start sending uniqid " + uniqid + ", runtime " + runtime + ", version " + str(version) + " to " + destination + " for updating stats rpisurv community")
    try:
        response = opener.open(destination, timeout=20)
    except urllib2.HTTPError, e:
        logger_send_stats.error("There was an error connecting to the statistics server at " + destination + ". Failed with code " + str(e.code))
    except Exception as e:
        logger_send_stats.error("There was an error connecting to the statistics server at " + destination + " , the error is " + repr(e))
    else:
        logger_send_stats.debug("data sent succesfully, response code " + str(response.getcode()))


