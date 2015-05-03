# -*- coding: utf8 -*-

from __future__ import unicode_literals

from colorama import Fore, Style
import os, sys, errno
import re

def print_str(args, _str):
    """print without newline"""
    if not args.has_log:
        sys.stdout.write(_str)
        sys.stdout.flush()

def norm_path(path):
    """normalize path"""
    return os.path.normpath(os.path.realpath(path))

# borrowed from AndersTornkvist's fork
def escape_filename_part(part):
    """escape possible offending characters"""
    part = re.sub(r"\s*/\s*", r' & ', part)
    part = re.sub(r"""\s*[\\/:"*?<>|]+\s*""", r' ', part)
    part = part.strip()
    part = re.sub(r"(^\.+\s*|(?<=\.)\.+|\s*\.+$)", r'', part)
    return part

def to_ascii(args, _str, on_error='ignore'):
    """convert unicode to ascii if necessary"""
    # python 3 renamed unicode to str
    if sys.version_info >= (3, 0):
        if isinstance(_str, bytes) and not args.ascii:
            return str(_str, "utf-8")
        elif isinstance(_str, str) and args.ascii:
            return _str.encode('ascii', on_error).decode("utf-8")
        else:
            return _str
    else:
        if isinstance(_str, str) and not args.ascii:
            return unicode(_str, "utf-8")
        elif isinstance(_str, unicode) and args.ascii:
            return _str.encode('ascii', on_error).decode("utf-8")
        else:
            return _str

def rm_file(file_name):
    try:
        os.remove(file_name)
    except OSError as e:
        # don't need to print a warning if the file doesn't exist
        if e.errno != errno.ENOENT:
            print(Fore.YELLOW + "Warning: error while trying to remove file " + file_name + Fore.RESET)
            print(str(e))

def default_settings_dir():
    return norm_path(os.path.join(os.path.expanduser("~"), ".spotify-ripper"))

KB_BYTES = 1024
'''Number of bytes per KB (2^10)'''
MB_BYTES = 1048576
'''Number of bytes per MB (2^20)'''
GB_BYTES = 1073741824
'''Number of bytes per GB (2^30)'''
KB_UNIT = "KB"
'''Kilobytes abbreviation'''
MB_UNIT = "MB"
'''Megabytes abbreviation'''
GB_UNIT = "GB"
'''Gigabytes abbreviation'''

# borrowed from eyeD3
def format_size(size, short=False):
    '''Format ``size`` (nuber of bytes) into string format doing KB, MB, or GB
    conversion where necessary.

    When ``short`` is False (the default) the format is smallest unit of
    bytes and largest gigabytes; '234 GB'.
    The short version is 2-4 characters long and of the form

        256b
        64k
        1.1G
    '''
    if not short:
        unit = "Bytes"
        if size >= GB_BYTES:
            size = float(size) / float(GB_BYTES)
            unit = GB_UNIT
        elif size >= MB_BYTES:
            size = float(size) / float(MB_BYTES)
            unit = MB_UNIT
        elif size >= KB_BYTES:
            size = float(size) / float(KB_BYTES)
            unit = KB_UNIT
        return "%.2f %s" % (size, unit)
    else:
        suffixes = u' kMGTPEH'
        if size == 0:
            num_scale = 0
        else:
            num_scale = int(math.floor(math.log(size) / math.log(1000)))
        if num_scale > 7:
            suffix = '?'
        else:
            suffix = suffixes[num_scale]
        num_scale = int(math.pow(1000, num_scale))
        value = size / num_scale
        str_value = str(value)
        if len(str_value) >= 3 and str_value[2] == '.':
            str_value = str_value[:2]
        else:
            str_value = str_value[:3]
        return "{0:>3s}{1}".format(str_value, suffix)

# borrowed from eyeD3
def format_time(seconds, total=None, short=False):
    '''
    Format ``seconds`` (number of seconds) as a string representation.
    When ``short`` is False (the default) the format is:

        HH:MM:SS.

    Otherwise, the format is exacly 6 characters long and of the form:

        1w 3d
        2d 4h
        1h 5m
        1m 4s
        15s

    If ``total`` is not None it will also be formatted and
    appended to the result seperated by ' / '.
    '''
    def time_tuple(ts):
        if ts is None or ts < 0:
            ts = 0
        hours = ts / 3600
        mins = (ts % 3600) / 60
        secs = (ts % 3600) % 60
        tstr = '%02d:%02d' % (mins, secs)
        if int(hours):
            tstr = '%02d:%s' % (hours, tstr)
        return (int(hours), int(mins), int(secs), tstr)

    if not short:
        hours, mins, secs, curr_str = time_tuple(seconds)
        retval = curr_str
        if total:
            hours, mins, secs, total_str = time_tuple(total)
            retval += ' / %s' % total_str
        return retval
    else:
        units = [
            (u'y', 60 * 60 * 24 * 7 * 52),
            (u'w', 60 * 60 * 24 * 7),
            (u'd', 60 * 60 * 24),
            (u'h', 60 * 60),
            (u'm', 60),
            (u's', 1),
        ]

        seconds = int(seconds)

        if seconds < 60:
            return u'   {0:02d}s'.format(seconds)
        for i in xrange(len(units) - 1):
            unit1, limit1 = units[i]
            unit2, limit2 = units[i + 1]
            if seconds >= limit1:
                return u'{0:02d}{1}{2:02d}{3}'.format(
                    seconds // limit1, unit1,
                    (seconds % limit1) // limit2, unit2)
        return u'  ~inf'
