from __future__ import absolute_import, print_function, unicode_literals

from django.utils.encoding import force_bytes  # noqa
from requests.exceptions import HTTPError
from sentry.http import build_session
from sentry_plugins.exceptions import ApiError

from sentry_zendesk import logger


class ZendeskClient(object):

    SEARCH_URL = '/api/v2/search.json'
    CREATE_URL = '/api/v2/tickets.json'
    HTTP_TIMEOUT = 5

    def __init__(self, zendesk_url, username, password):
        self.zendesk_url = zendesk_url.rstrip('/')
        self.username = username
        self.password = password

    def create_ticket(self, title, comment, ticket_type, problem_id):
        params = {
            'ticket': {
                'type': ticket_type,
                'subject': title,
                'comment': comment,
            }
        }
        if problem_id is not None:
            params['ticket']['problem_id'] = problem_id

        response = self.make_request('post', self.CREATE_URL, params)
        created_ticket = response.json()['ticket']
        ticket_id = unicode(created_ticket['id'])
        logger.info('Created new ticket id "{}"'.format(ticket_id))
        return ticket_id

    def search_tickets(self, query):
        params = {'query': 'type:ticket subject:{}*'.format(query)}
        response = self.make_request('get', self.SEARCH_URL, params)
        return response.json()

    def make_request(self, method, url, payload=None):
        if url[:4] != "http":
            url = self.zendesk_url + url
        auth = self.username.encode('utf8'), self.password.encode('utf8')
        session = build_session()
        if method == 'get':
            response = session.get(url, params=payload, auth=auth,
                                   verify=False, timeout=self.HTTP_TIMEOUT)
        else:
            response = session.post(url, json=payload, auth=auth,
                                    verify=False, timeout=self.HTTP_TIMEOUT)

        try:
            response.raise_for_status()
        except HTTPError as e:
            raise ApiError.from_response(e.response)
        return response
