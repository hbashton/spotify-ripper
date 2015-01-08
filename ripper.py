#!/usr/bin/env python
# -*- coding: utf8 -*-

from __future__ import unicode_literals

from subprocess import call, Popen, PIPE
from spotify import Link, LinkType
import os, sys
import time
import cmd
import logging
import threading
import spotify

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

    playback = False # set if you want to listen to the tracks that are currently ripped (start with "padsp ./jbripper.py ..." if using pulse audio)
    rawpcm = False # also saves a .pcm file with the raw PCM data as delivered by libspotify ()

    pcmfile = None
    pipe = None
    ripping = False
    end_of_track = threading.Event()

    def __init__(self):
        threading.Thread.__init__(self)

        self.logged_in = threading.Event()
        self.logged_out = threading.Event()
        self.logged_out.set()

        self.session = spotify.Session()
        self.session.preferred_bitrate(1) # 320 bps
        self.session.on(spotify.SessionEvent.CONNECTION_STATE_UPDATED,
            self.on_connection_state_changed)
        self.session.on(spotify.SessionEvent.END_OF_TRACK,
            self.on_end_of_track)
        #self.session.on(spotify.SessionEvent.MUSIC_DELIVERY,
        #    self.on_music_delivery)

        # try:
        #     self.audio_driver = spotify.PortAudioSink(self.session)
        # except ImportError:
        #     self.logger.warning(
        #         'No audio sink found; audio playback unavailable.')

        self.event_loop = spotify.EventLoop(self.session)
        self.event_loop.start()

    def run(self):

        # login
        print("logging in")
        self.do_login("jrnewell luve4LAN")

        # ripping loop
        session = self.session

        session.on(spotify.SessionEvent.MUSIC_DELIVERY,
            self.on_music_delivery)

        # create track iterator
        link = session.get_link(sys.argv[3])
        if link.type == LinkType.TRACK:
            track = link.as_track()
            itrack = iter([track])
        elif link.type == LinkType.PLAYLIST:
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

            #session.player.play()

            #self.end_of_track.wait()
            #self.end_of_track.clear() # TODO check if necessary

            self.rip_terminate(session, track)
            self.rip_id3(session, track)

        print("logging out")
        self.do_disconnect()

    def on_music_delivery(self, session, audio_format, frame_bytes, num_frames):
        self.rip(session, audio_format, frame_bytes, num_frames)
        # if playback:
        #     return Jukebox.music_delivery_safe(self, session, frames, frame_size, num_frames, sample_type, sample_rate, channels)
        # else:
        #     return num_frames
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

    def do_login(self, line):
        "login <username> <password>"
        username, password = line.split(' ', 1)
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
        if self.rawpcm:
          self.pcmfile = open(directory + pcmfile, 'w')
        self.ripping = True


    def rip_terminate(self, session, track):
        if self.pipe is not None:
            print(' done!')
            self.pipe.close()
        if self.rawpcm:
            self.pcmfile.close()
        self.ripping = False

    def rip(self, session, audio_format, frame_bytes, num_frames):
        if self.ripping:
            Utils.print_str('.')
            pipe.write(frame_bytes);
            if self.rawpcm:
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

    if len(sys.argv) >= 3:
        ripper = Ripper()
        ripper.start()
    else:
        print "usage : \n"
        print "   ./ripper.py [username] [password] [spotify_url]"
        print "example : \n"
        print "   ./ripper.py user pass spotify:track:52xaypL0Kjzk0ngwv3oBPR - for a single file"
        print "   ./ripper.py user pass spotify:user:username:playlist:4vkGNcsS8lRXj4q945NIA4 - rips entire playlist"
