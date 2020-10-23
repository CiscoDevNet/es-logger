#!/usr/bin/env python

# Copyright (c) 2018 Cisco Systems, Inc.
# All rights reserved.

__author__ = 'jonpsull'

import argparse
import asyncio
import configparser
import es_logger
import json
import logging
import os
import signal
from stevedore import driver
import sys
import urllib
import zmq
from zmq.asyncio import Context


# Configure logging for the daemon
def configure_logging(debug=False):  # pragma: no cover
    if debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logging.basicConfig(level=log_level,
                        format='%(asctime)s %(name)s %(levelname)s %(message)s')


# Base Exception Class
class ZMQClientError(Exception):
    pass


# Misconfiguration exception class
class ZMQClientMisconfiguration(ZMQClientError):
    pass


# Class for running es-logger as Jenkins ZMQ listener
class ESLoggerZMQDaemon(object):
    def __init__(self, args):
        self.listener = None
        self.tasks = []
        self.env_vars = ['JENKINS_URL', 'JENKINS_USER', 'JENKINS_PASSWORD', 'PROCESS_CONSOLE_LOGS',
                         'GATHER_BUILD_DATA', 'GENERATE_EVENTS']
        self.process_console_logs = ''
        self.gather_build_data = ''
        self.generate_events = ''
        self.async_main_sleep = 30
        self.worker_sleep = 15
        self.test_zmq = args.test_zmq
        self.targets = {}

    # Read the configuration
    def configure(self, config_file='es-logger.ini'):
        config = configparser.ConfigParser()
        config.read(config_file)

        if 'zmq' in config:
            self.num_workers = int(config['zmq'].get('num_workers', 3))
            self.zmq_publisher = config['zmq'].get('zmq_publisher')

        if 'jenkins' in config:
            self.jenkins_url = config['jenkins'].get('jenkins_url')
            self.jenkins_user = config['jenkins'].get('jenkins_user')
            self.jenkins_password = config['jenkins'].get('jenkins_password')

        if 'eslogger' in config:
            targets = config['eslogger'].get('targets', 'logstash').split(' ')
        else:
            targets = ['logstash']

        # Handle target configuration
        for target in targets:
            logging.debug("Checking for {} target configuration".format(target))
            self.targets[target] = {}
            if target in config.keys():
                for var in config[target].keys():
                    self.targets[target][var] = config[target].get(var)
                    logging.debug("Setting target configuration {}".format(self.targets[target]))
                    self.set_in_env(var, self.targets[target][var])

        # Set defaults plugins to all unless overridden
        if 'plugins' not in config:
            config['plugins'] = {}
        self.plugins = {}

        console_log_processor = ' '.join(
            es_logger.EsLogger.list_plugins(True, ['console_log_processor']))
        self.process_console_logs = config['plugins'].get('process_console_logs',
                                                          console_log_processor)
        logging.info("Using console_log_processor plugins: {}".format(self.process_console_logs))
        self.get_plugin_config("process_console_logs", self.process_console_logs.split(" "), config)

        gather_build_data = ' '.join(
            es_logger.EsLogger.list_plugins(True, ['gather_build_data']))
        self.gather_build_data = config['plugins'].get('gather_build_data', gather_build_data)
        logging.info("Using gather_build_data plugins: {}".format(self.gather_build_data))
        self.get_plugin_config("gather_build_data", self.gather_build_data.split(" "), config)

        event_generator = ' '.join(es_logger.EsLogger.list_plugins(True, ['event_generator']))
        self.generate_events = config['plugins'].get('generate_events', event_generator)
        logging.info("Using generate_events plugins: {}".format(self.generate_events))
        self.get_plugin_config("generate_events", self.generate_events.split(" "), config)

        # Set the necessary environment variables
        for var in self.env_vars:
            if hasattr(self, var.lower()):
                self.set_in_env(var, getattr(self, var.lower()))

        # Iterate over the plugin configuration and set it in the environment
        for plugin in self.plugins.keys():
            for var in self.plugins[plugin].keys():
                self.set_in_env(var, self.plugins[plugin][var])

        self.validate_config()

    # lower case var to upper case env var
    @staticmethod
    def set_in_env(var, val):
        var_name = var.upper()
        if val is not None and val != '':
            os.environ[var_name] = val
            logging.debug('Setting env var {}'.format(var_name))

    # Check for plugin-specific configuration
    def get_plugin_config(self, plugin_type, plugin_list, config):
        for plugin in plugin_list:
            plugin_key = plugin_type + ":" + plugin
            if plugin_key in config:
                self.plugins[plugin_key] = {}
                for key in config[plugin_key]:
                    self.plugins[plugin_key][key] = config[plugin_key].get(key)

    # Make sure we are correctly configured
    def validate_config(self):
        # Confirm configuration or raise an exception
        unset_attr = []
        needed_attrs = ['jenkins_url', 'jenkins_user', 'jenkins_password', 'zmq_publisher']
        target_attrs = []
        for target in self.targets:
            drv = driver.DriverManager(namespace='es_logger.plugins.event_target',
                                       invoke_on_load=False,
                                       name=target)
            target_attrs = target_attrs + drv.driver.get_required_vars()
        for attr in needed_attrs + target_attrs:
            if ((not hasattr(self, attr.lower())) or getattr(self, attr.lower()) is None) and \
                    os.environ.get(attr.upper(), None) is None:
                unset_attr.append(attr)
        if len(unset_attr) > 0:
            e = ZMQClientMisconfiguration(
                "Unconfigured for daemon operation, check config or environment for the following "
                + "variables (UPPERCASE for environment variables):\n{}".format(unset_attr))
            raise(e)

    # Strip off trailing slashes, and remove each "job" path element
    @staticmethod
    def get_project_name(job):
        project = urllib.parse.urlsplit(job).path
        # Ensure no trailing slash
        project = project.rstrip('/')
        # Ensure no job elements in path, as python-jenkins expects to add them
        project = '/'.join([p for p in project.split('/') if p != 'job'])
        # Finally, unquote the string, as python-jenkins expects to url encode
        project = urllib.parse.unquote(project)
        return project

    # Processing function to validate ZMQ connection
    def test_zmq_task(self, msg):
        var = json.loads(''.join(msg[0].decode("utf-8").split()[1:]))
        job = self.get_project_name(var['url'])
        number = var['build'].get('number')
        phase = var['build'].get('phase')
        logging.info(f'Got event: job [{job}] number [{number}] phase [{phase}]')
        return 0

    # Processing function to run es-logger
    def es_logger_task(self, msg):
        var = json.loads(''.join(msg[0].decode("utf-8").split()[1:]))
        phase = var['build'].get('phase')
        if phase == 'FINISHED':
            job = self.get_project_name(var['url'])
            number = var['build'].get('number')
            logging.info("Process {} number {} on {}".format(job, number, self.jenkins_url))
            # Create and configure the ES-Logger instance
            esl = es_logger.EsLogger(console_length=32500, targets=self.targets)
            esl.es_job_name = job
            esl.es_build_number = int(number)
            esl.gather_all()
            status = esl.post_all()
            logging.info("{} number {} status {}".format(job, number, status))
        else:
            logging.debug('Not collecting from job in phase {}'.format(phase))
            status = None
        return status

    # Worker to pull tasks off queue, process message, and execute
    async def worker(self, name, process_func):
        logging.info("{} Starting".format(name))
        current_task = asyncio.current_task()
        while not current_task.done():
            try:
                logging.debug("{} waiting for work".format(name))
                msg = await asyncio.wait_for(self.queue.get(), self.worker_sleep)
                logging.debug("{} processing msg {}".format(name, msg))
                result = getattr(self, process_func)(msg)
                self.queue.task_done()
                logging.debug("{} result {}".format(name, result))
            except asyncio.TimeoutError:
                logging.debug("{} timeout waiting for work, looping".format(name))
            except asyncio.CancelledError:
                logging.info("{} cancelled, finishing".format(name))
                break
        logging.info("{} Finished".format(name))
        return 0

    # Drain the queue to enable clean shutdown
    async def drain_queue(self):
        status_list = []
        qsize = self.queue.qsize()
        processed = 0
        logging.info("Draining queue of size {}".format(qsize))
        while self.queue.qsize() != 0:
            msg = self.queue.get_nowait()
            logging.debug("Processing msg {}".format(msg))
            result = self.es_logger_task(msg)
            self.queue.task_done()
            logging.debug("Result {}".format(result))
            if result is not None:
                status_list.append(result)
            processed += 1
        logging.info("Queue drained, processed {}".format(processed))
        return status_list

    # Connection function executed as listener task
    async def recv(self):
        logging.info('Listener Starting against {}'.format(self.zmq_publisher))
        # Connect to ZMQ
        ctx = Context.instance()
        s = ctx.socket(zmq.SUB)
        s.connect(self.zmq_publisher)
        s.subscribe(b'')

        current_task = asyncio.current_task()
        while not current_task.done():
            try:
                logging.debug("Listener waiting for message")
                msg = await asyncio.wait_for(s.recv_multipart(), None)
                logging.debug("Adding {} to queue {}".format(msg, self.queue.qsize()))
                await self.queue.put(msg)
            except asyncio.CancelledError:
                logging.info("Listener cancelled, finishing")
                break
        s.close()
        logging.info("Listener Finished")
        return 0

    # Start the threads for processing
    def start(self):
        logging.info('Starting')
        # Setup signal handlers
        self.loop = asyncio.get_running_loop()
        for signame in ('SIGINT', 'SIGTERM'):
            self.loop.add_signal_handler(getattr(signal, signame), self.stop)
        self.queue = asyncio.Queue()
        # Create an asynchronous listener task
        self.listener = asyncio.create_task(self.recv())
        # Create worker tasks to process the queue concurrently.
        self.tasks = []
        if self.test_zmq:
            process_func = 'test_zmq_task'
        else:
            process_func = 'es_logger_task'
        for i in range(self.num_workers):
            task = asyncio.create_task(self.worker(f'worker-{i}', process_func))
            self.tasks.append(task)
        logging.info(f'Started {self.num_workers} workers using {process_func}')

    # Cancel the threads for stopping
    def stop(self):
        if self.listener is not None:
            logging.info("Stopping listener")
            self.listener.cancel()
        if len(self.tasks) > 0:
            logging.info("Stopping tasks")
            for task in self.tasks:
                task.cancel()
        all_tasks = asyncio.all_tasks()
        logging.debug("All Tasks: {}".format(all_tasks))
        logging.info("Stopped, waiting for tasks to finish")

    # Check a task is in a good state
    def check_task(self, task):
        if task.done():
            return False
        return True

    # Check that the listener is still running correctly
    def check_listener(self):
        logging.debug(self.listener)
        return self.check_task(self.listener)

    # Check that worker tasks are still running
    def check_tasks(self):
        logging.debug(self.tasks)
        for task in self.tasks:
            if not self.check_task(task):
                return False
        return True

    # Return a list of all tasks started
    def all_tasks(self):
        return [self.listener] + self.tasks

    # Boolean declaring whether all tasks are done or not
    def tasks_done(self):
        for task in self.all_tasks():
            if not task.done():
                return False
        return True

    # The ASync executed main function to control lifecycle
    async def async_main(self):
        # Start, monitor, then stop
        self.start()
        # Give some time to start up (also helps tests run faster)
        await asyncio.sleep(2)
        logging.info("Started tasks, entering status check loop")
        while not self.tasks_done():
            if not self.check_listener():
                logging.warning("Listener not running")
                self.stop()
                break
            if not self.check_tasks():
                logging.warning("Tasks not running")
                self.stop()
                break
            await asyncio.sleep(self.async_main_sleep)

        logging.info("Exited status check loop")

        # Ensure all the tasks get completed
        drain_status = await self.drain_queue()

        # Wait for all of the coroutines to finish and gather the result
        logging.info("Gathering task statuses")
        status_list = await asyncio.gather(*([self.listener] + self.tasks), return_exceptions=True)
        status_list = status_list + drain_status
        status = 0
        for s in status_list:
            if isinstance(s, Exception):
                logging.warning("Exception: {}".format(s))
                status += 1
            elif isinstance(s, int):
                status += s
            else:
                logging.warning("Unknown status: {}".format(s))
                status += 1
        return status

    # Synchronous main to trigger async main only,
    # after loading configuration and setting environment
    def main(self):
        self.configure()
        status = asyncio.run(self.async_main())
        logging.info("Finished")
        return status


# Argument parsing shouldn't need coverage, just effects of flags elsewhere
def parse_args():  # pragma: no cover
    desc = '''
Run a ZMQ subscription to connect to the Jenkins Event Publisher (via ZMQ PUB SUB) plugin.
https://plugins.jenkins.io/zmq-event-publisher/
'''
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=desc)
    parser.add_argument('-t', '--test-zmq', action='store_true',
                        help='Print details instead of processing with es-logger.')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Print debug logs to console during execution')
    args = parser.parse_args()
    return args


# Shouldn't need individual unit testing, keep as simple as possible
def main():  # pragma: no cover
    args = parse_args()
    configure_logging(args.debug)
    d = ESLoggerZMQDaemon(args)
    status = d.main()
    sys.exit(status)
