from __future__ import absolute_import, print_function, unicode_literals

import logging

from django.conf import settings  # noqa

from ._version import version as VERSION  # noqa

logger = logging.getLogger('sentry_zendesk')
