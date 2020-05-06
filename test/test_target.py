# Copyright (c) 2018 Cisco Systems, Inc.
# All rights reserved.

__author__ = 'jonpsull'

from es_logger.plugins.target import LogstashPostError, LogstashTarget
import nose
import os
import requests
import unittest.mock


class TestLogstashTarget(object):

    def setup(self):
        self.lt = LogstashTarget()

    @unittest.mock.patch.dict('os.environ', {'LOGSTASH_SERVER': "https://example.com",
                                             'LS_USER': 'user',
                                             'LS_PASSWORD': 'pass'})
    def test_LogstashTarget(self):
        lt = LogstashTarget()
        nose.tools.ok_(lt.get_logstash_server() == os.getenv('LOGSTASH_SERVER'))
        nose.tools.ok_(lt.get_ls_user() == os.getenv('LS_USER'))
        nose.tools.ok_(lt.get_ls_password() == os.getenv('LS_PASSWORD'))

    @unittest.mock.patch('requests.Session')
    def test_get_session(self, mock_session):
        self.lt.get_session()
        print(mock_session.mock_calls)
        nose.tools.ok_(self.lt.ls_session is not None,
                       "Session is None: {}".format(self.lt.ls_session))

    @unittest.mock.patch('requests.Session')
    def test_send_event_good(self, mock_session):
        mock_session().post().ok = True
        res = self.lt.send_event({"event": "event"})
        nose.tools.ok_(res == 0,
                       "res not 0: {}".format(res))

    @unittest.mock.patch('requests.Session')
    def test_send_event_bad(self, mock_session):
        mock_session().post().ok = False
        res = self.lt.send_event({"event": "event"})
        nose.tools.ok_(res == 1,
                       "res not 1: {}".format(res))

    @unittest.mock.patch('requests.Session')
    def test_send_event_bad_session(self, mock_session):
        mock_session().post.side_effect = requests.exceptions.ReadTimeout
        self.lt.timeout_sleep = 0
        nose.tools.assert_raises(LogstashPostError, self.lt.send_event, {"event": "event"})
        # We should see this created and called 5 times attempting to get post finished
        calls = [unittest.mock.call(),
                 unittest.mock.call(),
                 unittest.mock.call().post(None, json={'event': 'event'}),
                 unittest.mock.call(),
                 unittest.mock.call().post(None, json={'event': 'event'}),
                 unittest.mock.call(),
                 unittest.mock.call().post(None, json={'event': 'event'}),
                 unittest.mock.call(),
                 unittest.mock.call().post(None, json={'event': 'event'}),
                 unittest.mock.call(),
                 unittest.mock.call().post(None, json={'event': 'event'})]
        print(mock_session.mock_calls)
        nose.tools.ok_(mock_session.mock_calls == calls)

    @unittest.mock.patch('requests.Session')
    def test_send_event_bad_post(self, mock_session):
        mock_session().post.side_effect = Exception
        self.lt.timeout_sleep = 0
        nose.tools.assert_raises(LogstashPostError, self.lt.send_event, {"event": "event"})

    def test_validate(self):
        ret = self.lt.validate()
        nose.tools.ok_(ret, "Validate must return True")
