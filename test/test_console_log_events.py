__author__ = 'jonpsull'

import es_logger
import es_logger.plugins.console_log_events
from .event_generator_base import TestEventGenerator
import nose.tools
import unittest.mock


class TestConsoleLog(TestEventGenerator):
    def setup(self):
        self.esl = unittest.mock.MagicMock(
            spec=es_logger.EsLogger, console_log='Log', build_info={}, es_info={},
            data_name='eslogger')

    def test_read_regex_file(self):
        with unittest.mock.patch('os.path.isfile') as mock_isfile, \
                unittest.mock.patch('builtins.open') as mock_file, \
                unittest.mock.patch(
                    'es_logger.plugins.console_log_events.json.loads') as mock_json_loads:
            mock_isfile.return_value = True
            mock_json_loads.return_value = [{"name": "one", "pattern": "one (?P<one>.*)$"},
                                            {"name": "two", "pattern": "two(?P<two>.*)$"}]
            p = es_logger.plugins.console_log_events.ConsoleLogEvent()
            self.esl.console_log = ''
            self.esl.console_log += '''
one match
two matches
'''
            ret = p.generate_events(self.esl)
            self.return_length_check(ret, 2)
            mock_file_calls = [unittest.mock.call('console_log_event_regex.json', 'r'),
                               unittest.mock.call().__enter__(),
                               unittest.mock.call().__exit__(None, None, None)]
            nose.tools.ok_(mock_file.mock_calls == mock_file_calls,
                           "Wrong file calls:\n{}".format(mock_file.mock_calls))

        one = [x for x in ret if x['name'] == 'one']
        self.return_length_check(one, 1)
        self.check_named_match(one[0], 'one', 'match')

        two = [x for x in ret if x['name'] == 'two']
        self.return_length_check(two, 1)
        self.check_named_match(two[0], 'two', ' matches')

    def test_ConsoleLogEvent(self):
        p = es_logger.plugins.console_log_events.ConsoleLogEvent()
        self.expected_fields_check(p.get_fields(), ['NODE_NAME', 'NODE_LABELS'])
        self.esl.console_log = ''

        self.esl.console_log += '''
Running on jenkins-agent-1 in /mnt/jenkins/workspace/job-name-random
'''
        self.esl.console_log += '\n'
        self.esl.console_log += '''
Error response from daemon: The error message
next line

preceeding line
same line unknown blob trailing
'''
        self.esl.console_log += '\n'
        self.esl.console_log += 'Error response from daemon: The error message net/http: request'
        self.esl.console_log += ' canceled (Client.Timeout exceeded while awaiting headers)'
        self.esl.console_log += '''
Error response from daemon: missing signature key

Pulling repository docker_repository
Error: image docker_image not found

Error: image docker_image not found
'''
        self.esl.console_log += '\n'
        self.esl.console_log += 'Error pulling image (docker_image:tag) from docker_repository,'
        self.esl.console_log += ' endpoint: docker_endpoint, The error message'
        self.esl.console_log += '''
Please login prior to pull:
Error: Cannot perform an interactive login from a non TTY device

received unexpected HTTP status: http_status
'''
        self.esl.console_log += '\n'
        self.esl.console_log += 'devmapper: Thin Pool has 100000 free data blocks which is less'
        self.esl.console_log += ' than minimum required 100000 free data blocks. Create more free'
        self.esl.console_log += ' space in thin pool or use dm.min_free_space option to change'
        self.esl.console_log += ' behavior'
        self.esl.console_log += '''
Total reclaimed space 4MB

/dev/stdout: resource temporarily unavailable

java.class.AnException: This is the exception

ERROR: Error message
next line

FATAL: Fatal message
next line

remote file operation failed: remote failed text
next line
'''

        self.esl.console_log += '''
[DEPRECATION WARNING]: Multi
line
deprecation
[WARNING]: One line warning
[WARNING]: Multi
line
warning

'''
        ret = p.generate_events(self.esl)
        self.return_length_check(ret, 23)

        jenkins_agent = [x for x in ret if x['name'] == 'jenkins agent']
        self.return_length_check(jenkins_agent, 1)
        self.check_named_match(jenkins_agent[0], 'jenkins_agent', 'jenkins-agent-1')
        self.check_named_match(jenkins_agent[0], 'workspace',
                               '/mnt/jenkins/workspace/job-name-random')

        docker_error = [x for x in ret if x['name'] == 'docker error']
        self.return_length_check(docker_error, 3)
        self.check_named_match(docker_error[0], 'docker_error', ' The error message')

        blob_error = [x for x in ret if x['name'] == 'docker blob error']
        self.return_length_check(blob_error, 1)
        self.check_named_match(blob_error[0], 'preceding', 'preceeding line')
        self.check_named_match(blob_error[0], 'blob', 'same line unknown blob trailing')

        docker_timeout = [x for x in ret if x['name'] == 'docker timeout']
        self.return_length_check(docker_timeout, 1)
        self.check_named_match(docker_timeout[0], 'err', ' The error message ')

        missing_sig = [x for x in ret if x['name'] == 'docker missing signature']
        self.return_length_check(missing_sig, 1)

        image_not_found = [x for x in ret if x['name'] == 'docker image not found']
        self.return_length_check(image_not_found, 3)
        self.check_named_match(image_not_found[0], 'docker_repository', 'docker_repository')
        self.check_named_match(image_not_found[0], 'docker_image', 'docker_image')
        self.check_named_match(image_not_found[1], 'image', 'docker_image')
        self.check_named_match(image_not_found[2], 'image', 'docker_image')

        pull_error = [x for x in ret if x['name'] == 'docker pull error']
        self.return_length_check(pull_error, 2)
        self.check_named_match(pull_error[0], 'docker_tag', 'docker_image:tag')
        self.check_named_match(pull_error[0], 'docker_registry', 'docker_repository')
        self.check_named_match(pull_error[0], 'docker_endpoint', 'docker_endpoint')
        self.check_named_match(pull_error[0], 'error', 'The error message')

        http_status = [x for x in ret if x['name'] == 'http_status']
        self.return_length_check(http_status, 1)
        self.check_named_match(http_status[0], 'http_status', ' http_status')

        thin_pool_full = [x for x in ret if x['name'] == 'thin pool full']
        self.return_length_check(thin_pool_full, 1)

        reclaimed_space = [x for x in ret if x['name'] == 'reclaimed space']
        self.return_length_check(reclaimed_space, 1)

        stdout_unavail = [x for x in ret if x['name'] == 'stdout temporarily unavailable']
        self.return_length_check(stdout_unavail, 1)

        java_exception = [x for x in ret if x['name'] == 'java exception']
        self.return_length_check(java_exception, 1)
        self.check_named_match(java_exception[0], 'exception', 'java.class.AnException')
        self.check_named_match(java_exception[0], 'exception_text', 'This is the exception')

        jenkins_error = [x for x in ret if x['name'] == 'jenkins error']
        self.return_length_check(jenkins_error, 1)
        self.check_named_match(jenkins_error[0], 'error_text', 'Error message')

        jenkins_fatal = [x for x in ret if x['name'] == 'jenkins fatal error']
        self.return_length_check(jenkins_fatal, 1)
        self.check_named_match(jenkins_fatal[0], 'fatal_text', 'Fatal message')

        jenkins_remote_failed = [x for x in ret if x['name'] == 'remote file operation failed']
        self.return_length_check(jenkins_remote_failed, 1)
        self.check_named_match(jenkins_remote_failed[0], 'remote_fail_text', 'remote failed text')

        ansible_warning = [x for x in ret if x['name'] == 'ansible warning']
        self.return_length_check(ansible_warning, 2)
        self.check_named_match(ansible_warning[0], 'warning_text', 'One line warning\n')
        self.check_named_match(ansible_warning[1], 'warning_text', 'Multi\nline\nwarning\n')

        ansible_deprecation = [x for x in ret if x['name'] == 'ansible deprecation']
        self.return_length_check(ansible_deprecation, 1)
        self.check_named_match(ansible_deprecation[0], 'deprecation_text',
                               'Multi\nline\ndeprecation\n')
