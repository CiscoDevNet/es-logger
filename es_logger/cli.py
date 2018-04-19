#!/usr/bin/env python

# Copyright (c) 2018 Cisco Systems, Inc.
# All rights reserved.

__author__ = 'jonpsull'

import argparse
import es_logger
import logging
import sys


def parse_args():
    desc = '''
Read data from a completed Jenkins job and push it to a logstash instance.

Behaviour is controlled through a number of environment variables as follows:

What data to gather:
    PROCESS_CONSOLE_LOGS    Which ConsoleLogProcessor plugins to use in processing
    GATHER_BUILD_DATA       Which GatherBuildData plugins to use in processing
    GENERATE_EVENTS         Which EventGenerator plugins to use in processing

Where to gather data from:
    JENKINS_URL             The url to access Jenkins at
    JENKINS_USER            The username for Jenkins access
    JENKINS_PASSWORD        The password or API token for Jenkins access

What to gather data from:
    ES_JOB_NAME             The "Full Project Name" style job name for the job to process
    ES_BUILD_NUMBER         The build number for the job to process

Where to push the data:
    LOGSTASH_SERVER         The server to send events to
    LS_USER                 The user for logstash access
    LS_PASSWORD             The password for logstash access
'''

    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=desc)

    output = parser.add_mutually_exclusive_group()
    output.add_argument('--no-dump', action='store_true')
    output.add_argument('--no-post', action='store_true')

    parser.add_argument('-c', '--console-length', type=int, default=32500)
    parser.add_argument('-e', '--events-only', action='store_true')
    parser.add_argument('-p', '--list-plugins', action='store_true')

    parser.add_argument(
        '--debug', action='store_true', help='Print debug logs to console during execution')

    return parser.parse_args()


def configure_logging(args):
    if args.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logging.basicConfig(level=log_level,
                        format='%(asctime)s %(name)s %(levelname)s %(message)s')


def main():
    args = parse_args()
    configure_logging(args)

    esl = es_logger.EsLogger(console_length=args.console_length)
    if args.list_plugins:
        esl.list_plugins()
        sys.exit(0)

    esl.get_build_data()
    esl.get_events()

    status = 0
    # Loop over all of the events to send,
    # main job in es_info, then events generated from plugins
    process_events = [esl.es_info] if not args.events_only else []
    process_events += esl.events
    for e in process_events:
        if not args.no_dump:
            esl.dump(e)
        if not args.no_post:
            status += esl.post(e)

    sys.exit(status)
