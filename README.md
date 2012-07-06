# Mutiny.py #

"Mutiny is what you get whan Pirates have Meetings."

This is an HTTP server implementing a web-interface for a single IRC channel,
geared towards accessibility and managing structured meetings.  It was written
for the Icelandic pirate party.


## Getting started ##

Quick-start:

   1. Download [Mutiny.combined.py](https://raw.github.com/pagekite/plugins-pyMutiny/master/bin/Mutiny.combined.py)
   2. In a console: `python ./Mutiny.combined.py BOTNAME irc.server.net:#channel`
   3. Open up `http://localhost:2127/` in your browser

You should now be able to see what is going on in the channel.


## Play! ##

...


## Hacking ##

The file `Mutiny.combined.py` is combination of `Mutiny.py` and the
`HttpdLite.py` module it depends on.  For hacking, you'll want to check
both out from [github](https://github.com/):

   * [Mutiny.py](https://github.com/pagekite/plugins-pyMutiny)
   * [HttpdLite.py](https://github.com/pagekite/plugins-pyHttpdLite)

The combined "binary" is generated using
[Breeder](https://github.com/pagekite/PyBreeder).


## Bugs ##

   * ...

