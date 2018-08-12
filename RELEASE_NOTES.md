# rpisurv 2.0.beta1 release notes
## Upgrade notes from 1.0
The config file is still a yaml file but the keys have been changed to support the configuration of multiple screen in a rotation
You must manually convert your 1.0 config file to the new 2.0 config file format. However the format is still as clear to use, but it is still a yaml file. So as always watch the indentations and do not use tabs, see [example config file](https://github.com/SvenVD/rpisurv/blob/v2.0_branch/surveillance/conf/surveillance.yml)
The normal update [procedure](https://github.com/SvenVD/rpisurv/blob/v2.0_branch/README.md#how-to-update) can be followed for upgrading.

## Features and changes since 1.0
- Implemented "Automatic cycle through list of cameras/screens" [link](https://feathub.com/SvenVD/rpisurv/+4).
- Pressing keys F1 to F12 on an attached keyboard, will force the equal numbered screen to be shown onscreen (this takes longer depending on amount of unconnectable streams and they thus need to wait for timeout, keep holding until screen changes. Note, you can change probe_timeout per camera stream if needed). Example use case: you can define one '4x4' screen and 4 1x1 screens with the same camera streams. That way you can select one camera stream out of the 4x4 by pressing F2-F5 and go back to 4x4 by pressing F1 [link](https://feathub.com/SvenVD/rpisurv/+3).
- Disable rotation (as in pause rotation, as in fix the current displayed screen) dynamically during runtime. Press "p" to pause and "r" to resume/rotate. This overrides the disable_autorotation option if this has been set in the config file.
- There is virtually no limit(hardware or software) for the amount of screens that can be defined.
- Implemented "Add mjpeg camera support" [link](https://feathub.com/SvenVD/rpisurv/+5) but not limited to mjpeg support, all omxplayer supported http/https streams can be configured.
- Possibility to force next screen in a carousel/slideshow by pressing "n" or "space" on an attached keyboard.
- Enabling the user to configure the duration of each screen in the carousel/slideshow by overriding the default with the "duration" option, see [example config file](https://github.com/SvenVD/rpisurv/blob/v2.0_branch/surveillance/conf/surveillance.yml).
- Enabling the user to specify a "probe_timeout" per camera stream. This for slow connecting streams to not be regarded as unconnectable by rpisurv, see [example config file](https://github.com/SvenVD/rpisurv/blob/v2.0_branch/surveillance/conf/surveillance.yml).
- "keep_first_screen_layout" option in v1.0 has been replaced by "disable_probing_for_all_streams" option in v2.0 and has become a per screen configuration, which effect is roughly the same. (Not recommended to enable this though).
- All existing functionality from v1.0 is still available. If you only define one screen you essentially get the rpisurv v1.0 behaviour.
- rtps_urls config option which was already deprecated in v1.0 is now completely removed.
- "autostretch" and "nr_of_columns" options are now per-screen configuration options.
- Installer has been updated to request the user to preserve his current configuration file.

