import re
import os

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

import json
import datetime
from dateutil.tz import tzlocal
from babel.dates import format_timedelta
from dateutil.parser import parse


def _parse_airstamp(airstamp):
    if not airstamp:
        return None

    try:
        airtime = parse(airstamp)
    except (TypeError, ValueError, OverflowError):
        return None

    if airtime.tzinfo is None:
        return airtime.replace(tzinfo=tzlocal())

    return airtime


def _format_episode_airtime(airtime, now=None):
    if airtime is None:
        return 'an unknown date'

    if now is None:
        now = datetime.datetime.now(tzlocal())

    local_airtime = airtime.astimezone(tzlocal())
    if abs(airtime - now) < datetime.timedelta(hours=24):
        return local_airtime.strftime('%Y-%m-%d %H:%M %Z')

    return local_airtime.strftime('%Y-%m-%d')


def _format_relative_airtime(airtime, now=None):
    if airtime is None:
        return 'airtime unavailable'

    if now is None:
        now = datetime.datetime.now(tzlocal())

    delta = airtime - now
    relative_time = format_timedelta(abs(delta), granularity='minutes')

    if delta.total_seconds() >= 0:
        return 'in %s' % relative_time

    return '%s ago' % relative_time


def _format_episode(prefix, episode, color, now=None):
    if not episode:
        return ''

    episode_code = '%sx%s' % (episode.get('season', '?'), episode.get('number', '?'))
    episode_name = episode.get('name', 'Unknown')
    airtime = _parse_airstamp(episode.get('airstamp'))
    display_time = _format_episode_airtime(airtime, now=now)
    relative_time = _format_relative_airtime(airtime, now=now)

    return format('%s: [%s] %s on %s (%s).',
            ircutils.underline(prefix),
            ircutils.bold(episode_code),
            ircutils.bold(episode_name),
            ircutils.bold(display_time),
            ircutils.mircColor(relative_time, color))


def _format_show_schedule(show):
    network = show.get('network') or {}
    web_channel = show.get('webChannel') or {}
    schedule = show.get('schedule') or {}
    timezone = ((network.get('country') or {}).get('timezone') or
                (web_channel.get('country') or {}).get('timezone'))

    if network:
        show_network = format('%s', ircutils.bold(network.get('name', 'Unknown network')))

        days = ', '.join(schedule.get('days') or ['Unknown day'])
        schedule_time = schedule.get('time') or 'Unknown time'
        show_schedule = format('%s: %s @ %s',
                ircutils.underline('Schedule'),
                ircutils.bold(days),
                ircutils.bold(schedule_time))
        if timezone:
            show_schedule = format('%s %s', show_schedule, ircutils.bold(timezone))
    else:
        show_network = format('%s',
            ircutils.bold(web_channel.get('name', 'Unknown web channel')))

        premiered = show.get('premiered') or 'Unknown'
        show_schedule = format('%s: %s',
                ircutils.underline('Premiered'),
                ircutils.bold(premiered))

    genres = '/'.join(show.get('genres') or ['Unknown'])
    show_genre = format('%s: %s/%s',
            ircutils.underline('Genre'),
            ircutils.bold(show.get('type', 'Unknown')),
            genres)

    return format('%s on %s. %s', show_schedule, show_network, show_genre)

def fetch(show=False, country='US'):
    if show:
        query_string = '?q=' + utils.web.urlquote(show) + '&embed[]=previousepisode&embed[]=nextepisode'
        url = 'http://api.tvmaze.com/singlesearch/shows' + query_string
    else:
        url = 'http://api.tvmaze.com/schedule?country=' + utils.web.urlquote(country)

    try:
        resp = utils.web.getUrl(url)
    except utils.web.Error as e:
        return False
    
    data = json.loads(resp.decode('utf-8'))

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
                elif stuff == 'detail':
                    details = True

        show = fetch(tvshow)

        if show:
            if show.get('premiered'):
                premiered = show['premiered']
            else:
                premiered = "SOON"

            show_state = format('%s %s (%s).',
                    ircutils.bold(ircutils.underline(show.get('name', tvshow))),
                    premiered[:4], show.get('status', 'Unknown'))

            embedded = show.get('_embedded') or {}
            now = datetime.datetime.now(tzlocal())

            if 'previousepisode' in embedded:
                last_episode = _format_episode(
                        'Previous Episode',
                        embedded.get('previousepisode'),
                        'red',
                        now=now)
            else:
                last_episode = ''

            if 'nextepisode' in embedded:
                next_episode = _format_episode(
                        'Next Episode',
                        embedded.get('nextepisode'),
                        'green',
                        now=now)
            else:
                next_episode = format('%s: %s.',
                        ircutils.underline('Next Episode'),
                        ircutils.bold('not yet scheduled'))

            
            irc.reply(format('%s %s %s %s', show_state, last_episode, next_episode, show['url']))
        else:
            irc.reply(format('No show found named "%s"', ircutils.bold(tvshow)))
            return

        if details:
            irc.reply(_format_show_schedule(show))
        
    tv = wrap(tv, [getopts({'d': '', 'detail': ''}), 'text'])

    def schedule(self, irc, msg, args, opts):
        """[--country <ISO 3166-1 alpha-2 code>]

        """
        country = 'US'
        for (opt, arg) in opts:
            if opt == 'country':
                country = arg.upper()

        if not re.match(r'^[A-Z]{2}$', country):
            irc.reply('Invalid country code. Use a 2-letter ISO 3166-1 alpha-2 code, for example US or GB.')
            return

        shows = fetch(False, country=country)
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

    schedule = wrap(schedule, [getopts({'country': 'somethingWithoutSpaces'})])

                

Class = tvmaze

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
