ES-Logger
=========

[![Build Status](https://travis-ci.org/CiscoDevNet/es-logger.svg?branch=master)](https://travis-ci.org/CiscoDevNet/es-logger) [![PyPi](https://img.shields.io/pypi/v/es-logger.svg)](https://pypi.org/project/es-logger/) [![Gitter chat](https://badges.gitter.im/es-logger.png)](https://gitter.im/es-logger)

The es-logger project intends to build a pluggable data processor that will take data from
Jenkins builds and push that data into Elasticsearch via Logstash.  Overview slides are available
on slideshare in [Pipeline Analytics](https://www.slideshare.net/JonPaulSullivan/pipeline-analytics)

# Installation and Running

Install the framework using:

    python ./setup.py install

Install from source for developing using:

    python ./setup.py develop

Install from pypi repository with:

    pip install es-logger

After that, set environment variables needed, and just execute es-logger!

## Jenkins Connection
* JENKINS_URL - Used to prefix the location to gather Jenkins data from using the
[python-jenkins](https://python-jenkins.readthedocs.io/en/latest/) library
* JENKINS_USER - Username to access Jenkins
* JENKINS_PASSWORD - Password to access Jenkins.  Can also be an API key

## Job Information
* ES_JOB_NAME - The full job name with all paths, added to the JENKINS_URL
* ES_BUILD_NUMBER - The build number to collect data for

## Plugins
* PROCESS_CONSOLE_LOGS - Console log processor plugins to run, space separated list
* GATHER_BUILD_DATA - Build data gatherer plugins to run, space separated list
* GENERATE_EVENTS - Event generator plugins to run, space separated list

# Plugins

The plugin infrastructure is provided by the
[stevedore library](https://pypi.python.org/pypi/stevedore).

There are following types of plugin supported:

## Console Log Processors

These plugins will have a *process* function called that is passed the full console log
of the job.  It can perform any actions desirable, and shall return data, which will be
added to the es_info['console_log_plugins'][**plugin_name**] structure that is pushed to
logstash.  A list or a dict is preferred as a return type.

## Build Data Gatherers

These plugins will have a *gather* function that is passed the EsCollector object.  This
should provide any data needed for the plugin to gather any additional data that should
be added to the es_info.  This could include test results from an external system not
available to Jenkins, parsed logs from an external piece of hardware, etc.

The return should be a dictionary, which will be added to the
es_info['build_data'][**plugin_name**] structure that is pushed to logstash.

## Event Targets

Once the data is collected by Es-Logger and constructed into a series of events,
these events need to be sent to a target.  A target is any location that will accept
json structured events.

### Logstash Target

The logstash target

* LOGSTASH_SERVER - HTTP server configured to receive json messages, as per the sample
configuration
* LS_USER - User to connect to Logstash with
* LS_PASSWORD - Password to connect to Logstash with

## Event Generators

An event generator is intended to process the Jenkins information and generate a number of
events based off that data.  This allows for the creation of unique events per-host or
per-test if the Jenkins job operates on multiple resources.  The structures returned are
expected to be very small, so surfacing data points to form the basis of visualisations.  A
small number of default fields will be added by the main program to identify the origination
of the data, and the event data will become contained in a top-level key named after the plugin.

The return from the generator should be a list of events that will be posted to logstash

# Example Execution

Here is a sample execution of es-logger against a public Jenkins repo.

It uses the public Jenkins that Netflix builds code upon at
[netflixoss.ci.cloudbees.com](https://netflixoss.ci.cloudbees.com/job/Lipstick-pull-requests)

```
export JENKINS_URL=https://netflixoss.ci.cloudbees.com/
export ES_JOB_NAME=Lipstick-pull-requests
export GENERATE_EVENTS="junit commit"
ES_BUILD_NUMBER=117 es-logger --no-post -c 100
```

Each execution can get a single jobs data.  To iterate over many, a simple bash loop can
suffice, or you can import es-logger into a python script and use it directly, similarly
to how it is used in [es\_logger/cli.py](es_logger/cli.py).

```
for i in $(seq 110 116)
do
    ES_BUILD_NUMBER=${i} es-logger --no-post -c 100
done
```

```
usage: es-logger [-h] [--no-dump | --no-post] [-c CONSOLE_LENGTH] [-e] [-p]
                 [-t TARGET] [--debug]

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

Target Variables:

Logstash Target Environment Variables:
    LOGSTASH_SERVER         The server to send events to
    LS_USER                 The user for logstash access
    LS_PASSWORD             The password for logstash access

optional arguments:
  -h, --help            show this help message and exit
  --no-dump             Do not dump events to the console
  --no-post             Do not post events to any targets
  -c CONSOLE_LENGTH, --console-length CONSOLE_LENGTH
                        Restrict the console length in the event to this
                        number of characters
  -e, --events-only     Do not dump or post the main job event, only events
                        from EventGenerator plugins
  -p, --list-plugins    List all plugins available
  -t TARGET, --target TARGET
                        A target to send events to
  --debug               Print debug logs to console during execution
```
