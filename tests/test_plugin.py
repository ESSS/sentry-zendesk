from __future__ import absolute_import, print_function, unicode_literals

from urllib import urlencode

from django.test import RequestFactory
from exam import fixture
from sentry.testutils import TestCase
from sentry.utils import json
from sentry_plugins.exceptions import ApiError
import pytest
import responses

from sentry_zendesk.plugin import ZendeskPlugin


class ZendeskPluginTest(TestCase):

    @fixture
    def plugin(self):
        return ZendeskPlugin()

    @fixture
    def request(self):
        return RequestFactory()

    def test_conf_key(self):
        assert self.plugin.conf_key == 'sentry_zendesk'

    def test_get_issue_label(self):
        group = self.create_group(message='Hello world', culprit='foo.bar')
        assert self.plugin.get_issue_label(group, '12345') == '#12345'

    def test_get_issue_url(self):
        self.plugin.set_option(
            'zendesk_url', 'https://foocompany.zendesk.com', self.project)
        group = self.create_group(message='Hello world', culprit='foo.bar')
        assert self.plugin.get_issue_url(
            group, '12345') == 'https://foocompany.zendesk.com/tickets/12345'

    def test_is_configured(self):
        assert self.plugin.is_configured(None, self.project) is False
        self.plugin.set_option(
            'zendesk_url', 'https://foocompany.zendesk.com', self.project)
        assert self.plugin.is_configured(None, self.project) is True

    @responses.activate
    def test_dont_create_problem_after_event_when_option_is_disabled(self):
        self._configure_plugin()
        self.plugin.set_option('auto_create_problems', False, self.project)
        group = self.create_group(message='Hello world', culprit='foo.bar')

        # Should do nothing, and therefore not raise
        self.plugin.post_process(
            group, event=self.event, is_new=True, is_sample=False)

    def _configure_plugin(self):
        self.plugin.set_option(
            'zendesk_url', 'https://foocompany.zendesk.com', self.project)
        self.plugin.set_option('username', 'Bob', self.project)
        self.plugin.set_option('password', 'bob123', self.project)

    @responses.activate
    def test_create_problem_after_event_raises_on_http_error(self):
        self._configure_plugin()
        self.plugin.set_option('auto_create_problems', True, self.project)
        group = self.create_group(message='Hello world', culprit='foo.bar')

        responses.add(
            responses.POST,
            'https://foocompany.zendesk.com/api/v2/tickets.json',
            body='Error creating ticket',
            status=500,
        )

        with pytest.raises(ApiError):
            self.plugin.post_process(
                group, event=self.event, is_new=True, is_sample=False)

    @responses.activate
    def test_create_problem_after_event_does_nothing_when_already_linked(self):
        """
        In the case it is possible for a new event to arrive, but there is
        already a ticket linked to the sentry issue, nothing should be done.

        This behavior may be reconsidered in the future. Maybe it is better
        to raise some error.
        """
        from sentry.models.groupmeta import GroupMeta

        self._configure_plugin()
        self.plugin.set_option('auto_create_problems', True, self.project)
        group = self.create_group(message='Hello world', culprit='foo.bar')
        GroupMeta.objects.set_value(group,
                                    '%s:tid' % self.plugin.get_conf_key(),
                                    '12345')

        # Should not raise
        self._process_new_event(group)

    @responses.activate
    def test_create_problem_after_event(self):
        self._configure_plugin()
        self.plugin.set_option('auto_create_problems', True, self.project)
        group = self.create_group(message='Hello world', culprit='foo.bar')

        self._process_new_event(group)

        assert len(responses.calls) == 1
        sent_data = json.loads(responses.calls[0].request.body)
        assert sent_data == {
            'ticket': {
                'comment': '[http://testserver/baz/bar/issues/1/](http://testserver/baz/bar/issues/1/)',  # noqa
                'type': 'problem',
                'subject': self.event.error(),
            }
        }
        # Newly created problem should be linked to the sentry issue
        assert self._get_linked_ticket_id(group) == unicode(
            create_problem_response['ticket']['id'])

    def _process_new_event(self, group):
        responses.add(
            responses.POST,
            'https://foocompany.zendesk.com/api/v2/tickets.json',
            json=create_problem_response,
            content_type='application/json',
        )

        self.plugin.post_process(
            group, event=self.event, is_new=True, is_sample=False)

    def _process_repeated_event(self, group):
        responses.add(
            responses.POST,
            'https://foocompany.zendesk.com/api/v2/tickets.json',
            json=create_incident_response,
            content_type='application/json',
        )

        self.plugin.post_process(
            group, event=self.event, is_new=False, is_sample=False)

    def _get_linked_ticket_id(self, group):
        from sentry.models.groupmeta import GroupMeta
        return GroupMeta.objects.get_value(
            group, '%s:tid' % self.plugin.get_conf_key())

    @responses.activate
    def test_dont_create_incident_after_event_when_option_is_disabled(self):
        self._configure_plugin()
        self.plugin.set_option('auto_create_problems', True, self.project)
        self.plugin.set_option('auto_create_incidents', False, self.project)
        group = self.create_group(message='Hello world', culprit='foo.bar')

        # Should do nothing, and therefore not raise
        self.plugin.post_process(
            group, event=self.event, is_new=False, is_sample=False)

    @responses.activate
    def test_dont_create_incident_after_event_when_no_problem_is_linked(self):
        self._configure_plugin()
        self.plugin.set_option('auto_create_problems', False, self.project)
        self.plugin.set_option('auto_create_incidents', True, self.project)
        group = self.create_group(message='Hello world', culprit='foo.bar')

        # As there is no problem previously linked, there is no way to create
        # an incident. Should do nothing, and therefore not raise
        self.plugin.post_process(
            group, event=self.event, is_new=False, is_sample=False)

    @responses.activate
    def test_create_incident_after_event_when_problem_is_already_linked(self):
        """
        Even if auto_create_problems setting is disabled, and incident should
        be created if the user manually linked to a problem.
        """
        from sentry.models.groupmeta import GroupMeta

        self._configure_plugin()
        self.plugin.set_option('auto_create_problems', False, self.project)
        self.plugin.set_option('auto_create_incidents', True, self.project)
        group = self.create_group(message='Hello world', culprit='foo.bar')
        # Emulates as if the user had manually linked to a ticket
        GroupMeta.objects.set_value(group,
                                    '%s:tid' % self.plugin.get_conf_key(),
                                    '12345')

        self._process_repeated_event(group)

        assert len(responses.calls) == 1
        sent_data = json.loads(responses.calls[0].request.body)
        assert sent_data == {
            'ticket': {
                'comment': '[http://testserver/baz/bar/issues/1/](http://testserver/baz/bar/issues/1/)',  # noqa
                'type': 'incident',
                'problem_id': '12345',
                'subject': self.event.error()
            }
        }
        # Original problem created on first event should still be linked to the
        # sentry issue
        assert self._get_linked_ticket_id(group) == '12345'

    @responses.activate
    def test_create_incident_after_event_raises_on_http_error(self):
        from sentry.models.groupmeta import GroupMeta

        self._configure_plugin()
        self.plugin.set_option('auto_create_incidents', True, self.project)
        group = self.create_group(message='Hello world', culprit='foo.bar')
        # Emulates as if the user had manually linked to a ticket
        GroupMeta.objects.set_value(group,
                                    '%s:tid' % self.plugin.get_conf_key(),
                                    '12345')

        responses.add(
            responses.POST,
            'https://foocompany.zendesk.com/api/v2/tickets.json',
            body='Error creating ticket',
            status=500,
        )

        with pytest.raises(ApiError):
            self.plugin.post_process(
                group, event=self.event, is_new=False, is_sample=False)

    @responses.activate
    def test_create_problem_and_incident_after_two_events(self):
        self._configure_plugin()
        self.plugin.set_option('auto_create_problems', True, self.project)
        self.plugin.set_option('auto_create_incidents', True, self.project)
        group = self.create_group(message='Hello world', culprit='foo.bar')

        self._process_new_event(group)
        self._process_repeated_event(group)

        assert len(responses.calls) == 2
        sent_data = json.loads(responses.calls[1].request.body)
        assert sent_data == {
            'ticket': {
                'comment': '[http://testserver/baz/bar/issues/1/](http://testserver/baz/bar/issues/1/)',  # noqa
                'type': 'incident',
                'problem_id': unicode(create_problem_response['ticket']['id']),
                'subject': self.event.error()
            }
        }
        # Original problem created on first event should still be linked to the
        # sentry issue
        assert self._get_linked_ticket_id(group) == unicode(
            create_problem_response['ticket']['id'])

    @responses.activate
    def test_search_when_autocompleting(self):
        self._configure_plugin()
        group = self.create_group(message='Hello world', culprit='foo.bar')

        responses.add(
            responses.GET, 'https://foocompany.zendesk.com/api/v2/search.json',
            json=search_response,
            content_type='application/json',
        )
        # This would be the request sent when the user fills the issue field on
        # UI
        request = self.request.get(
            '/',
            data={'autocomplete_query': 'foo',
                  'autocomplete_field': 'issue_id'}
        )

        assert self.plugin.view_autocomplete(request, group).data == {
            'issue_id': [
                {'id': '4178', 'text': '(4178) Cannot run foo'},
                {'id': '5289', 'text': '(5289) Problem running bar with foo'}
            ]}
        assert len(responses.calls) == 1
        assert urlencode({'query': 'type:ticket subject:foo*'}
                         ) in responses.calls[0].request.url

    @responses.activate
    def test_search_when_autocompleting_raises_on_http_error(self):
        self._configure_plugin()
        group = self.create_group(message='Hello world', culprit='foo.bar')

        responses.add(
            responses.GET, 'https://foocompany.zendesk.com/api/v2/search.json',
            body='Error searching',
            status=500,
        )
        # This would be the request sent when the user fills the issue field on
        # UI
        request = self.request.get(
            '/',
            data={'autocomplete_query': 'foo',
                  'autocomplete_field': 'issue_id'}
        )

        with pytest.raises(ApiError):
            self.plugin.view_autocomplete(request, group)


problem_ticket = {
    'allow_channelback': False,
    'assignee_id': 111222333,
    'brand_id': 120120,
    'collaborator_ids': [],
    'created_at': '2011-01-17T15:41:29Z',
    'custom_fields': [{'id': 23000032, 'value': 'basic'}],
    'description': 'I had some problems while running foo',
    'due_at': None,
    'external_id': None,
    'fields': [{'id': 23000032, 'value': 'basic'}],
    'forum_topic_id': None,
    'group_id': 21617466,
    'has_incidents': False,
    'id': 4178,
    'is_public': True,
    'organization_id': 274274274,
    'priority': None,
    'problem_id': None,
    'raw_subject': 'Cannot run foo',
    'recipient': None,
    'requester_id': 341341341,
    'result_type': 'ticket',
    'satisfaction_rating': {'score': 'unoffered'},
    'sharing_agreement_ids': [20022002],
    'status': 'open',
    'subject': 'Cannot run foo',
    'submitter_id': 18161816,
    'tags': ['basic', 'foo'],
    'type': 'problem',
    'updated_at': '2011-01-17T15:41:29Z',
    'url': 'https://foocompany.zendesk.com/api/v2/tickets/4178.json',
    'via': {
        'channel': 'web',
        'source': {
            'from': {'subject': 'Cannot run foo', 'ticket_id': 4193},
            'rel': 'follow_up',
            'to': {}
        }
    }
}


incident_ticket = {
    'allow_channelback': False,
    'assignee_id': 111222333,
    'brand_id': 120120,
    'collaborator_ids': [],
    'created_at': '2013-08-13T10:59:34Z',
    'custom_fields': [{'id': 23000032, 'value': ''}],
    'description': 'After installing foo I can\'t run bar',
    'due_at': None,
    'external_id': None,
    'fields': [{'id': 23000032, 'value': ''}],
    'forum_topic_id': None,
    'group_id': 21617466,
    'has_incidents': False,
    'id': 5289,
    'is_public': True,
    'organization_id': 274274274,
    'priority': None,
    'problem_id': 4178,
    'raw_subject': 'Problem running bar with foo',
    'recipient': None,
    'requester_id': 18161816,
    'result_type': 'ticket',
    'satisfaction_rating': {'score': 'unoffered'},
    'sharing_agreement_ids': [20022002],
    'status': 'open',
    'subject': 'Problem running bar with foo',
    'submitter_id': 18161816,
    'tags': ['foo', 'bar'],
    'type': 'incident',
    'updated_at': '2013-08-13T11:59:34Z',
    'url': 'https://foocompany.zendesk.com/api/v2/tickets/5289.json',
    'via': {'channel': 'web',
            'source': {'from': {}, 'rel': None, 'to': {}}}
}


search_response = {
    'count': 2,
    'facets': None,
    'next_page': None,
    'previous_page': None,
    'results': [problem_ticket, incident_ticket]
}


create_problem_response = {
    'audit': {
        'author_id': 111222111,
        'created_at': '2017-03-30T19:52:24Z',
        'events': [{'attachments': [],
                    'audit_id': 191819181918,
                    'author_id': 111222111,
                    'body': 'I had some problems while running foo',
                    'html_body': '<div class="zd-comment">\n<p dir="auto">I had some problems while running foo</p></div>',  # noqa
                    'id': 191874783063,
                    'plain_body': 'I had some problems while running foo',
                    'public': True,
                    'type': 'Comment'},
                   {'field_name': 'subject',
                    'id': 191874783223,
                    'type': 'Create',
                    'value': 'Cannot run foo'}],
        'id': 191819181918,
        'metadata': {'custom': {},
                     'system': {'client': 'python-requests/2.12.5',
                                'ip_address': '174.89.241.195',
                                'latitude': -26.38399899999999,  # noqa
                                'location': 'Unknown City, 26, Some Country',
                                'longitude': -124.10156399999999}},  # noqa
        'ticket_id': 4178,
        'via': {'channel': 'api',
                'source': {'from': {}, 'rel': None, 'to': {}}}},
    'ticket': problem_ticket
}


create_incident_response = {
    'audit': {
        'author_id': 111222111,
        'created_at': '2017-03-30T19:50:28Z',
        'events': [{'attachments': [],
                    'audit_id': 191874224843,
                    'author_id': 111222111,
                    'body': 'After installing foo I can\'t run bar',
                    'html_body': '<div class="zd-comment">\n<p dir="auto">After installing foo I can\'t run bar</p></div>',  # noqa
                    'id': 191874224863,
                    'plain_body': 'After installing foo I can\'t run bar',
                    'public': True,
                    'type': 'Comment'},
                   {'field_name': 'subject',
                    'id': 191874224903,
                    'type': 'Create',
                    'value': 'Problem running bar with foo'},
                   {'field_name': 'assignee_id',
                    'id': 191874224963,
                    'type': 'Create',
                    'value': '111222111'},
                   ],
        'id': 191874224843,
        'metadata': {'custom': {},
                     'system': {'client': 'python-requests/2.12.5',
                                'ip_address': '174.89.241.195',
                                'latitude': -26.38399899999999,  # noqa
                                'location': 'Unknown City, 26, Some Country',
                                'longitude': -124.10156399999999}},  # noqa
        'ticket_id': 5289,
        'via': {'channel': 'api',
                'source': {'from': {}, 'rel': None, 'to': {}}}},
    'ticket': incident_ticket
}
