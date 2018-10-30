# Copyright (c) 2018 Cisco Systems, Inc.
# All rights reserved.

__author__ = 'jonpsull'

import itertools
import logging
from ..interface import EventGenerator
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
                r'PLAY\s*\[(?P<play>.*)\]\s*\**\s*\n' +     # Group 1 matches the play name
                r'(?:.*\n(?!.*PLAY RECAP))*?' +             # Discard lines to 1st recap
                r'\s*PLAY RECAP \**\s*\n' +                 # Match the recap start
                r'(?P<hosts>(?:.*\n(?!.*PLAY RECAP))*?)' +  # Match all host lines, and not a recap
                r'(?:\s*\n)+' +                             # Blank lines
                r'.*?\s+(?P<total>[^\s]+)\s+\*+\s*\n' +     # Match total time
                r'\s*={79}\s*\n' +                          # Separator
                r'(?P<tasks>(?:(?:.*\s:\s)?.*---.*\n)*)',   # These are individual timings
                re.MULTILINE)
        # Task output matcher, get a description and a timing from, e.g.:
        #  ssh-tunnel : Create the ssh-tunnel -...- 6.21s (not verified)
        task_regex = re.compile(r'\s*(?P<task>.*?)\s+[-]{2,}\s+(?P<time>\S*)s.*?\n', re.MULTILINE)
        host_regex = re.compile(r'\s*(?P<host>[^\s]*)\s*:\s*(?P<status>.*?)\s*\n', re.MULTILINE)

        for recap_match in itertools.chain(recap_regex.finditer(esl.console_log),
                                           profile_regex.finditer(esl.console_log)):
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
                    string, count = status.split('=')
                    add_event[string] = int(count)
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
