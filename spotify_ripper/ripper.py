# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from subprocess import Popen, PIPE
from colorama import Fore, Style
from spotify_ripper.utils import *
from spotify_ripper.tags import set_metadata_tags
from spotify_ripper.progress import Progress
from spotify_ripper.post_actions import PostActions
from spotify_ripper.web import WebAPI
from spotify_ripper.sync import Sync
from spotify_ripper.eventloop import EventLoop
from datetime import datetime
import os
import sys
import time
import threading
import spotify
import getpass
import itertools
import wave
import re
import select

try:
    # Python 3
    import queue
except ImportError:
    # Python 2
    import Queue as queue


class BitRate(spotify.utils.IntEnum):
    BITRATE_160K = 0
    BITRATE_320K = 1
    BITRATE_96K = 2


class Ripper(threading.Thread):
    name = 'SpotifyRipperThread'

    audio_file = None
    pcm_file = None
    wav_file = None
    rip_proc = None
    pipe = None
    current_playlist = None
    current_album = None
    current_chart = None

    login_success = False
    progress = None
    sync = None
    post = None
    web = None
    dev_null = None
    stop_time = None

    rip_queue = queue.Queue()

    # threading events
    logged_in = threading.Event()
    logged_out = threading.Event()
    ripper_continue = threading.Event()
    ripping = threading.Event()
    end_of_track = threading.Event()
    finished = threading.Event()
    abort = threading.Event()
    skip = threading.Event()

    def __init__(self, args):
        threading.Thread.__init__(self)

        # initialize progress meter
        self.progress = Progress(args, self)

        self.args = args

        # initially logged-out
        self.logged_out.set()

        config = spotify.Config()
        default_dir = default_settings_dir()

        self.post = PostActions(args, self)
        self.web = WebAPI(args, self)

        # application key location
        if args.key is not None:
            config.load_application_key_file(args.key[0])
        else:
            if not path_exists(default_dir):
                os.makedirs(enc_str(default_dir))

            app_key_path = os.path.join(default_dir, "spotify_appkey.key")
            if not path_exists(app_key_path):
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

        # disable scrobbling
        self.session.social.set_scrobbling(
            spotify.SocialProvider.SPOTIFY,
            spotify.ScrobblingState.LOCAL_DISABLED)
        self.session.social.set_scrobbling(
            spotify.SocialProvider.FACEBOOK,
            spotify.ScrobblingState.LOCAL_DISABLED)
        self.session.social.set_scrobbling(
            spotify.SocialProvider.LASTFM,
            spotify.ScrobblingState.LOCAL_DISABLED)

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

        self.event_loop = EventLoop(self.session, 0.1, self)

    def stop_event_loop(self):
        if self.event_loop.isAlive():
            self.event_loop.stop()
            self.event_loop.join()

    # executes on main thread (not SpotifyRipper thread)
    def login(self):
        args = self.args

        print("Logging in...")
        if args.last:
            self.login_as_last()

        if not self.login_success and args.user is not None:
            if args.password is None:
                password = getpass.getpass()
                self.login_as_user(args.user[0], password)
            else:
                self.login_as_user(args.user[0], args.password[0])

        return self.login_success

    def run(self):
        args = self.args

        # start event loop
        self.event_loop.start()

        # wait for main thread to login
        self.ripper_continue.wait()
        if self.abort.is_set():
            return

        # check if we were passed a file name or search
        if len(args.uri) == 1 and path_exists(args.uri[0]):
            uris = [line.strip() for line in open(args.uri[0])]
        elif len(args.uri) == 1 and not args.uri[0].startswith("spotify:"):
            uris = [list(self.search_query(args.uri[0]))]
        else:
            uris = args.uri

        def get_tracks_from_uri(uri):
            current_playlist = None
            current_album = None
            current_chart = None

            if isinstance(uri, list):
                return uri
            else:
                if (args.exclude_appears_on and
                        uri.startswith("spotify:artist:")):
                    album_uris = self.web.get_non_appears_on_albums(uri)
                    return itertools.chain(
                        *[self.load_link(album_uri) for
                          album_uri in album_uris])
                elif uri.startswith("spotify:charts:"):
                    charts = self.web.get_charts(uri)
                    if charts is not None:
                        self.current_chart = charts
                        chart_uris = [t["track"]["uri"] for t in charts["entries"]["items"]]
                        return itertools.chain(
                            *[self.load_link(chart_uri) for
                              chart_uri in chart_uris])
                    else:
                        return iter([])
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
            if self.abort.is_set():
                break

            tracks = list(get_tracks_from_uri(uri))

            if args.playlist_sync and self.current_playlist:
                self.sync = Sync(args, self)
                self.sync.sync_playlist(self.current_playlist)

            # ripping loop
            for idx, track in enumerate(tracks):
                try:
                    self.check_stop_time()
                    self.skip.clear()

                    if self.abort.is_set():
                        break

                    print('Loading track...')
                    track.load()
                    if track.availability != 1:
                        print(
                            Fore.RED + 'Track is not available, '
                                       'skipping...' + Fore.RESET)
                        self.post.log_failure(track)
                        continue

                    self.audio_file = self.format_track_path(idx, track)

                    if not args.overwrite and path_exists(self.audio_file):
                        print(
                            Fore.YELLOW + "Skipping " +
                            track.link.uri + Fore.RESET)
                        print(Fore.CYAN + self.audio_file + Fore.RESET)
                        self.post.queue_remove_from_playlist(idx)
                        continue

                    self.session.player.load(track)
                    self.prepare_rip(idx, track)
                    self.session.player.play()

                    timeout_count = 0
                    while not self.end_of_track.is_set() or \
                            not self.rip_queue.empty():
                        try:
                            if self.abort.is_set() or self.skip.is_set():
                                break

                            rip_item = self.rip_queue.get(timeout=1)

                            if self.abort.is_set() or self.skip.is_set():
                                break

                            self.rip(self.session, rip_item[0],
                                     rip_item[1], rip_item[2])
                        except queue.Empty:
                            timeout_count += 1
                            if timeout_count > 60:
                                raise spotify.Error("Timeout while "
                                                    "ripping track")

                    if self.skip.is_set():
                        print("\n" + Fore.YELLOW +
                            "User skipped track... " + Fore.RESET)
                        self.session.player.play(False)
                        self.post.clean_up_partial()
                        self.post.log_failure(track)
                        self.end_of_track.clear()
                        self.progress.end_track(show_end=False)
                        self.ripping.clear()
                        continue

                    if self.abort.is_set():
                        self.session.player.play(False)
                        self.end_of_track.set()
                        self.post.clean_up_partial()
                        self.post.log_failure(track)
                        break

                    self.end_of_track.clear()

                    self.finish_rip(track)

                    # update id3v2 with metadata and embed front cover image
                    set_metadata_tags(args, self.audio_file, idx, track, self)

                    # make a note of the index and remove all the
                    # tracks from the playlist when everything is done
                    self.post.queue_remove_from_playlist(idx)

                except (spotify.Error, Exception) as e:
                    if isinstance(e, Exception):
                        print(Fore.RED + "Spotify error detected" + Fore.RESET)
                    print(str(e))
                    print("Skipping to next track...")
                    self.session.player.play(False)
                    self.post.clean_up_partial()
                    self.post.log_failure(track)
                    continue

            # create playlist m3u file if needed
            self.post.create_playlist_m3u(tracks)

            # create playlist wpl file if needed
            self.post.create_playlist_wpl(tracks)

            # actually removing the tracks from playlist
            self.post.remove_tracks_from_playlist()

        # logout, we are done
        self.post.end_failure_log()
        self.post.print_summary()
        self.logout()
        self.stop_event_loop()
        self.finished.set()

    def check_stop_time(self):
        args = self.args

        def stop_time_triggered():
            print(Fore.YELLOW + "Stop time of " +
                  self.stop_time.strftime("%H:%M") +
                  " has been triggered, stopping..." + Fore.RESET)

            if args.resume_after is not None:
                resume_time = parse_time_str(args.resume_after)
                print(Fore.YELLOW + "Script will resume at " +
                      resume_time.strftime("%H:%M") + Fore.RESET)
                while datetime.now() < resume_time:
                    time.sleep(60)
                self.stop_time = None
            else:
                self.abort.set()

        if args.stop_after is not None:
            if self.stop_time is None:
                self.stop_time = parse_time_str(args.stop_after)
                print(Fore.YELLOW + "Script will stop after " +
                      self.stop_time.strftime("%H:%M") + Fore.RESET)

            if self.stop_time < datetime.now():
                stop_time_triggered()

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
            attempt_count = 1
            while self.current_playlist is None:
                if attempt_count > 3:
                    print(Fore.RED + "Could not load playlist..." +
                          Fore.RESET)
                    return iter([])
                print("Attempt " + str(attempt_count) + " failed: Spotify " +
                      "returned None for playlist, trying again in 5 " +
                      "seconds...")
                time.sleep(5.0)
                self.current_playlist = link.as_playlist()
                attempt_count += 1

            print('Loading playlist...')
            self.current_playlist.load()
            return iter(self.current_playlist.tracks)
        elif link.type == spotify.LinkType.STARRED:
            link_user = link.as_user()

            def load_starred():
                if link_user is not None:
                    return self.session.get_starred(link_user.canonical_name)
                else:
                    return self.session.get_starred()
            starred = load_starred()

            attempt_count = 1
            while starred is None:
                if attempt_count > 3:
                    print(Fore.RED + "Could not load starred playlist..." +
                          Fore.RESET)
                    return iter([])
                print("Attempt " + str(attempt_count) + " failed: Spotify " +
                      "returned None for starred playlist, trying again in " +
                      "5 seconds...")
                time.sleep(5.0)
                starred = load_starred()
                attempt_count += 1

            print('Loading starred playlist...')
            starred.load()
            return iter(starred.tracks)
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

    def search_query(self, query):
        print("Searching for query: " + query)

        try:
            result = self.session.search(query)
            result.load()
        except spotify.Error as e:
            print(str(e))
            return iter([])

        if len(result.tracks) == 0:
            print(Fore.RED + "No Results" + Fore.RESET)
            return iter([])

        # list tracks
        print(Fore.GREEN + "Results" + Fore.RESET)
        for track_idx, track in enumerate(result.tracks):
            print("  " + Fore.YELLOW + str(track_idx + 1) + Fore.RESET +
                  " [" + to_ascii(track.album.name) + "] " +
                  to_ascii(track.artists[0].name) + " - " +
                  to_ascii(track.name) +
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

    def on_music_delivery(self, session, audio_format,
                          frame_bytes, num_frames):
        try:
            self.rip_queue.put_nowait((audio_format.sample_rate,
                                       frame_bytes, num_frames))
        except queue.Full:
            print(Fore.RED + "rip_queue is full. dropped music data" +
                  Fore.RESET)
        return num_frames

    def on_connection_state_changed(self, session):
        if session.connection.state is spotify.ConnectionState.LOGGED_IN:
            self.login_success = True
            self.logged_in.set()
            self.logged_out.clear()
        elif session.connection.state is spotify.ConnectionState.LOGGED_OUT:
            self.logged_in.clear()
            self.ripper_continue.clear()
            self.logged_out.set()

    def on_logged_in(self, session, error):
        if error is spotify.ErrorType.OK:
            print("Logged in as " + session.user.display_name)
        else:
            error_map = {
                9: "CLIENT_TOO_OLD",
                8: "UNABLE_TO_CONTACT_SERVER",
                6: "BAD_USERNAME_OR_PASSWORD",
                7: "USER_BANNED",
                15: "USER_NEEDS_PREMIUM",
                16: "OTHER_TRANSIENT",
                10: "OTHER_PERMANENT"
            }
            print("Logged in failed: " +
                  error_map.get(error, "UNKNOWN_ERROR_CODE: " + str(error)))
            self.login_success = False
            self.logged_in.set()

    def play_token_lost(self, session):
        print("\n" + Fore.RED + "Play token lost, aborting..." + Fore.RESET)
        self.abort_rip()

    def on_end_of_track(self, session):
        self.session.player.play(False)
        self.end_of_track.set()

    def login_as_user(self, user, password):
        """login into Spotify"""
        self.session.login(user, password, remember_me=True)
        self.logged_in.wait()

    def login_as_last(self):
        """login as the previous logged in user"""
        try:
            self.session.relogin()
            self.logged_in.wait()
        except spotify.Error as e:
            self.login_success = False
            print(str(e))

    def logout(self):
        """logout from Spotify"""
        time.sleep(0.1)
        if self.logged_in.is_set():
            print('Logging out...')
            self.session.logout()
            self.logged_out.wait()

    def format_track_path(self, idx, track):
        args = self.args

        audio_file = \
            format_track_string(self, args.format[0].strip(), idx, track)

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

        # replace filename
        if args.replace is not None:
            audio_file = self.replace_filename(audio_file, args.replace)

        # remove not allowed characters in filename and encode utf-8
        audio_file = audio_file.replace('*."/\[]:;|=,', '')

        # prepend base_dir
        audio_file = to_ascii(os.path.join(base_dir(), audio_file))

        if args.normalized_ascii:
            audio_file = to_normalized_ascii(audio_file)

        # create directory if it doesn't exist
        audio_path = os.path.dirname(audio_file)
        if not path_exists(audio_path):
            os.makedirs(enc_str(audio_path))

        return audio_file

    def replace_filename(self, filename, pattern_list):
        for pattern in pattern_list:
            repl = pattern.split('/')
            filename = re.sub(repl[0], repl[1], filename)
        return filename

    def prepare_rip(self, idx, track):
        args = self.args

        # reset progress
        self.progress.prepare_track(track)

        if self.progress.total_tracks > 1:
            print(Fore.GREEN + "[ " + str(idx + 1) + " / " +
                  str(self.progress.total_tracks +
                      self.progress.skipped_tracks) + " ] Ripping " +
                  track.link.uri + Fore.WHITE + Style.DIM +
                  "\t(ESC to skip)" + Style.RESET_ALL)
        else:
            print(Fore.GREEN + "Ripping " + track.link.uri + Fore.RESET)
        print(Fore.CYAN + self.audio_file + Fore.RESET)

        file_size = calc_file_size(track)
        print("Track Download Size: " + format_size(file_size))

        audio_file_enc = enc_str(self.audio_file)

        if args.output_type == "wav":
            self.wav_file = wave.open(audio_file_enc, "wb")
            self.wav_file.setparams((2, 2, 44100, 0, 'NONE', 'not compressed'))
        elif args.output_type == "pcm":
            self.pcm_file = open(audio_file_enc, 'wb')
        elif args.output_type == "flac":
            self.rip_proc = Popen(
                ["flac", "-f", ("-" + str(args.comp)), "--silent", "--endian",
                 "little", "--channels", "2", "--bps", "16", "--sample-rate",
                 "44100", "--sign", "signed", "-o", audio_file_enc, "-"],
                stdin=PIPE)
        elif args.output_type == "alac.m4a":
            self.rip_proc = Popen(
                ["avconv", "-nostats", "-loglevel", "0", "-f", "s16le", "-ar",
                 "44100", "-ac", "2", "-channel_layout", "stereo", "-i", "-",
                 "-acodec", "alac", audio_file_enc],
                stdin=PIPE)
        elif args.output_type == "ogg":
            if args.cbr:
                self.rip_proc = Popen(
                    ["oggenc", "--quiet", "--raw", "-b", args.bitrate, "-o",
                     audio_file_enc, "-"], stdin=PIPE)
            else:
                self.rip_proc = Popen(
                    ["oggenc", "--quiet", "--raw", "-q", args.vbr, "-o",
                     audio_file_enc, "-"], stdin=PIPE)
        elif args.output_type == "opus":
            if args.cbr:
                self.rip_proc = Popen(
                    ["opusenc", "--quiet", "--comp", args.comp, "--cvbr",
                     "--bitrate", str(int(args.bitrate) / 2), "--raw",
                     "--raw-rate", "44100", "-", audio_file_enc], stdin=PIPE)
            else:
                self.rip_proc = Popen(
                    ["opusenc", "--quiet", "--comp", args.comp, "--vbr",
                     "--bitrate", args.vbr, "--raw", "--raw-rate", "44100",
                     "-", audio_file_enc], stdin=PIPE)
        elif args.output_type == "aac":
            if self.dev_null is None:
                self.dev_null = open(os.devnull, 'wb')
            if args.cbr:
                self.rip_proc = Popen(
                    ["faac", "-P", "-X", "-b", args.bitrate, "-o",
                     audio_file_enc, "-"], stdin=PIPE,
                    stdout=self.dev_null, stderr=self.dev_null)
            else:
                self.rip_proc = Popen(
                    ["faac", "-P", "-X", "-q", args.vbr, "-o",
                     audio_file_enc, "-"], stdin=PIPE,
                    stdout=self.dev_null, stderr=self.dev_null)
        elif args.output_type == "m4a":
            if args.cbr:
                self.rip_proc = Popen(
                    ["fdkaac", "-S", "-R", "-b",
                     args.bitrate, "-o", audio_file_enc, "-"], stdin=PIPE)
            else:
                self.rip_proc = Popen(
                    ["fdkaac", "-S", "-R", "-m", args.vbr,
                     "-o", audio_file_enc, "-"], stdin=PIPE)
        elif args.output_type == "mp3":
            lame_args = ["lame", "--silent"]

            if args.stereo_mode is not None:
                lame_args.extend(["-m", args.stereo_mode])

            if args.cbr:
                lame_args.extend(["-cbr", "-b", args.bitrate])
            else:
                lame_args.extend(["-V", args.vbr])

            lame_args.extend(["-h", "-r", "-", audio_file_enc])
            self.rip_proc = Popen(lame_args, stdin=PIPE)

        if self.rip_proc is not None:
            self.pipe = self.rip_proc.stdin

        self.ripping.set()

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

        self.ripping.clear()
        self.post.log_success(track)

    def rip(self, session, sample_rate, frame_bytes, num_frames):
        if self.ripping.is_set():
            self.progress.update_progress(num_frames, sample_rate)
            if self.pipe is not None:
                self.pipe.write(frame_bytes)

            if self.wav_file is not None:
                self.wav_file.writeframes(frame_bytes)

            if self.pcm_file is not None:
                self.pcm_file.write(frame_bytes)

    def abort_rip(self):
        self.ripping.clear()
        self.abort.set()
