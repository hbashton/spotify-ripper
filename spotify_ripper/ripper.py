# -*- coding: utf8 -*-

from __future__ import unicode_literals

from subprocess import Popen, PIPE
from colorama import Fore, Style
from spotify_ripper.utils import *
from spotify_ripper.id3 import set_id3_and_cover
import os, sys
import time
import threading
import spotify
import getpass
import itertools

class BitRate(spotify.utils.IntEnum):
    BITRATE_160K = 0
    BITRATE_320K = 1
    BITRATE_96K  = 2

class Ripper(threading.Thread):
    mp3_file = None
    pcm_file = None
    rip_proc = None
    pipe = None
    ripping = False
    finished = False
    current_playlist = None
    tracks_to_remove = []
    end_of_track = threading.Event()
    idx_digits = 3

    def __init__(self, args):
        threading.Thread.__init__(self)

        # set to a daemon thread
        self.daemon = True

        self.args = args
        self.logged_in = threading.Event()
        self.logged_out = threading.Event()
        self.logged_out.set()

        config = spotify.Config()

        default_dir = default_settings_dir()

        # application key location
        if args.key is not None:
            config.load_application_key_file(args.key[0])
        else:
            if not os.path.exists(default_dir):
                os.makedirs(default_dir)

            app_key_path = os.path.join(default_dir, "spotify_appkey.key")
            if not os.path.exists(app_key_path):
                print("\n" + Fore.YELLOW + "Please copy your spotify_appkey.key to " + default_dir +
                    ", or use the --key|-k option" + Fore.RESET)
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

        bit_rates = dict([
            ('160', BitRate.BITRATE_160K),
            ('320', BitRate.BITRATE_320K),
            ('96', BitRate.BITRATE_96K)])
        self.session.preferred_bitrate(bit_rates[args.bitrate])
        self.session.on(spotify.SessionEvent.CONNECTION_STATE_UPDATED,
            self.on_connection_state_changed)
        self.session.on(spotify.SessionEvent.END_OF_TRACK,
            self.on_end_of_track)
        self.session.on(spotify.SessionEvent.MUSIC_DELIVERY,
            self.on_music_delivery)
        self.session.on(spotify.SessionEvent.PLAY_TOKEN_LOST,
            self.play_token_lost)

        self.event_loop = spotify.EventLoop(self.session)
        self.event_loop.start()

    def run(self):
        args = self.args

        # login
        print("Logging in...")
        if args.last:
            self.login_as_last()
        elif args.user != None and args.password == None:
            password = getpass.getpass()
            self.login(args.user[0], password)
        else:
            self.login(args.user[0], args.password[0])

        # create track iterator
        if os.path.exists(args.uri):
            tracks = itertools.chain(*[self.load_link(line.strip()) for line in open(args.uri)])
        elif args.uri.startswith("spotify:"):
            tracks = self.load_link(args.uri)
        else:
            tracks = self.search_query(args.uri)

        if args.Flat and self.current_playlist:
            self.idx_digits = len(str(len(self.current_playlist.tracks)))

        # ripping loop
        for idx, track in enumerate(tracks):
            try:
                print('Loading track...')
                track.load()
                if track.availability != 1:
                    print(Fore.RED + 'Track is not available, skipping...' + Fore.RESET)
                    continue

                self.prepare_path(idx, track)

                if not args.overwrite and os.path.exists(self.mp3_file):
                    print(Fore.YELLOW + "Skipping " + track.link.uri + Fore.RESET)
                    print(Fore.CYAN + self.mp3_file + Fore.RESET)
                    continue

                self.session.player.load(track)
                self.prepare_rip(track)
                self.duration = track.duration
                self.position = 0
                self.session.player.play()

                self.end_of_track.wait()
                self.end_of_track.clear()

                self.end_progress()
                self.finish_rip(track)

                # update id3v2 with metadata and embed front cover image
                set_id3_and_cover(args, self.mp3_file, track)

                if args.remove_from_playlist:
                    if self.current_playlist:
                        if self.current_playlist.owner.canonical_name == self.session.user.canonical_name:
                            # since removing is instant we make a note of the index
                            # and remove the indexes when everything is done
                            self.tracks_to_remove.append(idx)
                        else:
                            print(Fore.RED + "This track will not be removed from playlist " +
                                self.current_playlist.name + " since " + self.session.user.canonical_name +
                                " is not the playlist owner..." + Fore.RESET)
                    else:
                        print(Fore.RED + "No playlist specified to remove this track from. " +
                                "Did you use '-r' without a playlist link?" + Fore.RESET)

            except spotify.Error as e:
                print(Fore.RED + "Spotify error detected" + Fore.RESET)
                print(str(e))
                print("Skipping to next track...")
                self.session.player.play(False)
                self.clean_up_partial()
                continue

        # actually removing the tracks from playlist
        if args.remove_from_playlist and self.current_playlist and len(self.tracks_to_remove) > 0:
            print(Fore.YELLOW + "Removing successfully ripped tracks from playlist " +
                    self.current_playlist.name + "..." + Fore.RESET)

            self.current_playlist.remove_tracks(self.tracks_to_remove)
            self.session.process_events()

            while self.current_playlist.has_pending_changes:
                time.sleep(0.1)

        # logout, we are done
        self.logout()
        self.finished = True

    def load_link(self, uri):
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
            starred = link.as_playlist()
            print('Loading starred playlist...')
            starred.load()
            return iter(starred.tracks)
        elif link.type == spotify.LinkType.ALBUM:
            album = link.as_album()
            album_browser = album.browse()
            print('Loading album browser...')
            album_browser.load()
            return iter(album_browser.tracks)
        elif link.type == spotify.LinkType.ARTIST:
            artist = link.as_artist()
            artist_browser = artist.browse()
            print('Loading artist browser...')
            artist_browser.load()
            return iter(artist_browser.tracks)
        return iter([])

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
            print("  " + Fore.YELLOW + str(track_idx + 1) + Fore.RESET + " [" + to_ascii(args, track.album.name) + "] " + to_ascii(args, track.artists[0].name) + " - " + to_ascii(args, track.name) + " (" + str(track.popularity) + ")")

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
                    return range(x[0], x[-1]+1)
                return itertools.chain(*[hyphen_range(r) for r in comma_string.split(',')])
            picks = sorted(set(list(range_string(pick))))
            return itertools.chain(*[get_track(p) for p in picks])

        if pick != "":
            print(Fore.RED + "Invalid selection" + Fore.RESET)
        return iter([])

    def clean_up_partial(self):
        if os.path.exists(self.mp3_file):
            print(Fore.YELLOW + "Deleting partially ripped file" + Fore.RESET)
            rm_file(self.mp3_file)

    def on_music_delivery(self, session, audio_format, frame_bytes, num_frames):
        self.rip(session, audio_format, frame_bytes, num_frames)
        return num_frames

    def on_connection_state_changed(self, session):
        if session.connection.state is spotify.ConnectionState.LOGGED_IN:
            self.logged_in.set()
            self.logged_out.clear()
        elif session.connection.state is spotify.ConnectionState.LOGGED_OUT:
            self.logged_in.clear()
            self.logged_out.set()

    def play_token_lost(self, session):
        print("\n"  + Fore.RED + "Play token lost, aborting..." + Fore.RESET)
        self.session.player.play(False)
        self.clean_up_partial()
        self.finished = True

    def on_end_of_track(self, session):
        self.session.player.play(False)
        self.end_of_track.set()

    def login(self, user, password):
        "login into Spotify"
        self.session.login(user, password, remember_me=True)
        self.logged_in.wait()

    def login_as_last(self):
        "login as the previous logged in user"
        try:
            self.session.relogin()
            self.logged_in.wait()
        except spotify.Error as e:
            print(str(e))

    def logout(self):
        "logout from Spotify"
        if self.logged_in.is_set():
            print('Logging out...')
            self.session.logout()
            self.logged_out.wait()
        self.event_loop.stop()

    def prepare_path(self, idx, track):
        args = self.args
        base_dir = norm_path(args.directory[0]) if args.directory != None else os.getcwd()

        artist = to_ascii(args, escape_filename_part(track.artists[0].name))
        album = to_ascii(args, escape_filename_part(track.album.name))
        track_name = to_ascii(args, escape_filename_part(track.name))
        if args.flat:
            self.mp3_file = to_ascii(args, os.path.join(base_dir, artist + " - " + track_name + ".mp3"))
        elif args.Flat:
            filled_idx = str(idx).zfill(self.idx_digits)
            self.mp3_file = to_ascii(args, os.path.join(base_dir, filled_idx + " - " + artist + " - " + track_name + ".mp3"))
        else:
            self.mp3_file = to_ascii(args, os.path.join(base_dir, artist, album, artist + " - " + track_name + ".mp3"))

        # create directory if it doesn't exist
        mp3_path = os.path.dirname(self.mp3_file)
        if not os.path.exists(mp3_path):
            os.makedirs(mp3_path)

    def prepare_rip(self, track):
        args = self.args

        print(Fore.GREEN + "Ripping " + track.link.uri + Fore.RESET)
        print(Fore.CYAN + self.mp3_file + Fore.RESET)
        if args.cbr:
            self.rip_proc = Popen(["lame", "--silent", "-cbr", "-b", args.bitrate, "-h", "-r", "-", self.mp3_file], stdin=PIPE)
        else:
            self.rip_proc = Popen(["lame", "--silent", "-V", args.vbr, "-h", "-r", "-", self.mp3_file], stdin=PIPE)
        self.pipe = self.rip_proc.stdin
        if args.pcm:
          self.pcm_file = open(self.mp3_file[:-4] + ".pcm", 'w')
        self.ripping = True

    def finish_rip(self, track):
        if self.pipe is not None:
            print(Fore.GREEN + 'Rip complete' + Fore.RESET)
            self.pipe.flush()
            self.pipe.close()

            # wait for process to end before continuing
            ret_code = self.rip_proc.wait()
            if ret_code != 0:
                print(Fore.YELLOW + "Warning: lame returned non-zero error code " + str(ret_code) + Fore.RESET)
            self.rip_proc = None
            self.pipe = None
        if self.args.pcm:
            self.pcm_file.flush()
            os.fsync(self.pcm_file.fileno())
            self.pcm_file.close()
            self.pcm_file = None
        self.ripping = False

    def update_progress(self):
        pos_seconds = self.position // 1000
        dur_seconds = self.duration // 1000
        pct = int(self.position * 100 // self.duration)
        x = int(pct * 40 // 100)
        print_str(self.args, ("\rProgress: [" + ("=" * x) + (" " * (40 - x)) + "] %d:%02d / %d:%02d") % (pos_seconds // 60, pos_seconds % 60, dur_seconds // 60, dur_seconds % 60))

    def end_progress(self):
        print_str(self.args, "\n")

    def rip(self, session, audio_format, frame_bytes, num_frames):
        if self.ripping:
            self.position += (num_frames * 1000) / audio_format.sample_rate
            self.update_progress()
            self.pipe.write(frame_bytes);
            if self.args.pcm:
              self.pcm_file.write(frame_bytes)

    def abort(self):
        self.session.player.play(False)
        self.clean_up_partial()
        self.logout()
        self.finished = True
