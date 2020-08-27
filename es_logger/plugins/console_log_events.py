__author__ = 'jonpsull'

from es_logger.interface import ConsoleLogEventRegex
from es_logger.interface import EventGenerator
import json
import logging
import os
import re
from stevedore import driver, ExtensionManager

LOGGER = logging.getLogger(__name__)


class ConsoleLogEvent(EventGenerator):
    """
    Load regex's and scan the console log for matches, generating events
    """
    def get_fields(self):
        return super(ConsoleLogEvent, self).get_fields() + ['NODE_NAME', 'NODE_LABELS']

    def generate_events(self, esl):
        """
        Parse the console log and return a list to send as events

        :param console_log: A dictionary with string keys and simple types as
        :type console_log: str
        :returns: list(dict(str:?))
        """
        LOGGER.debug("Starting: {}".format(type(self).__name__))
        output_list = []
        regex_list = []

        """
        Load all console log plugins
        """
        mgr = ExtensionManager(namespace='es_logger.plugins.event_generator.console_log_events',
                               invoke_on_load=False)
        for plugin in mgr.names():  # All known console_log_events plugins
            drv = driver.DriverManager(
                namespace='es_logger.plugins.event_generator.console_log_events',
                invoke_on_load=False,
                name=plugin)
            regex_list = drv.driver.get_regex(regex_list)
            LOGGER.debug('Loaded plugins from {}, regex_list now with {} elements'.format(
                         plugin, len(regex_list)))

        """
        Look for a json file with additional regex's
        """
        regex_filename = 'console_log_event_regex.json'
        if os.path.isfile(regex_filename):
            LOGGER.debug("Loading console_log_regex's from {}".format(regex_filename))
            with open(regex_filename, 'r') as regex_file:
                regex_data = json.loads(regex_file)
                for regex in regex_data:
                    regex_list.append((regex['name'], re.compile(regex['pattern'], re.MULTILINE)))
        else:
            LOGGER.debug("{} not found, not loading additional console_log_event_regex's".format(
                         regex_filename))

        """
        Processing
        """
        for regex_name, run_regex in regex_list:
            LOGGER.debug("Starting regex: {}".format(regex_name))
            for regex_match in run_regex.finditer(esl.console_log):
                add_event = {
                            'name': regex_name,
                            'match': regex_match.group(0),
                            'named_matches': regex_match.groupdict()
                        }
                output_list.append(add_event)
            LOGGER.debug("Finished regex: {}".format(regex_name))

        LOGGER.debug("Finished: {}".format(type(self).__name__))
        # Return the data
        return output_list


class EsLoggerConsoleLogRegex(ConsoleLogEventRegex):
    """
    """
    def get_regex(regex_list):
        """
        Pipeline job information
        """
        # Collect agent information for this job
        regex_list.append(("jenkins agent", re.compile(
            r"Running on (?P<jenkins_agent>.*?) in (?P<workspace>/.*?)\s*\n+",
            re.MULTILINE)))

        # Collect stopwatch results
        regex_list.append(("stopwatch", re.compile(
            r"stopwatch - name:(?P<name>.*?), elapsedTime:(?P<elapsed_time>.*?), "
            r"startTime:(?P<start_time>.*?), endTime:(?P<end_time>.*?), "
            r"status:(?P<status>.*?)\s*\n+",
            re.MULTILINE)))

        """
        Docker errors
        """
        # Generic error - should pick all docker errors, would be great to auto-classify somehow
        regex_list.append(("docker error", re.compile(
            r"Error response from daemon:(?P<docker_error>.*?)\n+",
            re.MULTILINE)))

        # Registry issue
        regex_list.append(("docker blob error", re.compile(
            r"\n(?P<preceding>.*?)\n^(?P<blob>.*unknown blob.*)$",
            re.MULTILINE)))

        # Registry issue
        regex_list.append(("docker timeout", re.compile(
            r"Error response from daemon:(?P<err>.*?)net/http: request canceled " +
            r"\(Client\.Timeout exceeded while awaiting headers\)",
            re.MULTILINE)))

        # Registry issue
        regex_list.append(("docker missing signature", re.compile(
            r"Error response from daemon: missing signature key",
            re.MULTILINE)))

        # Registry issue
        regex_list.append(("docker image not found", re.compile(
            r"Pulling repository (?P<docker_repository>\S+)\n" +
            r"Error: image (?P<docker_image>\S+) not found",
            re.MULTILINE)))

        # Might be replaced by the multiline match, above
        # Registry issue
        regex_list.append(("docker image not found", re.compile(
            r"Error: image (?P<image>\S+) not found",
            re.MULTILINE)))

        # Registry issue
        regex_list.append(("docker pull error", re.compile(
            r"Error pulling image \((?P<docker_tag>\S+)\) from (?P<docker_registry>\S+), " +
            r"endpoint: (?P<docker_endpoint>\S+), (?P<error>.*?)\n",
            re.MULTILINE)))

        # Registry issue
        regex_list.append(("docker pull error", re.compile(
            r"Please login prior to pull:(?:\s*?\n*)*?" +
            r"Error: Cannot perform an interactive login from a non TTY device",
            re.MULTILINE)))

        # Registry issue
        regex_list.append(("http_status", re.compile(
            r"received unexpected HTTP status:(?P<http_status>.*?)\n+",
            re.MULTILINE)))

        # Client/agent issue
        regex_list.append(("thin pool full", re.compile(
            r"devmapper: Thin Pool has [0-9]+ free data blocks which is less than minimum " +
            r"required [0-9]+ free data blocks. Create more free space in thin pool or use " +
            r"dm.min_free_space option to change behavior",
            re.MULTILINE)))

        """
        Docker informational
        """
        regex_list.append(("reclaimed space", re.compile(
            r"Total reclaimed space.*?B",
            re.MULTILINE)))

        """
        Unclassified error
        """
        regex_list.append(("stdout temporarily unavailable", re.compile(
            r"/dev/stdout: resource temporarily unavailable",
            re.MULTILINE)))

        """
        Generic Jenkins errors
        """
        regex_list.append(("java exception", re.compile(
            r"^(?P<exception>java[.].*Exception):\s*(?P<exception_text>.*?)$",
            re.MULTILINE)))

        regex_list.append(("jenkins error", re.compile(
            r"^ERROR:\s*(?P<error_text>.*?)\n.*?\n+",
            re.MULTILINE)))

        regex_list.append(("jenkins fatal error", re.compile(
            r"^FATAL:\s*(?P<fatal_text>.*?)\n.*?\n+",
            re.MULTILINE)))

        regex_list.append(("remote file operation failed", re.compile(
            r"^remote file operation failed:\s*(?P<remote_fail_text>.*?)\n.*?\n+",
            re.MULTILINE)))

        return regex_list
