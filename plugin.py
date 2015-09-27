###
# Copyright (c) 2004, Jeremiah Fincher
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

import re
import os

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from urllib2 import urlopen, URLError, quote

import json
import datetime
from dateutil.tz import tzlocal
from babel.dates import format_timedelta
from dateutil.parser import parse

def fetch(show=False):
    if show:
        query_string = '?q=' + quote(show) + '&embed[]=previousepisode&embed[]=nextepisode'
        url = 'http://api.tvmaze.com/singlesearch/shows' + query_string
    else:
        url = 'http://api.tvmaze.com/schedule?country=US'

    try:
        resp = utils.web.getUrl(url)
    except utils.web.Error, e:
        return False
    
    data = json.loads(resp)

    return data

class tvmaze(callbacks.Privmsg):
    threaded=True

    def tv(self, irc, msg, args, opts, tvshow):
        """[-d | --detail] <tvshow>

        """
        
        if not opts:
            details = False
        else:
            for (stuff, arg) in opts:
                if stuff == 'd':
                    details = True
                elif stuff == 'details':
                    details = True

        show = fetch(tvshow)

        if show:
            show_state = format('%s %s (%s).',
                    ircutils.bold(ircutils.underline(show['name'])),
                    show['premiered'][:4], show['status'])
            
            if 'previousepisode' in show['_embedded']:
                airtime = parse(show['_embedded']['previousepisode']['airstamp'])
                timedelta = datetime.datetime.now(tzlocal()) - airtime
                relative_time = format_timedelta(timedelta,
                        granularity='minutes')
                last_episode = format('%s: [%s] %s on %s (%s).',
                        ircutils.underline('Previous Episode'),
                        ircutils.bold(str(show['_embedded']['previousepisode']['season'])
                            + 'x' +
                            str(show['_embedded']['previousepisode']['number'])),
                        ircutils.bold(show['_embedded']['previousepisode']['name']),
                        ircutils.bold(show['_embedded']['previousepisode']['airdate']),
                        ircutils.mircColor(relative_time, 'red'))
            else:
                last_episode = ''

            if 'nextepisode' in show['_embedded']:
                airtime = parse(show['_embedded']['nextepisode']['airstamp'])
                timedelta = datetime.datetime.now(tzlocal()) - airtime
                relative_time = format_timedelta(timedelta, granularity='minutes')

                next_episode = format('%s: [%s] %s on %s (%s).',
                        ircutils.underline('Next Episode'),
                        ircutils.bold(str(show['_embedded']['nextepisode']['season'])
                            + 'x' +
                            str(show['_embedded']['nextepisode']['number'])),
                        ircutils.bold(show['_embedded']['nextepisode']['name']),
                        ircutils.bold(show['_embedded']['previousepisode']['airdate']),
                        ircutils.mircColor(relative_time, 'green'))
            else:
                next_episode = format('%s: %s.',
                        ircutils.underline('Next Episode'),
                        ircutils.bold('not yet scheduled'))

            
            irc.reply(format('%s %s %s %s', show_state, last_episode, next_episode, show['url']))
        else:
            irc.reply(format('No show found named "%s"', ircutils.bold(tvshow)))

        if details:
            show_network = format('%s',
                    ircutils.bold(show['network']['name']))

            show_schedule = format('%s: %s @ %s',
                    ircutils.underline('Schedule'),
                    ircutils.bold(', '.join(show['schedule']['days'])),
                    ircutils.bold(show['schedule']['time']))

            show_genre = format('%s: %s/%s',
                    ircutils.underline('Genre'),
                    ircutils.bold(show['type']),
                    '/'.join(show['genres']))


            irc.reply(format('%s on %s. %s', show_schedule, show_network,
                show_genre))
        
    tv = wrap(tv, [getopts({'d': '', 'detail': ''}), 'text'])

    def schedule(self, irc, msg, args):
        """

        """
        shows = fetch(False)
        l = []

        if shows:
            for show in shows:
                if show['show']['type'] == 'Scripted':
                    this_show = format('%s [%s] (%s)',
                            ircutils.bold(show['show']['name']),
                            str(show['season']) + 'x' + str(show['number']),
                            show['airtime'])
                    l.append(this_show)
        
        tonight_shows = ', '.join(l)

        irc.reply(format('%s: %s',
            ircutils.underline("Tonight's Shows"),
            tonight_shows))

                

Class = tvmaze

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
