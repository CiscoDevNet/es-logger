ES-Logger
=========

[![Build Status](https://travis-ci.org/CiscoDevNet/es-logger.svg?branch=master)](https://travis-ci.org/CiscoDevNet/es-logger) [![PyPi](https://img.shields.io/pypi/v/es-logger.svg)](https://pypi.org/project/es-logger/)

The es-logger project intends to build a pluggable data processor that will take data from
Jenkins builds and push that data into Elasticsearch via Logstash.

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

## Logstash Target
* LOGSTASH_SERVER - HTTP server configured to receive json messages, as per the sample
configuration
* LS_USER - User to connect to Logstash with
* LS_PASSWORD - Password to connect to Logstash with

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

## Event Generators

An event generator is intended to process the Jenkins information and generate a number of
events based off that data.  This allows for the creation of unique events per-host or
per-test if the Jenkins job operates on multiple resources.  The structures returned are
expected to be very small, so surfacing data points to form the basis of visualisations.  A
small number of default fields will be added by the main program to identify the origination
of the data, and the event data will become contained in a top-level key named after the plugin.

The return from the generator should be a list of events that will be posted to logstash
