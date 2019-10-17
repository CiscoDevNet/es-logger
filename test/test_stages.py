# Copyright (c) 2018 Cisco Systems, Inc.
# All rights reserved.

__author__ = 'mvillene'

import es_logger
import nose
import unittest.mock


class TestStageEvent(object):
    def test_stage_fields(self):
        eg = es_logger.plugins.stages.StageEvent()
        fields = eg.get_fields()
        nose.tools.ok_(fields == es_logger.interface.EventGenerator.DEFAULT_FIELDS)

    def test_no_stages(self):
        eg = es_logger.plugins.stages.StageEvent()
        esl = unittest.mock.MagicMock()
        esl.get_stages.return_value = None
        events = eg.generate_events(esl)
        nose.tools.ok_(len(events) == 0)

    def test_with_stage_report(self):
        eg = es_logger.plugins.stages.StageEvent()
        esl = unittest.mock.MagicMock()
        esl.get_stages.return_value = {
            "_links": {"self": {"href": "/job/test/job/HelloWorld/78/wfapi/describe"}},
            "id": "78", "name": "#78", "status": "SUCCESS", "startTimeMillis": 1549926641427,
            "endTimeMillis": 1549926650050, "durationMillis": 8623, "queueDurationMillis": 1,
            "pauseDurationMillis": 0,
            "stages": [
                {"_links": {"self": {
                    "href": "/job/test/job/HelloWorld/78/execution/node/6/wfapi/describe"}},
                 "id": "6", "name": "Stage 1", "execNode": "", "status": "SUCCESS",
                 "startTimeMillis": 1549926642588, "durationMillis": 18, "pauseDurationMillis": 0},
                {"_links": {"self": {
                    "href": "/job/test/job/HelloWorld/78/execution/node/11/wfapi/describe"}},
                 "id": "11", "name": "Stage 2", "execNode": "", "status": "SUCCESS",
                 "startTimeMillis": 1549926642613, "durationMillis": 17, "pauseDurationMillis": 0},
                {"_links": {"self": {
                    "href": "/job/test/job/HelloWorld/78/execution/node/16/wfapi/describe"}},
                 "id": "16", "name": "Declarative: Post Actions", "execNode": "",
                 "status": "SUCCESS", "startTimeMillis": 1549926642637, "durationMillis": 7398,
                 "pauseDurationMillis": 0}
            ]
        }
        events = eg.generate_events(esl)
        nose.tools.ok_(len(events) == 3,
                       "Wrong number of events returned ({}): {}".format(len(events), events))
        results = [
            {"status": "SUCCESS", "id": "6", "pauseDurationMillis": 0, "durationMillis": 18,
             "_links": {"self": {
                "href": "/job/test/job/HelloWorld/78/execution/node/6/wfapi/describe"}},
             "startTimeMillis": 1549926642588, "execNode": "", "name": "Stage 1"},
            {"status": "SUCCESS", "id": "11", "pauseDurationMillis": 0, "durationMillis": 17,
             "_links": {"self": {
                "href": "/job/test/job/HelloWorld/78/execution/node/11/wfapi/describe"}},
             "startTimeMillis": 1549926642613, "execNode": "", "name": "Stage 2"},
            {"status": "SUCCESS", "id": "16", "pauseDurationMillis": 0, "durationMillis": 7398,
             "_links": {"self": {
                "href": "/job/test/job/HelloWorld/78/execution/node/16/wfapi/describe"}},
             "startTimeMillis": 1549926642637, "execNode": "", "name": "Declarative: Post Actions"}
        ]

        for idx, event in enumerate(events):
            nose.tools.ok_(event == results[idx], "Bad event[{}] returned: {}".format(idx, events))
