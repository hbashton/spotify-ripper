# -*- coding: utf8 -*-

from __future__ import unicode_literals

from subprocess import call
from colorama import Fore, Style
from mutagen import mp3, id3
from stat import ST_SIZE
from spotify_ripper.utils import *
import os, sys

def set_id3_and_cover(args, mp3_file, track):
    # ensure everything is loaded still
    if not track.is_loaded: track.load()
    if not track.album.is_loaded: track.album.load()
    album_browser = track.album.browse()
    album_browser.load()

    # calculate num of tracks on disc and num of dics
    num_discs = 0
    num_tracks = 0
    for track_browse in album_browser.tracks:
        if track_browse.disc == track.disc and track_browse.index > track.index:
            num_tracks = track_browse.index
        if track_browse.disc > num_discs:
            num_discs = track_browse.disc

    # use mutagen to update id3v2 tags
    try:
        audio = mp3.MP3(mp3_file, ID3=id3.ID3)

        # add ID3 tag if it doesn't exist
        audio.add_tags()

        image = track.album.cover()
        if image is not None:
            image.load()

            fh_cover = open('cover.jpg', 'wb')
            fh_cover.write(image.data)
            fh_cover.flush()
            os.fsync(fh_cover.fileno())
            fh_cover.close()

            audio.tags.add(
                id3.APIC(
                    encoding=3,
                    mime='image/jpeg',
                    type=3,
                    desc='Front Cover',
                    data=open('cover.jpg', 'rb').read()
                )
            )

        audio.tags.add(id3.TALB(text=[track.album.name], encoding=3))
        audio.tags.add(id3.TIT2(text=[track.name], encoding=3))
        audio.tags.add(id3.TPE1(text=[track.artists[0].name], encoding=3))
        audio.tags.add(id3.TDRL(text=[str(track.album.year)], encoding=3))
        audio.tags.add(id3.TPOS(text=[("%d/%d" % (track.disc, num_discs))], encoding=3))
        audio.tags.add(id3.TRCK(text=[("%d/%d" % (track.index, num_tracks))], encoding=3))

        def bit_rate_str(bit_rate):
           brs = "%d kb/s" % bit_rate
           if not args.cbr:
              brs = "~" + brs
           return brs

        def mode_str(mode):
            modes = ["Stereo", "Joint Stereo", "Dual Channel", "Mono"]
            if mode < len(modes):
                return modes[mode]
            else:
                return ""

        print(Fore.GREEN + Style.BRIGHT + os.path.basename(mp3_file) + Style.NORMAL + "\t[ " + format_size(os.stat(mp3_file)[ST_SIZE]) + " ]" + Fore.RESET)
        print("-" * 79)
        print(Fore.YELLOW + "Setting artist: " + track.artists[0].name + Fore.RESET)
        print(Fore.YELLOW + "Setting album: " + track.album.name + Fore.RESET)
        print(Fore.YELLOW + "Setting title: " + track.name + Fore.RESET)
        print(Fore.YELLOW + "Setting track info: (" + str(track.index) + ", " + str(num_tracks) + ")"  + Fore.RESET)
        print(Fore.YELLOW + "Setting disc info: (" + str(track.disc) + ", " + str(num_discs) + ")"  + Fore.RESET)
        print(Fore.YELLOW + "Setting release year: " + str(track.album.year) + Fore.RESET)
        if image is not None: print(Fore.YELLOW + "Adding image cover.jpg" + Fore.RESET)
        print("Time: " + format_time(audio.info.length) + "\tMPEG" + str(audio.info.version) +
            ", Layer " + ("I" * audio.info.layer) + "\t[ " + bit_rate_str(audio.info.bitrate / 1000) +
            " @ " + str(audio.info.sample_rate) + " Hz - " + mode_str(audio.info.mode) + " ]")
        print("-" * 79)
        id3_version = "v%d.%d" % (audio.tags.version[0], audio.tags.version[1])
        print("ID3 " + id3_version + ": " + str(len(audio.tags.values())) + " frames")
        print(Fore.YELLOW + "Writing ID3 version " + id3_version + Fore.RESET)
        print("-" * 79)

        audio.save()

    except id3.error:
        print(Fore.YELLOW + "Warning: exception while saving id3 tag: " + str(id3.error) + Fore.RESET)

    # delete cover
    call(["rm", "-f", "cover.jpg"])
