#!/usr/bin/python
#
# Mutiny.py, Copyright 2012, Bjarni R. Einarsson <http://bre.klaki.net/>
#
# This is an IRC-to-WWW gateway designed to help Pirates have Meetings.
#
VERSION = 'v0.0'
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
import json
import os
import sys
import threading
import time
import traceback
import urllib
import zlib
# Stuff from PageKite
import sockschain
import HttpdLite
# Stuff from Mutiny
from mutiny.io import SelectLoop, SelectAborted, Connect
from mutiny.irc import IrcClient, IrcBot


DEFAULT_PATH = os.path.expanduser('~/.mutiny')
DEFAULT_PATH_HTML = os.path.join(DEFAULT_PATH, 'html')

html_escape_table = {
  "&": "&amp;",
  '"': "&quot;",
  "'": "&apos;",
  ">": "&gt;",
  "<": "&lt;",
}
def html_escape(text):
  """Produce entities within text."""
  return "".join(html_escape_table.get(c,c) for c in text)


class NotFoundException(Exception):
  """Thrown when we want to render a 404."""
  pass


class Mutiny(IrcBot):
  """The main Mutiny class."""

  def __init__(self, config, nickname, server, channels):
    self.log_path = config['log_path']
    self.config = config
    self.listen_on = ('localhost', 4950)  # 99 bottles of beer on the wall!
    if ':' in server:
      self.proto, server = server.split(':', 1)
    else:
      self.proto = 'irc'
    if ':' in server:
      self.server, self.port = server.strip('/').rsplit(':', 1)
    else:
      self.server, self.port = server.strip('/'), 6667

    IrcBot.__init__(self)
    self.irc_nickname(nickname).irc_channels(channels)

    self.select_loop = SelectLoop()
    self.DEBUG = self.select_loop.DEBUG = self.config.get('debug', False)

  def start(self):
    if not os.path.exists(self.log_path):
      os.mkdir(self.log_path)
    Connect(self.proto, self.server, self.port,
            self.connected, self.failed).start()

  def stop(self):
    self.select_loop.stop()

  def failed(self, socket):
    self.stop()
    raise

  def connected(self, socket):
    print 'Connected to %s://%s:%s/' % (self.proto, self.server, self.port)
    self.process_connect(lambda d: self.select_loop.sendall(socket, d))
    self.select_loop.add(socket, self)
    self.select_loop.start()

  def load_template(self, name, config={}, max_size=102400):
    sv = {}
    for setting, default in [('lang', 'en'),
                             ('skin', 'default'),
                             ('templates', '.SELF/html')]:
      sv[setting] = [config.get(setting, self.config.get(setting, default))]
      if default not in sv[setting]:
        sv[setting].append(default)
    tried = []
    for path in sv['templates']:
      for skin in sv['skin']:
        for lang in sv['lang']:
          fp = os.path.join(path, os.path.join(skin, os.path.join(lang, name)))
          tried.append(fp)
          if os.path.exists(fp):
            fd = open(fp, 'rb')
            return open(fp).read(max_size)
    raise NotFoundException('Not found: %s, tried: %s' % (name, tried))

  def fixup_channel(self, channel):
    if not channel[0] in ('!', '&'):
      channel = '#' + channel
    return channel

  def handleHttpRequest(self, req, scheme, netloc, path,
                              params, query, frag,
                              qs, posted, cookies, user=None):
    if path.startswith('/'): path = path[1:]
    path_url = path
    path = urllib.unquote(path).decode('utf-8')

    # Defaults, will probably be overridden by individual response pages
    headers = []
    cachectrl = 'max-age=3600, public'
    mime_type = 'text/html'
    code = 200
    data = None

    # Shared values for rendering templates
    host = req.header('Host', 'unknown').lower()
    page = {
      'templates': DEFAULT_PATH_HTML,
      'version': VERSION,
      'skin': host,
      'host': host,
    }

    # Get the actual content.
    try:
      if req.command == 'GET':
        if path == '':
          template = self.load_template('index.html', config=page)
          page.update({
            'linked_channel_list': ''
          })
        elif path.startswith('_api/v1/'):
          return self.handleApiRequest(req, path, qs, posted, cookies)
        elif path.startswith('join/'):
          join, network, channel = path.split('/')
          page.update({
            'network': network,
            'channel': self.fixup_channel(channel),
            'log_status': 'off',
            'log_not': 'not ',
            'log_url': '/',
          })
          template = self.load_template('channel.html', config=page)
        elif (path.startswith('_skin/') or
              path in ('favicon.ico', )):
          template = self.load_template(path.split('/')[-1], config=page)
          mime_type = HttpdLite.GuessMimeType(path)
          if mime_type != 'application/octet-stream' and path.endswith('.gz'):
            headers.append(('Content-Encoding', 'gzip'))
        elif path == 'robots.txt':
          # FIXME: Have an explicit search-engine policy in settings
          raise NotFoundException('FIXME')
        else:
          cachectrl, code, data = 'no-cache', 404, '<h1>404 Not found</h1>\n'
    except NotFoundException:
      cachectrl, code, data = 'no-cache', 404, '<h1>404 Not found</h1>\n'

    if not data:
      if '__Mutiny_Template__' in template:
        data = (template.decode('utf-8') % page).encode('utf-8')
        cachectrl = 'no-cache'
      else:
        data = template
    return req.sendResponse(data,
                            code=code, mimetype=mime_type,
                            header_list=headers, cachectrl=cachectrl)

  CORS_HEADERS = [
    ('Access-Control-Allow-Origin', '*'),
    ('Access-Control-Allow-Methods', 'GET, POST'),
    ('Access-Control-Allow-Headers', 'content-length, authorization')
  ]

  def handleApiRequest(self, req, path, qs, posted, cookies):
    api, v1, network, channel = path.split('/')
    headers = self.CORS_HEADERS[:]
    mime_type, data = getattr(self, 'api_%s' % qs['a'][0]
                              )(network, channel, qs, posted, cookies)
    return req.sendResponse(data,
                            mimetype=mime_type,
                            header_list=headers, cachectrl='no-cache')

  def api_log(self, network, channel, qs, posted, cookies):
    # FIXME: Choose between bots based on network

    channel = self.fixup_channel(channel)
    grep = qs.get('grep', [''])[0]
    after = qs.get('seen', [None])[0]
    limit = int(qs.get('limit', [0])[0])
    timeout = int(qs.get('timeout', [0])[0])
    if timeout:
      timeout += time.time()

    data = []
    try:
      while not data:
        data = self.irc_channel_log(channel)
        if after or grep:
          data = [x for x in data if (x[0] > after) and
                                     (not grep or
                                      grep in x[1]['nick'].lower() or
                                      grep in x[1].get('text', ''))]
        if timeout and not data:
          cond = threading.Condition()
          ev = self.select_loop.add_sleeper(timeout, cond, 'API request')
          self.irc_watch_channel(channel, ev)
          cond.acquire()
          cond.wait()
          cond.release()
          self.select_loop.remove_sleeper(ev)
        if time.time() >= timeout:
          break
    except SelectAborted:
      pass

    if limit:
      data = data[-limit:]

    return 'application/json', json.dumps(data, indent=1)


if __name__ == "__main__":
  try:
    if '--version' in sys.argv:
      print '%s' % VERSION
      sys.exit(0)

    config = {
      'log_path': DEFAULT_PATH,
      'lang': 'en',
      'skin': 'default',
      'debug': False,
      # These are ignored, but picked up by sockschain
      'nossl': None,
      'nopyopenssl': None,
    }
    for arg in sys.argv[1:]:
      if arg.startswith('--'):
        found = None
        for var in config:
          if arg.startswith('--%s=' % var):
            found = config[var] = arg.split('=', 1)[1]
          elif arg == ('--%s' % var):
            found = config[var] = True
        if found is None:
          raise ValueError('Unknown arg: %s' % arg)
        sys.argv.remove(arg)

    if config['debug']:
      def dbg(text):
        print '%s' % text
      sockschain.DEBUG = dbg

    nickname = sys.argv[1].replace(' ', '_')
    server = sys.argv[2].rsplit('/', 1)[0]
    channels = sys.argv[2].rsplit('/', 1)[1].split(',', 1)

    mutiny = Mutiny(config,  nickname, server, channels)

  except (IndexError, ValueError, OSError, IOError):
    print '%s\n' % traceback.format_exc()
    print 'Usage: %s <nick> irc://<server:port>/<channel>' % sys.argv[0]
    print '       %s <nick> ssl://<server:port>/<channel>' % sys.argv[0]
    print
    print 'Logs and settings will be stored here: %s' % config['log_path']
    print
    sys.exit(1)
  try:
    try:
      print 'This is Mutiny.py, listening on %s:%s' % mutiny.listen_on
      print 'Fork me on Github: https://github.com/pagekite/plugins-pyMutiny'
      print
      mutiny.start()
      HttpdLite.Server(mutiny.listen_on, mutiny).serve_forever()
    except KeyboardInterrupt:
      mutiny.stop()
  except:
    mutiny.stop()
    raise

