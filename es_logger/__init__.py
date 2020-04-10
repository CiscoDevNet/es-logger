#!/usr/bin/env python

# Copyright (c) 2018 Cisco Systems, Inc.
# All rights reserved.

__author__ = 'jonpsull'

import jenkins
import json
import logging
import os
import re
import requests
from stevedore import driver, ExtensionManager
import xml.etree.ElementTree as ET


# Monkey patch the jenkins import
# Get Artifact
BUILD_ARTIFACT = '%(folder_url)sjob/%(short_name)s/%(number)d/artifact/%(artifact)s'


def get_build_artifact(self, name, number, artifact):
    """Get artifacts from job

    :param name: Job name, ``str``
    :param number: Build number, ``int``
    :param artifact: Artifact relative path, ``str``
    :returns: artifact to download, ``dict``
    """
    folder_url, short_name = self._get_job_folder(name)

    try:
        response = self.jenkins_open(requests.Request(
                'GET', self._build_url(BUILD_ARTIFACT, locals())))

        if response:
            return json.loads(response)
        else:
            raise jenkins.JenkinsException('job[%s] number[%d] does not exist' % (name, number))
    except requests.exceptions.HTTPError:
        raise jenkins.JenkinsException('job[%s] number[%d] does not exist' % (name, number))
    except ValueError:
        raise jenkins.JenkinsException(
                'Could not parse JSON info for job[%s] number[%d]' % (name, number))
    except jenkins.NotFoundException as e:
        # This can happen if the artifact is not found
        print("Not retrieving artifact: %s" % e)
        return None


jenkins.Jenkins.get_build_artifact = get_build_artifact


# Get Stages
BUILD_STAGES = '%(folder_url)sjob/%(short_name)s/%(number)d/wfapi/describe/'


def get_build_stages(self, name, number):
    """Get stages info from job

    :param name: Job name, ``str``
    :param number: Build number, ``int``
    :returns: dictionary of stages in the job, ``dict``
    """
    folder_url, short_name = self._get_job_folder(name)

    try:
        response = self.jenkins_open(requests.Request(
                'GET', self._build_url(BUILD_STAGES, locals())))

        if response:
            return json.loads(response)
        else:
            raise jenkins.JenkinsException('job[%s] number[%d] does not exist' % (name, number))
    except requests.exceptions.HTTPError:
        raise jenkins.JenkinsException('job[%s] number[%d] does not exist' % (name, number))
    except ValueError:
        raise jenkins.JenkinsException(
                'Could not parse JSON info for job[%s] number[%d]' % (name, number))
    except jenkins.NotFoundException as e:
        # This can happen if this isn't a stages/pipeline job
        print("Not retrieving stages: %s" % e)
        return None


jenkins.Jenkins.get_build_stages = get_build_stages
# End Monkey Patch

LOGGER = logging.getLogger(__name__)


class JenkinsCollectError(Exception):
    pass


class EsLogger(object):
    # Initialise the object
    def __init__(self, console_length, targets):
        self.data_name = type(self).__name__.lower()

        self.server = None
        self.jenkins_url = None
        self.jenkins_user = None
        self.jenkins_password = None

        self.es_job_name = None
        self.es_build_number = None
        self.build_info_fields = ['description', 'number', 'result', 'url']

        self.es_info = {}
        self.es_info['test_report'] = None
        self.es_info['stages'] = None
        self.es_info[self.data_name] = {}
        self.events = []

        self.job_xml_raw = None
        self.job_xml = None

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
        self.process_console_logs = self.get_process_console_logs()
        self.gather_build_data = self.get_gather_build_data()
        self.generate_events = self.get_generate_events()
        self.console_length = console_length

        self.targets = []
        for target in targets:
            self.targets.append(driver.DriverManager(namespace='es_logger.plugins.event_target',
                                                     invoke_on_load=True, name=target))
        LOGGER.info('Using targets: {}'.format(targets))

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

    def get_process_console_logs(self):
        if not self.process_console_logs:
            process_console_logs = os.environ.get('PROCESS_CONSOLE_LOGS')
            if process_console_logs in [None, '']:
                self.process_console_logs = []
            else:
                self.process_console_logs = process_console_logs.split(' ')
        return self.process_console_logs

    def get_gather_build_data(self):
        if not self.gather_build_data:
            gather_build_data = os.environ.get('GATHER_BUILD_DATA')
            if gather_build_data in [None, '']:
                self.gather_build_data = []
            else:
                self.gather_build_data = gather_build_data.split(' ')
        return self.gather_build_data

    def get_generate_events(self):
        if not self.generate_events:
            generate_events = os.environ.get('GENERATE_EVENTS')
            if generate_events in [None, '']:
                self.generate_events = []
            else:
                self.generate_events = generate_events.split(' ')
            self.generate_events.append('commit')
        return self.generate_events
    ################
    # End of getters
    ################

    # List all of the plugins we know about
    @staticmethod
    def list_plugins(data_only=False,
                     namespaces=['gather_build_data', 'console_log_processor', 'event_generator',
                                 'event_generator.console_log_events', 'event_target']):
        def print_plugin(ext):
            print("\t{}".format(ext.entry_point.name))

        plugins = {}
        for namespace in namespaces:
            plugins[namespace] = ExtensionManager(namespace='es_logger.plugins.' + namespace,
                                                  invoke_on_load=False)
        if data_only:
            ret_list = []
            for namespace in namespaces:
                ret_list += plugins[namespace].names()
            return ret_list

        for namespace in namespaces:
            print("{}:".format('es_logger.plugins.' + namespace))
            if len(plugins[namespace].names()) > 0:
                plugins[namespace].map(print_plugin)
            else:
                print("\tNone found")

    # Return the help for all of the event_target plugins loaded
    @staticmethod
    def get_event_target_plugin_help():
        ret = ''
        mgr = ExtensionManager(namespace='es_logger.plugins.event_target', invoke_on_load=False)
        for target_plugin in mgr.names():  # All known target plugins
            drv = driver.DriverManager(namespace='es_logger.plugins.event_target',
                                       invoke_on_load=False,
                                       name=target_plugin)
            ret = ret + '\n{}'.format(drv.driver.get_help_string())
        return ret

    # Get the data that we want from a build
    def get_build_data(self):
        # Add the base info we have
        self.es_info[self.data_name]['job_name'] = self.es_job_name
        self.es_info[self.data_name]['jenkins_url'] = self.jenkins_url
        self.es_info[self.data_name]['build_number'] = self.es_build_number

        try:
            # Build Info (Parameters, Status)
            self.build_info = self.server.get_build_info(self.es_job_name, self.es_build_number,
                                                         depth=0)
        except Exception as exc:
            raise JenkinsCollectError("get_build_info") from exc
        self.es_info['build_info'] = self.build_info

        try:
            self.job_xml_raw = self.server.get_job_config(self.es_job_name)
        except jenkins.JenkinsException as jenkins_err:
            LOGGER.error("JenkinsException when attempting to get job config: {}".format(
                    jenkins_err))
            self.es_info['job_config_info'] = None
            self.es_info['job_config_info_status'] = "Unable to retrieve config.xml."
        except Exception as exc:
            raise JenkinsCollectError("get_job_config") from exc

        if self.job_xml_raw is not None:
            self.job_xml = ET.fromstring(self.job_xml_raw)
            self.es_info['job_config_info'] = self.get_pipeline_job_info()
            self.es_info['job_config_info_status'] = "Retrieved config.xml."

        # Environment Variables
        try:
            self.env_vars = self.server.get_build_env_vars(self.es_job_name, self.es_build_number)
        except Exception as exc:
            raise JenkinsCollectError("get_build_env_vars") from exc
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

    def get_pipeline_job_type(self):
        pipeline_types = {"org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition": "Script",
                          "org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition": "SCM",
                          "org.jenkinsci.plugins.workflow.multibranch.SCMBinder": "Multibranch"}
        if self.job_xml is None:
            pipeline_type = None
        else:
            try:
                # Figure out what type of pipeline job this is.
                pipeline_type = pipeline_types[self.job_xml.find("./definition").attrib["class"]]
                LOGGER.debug("Pipeline Type is {}".format(pipeline_type))
            except (KeyError, AttributeError):
                LOGGER.error("Pipeline Type not found.")
                pipeline_type = "Unknown"
        return pipeline_type

    # Get some more info for a pipeline job.
    def get_pipeline_job_info(self):
        pipeline_data = {}
        if self.job_xml is None:
            pipeline_data = {}
        elif self.job_xml.tag != "flow-definition":
            pipeline_data = {"is_pipeline_job": False}
        else:
            # Store that this is a pipeline job and its type.
            pipeline_data["is_pipeline_job"] = True
            pipeline_data["pipeline_job_type"] = self.get_pipeline_job_type()

            # Check if its using git as the scm or not.
            git_scm_plugin = "hudson.plugins.git.GitSCM"
            if pipeline_data["pipeline_job_type"] in ["SCM", "Multibranch"]:
                # Both SCM types will use a Jenkinsfile
                pipeline_data["jenkinsfile"] = self.job_xml.find("./definition/scriptPath").text
                # Get the git source details from the definition or properties xml tag
                xml_tag = "./definition/" if pipeline_data["pipeline_job_type"] == "SCM" else \
                    "./properties/org.jenkinsci.plugins.workflow.multibranch." + \
                    "BranchJobProperty/branch/"
                # Get the git properties if git is in use
                if self.job_xml.find(xml_tag + "scm").attrib["class"] == git_scm_plugin:
                    pipeline_data["git_repo"] = self.job_xml.find(
                        xml_tag + "scm/userRemoteConfigs/" +
                        "hudson.plugins.git.UserRemoteConfig/url").text
                    pipeline_data["git_branch"] = self.job_xml.find(
                        xml_tag + "scm/branches/hudson.plugins.git.BranchSpec/name").text

        return pipeline_data

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
        try:
            self.console_log_ts = self.server.get_build_console_output(self.es_job_name,
                                                                       self.es_build_number)
        except Exception as exc:
            raise JenkinsCollectError("get_build_console_output") from exc
        # Because of timestamper 1.9+
        # https://issues.jenkins-ci.org/browse/JENKINS-48344
        # if the line starts with the timestamp, strip it
        # [2020-04-22T11:21:48.848Z] console log
        all_lines = []
        time_re = re.compile(
                r'(^\[[0-9]{4}-[0-9]{2}-[0-9]{2}' +                 # Date: '[2020-04-22'
                r'T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z\]\s)' +    # Time: 'T11:21:48.848Z] '
                r'(.*$)')                                           # Actual console log line
        for line in self.console_log_ts.splitlines():
            mo = time_re.match(line)
            if mo:
                all_lines.append(mo.group(2))
            else:
                all_lines.append(line)
        self.console_log = "\n".join(all_lines)

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
        console_log_length = len(self.console_log)
        if console_log_length > self.console_length:
            self.es_info['console_log'] = self.console_log[-self.console_length:]
        else:
            self.es_info['console_log'] = self.console_log
        # Add the length of the console log
        self.es_info['console_log_length'] = console_log_length

    def get_event_info(self, fields):
        event_info = {'build_info': {}}

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
            event_info['build_info'][field] = self.es_info['build_info'].get(field, '')
            # As we previously did this, keep doing it
            event_info[field] = event_info['build_info'][field]

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
            try:
                self.es_info['test_report'] = self.server.get_build_test_report(
                    self.es_job_name, self.es_build_number)
            except Exception as exc:
                raise JenkinsCollectError("get_build_test_report") from exc
        return self.es_info['test_report']

    def get_stages(self):
        if self.es_info['stages'] is None:
            try:
                self.es_info['stages'] = self.server.get_build_stages(
                    self.es_job_name, self.es_build_number)
            except Exception as exc:
                raise JenkinsCollectError("get_build_stages") from exc
        return self.es_info['stages']

    # Dump the string
    def dump(self, json_event):
        print(json.dumps(json_event, sort_keys=True, indent=2))

    # Post the event to each target
    def post(self, json_event):
        status = 0
        for target in self.targets:
            status += target.driver.send_event(json_event)
        return status

    def finish(self):
        status = 0
        for target in self.targets:
            status += target.driver.finish_send()
        return status

    def gather_all(self):
        self.get_build_data()
        self.get_events()

    def post_all(self):
        process_events = [self.es_info] + self.events
        status = 0
        for e in process_events:
            status += self.post(e)
        status += self.finish()
        return status
