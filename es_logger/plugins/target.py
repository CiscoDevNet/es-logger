# Copyright (c) 2018 Cisco Systems, Inc.
# All rights reserved.

__author__ = 'jonpsull'

from ..interface import EventTarget
import boto3
import hashlib
import json
import logging
import os
import requests
import time
import urllib3.exceptions

LOGGER = logging.getLogger(__name__)


class LogstashPostError(Exception):
    pass


class LogstashTarget(EventTarget):
    """
    """
    def __init__(self):
        super().__init__()

        self.logstash_server = None
        self.ls_user = None
        self.ls_password = None
        self.ls_session = None

        self.timeout_sleep = 2

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

    @staticmethod
    def get_required_vars():
        return ['LOGSTASH_SERVER', 'LS_USER', 'LS_PASSWORD']

    def validate(self):
        return True

    # Post to ES
    def send_event(self, json_event):
        # We see a lot of logstash timeout errors
        post_attempts = []
        r = None
        # If we successfully post, r becomes the response
        while r is None:
            try:
                session = self.get_session()
                r = session.post(self.logstash_server, json=json_event)
            except (requests.exceptions.ReadTimeout, urllib3.exceptions.ProtocolError) as exc:
                post_attempts.append(exc)
                LOGGER.warn("Setting session to None on post_attempt {}".format(
                            len(post_attempts)))
                self.ls_session = None
                if len(post_attempts) >= 5:
                    raise LogstashPostError(
                        "Logstash post errors {}".format(post_attempts)) from exc
                time.sleep(self.timeout_sleep)
            except Exception as exc:
                raise LogstashPostError(
                    "Logstash post error on attempt {}".format(post_attempts)) from exc
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


class SqsPostError(Exception):
    pass


class SqsTarget(EventTarget):
    """
    """
    def __init__(self):
        super().__init__()
        self.client = None
        self.data = []
        self.error_count = 0
        # boto3 SQS limits are 256KB per message, and per batch, and max 10 messages per batch
        self.message_count_limit = 10
        self.message_limit = 256 * 1024  # 256KB
        self.sqs_queue = None
        self.timeout_sleep = 2

    @staticmethod
    def get_help_string():
        return '''
AWS SQS Target Environment Variables:
    Credentials:
        Uses boto3, so ensure you have credentials set appropriately
        See: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html

    SQS_QUEUE       Name of the queue to send the data into
'''

    @staticmethod
    def get_required_vars():
        return ['SQS_QUEUE']

    def validate(self):
        return True

    # Post to SQS
    def send_event(self, json_event):
        error_count = 0
        message_data = json.dumps(json_event)
        data_item = {
            'MessageBody': message_data,
            'MessageAttributes': {
                'source': {
                    'StringValue': 'es-logger',
                    'DataType': 'String'
                }
            },
            'MessageDeduplicationId': hashlib.sha256(message_data.encode('utf-8')).hexdigest(),
            'MessageGroupId': 'es-logger'
        }
        size = len(json.dumps(data_item))
        # 256Kb limit on message_data
        if size >= self.message_limit:
            LOGGER.warn("Message too big: {}".format(size))
            error_count = 1
        else:
            # 256Kb total limit on all messages
            total_size = len(json.dumps(self.data)) + size
            if total_size >= self.message_limit or len(self.data) == self.message_count_limit:
                LOGGER.debug("Sending max message size {} count {}".format(
                             total_size, len(self.data)))
                error_count = self.do_send()
            # The Ids of a batch request need to be unique within a request.
            data_item['Id'] = "{}".format(len(self.data))
            self.data.append(data_item)
        return error_count

    def finish_send(self):
        return self.do_send()

    def do_send(self):
        sqs_client = self.get_sqs()
        LOGGER.debug("Sending {} events to {}".format(len(self.data), self.get_sqs_queue()))
        response = sqs_client.send_message_batch(QueueUrl=self.get_sqs_queue(), Entries=self.data)
        LOGGER.debug("Response: {}".format(response))

        error_count = 0
        if 'Successful' in response.keys():
            for record in response['Successful']:
                LOGGER.debug("Added record {} as sequence number {}".format(
                    record['Id'], record['SequenceNumber']))
        if 'Failed' in response.keys():
            for record in response['Failed']:
                LOGGER.warn("Error on record {} code {} message {} SenderFault {}".format(
                    record['Id'], record['Code'], record['Message'], record['SenderFault']))
            error_count = len(response['Failed'])
        if error_count > 0:
            LOGGER.warn("Total {} errors in do_send()".format(error_count))
        self.data = []
        return error_count

    def get_sqs_queue(self):
        if self.sqs_queue is None:
            self.sqs_queue = os.environ.get('SQS_QUEUE')
        return self.sqs_queue

    def get_sqs(self):
        if self.client is None:
            self.client = boto3.client('sqs')
        return self.client
