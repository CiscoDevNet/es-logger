__author__ = 'jonpsull'

from ..interface import EventGenerator
import logging

LOGGER = logging.getLogger(__name__)


class JUnitEvent(EventGenerator):
    """
    Process the junit output
    """
    def get_fields(self):
        return super(JUnitEvent, self).get_fields() + ['GERRIT_PATCHSET_REVISION',
                                                       'GERRIT_REFSPEC']

    def generate_events(self, esl):
        """
        return a list of objects to send as events

        :param esl: the calling es_logger object
        :type console_log: object
        :returns: list(dict(str:?))
        """
        LOGGER.debug("Starting: {}".format(type(self).__name__))
        output_list = []

        # Get the test report from Jenkins (if not already cached)
        test_report = esl.get_test_report()
        if test_report is not None:
            # Annotate the return with extra info
            test_report['type'] = 'total'
            test_report['totalCount'] = test_report['failCount'] +\
                test_report['skipCount'] + test_report['passCount']

            # Remove the suites, and process them as individual events
            test_suites = test_report.pop("suites")
            # Iterate and add 1 event per suite
            for suite in test_suites:
                test_cases = suite.pop("cases")
                suite_name = suite['name']
                suite_pass = 0
                suite_skip = 0
                suite_fail = 0
                suite_unknown = 0
                # Iterate and add 1 event per case
                for case in test_cases:
                    case['suite'] = suite_name
                    if case['status'] == 'PASSED':
                        suite_pass += 1
                    elif case['status'] == 'SKIPPED':
                        suite_skip += 1
                    elif case['status'] == 'FAILED':
                        suite_fail += 1
                    else:
                        suite_unknown += 1
                    case['type'] = 'case'
                    if 'errorDetails' in case.keys():
                        if case['errorDetails'] is not None:
                            case['errorDetailsTruncated'] = case['errorDetails'][:255]
                        else:
                            case['errorDetailsTruncated'] = None
                    output_list.append(case)
                suite['passCount'] = suite_pass
                suite['skipCount'] = suite_skip
                suite['failCount'] = suite_fail
                suite['unknownCount'] = suite_unknown
                suite['totalCount'] = suite_pass + suite_skip + suite_fail + suite_unknown
                suite['type'] = 'suite'
                output_list.append(suite)

            # Add our overall result as an event
            output_list.append(test_report)
        LOGGER.debug("Finished: {}".format(type(self).__name__))
        return output_list
