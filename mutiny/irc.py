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
import random
import socket


class IrcClient:
  """This is a bare-bones IRC client which logs on and ping/pongs."""

  def __init__(self, nickname, channels):
    self.rid = '%x' % random.randint(0, 0x7fffffff)
    self.nickname = None
    self.channels = []
    self.server_spec = None
    self.partial = ''
    self.fd = None

  def process_connect(self, write_cb):
    """Process a new connection."""
    write_cb('NICK %s\nUSER mutiny x x :Mutiny\n' % (self.nickname))

  def process_data(self, data, write_cb):
    """Process data, presumably from a server."""
    lines = (self.partial+data).splitlines(True)
    if lines and not lines[-1].endswith('\n'):
      self.partial = lines.pop(-1)

    for line in lines:
      self.process_line(line, write_cb)

  def process_line(self, line, write_cb):
    """IRC is line oriented, process just one line."""
    pass


class IrcLogger(IrcClient):
  """This client logs what he sees."""
  pass


class IrcBot(IrcLogger):
  """This client logs what he sees and is very helpful."""
  pass


if __name__ == "__main__":
  # Test things?
  pass
