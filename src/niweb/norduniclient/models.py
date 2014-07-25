# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from collections import defaultdict
import core


class BaseRelationshipModel(object):

    def __init__(self, manager):
        self.manager = manager
        self.id = None
        self.type = None
        self.data = None
        self.start = None
        self.end = None

    def load(self, relationship_bundle):
        self.id = relationship_bundle.get('id')
        self.type = relationship_bundle.get('type')
        self.data = relationship_bundle.get('data')
        self.start = core.get_node_model(self.manager, relationship_bundle.get('start'))
        self.end = core.get_node_model(self.manager, relationship_bundle.get('end'))
        return self

    def delete(self):
        core.delete_relationship(self.manager, self.id)


class BaseNodeModel(object):

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
            return self._read_query_to_dict(result)

    def _read_query_to_dict(self, result):
        d = defaultdict(list)
        for row in result:
            rel_type, rel_id, rel, handle_id = row
            d[rel_type].append({
                'relationship_id': rel_id,
                'relationship': rel,
                'node': core.get_node_model(self.manager, handle_id)
            })
        d.default_factory = None
        return d

    def _basic_write_query_to_dict(self, query, **kwargs):
        with self.manager.transaction as t:
            result = t.execute(query, handle_id=self.handle_id, **kwargs).fetchall()
            return self._write_query_to_dict(result)

    def _write_query_to_dict(self, result):
        d = defaultdict(list)
        for row in result:
            created, rel_type, rel_id, rel, handle_id = row
            d[rel_type].append({
                'created': created,
                'relationship_id': rel_id,
                'relationship': rel,
                'node': core.get_node_model(self.manager, handle_id)
            })
        d.default_factory = None
        return d

    def load(self, node_bundle):
        self.meta_type = node_bundle.get('meta_type')
        self.labels = node_bundle.get('labels')
        self.data = node_bundle.get('data')
        return self

    def change_meta_type(self, meta_type):
        if meta_type == self.meta_type:
            return self
        if meta_type not in core.META_TYPES:
            raise core.exceptions.MetaLabelNamingError(meta_type)
        q = """
            MATCH (n:Node {{handle_id: {{handle_id}}}})
            REMOVE n:{old_meta_type}
            SET n:{meta_type}
            """.format(old_meta_type=self.meta_type, meta_type=meta_type)
        with self.manager.transaction as t:
            t.execute(q, handle_id=self.handle_id).fetchall()
        return core.get_node_model(self.manager, self.handle_id)

    def delete(self):
        core.delete_node(self.manager, self.handle_id)


class CommonQueries(BaseNodeModel):
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

    def set_user(self, user_handle_id):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})
            MERGE (n)<-[r:Uses]-(user:Host_User {handle_id: {user_handle_id}})
            RETURN created, type(r), id(r), r, user.handle_id
            """
        return self._basic_write_query_to_dict(q, user_handle_id=user_handle_id)

    # TODO: Create a method that complains if any relationships that breaks the model exists


class PhysicalModel(CommonQueries):

    def get_location(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})-[r:Located_in]->(node)
            RETURN type(r), id(r), r, node.handle_id
            """
        return self._basic_read_query_to_dict(q)

    def set_owner(self, user_handle_id):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})
            MERGE (n)<-[r:Owns]-(user:Host_User {handle_id: {user_handle_id}})
            RETURN created, type(r), id(r), r, user.handle_id
            """
        return self._basic_write_query_to_dict(q, user_handle_id=user_handle_id)

    # TODO: Create a method that complains if any relationships that breaks the model exists


class LocationModel(CommonQueries):

    def get_location(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})<-[r:Has]-(node)
            RETURN type(r), id(r), r, node.handle_id
            """
        return self._basic_read_query_to_dict(q)


class EquipmentModel(PhysicalModel):

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


class HostModel(CommonQueries):

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


class PhysicalHostModel(HostModel, EquipmentModel):
    pass


class LogicalHostModel(HostModel, LogicalModel):
    pass


class OpticalNodeModel(EquipmentModel):
    pass


class RouterModel(EquipmentModel):
    pass
