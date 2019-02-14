# Copyright (c) 2018 Cisco Systems, Inc.
# All rights reserved.

__author__ = 'mvillene'

from ..interface import EventGenerator
import logging

LOGGER = logging.getLogger(__name__)


class StageEvent(EventGenerator):
    """
    """
    def get_fields(self):
        return super(StageEvent, self).get_fields()

    def generate_events(self, esl):

        LOGGER.debug("Starting: {}".format(type(self).__name__))

        output_list = []

        stages_report = esl.get_stages()

        if stages_report is not None:

            stages = stages_report.pop('stages', None)
            stages_report.pop('name', None)

            for stage in stages:
                output_list.append(stage)

        LOGGER.debug("Finished: {}".format(type(self).__name__))
        return output_list



