#!/usr/bin/env python

# Copyright (c) 2018 Cisco Systems, Inc.
# All rights reserved.

__author__ = 'jonpsull'

import jenkins
import json
import logging
import os
import requests
from stevedore import driver, ExtensionManager


# Monkey patch the jenkins import
def _response_handler(self, response):  # pragma: no cover
    '''Handle response objects'''
    # raise exceptions if occurred
    response.raise_for_status()
    headers = response.headers
    if (headers.get('content-length') is None and
            headers.get('transfer-encoding') is None and
            len(response.content) <= 0):
        # response body should only exist if one of these is provided
        raise jenkins.EmptyResponseException(
            "Error communicating with server[%s]: "
            "empty response" % self.server)
    # Response objects will automatically return unicode encoded
    # when accessing .text property
    return response


jenkins.Jenkins._response_handler = _response_handler


BUILD_ENV_VARS = '%(folder_url)sjob/%(short_name)s/%(number)d/injectedEnvVars/api/json' + \
    '?depth=%(depth)s'


def get_build_env_vars(self, name, number, depth=0):
    '''Get build environment variables.

    :param name: Job name, ``str``
    :param name: Build number, ``int``
    :param depth: JSON depth, ``int``
    :returns: dictionary of build env vars, ``dict``
    '''
    folder_url, short_name = self._get_job_folder(name)
    try:
        response = self.jenkins_open(requests.Request(
                'GET', self._build_url(BUILD_ENV_VARS, locals())
            ))
        if response:
            return json.loads(response)
        else:
            raise jenkins.JenkinsException('job[%s] number[%d] does not exist'
                                           % (name, number))
    except requests.exceptions.HTTPError:
        raise jenkins.JenkinsException('job[%s] number[%d] does not exist'
                                       % (name, number))
    except ValueError:
        raise jenkins.JenkinsException(
            'Could not parse JSON info for job[%s] number[%d]'
            % (name, number)
        )
    except jenkins.NotFoundException as e:
        # This can happen on workflow jobs, or if InjectEnvVars plugin not installed
        print("Not retrieving env_vars: %s" % e)
        return None


jenkins.Jenkins.get_build_env_vars = get_build_env_vars


# Get Test results
BUILD_TEST_REPORT = '%(folder_url)sjob/%(short_name)s/%(number)d/testReport/api/json' + \
    '?depth=%(depth)s'


def get_build_test_report(self, name, number, depth=0):
    '''Get test results report.

    :param name: Job name, ``str``
    :param name: Build number, ``int``
    :returns: dictionary of test report results, ``dict``
    '''
    folder_url, short_name = self._get_job_folder(name)
    try:
        response = self.jenkins_open(requests.Request(
                'GET', self._build_url(BUILD_TEST_REPORT, locals())
            ))
        if response:
            return json.loads(response)
        else:
            raise jenkins.JenkinsException('job[%s] number[%d] does not exist'
                                           % (name, number))
    except requests.exceptions.HTTPError:
        raise jenkins.JenkinsException('job[%s] number[%d] does not exist'
                                       % (name, number))
    except ValueError:
        raise jenkins.JenkinsException(
            'Could not parse JSON info for job[%s] number[%d]'
            % (name, number)
        )
    except jenkins.NotFoundException as e:
        # This can happen if the test report wasn't generated for any reason
        print("Not retrieving test report: %s" % e)
        return None


jenkins.Jenkins.get_build_test_report = get_build_test_report
# End Monkey Patch

LOGGER = logging.getLogger(__name__)


class EsLogger(object):
    # Initialise the object
    def __init__(self, console_length):
        self.data_name = type(self).__name__.lower()

        self.server = None
        self.jenkins_url = None
        self.jenkins_user = None
        self.jenkins_password = None

        self.es_job_name = None
        self.es_build_number = None
        self.build_info_fields = ['description', 'number', 'url']

        self.logstash_server = None
        self.ls_user = None
        self.ls_password = None
        self.ls_session = None

        self.es_info = {}
        self.es_info['test_report'] = None
        self.es_info[self.data_name] = {}
        self.events = []

        self.process_console_logs = []
        self.gather_build_data = []
        self.generate_events = []

        self.jenkins_url = self.get_jenkins_url()
        self.jenkins_user = self.get_jenkins_user()
        self.jenkins_password = self.get_jenkins_password()
        if self.jenkins_url:
            self.server = jenkins.Jenkins(self.jenkins_url,
                                          username=self.jenkins_user,
                                          password=self.jenkins_password)
        self.es_job_name = self.get_es_job_name()
        self.es_build_number = self.get_es_build_number()
        self.logstash_server = self.get_logstash_server()
        self.ls_user = self.get_ls_user()
        self.ls_password = self.get_ls_password()
        self.process_console_logs = self.get_process_console_logs()
        self.gather_build_data = self.get_gather_build_data()
        self.generate_events = self.get_generate_events()
        self.console_length = console_length

    ####################################
    # Get variables from the environment
    ####################################
    def get_jenkins_url(self):
        if not self.jenkins_url:
            return os.environ.get('JENKINS_URL')
        return self.jenkins_url

    def get_jenkins_user(self):
        if not self.jenkins_user:
            return os.environ.get('JENKINS_USER')
        return self.jenkins_user

    def get_jenkins_password(self):
        if not self.jenkins_password:
            return os.environ.get('JENKINS_PASSWORD')
        return self.jenkins_password

    def get_es_job_name(self):
        if not self.es_job_name:
            return os.environ.get('ES_JOB_NAME')
        return self.es_job_name

    def get_es_build_number(self):
        if not self.es_build_number:
            return int(os.environ.get('ES_BUILD_NUMBER', 0))
        return self.es_build_number

    def get_logstash_server(self):
        if not self.logstash_server:
            return os.environ.get('LOGSTASH_SERVER')
        return self.logstash_server

    def get_ls_user(self):
        if not self.ls_user:
            return os.environ.get('LS_USER')
        return self.ls_user

    def get_ls_password(self):
        if not self.ls_password:
            return os.environ.get('LS_PASSWORD')
        return self.ls_password

    def get_process_console_logs(self):
        if not self.process_console_logs:
            process_console_logs = os.environ.get('PROCESS_CONSOLE_LOGS')
            if process_console_logs is None:
                self.process_console_logs = []
            else:
                self.process_console_logs = process_console_logs.split(' ')
        return self.process_console_logs

    def get_gather_build_data(self):
        if not self.gather_build_data:
            gather_build_data = os.environ.get('GATHER_BUILD_DATA')
            if gather_build_data is None:
                self.gather_build_data = []
            else:
                self.gather_build_data = gather_build_data.split(' ')
        return self.gather_build_data

    def get_generate_events(self):
        if not self.generate_events:
            generate_events = os.environ.get('GENERATE_EVENTS')
            if generate_events is None:
                self.generate_events = []
            else:
                self.generate_events = generate_events.split(' ')
            self.generate_events.append('commit')
        return self.generate_events
    ################
    # End of getters
    ################

    # List all of the plugins we know about
    def list_plugins(self):
        def print_plugin(ext):
            print("\t{}".format(ext.entry_point.name))

        for namespace in ['es_logger.plugins.gather_build_data',
                          'es_logger.plugins.console_log_processor',
                          'es_logger.plugins.event_generator']:
            mgr = ExtensionManager(namespace=namespace, invoke_on_load=False)
            print("{}:".format(namespace))
            if len(mgr.names()) > 0:
                mgr.map(print_plugin)
            else:
                print("\tNone found")

    # Get the data that we want from a build
    def get_build_data(self):
        # Add the base info we have
        self.es_info[self.data_name]['job_name'] = self.es_job_name
        self.es_info[self.data_name]['jenkins_url'] = self.jenkins_url

        # Build Info (Parameters, Status)
        self.build_info = self.server.get_build_info(self.es_job_name, self.es_build_number,
                                                     depth=0)
        self.es_info['build_info'] = self.build_info

        # Environment Variables
        self.env_vars = self.server.get_build_env_vars(self.es_job_name, self.es_build_number)
        self.es_info['env_vars'] = self.env_vars

        # Process build_info
        self.process_build_info()

        # Process the console log
        self.process_console_log()

        # Now run through any extra data gathering plugins to annotate the event
        for plugin in self.gather_build_data:
            data = driver.DriverManager(
                    namespace='es_logger.plugins.gather_build_data',
                    name=plugin,
                    invoke_on_load=True,
                    invoke_args=()
                )
            self.es_info.setdefault('build_data', {})[plugin] = data.driver.gather(self)

    # Process Build Info
    def process_build_info(self):
        for action in self.es_info['build_info']['actions']:
            # Parameters - make the data in the build_info useful
            if action.get('_class', '') in [
                    'hudson.model.ParametersAction',
                    'com.tikal.jenkins.plugins.multijob.MultiJobParametersAction']:
                for param in action['parameters']:
                    try:
                        self.es_info.setdefault(
                            'parameters', {})[param['name']] = param['value']
                    except KeyError:
                        LOGGER.debug("KeyError on {}".format(param))
                        continue
            # BuildData - parse through the data and make usable in ES
            if action.get('_class', '') in ['hudson.plugins.git.util.BuildData']:
                scm_urls = action['remoteUrls']
                for build_branch_key in action['buildsByBranchName']:
                    build_data = action['buildsByBranchName'][build_branch_key]
                    # If the build matches this number, add it to the info
                    if build_data.get('buildNumber', '') == self.es_build_number:
                        self.es_info.setdefault('build_data', {})[scm_urls[0]] = build_data
                        self.es_info['build_data'][scm_urls[0]]['scm_urls'] = scm_urls
                        self.es_info['build_data'][scm_urls[0]]['branch'] = build_branch_key
                # Clear the field that causes ES field explosion
                action['buildsByBranchName'] = "Removed by es-logger"

    # Process Console Log
    def process_console_log(self):
        self.console_log = self.server.get_build_console_output(self.es_job_name,
                                                                self.es_build_number)

        # Add plugin loading and processing with an array of plugins
        # e.g. - count errors, count warnings, parse test results, etc.
        for plugin in self.process_console_logs:
            processor = driver.DriverManager(
                    namespace='es_logger.plugins.console_log_processor',
                    name=plugin,
                    invoke_on_load=True,
                    invoke_args=()
                )
            self.es_info.setdefault('console_log_plugins', {})[plugin] = processor.driver.process(
                self.console_log)

        # Max length for an indexed field is 32766, if longer, reduce
        # Default value in args parsing is 32500,
        # as when using larger values saw failures (not sure why)
        if len(self.console_log) > self.console_length:
            self.es_info['console_log'] = self.console_log[-self.console_length:]
        else:
            self.es_info['console_log'] = self.console_log

    def get_event_info(self, fields):
        event_info = {}

        if self.es_info['env_vars'] is not None:
            # XXX: Just returning self.es_info['env_vars'] is likely better...
            for field in fields:
                event_info.setdefault(
                    'env_vars', {}).setdefault('envMap', {})[field] = \
                        self.es_info['env_vars']['envMap'].get(field)

        # Add the parameters
        if self.es_info.get('parameters') is not None:
            event_info['parameters'] = self.es_info['parameters']

        # Add generic Jenkins info
        for field in self.build_info_fields:
            event_info[field] = self.es_info['build_info'].get(field, '')

        # Add the extras added by es-logger
        event_info[self.data_name] = dict(self.es_info[self.data_name])

        return event_info

    # To enable best visualisation of data,
    # allow for plugins that create an array of events to post
    def get_events(self):
        # Run through any event generator plugins
        for plugin in self.generate_events:
            event_generator = driver.DriverManager(
                    namespace='es_logger.plugins.event_generator',
                    name=plugin,
                    invoke_on_load=True,
                    invoke_args=()
                )
            gen_events = event_generator.driver.generate_events(self)

            # Get the default event info
            event_info = self.get_event_info(event_generator.driver.get_fields())
            # Add the name of the driver into the event field
            event_info[self.data_name]['event'] = plugin

            # Add the default data to each of the events we are sending in
            add_events = []
            for event in gen_events:
                new_event = {plugin: event}
                new_event.update(event_info)
                # Add the timestamp for logging when this ran
                new_event.setdefault('build_info', {})['timestamp'] = \
                    self.es_info['build_info'].get('timestamp')
                add_events.append(new_event)
            self.events += add_events

    def get_test_report(self):
        if self.es_info['test_report'] is None:
            self.es_info['test_report'] = self.server.get_build_test_report(
                self.es_job_name, self.es_build_number)
        return self.es_info['test_report']

    def get_session(self):
        if self.ls_session is None:
            self.ls_session = requests.Session()
            self.ls_session.auth = (self.ls_user, self.ls_password)
        return self.ls_session

    # Post to ES
    def post(self, json_event):
        session = self.get_session()
        r = session.post(self.logstash_server, json=json_event)
        print(r)
        if r.ok:
            return 0
        return 1

    # Dump the string
    def dump(self, json_event):
        print(json.dumps(json_event, sort_keys=True, indent=2))
