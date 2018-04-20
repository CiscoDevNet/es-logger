# Copyright (c) 2018 Cisco Systems, Inc.
# All rights reserved.

__author__ = 'jonpsull'

from ..interface import EventGenerator


class CommitEvent(EventGenerator):
    """
    """
    def __init__(self):
        super().__init__()

    def get_fields(self):
        return super().get_fields()

    def generate_events(self, esl):
        # Prep the event info if there are change sets
        add_events = []
        parse_events = []
        # Process the change sets and create events for each - pipeline job
        for change_set in esl.build_info.get('changeSets', []):
            parse_events += change_set['items']
        if 'changeSet' in esl.build_info:
            parse_events += esl.build_info['changeSet']['items']

        for change_item in parse_events:
            new_event = {'changeSet': change_item}
            new_event['build_data'] = esl.es_info.get('build_data')
            # If the date is in a bad format, modify it
            if 'date' in new_event['changeSet'].keys() and \
                    ' ' in new_event['changeSet']['date']:
                parts = new_event['changeSet']['date'].split()
                new_event['changeSet']['date'] = parts[0] + 'T' + parts[1] + parts[2]
            add_events.append(new_event)
        return add_events
