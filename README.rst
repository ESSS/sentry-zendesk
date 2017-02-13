Sentry Zendesk
==============

.. image:: https://img.shields.io/pypi/v/sentry-zendesk.svg
    :target: https://pypi.python.org/pypi/sentry-zendesk

.. image:: https://img.shields.io/pypi/pyversions/sentry-zendesk.svg
    :target: https://pypi.python.org/pypi/sentry-zendesk

.. image:: https://img.shields.io/pypi/l/sentry-zendesk.svg
    :target: https://pypi.python.org/pypi/sentry-zendesk

.. image:: https://travis-ci.org/ESSS/sentry-zendesk.svg?branch=master
    :target: https://travis-ci.org/ESSS/sentry-zendesk
    :alt: See Build Status on Travis CI

.. image:: https://codecov.io/gh/ESSS/sentry-zendesk/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/ESSS/sentry-zendesk?branch=master
   :alt: Coverage Status


Plugin for Sentry which allows linking Zendesk tickets to Sentry issues

**DISCLAIMER**: Sentry API under development and `is not frozen <https://docs.sentry.io/server/plugins/>`_.
Therefore this plugin is not guaranteed to work with all Sentry versions. Currently it is being
tested against versions **8.11, 8.12, 8.13, 8.14**.

Features
--------

Currently this plugin offers very basic functionality:

- Manually link a Sentry issue to an existing Zendesk ticket
- Automatically create a Zendesk ticket of type **problem** when a new event arrives
- Automatically create a Zendesk ticket of type **incident** when a recurrent event arrives. In this case, there must be a problem linked to the Sentry issue when the event arrives.

Limitations
-----------

Some features present on similar plugins (e.g. Jira) are not implemented yet for
Zendesk. For example, the following are currently **not possible**:

- Manually create a new Zendesk ticket through the UI button
- Customize fields of automatically created tickets. Most fields are left blank and the ones that are filled are automatically generated.
- Add comment to the Zendesk ticket when it is linked to a Sentry issue

Installation
------------

Using pip:

.. code-block:: bash

    pip install sentry-zendesk

or from source:

.. code-block:: bash

    python setup.py install

Then restart the sentry server. Please note that sentry is composed by multiple
processes. **Make sure you restart all of them** or at least the web and workers
processes.

If you are using ``docker-compose`` with `onpremise`_ repo you probably can just
add sentry-zendesk to ``requirements.txt`` and restart all services.

.. _`onpremise`: https://github.com/getsentry/onpremise
