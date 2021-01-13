# Copyright (c) 2018 Cisco Systems, Inc.
# All rights reserved.

__author__ = 'jonpsull'

import es_logger
from jenkins import JenkinsException
import nose
import unittest.mock


class TestArtifactEvent(object):

    def test_artifact_event_json_decode_error(self):
        eg = es_logger.plugins.artifact.ArtifactEvent()
        fields = eg.get_fields()
        nose.tools.ok_(fields == es_logger.interface.EventGenerator.DEFAULT_FIELDS)

        esl = unittest.mock.MagicMock()
        esl.console_log = 'log'
        esl.build_info = {'artifacts': [{'relativePath': 'es-logger-data.json'}]}
        # Invalid json as not in []
        esl.server.get_build_artifact.return_value = ('{"name": "event1"},'
                                                      + '{"name": "event2"}')

        with nose.tools.assert_logs(level='DEBUG') as cm:
            events = eg.generate_events(esl)

        nose.tools.ok_(events == [])
        nose.tools.assert_equal(
            cm.output,
            ['WARNING:es_logger.plugins.artifact:JSONDecodeError when attempting to get '
             + 'es-logger-data.json artifact: Extra data: line 1 column 19 (char 18)',
             'WARNING:es_logger.plugins.artifact:Data: {"name": "event1"},{"name": "event2"}',
             'INFO:es_logger.plugins.artifact:No saved event data found in artifact '
             + 'es-logger-data.json',
             'DEBUG:es_logger.plugins.artifact:Data: []'])

    def test_artifact_event_jenkins_exception(self):
        eg = es_logger.plugins.artifact.ArtifactEvent()
        fields = eg.get_fields()
        nose.tools.ok_(fields == es_logger.interface.EventGenerator.DEFAULT_FIELDS)

        esl = unittest.mock.MagicMock()
        esl.console_log = 'log'
        esl.build_info = {'artifacts': [{'relativePath': 'es-logger-data.json'}]}
        esl.server.get_build_artifact.side_effect = JenkinsException("Bad download")

        with nose.tools.assert_logs(level='DEBUG') as cm:
            events = eg.generate_events(esl)

        nose.tools.ok_(events == [])
        nose.tools.assert_equal(
            cm.output,
            ['WARNING:es_logger.plugins.artifact:JenkinsException when attempting to get '
             + 'es-logger-data.json artifact: Bad download',
             'INFO:es_logger.plugins.artifact:No saved event data found in artifact '
             + 'es-logger-data.json',
             'DEBUG:es_logger.plugins.artifact:Data: []'])

    def test_artifact_event(self):
        eg = es_logger.plugins.artifact.ArtifactEvent()
        fields = eg.get_fields()
        nose.tools.ok_(fields == es_logger.interface.EventGenerator.DEFAULT_FIELDS)

        esl = unittest.mock.MagicMock()
        esl.console_log = 'log'
        esl.build_info = {'artifacts': [{'relativePath': 'es-logger-data.json'}]}
        esl.server.get_build_artifact.return_value = ('[{"name": "event1"},'
                                                      + '{"name": "event2"},'
                                                      + '{"name": "event3"}]')

        events = eg.generate_events(esl)
        nose.tools.ok_(len(events) == 3,
                       "Wrong number of events returned ({}): {}".format(len(events), events))
        results = [{"name": "event1"}, {"name": "event2"}, {"name": "event3"}]

        for idx, event in enumerate(events):
            nose.tools.ok_(event == results[idx],
                           "Bad event[{}] returned: {}".format(idx, events))

    @unittest.mock.patch.dict('os.environ', {'ES_EVENT_ARTIFACT': 'random.json'})
    def test_artifact_event_env_filename(self):
        eg = es_logger.plugins.artifact.ArtifactEvent()
        fields = eg.get_fields()
        nose.tools.ok_(fields == es_logger.interface.EventGenerator.DEFAULT_FIELDS)

        esl = unittest.mock.MagicMock()
        esl.console_log = 'log'
        esl.build_info = {'artifacts': [{'relativePath': 'random.json'}]}
        esl.server.get_build_artifact.return_value = ('[{"name": "event1"},'
                                                      + '{"name": "event2"},'
                                                      + '{"name": "event3"}]')

        events = eg.generate_events(esl)
        nose.tools.ok_(len(events) == 3,
                       "Wrong number of events returned ({}): {}".format(len(events), events))
        results = [{"name": "event1"}, {"name": "event2"}, {"name": "event3"}]

        for idx, event in enumerate(events):
            nose.tools.ok_(event == results[idx],
                           "Bad event[{}] returned: {}".format(idx, events))
