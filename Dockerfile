FROM selenium/standalone-chrome:4.0.0-rc-1-prerelease-20210804

# Selenium img has Selusr as user we need root to add packages
USER root
RUN apt-get update --fix-missing && apt-get -y upgrade
RUN apt install python3-pip -y
RUN apt-get install software-properties-common -y

#Install Cron
RUN apt-get update
RUN apt-get -y install cron
# Add crontab file in the cron directory
COPY seluser /var/spool/cron/crontabs/seluser

# Give execution rights on the cron job
# RUN chmod 0644 /etc/cron.d/clean-cron
# If you're adding a script file and telling cron to run it, remember to
# RUN chmod 0744 /the_script

# Run the command on container startup
# CMD cron && tail -f /var/log/cron.log

# Supervisor runs different applications for ScraFi to work
RUN apt-get update && apt-get install -y supervisor
RUN mkdir -p /var/log/supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Some mods need tesseract to read images text
RUN apt-get install pkg-config -y
RUN apt-get install libpng-dev -y
RUN apt-get install libjpeg8-dev -y
RUN apt-get install libtiff5-dev -y
RUN apt-get install vim -y
RUN apt install tesseract-ocr -y
RUN pip install Pillow
RUN pip install pytesseract
RUN pip install numpy

# Adding english for tesseract to work properly
COPY eng.traineddata /usr/share/tesseract-ocr/4.00/tessdata

COPY Logs /home/seluser/scrafi_project/Logs
COPY supervizor /home/seluser/scrafi_project/supervizor

# Creating app directory and adding requirements 
# **TODO : delete requirements we no longer need
WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Selenium and chromedriver if basic image isn't selenium standalone
# RUN pip install selenium
# RUN pip install chromedriver

# Adding Xvfb for selenium to work properly
RUN apt-get install -y xvfb
RUN pip install xvfbwrapper

# Copying woob with our mods and adding them 
# to sources list for woob to recongnize them
COPY ScraFi /home/seluser/scrafi_project/ScraFi
RUN pip install -e /home/seluser/scrafi_project/ScraFi
RUN woob update
RUN echo "file:///home/seluser/scrafi_project/ScraFi/modules" >> /home/seluser/.config/woob/sources.list
RUN woob update
RUN pip install prettytable

# Dowloading redis and installing it
RUN add-apt-repository ppa:redislabs/redis -y
RUN apt-get update
RUN apt-get install redis -y
RUN pip install rq

# Copying Django api app (No install needed because already in requirements)
COPY API /home/seluser/scrafi_project/API
RUN pip install django-oauth-toolkit
RUN pip install django-cors-headers
RUN pip install discord.py
RUN python3 /home/seluser/scrafi_project/API/manage.py migrate

# ngrok install
# RUN apt-get update
# RUN apt-get install unzip wget
# RUN wget https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-amd64.zip
# RUN unzip ngrok-stable-linux-amd64.zip
# RUN mv ./ngrok /usr/bin/ngrok

# pyngrok to use django with ngrok
# RUN pip install pyngrok

CMD ["/usr/bin/supervisord"]

# RUN export PATH="/home/zhor/.local/bin:$PATH"