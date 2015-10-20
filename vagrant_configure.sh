#!/bin/sh

sudo apt-add-repository multiverse
sudo apt-get update
sudo apt-get -y install lame build-essential libffi-dev python-pip libffi-dev libssl-dev python-dev flac libav-tools faac libfdk-aac-dev automake autoconf vorbis-tools opus-tools
# MP4/M4A (need to compile fdkaac from source)
wget https://github.com/nu774/fdkaac/archive/v0.6.2.tar.gz
tar xvf v0.6.2.tar.gz
cd fdkaac-0.6.2
autoreconf -i
./configure
sudo make install
# Install libspotify
wget https://developer.spotify.com/download/libspotify/libspotify-12.1.51-Linux-x86_64-release.tar.gz
tar xvf libspotify-12.1.51-Linux-x86_64-release.tar.gz
cd libspotify-12.1.51-Linux-x86_64-release/
sudo make install prefix=/usr/local
# Install spotify-ripper
sudo -H pip install spotify-ripper
