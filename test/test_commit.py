# Copyright (c) 2018 Cisco Systems, Inc.
# All rights reserved.

__author__ = 'jonpsull'

import es_logger
import nose
import unittest.mock


class TestCommitEvent(object):
    def test_commit_event(self):
        eg = es_logger.plugins.commit.CommitEvent()
        fields = eg.get_fields()
        nose.tools.ok_(fields == es_logger.interface.EventGenerator.DEFAULT_FIELDS)
        esl = unittest.mock.MagicMock()
        esl.build_info = {
                "changeSet": {
                    "_class": "hudson.plugins.git.GitChangeSetList",
                    "items": [{"date": "2018-03-07 09:22:36 +0000"}],
                    "kind": "git"},
                "changeSets": [{
                    "items": [{"date": "2018-03-14T12:09:16+0000"}],
                    "kind": "git"}]}
        events = eg.generate_events(esl)
        nose.tools.ok_(len(events) == 2,
                       "Wrong number of events returned: {}".format(events))
        nose.tools.ok_(events[0]['changeSet']['date'] == "2018-03-14T12:09:16+0000",
                       "Bad event[0] returned: {}".format(events))
        nose.tools.ok_(events[1]['changeSet']['date'] == "2018-03-07T09:22:36+0000",
                       "Bad event[1] returned: {}".format(events))
