# Copyright (c) 2018 Cisco Systems, Inc.
# All rights reserved.

__author__ = 'jonpsull'

import es_logger
import nose
import unittest.mock


class TestAnsibleRecapEvent(object):
    def test_ansible_recap_event(self):
        eg = es_logger.plugins.ansible.AnsibleRecapEvent()
        fields = eg.get_fields()
        nose.tools.ok_(fields == es_logger.interface.EventGenerator.DEFAULT_FIELDS)
        esl = unittest.mock.MagicMock()
        esl.console_log = '''
+ ansible-playbook command

PLAY [Play 1] ******************************************************************

TASK [Task 1] ******************************************************************
Sunday 15 April 2018  11:36:41 +0000 (0:00:00.096)       0:00:00.096 **********
ok: [host1 -> localhost]

PLAY RECAP *********************************************************************
host1 : ok=1   changed=2    unreachable=3    failed=4
host1 : ok=8   changed=7    unreachable=6    failed=5

Sunday 15 April 2018  11:40:35 +0000 (0:00:03.299)       1:29:59.000 **********
===============================================================================
plays-in-role-1 : The first task performed ---------------------------- 161.34s
plays-in-role-2 : The last task performed with a long name leaving only 3 dashes --- 0.03s
plays-in-role-3 : The last task performed with a long name leaving only 2 spaces  1.03s
+ ansible-playbook command
 [WARNING]: Found variable using reserved name: hosts


PLAY [Play 2] *********************

TASK [role2 : Perform task 1] *****
changed: [host2]

TASK [role2 : Perform task 2] *****
changed: [host2]

PLAY [Play 3] *********************************************
skipping: no hosts matched

PLAY RECAP *********************************************************************
host2 : ok=4   changed=3    unreachable=2    failed=1
host3 : ok=5   changed=6    unreachable=7    failed=8

TASK: role2 : task 1 --- 161.27s (not verified)
TASK: role2 : task 2 ----------------- 0.29s (not verified)

Total -------------------------------------------------- 259.72s (4 min 20 sec)

Finished: SUCCESS
'''
        events = eg.generate_events(esl)
        nose.tools.ok_(len(events) == 9,
                       "Wrong number of events returned ({}): {}".format(len(events), events))
        results = [
            {'play': 'Play 2', 'host': 'host2', 'ok': 4, 'changed': 3, 'unreachable': 2,
             'failed': 1},
            {'play': 'Play 2', 'host': 'host3', 'ok': 5, 'changed': 6, 'unreachable': 7,
             'failed': 8},
            {'play': 'Play 2', 'total': 259.72, 'time_percentage': 62.09379331587863,
             'description': 'TASK: role2 : task 1', 'time': 161.27},
            {'play': 'Play 2', 'total': 259.72, 'time_percentage': 0.11165870937933156,
             'description': 'TASK: role2 : task 2', 'time': 0.29},
            {'play': 'Play 1', 'host': 'host1', 'ok': 1, 'changed': 2, 'unreachable': 3,
             'failed': 4},
            {'play': 'Play 1', 'host': 'host1', 'ok': 8, 'changed': 7, 'unreachable': 6,
             'failed': 5},
            {'play': 'Play 1', 'total': 5399.0, 'time_percentage': 2.9883311724393407,
             'description': 'plays-in-role-1 : The first task performed', 'time': 161.34},
            {'play': 'Play 1', 'total': 5399.0, 'time_percentage': 0.0005556584552694943,
             'description':
             'plays-in-role-2 : The last task performed with a long name leaving only 3 dashes',
             'time': 0.03},
            {'play': 'Play 1', 'total': 5399.0, 'time_percentage': 0.01907760696425264,
             'description':
             'plays-in-role-3 : The last task performed with a long name leaving only 2 spaces',
             'time': 1.03}]

        for idx, event in enumerate(events):
            nose.tools.ok_(event == results[idx],
                           "Bad event[{}] returned: {}".format(idx, events))
