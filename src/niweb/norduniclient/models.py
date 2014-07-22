# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from collections import defaultdict
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
            meta_type=self.meta_type, handle_id=self.handle_id, labels=self.labels, db=self.manager.dsn
        )

    def _query_to_defaultdict(self, query):
        with self.manager.read as r:
            hits = r.execute(query, handle_id=self.handle_id).fetchall()
        d = defaultdict(list)
        for hit in hits:
            rel_type, rel_id, rel, handle_id = hit
            d[rel_type].append({
                'relationship_id': rel_id,
                'relationship': rel,
                'node': core.get_model(self.manager, handle_id)
            })
        d.default_factory = None
        return d

    def _get_handle_id(self):
        return self.data.get('handle_id')
    handle_id = property(_get_handle_id)

    def load(self, node_bundle):
        self.meta_type = node_bundle.get('meta_type')
        self.labels = node_bundle.get('labels')
        self.data = node_bundle.get('data')
        return self

    def get_relations(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})<-[r:Owns|Uses|Provides|Responsible_for]-(node)
            RETURN type(r), id(r), r, node.handle_id
            """
        return self._query_to_defaultdict(q)

    def get_incoming_logical(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})<-[r:Depends_on|Part_of]-(node)
            RETURN type(r), id(r), r, node.handle_id
            """
        return self._query_to_defaultdict(q)

    def get_outgoing_logical(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})-[r:Depends_on|Part_of]->(node)
            RETURN type(r), id(r), r, node.handle_id
            """
        return self._query_to_defaultdict(q)

    def get_locations(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})<-[r:Located_in]-(node)
            RETURN type(r), id(r), r, node.handle_id
            """
        return self._query_to_defaultdict(q)


class LocationModel(BaseModel):

    def get_locations(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})<-[r:Has]-(node)
            RETURN type(r), id(r), r, node.handle_id
            """
        return self._query_to_defaultdict(q)


class EquipmentModel(BaseModel):

    def get_full_location(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})-[:Located_in]->(r)
            MATCH p=()-[:Has*]->(r)
            WITH COLLECT(nodes(p)) as paths, MAX(length(nodes(p))) AS maxLength
            WITH FILTER(path IN paths WHERE length(path)=maxLength) AS longestPaths
            RETURN longestPaths
            """
        d = defaultdict(list)
        with self.manager.read as r:
            try:
                d['Located_in'] = r.execute(q, handle_id=self.handle_id).fetchall()[0][0][0]
            except IndexError:
                pass
        d.default_factory = None
        return d

    def get_incoming_logical(self):
        q = """
            MATCH (equipment {handle_id: {handle_id}})
            OPTIONAL MATCH (equipment)<-[r1:Depends_on|Part_of]-(l1)
            WITH equipment, r1, l1
            OPTIONAL MATCH (equipment)-[:Has*]->(port)<-[r2:Depends_on|Part_of]-(l2)
            RETURN type(r1), id(r1), r1, l1.handle_id, port.handle_id, type(r2), id(r2), r2, l2.handle_id
            """
        logical = defaultdict(list)
        with self.manager.read as r:
            for hit in r.execute(q, handle_id=self.handle_id):
                type_r1, id_r1, r1, l1, port, type_r2, id_r2, r2, l2 = hit
                if port:
                    logical[type_r2].append({
                        'port': core.get_model(self.manager, port),
                        'relationship_id': id_r2,
                        'relationship': r2,
                        'node': core.get_model(self.manager, l2)
                    })
                else:
                    logical[type_r1].append({
                        'port': None,
                        'relationship_id': id_r1,
                        'relationship': r1,
                        'node': core.get_model(self.manager, l1)
                    })
        logical.default_factory = None
        return logical


class HostModel(EquipmentModel):

    def get_host_services(self):
        q = """
            MATCH (host {handle_id: {handle_id}})<-[r:Depends_on]-(service:Host_Service)
            RETURN type(r), id(r), r, service.handle_id
            """
        return self._query_to_defaultdict(q)


class OpticalNodeModel(EquipmentModel):
    pass


class RouterModel(EquipmentModel):
    pass