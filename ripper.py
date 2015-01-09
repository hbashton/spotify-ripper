#!/usr/bin/env python
# -*- coding: utf8 -*-

from __future__ import unicode_literals

from subprocess import call, Popen, PIPE
from colorama import init, Fore
import os, sys
import time
import cmd
import logging
import threading
import spotify
import argparse

class Utils():
    @staticmethod
    def print_str(str):
        """print without newline"""
        sys.stdout.write(str)
        sys.stdout.flush()

class Ripper(threading.Thread):

    logger = logging.getLogger('shell.ripper')

    mp3_file = None
    pcm_file = None
    pipe = None
    ripping = False
    finished = False
    end_of_track = threading.Event()

    def __init__(self, args):
        threading.Thread.__init__(self)

        # set to a daemon thread
        self.daemon = True

        self.args = args
        self.logged_in = threading.Event()
        self.logged_out = threading.Event()
        self.logged_out.set()

        self.session = spotify.Session()
        self.session.preferred_bitrate(1) # 320 bps
        self.session.on(spotify.SessionEvent.CONNECTION_STATE_UPDATED,
            self.on_connection_state_changed)
        self.session.on(spotify.SessionEvent.END_OF_TRACK,
            self.on_end_of_track)
        self.session.on(spotify.SessionEvent.MUSIC_DELIVERY,
            self.on_music_delivery)

        self.event_loop = spotify.EventLoop(self.session)
        self.event_loop.start()

    def run(self):

        # login
        print("Logging in...")
        if args.last:
            self.login_as_last()
        else:
            self.login(args.user[0], args.password[0])

        session = self.session

        # create track iterator
        link = session.get_link(args.uri)
        if link.type == spotify.LinkType.TRACK:
            track = link.as_track()
            itrack = iter([track])
        elif link.type == spotify.LinkType.PLAYLIST or link.type == spotify.LinkType.STARRED:
            playlist = link.as_playlist()
            Utils.print_str('Loading playlist...')
            playlist.load()
            print(' done')
            itrack = iter(playlist)
        elif link.type() == spotify.LinkType.ALBUM:
            album = spotify.AlbumBrowser(link.as_album())
            print('Loading album...')
            album.load()
            print(' done')
            itrack = iter(album)
        elif link.type() == spotify.LinkType.ARTIST:
            artist = spotify.ArtistBrowser(link.as_artist())
            print('Loading artist...')
            artist.load()
            print(' done')
            itrack = iter(artist)

        # ripping loop
        for track in itrack:
            track.load() # try/catch
            session.player.load(track)

            self.prepare_rip(session, track)

            session.player.play()

            self.end_of_track.wait()
            self.end_of_track.clear() # TODO check if necessary

            self.finish_rip(session, track)
            self.set_id3_and_cover(session, track)

        # logout, we are done
        self.logout()
        self.finished = True

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
            self.logger.error(e)

    def logout(self):
        "logout from Spotify"
        if self.logged_in.is_set():
            print('Logging out...')
            self.session.logout()
            self.logged_out.wait()
        self.event_loop.stop()

    def prepare_rip(self, session, track):
        num_track = "%02d" % (track.index)
        file_prefix = os.getcwd() + "/" + track.artists[0].name + "/" + track.album.name + "/" + track.name
        file_prefix = file_prefix.replace('*', '_')
        self.mp3_file = file_prefix + ".mp3"
        mp3_path = os.path.dirname(file_prefix)

        if not os.path.exists(mp3_path):
            os.makedirs(mp3_path)
        print(Fore.GREEN + "Ripping " + track.link.uri + Fore.RESET)
        print(Fore.CYAN + self.mp3_file + Fore.RESET)
        p = Popen(["lame", "--silent", "-V", args.vbr, "-h", "-r", "-", self.mp3_file], stdin=PIPE)
        self.pipe = p.stdin
        if args.pcm:
          self.pcm_file = open(file_prefix + ".pcm", 'w')
        self.ripping = True

    def finish_rip(self, session, track):
        if self.pipe is not None:
            print(' done')
            self.pipe.close()
        if args.pcm:
            self.pcm_file.close()
        self.ripping = False

    def rip(self, session, audio_format, frame_bytes, num_frames):
        if self.ripping:
            Utils.print_str('.')
            self.pipe.write(frame_bytes);
            if args.pcm:
              self.pcm_file.write(frame_bytes)

    def set_id3_and_cover(self, session, track):
        num_track = "%02d" % (track.index)
        artist = track.artists[0].name
        album = track.album.name
        title = track.name
        year = track.album.year

        # download cover
        image = track.album.cover()
        image.load()

        fh_cover = open('cover.jpg','wb')
        fh_cover.write(image.data)
        fh_cover.close()

        # write id3 data
        call(["eyeD3",
              "--add-image", "cover.jpg:FRONT_COVER",
              "-t", title,
              "-a", artist,
              "-A", album,
              "-n", str(num_track),
              "-Y", str(year),
              "-Q",
              self.mp3_file
        ])

        # delete cover
        call(["rm", "-f", "cover.jpg"])

# example uri : spotify:track:52xaypL0Kjzk0ngwv3oBPR
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description='Rips Spotify URIs to mp3s with ID3 tags and album covers')

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument('-u', '--user', nargs=1, help='Spotify username')
    parser.add_argument('-p', '--password', nargs=1, help='Spotify password')
    group.add_argument('-l', '--last', action='store_true', help='Use last login credentials')
    parser.add_argument('-m', '--pcm', action='store_true', help='Saves a .pcm file with the raw PCM data')
    parser.add_argument('-V', '--vbr', default='0', help='Lame VBR quality setting [Default=0]')
    parser.add_argument('uri', help='Spotify URI (either track or playlist)')
    args = parser.parse_args()

    init()

    ripper = Ripper(args)
    ripper.start()

    # wait for ripping thread to finish
    while not ripper.finished:
        time.sleep(0.1)

