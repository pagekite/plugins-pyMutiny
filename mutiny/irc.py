#!/usr/bin/python
#
# Mutiny.py, Copyright 2012, Bjarni R. Einarsson <http://bre.klaki.net/>
#
# This is an IRC-to-WWW gateway designed to help Pirates have Meetings.
#
################################################################################
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the  GNU  Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful,  but  WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see: <http://www.gnu.org/licenses/>
#
################################################################################
#
# Python standard
import random
import socket
import threading
import traceback


COUNTER, COUNTER_LOCK = 0, threading.Lock()
def GetUID():
  global COUNTER, COUNTER_LOCK
  COUNTER_LOCK.acquire()
  uid = '%x.%x' % (random.randint(0, 0x7fffffff), COUNTER)
  COUNTER += 1
  COUNTER_LOCK.release()
  return uid


class IrcClient:
  """This is a bare-bones IRC client which logs on and ping/pongs."""

  def __init__(self):
    self.nickname = None
    self.channels = None
    self.partial = ''
    self.uid = GetUID()

  def set_nickname(self, nickname):
    self.nickname = nickname.lower()
    return self

  def set_channels(self, channels):
    self.channels = channels
    return self

  def process_connect(self, write_cb):
    """Process a new connection."""
    write_cb('NICK %s\nUSER mutiny x x :Mutiny\n' % (self.nickname))

  def process_data(self, data, write_cb):
    """Process data, presumably from a server."""
    lines = (self.partial+data).splitlines(True)
    if lines and not lines[-1].endswith('\n'):
      self.partial = lines.pop(-1)
    else:
      self.partial = ''

    for line in lines:
      self.process_line(line, write_cb)

  def process_line(self, line, write_cb):
    """IRC is line based, this routine process just one line."""
    try:
      parts = line.strip().split(' ', 1)
      if not line[0] == ':':
        parts[0:0] = ['']
      while (parts[-1][0] != ':') and (' ' in parts[-1]):
        parts[-1:] = parts[-1].split(' ', 1)
      for p in range(0, len(parts)):
        if parts[p] and parts[p][0] == ':':
          parts[p] = parts[p][1:]
      return getattr(self, 'on_%s' % parts[1].lower())(parts, write_cb)
    except (IndexError, AttributeError, ValueError):
      print '%s' % parts
      return None

  ### Protocol callbacks follow ###

  def on_001(self, parts, write_cb):
    self.nickname = parts[2].lower()

  def on_002(self, parts, write_cb): """Server info."""
  def on_003(self, parts, write_cb): """Server uptime."""
  def on_004(self, parts, write_cb): """Mode characters."""
  def on_005(self, parts, write_cb): """Limits."""
  def on_250(self, parts, write_cb): """Max connection count."""
  def on_251(self, parts, write_cb): """Users visible/invisible on N servers."""
  def on_252(self, parts, write_cb): """IRCOPs online."""
  def on_254(self, parts, write_cb): """Channels."""
  def on_255(self, parts, write_cb): """Clients and servers."""
  def on_265(self, parts, write_cb): """Local user stats, current/max."""
  def on_266(self, parts, write_cb): """Global user stats, current/max."""
  def on_372(self, parts, write_cb): """MOTD line."""
  def on_375(self, parts, write_cb): """Start of MOTD."""

  def on_376(self, parts, write_cb):
    """End of MOTD."""
    if self.channels:
      write_cb('JOIN %s\n' % '\nJOIN '.join(self.channels))

  def on_396(self, parts, write_cb): """Hidden host."""

  def on_error(self, parts, write_cb):
    print 'ERROR: %s' % parts
    write_cb('QUIT\n')

  def on_notice(self, parts, write_cb): pass

  def on_ping(self, parts, write_cb):
    write_cb('PONG %s\n' % parts[2])

  def on_privmsg(self, parts, write_cb):
    if parts[2].lower() == self.nickname:
      return self.on_privmsg_self(parts, write_cb)
    elif parts[2] in self.channels:
      if parts[3].strip().lower().startswith('%s:' % self.nickname):
        return self.on_privmsg_self(parts, write_cb)
      return self.on_privmsg_channel(parts, write_cb)

  def on_privmsg_self(self, parts, write_cb):
    fromnick = parts[0].split('!', 1)[0]
    write_cb(('NOTICE %s :Sorry, my client does not support private messages.\n'
              ) % fromnick)


class IrcLogger(IrcClient):
  """This client logs what he sees."""

  MAXLINES = 200

  def __init__(self):
    IrcClient.__init__(self)
    self.logs = {}

  def irc_channel_log(self, channel):
    if channel not in self.channels:
      return []
    if channel not in self.logs:
      self.logs[channel] = []
    else:
      while len(self.logs[channel]) > self.MAXLINES:
        self.logs[channel].pop(0)
    return self.logs[channel]

  def on_join(self, parts, write_cb):
    self.irc_channel_log(parts[2]).append(parts)
    write_cb('WHO %s\n' % parts[2])
    IrcClient.on_join(self, parts, write_cb)

  def on_privmsg_channel(self, parts, write_cb):
    self.irc_channel_log(parts[2]).append(parts)
    IrcClient.on_privmsg_channel(self, parts, write_cb)


class IrcBot(IrcLogger):
  """This client logs what he sees and is very helpful."""

  def on_privmsg_self(self, parts, write_cb):
    fromnick = parts[0].split('!', 1)[0]
    message = parts[3].strip()
    if message.lower().startswith('%s:' % self.nickname):
      message = message[len(self.nickname)+1:]
    if parts[2].lower() != self.nickname:
      channel = parts[2]
    else:
      channel = None
    parts = message.split()
    try:
      return getattr(self, 'cmd_%s' % parts[0].lower()
                     )(fromnick, channel, parts, write_cb)
    except (IndexError, AttributeError):
      return None

  def cmd_ping(self, fromnick, channel, parts, write_cb):
    write_cb('NOTICE %s :pongalong!\n' % fromnick)


if __name__ == "__main__":
  # Test things?
  pass
