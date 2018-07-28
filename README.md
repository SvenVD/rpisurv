# rpisurv - Raspberry pi surveillance an RPI IP Camera Monitor
Follow us on facebook https://www.facebook.com/rpisurv

If you like this software please consider donating:
 <a href="https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=QPJU9K2KZ8D94" target="_blank" rel="nofollow"><img src="https://www.paypal.com/en_US/i/btn/x-click-but21.gif" alt="" /></a>

## Goal
Rpisurv is designed to be simple to use. The goal is to connect your raspberry pi to a monitor, tell rpisurv which rtsp streams it should display and tell it the max number of "columns" of streams you want. It will then autocalculate the rest, like how many rows are needed etc ...

## Description
You can think of rpisurv as a wrapper for omxplayer with following features. Rpisurv uses omxplayer to fully make use of the GPU of the raspberry pi.

- Rpisurv implements a watchdog for every stream displayed, if the process gets killed somehow. It will try to restart the stream/process. This gives you a very robust surveillance screen.
- Autocalculcate coordinates for every stream displayed. The last stream defined will be stretched to make use of the complete screen but only if some pixels are unused (if autostretch option is True).
- RTSP stream up/down detection and autorearrange of the screen layout. So for example if you stop a camera (or just stop the rtsp server on the camera), rpisurv will detects this and will recalculate/redraw the screen with the still available cameras. The same is true if a previous unconnectable rtsp stream becomes connectable. All without any user interaction.

## How to get started

- Get a monitor or a TV
- Get a raspberry pi dedicated for rpisurv, and install raspbian on it. Make sure your monitor is operating at the correct resolution
- If you are going to have multiple streams, add gpu_mem=512 to your /boot/config.txt
- git clone this repository: `git clone https://github.com/SvenVD/rpisurv`
- move into folder `cd rpisurv`
- run `sudo ./install.sh`
- Get the correct rtsp stream url for your ip camera(s), there are some examples in /etc/rpisurv
- configure your rtsp streams in /etc/rpisurv ( do NOT use tabs in this file, only use spaces! ).
- configure your max number of columns in /etc/rpisurv
- reboot

## How to update
- save your config:
  `cp -v /usr/local/bin/rpisurv/conf/surveillance.yml /usr/local/bin/rpisurv/conf/surveillance.yml.back_update`
- `cd rpisurv; git pull`
- run `sudo ./install.sh`
- restore your config:
  `cp -v /usr/local/bin/rpisurv/conf/surveillance.yml.back_update /usr/local/bin/rpisurv/conf/surveillance.yml`
- `sudo systemctl restart rpisurv`

## Placeholder images
After installation you may change the placeholder images to something you like.
- /usr/local/bin/rpisurv/images/connecting.png is shown when a camera stream is starting up
- /usr/local/bin/rpisurv/images/placeholder.png is shown on empty squares
- /usr/local/bin/rpisurv/images/noconnectable.png is shown full screen when no connectable streams are detected
- `sudo systemctl restart rpisurv`

## Rpisurv in operation

If you used the install.sh script, you can configure your streams in /etc/rpisurv. Do not forget to reboot afterwards.

## Troubleshooting

- I advise you to test your rtsp urls in vlc or omxplayer (command line) first. It should work in these applications before attempting to use them in rpisurv

- If you used the install.sh script, logs are created at /usr/local/bin/rpisurv/logs/. You can use them for troubleshooting.

- If you are connected via keyboard, you can stop rpisurv by pressing q for about 25 seconds.

- To manage the screen without rebooting use systemctl
  - `sudo systemctl stop rpisurv` to stop the screen
  - `sudo systemctl start rpisurv` to start the screen
  - `sudo systemctl status rpisurv` to see last log and status of service
- DEPRECATED: To start the screen without rebooting on non systemd enabled raspbian, run `cd /usr/local/bin/rpisurv; sudo python surveillance.py`

- If you want to stream rtsp over tcp please add `rtsp_over_tcp: true` to the stream in /etc/rpisurv.
  See https://github.com/SvenVD/rpisurv/blob/master/surveillance/conf/surveillance.yml for an example.
  If you have a "smearing" effect this option may resolve it.
  Note that you need a version of omxplayer which is released afer 14 March 2016 (https://github.com/popcornmix/omxplayer/pull/433) to do this.

- On a raspberry pi 3 it seems the default overscan settings are not good. If full screen is not used, if you have an unused bar in the bottom -> try to set `disable_overscan=1` in /boot/config.txt

## Feature requests

Feature requests are tracked on https://feathub.com/SvenVD/rpisurv. If you would like to have a feature implemented on rpisurv, please check that this is not already been requested on feathub. If it is then add your vote to it, if it is not then request it as a new feature. The votes give us an indication on how feature requests compare to each other regarding popularity.
