#!/usr/bin/python
#
# Mutiny.py, Copyright 2012, Bjarni R. Einarsson <http://bre.klaki.net/>
#
# This is an IRC-to-WWW gateway designed to help Pirates have Meetings.
#
VERSION = 'v0.1'
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
import random
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


class Mutiny():
  """The main Mutiny class."""

  def __init__(self, config):
    self.work_dir = config['work_dir']
    self.listen_on = (config['http_host'], int(config['http_port']))
    self.config = config

    self.event_loop = SelectLoop()
    self.DEBUG = self.event_loop.DEBUG = self.config.get('debug', False)

    self.config_irc = config['irc']
    self.networks = {}

  def parse_spec(self, server):
    if ':' in server:
      proto, server = server.split(':', 1)
      if proto in ('ircs', 'sirc'): proto = 'ssl'
    else:
      proto = 'irc'
    if ':' in server:
      server, port = server.strip('/').rsplit(':', 1)
    else:
      server, port = server.strip('/'), (proto == 'ssl') and 6697 or 6667
    return proto, str(server), int(port)

  def start(self):
    if not os.path.exists(self.work_dir):
      os.mkdir(self.work_dir)
    for network, settings in self.config['irc'].iteritems():
      if settings['enable']:
        bot = self.networks[network] = IrcBot()
        bot.irc_nickname(settings['nickname'])
        bot.irc_channels(settings['channels'].keys())
        self.connect_client(network, bot)
    self.event_loop.start()

  def connect_client(self, network, client, server_spec=None):
    if not server_spec:
      server_spec = self.config['irc'][network]['servers'][0]
    proto, server, port = self.parse_spec(server_spec)
    print 'Connecting to %-15s %s://%s:%d/' % (network, proto, server, port)
    Connect(proto, server, port, *self.callbacks(network, client)).start()

  def stop(self):
    self.event_loop.stop()

  def failed(self, network, bot, socket):
    # FIXME: This is rather dumb, we should retry.
    self.stop()
    raise

  def callbacks(self, network, bot):
    def ok(sockfd):
      return self.connected(network, bot, sockfd)
    def fail(sockfd):
      return self.failed(network, bot, sockfd)
    return ok, fail

  def connected(self, network, bot, sockfd):
    print 'Connected to %s!' % (network)
    bot.process_connect(lambda d: self.event_loop.sendall(sockfd, d))
    self.event_loop.add(sockfd, bot)

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

  def renderChannelList(self):
    html = []
    networks = sorted([(n, self.config_irc[n])
                       for n in self.config_irc
                             if self.config_irc[n]['enable']])
    for net_id, network in networks:
      if len(networks) > 1:
        html.append('<li class="network">%s<ul>' % network.get('description',
                                                               net_id))
      channels = network['channels']
      for ch_id, channel in sorted([(i, c) for i, c in channels.items()]):
        if 'unlisted' not in channel.get('access', 'open'):
          html.append(('<li><a href="/join/%s/%s">%s</a></li>'
                       ) % (net_id, ch_id.replace('#', ''),
                            channel.get('description', ch_id)))
      if len(networks) > 1:
        html.append('</ul></li>')
    if html:
      html[0:0] = ['<ul class="channel_list">']
      html.append('</ul>')
    else:
      html = ['<ul class="channel_list_empty"><i>None, sorry</i></ul>']
    return ''.join(html)

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

    # Clear any expired cookies, update others, record credentials
    credentials = {}
    for c, v in cookies.items():
      try:
        prefix, network = c.split('-', 1)
        muid = v.value.split(',')[0]
        if (not network in self.networks or
            muid not in self.networks[network].users):
          req.setCookie(c, '', delete=True)
        else:
          log_id = v.value.split(',', 1)[1]
          user = self.networks[network].users[muid]
          if log_id != user.log_id:
            req.setCookie(c, '%s,%s' % (muid, user.log_id))
          else:
            user.seen = time.time()
            credentials[network] = user
      except (ValueError, KeyError):
        pass

    # Shared values for rendering templates
    page_url = req.absolute_url()
    page_prefix = '/'.join(page_url.split('/', 4)[:3])
    host = req.header('Host', 'unknown').lower()
    template = ''
    page = {
      'templates': os.path.join(self.work_dir, 'html'),
      'version': VERSION,
      'skin': host,
      'host': host,
      'page_path': '/'+path_url,
      'page_url': page_url,
    }

    # Get the actual content.
    try:
      if req.command == 'GET':

        if path == '':
          template = self.load_template('index.html', config=page)
          page.update({
            'linked_channel_list': self.renderChannelList()
          })

        elif path.startswith('_api/v1/'):
          return self.handleApiRequest(req, path, qs, posted, credentials)

        elif path.startswith('join/'):
          template, page = self.prepareChannelPage(path, page)

        elif (path.startswith('_skin/') or
              path in ('favicon.ico', )):
          template = self.load_template(path.split('/')[-1], config=page)
          mime_type = HttpdLite.GuessMimeType(path)
          if mime_type != 'application/octet-stream' and path.endswith('.gz'):
            headers.append(('Content-Encoding', 'gzip'))

        elif path.startswith('_authlite/') and req.auth_info:
          return self.handleUserLogin(req, page_prefix, path, qs)

        elif path == 'robots.txt':
          # FIXME: Have an explicit search-engine policy in settings?
          raise NotFoundException('FIXME')

        else:
          raise NotFoundException()

      elif req.command == 'POST':
        if path.startswith('_api/v1/'):
          return self.handleApiRequest(req, path, qs, posted, credentials)
        else:
          raise NotFoundException()

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

  def get_channel_from_path(self, path):
    join, network, channel = path.split('/')
    if join != 'join':
      raise ValueError('Invalid path')
    channel = self.fixup_channel(channel)
    return network, channel

  VALID_CHARS = 'abcdefghijklmnopqrstuvwxyz_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
  TRANSLATE = [
    # Some things we map to underscores.
    (u'\n\r\t\'\"&-', '_' * 100),
    # Icelandic map
    (u'\xe1\xe9\xed\xf3\xfa\xfd\xfe\xe6\xf6\xf0' +
     u'\xc1\xc9\xcd\xd3\xda\xdd\xde\xc6\xd6\xd0',
     ['a', 'e', 'i', 'o', 'u', 'y', 'th', 'a', 'o', 'd',
      'A', 'E', 'I', 'O', 'U', 'Y', 'Th', 'A', 'O', 'D'])
    # Add more maps here, unlisted chars get stripped. :-)
  ]
  def dumb_down(self, string):
    for src, dst in self.TRANSLATE:
      output = []
      for c in string:
        try:
          output.append(dst[src.index(c)])
        except ValueError:
          output.append(c)
      string = ''.join(output)
    return ''.join(i for i in string if i in self.VALID_CHARS)

  def handleUserLogin(self, req, page_prefix, path, qs):
    state = qs.get('state', ['/'])[0]
    network, channel = self.get_channel_from_path(state[1:])
    provider, token = req.auth_info
    profile = {
      'source': provider,
      'home': 'The Internet'
    }

    # First, pull details from their on-line profile, if possible...
    try:
      if provider == 'Facebook':
        fbp = req.server.auth_handler.getFacebookProfile(token)
        profile.update({
          'name': fbp.get('name'),
          'home': fbp.get('hometown', {}).get('name', 'The Internet'),
          'uid': 'fb%s' % fbp.get('id', ''),
          'pic': 'https://graph.facebook.com/%s/picture' % fbp.get('id', ''),
          'url': 'https://www.facebook.com/%s' % fbp.get('username',
                                                         fbp.get('id', ''))
        })

      elif provider == 'Google':
        profile = req.server.auth_handler.getGoogleProfile(token)

      else:
        print '*** Not sure how to get profiles from %s' % provider

    except (IOError, OSError):
      # Network problems...?
      pass

    # Create a nick-name for them
    nickname = profile.get('name', 'Guest %x' % random.randint(0, 10000))
    while (len(nickname) > 15 and ' ' in nickname):
      nickname = nickname.rsplit(' ', 1)[0]
    profile['nick'] = self.dumb_down(nickname)

    # Create an IRC client, start the connection.
    client = IrcClient().irc_profile(profile).irc_channels([channel])
    self.networks[network].users[client.uid] = client
    self.connect_client(network, client)

    # Finally, set a cookie with their client's UID.
    req.setCookie('muid-%s' % network, '%s,pending' % client.uid)

    print 'Logged in: %s' % json.dumps(profile, indent=2)
    return req.sendRedirect(page_prefix + state)

  def prepareChannelPage(self, path, page):
    network, channel = self.get_channel_from_path(path)
    nw_channels = self.config_irc.get(network, {}).get('channels', [])
    if channel in nw_channels:
      info = nw_channels[channel]
      page.update({
        'network': network,
        'network_desc': self.config_irc[network].get('description', network),
        'channel': channel,
        'channel_desc': info.get('description', channel),
        'channel_access': info.get('access', 'open').replace(',', ' '),
        'logged_in': 'no',
        'log_status': 'off',
        'log_not': 'not ',
        'log_url': '/',
      })
      template = self.load_template('channel.html', config=page)
      return template, page
    else:
      raise NotFoundException()

  CORS_HEADERS = [
    ('Access-Control-Allow-Origin', '*'),
    ('Access-Control-Allow-Methods', 'GET, POST'),
    ('Access-Control-Allow-Headers', 'content-length, authorization')
  ]

  def handleApiRequest(self, req, path, qs, posted, credentials):
    api, v1, network, channel = path.split('/')
    headers = self.CORS_HEADERS[:]
    method = (posted or qs).get('a', qs.get('a'))[0]
    mime_type, data = getattr(self, 'api_%s' % method
                              )(network, self.fixup_channel(channel),
                                req, qs, posted, credentials)
    return req.sendResponse(data,
                            mimetype=mime_type,
                            header_list=headers, cachectrl='no-cache')

  def api_log(self, network, channel, req, qs, posted, credentials):
    # FIXME: Choose between bots based on network

    grep = qs.get('grep', [''])[0]
    after = qs.get('seen', [None])[0]
    limit = int(qs.get('limit', [0])[0])
    timeout = int(qs.get('timeout', [0])[0])
    if timeout:
      timeout += time.time()

    data = []
    try:
      while not data:
        bot = self.networks[network]
        data = bot.irc_channel_log(channel)
        if after or grep:
          data = [x for x in data if (x[0] > after) and
                                     (not grep or
                                      grep in x[1]['nick'].lower() or
                                      grep in x[1].get('text', ''))]
        if timeout and not data:
          cond = threading.Condition()
          ev = self.event_loop.add_sleeper(timeout, cond, 'API request')
          bot.irc_watch_channel(channel, ev)
          cond.acquire()
          cond.wait()
          cond.release()
          self.event_loop.remove_sleeper(ev)
        if time.time() >= timeout:
          break
    except SelectAborted:
      pass

    if limit:
      data = data[-limit:]

    return 'application/json', json.dumps(data)

  def api_logout(self, network, channel, req, qs, posted, credentials):
    user = credentials[network]
    del self.networks[network].users[user.uid]
    req.setCookie('muid-%s' % network, '', delete=True)

    sockfd = self.event_loop.fds_by_uid[user.uid]
    self.event_loop.sendall(sockfd, 'QUIT :Logged off\r\n')
    return 'application/json', json.dumps(['ok'])

  def api_say(self, network, channel, req, qs, posted, credentials):
    sockfd = self.event_loop.fds_by_uid[credentials[network].uid]
    privmsg = 'PRIVMSG %s :%s\r\n' % (channel,
                                      posted['msg'][0].decode('utf-8'))
    self.event_loop.sendall(sockfd, privmsg.encode('utf-8'))
    return 'application/json', json.dumps(['ok'])


def Configuration():
  if '--version' in sys.argv:
    print '%s' % VERSION
    sys.exit(0)

  config = {
    'work_dir': DEFAULT_PATH,
    'http_port': 4950,
    'http_host': 'localhost',
    'lang': 'en',
    'skin': 'default',
    'debug': False,
    'irc': {},
    # These are ignored, but picked up by sockschain
    'nossl': None,
    'nopyopenssl': None,
  }

  # Set work dir before loading config, all other command-line arguments
  # will override the config file.
  for arg in sys.argv[1:]:
    if arg.startswith('--work_dir='):
      config['work_dir'] = arg.split('=', 1)[1]

  try:
    fd = open(os.path.join(config['work_dir'], 'config.json'), 'rb')
    config.update(json.load(fd))
  except ValueError, e:
    print 'Failed to parse config: %s' % e
    sys.exit(1)
  except (OSError, IOError):
    pass

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

  nickname = server = channels = None
  if len(sys.argv) > 1:
    config['irc']['irc'] = {
      'enable': 1,
      'nickname': sys.argv.pop(1).replace(' ', '_'),
      'userinfo': 'Mutiny %s' % VERSION
    }
  if len(sys.argv) > 1:
    arg = sys.argv.pop(1)
    config['irc']['irc']['servers'] = [
      arg.rsplit('/', 1)[0]
    ]
    config['irc']['irc']['channels'] = channels = {}
    for channel in arg.rsplit('/', 1)[1].split(',', 1):
      channels[channel] = {'description': 'IRC channel', 'access': 'open'}
  if len(sys.argv) > 1:
    arg = sys.argv.pop(1)
    for channel in channels:
      channels[channel]['access'] = arg

  print 'Config is: %s' % json.dumps(config, indent=2)
  return config


if __name__ == "__main__":
  try:
    mutiny = Mutiny(Configuration())
  except (IndexError, ValueError, OSError, IOError):
    print '%s\n' % traceback.format_exc()
    print 'Usage: %s <nick> irc://<server:port>/<channel>' % sys.argv[0]
    print '       %s <nick> ssl://<server:port>/<channel>' % sys.argv[0]
    print
    print 'Logs and settings will be stored here: %s' % config['work_dir']
    print
    sys.exit(1)
  try:
    try:
      print 'This is Mutiny.py, listening on http://%s:%s/' % mutiny.listen_on
      print 'Fork me on Github: https://github.com/pagekite/plugins-pyMutiny'
      print

      auth_handler = HttpdLite.AuthHandler()
      auth_cfg = mutiny.config.get('oauth2', {})
      for provider in auth_cfg:
        if provider in auth_handler.oauth2:
          auth_handler.oauth2[provider].update(auth_cfg[provider])
        else:
          auth_handler.oauth2[provider] = auth_cfg[provider]

      mutiny.start()
      HttpdLite.Server(mutiny.listen_on, mutiny,
                       auth_handler=auth_handler).serve_forever()
    except KeyboardInterrupt:
      mutiny.stop()
  except:
    mutiny.stop()
    raise

