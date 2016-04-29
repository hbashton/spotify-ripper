# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from colorama import Fore
from spotify_ripper.utils import *
import os
import time
import spotify
import requests
import re


class WebAPI(object):

    def __init__(self, args, ripper):
        self.args = args
        self.ripper = ripper
        self.cache = {}

    def cache_result(self, uri, result):
        self.cache[uri] = result

    def get_cached_result(self, uri):
        return self.cache.get(uri)

    def request_json(self, url, msg):
        print(Fore.GREEN + "Attempting to retrieve " + msg +
              " from Spotify's Web API" + Fore.RESET)
        print(Fore.CYAN + url + Fore.RESET)
        req = requests.get(url)
        if req.status_code == 200:
            return req.json()
        else:
            print(Fore.YELLOW + "URL returned non-200 HTTP code: " +
                  str(req.status_code) + Fore.RESET)
        return None

    def api_url(self, url_path):
        return 'https://api.spotify.com/v1/' + url_path

    def charts_url(self, url_path):
        return 'https://spotifycharts.com/api/' + url_path

    # excludes 'appears on' albums for artist
    def get_albums_with_filter(self, uri):
        args = self.args

        album_type = ('&album_type=' + args.artist_album_type[0]) \
            if args.artist_album_type is not None else ""

        market = ('&market=' + args.artist_album_market[0]) \
            if args.artist_album_market is not None else ""

        def get_albums_json(offset):
            url = self.api_url(
                    'artists/' + uri_tokens[2] +
                    '/albums/?=' + album_type + market +
                    '&limit=50&offset=' + str(offset))
            return self.request_json(url, "albums")

        # check for cached result
        cached_result = self.get_cached_result(uri)
        if cached_result is not None:
            return cached_result

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
        self.cache_result(uri, album_uris)
        return album_uris

    def get_artists_on_album(self, uri):
        def get_album_json(album_id):
            url = self.api_url('albums/' + album_id)
            return self.request_json(url, "album")

        # check for cached result
        cached_result = self.get_cached_result(uri)
        if cached_result is not None:
            return cached_result

        # extract album id from uri
        uri_tokens = uri.split(':')
        if len(uri_tokens) != 3:
            return None

        album = get_album_json(uri_tokens[2])
        if album is None:
            return None

        result = [artist['name'] for artist in album['artists']]
        self.cache_result(uri, result)
        return result

    # genre_type can be "artist" or "album"
    def get_genres(self, genre_type, track):
        def get_genre_json(spotify_id):
            url = self.api_url(genre_type + 's/' + spotify_id)
            return self.request_json(url, "genres")

        # extract album id from uri
        item = track.artists[0] if genre_type == "artist" else track.album
        uri = item.link.uri

        # check for cached result
        cached_result = self.get_cached_result(uri)
        if cached_result is not None:
            return cached_result

        uri_tokens = uri.split(':')
        if len(uri_tokens) != 3:
            return None

        json_obj = get_genre_json(uri_tokens[2])
        if json_obj is None:
            return None

        result = json_obj["genres"]
        self.cache_result(uri, result)
        return result

    # doesn't seem to be officially supported by Spotify
    def get_charts(self, uri):
        def get_tracks_json(metrics, region, time_window, from_date):
            limit = "50" if metrics == "viral" else "200"
            url = self.charts_url(
                    "?limit=" + limit + "&country=" + region +
                    "&recurrence=" + time_window + "&date=" + from_date +
                    "&type=" + metrics)
            return self.request_json(url, region + " " + metrics + " charts")

        # check for cached result
        cached_result = self.get_cached_result(uri)
        if cached_result is not None:
            return cached_result

        # spotify:charts:metric:region:time_window:date
        uri_tokens = uri.split(':')
        if len(uri_tokens) != 6:
            return None

        # some sanity checking
        valid_metrics = {"regional", "viral"}
        valid_regions = {"us", "gb", "ad", "ar", "at", "au", "be", "bg", "bo",
                         "br", "ca", "ch", "cl", "co", "cr", "cy", "cz", "de",
                         "dk", "do", "ec", "ee", "es", "fi", "fr", "gr", "gt",
                         "hk", "hn", "hu", "id", "ie", "is", "it", "lt", "lu",
                         "lv", "mt", "mx", "my", "ni", "nl", "no", "nz", "pa",
                         "pe", "ph", "pl", "pt", "py", "se", "sg", "sk", "sv",
                         "tr", "tw", "uy", "global"}
        valid_windows = {"daily", "weekly"}

        def sanity_check(val, valid_set):
            if val not in valid_set:
                print(Fore.YELLOW +
                      "Not a valid Spotify charts URI parameter: " +
                      val + Fore.RESET)
                print("Valid parameter options are: [" +
                      ", ".join(valid_set)) + "]"
                return False
            return True

        def sanity_check_date(val):
            if  re.match(r"^\d{4}-\d{2}-\d{2}$", val) is None and \
                    val != "latest":
                print(Fore.YELLOW +
                      "Not a valid Spotify charts URI parameter: " +
                      val + Fore.RESET)
                print("Valid parameter options are: ['latest', a date "
                      "(e.g. 2016-01-21)]")
                return False
            return True

        check_results = sanity_check(uri_tokens[2], valid_metrics) and \
            sanity_check(uri_tokens[3], valid_regions) and \
            sanity_check(uri_tokens[4], valid_windows) and \
            sanity_check_date(uri_tokens[5])
        if not check_results:
            print("Generally, a charts URI follow the pattern "
                  "spotify:charts:metric:region:time_window:date")
            return None

        json_obj = get_tracks_json(uri_tokens[2], uri_tokens[3],
                                   uri_tokens[4], uri_tokens[5])
        if json_obj is None:
            return None

        self.cache_result(uri, json_obj)
        return json_obj
