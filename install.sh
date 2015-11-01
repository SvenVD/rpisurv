#!/bin/bash

echo "Use this installer on your own risk. Make sure this host does not contain important data and is replacable"
echo "Do you want to continue press <Enter>, Ctrl-C to cancel"
read

BASEPATH="$(cd $(dirname "${BASH_SOURCE[0]}");pwd)"

#Install needed packages
apt-get install python-yaml python

#Only install omxplayer if it isn't already installed (from source or package)
if [ ! -e /usr/bin/omxplayer ];then
 apt-get install omxplayer
else
 echo "Omxplayer install detected, not reinstalling"
fi

#Prevent starting up in graphical mode, we do not need this -> save resources
update-rc.d lightdm disable

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
