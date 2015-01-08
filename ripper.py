#!/usr/bin/env python
# -*- coding: utf8 -*-

from __future__ import unicode_literals

from subprocess import call, Popen, PIPE
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

    @staticmethod
    def shell(cmdline):
        """execute shell commands (unicode support)"""
        call(cmdline, shell=True)

class Ripper(threading.Thread):

    logger = logging.getLogger('shell.ripper')

    pcmfile = None
    pipe = None
    ripping = False
    end_of_track = threading.Event()

    def __init__(self, args):
        threading.Thread.__init__(self)

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
        print("logging in")
        if args.last:
            self.do_relogin()
        else:
            self.do_login(args.user, args.password)

        # ripping loop
        session = self.session

        # create track iterator
        link = session.get_link(args.uri)
        if link.type == spotify.LinkType.TRACK:
            track = link.as_track()
            itrack = iter([track])
        elif link.type == spotify.LinkType.PLAYLIST:
            playlist = link.as_playlist()
            print('loading playlist ...')
            while not playlist.is_loaded():
                time.sleep(0.1)
            print('done')
            itrack = iter(playlist)

        for track in itrack:
            print "ripping track %s" % (track)
            track.load() # try/catch
            session.player.load(track)

            self.rip_init(session, track)

            session.player.play()

            self.end_of_track.wait()
            self.end_of_track.clear() # TODO check if necessary

            self.rip_terminate(session, track)
            self.rip_id3(session, track)

        print("logging out")
        self.do_disconnect()

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
        end_of_track.set()

    def do_login(self, user, password):
        self.session.login(username, password, remember_me=True)
        self.logged_in.wait()

    def do_relogin(self):
        "relogin -- login as the previous logged in user"
        try:
            self.session.relogin()
            self.logged_in.wait()
        except spotify.Error as e:
            self.logger.error(e)

    def do_disconnect(self):
        "Exit"
        if self.logged_in.is_set():
            print('Logging out...')
            self.session.logout()
            self.logged_out.wait()
        self.event_loop.stop()
        print('')
        return True

    def rip_init(self, session, track):
        num_track = "%02d" % (track.index)
        print "rip_init: %s %s" % (track.name, num_track)
        mp3file = track.name+".mp3"
        pcmfile = track.name+".pcm"
        directory = os.getcwd() + "/" + track.artists[0].name + "/" + track.album.name + "/"
        if not os.path.exists(directory):
            os.makedirs(directory)
        Utils.print_str("ripping " + mp3file + " ...")
        p = Popen("lame --silent -V0 -h -r - \""+ directory + mp3file+"\"", stdin=PIPE, shell=True)
        self.pipe = p.stdin
        if args.pcm:
          self.pcmfile = open(directory + pcmfile, 'w')
        self.ripping = True


    def rip_terminate(self, session, track):
        if self.pipe is not None:
            print(' done!')
            self.pipe.close()
        if args.pcm:
            self.pcmfile.close()
        self.ripping = False

    def rip(self, session, audio_format, frame_bytes, num_frames):
        if self.ripping:
            Utils.print_str('.')
            pipe.write(frame_bytes);
            if args.pcm:
              self.pcmfile.write(frame_bytes)

    def rip_id3(self, session, track): # write ID3 data
        num_track = "%02d" % (track.index)
        mp3file = track.name+".mp3"
        artist = track.artists[0].name
        album = track.album.name
        title = track.name
        year = track.album.year
        directory = os.getcwd() + "/" + track.artists[0].name + "/" + track.album.name + "/"

        # download cover
        image = track.album.cover()
        image.load()

        fh_cover = open('cover.jpg','wb')
        fh_cover.write(image.data)
        fh_cover.close()

        # write id3 data
        cmd = "eyeD3" + \
              " --add-image cover.jpg:FRONT_COVER" + \
              " -t \"" + title + "\"" + \
              " -a \"" + artist + "\"" + \
              " -A \"" + album + "\"" + \
              " -n " + str(num_track) + \
              " -Y " + str(year) + \
              " -Q " + \
              " \"" + directory + mp3file + "\""
        Utils.shell(cmd)

        # delete cover
        Utils.shell("rm -f cover.jpg")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description='rips Spotify URIs to mp3s with ID3 tags and album covers')

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument('-u', '--user', nargs=1, help='Spotify username')
    parser.add_argument('-p', '--password', nargs=1, help='Spotify password')
    group.add_argument('-l', '--last', action='store_true', help='Use last login credentials')
    parser.add_argument('-m', '--pcm', action='store_true', help='Saves a .pcm file with the raw PCM data')
    parser.add_argument('uri', help='Spotify URI (either track or playlist)')
    args = parser.parse_args()

    ripper = Ripper(args)
    ripper.start()

    # example : spotify:track:52xaypL0Kjzk0ngwv3oBPR

