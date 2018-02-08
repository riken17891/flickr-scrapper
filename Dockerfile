FROM ubuntu:16.04

MAINTAINER Riken Patel riken17891@gmail.com

ADD . /flickr-scrapper

# install python and pip
RUN apt-get update
RUN apt-get install -y software-properties-common vim
RUN add-apt-repository ppa:jonathonf/python-3.6
RUN apt-get update

RUN apt-get install -y python3.6 python3.6-dev python3-pip

# Install Requirements
RUN python3.6 -m pip install -r /flickr-scrapper/requirements.txt

RUN apt-get -y install libxss1 libappindicator1 libindicator7 wget
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN dpkg -i google-chrome-stable_current_amd64.deb; apt-get -fy install

RUN apt-get -y install xvfb unzip supervisor

RUN wget -N http://chromedriver.storage.googleapis.com/2.32/chromedriver_linux64.zip
RUN unzip chromedriver_linux64.zip
RUN ["chmod", "+x", "chromedriver"]

RUN mv -f chromedriver /usr/local/share/chromedriver
RUN ln -s /usr/local/share/chromedriver /usr/local/bin/chromedriver
RUN ln -s /usr/local/share/chromedriver /usr/bin/chromedriver

ENV PYTHONPATH /flickr-scrapper/scrapper

ENTRYPOINT ["/usr/bin/supervisord", "-c", "/flickr-scrapper/supervisord.conf"]