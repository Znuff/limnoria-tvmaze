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

class tvmaze(callbacks.Plugin):
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
                        ircutils.bold(show['_embedded']['nextepisode']['airdate']),
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
