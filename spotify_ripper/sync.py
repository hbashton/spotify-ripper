# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from colorama import Fore, Style
from spotify_ripper.utils import *
import os
import sys
import json

class Sync(object):

    def __init__(self, args, ripper):
        self.args = args
        self.ripper = ripper

    def sync_lib_path(self, name):
        # lib path
        args = self.args
        if args.settings is not None:
            lib_path = os.path.join(norm_path(args.settings[0]), "Sync")
        else:
            lib_path = os.path.join(default_settings_dir(), "Sync")

        if not os.path.exists(lib_path):
            os.makedirs(lib_path)

        return os.path.join(lib_path, name + ".json")

    def save_sync_library(self, name, lib):
        lib_path = self.sync_lib_path(name)

        with open(lib_path, 'w') as lib_file:
            lib_file.write(json.dumps(lib, ensure_ascii=self.args.ascii,
                indent=4, separators=(',', ': ')))

    def load_sync_library(self, name):
        lib_path = self.sync_lib_path(name)

        if os.path.exists(lib_path):
            with open(lib_path, 'r') as lib_file:
                return json.loads(lib_file.read())
        else:
            return {}


    def sync_playlist(self, playlist):
        name = playlist.name
        lib = self.load_sync_library(name)
        new_lib = {}

        print("Syncing playlist " + name)

        # remove any missing files from the lib or playlist
        uris = set([t.link.uri for t in playlist.tracks])
        for uri, file_path in lib.items():
            if not os.path.exists(file_path):
                del lib[uri]
            elif uri not in uris:
                os.remove(file_path)
                del lib[uri]

        # check if we need to rename any songs already ripped
        for idx, track in enumerate(playlist.tracks):
            try:
                track.load()
                if track.availability != 1:
                    continue

                audio_file = self.ripper.format_track_path(idx, track)

                # rename the ripped file if needed
                if track.link.uri in lib:
                    if lib[track.link.uri] != audio_file:
                        os.rename(lib[track.link.uri], audio_file)

                # add file to new lib
                new_lib[track.link.uri] = audio_file

            except spotify.Error as e:
                continue

        # save new lib
        self.save_sync_library(name, new_lib)
