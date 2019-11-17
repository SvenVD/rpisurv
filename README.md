# Rpisurv 2 - Raspberry pi surveillance an RPI IP Camera Monitor
Join the community on https://community.rpisurv.net (Please use this place for support questions instead of github issues).<br/>
Bug tracking https://github.com/SvenVD/rpisurv/issues.<br/>
Follow us on facebook https://www.facebook.com/rpisurv.<br/>
Have a chat on https://gitter.im/rpisurv/general.<br/>

If you like this software please consider donating:
 <a href="https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=QPJU9K2KZ8D94" target="_blank" rel="nofollow"><img src="https://www.paypal.com/en_US/i/btn/x-click-but21.gif" alt="" /></a>

## Release notes

See [RELEASE_NOTES](https://github.com/SvenVD/rpisurv/blob/master/RELEASE_NOTES.md)

## Goal
Rpisurv is designed to be simple to use (no need to fiddle with coordinates or detailed layout configs) and to be able to run unattended for long periods of time. Therefore watchdogs and autohealing logic have been implemented.
Version 2 adds functionality to define multiple screens which can be cycled between.

## Description
You can think of rpisurv as a wrapper for omxplayer with following features (Rpisurv uses omxplayer to fully make use of the GPU of the raspberry pi).

- Rpisurv implements a watchdog for every stream displayed, if the process gets killed somehow. It will try to restart the stream/process. This gives you a very robust surveillance screen.
- Autocalculcate coordinates for every stream displayed. The last stream defined will be stretched to make use of the complete screen but only if some pixels are unused (if autostretch option is True).
- Stream up/down detection and autorearrange of the screen layout (if disable_probing_for_all_streams is False). So for example if you stop a camera (or just stop the server on the camera), rpisurv will detect this and will recalculate/redraw the screen with the still available cameras. The same is true if a previous unconnectable rtsp stream becomes connectable. All without any user interaction.
- All this behaviour is available per screen, but as of version 2 you can configure multiple screens and cycle between them in an automated way or via the keyboard.
- Since 2.1.0 you can now also specify "image streams", to display images next to or instead of camera streams. The images will be auto-updated if they change remotely.

## How to get started
In short: The idea is to connect your raspberry pi to a monitor and tell rpisurv which stream(s) and screen(s) it should display or cycle between. Rpisurv will autocalculate all the rest.
- Get a monitor or a TV
- Get a raspberry pi dedicated for rpisurv, and install raspbian on it. Make sure your monitor is operating at the correct resolution
- If you are going to have multiple streams, add gpu_mem=512 to your /boot/config.txt
- git clone this repository: `git clone https://github.com/SvenVD/rpisurv`
- move into folder `cd rpisurv`
- OPTIONAL: checkout a specific branch, for example `git checkout v2_latest`, if you want to override the default version on master
- run `sudo ./install.sh`
- Get the correct stream url for your ip camera(s), there are some examples in /etc/rpisurv.conf
- configure your screen(s) and stream(s) in /etc/rpisurv.conf.
- OPTIONAL: configure optional options per screen or per camera stream in /etc/rpisurv.conf, the [example config file](https://github.com/SvenVD/rpisurv/blob/master/surveillance/conf/surveillance.yml) file explains them all
- reboot

## How to update <a name="how-to-update"></a>
- `cd rpisurv; git pull`
- OPTIONAL: checkout a specific branch, for example `git checkout v2_latest`, if you want to override the default version on master
- run `sudo ./install.sh` (The installer will ask if you want to preserve your current config file)
- `systemctl restart rpisurv`

## Placeholder images
After installation you may change the placeholder images to something you like.
- /usr/local/bin/rpisurv/images/connecting.png is shown when a camera stream is starting up
- /usr/local/bin/rpisurv/images/placeholder.png is shown on empty squares
- /usr/local/bin/rpisurv/images/noconnectable.png is shown full screen when no connectable streams are detected for the current active screen in case multiple are cycled between
- `systemctl restart rpisurv`

## Rpisurv in operation

If you used the install.sh script, you can configure your streams in /etc/rpisurv.conf. Do not forget to reboot afterwards.

If you are connected via keyboard/keypad, you can force the next screen by pressing and holding n or space (or keypad "+") for some seconds in case multiple screens were defined (this takes longer depending on amount of unconnectable streams and they thus need to wait for timeout, keep holding until screen changes. Note, you can change probe_timeout per camera stream if needed).

Keys F1 to F12 (or keypad 0 to 9), will force the equal numbered screen to be shown onscreen (this takes longer depending on amount of unconnectable streams and they thus need to wait for timeout, keep holding until screen changes. Note, you can change probe_timeout per camera stream if needed).

Disable rotation (as in pause rotation, as in fix the current displayed screen) dynamically during runtime. By pressing "p" (or keypad "*") to pause or "r" (or "," or keypad ".")' to resume/rotate. This overrides the disable_autorotation option if this has been set in the config file.


## Troubleshooting

- I advise you to test your urls in vlc or omxplayer (command line) first. It should work in these applications before attempting to use them in rpisurv

- If you used the install.sh script, logs are created at /usr/local/bin/rpisurv/logs/. You can use them for troubleshooting. Enable DEBUG logging for very detailed output of what is going on. see [logging_config](https://github.com/SvenVD/rpisurv/blob/master/surveillance/conf/logging.yml)

- If you are connected via keyboard/keypad, you can stop rpisurv by pressing and holding q (or backspace or keypad "/") (this can take some seconds) .

- To manage the screen without rebooting use systemctl
  - `sudo systemctl stop rpisurv` to stop the screen
  - `sudo systemctl start rpisurv` to start the screen
  - `sudo systemctl status rpisurv` to see last log and status of service

- If you want to stream rtsp over tcp please add `rtsp_over_tcp: true` to the stream in /etc/rpisurv.conf.
  See [example config file](https://github.com/SvenVD/rpisurv/blob/master/surveillance/conf/surveillance.yml) for an example.
  If you have a "smearing" effect this option may resolve it.
  Note that you need a version of omxplayer which is released after 14 March 2016 (https://github.com/popcornmix/omxplayer/pull/433) to do this.

- On a raspberry pi 3 it seems the default overscan settings are not good. If full screen is not used, if you have an unused bar in the bottom -> try to set `disable_overscan=1` in /boot/config.txt


## Feature requests

Feature requests are tracked on https://community.rpisurv.net. If you would like to have a feature implemented on rpisurv, please check that this is not already been requested on https://community.rpisurv.net. If it is then add your vote to it, if it is not then request it as a new feature. The votes give us an indication on how feature requests compare to each other regarding popularity.
