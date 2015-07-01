spotify-ripper |Version|
========================

A fork of
`spotify-ripper <https://github.com/robbeofficial/spotifyripper>`__ that
uses `pyspotify <https://github.com/mopidy/pyspotify>`__ v2.x

Spotify-ripper is a small ripper script for Spotify that rips Spotify
URIs to audio files and includes ID3 tags and cover art.  By default spotify-ripper will encode to MP3 files, but includes the ability to rip to WAV, FLAC, Ogg Vorbis, Opus, AAC, and MP4/M4A.

**Note that stream ripping violates the libspotify's ToS**

Libspotify’s Deprecation
------------------------
**From Mopidy's documentation**

*Note that as of May 2015 libspotify is officially deprecated by Spotify and is no longer actively maintained.*

*Spotify has published newer libraries intended for Android and iOS development, as well as web APIs to access track metadata and manage playlists. Though, for making apps with Spotify playback capabilities, on any other platform than Android and iOS, there is currently no alternative to libspotify.*

*libspotify has been the main way of integrating with Spotify since 2009, and is today a part of numerous open source projects and commercial applications, including many receivers and even cars. There’s no guarantees, but one can hope that the large deployment of libspotify means that the library will continue to work with the Spotify service for a long time into the future.*

Features
--------

-  real-time VBR or CBR ripping from Spotify PCM stream

-  writes ID3v2/metadata tags (including album covers)

-  rips files into the following directory structure: ``artist/album/artist - song.mp3`` by default or optionally into a user-specified structure (see `Format String`_ section below)

-  option to skip or overwrite existing files

-  accepts tracks, playlists, albums, and artist URIs

-  search for tracks using Spotify queries

-  options for interactive login (no password in shell history) and
   to relogin using previous credentials

-  option to remove tracks from playlist after successful ripping

-  globally installs ripper script using pip

-  Python 2.7.x and 3.4.x compatible.  Python 3 will occasionally throw a ``NameError: name '_lock' is not defined`` exception at the end of the script due to an `upstream bug <https://github.com/mopidy/pyspotify/issues/133>`__ in ``pyspotify``.

-  use a config file to specify common command-line options

-  helpful progress bar to gauge the time remaining until completion

-  option to rip to FLAC, a loseless codec, instead of MP3 (requires extra ``flac`` dependency)

-  option to rip to Ogg Vorbis instead of MP3 (requires extra ``vorbis-tools`` dependency)

-  option to rip to Opus instead of MP3 (requires extra ``opus-tools`` dependency)

-  option to rip to AAC instead of MP3 (requires extra ``faac`` dependency)

-  option to rip to MP4/M4A instead of MP3 (requires compiling ``fdkaac``)


Usage
-----

Command Line
~~~~~~~~~~~~

``spotify-ripper`` takes many command-line options

.. code::

    usage: spotify-ripper [-h] [-S SETTINGS] [-a] [--aac] [-A] [-b BITRATE] [-c]
                          [--comp COMP] [-d DIRECTORY] [--fail-log FAIL_LOG]
                          [--flac] [-f FORMAT] [--flat] [--flat-with-index]
                          [-g {artist,album}] [-k KEY] [-u USER] [-p PASSWORD]
                          [-l] [-L LOG] [--pcm] [--mp4] [-o] [--opus] [-q VBR]
                          [-Q {160,320,96}] [-s] [-V] [--wav] [--vorbis] [-r] [-x]
                          uri [uri ...]

    Rips Spotify URIs to MP3s with ID3 tags and album covers

    positional arguments:
      uri                   One or more Spotify URI(s) (either URI, a file of URIs or a search query)

    optional arguments:
      -h, --help            show this help message and exit
      -S SETTINGS, --settings SETTINGS
                            Path to settings, config and temp files directory [Default=~/.spotify-ripper]
      -a, --ascii           Convert the file name and the metadata tags to ASCII encoding [Default=utf-8]
      --aac                 Rip songs to AAC format with FreeAAC instead of MP3
      -A, --ascii-path-only
                            Convert the file name (but not the metadata tags) to ASCII encoding [Default=utf-8]
      -b BITRATE, --bitrate BITRATE
                            CBR bitrate [Default=320]
      -c, --cbr             CBR encoding [Default=VBR]
      --comp COMP           compression complexity for FLAC and Opus [Default=Max]
      -d DIRECTORY, --directory DIRECTORY
                            Base directory where ripped MP3s are saved [Default=cwd]
      --fail-log FAIL_LOG   Logs the list of track URIs that failed to rip
      --flac                Rip songs to lossless FLAC encoding instead of MP3
      -f FORMAT, --format FORMAT
                            Save songs using this path and filename structure (see README)
      --flat                Save all songs to a single directory (overrides --format option)
      --flat-with-index     Similar to --flat [-f] but includes the playlist index at the start of the song file
      -g {artist,album}, --genres {artist,album}
                            Attempt to retrieve genre information from Spotify's Web API [Default=skip]
      -k KEY, --key KEY     Path to Spotify application key file [Default=cwd]
      -u USER, --user USER  Spotify username
      -p PASSWORD, --password PASSWORD
                            Spotify password [Default=ask interactively]
      -l, --last            Use last login credentials
      -L LOG, --log LOG     Log in a log-friendly format to a file (use - to log to stdout)
      --pcm                 Saves a .pcm file with the raw PCM data instead of MP3
      --mp4                 Rip songs to MP4/M4A format with Fraunhofer FDK AAC codec instead of MP3
      -o, --overwrite       Overwrite existing MP3 files [Default=skip]
      --opus                Rip songs to Opus encoding instead of MP3
      -q VBR, --vbr VBR     VBR quality setting or target bitrate for Opus [Default=0]
      -Q {160,320,96}, --quality {160,320,96}
                            Spotify stream bitrate preference [Default=320]
      -s, --strip-colors    Strip coloring from output[Default=colors]
      -V, --version         show program's version number and exit
      --wav                 Rip songs to uncompressed WAV file instead of MP3
      --vorbis              Rip songs to Ogg Vorbis encoding instead of MP3
      -r, --remove-from-playlist
                            Delete tracks from playlist after successful ripping [Default=no]
      -x, --exclude-appears-on
                            Exclude albums that an artist 'appears on' when passing a Spotify artist URI

    Example usage:
        rip a single file: spotify-ripper -u user -p password spotify:track:52xaypL0Kjzk0ngwv3oBPR
        rip entire playlist: spotify-ripper -u user -p password spotify:user:username:playlist:4vkGNcsS8lRXj4q945NIA4
        rip a list of URIs: spotify-ripper -u user -p password list_of_uris.txt
        search for tracks to rip: spotify-ripper -l -b 160 -o "album:Rumours track:'the chain'"

Config File
~~~~~~~~~~~

For options that you want set on every run, you can use a config file named ``config.ini`` in the settings folder (defaults to ``~/.spotify-ripper``).  The options in the config file use the same name as the command line options with the exception that dashes are translated to ``snake_case``.  Any option specified in the command line will overwrite any setting in the config file.  Please put all options under a ``[main]`` section.

Here is an example config file

.. code:: ini

    [main]
    ascii = True
    bitrate = 160
    flat = True
    last = True
    remove_from_playlist = True

Format String
-------------

The format string dictates how ``spotify-ripper`` will organize your ripped files.  This is controlled through the ``-f | --format`` option.  The string should include the format of the file name and optionally a directory structure.   If you do not include a format string, the default format will be used: ``{album_artist}/{album}/{artist} - {track_name}.{ext}``.

The ``--flat`` option is shorthand for using the format string: ``{artist} - {track_name}.{ext}``, and the ``--flat-with-index`` option is shorthand for using the format string: ``{idx:3} - {artist} - {track_name}.{ext}``.  The use of these shorthand options will override any ``--format`` string option given.

Your format string can include the following variables names, which are case-sensitive and wrapped in curly braces, if you want your file/path name to be overwritten with Spotify metadata.

Format String Variables
~~~~~~~~~~~~~~~~~~~~~~~

+-----------------------------------------+-----------------------------------------------+
| Names and Aliases                       | Description                                   |
+=========================================+===============================================+
| ``{track_artist}``, ``{artist}``        | The track's artist                            |
+-----------------------------------------+-----------------------------------------------+
| ``{track_artists}``, ``{artists}``      | Similar to ``{track_artist}`` but will be join|
|                                         | multiple artists with a comma                 |
|                                         | (e.g. "artist 1, artist 2")                   |
+-----------------------------------------+-----------------------------------------------+
| ``{album_artist}``                      | When passing an album, the album's artist     |
|                                         | (e.g. "Various Artists").  If no album artist |
|                                         | exists, the track artist is used instead      |
+-----------------------------------------+-----------------------------------------------+
| ``{album_artists_web}``                 | Similar to ``{album_artist}`` but retrieves   |
|                                         | artist information from Spotify's Web API.    |
|                                         | Unlike ``{album_artist}``, multiple album     |
|                                         | artists can be retrieved and will be joined   |
|                                         | with a comma (e.g. "artist 1, artist 2")      |
+-----------------------------------------+-----------------------------------------------+
| ``{album}``                             | Album name                                    |
+-----------------------------------------+-----------------------------------------------+
| ``{track_name}``, ``{track}``           | Track name                                    |
+-----------------------------------------+-----------------------------------------------+
| ``{year}``                              | Release year of the album                     |
+-----------------------------------------+-----------------------------------------------+
| ``{ext}``, ``{extension}``              | Filename extension (i.e. "mp3", "ogg", "flac",|
|                                         | ...)                                          |
+-----------------------------------------+-----------------------------------------------+
| ``{idx}``, ``{index}``                  | Playlist index                                |
|                                         |                                               |
+-----------------------------------------+-----------------------------------------------+
| ``{track_num}``, ``{track_idx}``,       | The track number of the disc                  |
| ``{track_index}``                       |                                               |
+-----------------------------------------+-----------------------------------------------+
| ``{disc_num}``, ``{disc_idx}``,         | The disc number of the album                  |
| ``{disc_index}``                        |                                               |
+-----------------------------------------+-----------------------------------------------+

Any substring in the format string that does not match a variable above will be passed through to the file/path name unchanged.

Zero-Filled Padding
~~~~~~~~~~~~~~~~~~~

Format variables that represent an index can be padded with zeros to a user-specified length.  For example, ``{idx:3}`` will produce the following output: 001, 002, 003, etc.  If no number is provided, no zero-filled padding will occur (e.g. 8, 9, 10, 11, ...). The variables that accept this option include ``{idx}``, ``{track_num}``, and ``{disc_num}`` and thier aliases.

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

-  (optional) `flac <https://xiph.org/flac/index.html>`__

-  (optional) `opus-tools <http://www.opus-codec.org/downloads/>`__

-  (optional) `vorbis-tools <http://downloads.xiph.org/releases/vorbis/>`__

-  (optional) `faac <http://www.audiocoding.com/downloads.html>`__

-  (optional) `fdkaac <https://github.com/nu774/fdkaac>`__

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

Optional Encoding Formats
~~~~~~~~~~~~~~~~~~~~~~~~~

In addition to MP3 encoding, ``spotify-ripper`` supports encoding to FLAC, AAC, MP4/M4A, Ogg Vorbis and Opus.  However, additional encoding tools need to be installed for each codec you wish to use.

**Mac OS X**

.. code:: bash

    # FLAC
    $ brew install flac

    # AAC
    $ brew install faac

    # MP4/M4A
    $ brew install fdkaac

    # Ogg Vorbis
    $ brew install vorbis-tools

    # Opus
    $ brew install opus-tools

**Ubuntu/Debian**

.. code:: bash

    # FLAC
    $ sudo apt-get install flac

    # AAC
    $ sudo apt-get install faac

    # MP4/M4A (need to compile fdkaac from source)
    $ sudo apt-get install libfdk-aac-dev automake autoconf
    $ wget https://github.com/nu774/fdkaac/archive/v0.6.2.tar.gz
    $ tar xvf v0.6.2.tar.gz
    $ cd fdkaac-0.6.2
    $ autoreconf -i
    $ ./configure
    $ sudo make install

    # Ogg Vorbis
    $ sudo apt-get install vorbis-tools

    # Opus
    $ sudo apt-get install opus-tools


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
