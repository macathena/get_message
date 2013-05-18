#!/usr/bin/python

import hesiod
import select
import socket
import os

MESSAGE_VERS = 'GMS:0'
MESSAGE_SIZE = 2048
MESSAGE_CACHE = '/var/cache/libgms/messages'
MESSAGE_TIMEOUT = 5
GMS_USERFILE = '.message_times'
GMS_PORT = 2106

def get_server():
    """Look up the globalmessage service in Hesiod, to get a server to connect to."""
    try:
        return hesiod.Lookup('globalmessage', 'sloc').results[0]
    except:
        raise Exception('Unable to lookup gms server')

def parse(msg):
    """Parse a gms message, returning a version, timestamp, text tuple
    if successful, and an Exception otherwise."""
    try:
        header, text = msg.split('\n', 1)
        version, timestamp = header.split(' ', 1)
        if version != MESSAGE_VERS:
            raise Exception('Incompatible version of GMS [%s] found' % (version,))
        return (version, int(timestamp), text)
    except:
        raise Exception('Unable to parse the specified message')

def get_message_times():
    return os.path.expanduser(os.path.join('~', GMS_USERFILE))
    
def has_seen(timestamp):
    """Check if the user has seen this message, by reading
    ~/.message_times. If this file cannot be read, assume no."""
    try:
        with open(get_message_times(), 'r') as mtimes:
            _, lastread, _ = parse(mtimes.read())
            return timestamp <= lastread
    except:
        return False

def write_message_times(timestamp):
    """Write ~/.message_times with the specified timestamp."""
    try:
        with open(get_message_times(), 'w') as mtimes:
            mtimes.write('%s %d\n' % (MESSAGE_VERS, timestamp))
    except:
        # The write failed. All this means is the user will see the
        # message again later.
        pass

def fetch_message():
    """Connect to the globalmessage server, and read a message."""
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.sendto('%s 0\n' % (MESSAGE_VERS,), (get_server(), GMS_PORT))
    message = None
    readable, _, _  = select.select([server], [], [], MESSAGE_TIMEOUT)
    for i in readable:
        message, _ = i.recvfrom(MESSAGE_SIZE)
    return message

def save_message_to_cache(msg_tuple):
    """Save the specified message to the cache."""
    with open(MESSAGE_CACHE, 'w') as f:
        f.write('%s %d\n%s' % msg_tuple)

def read_message_from_cache():
    with open(MESSAGE_CACHE, 'r') as f:
        return f.read()
        
def get_message():
    msg = fetch_message()
    if msg is not None:
        # Save the message to the cache, if it parses
        msg_tuple = parse(msg)
        save_message_to_cache(msg_tuple)
    else:
        # Huh, no message. Try to read it from cache
        msg = read_message_from_cache()

    return parse(msg)
