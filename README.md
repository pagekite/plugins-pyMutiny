# mutiny.py #

"Mutiny is what you get whan Pirates have Meetings."

This is an HTTP server implementing a web-interface for a single IRC channel,
geared towards accessibility and managing structured meetings.  It is being
written for the Icelandic pirate party.


## Getting started ##

Quick-start:

   1. Download [mutiny-v0.1.py](https://raw.github.com/pagekite/plugins-pyMutiny/master/bin/mutiny-v0.1.py)
   2. In a console: `python ./mutiny-v0.1.py BOTNAME "irc://irc.server.net:6667/#channel"`
   3. Open up `http://localhost:4950/` in your browser

You should now be able to see what is going on in the channel.


## Play! ##

...


## Themes and Translations ##

Mutiny pulls all HTML templates and messages used by the bot from a some
predictable locations, falling back to built-in defaults if nothing more
interesting is found.

The default location to look for templates, media, CSS etc. is:

    ~/.mutiny/html/HOST/LANG/...

Where HOST is the DNS host name of the web server and LANG is a language
code.  Default values are `default` and `en`.


## Hacking ##

The file `mutiny-XXX.py` is combination of `Mutiny` and the non-standard
modules it depends on.  For hacking, you'll want to check them all out from
[github](https://github.com/):

   * [Mutiny](https://github.com/pagekite/plugins-pyMutiny)
   * [HttpdLite](https://github.com/pagekite/plugins-pyHttpdLite)
   * [SocksipyChain](https://github.com/pagekite/pySocksipyChain)

The combined "binary" is generated using
[Breeder](https://github.com/pagekite/PyBreeder).


## Bugs ##

   * Does not reconnect when disconnected
   * The web UI sometimes stops refreshing


## Ideas ##

A bunch of ideas by importance/feasibility:

   * Twitter / Google / BrowserID+Gravatar authenticated sign in
   * Invite-only or Authenticated-only channels
   * Tagging/Starring/ThumbsUp/ThumbsDown for comments in the web UI
   * Election helper
   * Permanent logging
   * Browsable stored logs
   * Curation: Ways to extract and publish conversation fragments.
   * Nickserv support
   * Search engine
   * Channels as RSS / Atom / ActivityStreams?
   * Embeddeable UI for use as blog commenting engine?
   * Rebroadcast Twitter / ActivityStream feeds
   * Traditional bot roles: Banning users etc.
   * Learn from: https://wiki.ubuntu.com/meetingology

Done:

   * OAuth2 log-in/out: Facebook works
   * Chatting
   * Filtered view
   * Auto-link URLs


## Credits ##

Created by Bjarni R. Einarsson <http://bre.klaki.net/> for the fledgeling
Icelandic Pirate Party.

Other contributors:

   * *your name here!*

