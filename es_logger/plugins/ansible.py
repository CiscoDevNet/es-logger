# Copyright (c) 2018 Cisco Systems, Inc.
# All rights reserved.

__author__ = 'jonpsull'

import itertools
import json
import logging
import urllib
from ..interface import ConsoleLogEventRegex, EventGenerator
import re

LOGGER = logging.getLogger(__name__)


class AnsibleRecapEvent(EventGenerator):
    """
    """
    def __init__(self):
        super().__init__()

    def get_fields(self):
        return super().get_fields()

    def generate_events(self, esl):
        """
        Parse the console log and return a list for ES

        :param esl: The es_logger object being collected
        :returns: list(obj)
        """
        LOGGER.debug("Starting: {}".format(type(self).__name__))
        output_list = []
        # Find the play, e.g.: PLAY [Play name or hosts] **...**
        # Find the recap start, e.g.: PLAY RECAP **...**
        # Find the recap end, e.g.: Total --...-- 1861.60s (31 min 2 sec)
        recap_regex = re.compile(
                r'PLAY\s*\[(?P<play>.*)\]\s*\**\s*\n' +    # Group 1 matches the play name
                r'(?:.*\n(?!.*PLAY RECAP))*?' +            # Discard lines to 1st recap (non-greedy)
                r'\s*PLAY RECAP \**\s*\n' +                # Match the recap start
                r'(?P<hosts>(?:[^\s].*\n)*)' +             # Match all host lines
                r'(?:\s*\n)*' +                            # Blank lines
                r'(?P<tasks>(?:TASK:\s*.*\n)*)' +          # These are individual timings
                r'(?:\s*\n)*' +                            # Blank lines
                r'Total\s*[-]*\s*(?P<total>[^\s]*)s.*\n',  # Total time
                re.MULTILINE)
        # Find the play, e.g.: PLAY [Play name or hosts] **...**
        # Find the recap start, e.g.: PLAY RECAP **...**
        # Find the recap end, which is finished with all tasks recapped
        profile_regex = re.compile(
                r'PLAY\s*\[(?P<play>.*)\]\s*\**\s*\n' +            # Group 1 matches the play name
                r'(?:.*\n(?!.*PLAY RECAP))*?' +                    # Discard lines to 1st recap
                r'\s*PLAY RECAP \**\s*\n' +                        # Match the recap start
                r'(?P<hosts>(?:.*\n(?!.*PLAY RECAP))*?)' +         # Match all host lines,
                                                                   #    and not a recap
                r'(?:\s*\n)+' +                                    # Blank lines
                r'.*?\s+(?P<total>[^\s]+)\s+\*+\s*\n' +            # Match total time
                r'\s*={79}\s*\n' +                                 # Separator
                r'(?P<tasks>(?:(?:.*\s:\s)?.*\s[0-9.]+s\s*\n)*)',  # These are individual timings
                re.MULTILINE)
        # Task output matcher, get a description and a timing from, e.g.:
        #  ssh-tunnel : Create the ssh-tunnel -...- 6.21s (not verified)
        task_regex = re.compile(r'\s*(?P<task>.*?)\s+[-]*\s+(?P<time>[0-9.]+)s.*?\n', re.MULTILINE)
        host_regex = re.compile(r'\s*(?P<host>[^\s]*)\s*:\s*(?P<status>.*?)\s*\n', re.MULTILINE)

        # Using coloured output can lead to ANSI escapes buried in the string
        ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
        console_no_ansi = ansi_escape.sub('', esl.console_log)

        for recap_match in itertools.chain(recap_regex.finditer(console_no_ansi),
                                           profile_regex.finditer(console_no_ansi)):
            play = recap_match.group('play')
            if ':' in recap_match.group('total'):
                parts = recap_match.group('total').split(':')
                total_time = float(int(parts[-3]) * 60 * 60 +
                                   int(parts[-2]) * 60 +
                                   float(parts[-1]))
            else:
                total_time = float(recap_match.group('total'))
            # Process individual hosts
            for host_match in host_regex.finditer(recap_match.group('hosts')):
                add_event = {}
                add_event['play'] = play
                add_event['host'] = host_match.group('host')
                for status in host_match.group('status').split():
                    try:
                        string, count = status.split('=')
                        add_event[string] = int(count)
                    except ValueError as e:
                        LOGGER.error("Bad status match in hosts:\n{}".format(
                                     recap_match.group('hosts')))
                        raise(e)
                output_list.append(add_event)
            # Process individual tasks
            for task_match in task_regex.finditer(recap_match.group('tasks')):
                time = float(task_match.group('time'))
                add_event = {}
                add_event['play'] = play
                # Add the total play time
                add_event['total'] = total_time
                add_event['time_percentage'] = (time / total_time) * 100
                add_event['description'] = task_match.group('task')
                add_event['time'] = time
                output_list.append(add_event)
        LOGGER.debug("Finished: {}".format(type(self).__name__))
        # Return the data
        return output_list


class AnsibleFatalGenerator(EventGenerator):
    """
    Process the ansible play output for any lines beginning "fatal"
    """

    def get_fields(self):
        return super(AnsibleFatalGenerator, self).get_fields()

    def generate_events(self, esl):
        """
        Parse the console log and return a list for ES

        :param esl: The es_logger object being collected
        :returns: list(obj)
        """
        LOGGER.debug("Starting: {}".format(type(self).__name__))
        output_list = []
        # Log ansible fatal errors: e.g. fatal: [<host>]: FAILED! => <json_status>
        fatal_regex = re.compile(
                r'^fatal:\s*\[(?P<hostname>\S+)\]:\s*' +    # Group 1 matches the hostname
                r'(?P<type>FAILED|UNREACHABLE)!\s*=>\s*' +  # precursor to json status element
                r'(?P<error>{.*?})\s*$',                    # json status to parse in to end of line
                re.MULTILINE | re.DOTALL)
        for fatal_match in fatal_regex.finditer(esl.console_log):
            add_event = {}
            add_event['hostname'] = fatal_match.group('hostname')
            add_event['type'] = fatal_match.group('type')
            try:
                add_event['data'] = json.loads(urllib.parse.quote(fatal_match.group('error'),
                                                                  '":{} ,'))
            except json.decoder.JSONDecodeError:
                add_event['bad_data'] = fatal_match.group('error')
            output_list.append(add_event)
        LOGGER.debug("Finished: {}".format(type(self).__name__))
        # Return the data
        return output_list


class AnsibleConsoleLogRegex(ConsoleLogEventRegex):
    """
    """
    def get_regex(regex_list):
        """
        Ansible warnings and deprecations
        """
        regex_list.append(("ansible warning", re.compile(
            r"^\[WARNING\]:\s*(?P<warning_text>(?:.*?\n)+?)(?=^\[.*|\s*\n)",
            re.MULTILINE)))

        regex_list.append(("ansible deprecation", re.compile(
            r"^\[DEPRECATION WARNING\]:\s*(?P<deprecation_text>(?:.*?\n)+?)(?=^\[.*|\s*\n)",
            re.MULTILINE)))

        return regex_list
