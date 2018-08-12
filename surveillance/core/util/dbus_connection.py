#Based on https://github.com/willprice/python-omxplayer-wrapper


import dbus
import logging

logger = logging.getLogger('l_default')

class DBusConnectionError(Exception):
    """ Connection error raised when DBusConnection can't set up a connection
    """
    logger.error('DBusConnectionError: Could not get proxy object')
    pass

class DBusConnection(object):
    """
    Attributes:
        proxy:  The proxy object by which one interacts  with a dbus object,
                this makes communicating with a similar to that of communicating
                with a  POJO.
        root_interface:  org.mpris.MediaPlayer2 interface proxy object
        player_interface: org.mpris.MediaPlayer2.Player interface  proxy object
    """

    def __init__(self, bus_address, dbus_name=None):
        if dbus_name:
            self._dbus_name = dbus_name
        else:
            self._dbus_name = 'org.mpris.MediaPlayer2.omxplayer'
        print bus_address
        self._bus = dbus.bus.BusConnection(bus_address)
        self.proxy = self._create_proxy()

        self.root_interface = dbus.Interface(self.proxy, 'org.mpris.MediaPlayer2')
        self.player_interface = dbus.Interface(self.proxy, 'org.mpris.MediaPlayer2.Player')
        self.properties_interface = dbus.Interface(self.proxy, 'org.freedesktop.DBus.Properties')

    def _create_proxy(self):
        try:
            # introspection fails so it is disabled
            proxy = self._bus.get_object(self._dbus_name,
                                         '/org/mpris/MediaPlayer2',
                                         introspect=False)
            return proxy
        except dbus.DBusException:
            raise DBusConnectionError('Could not get proxy object')

    def VideoPosWrapper(self,args):
        timeout=3
        try:
            # Neither get_object nor start_service_by_name support a timeout. As a workaround you can directly use call_blocking before.
            #This call is just for forcing a shorter timeout then default in case bus is not ready or available
            logger.debug("DBusConnection: start TESTING if bus " + self._dbus_name + " is ready to accept videopos commands")
            self._bus.call_blocking(self._dbus_name, '/org/mpris/MediaPlayer2',
                                    'org.mpris.MediaPlayer2.Player',
                                    'VideoPos',
                                    None, (args), timeout=timeout)

            logger.debug("DBusConnection: bus: " + self._dbus_name + " is ready to accept videopos commands")

            #The previous call_blocking directly is kind of a hack to be able to set the timeout, if this stops working in the future use below to set the VideoPos
            #self.player_interface.VideoPos(args)
        except dbus.DBusException as e:
            logger.debug("DBusConnection: The bus: " + self._dbus_name + " is NOT ready to accept videopos commands: %s", e)

# The python dbus bindings don't provide property access via the
# 'org.freedesktop.DBus.Properties' interface so we wrap the access of
# properties using
class DbusObject(object):
    def __init__(self, object_proxy, property_manager, interface_name, methods, properties):
        self._proxy = object_proxy
        self._property_manager = property_manager
        self._interface_name = interface_name
        self._methods = methods
        self._properties = properties

    def __getattr__(self, name):
        if name in self._methods:
            return self._proxy.__getattr__(name)
        elif name in self._properties:
            return self._property_manager.Get(self._interface_name, name)
        else:
            raise AttributeError("'{}' attribute not specified on this DBus object".format(name))

