import datetime
import importlib.util
import pathlib
import sys
import unittest
from unittest import mock

from dateutil.tz import tzoffset
from supybot.test import *


PLUGIN_PATH = pathlib.Path(__file__).with_name('plugin.py')
PLUGIN_SPEC = importlib.util.spec_from_file_location('tvmaze_plugin', PLUGIN_PATH)
plugin_module = importlib.util.module_from_spec(PLUGIN_SPEC)
sys.modules[PLUGIN_SPEC.name] = plugin_module
PLUGIN_SPEC.loader.exec_module(plugin_module)


class FakeIrc(object):
    def __init__(self):
        self.replies = []

    def reply(self, message):
        self.replies.append(message)


class tvmazeTestCase(PluginTestCase):
    plugins = ('tvmaze',)


class EpisodeFormattingTestCase(unittest.TestCase):
    def test_relative_airtime_formats_future_and_past(self):
        now = datetime.datetime(2024, 5, 10, 20, 0, tzinfo=datetime.timezone.utc)

        future = plugin_module._format_relative_airtime(
                now + datetime.timedelta(hours=2), now=now)
        past = plugin_module._format_relative_airtime(
                now - datetime.timedelta(hours=2), now=now)

        self.assertEqual(future, 'in 2 hours')
        self.assertEqual(past, '2 hours ago')

    def test_episode_output_uses_airstamp_with_local_timezone(self):
        episode = {
            'season': 2,
            'number': 3,
            'name': 'Crossing Midnight',
            'airstamp': '2024-05-10T23:30:00-04:00',
        }
        local_tz = tzoffset('LOCAL', 2 * 60 * 60)
        now = datetime.datetime(2024, 5, 10, 22, 0, tzinfo=datetime.timezone.utc)

        with mock.patch.object(plugin_module, 'tzlocal', return_value=local_tz):
            message = plugin_module._format_episode(
                    'Next Episode', episode, 'green', now=now)

        self.assertIn('2024-05-11 05:30 LOCAL', message)
        self.assertIn('in 6 hours', message)

    def test_episode_output_uses_date_only_beyond_twenty_four_hours(self):
        episode = {
            'season': 2,
            'number': 4,
            'name': 'Next Week',
            'airstamp': '2024-05-17T23:30:00-04:00',
        }
        local_tz = tzoffset('LOCAL', 2 * 60 * 60)
        now = datetime.datetime(2024, 5, 10, 22, 0, tzinfo=datetime.timezone.utc)

        with mock.patch.object(plugin_module, 'tzlocal', return_value=local_tz):
            message = plugin_module._format_episode(
                    'Next Episode', episode, 'green', now=now)

        self.assertIn('2024-05-18', message)
        self.assertNotIn('LOCAL', message)
        self.assertIn('in 1 week', message)

    def test_schedule_output_includes_network_timezone(self):
        show = {
            'network': {
                'name': 'Example Network',
                'country': {'timezone': 'America/New_York'},
            },
            'schedule': {'days': ['Friday'], 'time': '21:00'},
            'type': 'Scripted',
            'genres': ['Drama'],
        }

        message = plugin_module._format_show_schedule(show)

        self.assertIn('America/New_York', message)
        self.assertIn('Friday', message)

    def test_tv_detail_mode_returns_after_missing_show(self):
        irc = FakeIrc()
        unwrapped_tv = plugin_module.tvmaze.tv.__closure__[0].cell_contents

        with mock.patch.object(plugin_module, 'fetch', return_value=False):
            unwrapped_tv(object(), irc, None, None, [('detail', '')], 'missing')

        self.assertEqual(len(irc.replies), 1)
        self.assertIn('No show found named', irc.replies[0])

    def test_schedule_defaults_to_us_country(self):
        irc = FakeIrc()
        unwrapped_schedule = plugin_module.tvmaze.schedule.__closure__[0].cell_contents

        with mock.patch.object(plugin_module, 'fetch', return_value=[]) as mocked_fetch:
            unwrapped_schedule(object(), irc, None, None, [])

        mocked_fetch.assert_called_once_with(False, country='US')

    def test_schedule_country_option_is_uppercased(self):
        irc = FakeIrc()
        unwrapped_schedule = plugin_module.tvmaze.schedule.__closure__[0].cell_contents

        with mock.patch.object(plugin_module, 'fetch', return_value=[]) as mocked_fetch:
            unwrapped_schedule(object(), irc, None, None, [('country', 'gb')])

        mocked_fetch.assert_called_once_with(False, country='GB')

    def test_schedule_country_option_rejects_invalid_codes(self):
        irc = FakeIrc()
        unwrapped_schedule = plugin_module.tvmaze.schedule.__closure__[0].cell_contents

        with mock.patch.object(plugin_module, 'fetch') as mocked_fetch:
            unwrapped_schedule(object(), irc, None, None, [('country', 'usa')])

        mocked_fetch.assert_not_called()
        self.assertEqual(len(irc.replies), 1)
        self.assertIn('Invalid country code', irc.replies[0])

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
