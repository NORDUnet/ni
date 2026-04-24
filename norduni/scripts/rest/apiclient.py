# -*- coding: utf-8 -*-
"""
Created on 2013-10-24 1:57 PM

@author: lundberg
"""

import hammock
import json
from itertools import count
import logging

logger = logging.getLogger('niapiclient')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


class NIApiClient():

    def __init__(self, base_url, user, apikey):
        self.user = user
        self.apikey = apikey
        self.client = hammock.Hammock(base_url, append_slash=True)

    def create_headers(self, **kwargs):
        headers = {'Authorization': 'ApiKey %s:%s' % (self.user, self.apikey)}
        headers.update(kwargs)
        return headers

    def get_host_scan(self, limit=500, headers={}):
        headers = self.create_headers(**headers)
        for offset in count(start=0, step=limit):
            response = self.client.api.v1('host-scan').GET(headers=headers, params={'limit': limit, 'offset': offset})
            try:
                batch = response.json()['objects']
            except (ValueError, KeyError) as e:
                logger.error(e)
                logger.error('{} {}'.format(response.status_code, response.reason))
                break
            if not batch:
                raise StopIteration
            for obj in batch:
                yield obj

    def get_type(self, node_type, limit=20, headers={}):
        for offset in count(start=0, step=limit):
            request = self.client.api.v1(node_type).GET(headers=headers, params={'limit': limit, 'offset': offset})
            try:
                batch = json.loads(request.content)['objects']
            except (ValueError, KeyError) as e:
                logger.error(e)
                logger.error('%s %s' % (request.status_code, request.reason))
                break
            if not batch:
                raise StopIteration
            for obj in batch:
                yield obj

    def get_relationships(self, entity, limit=20, relationship_type=None, headers={}):
        try:
            pk = entity['handle_id']
            node_type = entity['node_type'].split('/')[-2]
        except KeyError as e:
            logger.error(e)
            logger.error('entity did not supply expected values.')
            raise KeyError
        for offset in count(start=0, step=limit):
            params = {'limit': limit, 'offset': offset}
            if not relationship_type:
                request = self.client.api.v1(node_type)(pk).relationships.GET(headers=headers, params=params)
            else:
                request = self.client.api.v1(node_type)(pk).relationships(relationship_type).GET(headers=headers,
                                                                                                 params=params)
            try:
                batch = json.loads(request.content)['objects']
            except ValueError as e:
                logger.error(e)
                logger.error('%s %s' % (request.status_code, request.reason))
                break
            if not batch:
                raise StopIteration
            for obj in batch:
                yield obj
