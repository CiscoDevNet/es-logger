# Copyright (c) 2018 Cisco Systems, Inc.
# All rights reserved.

__author__ = 'jonpsull'

from ..interface import EventTarget
import logging
import os
import requests

LOGGER = logging.getLogger(__name__)


class LogstashTarget(EventTarget):
    """
    """
    def __init__(self):
        super().__init__()

        self.logstash_server = None
        self.ls_user = None
        self.ls_password = None
        self.ls_session = None

        # Where to send the json event
        self.logstash_server = self.get_logstash_server()
        self.ls_user = self.get_ls_user()
        self.ls_password = self.get_ls_password()

    @staticmethod
    def get_help_string():
        return '''
Logstash Target Environment Variables:
    LOGSTASH_SERVER         The server to send events to
    LS_USER                 The user for logstash access
    LS_PASSWORD             The password for logstash access
'''

    def validate(self):
        return True

    # Post to ES
    def send_event(self, json_event):
        session = self.get_session()
        r = session.post(self.logstash_server, json=json_event)
        LOGGER.debug("Posted event, result {}".format(r.ok))
        if r.ok:
            return 0
        return 1

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

    def get_session(self):
        if self.ls_session is None:
            LOGGER.debug("Creating session against {}".format(self.logstash_server))
            self.ls_session = requests.Session()
            self.ls_session.auth = (self.ls_user, self.ls_password)
        return self.ls_session
