# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from colorama import Fore, Style
from spotify_ripper.utils import *
import os
import json
import codecs
import copy
import spotify


class Sync(object):

    def __init__(self, args, ripper):
        self.args = args
        self.ripper = ripper

    def sync_lib_path(self, playlist):
        args = self.args

        # get playlist_id
        uri_tokens = playlist.link.uri.split(':')
        if len(uri_tokens) != 5:
            return None

        # lib path
        if args.settings is not None:
            lib_path = os.path.join(norm_path(args.settings[0]), "Sync")
        else:
            lib_path = os.path.join(default_settings_dir(), "Sync")

        if not path_exists(lib_path):
            os.makedirs(enc_str(lib_path))

        return os.path.join(enc_str(lib_path), enc_str(uri_tokens[4] + ".json"))

    def save_sync_library(self, playlist, lib):
        args = self.args
        lib_path = self.sync_lib_path(playlist)

        encoding = "ascii" if args.ascii else "utf-8"
        with codecs.open(lib_path, 'w', encoding) as lib_file:
            lib_file.write(
                json.dumps(lib, ensure_ascii=args.ascii,
                           indent=4, separators=(',', ': ')))

    def load_sync_library(self, playlist):
        args = self.args
        lib_path = self.sync_lib_path(playlist)

        if os.path.exists(lib_path):
            encoding = "ascii" if args.ascii else "utf-8"
            with codecs.open(lib_path, 'r', encoding) as lib_file:
                return json.loads(lib_file.read())
        else:
            return {}

    def sync_playlist(self, playlist):
        args = self.args
        lib = self.load_sync_library(playlist)
        new_lib = {}

        print("Syncing playlist " + to_ascii(playlist.name))

        # remove any missing files from the lib or playlist
        uris = set([t.link.uri for t in playlist.tracks])
        copy_lib = copy.deepcopy(lib)
        for uri, file_path in lib.items():
            file_path = enc_str(file_path)
            if not os.path.exists(file_path):
                del copy_lib[uri]
            elif uri not in uris:
                os.remove(file_path)
                del copy_lib[uri]
        lib = copy_lib

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
        self.save_sync_library(playlist, new_lib)
