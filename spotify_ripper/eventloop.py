# -*- coding: utf-8 -*-

# From PySpotify's EventLoop
# https://github.com/mopidy/pyspotify/blob/v2.x/master/spotify/eventloop.py

from __future__ import unicode_literals

from colorama import Fore
import threading

try:
    # Python 3
    import queue
except ImportError:
    # Python 2
    import Queue as queue

import spotify


__all__ = [
    'EventLoop',
]


class EventLoop(threading.Thread):

    """Event loop for automatically processing events from libspotify.

    The event loop is a :class:`~threading.Thread` that listens to
    :attr:`~spotify.SessionEvent.NOTIFY_MAIN_THREAD` events and calls
    :meth:`~spotify.Session.process_events` when needed.

    To use it, pass it your :class:`~spotify.Session` instance and call
    :meth:`start`::

        >>> session = spotify.Session()
        >>> event_loop = EventLoop(session)
        >>> event_loop.start()

    .. warning::

        If you use :class:`EventLoop` to process the libspotify events, any
        event listeners you've registered will be called from the event loop
        thread. pyspotify itself is thread safe, but you'll need to ensure that
        you have proper synchronization in your own application code, as always
        when working with threads.
    """

    name = 'SpotifyEventLoop'

    def __init__(self, session, timeout, ripper):
        threading.Thread.__init__(self)

        self._session = session
        self._runnable = True
        self._queue_timeout = timeout * 1000
        self._queue = queue.Queue()
        self._ripper = ripper

    def start(self):
        """Start the event loop."""
        self._session.on(
            spotify.SessionEvent.NOTIFY_MAIN_THREAD,
            self._on_notify_main_thread)
        threading.Thread.start(self)

    def stop(self):
        """Stop the event loop."""
        self._runnable = False
        self._session.off(
            spotify.SessionEvent.NOTIFY_MAIN_THREAD,
            self._on_notify_main_thread)

    def run(self):
        timeout_countdown = self._session.process_events()

        while self._runnable and self._ripper.isAlive():
            timeout = min(timeout_countdown, self._queue_timeout)

            try:
                self._queue.get(timeout=(timeout / 1000.0))
            except queue.Empty:
                # queue timeout
                timeout_countdown -= timeout
            else:
                # notification
                timeout_countdown = 0
            finally:
                if timeout_countdown <= 0:
                    timeout_countdown = self._session.process_events()

    def _on_notify_main_thread(self, session):
        # WARNING: This event listener is called from an internal libspotify
        # thread. It must not block.
        try:
            self._queue.put_nowait(1)
        except queue.Full:
            print(Fore.RED +
                  "event loop queue full. dropped notification event" +
                  Fore.RESET)
