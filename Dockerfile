FROM debian:buster

# install apt dependencies
RUN apt-get update -y
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y locales chromium=90.0.4430.212-1~deb10u1 chromium-driver=90.0.4430.212-1~deb10u1 python3 python3-pip python-websockify git xorg vnc4server autocutsel lxde-core novnc
RUN pip3 install --upgrade pip

RUN sed -i -e 's/# de_DE.UTF-8 UTF-8/de_DE.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales && \
    update-locale LANG=de_DE.UTF-8

ENV LANG de_DE.UTF-8 

WORKDIR /app

ENV VACCIPY_CHROMEDRIVER="/usr/bin/chromedriver"

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

# setup vnc
RUN echo "# XScreenSaver Preferences File\nmode:		off\nselected:  -1" > /root/.xscreensaver && \
  cat /root/.xscreensaver && mkdir /root/.vnc/ && \
  echo "#!/bin/sh\n/usr/bin/autocutsel -s CLIPBOARD -fork\nxrdb $HOME/.Xresources\nxsetroot -solid grey\n#x-terminal-emulator -geometry  80x24+10+10 -ls -title \"$VNCDESKTOP Desktop\" &\n#x-window-manager &\n# Fix   to make GNOME work\nexport XKL_XMODMAP_DISABLE=1\n/etc/X11/Xsession  &\nx-terminal-emulator -e \"python3 /app/main.py search -r -d -f /app/kontaktdaten.json 2>&1 | tee  /app/vaccipy\"" > /root/.vnc/xstartup && \
  chmod +x /root/.vnc/xstartup && \
  cat /root/.vnc/xstartup && \
  mv /usr/share/novnc/vnc.html /usr/share/novnc/index.html && \
  echo "#!/bin/bash\nsetxkbmap -option lv3:rwin_switch\necho -n \${VNC_PASSWORD:-vaccipy} | vncpasswd -f > /root/.vnc/passwd\nchmod 400 ~/.vnc/passwd\n\nexport USER=root\nvncserver -localhost no :1 -geometry 1920x1080 -depth 24 -rfbport \${VNC_PORT:-5901} && websockify -D --web=/usr/share/novnc/ \${WEB_PORT:-6901}  localhost:\${VNC_PORT:-5901} \ntail -f /app/vaccipy" > /root/vnc-startup.sh && \
  chmod +x /root/vnc-startup.sh && \
  cat /root/vnc-startup.sh && \
  chmod go-rwx /root/.vnc 

# copy whole folder into container
COPY . .

CMD ["/root/vnc-startup.sh"]
