# -*- coding: utf-8 -*-
__author__ = 'lundberg'

import hammock
import json

base_url = 'https://nidev-consumer.nordu.net'
user = 'lundberg'
key = '204db7bcfafb2deb7506b89eb3b9b715b09905c8'
nidev = hammock.Hammock(base_url, append_slash=True)
headers = {'Authorization': 'ApiKey %s:%s' % (user, key)}
hosts = json.loads(nidev.api.v1.host.GET(headers=headers).content)['objects']