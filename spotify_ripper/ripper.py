# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from subprocess import Popen, PIPE
from colorama import Fore
from spotify_ripper.utils import *
from spotify_ripper.tags import set_metadata_tags
from spotify_ripper.progress import Progress
from spotify_ripper.sync import Sync
import os
import sys
import time
import threading
import spotify
import getpass
import itertools
import requests
import wave
import re
import codecs

class BitRate(spotify.utils.IntEnum):
    BITRATE_160K = 0
    BITRATE_320K = 1
    BITRATE_96K = 2


class Ripper(threading.Thread):
    audio_file = None
    pcm_file = None
    wav_file = None
    rip_proc = None
    pipe = None
    ripping = False
    finished = False
    current_playlist = None
    current_album = None
    tracks_to_remove = []
    end_of_track = threading.Event()
    idx_digits = 3
    login_success = False
    progress = None
    sync = None
    dev_null = None
    fail_log_file = None
    success_tracks = []
    failure_tracks = []

    def __init__(self, args):
        threading.Thread.__init__(self)

        # set to a daemon thread
        self.daemon = True

        # initialize progress meter
        self.progress = Progress(args, self)

        self.args = args
        self.logged_in = threading.Event()
        self.logged_out = threading.Event()
        self.logged_out.set()

        config = spotify.Config()

        default_dir = default_settings_dir()

        # create a log file for rip failures
        if args.fail_log is not None:
            _base_dir = base_dir(args)
            if not os.path.exists(_base_dir):
                os.makedirs(_base_dir)

            encoding = "ascii" if args.ascii else "utf-8"
            self.fail_log_file = codecs.open(os.path.join(
                _base_dir, args.fail_log[0]), 'w', encoding)

        # application key location
        if args.key is not None:
            config.load_application_key_file(args.key[0])
        else:
            if not os.path.exists(default_dir):
                os.makedirs(default_dir)

            app_key_path = os.path.join(default_dir, "spotify_appkey.key")
            if not os.path.exists(app_key_path):
                print("\n" + Fore.YELLOW +
                      "Please copy your spotify_appkey.key to " +
                      default_dir + ", or use the --key|-k option" +
                      Fore.RESET)
                sys.exit(1)

            config.load_application_key_file(app_key_path)

        # settings directory
        if args.settings is not None:
            settings_dir = norm_path(args.settings[0])
            config.settings_location = settings_dir
            config.cache_location = settings_dir
        else:
            config.settings_location = default_dir
            config.cache_location = default_dir

        self.session = spotify.Session(config=config)
        self.session.volume_normalization = args.normalize

        bit_rates = dict([
            ('160', BitRate.BITRATE_160K),
            ('320', BitRate.BITRATE_320K),
            ('96', BitRate.BITRATE_96K)])
        self.session.preferred_bitrate(bit_rates[args.quality])
        self.session.on(spotify.SessionEvent.CONNECTION_STATE_UPDATED,
                        self.on_connection_state_changed)
        self.session.on(spotify.SessionEvent.END_OF_TRACK,
                        self.on_end_of_track)
        self.session.on(spotify.SessionEvent.MUSIC_DELIVERY,
                        self.on_music_delivery)
        self.session.on(spotify.SessionEvent.PLAY_TOKEN_LOST,
                        self.play_token_lost)
        self.session.on(spotify.SessionEvent.LOGGED_IN,
                        self.on_logged_in)

        self.event_loop = spotify.EventLoop(self.session)
        self.event_loop.start()

    def log_failure(self, track):
        self.failure_tracks.append(track)
        if self.fail_log_file is not None:
            self.fail_log_file.write(track.link.uri + "\n")

    def end_failure_log(self):
        if self.fail_log_file is not None:
            file_name = self.fail_log_file.name
            self.fail_log_file.flush()
            os.fsync(self.fail_log_file.fileno())
            self.fail_log_file.close()
            self.fail_log_file = None

            if os.path.getsize(file_name) == 0:
                rm_file(file_name)

    def print_summary(self):
        if len(self.success_tracks) + len(self.failure_tracks) <= 1:
            return

        def print_with_bullet(_str):
            if self.args.ascii:
                print(" * " + _str)
            else:
                print(" • " + _str)

        def log_tracks(tracks):
            for track in tracks:
                try:
                    track.load()
                    if (len(track.artists) > 0 and track.artists[0].name is not None
                        and track.name is not None):
                        print_with_bullet(track.artists[0].name + " - " +
                            track.name)
                    else:
                       print_with_bullet(track.link.uri)
                except spotify.Error as e:
                    print_with_bullet(track.link.uri)
            print("")

        if len(self.success_tracks) > 0:
            print(Fore.GREEN + "\nSuccess Summary (" + str(len(self.success_tracks)) +
                ")\n" + ("-" * 79) + Fore.RESET)
            log_tracks(self.success_tracks)
        if len(self.failure_tracks) > 0:
            print(Fore.RED + "\nFailure Summary (" + str(len(self.failure_tracks)) +
                ")\n" + ("-" * 79) + Fore.RESET)
            log_tracks(self.failure_tracks)

    def create_playlist_m3u(self, tracks):
        args = self.args
        if self.current_playlist is not None and args.playlist_m3u:
            _base_dir = base_dir(args)
            playlist_path = to_ascii(
                args, os.path.join(_base_dir, self.current_playlist.name + '.m3u')
            )

            print(Fore.GREEN + "Creating playlist m3u file " + playlist_path + Fore.RESET)

            encoding = "ascii" if args.ascii else "utf-8"
            with codecs.open(playlist_path, 'w', encoding) as playlist:
                for idx, track in enumerate(tracks):
                    _file = self.format_track_path(idx, track)
                    if os.path.exists(_file):
                        playlist.write(os.path.relpath(_file, _base_dir) + "\n")


    def run(self):
        args = self.args

        # login
        print("Logging in...")
        if args.last:
            self.login_as_last()
        elif args.user is not None and args.password is None:
            password = getpass.getpass()
            self.login(args.user[0], password)
        else:
            self.login(args.user[0], args.password[0])

        if not self.login_success:
            print(
                Fore.RED + "Encountered issue while logging into "
                           "Spotify, aborting..." + Fore.RESET)
            self.finished = True
            return

        # check if we were passed a file name or search
        if len(args.uri) == 1 and os.path.exists(args.uri[0]):
            uris = [line.strip() for line in open(args.uri[0])]
        elif len(args.uri) == 1 and not args.uri[0].startswith("spotify:"):
            uris = [list(self.search_query(args.uri[0]))]
        else:
            uris = args.uri

        def get_tracks_from_uri(uri):
            if isinstance(uri, list):
                return uri
            else:
                if (args.exclude_appears_on and
                        uri.startswith("spotify:artist:")):
                    album_uris = self.load_artist_albums(uri)
                    return itertools.chain(
                        *[self.load_link(album_uri) for
                          album_uri in album_uris])
                else:
                    return self.load_link(uri)

        # calculate total size and time
        all_tracks = []
        for uri in uris:
            tracks = get_tracks_from_uri(uri)
            all_tracks += list(tracks)

        self.progress.calc_total(all_tracks)

        if self.progress.total_size > 0:
            print(
                "Total Download Size: " +
                format_size(self.progress.total_size))

        # create track iterator
        for uri in uris:
            tracks = get_tracks_from_uri(uri)

            if args.flat_with_index and self.current_playlist:
                self.idx_digits = len(str(len(self.current_playlist.tracks)))

            if args.playlist_sync and self.current_playlist:
                self.sync = Sync(args, self)
                self.sync.sync_playlist(self.current_playlist)

            # ripping loop
            for idx, track in enumerate(tracks):
                try:
                    print('Loading track...')
                    track.load()
                    if track.availability != 1:
                        print(
                            Fore.RED + 'Track is not available, '
                                       'skipping...' + Fore.RESET)
                        self.log_failure(track)
                        continue

                    self.audio_file = self.format_track_path(idx, track)

                    if not args.overwrite and os.path.exists(self.audio_file):
                        print(
                            Fore.YELLOW + "Skipping " +
                            track.link.uri + Fore.RESET)
                        print(Fore.CYAN + self.audio_file + Fore.RESET)
                        self.queue_remove_from_playlist(idx)
                        continue

                    self.session.player.load(track)
                    self.prepare_rip(idx, track)
                    self.session.player.play()

                    self.end_of_track.wait()
                    self.end_of_track.clear()

                    self.finish_rip(track)

                    # update id3v2 with metadata and embed front cover image
                    set_metadata_tags(args, self.audio_file, track)

                    # make a note of the index and remove all the
                    # tracks from the playlist when everything is done
                    self.queue_remove_from_playlist(idx)

                except spotify.Error as e:
                    print(Fore.RED + "Spotify error detected" + Fore.RESET)
                    print(str(e))
                    print("Skipping to next track...")
                    self.session.player.play(False)
                    self.clean_up_partial()
                    self.log_failure(track)
                    continue

            # create playlist m3u file if needed
            self.create_playlist_m3u(tracks)

            # actually removing the tracks from playlist
            self.remove_tracks_from_playlist()

        # logout, we are done
        self.end_failure_log()
        self.print_summary()
        self.logout()
        self.finished = True

    def load_link(self, uri):
        # ignore if the uri is just blank (e.g. from a file)
        if not uri:
            return iter([])

        link = self.session.get_link(uri)
        if link.type == spotify.LinkType.TRACK:
            track = link.as_track()
            return iter([track])
        elif link.type == spotify.LinkType.PLAYLIST:
            self.current_playlist = link.as_playlist()
            print('Loading playlist...')
            self.current_playlist.load()
            return iter(self.current_playlist.tracks)
        elif link.type == spotify.LinkType.STARRED:
            link_user = link.as_user()
            if link_user is not None:
                starred = self.session.get_starred(link_user.canonical_name)
            else:
                starred = self.session.get_starred()

            if starred is not None:
                print('Loading starred playlist...')
                starred.load()
                return iter(starred.tracks)
            else:
                print(
                    Fore.RED + "Could not load starred playlist..." +
                    Fore.RESET)
                return iter([])
        elif link.type == spotify.LinkType.ALBUM:
            album = link.as_album()
            album_browser = album.browse()
            print('Loading album browser...')
            album_browser.load()
            self.current_album = album
            return iter(album_browser.tracks)
        elif link.type == spotify.LinkType.ARTIST:
            artist = link.as_artist()
            artist_browser = artist.browse()
            print('Loading artist browser...')
            artist_browser.load()
            return iter(artist_browser.tracks)
        return iter([])

    # excludes 'appears on' albums
    def load_artist_albums(self, uri):
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

    def search_query(self, query):
        args = self.args

        print("Searching for query: " + query)
        try:
            result = self.session.search(query)
            result.load()
        except spotify.Error as e:
            print(str(e))
            return iter([])

        # list tracks
        print(Fore.GREEN + "Results" + Fore.RESET)
        for track_idx, track in enumerate(result.tracks):
            print("  " + Fore.YELLOW + str(track_idx + 1) + Fore.RESET +
                  " [" + to_ascii(args, track.album.name) + "] " +
                  to_ascii(args, track.artists[0].name) + " - " +
                  to_ascii(args, track.name) +
                  " (" + str(track.popularity) + ")")

        pick = raw_input("Pick track(s) (ex 1-3,5): ")

        def get_track(i):
            if i >= 0 and i < len(result.tracks):
                return iter([result.tracks[i]])
            return iter([])

        pattern = re.compile("^[0-9 ,\-]+$")
        if pick.isdigit():
            pick = int(pick) - 1
            return get_track(pick)
        elif pick.lower() == "a" or pick.lower() == "all":
            return iter(result.tracks)
        elif pattern.match(pick):
            def range_string(comma_string):
                def hyphen_range(hyphen_string):
                    x = [int(x) - 1 for x in hyphen_string.split('-')]
                    return range(x[0], x[-1] + 1)

                return itertools.chain(
                    *[hyphen_range(r) for r in comma_string.split(',')])

            picks = sorted(set(list(range_string(pick))))
            return itertools.chain(*[get_track(p) for p in picks])

        if pick != "":
            print(Fore.RED + "Invalid selection" + Fore.RESET)
        return iter([])

    def clean_up_partial(self):
        if self.audio_file is not None and os.path.exists(self.audio_file):
            print(Fore.YELLOW + "Deleting partially ripped file" + Fore.RESET)
            rm_file(self.audio_file)

    def on_music_delivery(self, session, audio_format,
                          frame_bytes, num_frames):
        self.rip(session, audio_format, frame_bytes, num_frames)
        return num_frames

    def on_connection_state_changed(self, session):
        if session.connection.state is spotify.ConnectionState.LOGGED_IN:
            self.login_success = True
            self.logged_in.set()
            self.logged_out.clear()
        elif session.connection.state is spotify.ConnectionState.LOGGED_OUT:
            self.logged_in.clear()
            self.logged_out.set()

    def on_logged_in(self, session, error):
        if error is spotify.ErrorType.OK:
            print("Logged in as " + session.user.display_name)
        else:
            errorMap = {
                9: "CLIENT_TOO_OLD",
                8: "UNABLE_TO_CONTACT_SERVER",
                6: "BAD_USERNAME_OR_PASSWORD",
                7: "USER_BANNED",
                15: "USER_NEEDS_PREMIUM",
                16: "OTHER_TRANSIENT",
                10: "OTHER_PERMANENT"
            }
            print("Logged in failed: " +
                  errorMap.get(error, "UNKNOWN_ERROR_CODE: " + str(error)))
            self.login_success = False
            self.logged_in.set()

    def play_token_lost(self, session):
        print("\n" + Fore.RED + "Play token lost, aborting..." + Fore.RESET)
        self.session.player.play(False)
        self.clean_up_partial()
        self.finished = True

    def on_end_of_track(self, session):
        self.session.player.play(False)
        self.end_of_track.set()

    def login(self, user, password):
        """login into Spotify"""
        self.session.login(user, password, remember_me=True)
        self.logged_in.wait()

    def login_as_last(self):
        """login as the previous logged in user"""
        try:
            self.session.relogin()
            self.logged_in.wait()
        except spotify.Error as e:
            print(str(e))

    def logout(self):
        """logout from Spotify"""
        if self.logged_in.is_set():
            print('Logging out...')
            self.session.logout()
            self.logged_out.wait()
        self.event_loop.stop()

    def album_artists_web(self, uri):
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

    def format_track_path(self, idx, track):
        args = self.args
        _base_dir = base_dir(args)
        audio_file = args.format[0].strip()

        track_artist = to_ascii(
            args, escape_filename_part(track.artists[0].name))
        track_artists = to_ascii(args, ", ".join(
            [artist.name for artist in track.artists]))
        if len(track.artists) > 1:
            featuring_artists = to_ascii(args, ", ".join(
                [artist.name for artist in track.artists[1:]]))
        else:
            featuring_artists = ""

        album_artist = to_ascii(
            args,
            self.current_album.artist.name
            if self.current_album is not None else track_artist)
        album_artists_web = track_artists

        # only retrieve album_artist_web if it exists in the format string
        if (self.current_album is not None and
                audio_file.find("{album_artists_web}") >= 0):
            artist_array = self.album_artists_web(self.current_album.link.uri)
            if artist_array is not None:
                album_artists_web = to_ascii(args, ", ".join(artist_array))

        album = to_ascii(args, escape_filename_part(track.album.name))
        track_name = to_ascii(args, escape_filename_part(track.name))
        year = str(track.album.year)
        extension = args.output_type
        idx_str = str(idx)
        track_num = str(track.index)
        disc_num = str(track.disc)
        if self.current_playlist is not None:
            playlist_name = to_ascii(args, self.current_playlist.name)
            playlist_owner = to_ascii(args, self.current_playlist.owner.display_name)
        else:
            playlist_name = "No Playlist"
            playlist_owner = "No Playlist Owner"
        user = self.session.user.display_name

        tags = {
            "track_artist": track_artist,
            "track_artists": track_artists,
            "album_artist": album_artist,
            "album_artists_web": album_artists_web,
            "artist": track_artist,
            "artists": track_artists,
            "album": album,
            "track_name": track_name,
            "track": track_name,
            "year": year,
            "ext": extension,
            "extension": extension,
            "idx": idx_str,
            "index": idx_str,
            "track_num": track_num,
            "track_idx": track_num,
            "track_index": track_num,
            "disc_num": disc_num,
            "disc_idx": disc_num,
            "disc_index": disc_num,
            "playlist": playlist_name,
            "playlist_name": playlist_name,
            "playlist_owner": playlist_owner,
            "playlist_user": playlist_owner,
            "playlist_username": playlist_owner,
            "user": user,
            "username": user,
            "feat_artists": featuring_artists,
            "featuring_artists": featuring_artists
        }
        fill_tags = {"idx", "index", "track_num", "track_idx",
                     "track_index", "disc_num", "disc_idx", "disc_index"}
        prefix_tags = {"feat_artists", "featuring_artists"}
        for tag in tags.keys():
            audio_file = audio_file.replace("{" + tag + "}", tags[tag])
            if tag in fill_tags:
                match = re.search(r"\{" + tag + r":\d+\}", audio_file)
                if match:
                    tokens = audio_file[match.start():match.end()]\
                        .strip("{}").split(":")
                    tag_filled = tags[tag].zfill(int(tokens[1]))
                    audio_file = audio_file[:match.start()] + tag_filled + \
                        audio_file[match.end():]
            if tag in prefix_tags:
                # don't print prefix if there are no values
                if len(tags[tag]) > 0:
                    match = re.search(r"\{" + tag + r":[^\}]+\}", audio_file)
                    if match:
                        tokens = audio_file[match.start():match.end()]\
                            .strip("{}").split(":")
                        audio_file = audio_file[:match.start()] + tokens[1] + \
                            " " + tags[tag] + audio_file[match.end():]
                else:
                    match = re.search(r"\s*\{" + tag + r":[^\}]+\}", audio_file)
                    if match:
                        audio_file = audio_file[:match.start()] + audio_file[match.end():]

        # in case the file name is too long
        def truncate(_str, max_size):
            return _str[:max_size].strip() if len(_str) > max_size else _str

        def truncate_dir_path(dir_path):
            path_tokens = dir_path.split(os.pathsep)
            path_tokens = [truncate(token, 255) for token in path_tokens]
            return os.pathsep.join(path_tokens)

        def truncate_file_name(file_name):
            tokens = file_name.rsplit(os.extsep, 1)
            if len(tokens) > 1:
                tokens[0] = truncate(tokens[0], 255 - len(tokens[1]) - 1)
            else:
                tokens[0] = truncate(tokens[0], 255)
            return os.extsep.join(tokens)

        # ensure each component in path is no more than 255 chars long
        tokens = audio_file.rsplit(os.pathsep, 1)
        if len(tokens) > 1:
            audio_file = os.path.join(
                truncate_dir_path(tokens[0]), truncate_file_name(tokens[1]))
        else:
            audio_file = truncate_file_name(tokens[0])

        # prepend base_dir
        audio_file = to_ascii(args, os.path.join(_base_dir, audio_file))

        # create directory if it doesn't exist
        audio_path = os.path.dirname(audio_file)
        if not os.path.exists(audio_path):
            os.makedirs(audio_path)

        return audio_file

    def prepare_rip(self, idx, track):
        args = self.args

        # reset progress
        self.progress.prepare_track(track)

        if self.progress.total_tracks > 1:
            print(Fore.GREEN + "[ " + str(idx + 1) + " / " + str(
                self.progress.total_tracks) + " ] Ripping " +
                  track.link.uri + Fore.RESET)
        else:
            print(Fore.GREEN + "Ripping " + track.link.uri + Fore.RESET)
        print(Fore.CYAN + self.audio_file + Fore.RESET)

        file_size = calc_file_size(self.args, track)
        print("Track Download Size: " + format_size(file_size))

        if args.output_type == "wav":
            self.wav_file = wave.open(self.audio_file, "wb")
            self.wav_file.setparams((2, 2, 44100, 0, 'NONE', 'not compressed'))
        elif args.output_type == "pcm":
            self.pcm_file = open(self.audio_file, 'wb')
        elif args.output_type == "flac":
            self.rip_proc = Popen(
                ["flac", "-f", str("-" + args.comp), "--silent", "--endian",
                 "little", "--channels", "2", "--bps", "16", "--sample-rate",
                 "44100", "--sign", "signed", "-o", self.audio_file, "-"],
                stdin=PIPE)
        elif args.output_type == "alac.m4a":
            self.rip_proc = Popen(
                ["avconv", "-nostats", "-loglevel", "0", "-f", "s16le", "-ar", "44100", "-ac", "2", "-channel_layout", "stereo", "-i", "-", "-acodec", "alac", self.audio_file],
                stdin=PIPE)
        elif args.output_type == "ogg":
            if args.cbr:
                self.rip_proc = Popen(
                    ["oggenc", "--quiet", "--raw", "-b", args.bitrate, "-o",
                     self.audio_file, "-"], stdin=PIPE)
            else:
                self.rip_proc = Popen(
                    ["oggenc", "--quiet", "--raw", "-q", args.vbr, "-o",
                     self.audio_file, "-"], stdin=PIPE)
        elif args.output_type == "opus":
            if args.cbr:
                self.rip_proc = Popen(
                    ["opusenc", "--quiet", "--comp", args.comp, "--cvbr",
                     "--bitrate", str(int(args.bitrate) / 2), "--raw",
                     "--raw-rate", "44100", "-", self.audio_file], stdin=PIPE)
            else:
                self.rip_proc = Popen(
                    ["opusenc", "--quiet", "--comp", args.comp, "--vbr",
                     "--bitrate", args.vbr, "--raw", "--raw-rate", "44100",
                     "-", self.audio_file], stdin=PIPE)
        elif args.output_type == "aac":
            if self.dev_null is None:
                self.dev_null = open(os.devnull, 'wb')
            if args.cbr:
                self.rip_proc = Popen(
                    ["faac", "-P", "-X", "-b", args.bitrate, "-o",
                     self.audio_file, "-"], stdin=PIPE,
                    stdout=self.dev_null, stderr=self.dev_null)
            else:
                self.rip_proc = Popen(
                    ["faac", "-P", "-X", "-q", args.vbr, "-o",
                     self.audio_file, "-"], stdin=PIPE,
                    stdout=self.dev_null, stderr=self.dev_null)
        elif args.output_type == "m4a":
            if args.cbr:
                self.rip_proc = Popen(
                    ["fdkaac", "-S", "-R", "-b",
                     args.bitrate, "-o", self.audio_file, "-"], stdin=PIPE)
            else:
                self.rip_proc = Popen(
                    ["fdkaac", "-S", "-R", "-m", args.vbr,
                     "-o", self.audio_file, "-"], stdin=PIPE)
        elif args.output_type == "mp3":
            lame_args = ["lame", "--silent"]

            if args.stereo_mode is not None:
                lame_args.extend(["-m", args.stereo_mode])

            if args.cbr:
                lame_args.extend(["-cbr", "-b", args.bitrate])
            else:
                lame_args.extend(["-V", args.vbr])

            lame_args.extend(["-h", "-r", "-", self.audio_file])
            self.rip_proc = Popen(lame_args, stdin=PIPE)

        if self.rip_proc is not None:
            self.pipe = self.rip_proc.stdin

        self.ripping = True

    def finish_rip(self, track):
        self.progress.end_track()
        if self.pipe is not None:
            print(Fore.GREEN + 'Rip complete' + Fore.RESET)
            self.pipe.flush()
            self.pipe.close()

            # wait for process to end before continuing
            ret_code = self.rip_proc.wait()
            if ret_code != 0:
                print(
                    Fore.YELLOW + "Warning: encoder returned non-zero "
                                  "error code " + str(ret_code) + Fore.RESET)
            self.rip_proc = None
            self.pipe = None

        if self.wav_file is not None:
            self.wav_file.close()
            self.wav_file = None

        if self.pcm_file is not None:
            self.pcm_file.flush()
            os.fsync(self.pcm_file.fileno())
            self.pcm_file.close()
            self.pcm_file = None

        self.ripping = False
        self.success_tracks.append(track)

    def rip(self, session, audio_format, frame_bytes, num_frames):
        if self.ripping:
            self.progress.update_progress(num_frames, audio_format)
            if self.pipe is not None:
                self.pipe.write(frame_bytes)

            if self.wav_file is not None:
                self.wav_file.writeframes(frame_bytes)

            if self.pcm_file is not None:
              self.pcm_file.write(frame_bytes)

    def abort(self):
        self.session.player.play(False)
        self.clean_up_partial()
        self.remove_tracks_from_playlist()
        self.end_failure_log()
        self.print_summary()
        self.logout()
        self.finished = True

    def queue_remove_from_playlist(self, idx):
        if self.args.remove_from_playlist:
            if self.current_playlist:
                if self.current_playlist.owner.canonical_name == self.session.user.canonical_name:
                    self.tracks_to_remove.append(idx)
                else:
                    print(Fore.RED +
                          "This track will not be removed from playlist " +
                          self.current_playlist.name + " since " +
                          self.session.user.canonical_name +
                          " is not the playlist owner..." + Fore.RESET)
            else:
                print(Fore.RED +
                      "No playlist specified to remove this track from. " +
                      "Did you use '-r' without a playlist link?" + Fore.RESET)

    def remove_tracks_from_playlist(self):
        if self.args.remove_from_playlist and \
                self.current_playlist and len(self.tracks_to_remove) > 0:
            print(Fore.YELLOW +
                  "Removing successfully ripped tracks from playlist " +
                  self.current_playlist.name + "..." + Fore.RESET)

            self.current_playlist.remove_tracks(self.tracks_to_remove)
            self.session.process_events()

            while self.current_playlist.has_pending_changes:
                time.sleep(0.1)
