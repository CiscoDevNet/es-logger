# Copyright (c) 2018 Cisco Systems, Inc.
# All rights reserved.

__author__ = 'jonpsull'

import es_logger
import io
from jenkins import JenkinsException, NotFoundException
import nose
import os
from parameterized import parameterized
import pkg_resources
from six.moves.urllib.error import HTTPError
from stevedore import ExtensionManager
import unittest.mock


class TestEsLogger(object):

    def setup(self):
        self.esl = es_logger.EsLogger(1000)
        self.urls = {
            'get_build_env_vars': 'jenkins_url/job/job_name/1/injectedEnvVars/api/json?depth=0',
            'get_build_test_report': 'jenkins_url/job/job_name/1/testReport/api/json?depth=0'}

    @parameterized.expand(['get_build_env_vars', 'get_build_test_report'])
    def test_monkey_patch(self, param):
        with unittest.mock.patch('es_logger.Request') as mock_request, \
                unittest.mock.patch('jenkins.urlopen') as mock_urlopen:
            mock_urlopen().read().decode.return_value = '{}'
            self.esl.server.crumb = False
            func = getattr(self.esl.server, param)
            func('job_name', 1)
            print("Comparison calls: {}".format(mock_request.mock_calls))
            mock_request.assert_any_call(self.urls[param])

    @parameterized.expand(['get_build_env_vars', 'get_build_test_report'])
    def test_monkey_patch_missing(self, param):
        with unittest.mock.patch('es_logger.Request'), \
                unittest.mock.patch('jenkins.urlopen') as mock_urlopen:
            mock_urlopen().read().decode.return_value = None
            self.esl.server.crumb = False
            func = getattr(self.esl.server, param)
            nose.tools.assert_raises(JenkinsException,
                                     func, 'job_name', 1)

    @parameterized.expand(['get_build_env_vars', 'get_build_test_report'])
    def test_monkey_patch_http(self, param):
        with unittest.mock.patch('es_logger.Request'), \
                unittest.mock.patch('jenkins.Request'), \
                unittest.mock.patch('jenkins.urlopen') as mock_urlopen:
            mock_urlopen().read.side_effect = HTTPError('url', 'code', 'msg', 'hdrs', 'fp')
            self.esl.server.crumb = False
            func = getattr(self.esl.server, param)
            nose.tools.assert_raises(JenkinsException,
                                     func, 'job_name', 1)

    @parameterized.expand(['get_build_env_vars', 'get_build_test_report'])
    def test_monkey_patch_value(self, param):
        with unittest.mock.patch('es_logger.Request'), \
                unittest.mock.patch('jenkins.Request'), \
                unittest.mock.patch('jenkins.urlopen') as mock_urlopen:
            mock_urlopen().read.side_effect = ValueError()
            self.esl.server.crumb = False
            func = getattr(self.esl.server, param)
            nose.tools.assert_raises(JenkinsException,
                                     func, 'job_name', 1)

    @parameterized.expand(['get_build_env_vars', 'get_build_test_report'])
    def test_monkey_patch_not_found(self, param):
        with unittest.mock.patch('es_logger.Request'), \
                unittest.mock.patch('jenkins.Request'), \
                unittest.mock.patch('jenkins.urlopen') as mock_urlopen:
            mock_urlopen().read.side_effect = NotFoundException()
            self.esl.server.crumb = False
            func = getattr(self.esl.server, param)
            ret = 'Return not set'
            ret = func('job_name', 1)
            nose.tools.ok_(ret is None,
                           "Return not None: {}".format(ret))

    @parameterized.expand(['jenkins_url', 'jenkins_user', 'jenkins_password', 'es_job_name',
                           'logstash_server', 'ls_user', 'ls_password'])
    def test_get(self, param):
        nose.tools.ok_(getattr(self.esl, param) is None,
                       "{} not None: {}".format(param, getattr(self.esl, param)))
        getter = getattr(self.esl, 'get_' + param)
        os.environ[param.upper()] = param
        setattr(self.esl, param, getter())
        nose.tools.ok_(getter() == param,
                       "{} returned {} not {}".format(getter.__name__, getter(), param))

    def test_get_es_build_number(self):
        nose.tools.ok_(self.esl.es_build_number == 0,
                       "self.esl.es_build_number not 0: {}".format(self.esl.es_build_number))
        os.environ['ES_BUILD_NUMBER'] = '1000'
        self.esl.es_build_number = self.esl.get_es_build_number()
        nose.tools.ok_(self.esl.get_es_build_number() == 1000,
                       "{} not returning {}".format(self.esl.get_es_build_number, 1000))

    @parameterized.expand(['process_console_logs', 'gather_build_data', 'generate_events'])
    def test_get_plugin(self, param):
        if param == 'generate_events':
            base = ['commit']
        else:
            base = []
        nose.tools.ok_(getattr(self.esl, param) == base,
                       "{} not []: {}".format(param, getattr(self.esl, param)))
        setattr(self.esl, param, None)
        getter = getattr(self.esl, 'get_' + param)
        os.environ[param.upper()] = "{}1 {}2 {}3".format(param, param, param)
        plugins = getter()
        expected = [param + '1', param + '2', param + '3'] + base
        nose.tools.ok_(plugins == expected,
                       "{} returned {} not {}".format(getter.__name__, getter(), expected))

    def test_list_plugins(self):
        dep = pkg_resources.EntryPoint.parse(
            'dummy = test.test_plugins:DummyConsoleLogProcessor')
        d = pkg_resources.Distribution()
        d._ep_map = {'es_logger.plugins.console_log_processor': {'dummy': dep}}
        pkg_resources.working_set.add(d, 'dummy')
        ExtensionManager.ENTRY_POINT_CACHE = {}
        self.esl.list_plugins()

    def test_get_build_data(self):
        self.esl.gather_build_data = ['dummy']
        self.esl.es_build_number = '2'
        with unittest.mock.patch('stevedore.driver.DriverManager') as mock_driver_mgr, \
                unittest.mock.patch('jenkins.Jenkins.get_build_info') as mock_build_info, \
                unittest.mock.patch('jenkins.Jenkins.get_build_env_vars') as mock_env_vars, \
                unittest.mock.patch('jenkins.Jenkins.get_build_console_output') as mock_console:
                    mock_env_vars.return_value = {'envMap': {'BUILD_NUMBER': '1',
                                                             'JOB_NAME': 'job_name',
                                                             'BUILD_URL': 'url',
                                                             'dummy': 'dummy'}}
                    mock_build_info.return_value = {
                        'description': 'description',
                        'number': '1',
                        'url': 'url',
                        'actions': [{'_class': 'hudson.model.ParametersAction',
                                     'parameters': [{'name': 'param', 'value': 'value'}]},
                                    {'_class': 'hudson.plugins.git.util.BuildData',
                                     'buildsByBranchName': {'b1': {'buildNumber': '1'},
                                                            'b2': {'buildNumber': '2'}},
                                     'remoteUrls': ["repoURL"]}]}
                    mock_console.return_value = 'log'
                    self.esl.get_build_data()
                    mock_driver_mgr.assert_called_once()
                    # Console log recorded
                    nose.tools.ok_(self.esl.es_info['console_log'] == 'log',
                                   "console_log not 'log': {}".format(self.esl.es_info))
                    # Parameters pulled out
                    nose.tools.ok_(self.esl.es_info['parameters'].get('param') == 'value',
                                   "Parameter 'param' not 'value': {}".format(self.esl.es_info))
                    # Prevent ES field explosion through rewrite of builds by branch name
                    nose.tools.ok_(
                        self.esl.es_info['build_info']['actions'][1]['buildsByBranchName'] ==
                        'Removed by es-logger',
                        "buildsByBranchName not removed by es-logger: {}".format(self.esl.es_info))
                    # Make sure the gather of the gather_build_data plugins was called
                    nose.tools.ok_('dummy' in self.esl.es_info['build_data'].keys(),
                                   "dummy not in build_data keys: {}".format(
                                       self.esl.es_info))
                    # SCM correctly processed
                    nose.tools.ok_('repoURL' in self.esl.es_info['build_data'].keys(),
                                   "repoURL not in build_data keys: {}".format(
                                       self.esl.es_info['build_data']))

    def test_process_build_info_actions_no_key_error(self):
        self.esl.es_info = {'build_info': {'actions': [
            {'_class': 'hudson.model.ParametersAction', 'parameters': [{'name': 'param'}]}]}}
        self.esl.process_build_info()

    # This is tested through get of the build data above
    def test_process_build_info(self):
        pass

    def test_process_console_log(self):
        self.esl.process_console_logs = ['dummy']
        with unittest.mock.patch('stevedore.driver.DriverManager') as mock_driver_mgr:
            with unittest.mock.patch('jenkins.Jenkins.get_build_console_output') as mock_get:
                mock_get.return_value = 'log'
                self.esl.process_console_log()
                mock_driver_mgr.assert_called_once()
                self.esl.console_length = 1
                mock_get.return_value = 'log'
                self.esl.process_console_log()
                nose.tools.ok_(len(self.esl.es_info['console_log']) == 1,
                               "Console log length not 1: {}".format(
                                    self.esl.es_info['console_log']))

    # Tested in get_events
    def test_get_event_info(self):
        pass

    def test_get_events(self):
        self.esl.generate_events = ['dummy']
        self.esl.es_info['env_vars'] = {'envMap': {'BUILD_NUMBER': '1',
                                                   'JOB_NAME': 'job_name',
                                                   'BUILD_URL': 'url',
                                                   'dummy': 'dummy'}}
        self.esl.es_info['build_info'] = {'description': 'description',
                                          'number': '1',
                                          'url': 'url'}
        self.esl.es_info['parameters'] = {'parameter': 'parameter'}
        self.esl.es_info[self.esl.data_name]['job_name'] = 'job_name'
        self.esl.es_info[self.esl.data_name]['jenkins_url'] = 'url'
        with unittest.mock.patch('stevedore.driver.DriverManager') as mock_driver_mgr:
            mock_driver_mgr().driver.get_fields.return_value = 'dummy'
            mock_driver_mgr().driver.generate_events.return_value = [{'DummyEventGenerator': 1},
                                                                     {'DummyEventGenerator': 2}]
            self.esl.get_events()
            nose.tools.ok_(mock_driver_mgr.call_count == 3,
                           "Incorrect call count: {}".format(mock_driver_mgr.call_count))
            nose.tools.ok_(len(self.esl.events) == 2,
                           "Incorrect number of events: {}".format(self.esl.events))
            nose.tools.ok_('timestamp' in self.esl.events[0]['build_info'].keys(),
                           "No timestamp in event: {}".format(
                                self.esl.events[0]['build_info'].keys()))

    def test_get_test_report(self):
        with unittest.mock.patch('jenkins.Jenkins.get_build_test_report') as mock_get:
            self.esl.get_test_report()
            mock_get.assert_called_once()
        nose.tools.ok_(self.esl.es_info['test_report'] is not None,
                       "Test report is None: {}".format(self.esl.es_info['test_report']))

    @unittest.mock.patch('requests.Session')
    def test_get_session(self, session):
        self.esl.get_session()
        print(session.mock_calls)
        nose.tools.ok_(self.esl.ls_session is not None,
                       "Session is None: {}".format(self.esl.ls_session))

    @unittest.mock.patch('requests.Session')
    def test_post_good(self, session):
        session().post().ok = True
        res = self.esl.post({"event": "event"})
        nose.tools.ok_(res == 0,
                       "res not 0: {}".format(res))

    @unittest.mock.patch('requests.Session')
    def test_post_bad(self, session):
        session().post().ok = False
        res = self.esl.post({"event": "event"})
        nose.tools.ok_(res == 1,
                       "res not 1: {}".format(res))

    def test_dump(self):
        with unittest.mock.patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            self.esl.dump({"event": "event"})
        print(mock_stdout.getvalue())
        nose.tools.ok_(mock_stdout.getvalue() == '{\n  "event": "event"\n}\n',
                       "Incorrect output:\n{}".format(mock_stdout.getvalue()))
