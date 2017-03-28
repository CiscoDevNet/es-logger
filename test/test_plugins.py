# Copyright (c) 2018 Cisco Systems, Inc.
# All rights reserved.

__author__ = 'jonpsull'

import es_logger
import nose


class DummyConsoleLogProcessor(es_logger.plugins.ConsoleLogProcessor):
    def __init__(self):
        super().__init__()

    def process(self, console_log):
        return {'DummyConsoleLogProcessor': True}


class DummyGatherBuildData(es_logger.plugins.GatherBuildData):
    def __init__(self):
        super().__init__()

    def gather(self, es_logger):
        return {'DummyGatherBuildData': True}


class DummyEventGenerator(es_logger.plugins.EventGenerator):
    def __init__(self):
        super().__init__()

    def generate_events(self, es_logger):
        return [{'DummyEventGenerator': 1}, {'DummyEventGenerator': 2}]


class TestPlugins(object):

    def test_console_log_processor_plugins(self):
        clp = DummyConsoleLogProcessor()
        clp.process('log')

    def test_gather_build_data_plugins(self):
        gbd = DummyGatherBuildData()
        gbd.gather('log')

    def test_event_generator_plugins(self):
        eg = DummyEventGenerator()
        fields = eg.get_fields()
        nose.tools.ok_(fields == es_logger.plugins.EventGenerator.DEFAULT_FIELDS)
        eg.generate_events({'es_logger': True})
