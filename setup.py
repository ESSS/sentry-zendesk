#!/usr/bin/env python
from __future__ import absolute_import

from setuptools import setup

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

tests_require = [
    'exam',
    'flake8>=2.0,<2.1',
    'responses',
    'sentry>=8.11.0',
    'sentry-plugins>=8.11.0',
]

install_requires = [
    'sentry>=8.11.0',
    'sentry-plugins>=8.11.0',
]

setup(
    name='sentry-zendesk',
    author='ESSS',
    url='https://github.com/ESSS/sentry-zendesk',
    description='Plugin for Sentry which allows linking Zendesk tickets to '
                'Sentry issues',
    long_description=readme + '\n\n' + history,
    use_scm_version={'write_to': 'sentry_zendesk/_version.py'},
    setup_requires=['setuptools_scm'],
    license='Apache',
    packages=['sentry_zendesk'],
    zip_safe=False,
    install_requires=install_requires,
    entry_points={
        'sentry.apps': [
            'zendesk = sentry_zendesk',
        ],
        'sentry.plugins': [
            'zendesk = sentry_zendesk.plugin:ZendeskPlugin',
        ],
    },
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development'
    ],
    test_suite='tests',
    tests_require=tests_require,
)
