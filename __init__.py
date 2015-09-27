"""
Lists the current playing track on online radios
"""

import supybot
import supybot.world as world

__version__ = "0.0.1"
__author__ = supybot.authors.jemfinch

# This is a dictionary mapping supybot.Author instances to lists of
# contributions.
__contributors__ = {}

import config
import plugin
reload(plugin) # In case we're being reloaded.

if world.testing:
    import test

Class = plugin.Class
configure = config.configure

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
