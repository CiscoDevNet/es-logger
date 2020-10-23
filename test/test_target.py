# Copyright (c) 2018 Cisco Systems, Inc.
# All rights reserved.

__author__ = 'jonpsull'

from es_logger.plugins.target import LogstashPostError, LogstashTarget, SqsTarget
import json
import nose
import os
import requests
import unittest.mock


class TestLogstashTarget(object):

    def setup(self):
        self.lt = LogstashTarget()

    @unittest.mock.patch.dict('os.environ', {'LOGSTASH_SERVER': "https://example.com",
                                             'LS_USER': 'user',
                                             'LS_PASSWORD': 'pass'})
    def test_LogstashTarget(self):
        lt = LogstashTarget()
        nose.tools.ok_(lt.get_logstash_server() == os.getenv('LOGSTASH_SERVER'))
        nose.tools.ok_(lt.get_ls_user() == os.getenv('LS_USER'))
        nose.tools.ok_(lt.get_ls_password() == os.getenv('LS_PASSWORD'))

    @unittest.mock.patch('requests.Session')
    def test_get_session(self, mock_session):
        self.lt.get_session()
        print(mock_session.mock_calls)
        nose.tools.ok_(self.lt.ls_session is not None,
                       "Session is None: {}".format(self.lt.ls_session))

    @unittest.mock.patch('requests.Session')
    def test_send_event_good(self, mock_session):
        mock_session().post().ok = True
        res = self.lt.send_event({"event": "event"})
        nose.tools.ok_(res == 0,
                       "res not 0: {}".format(res))

    @unittest.mock.patch('requests.Session')
    def test_send_event_bad(self, mock_session):
        mock_session().post().ok = False
        res = self.lt.send_event({"event": "event"})
        nose.tools.ok_(res == 1,
                       "res not 1: {}".format(res))

    @unittest.mock.patch('requests.Session')
    def test_send_event_bad_session(self, mock_session):
        mock_session().post.side_effect = requests.exceptions.ReadTimeout
        self.lt.timeout_sleep = 0
        nose.tools.assert_raises(LogstashPostError, self.lt.send_event, {"event": "event"})
        # We should see this created and called 5 times attempting to get post finished
        calls = [unittest.mock.call(),
                 unittest.mock.call(),
                 unittest.mock.call().post(None, json={'event': 'event'}),
                 unittest.mock.call(),
                 unittest.mock.call().post(None, json={'event': 'event'}),
                 unittest.mock.call(),
                 unittest.mock.call().post(None, json={'event': 'event'}),
                 unittest.mock.call(),
                 unittest.mock.call().post(None, json={'event': 'event'}),
                 unittest.mock.call(),
                 unittest.mock.call().post(None, json={'event': 'event'})]
        print(mock_session.mock_calls)
        nose.tools.ok_(mock_session.mock_calls == calls)

    @unittest.mock.patch('requests.Session')
    def test_send_event_bad_post(self, mock_session):
        mock_session().post.side_effect = Exception
        self.lt.timeout_sleep = 0
        nose.tools.assert_raises(LogstashPostError, self.lt.send_event, {"event": "event"})

    def test_validate(self):
        ret = self.lt.validate()
        nose.tools.ok_(ret, "Validate must return True")

    def test_get_required_vars(self):
        ret = self.lt.get_required_vars()
        expected = ['LOGSTASH_SERVER', 'LS_USER', 'LS_PASSWORD']
        nose.tools.assert_equal(ret, expected, "{} doesn't match expected {}".format(ret, expected))


class TestSqsTarget(object):

    def setup(self):
        self.sqst = SqsTarget()

    def mock_do_send_good(self):
        self.sqst.data = []
        return 0

    def mock_do_send_bad(self):
        self.sqst.data = []
        return 3

    @unittest.mock.patch.dict('os.environ', {'SQS_QUEUE': "https://example.com"})
    def test_SqsTarget(self):
        sqs = SqsTarget()
        nose.tools.ok_(sqs.get_sqs_queue() == os.getenv('SQS_QUEUE'))

    @unittest.mock.patch('boto3.client')
    def test_get_sqs(self, mock_sqs_client):
        sqs = self.sqst.get_sqs()
        nose.tools.ok_(self.sqst.client == sqs)

    def test_send_event(self):
        self.sqst.orig_do_send = self.sqst.do_send
        self.sqst.do_send = unittest.mock.MagicMock()
        events = [{"event": 1}, {"event": 2}, {"event": 3}, {"event": 4}, {"event": 5},
                  {"event": 6}, {"event": 7}, {"event": 8}, {"event": 9}, {"event": 10}]
        for event in events:
            result = self.sqst.send_event(event)
            nose.tools.assert_equal(result, 0, "Return not equal to 0 for {}: {}".format(
                                    event, result))
        nose.tools.assert_equal(self.sqst.do_send.mock_calls, [],
                                "do_send called when it shouldn't be: {}".format(
                                self.sqst.do_send.mock_calls))
        print(self.sqst.data)
        expected_data = [{'MessageBody': '{"event": 1}',
                          'MessageAttributes': {'source': {'StringValue': 'es-logger',
                                                           'DataType': 'String'}},
                          'MessageDeduplicationId':
                              'db9d431fd703ff540c26ed0c90f3444c21c85e93fc85df615db1d1ee6ba807f0',
                          'MessageGroupId': 'es-logger',
                          'Id': '0'},
                         {'MessageBody': '{"event": 2}',
                          'MessageAttributes': {'source': {'StringValue': 'es-logger',
                                                           'DataType': 'String'}},
                          'MessageDeduplicationId':
                              'f2b0633851943e3867218dd90bffd435b780ba394d9ad79077eaa864c333034d',
                          'MessageGroupId': 'es-logger',
                          'Id': '1'},
                         {'MessageBody': '{"event": 3}',
                          'MessageAttributes': {'source': {'StringValue': 'es-logger',
                                                           'DataType': 'String'}},
                          'MessageDeduplicationId':
                              '3dfa501bc277b68b1a729c89ca0087dc8a96ad58247118cc8ca6b2e205db9551',
                          'MessageGroupId': 'es-logger',
                          'Id': '2'},
                         {'MessageBody': '{"event": 4}',
                          'MessageAttributes': {'source': {'StringValue': 'es-logger',
                                                           'DataType': 'String'}},
                          'MessageDeduplicationId':
                              '1595a52c83823adf955d2277549fc8e11ea3c472949e371ebaf195808d35f389',
                          'MessageGroupId': 'es-logger',
                          'Id': '3'},
                         {'MessageBody': '{"event": 5}',
                          'MessageAttributes': {'source': {'StringValue': 'es-logger',
                                                           'DataType': 'String'}},
                          'MessageDeduplicationId':
                              'a6e4d2e4e268b24dbd00ee31e06e42a8480e74a413975728f5f2172e2af0ec93',
                          'MessageGroupId': 'es-logger',
                          'Id': '4'},
                         {'MessageBody': '{"event": 6}',
                          'MessageAttributes': {'source': {'StringValue': 'es-logger',
                                                           'DataType': 'String'}},
                          'MessageDeduplicationId':
                              'f79b992a4a3eaaa120df50f6f03d98958fc8b657c25d21001c29b397daa779da',
                          'MessageGroupId': 'es-logger',
                          'Id': '5'},
                         {'MessageBody': '{"event": 7}',
                          'MessageAttributes': {'source': {'StringValue': 'es-logger',
                                                           'DataType': 'String'}},
                          'MessageDeduplicationId':
                              'efc806a2000faf8653cb98474da4bebed89a889854713374cd4171270592d759',
                          'MessageGroupId': 'es-logger',
                          'Id': '6'},
                         {'MessageBody': '{"event": 8}',
                          'MessageAttributes': {'source': {'StringValue': 'es-logger',
                                                           'DataType': 'String'}},
                          'MessageDeduplicationId':
                              '205bbcb226fa3827e735d8f8c12a7762a720edfb85563b483a6f28b1ca14e2b5',
                          'MessageGroupId': 'es-logger',
                          'Id': '7'},
                         {'MessageBody': '{"event": 9}',
                          'MessageAttributes': {'source': {'StringValue': 'es-logger',
                                                           'DataType': 'String'}},
                          'MessageDeduplicationId':
                              '0bfb313fb0ead16bcab13b4d6e7dc96f9685477c4e563b7ccd0cb28284e1e315',
                          'MessageGroupId': 'es-logger',
                          'Id': '8'},
                         {'MessageBody': '{"event": 10}',
                          'MessageAttributes': {'source': {'StringValue': 'es-logger',
                                                           'DataType': 'String'}},
                          'MessageDeduplicationId':
                              '3fa39e05fa189f6e25bed9401f9114fe2632c88444617bcae0b816c5cda510ba',
                          'MessageGroupId': 'es-logger',
                          'Id': '9'}]
        nose.tools.assert_equal(self.sqst.data, expected_data)

    def test_send_event_multiple(self):
        self.test_send_event()
        self.sqst.do_send.side_effect = self.mock_do_send_good

        event = {"event": 11}
        result = self.sqst.send_event(event)
        nose.tools.assert_equal(result, 0, "Return not equal to 0 for {}: {}".format(
                                event, result))
        nose.tools.assert_equal(self.sqst.do_send.mock_calls, [unittest.mock.call()],
                                "do_send not called when it should be: {}".format(
                                self.sqst.do_send.mock_calls))
        expected_data = [{'Id': '0',
                          'MessageAttributes': {'source': {'DataType': 'String',
                                                           'StringValue': 'es-logger'}},
                          'MessageBody': '{"event": 11}',
                          'MessageDeduplicationId':
                              'fa1ae522b46f3c4e653294e00e46a478c359e9c670018f87923187d9907f3191',
                          'MessageGroupId': 'es-logger'}]
        nose.tools.assert_equal(self.sqst.data, expected_data)

    def test_large_send_event(self):
        event = {"large_event": "x" * 256 * 1024}
        print("Event size is: {}".format(len(json.dumps(event))))
        with nose.tools.assert_logs(level='DEBUG') as cm:
            result = self.sqst.send_event(event)
        nose.tools.assert_equal(result, 1, "Return not equal to 0 for {}: {}".format(
                                event, result))
        nose.tools.assert_equal(cm.output,
                                ['WARNING:es_logger.plugins.target:Message too big: 262396'])

    def test_validate(self):
        ret = self.sqst.validate()
        nose.tools.ok_(ret, "Validate must return True")

    def test_get_required_vars(self):
        ret = self.sqst.get_required_vars()
        expected = ['SQS_QUEUE']
        nose.tools.assert_equal(ret, expected, "{} doesn't match expected {}".format(ret, expected))

    # Tested via test_finish_send()
    def test_do_send(self):
        pass

    def generate_good_response(self, entry):
        return {'Id': entry['Id'],
                'MessageId': entry['Id'],
                'MD5OfMessageBody': 'MessageBodyMD5',
                'MD5OfMessageAttributes': 'MessageAttributesMD5',
                'MD5OfMessageSystemAttributes': 'MessageSystemAttributesMD5',
                'SequenceNumber': entry['Id']}

    def generate_bad_response(self, entry):
        return {'Id': entry['Id'],
                'SenderFault': False,
                'Code': 'code',
                'Message': 'message'}

    def send_message_batch_good(self, QueueUrl, Entries):
        success = []
        for entry in Entries:
            success.append(self.generate_good_response(entry))
        return {'Successful': success}

    def send_message_batch_bad(self, QueueUrl, Entries):
        fail = []
        for entry in Entries:
            fail.append(self.generate_bad_response(entry))
        return {'Failed': fail}

    def test_finish_send(self):
        self.test_send_event()
        self.sqst.do_send = self.sqst.orig_do_send
        sqs_client_mock = unittest.mock.MagicMock()
        sqs_client_mock.send_message_batch = self.send_message_batch_good
        self.sqst.get_sqs = lambda: sqs_client_mock
        self.sqst.sqs_queue = 'http://sqs.dummy_queue.fifo'
        with nose.tools.assert_logs(level='DEBUG') as cm:
            ret = self.sqst.finish_send()
        nose.tools.assert_equal(sqs_client_mock.mock_calls, [])
        nose.tools.ok_(ret == 0, "Return not 0: {}".format(ret))
        nose.tools.ok_(len(self.sqst.data) == 0, "data queue not 0: {}".format(len(self.sqst.data)))
        print(cm.output)
        nose.tools.assert_equal(
            cm.output,
            ['DEBUG:es_logger.plugins.target:Sending 10 events to http://sqs.dummy_queue.fifo',
             "DEBUG:es_logger.plugins.target:Response: "
             + "{'Successful': ["
             + "{'Id': '0', 'MessageId': '0', 'MD5OfMessageBody': 'MessageBodyMD5', "
             + "'MD5OfMessageAttributes': 'MessageAttributesMD5', 'MD5OfMessageSystemAttributes': "
             + "'MessageSystemAttributesMD5', 'SequenceNumber': '0'}, "
             + "{'Id': '1', 'MessageId': '1', 'MD5OfMessageBody': 'MessageBodyMD5', "
             + "'MD5OfMessageAttributes': 'MessageAttributesMD5', 'MD5OfMessageSystemAttributes': "
             + "'MessageSystemAttributesMD5', 'SequenceNumber': '1'}, "
             + "{'Id': '2', 'MessageId': '2', 'MD5OfMessageBody': 'MessageBodyMD5', "
             + "'MD5OfMessageAttributes': 'MessageAttributesMD5', 'MD5OfMessageSystemAttributes': "
             + "'MessageSystemAttributesMD5', 'SequenceNumber': '2'}, "
             + "{'Id': '3', 'MessageId': '3', 'MD5OfMessageBody': 'MessageBodyMD5', "
             + "'MD5OfMessageAttributes': 'MessageAttributesMD5', 'MD5OfMessageSystemAttributes': "
             + "'MessageSystemAttributesMD5', 'SequenceNumber': '3'}, "
             + "{'Id': '4', 'MessageId': '4', 'MD5OfMessageBody': 'MessageBodyMD5', "
             + "'MD5OfMessageAttributes': 'MessageAttributesMD5', 'MD5OfMessageSystemAttributes': "
             + "'MessageSystemAttributesMD5', 'SequenceNumber': '4'}, "
             + "{'Id': '5', 'MessageId': '5', 'MD5OfMessageBody': 'MessageBodyMD5', "
             + "'MD5OfMessageAttributes': 'MessageAttributesMD5', 'MD5OfMessageSystemAttributes': "
             + "'MessageSystemAttributesMD5', 'SequenceNumber': '5'}, "
             + "{'Id': '6', 'MessageId': '6', 'MD5OfMessageBody': 'MessageBodyMD5', "
             + "'MD5OfMessageAttributes': 'MessageAttributesMD5', 'MD5OfMessageSystemAttributes': "
             + "'MessageSystemAttributesMD5', 'SequenceNumber': '6'}, "
             + "{'Id': '7', 'MessageId': '7', 'MD5OfMessageBody': 'MessageBodyMD5', "
             + "'MD5OfMessageAttributes': 'MessageAttributesMD5', 'MD5OfMessageSystemAttributes': "
             + "'MessageSystemAttributesMD5', 'SequenceNumber': '7'}, "
             + "{'Id': '8', 'MessageId': '8', 'MD5OfMessageBody': 'MessageBodyMD5', "
             + "'MD5OfMessageAttributes': 'MessageAttributesMD5', 'MD5OfMessageSystemAttributes': "
             + "'MessageSystemAttributesMD5', 'SequenceNumber': '8'}, "
             + "{'Id': '9', 'MessageId': '9', 'MD5OfMessageBody': 'MessageBodyMD5', "
             + "'MD5OfMessageAttributes': 'MessageAttributesMD5', 'MD5OfMessageSystemAttributes': "
             + "'MessageSystemAttributesMD5', 'SequenceNumber': '9'}"
             + "]}",
             'DEBUG:es_logger.plugins.target:Added record 0 as sequence number 0',
             'DEBUG:es_logger.plugins.target:Added record 1 as sequence number 1',
             'DEBUG:es_logger.plugins.target:Added record 2 as sequence number 2',
             'DEBUG:es_logger.plugins.target:Added record 3 as sequence number 3',
             'DEBUG:es_logger.plugins.target:Added record 4 as sequence number 4',
             'DEBUG:es_logger.plugins.target:Added record 5 as sequence number 5',
             'DEBUG:es_logger.plugins.target:Added record 6 as sequence number 6',
             'DEBUG:es_logger.plugins.target:Added record 7 as sequence number 7',
             'DEBUG:es_logger.plugins.target:Added record 8 as sequence number 8',
             'DEBUG:es_logger.plugins.target:Added record 9 as sequence number 9'])

    def test_finish_send_bad(self):
        self.test_send_event()
        self.sqst.do_send = self.sqst.orig_do_send
        sqs_client_mock = unittest.mock.MagicMock()
        sqs_client_mock.send_message_batch = self.send_message_batch_bad
        self.sqst.get_sqs = lambda: sqs_client_mock
        self.sqst.sqs_queue = 'http://sqs.dummy_queue.fifo'
        with nose.tools.assert_logs(level='DEBUG') as cm:
            ret = self.sqst.finish_send()
        nose.tools.assert_equal(sqs_client_mock.mock_calls, [])
        nose.tools.ok_(ret == 10, "Return not 10: {}".format(ret))
        nose.tools.ok_(len(self.sqst.data) == 0, "data queue not 0: {}".format(len(self.sqst.data)))
        print(cm.output)
        nose.tools.assert_equal(
            cm.output,
            ['DEBUG:es_logger.plugins.target:Sending 10 events to http://sqs.dummy_queue.fifo',
             "DEBUG:es_logger.plugins.target:Response: "
             + "{'Failed': ["
             + "{'Id': '0', 'SenderFault': False, 'Code': 'code', 'Message': 'message'}, "
             + "{'Id': '1', 'SenderFault': False, 'Code': 'code', 'Message': 'message'}, "
             + "{'Id': '2', 'SenderFault': False, 'Code': 'code', 'Message': 'message'}, "
             + "{'Id': '3', 'SenderFault': False, 'Code': 'code', 'Message': 'message'}, "
             + "{'Id': '4', 'SenderFault': False, 'Code': 'code', 'Message': 'message'}, "
             + "{'Id': '5', 'SenderFault': False, 'Code': 'code', 'Message': 'message'}, "
             + "{'Id': '6', 'SenderFault': False, 'Code': 'code', 'Message': 'message'}, "
             + "{'Id': '7', 'SenderFault': False, 'Code': 'code', 'Message': 'message'}, "
             + "{'Id': '8', 'SenderFault': False, 'Code': 'code', 'Message': 'message'}, "
             + "{'Id': '9', 'SenderFault': False, 'Code': 'code', 'Message': 'message'}]}",
             'WARNING:es_logger.plugins.target:Error on record 0 code code message message '
             + 'SenderFault False',
             'WARNING:es_logger.plugins.target:Error on record 1 code code message message '
             + 'SenderFault False',
             'WARNING:es_logger.plugins.target:Error on record 2 code code message message '
             + 'SenderFault False',
             'WARNING:es_logger.plugins.target:Error on record 3 code code message message '
             + 'SenderFault False',
             'WARNING:es_logger.plugins.target:Error on record 4 code code message message '
             + 'SenderFault False',
             'WARNING:es_logger.plugins.target:Error on record 5 code code message message '
             + 'SenderFault False',
             'WARNING:es_logger.plugins.target:Error on record 6 code code message message '
             + 'SenderFault False',
             'WARNING:es_logger.plugins.target:Error on record 7 code code message message '
             + 'SenderFault False',
             'WARNING:es_logger.plugins.target:Error on record 8 code code message message '
             + 'SenderFault False',
             'WARNING:es_logger.plugins.target:Error on record 9 code code message message '
             + 'SenderFault False',
             'WARNING:es_logger.plugins.target:Total 10 errors in do_send()'])
