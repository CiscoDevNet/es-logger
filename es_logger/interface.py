# Copyright (c) 2018 Cisco Systems, Inc.
# All rights reserved.

__author__ = 'jonpsull'

import abc
import six


@six.add_metaclass(abc.ABCMeta)
class ConsoleLogProcessor(object):
    """
    Base class for a console log processor
    """

    def __init__(self):
        super(ConsoleLogProcessor, self).__init__()

    @abc.abstractmethod
    def process(self, console_log):
        """
        Parse the console log and return a dict for ES

        :param console_log: The console log of the build
        :type console_log: str
        :returns: dict(str:?)
        """


@six.add_metaclass(abc.ABCMeta)
class GatherBuildData(object):
    """
    Base class for a build data gatherer
    """

    def __init__(self):
        super(GatherBuildData, self).__init__()

    @abc.abstractmethod
    def gather(self, esl):
        """
        Gather any extra data that is wanted to accompany the Jenkins info

        :param esl: The es-logger calling this plugin
        :type esl: object
        :returns: dict(str:?)
        """


@six.add_metaclass(abc.ABCMeta)
class EventGenerator(object):
    """
    Base class for a build data event generator
        * This will allow for the creation of an array of individual events from the data
          gathered by the EsLogger
        * Use cases include:
            * Pushing events for individual test runs
            * Pushing per-host data from a job that affects multiple hosts
    """
    # The default Jenkins fields to add to the generated events
    DEFAULT_FIELDS = [
        'BUILD_NUMBER',
        'JOB_NAME',
        'BUILD_URL'
    ]

    def __init__(self):
        super(EventGenerator, self).__init__()

    def get_fields(self):
        return self.DEFAULT_FIELDS

    @abc.abstractmethod
    def generate_events(self, esl):
        """
        Create the events to additionally push

        :param esl: The es-logger calling this plugin
        :type esl: object
        :returns: list(obj)
        """


@six.add_metaclass(abc.ABCMeta)
class EventTarget(object):
    """
    Base class for an event target
    """

    def __init__(self):
        super(EventTarget, self).__init__()

    @staticmethod
    @abc.abstractmethod
    def get_help_string(self):
        """
        """

    @abc.abstractmethod
    def validate(self):
        """
        Validate that we have all we need to send to target

        :returns: boolean
        """

    @abc.abstractmethod
    def send_event(self, json_event):
        """
        Parse the console log and return a dict for ES

        :param json_event: The variable containing the event to send
        :type json_event: dict
        :returns: int
        """

    def finish_send(self):
        return 0
