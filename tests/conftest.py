from __future__ import absolute_import, print_function, unicode_literals

import os

from django.conf import settings


# Run tests against sqlite for simplicity
os.environ.setdefault('DB', 'sqlite')
pytest_plugins = [b'sentry.utils.pytest']


def pytest_configure(config):
    settings.INSTALLED_APPS = tuple(settings.INSTALLED_APPS) + (
        'sentry_zendesk',
    )

    from sentry.plugins import plugins
    from sentry_zendesk.plugin import ZendeskPlugin
    plugins.register(ZendeskPlugin)
