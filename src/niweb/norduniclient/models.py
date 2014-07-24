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

    def _get_handle_id(self):
        return self.data.get('handle_id')
    handle_id = property(_get_handle_id)

    def _incoming(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})<-[r]-(node)
            RETURN type(r), id(r), r, node.handle_id
            """
        return self._basic_read_query_to_dict(q)
    incoming = property(_incoming)

    def _outgoing(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})-[r]->(node)
            RETURN type(r), id(r), r, node.handle_id
            """
        return self._basic_read_query_to_dict(q)
    outgoing = property(_outgoing)

    def _basic_read_query_to_dict(self, query, **kwargs):
        with self.manager.read as r:
            result = r.execute(query, handle_id=self.handle_id, **kwargs).fetchall()
            return self._query_to_dict(result)

    def _basic_write_query_to_dict(self, query, **kwargs):
        with self.manager.transaction as t:
            result = t.execute(query, handle_id=self.handle_id, **kwargs).fetchall()
            return self._query_to_dict(result)

    def _query_to_dict(self, result):
        d = defaultdict(list)
        for row in result:
            rel_type, rel_id, rel, handle_id = row
            d[rel_type].append({
                'relationship_id': rel_id,
                'relationship': rel,
                'node': core.get_model(self.manager, handle_id)
            })
        d.default_factory = None
        return d

    def load(self, node_bundle):
        self.meta_type = node_bundle.get('meta_type')
        self.labels = node_bundle.get('labels')
        self.data = node_bundle.get('data')
        return self


class CommonQueries(BaseModel):
    def get_relations(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})<-[r:Owns|Uses|Provides|Responsible_for]-(node)
            RETURN type(r), id(r), r, node.handle_id
            """
        return self._basic_read_query_to_dict(q)

    def get_incoming_logical(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})<-[r:Depends_on|Part_of]-(node)
            RETURN type(r), id(r), r, node.handle_id
            """
        return self._basic_read_query_to_dict(q)

    def get_outgoing_logical(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})-[r:Depends_on|Part_of]->(node)
            RETURN type(r), id(r), r, node.handle_id
            """
        return self._basic_read_query_to_dict(q)

    def get_location(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})<-[r:Located_in]-(node)
            RETURN type(r), id(r), r, node.handle_id
            """
        return self._basic_read_query_to_dict(q)

    def get_dependent_as_types(self):
        q = """
            MATCH (node {handle_id: {handle_id}})<-[:Depends_on]-(d)
            WITH node, collect(d) as direct
            MATCH (node)<-[:Depends_on*1..20]-(dep)
            WITH direct, collect(dep) as deps
            WITH direct, deps, filter(n in deps WHERE n:Service) as services
            WITH direct, deps, services, filter(n in deps WHERE n:Optical_Path) as paths
            WITH direct, deps, services, paths, filter(n in deps WHERE n:Optical_Multiplex_Section) as oms
            WITH direct, deps, services, paths, oms, filter(n in deps WHERE n:Optical_Link) as links
            RETURN direct, services, paths, oms, links
            """
        return core.query_to_dict(self.manager, q, handle_id=self.handle_id)

    def get_dependencies_as_types(self):
        q = """
            MATCH (node {handle_id: {handle_id}})-[:Depends_on]->(d)
            WITH node, collect(d) as direct
            MATCH node-[:Depends_on*1..20]->dep
            WITH node, direct, collect(dep) as deps
            WITH node, direct, deps, filter(n in deps WHERE n:Service) as services
            WITH node, direct, deps, services, filter(n in deps WHERE n:Optical_Path) as paths
            WITH node, direct, deps, services, paths, filter(n in deps WHERE n:Optical_Multiplex_Section) as oms
            WITH node, direct, deps, services, paths, oms, filter(n in deps WHERE n:Optical_Link) as links
            WITH node, direct, services, paths, oms, links
            OPTIONAL MATCH node-[:Depends_on*1..20]->()-[:Connected_to*1..50]-cable
            WITH distinct direct, cable, services, paths, oms, links
            RETURN direct, services, paths, oms, links, filter(n in collect(cable) WHERE n:Cable) as cables
            """
        return core.query_to_dict(self.manager, q, handle_id=self.handle_id)

    def get_ports(self):
        q = """
            MATCH (node {handle_id: {handle_id}})-[r:Connected_to|Depends_on]-(port:Port)
            WITH port, r
            OPTIONAL MATCH p=port<-[:Has*1..]-parent
            RETURN port, r as relationship, LAST(nodes(p)) as parent
            ORDER BY parent.name
            """
        return core.query_to_list(self.manager, q, handle_id=self.handle_id)


class LogicalModel(CommonQueries):
    pass


class LocationModel(CommonQueries):

    def get_location(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})<-[r:Has]-(node)
            RETURN type(r), id(r), r, node.handle_id
            """
        return self._basic_read_query_to_dict(q)


class EquipmentModel(CommonQueries):

    def get_location_path(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})-[:Located_in]->(r)
            MATCH p=()-[:Has*]->(r)
            WITH COLLECT(nodes(p)) as paths, MAX(length(nodes(p))) AS maxLength
            WITH FILTER(path IN paths WHERE length(path)=maxLength) AS longestPaths
            UNWIND(longestPaths) as Located_in
            RETURN Located_in
            """
        return core.query_to_dict(self.manager, q, handle_id=self.handle_id)


class HostModel(EquipmentModel):

    def get_dependent_as_types(self):  # Does not return Host_Service as a direct dependent
        q = """
            MATCH (node {handle_id: {handle_id}})<-[:Depends_on]-(d)
            WITH node, filter(n in collect(d) WHERE NOT(n:Host_Service)) as direct
            MATCH (node)<-[:Depends_on*1..20]-(dep)
            WITH direct, collect(dep) as deps
            WITH direct, deps, filter(n in deps WHERE n:Service) as services
            WITH direct, deps, services, filter(n in deps WHERE n:Optical_Path) as paths
            WITH direct, deps, services, paths, filter(n in deps WHERE n:Optical_Multiplex_Section) as oms
            WITH direct, deps, services, paths, oms, filter(n in deps WHERE n:Optical_Link) as links
            RETURN direct, services, paths, oms, links
            """
        return core.query_to_dict(self.manager, q, handle_id=self.handle_id)

    def get_host_services(self):
        q = """
            MATCH (host {handle_id: {handle_id}})<-[r:Depends_on]-(service:Host_Service)
            RETURN type(r), id(r), r, service.handle_id
            """
        return self._basic_read_query_to_dict(q)

    def set_user(self, user_handle_id):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})
            MERGE (n)<-[r:Uses]-(user:Host_User {handle_id: {user_handle_id}})
            RETURN type(r), id(r), r, user.handle_id
            """
        return self._basic_write_query_to_dict(q, user_handle_id=user_handle_id)


class OpticalNodeModel(EquipmentModel):
    pass


class RouterModel(EquipmentModel):
    pass
