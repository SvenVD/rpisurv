# Rpisurv 3 - Raspberry Pi surveillance
Join the community on https://community.rpisurv.net (Please use this place for support questions instead of github issues).<br/>
Bug tracking https://github.com/SvenVD/rpisurv/issues.<br/>
Follow us on facebook https://www.facebook.com/rpisurv.<br/>
Have a chat on https://gitter.im/rpisurv/general.<br/>

 You can help sustain our activities by donating here:
 <a href="https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=QPJU9K2KZ8D94" target="_blank" rel="nofollow"><img src="https://www.paypal.com/en_US/i/btn/x-click-but21.gif" alt="" /></a>

Or if you prefer crypto take a look at the funding page [here](FUNDING.md)

## What is Rpisurv?

Rpisurv is a free application that transforms your Raspberry Pi into a dedicated device to display video streams or images.

Take a look at some [showcases](https://www.tapatalk.com/groups/rpisurv/showcases-f8/)

![Screenshot](https://gist.githubusercontent.com/SvenVD/84b230515e56bc7dca915731425ce437/raw/df7691cca60850a5b3864ce17cd8c9a8a73861ac/demo2images_andautocalculation_small.png)

## Features
##### Self-healing and health monitoring including watchdogs
- Every stream will be monitored by an external watchdog process, if the stream gets killed somehow, the watchdog will try to restart the stream/process. This gives you a very robust surveillance screen.
- Stream up/down detection and autorepositioning of connectable streams on the screen layout. 
  For example: if you stop a camera (or just stop the server on the camera), Rpisurv will detect this and will recalculate/redraw the screen with the still available streams. The same is true if a previous unconnectable stream becomes connectable. All without any user interaction.

##### Automatically position streams (no manual coordinates calculation needed)
- Autocalculcate coordinates for every stream displayed.
- If you are not happy with the autocalculations you [can](https://gist.github.com/SvenVD/5c82acbb96dfb697e5e2d2420ab73ad9) customize yourself. 

##### Rotation of screens (autorotate or with keyboard control)
- You can configure multiple screens and cycle between them in an automated way or via the keyboard. 
- In the case of dual displays, you can configure multiple screens to be cycled between for each display.

##### Multiple types of streams
- You can also specify "image streams", to display images next to or instead of camera streams. The images will be auto-updated if they change remotely.

##### Dual Hdmi support
- Rpisurv will auto-detect if a second display is connected at boot and will automatically start the configured screens for the second display.

## How to get started
In short: The idea is to connect your Raspberry Pi to a monitor and tell Rpisurv which stream(s) and screen(s) it should display or cycle between. Rpisurv will autocalculate all the rest.
- Get a monitor or a TV ( or 2 )
- Get a Raspberry Pi dedicated for Rpisurv
- Install Raspberry Pi OS **Full (Legacy)** on the Pi (Tested successfully with the full version, not lite)
  - Make sure to select the **Legacy** version as there are [problems](https://github.com/SvenVD/rpisurv/issues/141) with VLC on latest RPi OS (which is based on Debian Bullseye).
- If you are going to have multiple streams, add gpu_mem=512 to your /boot/config.txt
- If you installed the "Lite" OS version you will need to edit /boot/config.txt and uncomment `framebuffer_width=1280' and 'framebuffer_height=720` and make them 1920 and 1080 respectively or you will encounter the following error `pygame.error: No video mode large enough for 1920x1080`
- git clone this repository: `git clone https://github.com/SvenVD/rpisurv`
- move into folder `cd rpisurv`
- OPTIONAL: checkout a specific branch, for example `git checkout v3_latest`, if you want to override the default version on master
- run `sudo ./install.sh`
- Enjoy the demo showcase

## Configuration

Rpisurv has the following config files
- `/etc/rpisurv/general.yml` => General config, mostly not needed to touch this.
- `/etc/rpisurv/display1.yml`  => Define screens and streams used for first monitor.
- `/etc/rpisurv/display2.yml`  => Define screens and streams used for second monitor.
Which monitor will be display1 or display2 depends on which HDMI port you plug it in.   
If you only plug one monitor then only one of the config files will be read (display1.yml or display2.yml).

A screen consists out of multiple streams.
A display is the equivalent of a monitor. On a display you can define multiple screens which can be cycled between.

For full config explanation with all possible options consult the config files in /etc/rpisurv after install.

## URL sources

#### file://
This is a path on disk, by default a videofile is expected. This videofile will then be played in an endless loop.
If used with imageurl: true then an image file is expected. If the image changes on disk then Rpisurv will also reload the stream with the new image.
Note in dual displays mode imageurl type streams are only displayed on 1 display (`/etc/rpisurv/display1.yml`).
TIP: If an external program rotates the images on disk then Rpisurv can thus be used as a frontend for a digital picture frame.
#### http:// and https://
This is a remote location with a video file or video stream
If used with imageurl: true then an image file is expected. If the remote image changes then Rpisurv will also reload the stream with the new image.
Note in dual displays mode imageurl type streams are only displayed on 1 display (`/etc/rpisurv/display1.yml`).
TIP: This can be used as part of a digital signage setup: several Rpisurv clients can be steered centrally by changing the image(s) on the central location.
Rpisurv will autodetect interruptions and tries to restore the stream.
#### rtsp:// and rtmp://
This is a remote location with a video stream, Rpisurv will do his best to display the stream, it will autodetect interruptions and tries to restore the stream.

## How to update Rpisurv to new version <a name="how-to-update"></a>
- `cd rpisurv; git pull`
- OPTIONAL: checkout a specific branch, for example `git checkout v3_latest`, if you want to override the default version on master
- run `sudo ./install.sh` (The installer will ask if you want to preserve your current config file)
- `systemctl restart rpisurv`

## Release notes

See [RELEASE_NOTES](https://github.com/SvenVD/rpisurv/releases)

## Placeholder images
After installation you may change the placeholder images to something you like.
- /usr/local/bin/rpisurv/images/connecting.png is shown when a camera stream is starting up
- /usr/local/bin/rpisurv/images/placeholder.png is shown on empty squares
- /usr/local/bin/rpisurv/images/noconnectable.png is shown full screen when no connectable streams are detected for the current active screen in case multiple are cycled between
- `systemctl restart rpisurv`

## Rpisurv in operation

If you used the install.sh script, you can configure your streams in /etc/rpisurv. After editing the config files you need to restart Rpisurv for the changes to be in effect.

If you are connected via keyboard/keypad, you can force the next screen by pressing and holding n or space (or keypad "+") for some seconds in case multiple screens were defined (this takes longer depending on amount of unconnectable streams and they thus need to wait for timeout, keep holding until screen changes. Note, you can change probe_timeout per camera stream if needed).

Keys F1 to F12 (or keypad 0 to 9), will force the equal numbered screen to be shown onscreen (this takes longer depending on amount of unconnectable streams and they thus need to wait for timeout, keep holding until screen changes. Note, you can change probe_timeout per camera stream if needed).

Disable rotation (as in pause rotation, as in fix the current displayed screen) dynamically during runtime. By pressing "p" (or keypad "*") to pause or "r" (or "," or keypad ".")' to resume/rotate. This overrides the disable_autorotation option if this has been set in the config file.

Touchscreen control:
The width of the screen is divided in four sections, 
- Touching on the first section trigger a pause event.
- Touching In the two sections in the middle trigger a resume event.
- Touching In the last section, a next screen event.
Note that a mouse can be used, however mouse cursor is hidden by default.

In case of dual HDMI then the screens on both displays will be controlled at the same time.


## Troubleshooting

- I advise you to test your urls in vlc (command line) first. It should work before attempting to use them in rpisurv.

- If you used the install.sh script, logs are created at /usr/local/bin/rpisurv/logs/. You can use them for troubleshooting. Enable DEBUG logging for very detailed output of what is going on. see [logging_config](https://github.com/SvenVD/rpisurv/blob/master/surveillance/conf/logging.yml)

- If you are connected via keyboard/keypad, you can stop Rpisurv by pressing and holding q (or backspace or keypad "/") (this can take some seconds) .

- To manage the screen without rebooting use systemctl
  - `sudo systemctl stop rpisurv` to stop the screen
  - `sudo systemctl start rpisurv` to start the screen
  - `sudo systemctl status rpisurv` to see last log and status of service

- If you want to stream rtsp over tcp please add `rtsp_over_tcp: true` to the stream in /etc/rpisurv.
  See in /etc/rpisurv for examples.
  If you have a "smearing" effect this option may resolve it.

- On a Raspberry Pi 3 and 4 it seems the default overscan settings are not good. If full screen is not used, if you have an unused bar in the bottom -> try to set `disable_overscan=1` in /boot/config.txt

- Users on a Raspberry Pi 4 which experience flickering can try to set `disable_overscan=1` in /boot/config.txt. As reported here: [link](https://www.tapatalk.com/groups/rpisurv/camera-flickering-not-sure-what-is-the-issue-t48.html#p192).


## Feature requests

Feature requests are tracked on https://community.rpisurv.net. If you would like to have a feature implemented on rpisurv, please check that this is not already been requested on https://community.rpisurv.net. If it is then add your vote to it, if it is not then request it as a new feature. The votes give us an indication on how feature requests compare to each other regarding popularity.
