# Copyright (c) 2018 Cisco Systems, Inc.
# All rights reserved.

__author__ = 'jonpsull'

import asyncio
import es_logger
import nose
import os
import unittest.mock


class TestZMQClient(object):
    config_dict = {}
    sample_completed_message = '''onFinalized {"name":"sample-job",
        "url":"job/folder/job/sample-job/","build":{
        "full_url":"https://joc.example.com/jenkins/jenkins_url/job/folder/job/sample-job/123/",
        "number":123,"phase":"COMPLETED","status":"SUCCESS","url":"job/folder/job/sample-job/123/",
        "node_name":"","node_description":"the master Jenkins node",
        "host_name":"jenkins_url"}}'''.encode('ascii')
    sample_completed_message_log = 'b\'onFinalized {"name":"sample-job",\\n        ' +\
        '"url":"job/folder/job/sample-job/","build":{\\n        "full_url":' +\
        '"https://joc.example.com/jenkins/jenkins_url/job/folder/job/sample-job/123/",\\n' +\
        '        "number":123,"phase":"COMPLETED","status":"SUCCESS","url":' +\
        '"job/folder/job/sample-job/123/",\\n        "node_name":"","node_description":' +\
        '"the master Jenkins node",\\n        "host_name":"jenkins_url"}}\''
    sample_finished_message = '''onFinalized {"name":"sample-job",
        "url":"job/folder/job/sample-job/","build":{
        "full_url":"https://joc.example.com/jenkins/jenkins_url/job/folder/job/sample-job/123/",
        "number":123,"phase":"FINISHED","status":"SUCCESS","url":"job/folder/job/sample-job/123/",
        "node_name":"","node_description":"the master Jenkins node",
        "host_name":"jenkins_url"}}'''.encode('ascii')
    sample_finished_message_log = 'b\'onFinalized {"name":"sample-job",\\n        ' +\
        '"url":"job/folder/job/sample-job/","build":{\\n        "full_url":' +\
        '"https://joc.example.com/jenkins/jenkins_url/job/folder/job/sample-job/123/",\\n' +\
        '        "number":123,"phase":"FINISHED","status":"SUCCESS","url":' +\
        '"job/folder/job/sample-job/123/",\\n        "node_name":"","node_description":' +\
        '"the master Jenkins node",\\n        "host_name":"jenkins_url"}}\''

    def setup(self):
        self.config_dict = {}
        self.zmqd = es_logger.zmq_client.ESLoggerZMQDaemon()
        self.zmqd.async_main_sleep = 5
        self.zmqd.worker_sleep = 5
        self.loop = asyncio.new_event_loop()
        self.loop.set_debug(True)
        asyncio.set_event_loop(self.loop)

    def get_config_item(self, name):
        return self.config_dict[name]

    def set_config_item(self, name, val):
        self.config_dict[name] = val

    def config_contains(self, name):
        return name in self.config_dict

    def config_setup(self, mock_config_parser):
        config = mock_config_parser.return_value
        config.__getitem__.side_effect = self.get_config_item
        config.__setitem__.side_effect = self.set_config_item
        config.__contains__.side_effect = self.config_contains
        return config

    def set_default_config(self, config):
        config['jenkins'] = {}
        config['jenkins']['jenkins_url'] = 'https://jenkins.example.com'
        config['jenkins']['jenkins_user'] = 'jenkins_user'
        config['jenkins']['jenkins_password'] = 'jenkins_password'
        config['logstash'] = {}
        config['logstash']['logstash_server'] = 'https://logstash.example.com:8080'
        config['logstash']['ls_user'] = 'ls_user'
        config['logstash']['ls_password'] = 'ls_password'
        config['zmq'] = {}
        config['zmq']['zmq_publisher'] = 'tcp://jenkins.example.com:8888'

    def set_plugin_config(self, config):
        config['plugins'] = {}
        config['plugins']['process_console_logs'] = 'process_console_logs'
        config['plugins']['gather_build_data'] = 'gather_build_data'
        config['plugins']['generate_events'] = 'generate_events'

    async def dummyTask(self, name, sleep=0, return_status=0, exception=None):
        print(f"I am dummyTask {name}")
        # Give 5 seconds to ensure the main loop drops into check status
        if sleep > 0:
            await asyncio.sleep(sleep)
        if exception is not None:
            raise exception
        print(f"dummyTask {name} finishing")
        return return_status

    # Test call flow with good options
    def test_zmq_client_configure_default(self):
        with unittest.mock.patch('configparser.ConfigParser') as mock_config_parser:
            config = self.config_setup(mock_config_parser)
            self.set_default_config(config)
            self.zmqd.configure()
            es_logger_default = ' '.join(
                es_logger.EsLogger.list_plugins(True, ['console_log_processor']))
            nose.tools.ok_(self.zmqd.process_console_logs == es_logger_default,
                           "{} did not match {}".format(self.zmqd.process_console_logs,
                                                        es_logger_default))
            es_logger_default = ' '.join(
                es_logger.EsLogger.list_plugins(True, ['gather_build_data']))
            nose.tools.ok_(self.zmqd.gather_build_data == es_logger_default,
                           "{} did not match {}".format(self.zmqd.gather_build_data,
                                                        es_logger_default))
            es_logger_default = ' '.join(
                es_logger.EsLogger.list_plugins(True, ['event_generator']))
            nose.tools.ok_(self.zmqd.generate_events == es_logger_default,
                           "{} did not match {}".format(self.zmqd.generate_events,
                                                        es_logger_default))

    # Test call flow with good options
    def test_zmq_client_configure(self):
        with unittest.mock.patch('configparser.ConfigParser') as mock_config_parser:
            config = self.config_setup(mock_config_parser)
            self.set_default_config(config)
            self.set_plugin_config(config)
            self.zmqd.configure()
            for key in self.zmqd.env_vars:
                if hasattr(self.zmqd, key.lower()):
                    nose.tools.ok_(os.environ[key] == getattr(self.zmqd, key.lower()))

    @nose.tools.raises(es_logger.zmq_client.ZMQClientMisconfiguration)
    def test_zmq_missing_config(self):
        es_logger.zmq_client.ESLoggerZMQDaemon().configure()

    def test_get_project_name(self):
        project = es_logger.zmq_client.ESLoggerZMQDaemon.get_project_name("//job/foo/job/bar/")
        nose.tools.ok_(project == '/foo/bar')

    @unittest.mock.patch('es_logger.EsLogger', autospec=True)
    def test_es_logger_task(self, mock_esl):
        self.zmqd.jenkins_url = 'https://joc.example.com/jenkins/jenkins_url'
        mock_esl_instance = mock_esl(32500, ['logstash'])
        mock_esl_instance.post_all.return_value = 0
        with nose.tools.assert_logs(level='DEBUG') as cm:
            self.zmqd.es_logger_task([self.sample_finished_message])
        nose.tools.assert_equal(cm.output,
                                ['DEBUG:root:Process folder/sample-job number 123 on ' +
                                 'https://joc.example.com/jenkins/jenkins_url',
                                 'DEBUG:root:folder/sample-job number 123 status 0'])
        esl_calls = [unittest.mock.call().gather_all(),
                     unittest.mock.call().post_all()]
        nose.tools.assert_equals(mock_esl.method_calls, esl_calls)

    @unittest.mock.patch('es_logger.EsLogger', autospec=True)
    def test_es_logger_task_not_finished(self, mock_esl):
        self.zmqd.jenkins_url = 'https://joc.example.com/jenkins/jenkins_url'
        mock_esl_instance = mock_esl(32500, ['logstash'])
        mock_esl_instance.post_all.return_value = 0
        with nose.tools.assert_logs(level='DEBUG') as cm:
            self.zmqd.es_logger_task([self.sample_completed_message])
        nose.tools.assert_equal(cm.output,
                                ['DEBUG:root:Not collecting from job in phase COMPLETED'])
        esl_calls = []
        nose.tools.assert_equals(mock_esl.method_calls, esl_calls)

    def test_worker(self):
        with nose.tools.assert_logs(level='DEBUG') as cm:
            status_list = asyncio.run(self.async_worker())
        nose.tools.ok_(self.zmqd.queue.qsize() == 0)
        nose.tools.ok_(status_list == [0])
        self.zmqd.es_logger_task.assert_called_with(self.sample_finished_message)
        nose.tools.assert_equal(
            cm.output,
            ['DEBUG:asyncio:Using selector: EpollSelector',
             'INFO:root:worker-1 Starting',
             'DEBUG:root:worker-1 waiting for work',
             'INFO:root:worker-1 processing msg ' + self.sample_finished_message_log,
             'DEBUG:root:worker-1 result 0',
             'DEBUG:root:worker-1 waiting for work',
             'INFO:root:worker-1 cancelled, finishing',
             'INFO:root:worker-1 Finished'])

    async def async_worker(self):
        self.zmqd.queue = asyncio.Queue()
        self.zmqd.es_logger_task = unittest.mock.MagicMock()
        self.zmqd.es_logger_task.return_value = 0
        task = asyncio.create_task(self.zmqd.worker(f'worker-1'))
        self.zmqd.queue.put_nowait(self.sample_finished_message)
        # Yield control to the worker task
        await asyncio.sleep(1)
        # Cancel the worker
        task.cancel()
        return await asyncio.gather(task, return_exceptions=True)

    def test_worker_timeout(self):
        with nose.tools.assert_logs(level='DEBUG') as cm:
            status_list = asyncio.run(self.async_worker_timeout())
        nose.tools.ok_(self.zmqd.queue.qsize() == 0)
        nose.tools.ok_(status_list == [0])
        nose.tools.assert_equal(
            cm.output,
            ['DEBUG:asyncio:Using selector: EpollSelector',
             'INFO:root:worker-1 Starting',
             'DEBUG:root:worker-1 waiting for work',
             'DEBUG:root:worker-1 timeout waiting for work, looping',
             'DEBUG:root:worker-1 waiting for work',
             'INFO:root:worker-1 cancelled, finishing',
             'INFO:root:worker-1 Finished'])

    async def async_worker_timeout(self):
        self.zmqd.queue = asyncio.Queue()
        task = asyncio.create_task(self.zmqd.worker(f'worker-1'))
        # Yield control to the worker task
        await asyncio.sleep(self.zmqd.worker_sleep + 1)
        # Cancel the worker
        task.cancel()
        return await asyncio.gather(task, return_exceptions=True)

    def test_drain_queue(self):
        with nose.tools.assert_logs(level='DEBUG') as cm:
            status_list = asyncio.run(self.async_drain_queue())
        nose.tools.ok_(status_list == [0])
        calls = [unittest.mock.call(self.sample_completed_message),
                 unittest.mock.call(self.sample_finished_message)]
        self.zmqd.es_logger_task.assert_has_calls(calls)
        nose.tools.assert_equal(
            cm.output,
            ['DEBUG:asyncio:Using selector: EpollSelector',
             'INFO:root:Draining queue',
             'DEBUG:root:Queue of size 2',
             'INFO:root:Processing msg ' + self.sample_completed_message_log,
             'DEBUG:root:Result None',
             'DEBUG:root:Queue of size 1',
             'INFO:root:Processing msg ' + self.sample_finished_message_log,
             'DEBUG:root:Result 0',
             'INFO:root:Queue drained, size 0'])

    async def async_drain_queue(self):
        self.zmqd.es_logger_task = unittest.mock.MagicMock()
        self.zmqd.es_logger_task.side_effect = [None, 0]
        self.zmqd.queue = asyncio.Queue()
        self.zmqd.queue.put_nowait(self.sample_completed_message)
        self.zmqd.queue.put_nowait(self.sample_finished_message)
        return await self.zmqd.drain_queue()

    @unittest.mock.patch('es_logger.zmq_client.Context', autospec=True)
    def test_recv(self, mock_context):
        self.zmqd.zmq_publisher = 'tcp://jenkins.example.com:8888'
        mc_instance = mock_context.instance()
        self.zmqd.queue = asyncio.Queue()

        with nose.tools.assert_logs(level='DEBUG') as cm:
            listener = asyncio.run(self.async_recv(mc_instance))

        nose.tools.assert_equal(
            cm.output,
            ['DEBUG:asyncio:Using selector: EpollSelector',
             'INFO:root:Listener Starting against tcp://jenkins.example.com:8888',
             'DEBUG:root:Listener waiting for message',
             'DEBUG:root:Adding 1 to queue 0',
             'DEBUG:root:Listener waiting for message',
             'INFO:root:Listener cancelled, finishing',
             'INFO:root:Listener Finished'])
        context_calls = [
            unittest.mock.call.instance(),
            unittest.mock.call.instance().socket(),
            unittest.mock.call.instance(),
            unittest.mock.call.instance().socket(2),
            unittest.mock.call.instance().socket().connect('tcp://jenkins.example.com:8888'),
            unittest.mock.call.instance().socket().subscribe(b'')]
        mock_context.assert_has_calls(context_calls)
        nose.tools.ok_(listener.done())

    async def async_recv(self, mc_instance):
        future_msg = asyncio.Future()
        future_msg.set_result(1)
        mc_instance.socket().recv_multipart.side_effect = [future_msg, asyncio.Future()]
        listener = asyncio.create_task(self.zmqd.recv())
        await asyncio.sleep(1)
        listener.cancel()
        return listener

    def test_start(self):
        dummy_task = unittest.mock.MagicMock()
        dummy_task.return_value = self.dummyTask(0)
        self.zmqd.recv = dummy_task
        self.zmqd.worker = dummy_task
        self.zmqd.num_workers = 2
        with nose.tools.assert_logs(level='DEBUG') as cm:
            asyncio.run(self.async_start())
        nose.tools.assert_equal(
            cm.output,
            ['DEBUG:asyncio:Using selector: EpollSelector',
             'INFO:root:Starting',
             'INFO:root:Started 2 workers'])
        nose.tools.ok_(len(self.zmqd.tasks) == 2)
        nose.tools.ok_(self.zmqd.listener)

    async def async_start(self):
        self.zmqd.start()

    def test_stop(self):
        with nose.tools.assert_logs(level='DEBUG') as cm:
            asyncio.run(self.async_stop())
        # Use the log messages to assert we cancelled the tasks
        nose.tools.assert_regex(
            '\n'.join(cm.output),
            '\n'.join(
                [r'DEBUG:asyncio:Using selector: EpollSelector',
                 r'INFO:root:Stopping listener',
                 r'INFO:root:Stopping tasks',
                 r'DEBUG:root:All Tasks: {.*}',
                 r'INFO:root:Stopped, waiting for tasks to finish']))

    async def async_stop(self):
        self.zmqd.listener = asyncio.create_task(self.dummyTask(1, sleep=5))
        self.zmqd.tasks = [asyncio.create_task(self.dummyTask(2, sleep=5))]
        return self.zmqd.stop()

    # Tested as part of next 2 tests
    def test_check_task(self):
        pass

    def test_check_listener(self):
        self.zmqd.listener = unittest.mock.create_autospec(asyncio.Task)
        self.zmqd.listener.done = unittest.mock.Mock(side_effect=[False, True])
        task_status = self.zmqd.check_listener()
        nose.tools.ok_(task_status)
        task_status = self.zmqd.check_listener()
        nose.tools.ok_(not task_status)

    def test_check_tasks(self):
        self.zmqd.tasks = [unittest.mock.create_autospec(asyncio.Task),
                           unittest.mock.create_autospec(asyncio.Task)]
        self.zmqd.tasks[0].done = unittest.mock.Mock(side_effect=[False, False, True])
        self.zmqd.tasks[1].done = unittest.mock.Mock(side_effect=[False, True])
        task_status = self.zmqd.check_tasks()
        nose.tools.ok_(task_status)
        task_status = self.zmqd.check_tasks()
        nose.tools.ok_(not task_status)
        task_status = self.zmqd.check_tasks()
        nose.tools.ok_(not task_status)

    def test_all_tasks(self):
        self.zmqd.listener = unittest.mock.create_autospec(asyncio.Task)
        self.zmqd.tasks = [unittest.mock.create_autospec(asyncio.Task)]
        nose.tools.assert_equal(self.zmqd.all_tasks(), [self.zmqd.listener] + self.zmqd.tasks)

    def test_tasks_done(self):
        self.zmqd.listener = unittest.mock.create_autospec(asyncio.Task)
        self.zmqd.tasks = [unittest.mock.create_autospec(asyncio.Task)]
        self.zmqd.listener.done = unittest.mock.Mock(side_effect=[False, True, True])
        self.zmqd.tasks[0].done = unittest.mock.Mock(side_effect=[False, True])
        # No tasks done
        tasks_done = self.zmqd.tasks_done()
        nose.tools.ok_(not tasks_done)
        # One task done
        tasks_done = self.zmqd.tasks_done()
        nose.tools.ok_(not tasks_done)
        # All tasks done
        tasks_done = self.zmqd.tasks_done()
        nose.tools.ok_(tasks_done)

    def test_async_main(self):
        self.zmqd.queue = asyncio.Queue()
        self.zmqd.check_listener = unittest.mock.MagicMock()
        self.zmqd.check_tasks = unittest.mock.MagicMock()
        self.zmqd.start = unittest.mock.MagicMock()
        with nose.tools.assert_logs(level='DEBUG') as cm:
            status = asyncio.run(self.async_async_main())
        nose.tools.assert_equal(
            cm.output,
            ['DEBUG:asyncio:Using selector: EpollSelector',
             'INFO:root:Started tasks, entering status check loop',
             'INFO:root:Exited status check loop',
             'INFO:root:Draining queue',
             'INFO:root:Queue drained, size 0',
             'INFO:root:Gathering task statuses'])
        nose.tools.ok_(status == 0)

    async def async_async_main(self):
        self.zmqd.listener = asyncio.create_task(self.dummyTask(1, sleep=5))
        self.zmqd.tasks = [asyncio.create_task(self.dummyTask(2, sleep=5))]
        return await self.zmqd.async_main()

    def test_async_main_unknown(self):
        self.zmqd.queue = asyncio.Queue()
        self.zmqd.start = unittest.mock.MagicMock()
        with nose.tools.assert_logs(level='DEBUG') as cm:
            status = asyncio.run(self.async_async_main_unknown())
        nose.tools.assert_equal(
            cm.output,
            ['DEBUG:asyncio:Using selector: EpollSelector',
             'INFO:root:Started tasks, entering status check loop',
             'INFO:root:Exited status check loop',
             'INFO:root:Draining queue',
             'INFO:root:Queue drained, size 0',
             'INFO:root:Gathering task statuses',
             'WARNING:root:Unknown status: Bad return'])
        nose.tools.ok_(status == 1)

    async def async_async_main_unknown(self):
        self.zmqd.listener = asyncio.create_task(self.dummyTask(1))
        self.zmqd.tasks = [asyncio.create_task(self.dummyTask(2, return_status="Bad return"))]
        return await self.zmqd.async_main()

    def test_async_main_exception(self):
        self.zmqd.queue = asyncio.Queue()
        self.zmqd.start = unittest.mock.MagicMock()
        with nose.tools.assert_logs(level='DEBUG') as cm:
            status = asyncio.run(self.async_async_main_exception())
        nose.tools.assert_equal(
            cm.output,
            ['DEBUG:asyncio:Using selector: EpollSelector',
             'INFO:root:Started tasks, entering status check loop',
             'INFO:root:Exited status check loop',
             'INFO:root:Draining queue',
             'INFO:root:Queue drained, size 0',
             'INFO:root:Gathering task statuses',
             'WARNING:root:Exception: Exception message'])
        nose.tools.ok_(status == 1)

    async def async_async_main_exception(self):
        self.zmqd.listener = asyncio.create_task(self.dummyTask(1))
        self.zmqd.tasks = [asyncio.create_task(
            self.dummyTask(2, exception=Exception("Exception message")))]
        return await self.zmqd.async_main()

    def test_async_main_bad_listener(self):
        self.zmqd.queue = asyncio.Queue()
        self.zmqd.start = unittest.mock.MagicMock()
        self.zmqd.stop = unittest.mock.MagicMock()
        self.zmqd.check_listener = unittest.mock.MagicMock()
        self.zmqd.check_listener.return_value = False
        with nose.tools.assert_logs(level='DEBUG') as cm:
            status = asyncio.run(self.async_async_bad_listener())
        nose.tools.ok_(status == 1)
        self.zmqd.stop.assert_called_once()
        nose.tools.assert_in('WARNING:root:Listener not running', cm.output)

    async def async_async_bad_listener(self):
        self.zmqd.listener = asyncio.create_task(
            self.dummyTask("listener", sleep=3, exception=Exception("Exception message")))
        self.zmqd.tasks = [asyncio.create_task(self.dummyTask("worker", sleep=5))]
        return await self.zmqd.async_main()

    def test_async_main_bad_worker(self):
        self.zmqd.queue = asyncio.Queue()
        self.zmqd.start = unittest.mock.MagicMock()
        self.zmqd.stop = unittest.mock.MagicMock()
        self.zmqd.check_tasks = unittest.mock.MagicMock()
        self.zmqd.check_tasks.return_value = False
        with nose.tools.assert_logs(level='DEBUG') as cm:
            status = asyncio.run(self.async_async_bad_worker())
        nose.tools.ok_(status == 1)
        self.zmqd.stop.assert_called_once()
        nose.tools.assert_in('WARNING:root:Tasks not running', cm.output)

    async def async_async_bad_worker(self):
        self.zmqd.listener = asyncio.create_task(self.dummyTask("listener", sleep=5))
        self.zmqd.tasks = [asyncio.create_task(
            self.dummyTask("worker", sleep=3, exception=Exception("Exception message")))]
        return await self.zmqd.async_main()

    @unittest.mock.patch('es_logger.zmq_client.asyncio', autospec=True)
    def test_main(self, mock_asyncio):
        with unittest.mock.patch('configparser.ConfigParser') as mock_config_parser:
            config = self.config_setup(mock_config_parser)
            self.set_default_config(config)
            self.set_plugin_config(config)
            mock_asyncio.run.return_value = 0
            self.zmqd.async_main = unittest.mock.Mock()
            status = self.zmqd.main()
        print(mock_asyncio.mock_calls)
        mock_asyncio.assert_has_calls([unittest.mock.call.run(self.zmqd.async_main())])
        nose.tools.assert_equal(status, 0)
