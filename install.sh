#!/bin/bash

if [ ! "$BASH_VERSION" ] ; then
    echo "ERROR: Please use bash not sh or other shells to run this installer. You can also run this script directly like ./install.sh"
    exit 1
fi

show_version() {
    grep fullversion_for_installer "$BASEPATH/surveillance/surveillance.py" | head -n 1 | cut -d"=" -f2
}
get_init_sys() {
  if command -v systemctl > /dev/null && systemctl | grep -q '\-\.mount'; then
    SYSTEMD=1
  elif [ -f /etc/init.d/cron ] && [ ! -h /etc/init.d/cron ]; then
    SYSTEMD=0
  else
    echo "Unrecognized init system"
    return 1
  fi
}

is_vlc_mmal_present() {
 sed -i 's/geteuid/getppid/' /usr/bin/vlc
 if /usr/bin/vlc -H  2>/dev/null | grep -q -- '--mmal-layer';then
    return 0
 else
    return 1
 fi
}

get_init_sys
BASEPATH="$(cd $(dirname "${BASH_SOURCE[0]}");pwd)"

echo "Use this installer on your own risk. Make sure this host does not contain important data and is replacable"
echo "This installer will disable graphical login on your pi, please revert with the raspi-config command if needed."
echo
echo -n "The following version will be installed:"
show_version
echo
#echo "By using this software, you agree that by default limited and non-sensitive (runtime, unique id and version) stats"
#echo "will be sent on a regular interval to a collector server over an encrypted connection."
#echo "You can disable this anytime by changing the update_stats: config option to False."
#echo "This has been introduced to get an idea of how much users are testing a beta version of the software."
#echo "Once the software comes out of beta, stats sending will be disabled by default."
#echo
echo "Do you want to continue press <Enter>, <Ctrl-C> to cancel"
read




#Install needed packages
sudo apt update
sudo apt remove vlc -y
sudo apt install xdg-utils rsync sed coreutils fbset ffmpeg openssl procps python3-pygame python3-yaml python3-openssl python3 libraspberrypi-bin -y

#Download debs for vlc
mkdir -p /tmp/rpisurv
cd /tmp/rpisurv/
echo -e "http://archive.raspbian.com/raspbian/pool/main/v/vlc/vlc-data_3.0.12-0%2Bdeb9u1_all.deb\nhttp://archive.raspbian.com/raspbian/pool/main/v/vlc/libvlc-bin_3.0.12-0%2Bdeb9u1_armhf.deb\nhttp://archive.raspbian.com/raspbian/pool/main/v/vlc/vlc-l10n_3.0.12-0%2Bdeb9u1_all.deb\nhttp://archive.raspbian.com/raspbian/pool/main/v/vlc/vlc-plugin-notify_3.0.12-0%2Bdeb9u1_armhf.deb\nhttp://archive.raspbian.com/raspbian/pool/main/v/vlc/vlc-plugin-samba_3.0.12-0%2Bdeb9u1_armhf.deb\nhttp://archive.raspbian.com/raspbian/pool/main/v/vlc/vlc-plugin-skins2_3.0.12-0%2Bdeb9u1_armhf.deb\nhttp://archive.raspbian.com/raspbian/pool/main/v/vlc/vlc-plugin-video-splitter_3.0.12-0%2Bdeb9u1_armhf.deb\nhttp://archive.raspbian.com/raspbian/pool/main/v/vlc/vlc-plugin-visualization_3.0.12-0%2Bdeb9u1_armhf.deb\nhttp://archive.raspbian.com/raspbian/pool/main/v/vlc/vlc-bin_3.0.12-0%2Bdeb9u1_armhf.deb\nhttp://archive.raspbian.com/raspbian/pool/main/v/vlc/vlc-plugin-base_3.0.12-0%2Bdeb9u1_armhf.deb\nhttp://archive.raspbian.com/raspbian/pool/main/v/vlc/vlc-plugin-qt_3.0.12-0%2Bdeb9u1_armhf.deb\nhttp://archive.raspbian.com/raspbian/pool/main/v/vlc/vlc-plugin-video-output_3.0.12-0%2Bdeb9u1_armhf.deb\nhttp://archive.raspbian.com/raspbian/pool/main/v/vlc/vlc_3.0.12-0%2Bdeb9u1_armhf.deb" > /tmp/rpisurv/vlc.txt
wget -i /tmp/rpisurv/vlc.txt
sudo dpkg -i /tmp/rpisurv/*.deb
#sudo apt-get install -f
sudo apt-mark hold vlc vlc-bin vlc-plugin-base vlc-plugin-qt vlc-plugin-video-output vlc-l10n vlc-plugin-notify vlc-plugin-samba vlc-plugin-skins2 vlc-plugin-video-splitter vlc-plugin-visualization libvlc-bin vlc-data
cd "$BASEPATH"
rm -rdf /tmp/rpisurv/

if ! is_vlc_mmal_present;then
    echo "Your version of vlc does not have the needed mmal options. Rpisurv needs those"
    echo "Minimum tested vlc version for Rpisurv is (VLC media player 3.0.12 Vetinari (revision 3.0.12-1-0-gd147bb5e7e)"
    echo "Aborting installation, upgrade to latest vlc player with mmal support"
    exit 2
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
CONFDIR="conf"
BACKUPCONFDIR=/tmp/backup_rpisurv3config_$(date +%Y%m%d_%s)


DESTPATH="/usr/local/bin/rpisurv"
sudo mkdir -p "$DESTPATH"

if [ -d "$DESTPATH/${CONFDIR}" ];then
   echo
   echo "Existing config dir will be backed up to "${BACKUPCONFDIR}""
   sudo cp -arv "$DESTPATH/${CONFDIR}" "${BACKUPCONFDIR}"

   echo
   echo "Do you want to overwrite your current config files with the example config files?"
   echo "Type yes/no"
   read USEEXAMPLECONFIG
else
   USEEXAMPLECONFIG="yes"
fi

if [ -d /usr/local/bin/rpisurv/images/ ];then
   echo
   echo "Do you want to overwrite you current images directory (/usr/local/bin/rpisurv/images/) with the images from the installer?"
   echo "Type yes/no"
   read OVERWRITESIMAGES
else
   OVERWRITESIMAGES="yes"
fi

echo
echo "Do you want me to (re-)start rpisurv after install?"
echo "Type yes/no"
read ANSWERSTART

if [ x"$OVERWRITESIMAGES" == x"no" ]; then
    RSYNCOPTIONS="${RSYNCOPTIONS} --exclude /images"
fi

if [ x"$USEEXAMPLECONFIG" == x"no" ]; then
    RSYNCOPTIONS="${RSYNCOPTIONS} --exclude /conf"
fi

sudo rsync -av $RSYNCOPTIONS "$SOURCEDIR/" "$DESTPATH/"

#Make sure pngview is executable by root
sudo chmod 770 "${DESTPATH}"/bin/pngview


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
#Link config file dir into /etc as convenient way to edit
if [ -f /etc/rpisurv ]; then sudo rm -fv /etc/rpisurv;fi
sudo ln -fs $DESTPATH/"$CONFDIR" /etc/rpisurv

if [ x"$ANSWERSTART" == x"yes" ]; then
    sudo systemctl restart rpisurv
fi
