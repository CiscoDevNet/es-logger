# Copyright (c) 2018 Cisco Systems, Inc.
# All rights reserved.

__author__ = 'jonpsull'

import es_logger
import nose
import unittest.mock


class TestJUnitEvent(object):
    def test_junit_fields(self):
        eg = es_logger.plugins.junit.JUnitEvent()
        fields = eg.get_fields()
        nose.tools.ok_(fields != es_logger.interface.EventGenerator.DEFAULT_FIELDS)

    def test_no_test_report(self):
        eg = es_logger.plugins.junit.JUnitEvent()
        esl = unittest.mock.MagicMock()
        esl.get_test_report.return_value = None
        events = eg.generate_events(esl)
        nose.tools.ok_(len(events) == 0)

    def test_with_test_report(self):
        eg = es_logger.plugins.junit.JUnitEvent()
        esl = unittest.mock.MagicMock()
        esl.get_test_report.return_value = {
            "_class": "hudson.tasks.junit.TestResult", "testActions": [], "duration": 4550245900,
            "empty": False, "failCount": 2, "passCount": 1, "skipCount": 1, "suites": [{
                "cases": [{
                    "testActions": [], "age": 0, "className": "com.test.one.Test",
                    "duration": 0.638, "errorDetails": None, "errorStackTrace": None,
                    "failedSince": 0, "name": "testone", "skipped": False,
                    "skippedMessage": None, "status": "PASSED", "stderr": "", "stdout": ""
                }, {
                    "testActions": [], "age": 0, "className": "com.test.two.Test",
                    "duration": 0.053, "errorDetails": None, "errorStackTrace": None,
                    "failedSince": 0, "name": "testtwo", "skipped": False, "skippedMessage": None,
                    "status": "SKIPPED", "stderr": "", "stdout": ""
                }, {
                    "testActions": [], "age": 0, "className": "com.test.three.Test",
                    "duration": 0.053, "errorDetails": 'Error Detail', "errorStackTrace": None,
                    "failedSince": 0, "name": "testthree", "skipped": False,
                    "skippedMessage": None, "status": "FAILED", "stderr": "", "stdout": ""
                }],
                "duration": 1516748670, "id": None, "name": "com.suite.one.Suite", "stderr": "",
                "stdout": "", "timestamp": "1970-01-01T00:00:00"
            }, {
                "cases": [{
                    "testActions": [], "age": 0, "className": "com.test.three.Test",
                    "duration": 0.551, "errorDetails": None, "errorStackTrace": None,
                    "failedSince": 0, "name": "testfour", "skipped": False, "skippedMessage": None,
                    "status": "REGRESSION", "stderr": "", "stdout": ""
                }],
                "duration": 0.551, "id": None, "name": "com.suite.two.Suite", "stderr": "",
                "stdout": "", "timestamp": "2018-01-23T23:05:17"
            }]}
        events = eg.generate_events(esl)
        nose.tools.ok_(len(events) == 7,
                       "Wrong number of events returned ({}): {}".format(len(events), events))
        results = [
            {'testActions': [], 'age': 0, 'className': 'com.test.one.Test', 'duration': 0.638,
             'errorDetails': None, 'errorStackTrace': None, 'failedSince': 0, 'name': 'testone',
             'skipped': False, 'skippedMessage': None, 'status': 'PASSED', 'stderr': '',
             'stdout': '', 'suite': 'com.suite.one.Suite', 'type': 'case',
             'errorDetailsTruncated': None},
            {'testActions': [], 'age': 0, 'className': 'com.test.two.Test', 'duration': 0.053,
             'errorDetails': None, 'errorStackTrace': None, 'failedSince': 0, 'name': 'testtwo',
             'skipped': False, 'skippedMessage': None, 'status': 'SKIPPED', 'stderr': '',
             'stdout': '', 'suite': 'com.suite.one.Suite', 'type': 'case',
             'errorDetailsTruncated': None},
            {'testActions': [], 'age': 0, 'className': 'com.test.three.Test', 'duration': 0.053,
             'errorDetails': 'Error Detail', 'errorStackTrace': None, 'failedSince': 0,
             'name': 'testthree', 'skipped': False, 'skippedMessage': None, 'status': 'FAILED',
             'stderr': '', 'stdout': '', 'suite': 'com.suite.one.Suite', 'type': 'case',
             'errorDetailsTruncated': 'Error Detail'},
            {'duration': 1516748670, 'id': None, 'name': 'com.suite.one.Suite', 'stderr': '',
             'stdout': '', 'timestamp': '1970-01-01T00:00:00', 'passCount': 1, 'skipCount': 1,
             'failCount': 1, 'unknownCount': 0, 'totalCount': 3, 'type': 'suite'},
            {'testActions': [], 'age': 0, 'className': 'com.test.three.Test', 'duration': 0.551,
             'errorDetails': None, 'errorStackTrace': None, 'failedSince': 0, 'name': 'testfour',
             'skipped': False, 'skippedMessage': None, 'status': 'REGRESSION', 'stderr': '',
             'stdout': '', 'suite': 'com.suite.two.Suite', 'type': 'case',
             'errorDetailsTruncated': None},
            {'duration': 0.551, 'id': None, 'name': 'com.suite.two.Suite', 'stderr': '',
             'stdout': '', 'timestamp': '2018-01-23T23:05:17', 'passCount': 0, 'skipCount': 0,
             'failCount': 0, 'unknownCount': 1, 'totalCount': 1, 'type': 'suite'},
            {'_class': 'hudson.tasks.junit.TestResult', 'testActions': [], 'duration': 4550245900,
             'empty': False, 'failCount': 2, 'passCount': 1, 'skipCount': 1, 'type': 'total',
             'totalCount': 4}]

        for idx, event in enumerate(events):
            nose.tools.ok_(event == results[idx],
                           "Bad event[{}] returned: {}".format(idx, events))
