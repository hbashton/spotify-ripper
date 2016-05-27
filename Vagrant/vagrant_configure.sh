#!/bin/sh

# This file includes all operations to create a working instance of spotify-ripper

# Install encoding
sudo apt-get install language-pack-UTF-8

# Add respository
sudo apt-add-repository multiverse

# Update apt-get
sudo apt-get update

#Install required packages
apt-get -y install lame build-essential libffi-dev python-pip libffi-dev libssl-dev python-dev flac libav-tools faac libfdk-aac-dev automake autoconf vorbis-tools opus-tools

# Install MP4/M4A (need to compile fdkaac from source)
wget https://github.com/nu774/fdkaac/archive/v0.6.2.tar.gz
tar xvf v0.6.2.tar.gz
cd fdkaac-0.6.2
autoreconf -i
./configure
make install

# Install libspotify
wget https://developer.spotify.com/download/libspotify/libspotify-12.1.51-Linux-x86_64-release.tar.gz
tar xvf libspotify-12.1.51-Linux-x86_64-release.tar.gz
cd libspotify-12.1.51-Linux-x86_64-release/
make install prefix=/usr/local

# Workaround for issue #214
pip uninstall spotify-ripper
pip install --upgrade pip
export CONFIGURE_OPTS="--enable-unicode=ucs4"
pyenv install 3.5.1
pyenv local 3.5.1
pyenv global 3.5.1

# Install spotify-ripper
pip install spotify-ripper

# Create directories
mkdir /home/vagrant/.spotify-ripper
mkdir /vagrant/Music

# Copy config-file
file="/vagrant/Settings/config.ini"
if [ -f "$file" ]
then
	echo "$file found. Linking file to ~/.spotify-ripper"
	ln -s "$file" /home/vagrant/.spotify-ripper/config.ini	
else
	echo "$file not found."
fi

# Copy spotify-key
file2="/vagrant/Settings/spotify_appkey.key"
if [ -f "$file2" ]
then
	echo "$file2 found. Linking file to ~/.spotify-ripper"
	ln -s "$file2" /home/vagrant/.spotify-ripper/spotify_appkey.key
	
else
	echo "$file2 not found. You need a spotify developer key to transcode pcm stream."
	echo "Please copy your spotify_appkey.key to your shared host directory /vagrant/Settings/"
fi

# final feedback
echo "Voila - Run 'vagrant ssh' to access your virtual box"
echo "After that you should able to download songs"
echo "e.g. spotify-ripper spotify:track:4txn9qnwK3ILQqv5oq2mO3"
echo "Have Fun!"