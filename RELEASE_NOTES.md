# rpisurv 2 release notes
## Changes in 2.1.2
The "comma" key can now be used to resume rotation, also the "backspace" key can now be used to quit rpisurv. This to allow german keypads to have all the needed functions.
This change has been requested on [link](https://www.tapatalk.com/groups/rpisurv/on-keypad-operation-change-rotation-key-from-to-t28.html).

## Bugfix in 2.1.1
Do not crash rpisurv if there is something wrong with loading the image.

## New features 2.1.0
It is now possible to show an image instead of a camerastream. The image is fetched from a choosen remote url. On top of that this remote url is watched for changes.
If the image is changed on the remote site, rpisurv will detect this and will also fetch the new image and update it on screen. The polling frequency is controlled by ```advanced: interval_check_status``` config option in /etc/rpisurv.conf.
The "image stream" follows the same health checks as a normal camera stream. This means if the specified image is unavailable it will not be shown on-screen by default (you can override this).
This feature has been requested on [link](https://www.tapatalk.com/groups/rpisurv/show-random-images-from-an-accessible-url-instead--t6.html).


## Upgrade notes from 1.0
The config file is still a yaml file but the keys have been changed to support the configuration of multiple screen in a rotation
You must manually convert your 1.0 config file to the new version 2 config file format. However the format is still as clear to use, but it is still a yaml file. So as always watch the indentations and do not use tabs, see [example config file](https://github.com/SvenVD/rpisurv/blob/v2.0_branch/surveillance/conf/surveillance.yml)
The normal update [procedure](https://github.com/SvenVD/rpisurv/blob/master/README.md#how-to-update) can be followed for upgrading.

## Features and changes since 1.0
- Implemented "Automatic cycle through list of cameras/screens" [link](https://feathub.com/SvenVD/rpisurv/+4).
- Pressing keys F1 to F12 (or keypad 0 to 9) on an attached keyboard/keypad, will force the equal numbered screen to be shown onscreen (this takes longer depending on amount of unconnectable streams and they thus need to wait for timeout, keep holding until screen changes. Note, you can change probe_timeout per camera stream if needed). Example use case: you can define one '2x2' screen and 4 1x1 screens with the same camera streams. That way you can select one camera stream out of the 2x2 by pressing F2-F5 and go back to 2x2 by pressing F1 [link](https://feathub.com/SvenVD/rpisurv/+3).
- Disable rotation (as in pause rotation, as in fix the current displayed screen) dynamically during runtime. Press "p" to pause and "r" to resume/rotate. This overrides the disable_autorotation option if this has been set in the config file.
- There is virtually no limit(hardware or software) for the amount of screens that can be defined.
- Implemented "Add mjpeg camera support" [link](https://feathub.com/SvenVD/rpisurv/+5) but not limited to mjpeg support, all omxplayer supported http/https streams can be configured.
- Possibility to force next screen in a carousel/slideshow by pressing "n" or "space" (or keypad "+") on an attached keyboard/keypad.
- Enabling the user to configure the duration of each screen in the carousel/slideshow by overriding the default with the "duration" option, see [example config file](https://github.com/SvenVD/rpisurv/blob/master/surveillance/conf/surveillance.yml).
- Enabling the user to specify a "probe_timeout" per camera stream. This for slow connecting streams to not be regarded as unconnectable by rpisurv, see [example config file](https://github.com/SvenVD/rpisurv/blob/master/surveillance/conf/surveillance.yml).
- "keep_first_screen_layout" option in v1.0 has been replaced by "disable_probing_for_all_streams" option in version 2 and has become a per screen configuration, which effect is roughly the same. (Not recommended to enable this though).
- All existing functionality from v1.0 is still available. If you only define one screen you essentially get the rpisurv v1.0 behaviour.
- rtps_urls config option which was already deprecated in v1.0 is now completely removed.
- "autostretch" and "nr_of_columns" options are now per-screen configuration options.
- Installer has been updated to request the user to preserve his current configuration file.

