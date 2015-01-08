# spotify-ripper

A fork of [spotify-ripper](https://github.com/robbeofficial/spotifyripper) that uses [pyspotify](https://github.com/mopidy/pyspotify) v2.x

Spotify-ripper is a small ripper script for Spotify that rips playlists and track URIs to MP3 files and includes ID3 tags.

**Note that stream ripping violates the libspotify's ToS**

## Usage

```shell
usage: ripper.py [-h] [-u USER] [-p PASSWORD] [-l] [-m] uri

rips Spotify URIs to mp3s with ID3 tags and album covers

positional arguments:
  uri                   Spotify URI (either track or playlist)

optional arguments:
  -h, --help            show this help message and exit
  -u USER, --user USER  Spotify username
  -p PASSWORD, --password PASSWORD
                        Spotify password
  -l, --last            Use last login credentials
  -m, --pcm             Saves a .pcm file with the raw PCM data
```

## Examples

```bash
./ripper.py -u user -p password spotify:track:52xaypL0Kjzk0ngwv3oBPR # creates "Beat It.mp3" file
./ripper.py -l spotify:user:[user]:playlist:7HC9PMdSbwGBBn3EVTaCNx # rips entire playlist
```

## Features

* real-time VBR ripping from spotify PCM stream

* writes id3 tags (including album covers)

* creates files and directories based on the following structure artist/album/song.mp3

## Installation

### Prerequisites

* [libspotify](https://developer.spotify.com/technologies/libspotify)

* [pyspotify](https://github.com/mopidy/pyspotify)

* a Spotify binary [app key](https://devaccount.spotify.com/my-account/keys/) (spotify_appkey.key)

* [lame](http://lame.sourceforge.net)

* [eyeD3](http://eyed3.nicfit.net)

### Mac OS X

Recommend approach uses [homebrew](http://brew.sh/) and [pyenv](https://github.com/yyuu/pyenv)

```bash
$ git clone https://github.com/jrnewell/spotify-ripper.git
$ cd spotify-ripper
$ brew install homebrew/binary/libspotify
$ sudo ln -s /usr/local/opt/libspotify/lib/libspotify.12.1.51.dylib \
    /usr/local/opt/libspotify/lib/libspotify
$ pip install --pre pyspotify
$ brew install lame
$ pip install eyeD3 --allow-external eyeD3 --allow-unverified eyeD3
$ pyenv rehash
```

Download an application key file `spotify_appkey.key` from `https://devaccount.spotify.com/my-account/keys/` (requires a Spotify Premium Account) and move to the `spotify-ripper` directory.

### Ubuntu/Debian

Recommend approach uses [pyenv](https://github.com/yyuu/pyenv)

```bash
$ git clone https://github.com/jrnewell/spotify-ripper.git
$ cd spotify-ripper
$ sudo apt-get install lame build-essential libffi-dev
$ wget https://developer.spotify.com/download/libspotify/libspotify-12.1.51-Linux-x86_64-release.tar.gz # (assuming 64-bit)
$ cd libspotify-12.1.51-Linux-x86_64-release/
$ sudo make install prefix=/usr/local
$ cd ..
$ pip install --pre pyspotify
$ pip install eyeD3 --allow-external eyeD3 --allow-unverified eyeD3
$ pyenv rehash
```

Download an application key file `spotify_appkey.key` from `https://devaccount.spotify.com/my-account/keys/` (requires a Spotify Premium Account) and move to the `spotify-ripper` directory.

## License

[MIT License](http://en.wikipedia.org/wiki/MIT_License)
