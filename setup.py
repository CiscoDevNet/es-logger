# Copyright (c) 2018 Cisco Systems, Inc.
# All rights reserved.

__author__ = 'jonpsull'

import os
from setuptools import setup, find_packages

BUILD_NUMBER = os.environ.get('BUILD_NUMBER', '0')

setup(
    name='es_logger',
    version='2.' + BUILD_NUMBER,

    description='Framework for Creating Logstash events from Jenkins Jobs',

    author='JP Sullivan (j3p0uk)',
    author_email='jonpsull@cisco.com',

    install_requires=[
        'python-jenkins',
        'requests',
        'stevedore',
    ],

    platforms=['Any'],

    scripts=[],

    provides=['es_logger'],

    packages=find_packages(),
    include_package_data=True,

    entry_points={
        'console_scripts': [
            'es-logger=es_logger.cli:main',
        ],
        'es_logger.plugins.console_log_processor': [
        ],
        'es_logger.plugins.gather_build_data': [
        ],
        'es_logger.plugins.event_generator': [
            'commit = es_logger.event_generator:CommitEvent',
        ],
    },

    zip_safe=False,
)
