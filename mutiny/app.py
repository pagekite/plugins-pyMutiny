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
import hashlib
import json
import os
import random
import re
import time
import urllib

import HttpdLite


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
  def __init__(self, log_path):
    self.log_path = log_path
    self.listen_on = ('localhost', 4950)  # 99 bottles of beer on the wall!
    os.mkdir(self.log_path)

  def stop(self):
    pass

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
    log_path = os.path.expanduser('~/.Mutiny')
    mutiny = Mutiny(log_path)
  except (IndexError, ValueError, OSError, IOError):
    print 'Usage: %s' % sys.argv[0]
    print
    print 'The program will store logs here: %s' % log_path
    print
    sys.exit(1)
  try:
    try:
      print 'This is Mutiny.py, listening on %s:%s' % mutiny.listen_on
      print 'Fork me on Github: https://github.com/pagekite/plugins-pyMutiny'
      print
      HttpdLite.Server(mutiny.listen_on, mutiny,
                       handler=RequestHandler).serve_forever()
    except KeyboardInterrupt:
      mutiny.stop()
  except:
    mutiny.stop()
    raise

