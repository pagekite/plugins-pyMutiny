# mutiny.py #

"Mutiny is what you get whan Pirates have Meetings."

This is an HTTP server implementing a web-interface for a single IRC channel,
geared towards accessibility and managing structured meetings.  It was written
for the Icelandic pirate party.


## Getting started ##

Quick-start:

   1. Download [mutiny-v0.1.py](https://raw.github.com/pagekite/plugins-pyMutiny/master/bin/mutiny-v0.1.py)
   2. In a console: `python ./mutiny-v0.1.py BOTNAME irc.server.net:#channel`
   3. Open up `http://localhost:4950/` in your browser

You should now be able to see what is going on in the channel.


## Play! ##

...


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

   * ...

