# -*- coding: utf-8 -*-
__author__ = 'lundberg'

import core


class BaseModel(object):

    def __init__(self, manager):
        self.manager = manager
        self.meta_type = None
        self.labels = None
        self.data = None

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return u'{meta_type} node ({handle_id}) with labels {labels} in database {db}.'.format(
            meta_type=self.meta_type, handle_id=self.get_handle_id(), labels=self.labels, db=self.manager.dsn
        )

    def get_handle_id(self):
        return self.data.get('handle_id')

    def load(self, node_bundle):
        self.meta_type = node_bundle.get('meta_type')
        self.labels = node_bundle.get('labels')
        self.data = node_bundle.get('data')
        return self


def load_object(manager, handle_id):
    bundle = core.get_node_bundle(manager, handle_id)
    # TODO: Implement sub classes and let load_object  choose
    return BaseModel(manager).load(bundle)