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
import hashlib
# Stuff from PageKite
import sockschain
import HttpdLite
# Stuff from Mutiny
from mutiny.io import SelectLoop, Connect
from mutiny.irc import IrcClient, IrcBot


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

def sha1sig(parts):
  h = hashlib.sha1()
  h.update(('-'.join(parts)).encode('utf-8'))
  return h.digest().encode('base64').replace('+', '^').replace('=', '').strip()


class Mutiny:
  """The main Mutiny class."""

  def __init__(self, config, nickname, server, channels):
    self.log_path = config['log_path']
    self.config = config
    self.listen_on = ('localhost', 4950)  # 99 bottles of beer on the wall!

    self.select_loop = SelectLoop()
    self.select_loop.DEBUG = self.config.get('debug', False)
    self.bot = IrcBot().set_nickname(nickname).set_channels(channels)

    if ':' in server:
      self.proto, server = server.split(':', 1)
    else:
      self.proto = 'irc'
    if ':' in server:
      self.server, self.port = server.strip('/').rsplit(':', 1)
    else:
      self.server, self.port = server.strip('/'), 6667

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
    self.bot.process_connect(lambda d: self.select_loop.sendall(socket, d))
    self.select_loop.add(socket, self.bot)
    self.select_loop.start()

  def handleHttpRequest(self, req, scheme, netloc, path,
                              params, query, frag,
                              qs, posted, cookies, user=None):
    if path.startswith('/'): path = path[1:]
    path_url = path
    path = urllib.unquote(path).decode('utf-8')

    # Defaults, may be overridden by individual response pages
    code = 200
    headers = self.CORS_HEADERS[:]
    cachectrl = 'no-cache'
    data = None

    # Shared values for rendering templates
    host = req.header('Host', 'unknown')
    page = {
      'proto': 'https', # FIXME
      'host': host,
    }
    page['unhosted_url'] = '%(proto)s://%(host)s' % page
    # host meta
    if req.command == 'GET' and path == '.well-known/host-meta':
      mime_type = 'application/xrd+xml'
      template = self.HOST_META

    elif req.command == 'GET' and path == 'webfinger':
      # FIXME: Does user really exist?
      page['subject'] = subject = qs['uri'][0]
      page['user'] = subject.split(':', 1)[-1].replace('@'+host, '')
      mime_type = 'application/xrd+xml'
      template = self.WEBFINGER.replace('\n', '\r\n')

    elif path == 'oauth':
      return self.handleOAuth(req, page, qs, posted)

    elif path.startswith('storage/'):
      return self.handleStorage(req, path[8:], page, qs, posted)

    else:
      code = 404
      mime_type = 'text/html'
      template = '<h1>404 Not found</h1>\n'

    if not data:
      for key in page.keys():
        page['q_%s' % key] = urllib.quote(page[key])
    return req.sendResponse(data or ((template % page).encode('utf-8')),
                            code=code, mimetype=mime_type,
                            header_list=headers, cachectrl=cachectrl)


if __name__ == "__main__":
  try:
    config = {
      'log_path': os.path.expanduser('~/.Mutiny'),
      'lang': 'en',
      # These are ignored, but picked up by sockschain
      'debug': False,
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
    print 'Usage: %s <nick> <server>/<channel>' % sys.argv[0]
    print
    print 'The program will store logs here: %s' % config['log_path']
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

