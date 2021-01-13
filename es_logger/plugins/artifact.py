# Copyright (c) 2020 Cisco Systems, Inc.
# All rights reserved.

__author__ = 'jonpsull'

from es_logger.interface import EventGenerator
import jenkins
import json
import logging
import os

LOGGER = logging.getLogger(__name__)


class ArtifactEvent(EventGenerator):
    '''
    '''
    def __init__(self):
        super().__init__()
        self.config_artifact = os.environ.get('ES_EVENT_ARTIFACT', 'es-logger-data.json')

    def generate_events(self, esl):
        """
        Create the events to additionally push

        :param esl: The es-logger calling this plugin
        :type esl: object
        :returns: list(obj)
        """
        data = None
        artifact_saved = False
        for artifact in esl.build_info['artifacts']:
            if self.config_artifact == artifact['relativePath']:
                artifact_saved = True
                break
        if artifact_saved:
            try:
                raw_data = esl.server.get_build_artifact(
                    esl.es_job_name, esl.es_build_number, self.config_artifact)
                try:
                    data = json.loads(raw_data)
                except json.decoder.JSONDecodeError as err:
                    LOGGER.warn("JSONDecodeError when attempting to get {} artifact: {}".format(
                        self.config_artifact, err))
                    LOGGER.warn("Data: {}".format(raw_data))
            except jenkins.JenkinsException as jenkins_err:
                LOGGER.warn("JenkinsException when attempting to get {} artifact: {}".format(
                    self.config_artifact, jenkins_err))

        ret_data = []

        if data is None:
            LOGGER.info("No saved event data found in artifact {}".format(self.config_artifact))
        else:
            ret_data = data

        LOGGER.debug("Data: {}".format(ret_data))
        return ret_data
