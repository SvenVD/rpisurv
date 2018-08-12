#Based on https://github.com/willprice/python-omxplayer-wrapper

import os.path
import time
from glob import glob
import logging

logger = logging.getLogger('l_default')

class BusFinder(object):
    def __init__(self, path=None):
        self.path = path
        logger.debug('BusFinder: initialised with path: %s' % path)

    def get_address(self):
        self.wait_for_file()
        logger.debug('BusFinder: Opening file at %s' % self.path)
        with open(self.path, 'r') as f:
            logger.debug('BusFinder: Opened file at %s' % self.path)
            self.address = f.read().strip()
            logger.debug('BusFinder: Address \'%s\' parsed from file' % self.address)
        return self.address

    def find_address_file(self):
        """
        Finds the OMXPlayer DBus connection
        Assumes there is an alive OMXPlayer process.
        :return:
        """
        possible_address_files = []
        while not possible_address_files:
            # filter is used here as glob doesn't support regexp :(
            isnt_pid_file = lambda path: not path.endswith('.pid')
            possible_address_files = list(filter(isnt_pid_file,
                                            glob('/tmp/omxplayerdbus.*')))
            possible_address_files.sort(key=lambda path: os.path.getmtime(path))
            time.sleep(0.05)

        self.path = possible_address_files[-1]

    def wait_for_path_to_exist(self):
        while not os.path.isfile(self.path):
            time.sleep(0.05)

    def wait_for_dbus_address_to_be_written_to_file(self):
        while not os.path.getsize(self.path):
            time.sleep(0.05)

    def wait_for_file(self):
        if self.path:
            self.wait_for_path_to_exist()
        else:
            self.find_address_file()
        self.wait_for_dbus_address_to_be_written_to_file()


#busfinder = BusFinder()
#print busfinder.get_address()
