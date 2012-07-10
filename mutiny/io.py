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
import errno
import select
import socket
import threading
import time
# Stuff from PageKite
import sockschain
from sockschain import SSL


class SelectAborted(Exception):
  pass


class SelectLoop(threading.Thread):
  """This class implements a select loop in a thread of its own."""

  DEBUG = False
  HARMLESS_ERRNOS = (errno.EINTR, errno.EAGAIN, errno.ENOMEM, errno.EBUSY,
                     errno.EDEADLK, errno.EWOULDBLOCK, errno.ENOBUFS,
                     errno.EALREADY)

  def __init__(self):
    threading.Thread.__init__(self)
    self.keep_running = True
    self.conns_by_fd = {}
    self.fds_by_uid = {}
    self.sleepers = []

  def stop(self):
    self.keep_running = False
    for sleeper in self.sleepers:
      self.awaken_sleeper(sleeper)

  def add(self, fd, owner):
    self.fds_by_uid[owner.uid] = fd
    self.conns_by_fd[fd] = owner

  def remove_owner(self, owner):
    del self.conns_by_fd[self.fds_by_uid[owner.uid]]
    del self.fds_by_uid[owner.uid]

  def remove_fd(self, fd):
    del self.fds_by_uid[self.conns_by_fd[fd].uid]
    del self.conns_by_fd[fd]

  def add_sleeper(self, waketime, condition, info):
    if not self.keep_running:
      raise SelectAborted()
    ev = (waketime, condition, info)
    self.sleepers.append(ev)
    self.sleepers.sort()
    return ev

  def remove_sleeper(self, ev):
    try:
      self.sleepers.remove(ev)
    except ValueError:
      pass

  def awaken_sleeper(self, ev):
    wt, cond, info = ev
    cond.acquire()
    cond.notify()
    if self.DEBUG:
      print '-*- Woke up: %s' % info
    cond.release()

  def sendall(self, fd, data):
    try:
      if self.DEBUG:
        print '>>> %s' % data.encode('string_escape')
      return fd.sendall(data)
    except SSL.WantWriteError:
      return self.sendall(fd, data)
    except IOError, err:
      if err.errno == errno.EINTR:
        return self.sendall(fd, data)

  def run(self):
    d = 0.1
    while self.keep_running:
      ready = select.select(self.conns_by_fd.keys(), [], [], d)[0]
      for fd in ready:
        try:
          data = fd.recv(32*1024)
          if self.DEBUG:
            print '<<< %s' % data.encode('string_escape')
          self.conns_by_fd[fd].process_data(data,
                                            lambda d: self.sendall(fd, d))
          if data == '':
            self.remove_fd(fd)
        except SSL.WantReadError:
          pass
        except IOError, err:
          if err.errno not in self.HARMLESS_ERRNOS:
            self.remove_fd(fd)
        except socket.error, (errno, msg):
          if errno not in self.HARMLESS_ERRNOS:
            self.remove_fd(fd)
        except (SSL.Error, SSL.ZeroReturnError, SSL.SysCallError):
          self.remove_fd(fd)

      if ready:
        d = 0.1
      else:
        d = min(1, d+0.1)

      if self.sleepers:
        now = time.time()
        try:
          while self.sleepers and self.sleepers[0][0] <= now:
            self.awaken_sleeper(self.sleepers.pop(0))
        except IndexError:
          pass


class Connect(threading.Thread):
  """This class implements a non-blocking connect in a thread of its own."""

  def __init__(self, proto, hostname, port, callback_ok, callback_err=None):
    threading.Thread.__init__(self)
    self.hostname = hostname
    self.proto = proto
    self.port = int(port)
    self.callback_ok = callback_ok
    self.callback_err = callback_err

  def run(self):
    sock = sockschain.socksocket()
    if self.proto in ('ircs', 'ssl'):
      if sockschain.HAVE_SSL:
        chain = ['default']
        chain.append('ssl!%s!%s' % (self.hostname, self.port))
        for hop in chain:
          sock.addproxy(*sockschain.parseproxy(hop))
    try:
      sock.connect((self.hostname, self.port))
      sock.setblocking(0)
      self.callback_ok(sock)
    except:
      if self.callback_err:
        self.callback_err(sock)

