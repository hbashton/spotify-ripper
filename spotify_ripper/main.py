#!/usr/bin/env python
# -*- coding: utf8 -*-

from __future__ import unicode_literals

from colorama import init, Fore, Style, AnsiToWin32
from spotify_ripper.ripper import Ripper
from spotify_ripper.utils import *
import os, sys
import time
import argparse
import pkg_resources
import ConfigParser

def load_config(args, defaults):
    settings_dir = args.settings[0] if args.settings is not None else default_settings_dir()
    config_file = os.path.join(settings_dir, "config.ini")
    if os.path.exists(config_file):
        try:
            config = ConfigParser.SafeConfigParser()
            config.read(config_file)
            if not config.has_section("main"): return defaults
            config_items = dict(config.items("main"))

            to_array_options = ["directory", "key", "user", "password", "log", "genres"]

            # coerce boolean and none types
            for _key in config_items:
                item = config_items[_key]
                if item == 'True': config_items[_key] = True
                elif item == 'False': config_items[_key] = False
                elif item == 'None': config_items[_key] = None

                # certain options need to be in array (nargs=1)
                if _key in to_array_options:
                    config_items[_key] = [item]

            # overwrite any existing defaults
            defaults.update(config_items)
        except (ConfigParser.Error) as e:
            print("\nError parsing config file: " + config_file)
            print(str(e))

    return defaults

def main():
    # in case we changed the location of the settings directory where the config file lives, we need to parse this argument
    # before we parse the rest of the arguments (which can overwrite the options in the config file)
    settings_parser = argparse.ArgumentParser(add_help=False)
    settings_parser.add_argument('-S', '--settings', nargs=1, help='Path to settings, config and temp files directory [Default=~/.spotify-ripper]')
    args, remaining_argv = settings_parser.parse_known_args()

    # load config file, overwriting any defaults
    defaults = {
        "bitrate": "320",
        "vbr": "0",
    }
    defaults = load_config(args, defaults)

    parser = argparse.ArgumentParser(prog='spotify-ripper', description='Rips Spotify URIs to MP3s with ID3 tags and album covers',
        parents=[settings_parser],
        formatter_class=argparse.RawTextHelpFormatter,
        epilog='''Example usage:
    rip a single file: spotify-ripper -u user -p password spotify:track:52xaypL0Kjzk0ngwv3oBPR
    rip entire playlist: spotify-ripper -u user -p password spotify:user:username:playlist:4vkGNcsS8lRXj4q945NIA4
    rip a list of URIs: spotify-ripper -u user -p password list_of_uris.txt
    search for tracks to rip: spotify-ripper -l -b 160 -o "album:Rumours track:'the chain'"
    ''')

    # create group to prevent to prevent user from using both the -l and -u option
    is_user_set = defaults.get('user') is not None
    is_last_set = defaults.get('last') is True
    if is_user_set or is_last_set:
        if is_user_set and is_last_set:
            print("spotify-ripper: error: one of the arguments -u/--user -l/--last is required")
            sys.exit(1)
        else:
            group = parser.add_mutually_exclusive_group(required=False)
    else:
        group = parser.add_mutually_exclusive_group(required=True)

    # set defaults
    parser.set_defaults(**defaults)

    parser.add_argument('-a', '--ascii', action='store_true', help='Convert the file name and the ID3 tag to ASCII encoding [Default=utf-8]')
    parser.add_argument('-A', '--ascii-path-only', action='store_true', help='Convert the file name (but not the ID3 tag) to ASCII encoding [Default=utf-8]')
    parser.add_argument('-b', '--bitrate', choices=['160', '320', '96'], help='Bitrate rip quality [Default=320]')
    parser.add_argument('-c', '--cbr', action='store_true', help='Lame CBR encoding [Default=VBR]')
    parser.add_argument('-d', '--directory', nargs=1, help='Base directory where ripped MP3s are saved [Default=cwd]')
    parser.add_argument('-f', '--flat', action='store_true', help='Save all songs to a single directory instead of organizing by album/artist/song')
    parser.add_argument('-F', '--Flat', action='store_true', help='Similar to --flat [-f] but includes the playlist index at the start of the song file')
    parser.add_argument('-g', '--genres', nargs=1, choices=['artist', 'album'], help='Attempt to retrieve genre information from Spotify\'s Web API [Default=skip]')
    parser.add_argument('-k', '--key', nargs=1, help='Path to Spotify application key file [Default=cwd]')
    group.add_argument('-u', '--user', nargs=1, help='Spotify username')
    parser.add_argument('-p', '--password', nargs=1, help='Spotify password [Default=ask interactively]')
    group.add_argument('-l', '--last', action='store_true', help='Use last login credentials')
    parser.add_argument('-L', '--log', nargs=1, help='Log in a log-friendly format to a file (use - to log to stdout)')
    parser.add_argument('-m', '--pcm', action='store_true', help='Saves a .pcm file with the raw PCM data')
    parser.add_argument('-o', '--overwrite', action='store_true', help='Overwrite existing MP3 files [Default=skip]')
    parser.add_argument('-s', '--strip-colors', action='store_true', help='Strip coloring from output[Default=colors]')
    parser.add_argument('-v', '--vbr', help='Lame VBR encoding quality setting [Default=0]')
    parser.add_argument('-V', '--version', action='version', version=pkg_resources.require("spotify-ripper")[0].version)
    parser.add_argument('-r', '--remove-from-playlist', action='store_true', help='Delete tracks from playlist after successful ripping [Default=no]')
    parser.add_argument('uri', help='Spotify URI (either URI, a file of URIs or a search query)')
    args = parser.parse_args(remaining_argv)

    # kind of a hack to get colorama stripping to work when outputting
    # to a file instead of stdout.  Taken from initialise.py in colorama
    def wrap_stream(stream, convert, strip, autoreset, wrap):
        if wrap:
            wrapper = AnsiToWin32(stream,
                convert=convert, strip=strip, autoreset=autoreset)
            if wrapper.should_wrap():
                stream = wrapper.stream
        return stream

    args.has_log = args.log is not None
    if args.has_log:
        if args.log[0] == "-":
            init(strip=True)
        else:
            log_file = open(args.log[0], 'a')
            sys.stdout = wrap_stream(log_file, None, True, False, True)
    else:
        init(strip=True if args.strip_colors else None)

    if args.ascii_path_only is True: args.ascii = True

    ripper = Ripper(args)
    ripper.start()

    # wait for ripping thread to finish
    try:
        while not ripper.finished:
            time.sleep(0.1)
    except (KeyboardInterrupt, Exception) as e:
        if not isinstance(e, KeyboardInterrupt):
            print(str(e))
        print("\n" + Fore.RED + "Aborting..." + Fore.RESET)
        ripper.abort()
        sys.exit(1)

if __name__ == '__main__':
    main()
