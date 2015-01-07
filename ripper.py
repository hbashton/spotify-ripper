#!/usr/bin/env python
# -*- coding: utf8 -*-

from __future__ import unicode_literals

from subprocess import call, Popen, PIPE
from spotify import Link, LinkType, Image
#from jukebox import Jukebox, container_loaded
import os, sys
#import threading
import time

import cmd
import logging
import threading

import spotify

playback = False # set if you want to listen to the tracks that are currently ripped (start with "padsp ./jbripper.py ..." if using pulse audio)
rawpcm = False # also saves a .pcm file with the raw PCM data as delivered by libspotify ()

pcmfile = None
pipe = None
ripping = False
end_of_track = threading.Event()

def printstr(str): # print without newline
    sys.stdout.write(str)
    sys.stdout.flush()

def shell(cmdline): # execute shell commands (unicode support)
    call(cmdline, shell=True)

def rip_init(session, track):
    global pipe, ripping, pcmfile, rawpcm
    num_track = "%02d" % (track.index)
    print "rip_init: %s %s" % (track.name, num_track)
    mp3file = track.name+".mp3"
    pcmfile = track.name+".pcm"
    directory = os.getcwd() + "/" + track.artists[0].name + "/" + track.album.name + "/"
    if not os.path.exists(directory):
        os.makedirs(directory)
    printstr("ripping " + mp3file + " ...")
    p = Popen("lame --silent -V0 -h -r - \""+ directory + mp3file+"\"", stdin=PIPE, shell=True)
    pipe = p.stdin
    if rawpcm:
      pcmfile = open(directory + pcmfile, 'w')
    ripping = True


def rip_terminate(session, track):
    global ripping, pipe, pcmfile, rawpcm
    if pipe is not None:
        print(' done!')
        pipe.close()
    if rawpcm:
        pcmfile.close()
    ripping = False

def rip(session, audio_format, frame_bytes, num_frames):
    if ripping:
        printstr('.')
        pipe.write(frame_bytes);
        if rawpcm:
          pcmfile.write(frame_bytes)

def rip_id3(session, track): # write ID3 data
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
    #image = session.get_image(track.album.cover)
    #while not image.is_loaded(): # does not work from MainThread!
    #    time.sleep(0.1)
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
    shell(cmd)

    # delete cover
    #shell("rm -f cover.jpg")

class RipperThread(threading.Thread):
    def __init__(self, ripper):
        threading.Thread.__init__(self)
        self.ripper = ripper

    def run(self):
        # wait for container
        #container_loaded.wait()
        #container_loaded.clear()

        # login
        print("logging in")
        self.ripper.do_login("user pass")

        # ripping loop
        session = self.ripper.session

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

            rip_init(session, track)

            session.player.play()

            end_of_track.wait()
            end_of_track.clear() # TODO check if necessary

            rip_terminate(session, track)
            rip_id3(session, track)

        print("logging out")
        self.ripper.do_disconnect()

class Ripper():

    logger = logging.getLogger('shell.ripper')

    def __init__(self):

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

        # try:
        #     self.audio_driver = spotify.PortAudioSink(self.session)
        # except ImportError:
        #     self.logger.warning(
        #         'No audio sink found; audio playback unavailable.')

        self.event_loop = spotify.EventLoop(self.session)
        self.event_loop.start()

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

    def on_music_delivery(self, session, audio_format, frame_bytes, num_frames):
        rip(session, audio_format, frame_bytes, num_frames)
        # if playback:
        #     return Jukebox.music_delivery_safe(self, session, frames, frame_size, num_frames, sample_type, sample_rate, channels)
        # else:
        #     return num_frames
        return num_frames
        #return 0

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

    def do_forget_me(self):
        "forget_me -- forget the previous logged in user"
        self.session.forget_me()

    def do_logout(self):
        "logout"
        self.session.logout()
        self.logged_out.wait()

    def do_whoami(self):
        "whoami"
        if self.logged_in.is_set():
            self.logger.info(
                'I am %s aka %s. You can find me at %s',
                self.session.user.canonical_name,
                self.session.user.display_name,
                self.session.user.link)
        else:
            self.logger.info(
                'I am not logged in, but I may be %s',
                self.session.remembered_user)

    def do_play_uri(self, line):
        "play <spotify track uri>"
        if not self.logged_in.is_set():
            self.logger.warning('You must be logged in to play')
            return
        try:
            track = self.session.get_track(line)
            track.load()
        except (ValueError, spotify.Error) as e:
            self.logger.warning(e)
            return
        self.logger.info('Loading track into player')
        self.session.player.load(track)
        self.logger.info('Playing track')
        self.session.player.play()

    def do_disconnect(self):
        "Exit"
        if self.logged_in.is_set():
            print('Logging out...')
            self.session.logout()
            self.logged_out.wait()
        self.event_loop.stop()
        print('')
        return True


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) >= 3:
        ripper = Ripper()
        ripper_thread = RipperThread(ripper)
        ripper_thread.start()

        #ripper.connect()
    else:
        print "usage : \n"
        print "   ./ripper.py [username] [password] [spotify_url]"
        print "example : \n"
        print "   ./ripper.py user pass spotify:track:52xaypL0Kjzk0ngwv3oBPR - for a single file"
        print "   ./ripper.py user pass spotify:user:username:playlist:4vkGNcsS8lRXj4q945NIA4 - rips entire playlist"
