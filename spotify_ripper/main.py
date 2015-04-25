#!/usr/bin/env python
# -*- coding: utf8 -*-

from __future__ import unicode_literals

from colorama import init, Fore, Style
from spotify_ripper.ripper import Ripper
import os, sys
import time
import logging
import argparse
import pkg_resources

def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('spotify.ripper')

    parser = argparse.ArgumentParser(prog='spotify-ripper', description='Rips Spotify URIs to MP3s with ID3 tags and album covers',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog='''Example usage:
    rip a single file: spotify-ripper -u user -p password spotify:track:52xaypL0Kjzk0ngwv3oBPR
    rip entire playlist: spotify-ripper -u user -p password spotify:user:username:playlist:4vkGNcsS8lRXj4q945NIA4
    search for tracks to rip: spotify-ripper -l -b 160 -o "album:Rumours track:'the chain'"
    ''')

    group = parser.add_mutually_exclusive_group(required=True)

    parser.add_argument('-a', '--ascii', action='store_true', help='Convert file name to ASCII encoding [Default=utf-8]')
    parser.add_argument('-b', '--bitrate', default='320', choices=['160', '320', '96'], help='Bitrate rip quality [Default=320]')
    parser.add_argument('-c', '--cbr', action='store_true', help='Lame CBR encoding [Default=VBR]')
    parser.add_argument('-d', '--directory', nargs=1, help='Base directory where ripped MP3s are saved [Default=cwd]')
    parser.add_argument('-f', '--flat', action='store_true', help='Save all songs to a single directory instead of organizing by album/artist/song')
    parser.add_argument('-F', '--Flat', action='store_true', help='Similar to --flat [-f] but includes the playlist index at the start of the song file')
    parser.add_argument('-k', '--key', nargs=1, help='Path to Spotify application key file [Default=cwd]')
    group.add_argument('-u', '--user', nargs=1, help='Spotify username')
    parser.add_argument('-p', '--password', nargs=1, help='Spotify password [Default=ask interactively]')
    group.add_argument('-l', '--last', action='store_true', help='Use last login credentials')
    parser.add_argument('-m', '--pcm', action='store_true', help='Saves a .pcm file with the raw PCM data')
    parser.add_argument('-o', '--overwrite', action='store_true', help='Overwrite existing MP3 files [Default=skip]')
    parser.add_argument('-s', '--strip-colors', action='store_true', help='Strip coloring from output[Default=colors]')
    parser.add_argument('-S', '--settings', nargs=1, help='Path to settings and temp files directory [Default=~/.spotify-ripper]')
    parser.add_argument('-v', '--vbr', default='0', help='Lame VBR encoding quality setting [Default=0]')
    parser.add_argument('-V', '--version', action='version', version=pkg_resources.require("spotify-ripper")[0].version)
    parser.add_argument('-r', '--remove-from-playlist', action='store_true', help='Delete tracks from playlist after successful ripping [Default=no]')
    parser.add_argument('uri', help='Spotify URI (either URI, a file of URIs or a search query)')
    args = parser.parse_args()

    init(strip=True if args.strip_colors else None)

    ripper = Ripper(args)
    ripper.start()

    # wait for ripping thread to finish
    try:
        while not ripper.finished:
            time.sleep(0.1)
    except (KeyboardInterrupt, Exception) as e:
        if not isinstance(e, KeyboardInterrupt):
            logger.error(e)
        print("\n" + Fore.RED + "Aborting..." + Fore.RESET)
        ripper.abort()
        sys.exit(1)

if __name__ == '__main__':
    main()
