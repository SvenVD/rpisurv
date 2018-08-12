import logging, logging.config
import yaml
import os
import errno

def setup_logging(logfilepath = None,loggername=None):
    #Create default logs directory
    try:
        os.makedirs("logs")
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

    with open("conf/logging.yml", 'r') as ymlfile:
        logcfg = yaml.load(ymlfile)

    #Override some contents of config yaml file if needed
    if logfilepath is not None:
        #Override default filename from logging config file
        logcfg['handlers']['h_rotfile']['filename']= logfilepath
        #Else just use the logfilepath from the logging dictionary/config

    logging.config.dictConfig(logcfg)


    if loggername is None:
        loggername="l_default"

    return logging.getLogger(loggername)










