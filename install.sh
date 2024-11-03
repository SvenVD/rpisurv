#!/bin/bash

if [ ! "$BASH_VERSION" ] ; then
    echo "ERROR: Please use bash not sh or other shells to run this installer. You can also run this script directly like ./install.sh"
    exit 1
fi

show_version() {
    grep fullversion_for_installer "$BASEPATH/surveillance/surveillance.py" | head -n 1 | cut -d"=" -f2
}

configure_lightdm() {
  echo '[Seat:*]
#Hide mouse cursor
greeter-setup-script=/usr/bin/unclutter -idle 2 -root
autologin-user=rpisurv
#autologin-session=xfce
autologin-session=rpisurv
autologin-user-timeout=0' > /etc/lightdm/lightdm.conf
}

if [ "$(id -u)" -ne 0 ];then echo "ABORT, run this installer as the root user (sudo ./install.sh)"; exit 2; fi


BASEPATH="$(cd $(dirname "${BASH_SOURCE[0]}");pwd)"

echo "Use this installer on your own risk. Make sure this host does not contain important data and is replacable"
echo "This installer will configure to boot directly into Rpisurv"
echo
echo -n "The following version will be installed:"
show_version
echo
echo "Do you want to continue press <Enter>, <Ctrl-C> to cancel"
read

#Install needed packages
apt update
apt install xdotool mpv xfce4 python3-pygame python3-xlib ffmpeg wmctrl unclutter -y

#Configure user and autologin
useradd -m rpisurv -s /bin/bash
configure_lightdm

DESTPATH="/home/rpisurv"
mkdir -pv "$DESTPATH"/{etc,lib,logs,bin}

SOURCEDIR="$BASEPATH/surveillance"
CONFDIR="etc"
BACKUPCONFDIR=/tmp/backup_rpisurv_config_$(date +%Y%m%d_%s)

if [ -d "$DESTPATH/${CONFDIR}" ];then
   echo
   echo "Existing config dir will be backed up to "${BACKUPCONFDIR}""
   cp -arv "$DESTPATH/${CONFDIR}" "${BACKUPCONFDIR}"

   echo
   echo "Do you want to overwrite your current config files with the example config files?"
   echo "Type yes/no"
   read USEEXAMPLECONFIG
else
   USEEXAMPLECONFIG="yes"
fi

if [ -d /home/rpisurv/images ];then
   echo
   echo "Do you want to overwrite you current images directory (/home/rpisurv/images) with the images from the installer?"
   echo "Type yes/no"
   read OVERWRITESIMAGES
else
   OVERWRITESIMAGES="yes"
fi

echo
echo "Do you want me to (re-)start rpisurv after install?"
echo "Type yes/no"
read ANSWERSTART

if [ x"$OVERWRITESIMAGES" == x"yes" ]; then
  rsync -av "$SOURCEDIR/images/" "$DESTPATH/lib/images/"
fi
if [ x"$USEEXAMPLECONFIG" == x"yes" ]; then
    rsync -av "$SOURCEDIR/etc/" "$DESTPATH/etc/"
    rsync -av "$SOURCEDIR/demo" "$DESTPATH/lib/"
fi
rsync -av "$SOURCEDIR/core" "$DESTPATH/lib/"
rsync -av "$SOURCEDIR/surveillance.py" "$DESTPATH/lib/"
rsync -av rpisurv "$DESTPATH/bin/"
rsync -av rpisurv.desktop "/usr/share/xsessions/"

chown -Rc rpisurv.rpisurv /home/rpisurv

#Link config file dir into /etc as convenient way to edit
if [ ! -L /etc/rpisurv ]; then
  ln -fsv "$DESTPATH/$CONFDIR" /etc/rpisurv
fi

if [ ! -f /home/rpisurv/firstinstall_DONE ];then
  #We use lightdm, do not let gdm3 be in our way
  apt remove gdm3
  touch /home/rpisurv/firstinstall_DONE
  echo "This is first install we need to reboot"
  echo "For reboot press <Enter>"
  read
  reboot
fi

if [ x"$ANSWERSTART" == x"yes" ]; then
    systemctl restart lightdm
fi

