#!/bin/bash

if [ ! "$BASH_VERSION" ] ; then
    echo "ERROR: Please use bash not sh or other shells to run this installer. You can also run this script directly like ./install.sh"
    exit 1
fi


get_init_sys() {
  if command -v systemctl > /dev/null && systemctl | grep -q '\-\.mount'; then
    SYSTEMD=1
  elif [ -f /etc/init.d/cron ] && [ ! -h /etc/init.d/cron ]; then
    SYSTEMD=0
  else
    echo "Unrecognised init system"
    return 1
  fi
}


echo "Use this installer on your own risk. Make sure this host does not contain important data and is replacable"
echo "This installer will disable graphical login on your pi, please revert with the raspi-config command if needed"
echo "Do you want to continue press <Enter>, Ctrl-C to cancel"
read


get_init_sys
BASEPATH="$(cd $(dirname "${BASH_SOURCE[0]}");pwd)"

#Install needed packages
apt-get install python-yaml python libraspberrypi-bin -y

#Only install omxplayer if it isn't already installed (from source or package)
if [ ! -e /usr/bin/omxplayer ];then
 apt-get install omxplayer -y
else
 echo "Omxplayer install detected, not reinstalling"
fi

#Prevent starting up in graphical mode, we do not need this -> save resources
if [ $SYSTEMD -eq 1 ]; then
	systemctl set-default multi-user.target
	#enable systemd-timesyncd
	timedatectl set-ntp true

else
	[ -e /etc/init.d/lightdm ] && update-rc.d lightdm disable
	#Enable timesync
	TIMESYNCCMD="/usr/sbin/service ntp stop 2>/dev/null 1>&2; /usr/sbin/ntpdate 0.debian.pool.ntp.org 2>/dev/null 1>&2; /usr/sbin/service ntp start 2>/dev/null 1>&2"
	if ! grep -q "^$TIMESYNCCMD" /etc/rc.local ;then
        	echo "$TIMESYNCCMD" >> /etc/rc.local

	fi
fi

SOURCEDIR="$BASEPATH/surveillance"
MAINSOURCE="surveillance.py"
CONFFILE="conf/surveillance.yml"


DESTPATH="/usr/local/bin/rpisurv"
mkdir -p "$DESTPATH"

rsync -av "$SOURCEDIR/" "$DESTPATH/"

#Filter out exit 0 command if present
sed -i '/exit 0$/d' /etc/rc.local

STARTUPCMD="cd $DESTPATH; python "$MAINSOURCE" &"
if ! grep -q "^$STARTUPCMD" /etc/rc.local ;then
	echo "$STARTUPCMD" >> /etc/rc.local

fi

#Link config file into /etc as convenient way to edit
ln -fs $DESTPATH/"$CONFFILE" /etc/rpisurv

#Add exit 0 as last line for good practise
echo  "exit 0" >> /etc/rc.local
