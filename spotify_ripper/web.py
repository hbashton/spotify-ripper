# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from colorama import Fore
from spotify_ripper.utils import *
import os
import time
import spotify
import requests


class WebAPI(object):

    def __init__(self, args, ripper):
        self.args = args
        self.ripper = ripper

    # excludes 'appears on' albums
    def get_non_appears_on_albums(self, uri):
        def get_albums_json(offset):
            url = 'https://api.spotify.com/v1/artists/' + \
                  uri_tokens[2] + \
                  '/albums/?=album_type=album,single,compilation' + \
                  '&limit=50&offset=' + str(offset)
            print(
                Fore.GREEN + "Attempting to retrieve albums "
                             "from Spotify's Web API" + Fore.RESET)
            print(Fore.CYAN + url + Fore.RESET)
            req = requests.get(url)
            if req.status_code == 200:
                return req.json()
            else:
                print(Fore.YELLOW + "URL returned non-200 HTTP code: " +
                      str(req.status_code) + Fore.RESET)
            return None

        # extract artist id from uri
        uri_tokens = uri.split(':')
        if len(uri_tokens) != 3:
            return []

        # it is possible we won't get all the albums on the first request
        offset = 0
        album_uris = []
        total = None
        while total is None or offset < total:
            try:
                # rate limit if not first request
                if total is None:
                    time.sleep(1.0)
                albums = get_albums_json(offset)
                if albums is None:
                    break

                # extract album URIs
                album_uris += [album['uri'] for album in albums['items']]
                offset = len(album_uris)
                if total is None:
                    total = albums['total']
            except KeyError as e:
                break
        print(str(len(album_uris)) + " albums found")
        return album_uris

    def get_artists_on_album(self, uri):
        def get_album_json(album_id):
            url = 'https://api.spotify.com/v1/albums/' + album_id
            print(
                Fore.GREEN + "Attempting to retrieve album "
                             "from Spotify's Web API" + Fore.RESET)
            print(Fore.CYAN + url + Fore.RESET)
            req = requests.get(url)
            if req.status_code == 200:
                return req.json()
            else:
                print(Fore.YELLOW + "URL returned non-200 HTTP code: " +
                      str(req.status_code) + Fore.RESET)
            return None

        # extract album id from uri
        uri_tokens = uri.split(':')
        if len(uri_tokens) != 3:
            return None

        album = get_album_json(uri_tokens[2])
        if album is None:
            return None

        return [artist['name'] for artist in album['artists']]

    # genre_type can be "artist" or "album"
    def get_genres(self, genre_type, track):
        def get_json(spotify_id):
            url = ('https://api.spotify.com/v1/' +
                   genre_type + 's/' + spotify_id)
            print(
                Fore.GREEN + "Attempting to retrieve genres "
                             "from Spotify's Web API" + Fore.RESET)
            print(Fore.CYAN + url + Fore.RESET)
            req = requests.get(url)
            if req.status_code == 200:
                try:
                    return req.json()
                except KeyError as e:
                    pass
            else:
                print(Fore.YELLOW + "URL returned non-200 HTTP code: " +
                      str(req.status_code) + Fore.RESET)

        # extract album id from uri
        item = track.artists[0] if genre_type == "artist" else track.album
        uri_tokens = item.link.uri.split(':')
        if len(uri_tokens) != 3:
            return None

        json_obj = get_json(uri_tokens[2])
        if json_obj is None:
            return None

        return json_obj["genres"]
