# spotify-ripper

A fork of [spotify-ripper](https://github.com/robbeofficial/spotifyripper) that uses [pyspotify](https://github.com/mopidy/pyspotify) v2.x

Spotify-ripper is a small ripper script for Spotify that rips Spotify URIs to MP3 files and includes ID3 tags and cover art.

**Note that stream ripping violates the libspotify's ToS**

## Features

* real-time VBR or CBR ripping from spotify PCM stream

* writes id3 tags (including album covers)

* creates files and directories based on the following structure artist/album/artist - song.mp3

* optionally skip existing files

* accepts tracks, playlists, albums, and artist URIs

* search for tracks using Spotify queries

* options for interactive login (no password in shell history) and relogin using previous credentials

## Usage

```shell
usage: ripper [-h] [-b {160,320,96}] [-c] [-d DIRECTORY] [-u USER]
              [-p PASSWORD] [-l] [-m] [-o] [-v VBR]
              uri

Rips Spotify URIs to MP3s with ID3 tags and album covers

positional arguments:
  uri                   Spotify URI (either URI, a file of URIs or a search query)

optional arguments:
  -h, --help            show this help message and exit
  -b {160,320,96}, --bitrate {160,320,96}
                        Bitrate rip quality [Default=320]
  -c, --cbr             Lame CBR encoding [Default=VBR]
  -d DIRECTORY, --directory DIRECTORY
                        Base directory where ripped MP3s are saved [Default=cwd]
  -u USER, --user USER  Spotify username
  -p PASSWORD, --password PASSWORD
                        Spotify password [Default=ask interactively]
  -l, --last            Use last login credentials
  -m, --pcm             Saves a .pcm file with the raw PCM data
  -o, --overwrite       Overwrite existing MP3 files [Default=skip]
  -v VBR, --vbr VBR     Lame VBR encoding quality setting [Default=0]

Example usage:
    rip a single file: ./ripper.py -u user -p password spotify:track:52xaypL0Kjzk0ngwv3oBPR
    rip entire playlist: ./ripper.py -u user -p password spotify:user:username:playlist:4vkGNcsS8lRXj4q945NIA4
    search for tracks to rip: /ripper.py -l -b 160 -o "album:Rumours track:'the chain'"
```

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
