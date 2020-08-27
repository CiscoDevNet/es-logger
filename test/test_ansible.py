# Copyright (c) 2018 Cisco Systems, Inc.
# All rights reserved.

__author__ = 'jonpsull'

import es_logger
from .event_generator_base import TestEventGenerator
import nose
import unittest.mock


class TestAnsibleRecapEvent(object):
    @nose.tools.raises(ValueError)
    def test_ansible_bad_hosts(self):
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

host1 : ok=13  bad changed=3   unreachable=1    failed=0

Sunday 15 April 2018  11:40:35 +0000 (0:00:03.299)       1:29:59.000 **********
===============================================================================
plays-in-role-1 : The first task performed ---------------------------- 161.34s
'''
        eg.generate_events(esl)

    def test_ansible_strip_ansi_colour(self):
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
host1 : \x1b[0;32mok=13  \x1b[0m \x1b[0;33mchanged=3   \x1b[0m unreachable=1    failed=0

Sunday 15 April 2018  11:40:35 +0000 (0:00:03.299)       1:29:59.000 **********
===============================================================================
plays-in-role-1 : The first task performed ---------------------------- 161.34s
'''
        events = eg.generate_events(esl)
        nose.tools.ok_(len(events) == 2,
                       "Wrong number of events returned ({}): {}".format(len(events), events))
        results = [
            {'play': 'Play 1', 'host': 'host1', 'ok': 13, 'changed': 3, 'unreachable': 1,
             'failed': 0},
            {'play': 'Play 1', 'total': 5399.0, 'time_percentage': 2.9883311724393407,
             'description': 'plays-in-role-1 : The first task performed', 'time': 161.34}]

        for idx, event in enumerate(events):
            nose.tools.ok_(event == results[idx],
                           "Bad event[{}] returned: {}".format(idx, events))

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


class TestAnsibleFatalGenerator(TestEventGenerator):
    def test_AnsibleFatalGenerator(self):
        p = es_logger.plugins.ansible.AnsibleFatalGenerator()
        self.expected_fields_check(p.get_fields(), [])
        self.esl.console_log = '''
TASK [ansible-task : Task Description] *****************************************
Thursday 01 March 2018  13:24:49 +0000 (0:00:05.686)       0:00:05.901 ********
fatal: [ansible_hostname]: FAILED! => {"failed": true, "msg": "Error message\n"}
        to retry, use: --limit @/ansible_root/ansible/playbook.retry

TASK [ansible-task : Task Description] *****************************************
Thursday 01 March 2018  13:24:49 +0000 (0:00:05.686)       0:00:05.901 ********
fatal: [ansible_hostname]: UNREACHABLE! => {"changed": false, "msg": "Error", "unreachable": true}
        to retry, use: --limit @/ansible_root/ansible/playbook.retry

PLAY RECAP *********************************************************************
'''
        ret = p.generate_events(self.esl)
        self.return_length_check(ret, 2)
        nose.tools.ok_(ret[0]['hostname'] == 'ansible_hostname',
                       "Hostname is not 'ansible_hostname' {}".format(ret))
        nose.tools.ok_('failed' in ret[0]['data'].keys(),
                       "Data doesn't have 'failed' key {}".format(ret))
        nose.tools.ok_('msg' in ret[0]['data'].keys(),
                       "Data doesn't have 'msg' key {}".format(ret))

    def test_AnsibleFatalGenerator_bad_json(self):
        p = es_logger.plugins.ansible.AnsibleFatalGenerator()
        self.expected_fields_check(p.get_fields(), [])
        self.esl.console_log = '''
TASK [ansible-task : Task Description] *****************************************
Thursday 01 March 2018  13:24:49 +0000 (0:00:05.686)       0:00:05.901 ********
fatal: [ansible_hostname]: FAILED! => {"failed": true, "msg": "Error message\n"}}
        to retry, use: --limit @/ansible_root/ansible/playbook.retry

TASK [ansible-task : Task Description] *****************************************
Thursday 01 March 2018  13:24:49 +0000 (0:00:05.686)       0:00:05.901 ********
fatal: [ansible_hostname]: UNREACHABLE! => {"changed": false, "msg": "Error", "unreachable": true}}
        to retry, use: --limit @/ansible_root/ansible/playbook.retry

PLAY RECAP *********************************************************************
'''
        ret = p.generate_events(self.esl)
        self.return_length_check(ret, 2)
        nose.tools.ok_(ret[0]['hostname'] == 'ansible_hostname',
                       "Hostname is not 'ansible_hostname' {}".format(ret))
        nose.tools.ok_(ret[1]['hostname'] == 'ansible_hostname',
                       "Hostname is not 'ansible_hostname' {}".format(ret))
        nose.tools.ok_('bad_data' in ret[0].keys(),
                       "No 'bad_data' key: {}".format(ret))
