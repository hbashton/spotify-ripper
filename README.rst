spotify-ripper |Version|
========================

A fork of
`spotify-ripper <https://github.com/robbeofficial/spotifyripper>`__ that
uses `pyspotify <https://github.com/mopidy/pyspotify>`__ v2.x

Spotify-ripper is a small ripper script for Spotify that rips Spotify
URIs to MP3 files and includes ID3 tags and cover art.

**Note that stream ripping violates the libspotify's ToS**

Features
--------

-  real-time VBR or CBR ripping from spotify PCM stream

-  writes id3 tags (including album covers)

-  creates files and directories based on the following structure
   artist/album/artist - song.mp3

-  optionally skip existing files

-  accepts tracks, playlists, albums, and artist URIs

-  search for tracks using Spotify queries

-  options for interactive login (no password in shell history) and
   relogin using previous credentials

-  option to remove tracks from playlist after successful ripping

-  globally installs ripper script using pip

-  Python 2.7.x and 3.4.x compatible.  Python 3 will occasionally throw a ``NameError: name '_lock' is not defined`` exception at the end of the script due to an `upstream bug <https://github.com/mopidy/pyspotify/issues/133>`__ in ``pyspotify``.

-  use a config file to specify common command-line options

Usage
-----

Command Line
~~~~~~~~~~~~

``spotify-ripper`` takes many command-line options

.. code::

    usage: spotify-ripper [-h] [-S SETTINGS] [-a] [-b {160,320,96}] [-c]
                          [-d DIRECTORY] [-f] [-F] [-k KEY] [-u USER]
                          [-p PASSWORD] [-l] [-m] [-o] [-s] [-v VBR] [-V] [-r]
                          uri

    Rips Spotify URIs to MP3s with ID3 tags and album covers

    positional arguments:
      uri                   Spotify URI (either URI, a file of URIs or a search query)

    optional arguments:
      -h, --help            show this help message and exit
      -S SETTINGS, --settings SETTINGS
                            Path to settings, config and temp files directory [Default=~/.spotify-ripper]
      -a, --ascii           Convert file name to ASCII encoding [Default=utf-8]
      -b {160,320,96}, --bitrate {160,320,96}
                            Bitrate rip quality [Default=320]
      -c, --cbr             Lame CBR encoding [Default=VBR]
      -d DIRECTORY, --directory DIRECTORY
                            Base directory where ripped MP3s are saved [Default=cwd]
      -f, --flat            Save all songs to a single directory instead of organizing by album/artist/song
      -F, --Flat            Similar to --flat [-f] but includes the playlist index at the start of the song file
      -k KEY, --key KEY     Path to Spotify application key file [Default=cwd]
      -u USER, --user USER  Spotify username
      -p PASSWORD, --password PASSWORD
                            Spotify password [Default=ask interactively]
      -l, --last            Use last login credentials
      -m, --pcm             Saves a .pcm file with the raw PCM data
      -o, --overwrite       Overwrite existing MP3 files [Default=skip]
      -s, --strip-colors    Strip coloring from output[Default=colors]
      -v VBR, --vbr VBR     Lame VBR encoding quality setting [Default=0]
      -V, --version         show program's version number and exit
      -r, --remove-from-playlist
                            Delete tracks from playlist after successful ripping [Default=no]

    Example usage:
        rip a single file: spotify-ripper -u user -p password spotify:track:52xaypL0Kjzk0ngwv3oBPR
        rip entire playlist: spotify-ripper -u user -p password spotify:user:username:playlist:4vkGNcsS8lRXj4q945NIA4
        search for tracks to rip: spotify-ripper -l -b 160 -o "album:Rumours track:'the chain'"

Config File
~~~~~~~~~~~

For options that you want set on every run, you can use a config file named ``config.ini`` in the settings folder (defaults to ``~/.spotify-ripper``).  The options in the config file use the same name as the command line options with the exception that dashes are tranlated to ``snake_case``.  Any option specified in the command line will overwrite any setting in the config file.  Please put all options under a ``[main]`` section.

Here is an example config file

.. code:: ini

    [main]
    ascii = True
    bitrate = 160
    flat = True
    last = True
    remove_from_playlist = True

Installation
------------

Prerequisites
~~~~~~~~~~~~~

-  `libspotify <https://developer.spotify.com/technologies/libspotify>`__

-  `pyspotify <https://github.com/mopidy/pyspotify>`__

-  a Spotify binary `app
   key <https://devaccount.spotify.com/my-account/keys/>`__
   (spotify\_appkey.key)

-  `lame <http://lame.sourceforge.net>`__

-  `mutagen <https://mutagen.readthedocs.org/en/latest/>`__

-  `colorama <https://pypi.python.org/pypi/colorama>`__

Mac OS X
~~~~~~~~

Recommend approach uses `homebrew <http://brew.sh/>`__ and
`pyenv <https://github.com/yyuu/pyenv>`__

.. code:: bash

    $ brew install homebrew/binary/libspotify
    $ sudo ln -s /usr/local/opt/libspotify/lib/libspotify.12.1.51.dylib \
        /usr/local/opt/libspotify/lib/libspotify
    $ brew install lame
    $ pip install spotify-ripper
    $ pyenv rehash

Download an application key file ``spotify_appkey.key`` from
``https://devaccount.spotify.com/my-account/keys/`` (requires a Spotify
Premium Account) and move the file to the ``~/.spotify-ripper`` directory (or use
the ``-k | --key`` option).

Ubuntu/Debian
~~~~~~~~~~~~~

Recommend approach uses `pyenv <https://github.com/yyuu/pyenv>`__. If
you don't use pyenv, you need to install the ``python-dev`` package
too. If you are installing on the Raspberry Pi (gen 1), use the
`eabi-armv6hf
version <https://developer.spotify.com/download/libspotify/libspotify-12.1.103-Linux-armv6-bcm2708hardfp-release.tar.gz>`__
of libspotify.

.. code:: bash

    $ sudo apt-get install lame build-essential libffi-dev
    $ wget https://developer.spotify.com/download/libspotify/libspotify-12.1.51-Linux-x86_64-release.tar.gz # (assuming 64-bit)
    $ tar xvf libspotify-12.1.51-Linux-x86_64-release.tar.gz
    $ cd libspotify-12.1.51-Linux-x86_64-release/
    $ sudo make install prefix=/usr/local
    $ pip install spotify-ripper
    $ pyenv rehash

Download an application key file ``spotify_appkey.key`` from
``https://devaccount.spotify.com/my-account/keys/`` (requires a Spotify
Premium Account) and move the file to the ``~/.spotify-ripper`` directory (or use
the ``-k | --key`` option).

Upgrade
~~~~~~~

Use ``pip`` to upgrade to the latest version.

.. code:: bash

    $ pip install --upgrade spotify-ripper

License
-------

`MIT License <http://en.wikipedia.org/wiki/MIT_License>`__

.. |Version| image:: http://img.shields.io/pypi/v/spotify-ripper.svg?style=flat-square
  :target: https://pypi.python.org/pypi/spotify-ripper
