============
Contributing
============

Contributions are welcome, and they are greatly appreciated! Every
little bit helps, and credit will always be given.

Here's how to set up `sentry-zendesk` for local development:

1. You will need a Linux machine. Make sure you have ``g++``, ``python 2.7``, ``virtualenv`` and ``redis`` installed on the system. On Ubuntu you can install with:

.. code-block:: bash

    sudo apt-get install g++ python2.7 redis-server virtualenv

2. Fork the `sentry-zendesk` repo on GitHub.
3. Clone your fork locally and install flake8 pre-commit hook

.. code-block:: bash

    git clone https://github.com/your_name_here/sentry-zendesk.git
    cd sentry-zendesk
    flake8 --install-hook=git
    git config --local flake8.strict true

4. Create a new virtualenv environment for developing

.. code-block:: bash

    virtualenv -p python2.7 venv
    source venv/bin/activate  # If using bash, otherwise use the appropriate activate script
    pip install -r requirements_dev.txt

4. Create a branch for local development

.. code-block:: bash

    git checkout -b name-of-your-bugfix-or-feature

Now you can make your changes locally.

5. After each change make sure the tests still pass

.. code-block:: bash

    py.test tests


6. Commit your changes and push your branch to GitHub

.. code-block:: bash

    git add .
    git commit -m "Your detailed description of your changes."
    git push origin name-of-your-bugfix-or-feature

7. Submit a pull request through the GitHub website.

Pull Request Guidelines
-----------------------

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated. Please
   add the feature to the list in README.rst.
3. The pull request should work for all sentry versions being tested on CI. Check
   https://travis-ci.org/ESSS/sentry-zendesk/pull_requests
   and make sure that the tests pass for all supported Sentry versions.
4. Additionally if the changes are complex or make use of new methods/hooks
   executed by the sentry server it is recommended to test against a full sentry
   server (unless you can find a good way to write integrated tests). To run a
   a sentry server locally the easiest option is the `onpremise`_ repo.

Tips
----

To run a specific test:

.. code-block:: bash

    py.test tests -k test_name

Sometimes is very useful to see a coverage report to check if you are forgetting
to test something. To generate an html report:

.. code-block:: bash

    py.test --cov sentry_zendesk --cov-config .coveragerc --cov-report html tests

.. _`onpremise`: https://github.com/getsentry/onpremise
