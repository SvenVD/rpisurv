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
echo
echo "Do you want to continue press <Enter>, Ctrl-C to cancel"
read

get_init_sys
BASEPATH="$(cd $(dirname "${BASH_SOURCE[0]}");pwd)"

#Install needed packages
sudo apt-get install coreutils python-pygame python-yaml python-dbus python libraspberrypi-bin -y

#Only install omxplayer if it isn't already installed (from source or package)
if [ ! -e /usr/bin/omxplayer ];then
 sudo apt-get install omxplayer -y
else
 echo "Omxplayer install detected, not reinstalling"
fi

#Prevent starting up in graphical mode, we do not need this -> save resources
if [ $SYSTEMD -eq 1 ]; then
  sudo systemctl set-default multi-user.target
  #enable systemd-timesyncd
  sudo timedatectl set-ntp true

else
  [ -e /etc/init.d/lightdm ] && update-rc.d lightdm disable
  #Enable timesync
  TIMESYNCCMD="/usr/sbin/service ntp stop 2>/dev/null 1>&2; /usr/sbin/ntpdate 0.debian.pool.ntp.org 2>/dev/null 1>&2; /usr/sbin/service ntp start 2>/dev/null 1>&2"
  if ! grep -q "^$TIMESYNCCMD" /etc/rc.local ;then
          sudo echo "$TIMESYNCCMD" >> /etc/rc.local

  fi
fi

SOURCEDIR="$BASEPATH/surveillance"
MAINSOURCE="surveillance.py"
CONFFILE="conf/surveillance.yml"
BACKUPCONFFILE=/tmp/surveillance.yml.$(date +%Y%m%d_%s)



DESTPATH="/usr/local/bin/rpisurv"
sudo mkdir -p "$DESTPATH"

if [ -f "$DESTPATH/$CONFFILE" ]; then sudo cp -v "$DESTPATH/$CONFFILE" "${BACKUPCONFFILE}";fi
echo
echo "Existing config file will be backed up to "${BACKUPCONFFILE}""


echo
echo "Do you want to overwrite you current config file with the example config file?"
echo "Newer major versions of rpisurv are not backwards compatible with old format of config file"
echo "Type yes/no"
read ANSWER

sudo rsync -av "$SOURCEDIR/" "$DESTPATH/"

if [ x"$ANSWER" == x"no" ]; then
    #Putting back old config file
    if [ -f "${BACKUPCONFFILE}" ]; then sudo cp -v "${BACKUPCONFFILE}" "$DESTPATH/$CONFFILE" ; fi
fi

STARTUPCMD="cd $DESTPATH; python "$MAINSOURCE" &"

if [ $SYSTEMD -eq 1 ]; then
    #Remove old way of starting rpisurv
    sudo sed -i /$MAINSOURCE/d /etc/rc.local
    sudo cp -v rpisurv /usr/bin/
    sudo chmod 700 /usr/bin/rpisurv
    sudo cp -v rpisurv.service /etc/systemd/system/
    sudo chmod 644 /etc/systemd/system/rpisurv.service
    sudo systemctl daemon-reload
    sudo systemctl enable rpisurv
else
    #No systemd detected use old method to start
    if ! grep -q "^$STARTUPCMD" /etc/rc.local ;then
        #Filter out exit 0 command if present
        sudo sed -i '/exit 0$/d' /etc/rc.local
        sudo echo "$STARTUPCMD" >> /etc/rc.local
        #Add exit 0 as last line for good practise
        sudo echo  "exit 0" >> /etc/rc.local
    fi
fi
#Link config file into /etc as convenient way to edit
sudo ln -fs $DESTPATH/"$CONFFILE" /etc/rpisurv
