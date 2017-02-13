# coding: utf-8
from __future__ import absolute_import, print_function, unicode_literals

from django.conf.urls import url
from rest_framework.response import Response
from sentry.models import GroupMeta
from sentry.plugins.bases.issue2 import IssuePlugin2, IssueGroupActionEndpoint
from sentry.utils.http import absolute_uri
from sentry_plugins.utils import get_secret_field_config

from sentry_zendesk import logger

from . import VERSION


class ZendeskPlugin(IssuePlugin2):
    title = 'Zendesk'
    slug = 'sentry_zendesk'
    description = 'Provides linking Zendesk tickets to Sentry issues.'
    version = VERSION
    author = 'ESSS'
    author_url = 'https://github.com/ESSS/sentry-zendesk'
    resource_links = [
        ('Bug Tracker', 'https://github.com/ESSS/sentry-zendesk/issues'),
        ('Source', 'https://github.com/ESSS/sentry-zendesk'),
    ]

    conf_key = 'sentry_zendesk'
    conf_title = title

    # Disable create action until it is implemented
    allowed_actions = ('link', 'unlink')

    def get_group_urls(self):
        _patterns = super(ZendeskPlugin, self).get_group_urls()
        _patterns.append(
            url(
                r'^autocomplete',
                IssueGroupActionEndpoint.as_view(
                    view_method_name='view_autocomplete',
                    plugin=self
                )
            )
        )
        return _patterns

    def is_configured(self, request, project, **kwargs):
        """
        Used by sentry to know if this plugin hooks should be executed.
        If the plugin is not configured its behavior is like if it was
        disabled.
        """

        if not self.get_option('zendesk_url', project):
            return False
        return True

    def get_config(self, *args, **kwargs):
        """
        Called by the web process when user wants to configure the plugin.
        """
        project = kwargs['project']
        pw = self.get_option('password', project)
        secret_field = get_secret_field_config(pw, '')
        secret_field.update({
            'name': 'password',
            'label': 'Password'
        })

        return [{
            'name': 'zendesk_url',
            'label': 'Zendesk URL',
            'default': self.get_option('zendesk_url', project),
            'type': 'text',
            'placeholder': 'e.g. "https://mycompany.zendesk.com"',
            'help': 'It must be visible to the Sentry server'
        }, {
            'name': 'username',
            'label': 'Username',
            'default': self.get_option('username', project),
            'type': 'text',
            'help': 'Ensure the Zendesk user has admin permissions on the '
                    'project'
        }, secret_field, {
            'name': 'auto_create_problems',
            'label': 'Automatically create Zendesk problems',
            'default': self.get_option('auto_create_problems', project) or False,  # noqa
            'type': 'bool',
            'required': False,
            'help': 'Automatically create a Zendesk ticket of type problem '
                    'for EVERY new issue'
        }, {
            'name': 'auto_create_incidents',
            'label': 'Automatically create Zendesk incidents',
            'default': self.get_option('auto_create_incidents', project) or False,  # noqa
            'type': 'bool',
            'required': False,
            'help': 'Automatically create a Zendesk ticket of type incident ' \
                    'for EVERY event after the first one, linking it to the ' \
                    'previously created problem.'
        }]

    def post_process(self, group, event, is_new, is_sample, **kwargs):
        """
        Called by the worker process whenever a new event arrives.
        """
        logger.info('event: {}, is_new: {}'.format(event, is_new))

        if is_new:
            if not self.get_option('auto_create_problems', group.project):
                return
            logger.info('New problem')
            problem_id = self._get_linked_ticket(group)
            if problem_id:
                logger.error('There is already a problem linked to this event')
                return

            logger.info('Creating new problem')
            ticket_id = self._create_ticket(
                group, event, ticket_type='problem')
            GroupMeta.objects.set_value(
                group, '%s:tid' % self.get_conf_key(), ticket_id)
        elif self.get_option('auto_create_incidents', group.project):
            problem_id = self._get_linked_ticket(group)
            if not problem_id:
                logger.info(
                    'Cannot create incident because there is no linked problem'
                )
                return

            logger.info(
                'Creating new incident linked to problem "{}"'
                .format(problem_id))
            self._create_ticket(
                group, event, ticket_type='incident', problem_id=problem_id)

    def _get_linked_ticket(self, group):
        # XXX(dcramer): Sentry doesn't expect GroupMeta referenced here so we
        # need to populate the cache
        GroupMeta.objects.populate_cache([group])
        problem_id = GroupMeta.objects.get_value(
            group, '%s:tid' % self.get_conf_key(), None)
        return problem_id

    def _create_ticket(self, group, event, ticket_type, problem_id=None):
        client = self.get_client(group.project)
        title = self.get_group_title(None, group, event)
        comment = '[{0}]({0})'.format(absolute_uri(group.get_absolute_url()))
        return client.create_ticket(title=title,
                                    ticket_type=ticket_type,
                                    problem_id=problem_id,
                                    comment=comment)

    def get_link_existing_issue_fields(self, request, group, event, **kwargs):
        """
        Called by the web process when showing a dialog to link to an external
        issue (ticket)
        """
        return [{
            'name': 'issue_id',
            'label': 'Ticket',
            'default': '',
            'type': 'select',
            'has_autocomplete': True
        }, {
            'name': 'comment',
            'label': 'Comment',
            'default': absolute_uri(group.get_absolute_url()),
            'type': 'textarea',
            'help': ('Leave blank if you don\'t want to '
                     'add a comment to the Zendesk ticket.'),
            'required': False
        }]

    def get_issue_url(self, group, issue_id, **kwargs):
        """
        Called by the web process to show a link of the external issue (ticket)
        """
        instance = self.get_option('zendesk_url', group.project)
        return "%s/tickets/%s" % (instance, issue_id)

    def view_autocomplete(self, request, group, **kwargs):
        """
        Called by the web process when user wants to link sentry issue to an
        existing Zendesk ticket.
        """
        query = request.GET.get('autocomplete_query')
        field = request.GET.get('autocomplete_field')
        client = self.get_client(group.project)

        data = client.search_tickets(query)
        issues = [{
            'text': '(%s) %s' % (i['id'], i['subject']),
            'id': unicode(i['id'])
        } for i in data.get('results', [])]

        return Response({field: issues})

    def get_client(self, project):
        from sentry_zendesk.client import ZendeskClient

        url = self.get_option('zendesk_url', project)
        username = self.get_option('username', project)
        password = self.get_option('password', project)
        return ZendeskClient(url, username, password)

    def create_issue(self, request, group, form_data, **kwargs):
        """
        Called by the web process when the user wants to create a new Zendesk
        ticket and link to the sentry issue.
        """
        raise NotImplementedError('This feature is not implemented yet')

    def link_issue(self, request, group, form_data, **kwargs):
        """
        Called by the web process to link to an existing Zendesk ticket
        """
        # TODO: Add comment to Zendesk ticket with sentry url
        return {
            'title': form_data['issue_id']
        }
