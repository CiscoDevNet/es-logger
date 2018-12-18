#!/usr/bin/env python

# Copyright (c) 2018 Cisco Systems, Inc.
# All rights reserved.

__author__ = 'jonpsull'

import asyncio
import configparser
import es_logger
import json
import logging
import os
import signal
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
    def __init__(self):
        self.listener = None
        self.tasks = []
        self.env_vars = ['JENKINS_URL', 'JENKINS_USER', 'JENKINS_PASSWORD', 'PROCESS_CONSOLE_LOGS',
                         'GATHER_BUILD_DATA', 'GENERATE_EVENTS', 'LOGSTASH_SERVER', 'LS_USER',
                         'LS_PASSWORD']
        self.process_console_logs = ''
        self.gather_build_data = ''
        self.generate_events = ''
        self.async_main_sleep = 30
        self.worker_sleep = 15

    # Read the configuration
    def configure(self, config_file='es-logger.ini'):
        config = configparser.ConfigParser()
        config.read(config_file)

        if 'zmq' in config:
            self.num_workers = config['zmq'].get('num_workers', 3)
            self.zmq_publisher = config['zmq'].get('zmq_publisher')

        if 'jenkins' in config:
            self.jenkins_url = config['jenkins'].get('jenkins_url')
            self.jenkins_user = config['jenkins'].get('jenkins_user')
            self.jenkins_password = config['jenkins'].get('jenkins_password')

        if 'plugins' in config:
            process_console_logs = ' '.join(
                es_logger.EsLogger.list_plugins(True, ['process_console_logs']))
            self.process_console_logs = config['plugins'].get('process_console_logs',
                                                              process_console_logs)
            gather_build_data = ' '.join(
                es_logger.EsLogger.list_plugins(True, ['gather_build_data']))
            self.gather_build_data = config['plugins'].get('gather_build_data', gather_build_data)
            event_generator = ' '.join(es_logger.EsLogger.list_plugins(True, ['event_generator']))
            self.generate_events = config['plugins'].get('generate_events', event_generator)

        if 'logstash' in config:
            self.logstash_server = config['logstash'].get('logstash_server')
            self.ls_user = config['logstash'].get('ls_user')
            self.ls_password = config['logstash'].get('ls_password')

        self.validate_config()

        # Set the necessary environment variables
        for var in self.env_vars:
            val = getattr(self, var.lower())
            if val is not None and val is not '':
                os.environ[var.upper()] = val

    # Make sure we are correctly configured
    def validate_config(self):
        # Confirm configuration or raise an exception
        unset_attr = []
        for attr in ['jenkins_url', 'jenkins_user', 'jenkins_password',
                     'logstash_server', 'zmq_publisher']:
            if (not hasattr(self, attr)) or getattr(self, attr) is None:
                unset_attr.append(attr)
        if len(unset_attr) > 0:
            e = ZMQClientMisconfiguration(
                "Unconfigured for daemon operation, check config "
                "for the following variables:\n{}".format(unset_attr))
            raise(e)

    # Strip off trailing slashes, and remove each "job" path element
    @staticmethod
    def get_project_name(job):
        project = urllib.parse.urlsplit(job).path
        # Ensure no trailing slash
        project = project.rstrip('/')
        # Ensure no job elements in path, as python-jenkins expects to add them
        project = '/'.join([p for p in project.split('/') if p != 'job'])
        return project

    # Processing function to run es-logger
    def es_logger_task(self, msg):
        var = json.loads(''.join(msg[0].decode("utf-8").split()[1:]))
        phase = var['build'].get('phase')
        if phase == 'FINISHED':
            job = self.get_project_name(var['url'])
            number = var['build'].get('number')
            logging.debug("Process {} number {} on {}".format(job, number, self.jenkins_url))
            # Create and configure the ES-Logger instance
            esl = es_logger.EsLogger(console_length=32500, targets=['logstash'])
            esl.es_job_name = job
            esl.es_build_number = int(number)
            esl.gather_all()
            status = esl.post_all()
            logging.debug("{} number {} status {}".format(job, number, status))
        else:
            logging.debug('Not collecting from job in phase {}'.format(phase))
            status = None
        return status

    # Worker to pull tasks off queue, process message, and execute
    async def worker(self, name):
        logging.info("{} Starting".format(name))
        current_task = asyncio.current_task()
        while not current_task.done():
            try:
                logging.debug("{} waiting for work".format(name))
                msg = await asyncio.wait_for(self.queue.get(), self.worker_sleep)
                logging.info("{} processing msg {}".format(name, msg))
                result = self.es_logger_task(msg)
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
        logging.info("Draining queue")
        status_list = []
        while self.queue.qsize() != 0:
            logging.debug("Queue of size {}".format(self.queue.qsize()))
            msg = self.queue.get_nowait()
            logging.info("Processing msg {}".format(msg))
            result = self.es_logger_task(msg)
            self.queue.task_done()
            logging.debug("Result {}".format(result))
            if result is not None:
                status_list.append(result)
        logging.info("Queue drained, size {}".format(self.queue.qsize()))
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
        for i in range(self.num_workers):
            task = asyncio.create_task(self.worker(f'worker-{i}'))
            self.tasks.append(task)
        logging.info(f'Started {self.num_workers} workers')

    # Cancel the threads for stopping
    def stop(self):
        if self.listener is not None:
            logging.info("Stopping listener")
            self.listener.cancel()
        if len(self.tasks) > 0:
            logging.info("Stopping tasks")
            for task in self.tasks:
                task.cancel()
        all_tasks = asyncio.Task.all_tasks()
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


# Shouldn't need individual unit testing, keep as simple as possible
def main():  # pragma: no cover
    configure_logging()
    d = ESLoggerZMQDaemon()
    status = d.main()
    sys.exit(status)
