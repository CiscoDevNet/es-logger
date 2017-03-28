# Copyright (c) 2018 Cisco Systems, Inc.
# All rights reserved.

__author__ = 'jonpsull'

import es_logger
import nose
import sys
import unittest.mock

DEFAULT_CONSOLE_LENGTH = 32500


class ExitException(Exception):
    pass


class TestCli(object):

    # Test call flow with good options
    @unittest.mock.patch('es_logger.EsLogger', autospec=True)
    def test_cli(self, mock_esl):
        sys.argv = ['es-logger']
        mock_event = unittest.mock.MagicMock()
        mock_es_info = unittest.mock.MagicMock()
        mock_esl(console_length=DEFAULT_CONSOLE_LENGTH).es_info = mock_es_info
        mock_esl(console_length=DEFAULT_CONSOLE_LENGTH).post.return_value = 0
        mock_esl(console_length=DEFAULT_CONSOLE_LENGTH).events = [mock_event, mock_event]
        with unittest.mock.patch('sys.exit', side_effect=ExitException) as mock_exit:
            nose.tools.assert_raises(ExitException, es_logger.cli.main)
            mock_exit.assert_called_with(0)
            calls = [unittest.mock.call().get_build_data(),
                     unittest.mock.call().get_events(),
                     unittest.mock.call().dump(mock_es_info),
                     unittest.mock.call().post(mock_es_info),
                     unittest.mock.call().dump(mock_event),
                     unittest.mock.call().post(mock_event),
                     unittest.mock.call().dump(mock_event),
                     unittest.mock.call().post(mock_event)]
            print(mock_esl.method_calls)
            nose.tools.ok_(mock_esl.method_calls == calls)

    # Test mutually exclusive options
    @unittest.mock.patch('es_logger.EsLogger', autospec=True)
    def test_exclusive_options(self, mock_esl):
        sys.argv = ['es-logger', '--no-dump', '--no-post']
        with unittest.mock.patch('sys.exit', side_effect=ExitException()) as mock_exit:
            nose.tools.assert_raises(ExitException, es_logger.cli.main)
            mock_exit.assert_called_with(2)

    # Test console length
    @unittest.mock.patch('es_logger.EsLogger', autospec=True)
    def test_console_length(self, mock_esl):
        sys.argv = ['es-logger', '-c', '1000', '-p']
        with unittest.mock.patch('sys.exit', side_effect=ExitException()) as mock_exit:
            nose.tools.assert_raises(ExitException, es_logger.cli.main)
            mock_exit.assert_called_with(0)
        mock_esl.assert_called_with(1000)

    # Test event only generation
    @unittest.mock.patch('es_logger.EsLogger', autospec=True)
    def test_event_only(self, mock_esl):
        sys.argv = ['es-logger', '-e']
        mock_event = unittest.mock.MagicMock()
        mock_es_info = unittest.mock.MagicMock()
        mock_esl(console_length=DEFAULT_CONSOLE_LENGTH).es_info = mock_es_info
        mock_esl(console_length=DEFAULT_CONSOLE_LENGTH).post.return_value = 0
        mock_esl(console_length=DEFAULT_CONSOLE_LENGTH).events = [mock_event, mock_event]
        with unittest.mock.patch('sys.exit', side_effect=ExitException) as mock_exit:
            nose.tools.assert_raises(ExitException, es_logger.cli.main)
            mock_exit.assert_called_with(0)
            calls = [unittest.mock.call().get_build_data(),
                     unittest.mock.call().get_events(),
                     unittest.mock.call().dump(mock_event),
                     unittest.mock.call().post(mock_event),
                     unittest.mock.call().dump(mock_event),
                     unittest.mock.call().post(mock_event)]
            print(mock_esl.method_calls)
            nose.tools.ok_(mock_esl.method_calls == calls)

    # Test list plugins
    def test_list_plugins(self):
        sys.argv = ['es-logger', '-p']
        with unittest.mock.patch('sys.exit', side_effect=ExitException()) as mock_exit:
            nose.tools.assert_raises(ExitException, es_logger.cli.main)
            mock_exit.assert_called_with(0)

    def test_cli_debug(self):
        sys.argv = ['es-logger', '--debug', '-p']
        with unittest.mock.patch.object(sys, 'exit', side_effect=ExitException) as mock_exit:
            with unittest.mock.patch('logging.basicConfig') as mock_logging:
                nose.tools.assert_raises(ExitException, es_logger.cli.main)
                mock_exit.assert_called_with(0)
                mock_logging.assert_called_with(
                    format='%(asctime)s %(name)s %(levelname)s %(message)s', level=10)
