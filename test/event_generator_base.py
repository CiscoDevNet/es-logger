__author__ = 'jonpsull'

import es_logger
import nose.tools
import unittest.mock


class TestEventGenerator(object):
    def setup(self):
        self.esl = unittest.mock.MagicMock(
            spec=es_logger.EsLogger, console_log='Log', build_info={}, es_info={},
            data_name='eslogger')

    def expected_fields_check(self, fields, additional):
        expected_fields = es_logger.interface.EventGenerator.DEFAULT_FIELDS + additional
        nose.tools.ok_(fields == expected_fields,
                       "Unexpected value for fields: {}\nExpected: {}".format(fields,
                                                                              expected_fields))

    def return_length_check(self, ret, expected):
        nose.tools.ok_(len(ret) == expected,
                       "Incorrect number of events returned, got {} expected {}: {}".format(
                       len(ret), expected, ret))

    def check_named_match(self, event, named_match, expected):
        nose.tools.ok_(named_match in event['named_matches'])
        nose.tools.ok_(event['named_matches'][named_match] == expected,
                       "Incorrect named_match {}: got '{}' expected '{}'".format(
                           named_match, event['named_matches'][named_match], expected))
