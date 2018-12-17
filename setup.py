# Copyright (c) 2018 Cisco Systems, Inc.
# All rights reserved.

__author__ = 'jonpsull'

import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
version_file = os.path.join(here, 'VERSION')

# Get the long description from the README file
with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

if not os.path.isfile(version_file):
    BUILD_NUMBER = os.environ.get('TRAVIS_BUILD_NUMBER', '0')
    with open(version_file, encoding='utf-8', mode='w') as f:
        f.write(BUILD_NUMBER)
else:
    with open(version_file, encoding='utf-8') as f:
        BUILD_NUMBER = f.read().strip()

setup(
    name='es_logger',
    version='2.' + BUILD_NUMBER,

    description='Framework for Creating Logstash events from Jenkins Jobs',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/CiscoDevNet/es-logger',

    author='JP Sullivan (j3p0uk)',
    author_email='jonpsull@cisco.com',

    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Testing',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],

    keywords='jenkins development elasticsearch logstash build',

    install_requires=[
        'python-jenkins>=1.0.0',
        'requests',
        'stevedore',
        'zmq',
    ],

    platforms=['Any'],

    scripts=[],

    provides=['es_logger'],

    packages=find_packages(exclude=['docs', 'test']),
    include_package_data=True,

    entry_points={
        'console_scripts': [
            'es-logger=es_logger.cli:main',
            'zmq-es-logger=es_logger.zmq_client:main',
        ],
        'es_logger.plugins.console_log_processor': [
        ],
        'es_logger.plugins.gather_build_data': [
        ],
        'es_logger.plugins.event_generator': [
            'commit = es_logger.plugins.commit:CommitEvent',
            'ansible_recap_v2 = es_logger.plugins.ansible:AnsibleRecapEvent',
            'junit = es_logger.plugins.junit:JUnitEvent',
        ],
        'es_logger.plugins.event_target': [
            'logstash = es_logger.plugins.target:LogstashTarget',
        ],
    },

    data_files=[("", ["LICENSE", "VERSION"])],

    project_urls={
        'Bug Reports': 'https://github.com/CiscoDevNet/es-logger/issues',
        'Source': 'https://github.com/CiscoDevNet/es-logger/',
    },

    zip_safe=False,
)
