# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from functools import total_ordering
from collections import defaultdict
import core


@total_ordering
class BaseRelationshipModel(object):

    def __init__(self, manager):
        self.manager = manager
        self.id = None
        self.type = None
        self.data = None
        self.start = None
        self.end = None

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return u'({start})-[{id}:{type}{data}]->({end}) in database {db}.'.format(
            start=self.start, type=self.type, id=self.id, data=self.data, end=self.end,
            db=self.manager.dsn
        )

    def __eq__(self, other):
        return self.id == other.id

    def __lt__(self, other):
        return self.id < other.id

    def __repr__(self):
        return u'<{c} id:{id} in {db}>'.format(c=self.__class__.__name__, id=self.id, db=self.manager.dsn)

    def load(self, relationship_bundle):
        self.id = relationship_bundle.get('id')
        self.type = relationship_bundle.get('type')
        self.data = relationship_bundle.get('data')
        self.start = relationship_bundle.get('start')
        self.end = relationship_bundle.get('end')
        return self

    def delete(self):
        core.delete_relationship(self.manager, self.id)


@total_ordering
class BaseNodeModel(object):

    def __init__(self, manager):
        self.manager = manager
        self.meta_type = None
        self.labels = None
        self.data = None

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        labels = ':'.join(self.labels)
        return u'(node:{meta_type}:{labels} {data}) in database {db}.'.format(
            meta_type=self.meta_type, labels=labels, data=self.data, db=self.manager.dsn
        )

    def __eq__(self, other):
        return self.handle_id == other.handle_id

    def __lt__(self, other):
        return self.handle_id < other.handle_id

    def __repr__(self):
        return u'<{c} handle_id:{handle_id} in {db}>'.format(c=self.__class__.__name__, handle_id=self.handle_id,
                                                             db=self.manager.dsn)

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

    def _relationships(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})-[r]-(node)
            RETURN type(r), id(r), r, node.handle_id
            """
        return self._basic_read_query_to_dict(q)
    relationships = property(_relationships)

    def _basic_read_query_to_dict(self, query, **kwargs):
        d = defaultdict(list)
        with self.manager.read as r:
            result = r.execute(query, handle_id=self.handle_id, **kwargs).fetchall()
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
        d = defaultdict(list)
        with self.manager.transaction as t:
            result = t.execute(query, handle_id=self.handle_id, **kwargs).fetchall()
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

    def add_label(self, label):
        q = """
            MATCH (n:Node {{handle_id: {{handle_id}}}})
            SET n:{label}
            """.format(old_meta_type=self.meta_type, label=label)
        with self.manager.transaction as t:
            t.execute(q, handle_id=self.handle_id).fetchall()
        return True

    def remove_label(self, label):
        q = """
            MATCH (n:Node {{handle_id: {{handle_id}}}})
            REMOVE n:{label}
            """.format(old_meta_type=self.meta_type, label=label)
        with self.manager.transaction as t:
            t.execute(q, handle_id=self.handle_id).fetchall()
        return True

    def change_meta_type(self, meta_type):
        if meta_type not in core.META_TYPES:
            raise core.exceptions.MetaLabelNamingError(meta_type)
        if meta_type == self.meta_type:
            return self
        if self.remove_label(self.meta_type):
            self.add_label(meta_type)
        return core.get_node_model(self.manager, self.handle_id)

    def switch_type(self, old_type, new_type):
        if old_type == new_type:
            return self
        if self.remove_label(old_type):
            self.add_label(new_type)
        return core.get_node_model(self.manager, self.handle_id)

    def delete(self):
        core.delete_node(self.manager, self.handle_id)


class CommonQueries(BaseNodeModel):

    def get_location_path(self):
        return {'location_path': []}

    def get_placement_path(self):
        return {'placement_path': []}

    def get_location(self):
        return {}

    def get_child_form_data(self, node_type):
        type_filter = ''
        if node_type:
            type_filter = 'and child:{node_type}'.format(node_type=node_type)
        q = """
            MATCH (parent:Node {{handle_id:{{handle_id}}}})
            MATCH parent--child
            WHERE (parent-[:Has]->child or parent<-[:Located_in|Part_of]-child) {type_filter}
            RETURN child.handle_id as handle_id, labels(child) as labels, child.name as name,
                   child.description as description
            """.format(type_filter=type_filter)
        return core.query_to_list(self.manager, q, handle_id=self.handle_id)

    def get_relations(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})<-[r:Owns|Uses|Provides|Responsible_for]-(node)
            RETURN type(r), id(r), r, node.handle_id
            """
        return self._basic_read_query_to_dict(q)

    def get_dependencies(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})-[r:Depends_on]->(node)
            RETURN type(r), id(r), r, node.handle_id
            """
        return self._basic_read_query_to_dict(q)

    def get_dependents(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})<-[r:Depends_on]-(node)
            RETURN type(r), id(r), r, node.handle_id
            """
        return self._basic_read_query_to_dict(q)

    def get_dependent_as_types(self):
        q = """
            MATCH (node:Node {handle_id: {handle_id}})<-[:Depends_on]-(d)
            WITH node, collect(DISTINCT d) as direct
            MATCH (node)<-[:Depends_on*1..20]-(dep)
            WITH direct, collect(DISTINCT dep) as deps
            WITH direct, deps, filter(n in deps WHERE n:Service) as services
            WITH direct, deps, services, filter(n in deps WHERE n:Optical_Path) as paths
            WITH direct, deps, services, paths, filter(n in deps WHERE n:Optical_Multiplex_Section) as oms
            WITH direct, deps, services, paths, oms, filter(n in deps WHERE n:Optical_Link) as links
            RETURN direct, services, paths, oms, links
            """
        return core.query_to_dict(self.manager, q, handle_id=self.handle_id)

    def get_dependencies_as_types(self):
        q = """
            MATCH (node:Node {handle_id: {handle_id}})-[:Depends_on]->(d)
            WITH node, collect(DISTINCT d) as direct
            MATCH node-[:Depends_on*1..20]->dep
            WITH node, direct, collect(DISTINCT dep) as deps
            WITH node, direct, deps, filter(n in deps WHERE n:Service) as services
            WITH node, direct, deps, services, filter(n in deps WHERE n:Optical_Path) as paths
            WITH node, direct, deps, services, paths, filter(n in deps WHERE n:Optical_Multiplex_Section) as oms
            WITH node, direct, deps, services, paths, oms, filter(n in deps WHERE n:Optical_Link) as links
            WITH node, direct, services, paths, oms, links
            OPTIONAL MATCH node-[:Depends_on*1..20]->()-[:Connected_to*1..50]-cable
            RETURN direct, services, paths, oms, links, filter(n in collect(DISTINCT cable) WHERE n:Cable) as cables
            """
        return core.query_to_dict(self.manager, q, handle_id=self.handle_id)

    def get_ports(self):
        q = """
            MATCH (node:Node {handle_id: {handle_id}})-[r:Connected_to|Depends_on]-(port:Port)
            WITH port, r
            OPTIONAL MATCH p=port<-[:Has*1..]-parent
            RETURN port, r as relationship, LAST(nodes(p)) as parent
            ORDER BY parent.name
            """
        return core.query_to_list(self.manager, q, handle_id=self.handle_id)


class LogicalModel(CommonQueries):

    def get_part_of(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})-[r:Part_of]->(node)
            RETURN type(r), id(r), r, node.handle_id
            """
        return self._basic_read_query_to_dict(q)

    def set_user(self, user_handle_id):
        q = """
            MATCH (n:Node {handle_id: {handle_id}}), (user:Node {handle_id: {user_handle_id}})
            WITH n, user, NOT EXISTS((n)<-[:Uses]-(user)) as created
            MERGE (n)<-[r:Uses]-(user)
            RETURN created, type(r), id(r), r, user.handle_id
            """
        return self._basic_write_query_to_dict(q, user_handle_id=user_handle_id)

    def set_provider(self, provider_handle_id):
        q = """
            MATCH (n:Node {handle_id: {handle_id}}), (provider:Node {handle_id: {provider_handle_id}})
            WITH n, provider, NOT EXISTS((n)<-[:Provides]-(provider)) as created
            MERGE (n)<-[r:Provides]-(provider)
            RETURN created, type(r), id(r), r, provider.handle_id
            """
        return self._basic_write_query_to_dict(q, provider_handle_id=provider_handle_id)

    def set_dependency(self, dependency_handle_id):
        q = """
            MATCH (n:Node {handle_id: {handle_id}}), (dependency:Node {handle_id: {dependency_handle_id}})
            WITH n, dependency, NOT EXISTS((n)-[:Depends_on]->(dependency)) as created
            MERGE (n)-[r:Depends_on]->(dependency)
            RETURN created, type(r), id(r), r, dependency.handle_id
            """
        return self._basic_write_query_to_dict(q, dependency_handle_id=dependency_handle_id)

    def get_connections(self):  # Logical versions of physical things can't have physical connections
        return []

    # TODO: Create a method that complains if any relationships that breaks the model exists


class PhysicalModel(CommonQueries):

    def get_location(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})-[r:Located_in]->(node)
            RETURN type(r), id(r), r, node.handle_id
            """
        return self._basic_read_query_to_dict(q)

    def set_owner(self, owner_handle_id):
        q = """
            MATCH (n:Node {handle_id: {handle_id}}), (owner:Node {handle_id: {owner_handle_id}})
            WITH n, owner, NOT EXISTS((n)<-[:Owns]-(owner)) as created
            MERGE (n)<-[r:Owns]-(owner)
            RETURN created, type(r), id(r), r, owner.handle_id
            """
        return self._basic_write_query_to_dict(q, owner_handle_id=owner_handle_id)

    def set_provider(self, provider_handle_id):
        q = """
            MATCH (n:Node {handle_id: {handle_id}}), (provider:Node {handle_id: {provider_handle_id}})
            WITH n, provider, NOT EXISTS((n)<-[:Provides]-(provider)) as created
            MERGE (n)<-[r:Provides]-(provider)
            RETURN created, type(r), id(r), r, provider.handle_id
            """
        return self._basic_write_query_to_dict(q, provider_handle_id=provider_handle_id)

    def set_location(self, location_handle_id):
        q = """
            MATCH (n:Node {handle_id: {handle_id}}), (location:Node {handle_id: {location_handle_id}})
            WITH n, location, NOT EXISTS((n)-[:Located_in]->(location)) as created
            MERGE (n)-[r:Located_in]->(location)
            RETURN created, type(r), id(r), r, location.handle_id
            """
        return self._basic_write_query_to_dict(q, location_handle_id=location_handle_id)

    def get_has(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})-[r:Has]->(part:Physical)
            RETURN type(r), id(r), r, part.handle_id
            """
        return self._basic_read_query_to_dict(q)

    def set_has(self, has_handle_id):
        q = """
            MATCH (n:Node {handle_id: {handle_id}}), (part:Node {handle_id: {has_handle_id}})
            WITH n, part, NOT EXISTS((n)-[:Has]->(part)) as created
            MERGE (n)-[r:Has]->(part)
            RETURN created, type(r), id(r), r, part.handle_id
            """
        return self._basic_write_query_to_dict(q, has_handle_id=has_handle_id)

    def get_part_of(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})<-[r:Part_of]-(part:Logical)
            RETURN type(r), id(r), r, part.handle_id
            """
        return self._basic_read_query_to_dict(q)

    def set_part_of(self, part_handle_id):
        q = """
            MATCH (n:Node {handle_id: {handle_id}}), (part:Node:Logical {handle_id: {part_handle_id}})
            WITH n, part, NOT EXISTS((n)<-[:Part_of]-(part)) as created
            MERGE (n)<-[r:Part_of]-(part)
            RETURN created, type(r), id(r), r, part.handle_id
            """
        return self._basic_write_query_to_dict(q, part_handle_id=part_handle_id)

    def get_parent(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})<-[r:Has]-(parent)
            RETURN type(r), id(r), r, parent.handle_id
            """
        return self._basic_read_query_to_dict(q)

    # TODO: Create a method that complains if any relationships that breaks the model exists


class LocationModel(CommonQueries):

    def get_location_path(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})<-[:Has]-(r)
            MATCH p=()-[:Has*0..20]->(r)
            WITH COLLECT(nodes(p)) as paths, MAX(length(nodes(p))) AS maxLength
            WITH FILTER(path IN paths WHERE length(path)=maxLength) AS longestPaths
            UNWIND(longestPaths) as location_path
            RETURN location_path
            """
        return core.query_to_dict(self.manager, q, handle_id=self.handle_id)

    def get_parent(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})<-[r:Has]-(parent)
            RETURN type(r), id(r), r, parent.handle_id
            """
        return self._basic_read_query_to_dict(q)

    def get_located_in(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})<-[r:Located_in]-(node)
            RETURN type(r), id(r), r, node.handle_id
            """
        return self._basic_read_query_to_dict(q)

    def get_has(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})-[r:Has]->(node:Location)
            RETURN type(r), id(r), r, node.handle_id
            """
        return self._basic_read_query_to_dict(q)

    def set_has(self, has_handle_id):
        q = """
            MATCH (n:Node {handle_id: {handle_id}}), (part:Node {handle_id: {has_handle_id}})
            WITH n, part, NOT EXISTS((n)-[:Has]->(part)) as created
            MERGE (n)-[r:Has]->(part)
            RETURN created, type(r), id(r), r, part.handle_id
            """
        return self._basic_write_query_to_dict(q, has_handle_id=has_handle_id)

    def set_responsible_for(self, owner_handle_id):
        q = """
            MATCH (n:Node {handle_id: {handle_id}}), (owner:Node {handle_id: {owner_handle_id}})
            WITH n, owner, NOT EXISTS((n)<-[:Responsible_for]-(owner)) as created
            MERGE (n)<-[r:Responsible_for]-(owner)
            RETURN created, type(r), id(r), r, owner.handle_id
            """
        return self._basic_write_query_to_dict(q, owner_handle_id=owner_handle_id)


class RelationModel(CommonQueries):

    def with_same_name(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}}), (other:Node:Relation {name: {name}})
            WHERE other.handle_id <> n.handle_id
            RETURN COLLECT(other.handle_id) as ids
            """
        return core.query_to_dict(self.manager, q, handle_id=self.handle_id, name=self.data.get('name'))

    def get_uses(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})-[r:Uses]->(usable)
            RETURN type(r), id(r), r, usable.handle_id
            """
        return self._basic_read_query_to_dict(q)

    def get_provides(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})-[r:Provides]->(usable)
            RETURN type(r), id(r), r, usable.handle_id
            """
        return self._basic_read_query_to_dict(q)

    def get_owns(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})-[r:Owns]->(usable)
            RETURN type(r), id(r), r, usable.handle_id
            """
        return self._basic_read_query_to_dict(q)

    def get_responsible_for(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})-[r:Responsible_for]->(usable)
            RETURN type(r), id(r), r, usable.handle_id
            """
        return self._basic_read_query_to_dict(q)


class EquipmentModel(PhysicalModel):

    def get_location_path(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})-[:Located_in]->(r)
            MATCH p=()-[:Has*0..20]->(r)
            WITH COLLECT(nodes(p)) as paths, MAX(length(nodes(p))) AS maxLength
            WITH FILTER(path IN paths WHERE length(path)=maxLength) AS longestPaths
            UNWIND(longestPaths) as location_path
            RETURN location_path
            """
        return core.query_to_dict(self.manager, q, handle_id=self.handle_id)

    def get_ports(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})-[r:Has]->(port:Port)
            RETURN type(r), id(r), r, port.handle_id
            """
        return self._basic_read_query_to_dict(q)

    def get_port(self, port_name):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})-[r:Has]->(port:Port)
            WHERE port.name = {port_name}
            RETURN type(r), id(r), r, port.handle_id
            """
        return self._basic_read_query_to_dict(q, port_name=port_name)

    def get_dependent_as_types(self):
        q = """
            MATCH (node:Node {handle_id: {handle_id}})
            OPTIONAL MATCH (node)<-[:Depends_on]-(d)
            WITH node, collect(DISTINCT d) as direct
            OPTIONAL MATCH (node)-[:Has*1..20]->()<-[:Part_of|Depends_on*1..20]-(dep)
            OPTIONAL MATCH (node)-[:Has*1..20]->()<-[:Connected_to]-()-[:Connected_to]->()<-[:Depends_on*1..20]-(cable_dep)
            WITH direct, collect(DISTINCT dep) + collect(DISTINCT cable_dep) as coll UNWIND coll AS x
            WITH direct, collect(DISTINCT x) as deps
            WITH direct, deps, filter(n in deps WHERE n:Service) as services
            WITH direct, deps, services, filter(n in deps WHERE n:Optical_Path) as paths
            WITH direct, deps, services, paths, filter(n in deps WHERE n:Optical_Multiplex_Section) as oms
            WITH direct, deps, services, paths, oms, filter(n in deps WHERE n:Optical_Link) as links
            RETURN direct, services, paths, oms, links
            """
        return core.query_to_dict(self.manager, q, handle_id=self.handle_id)

    def get_connections(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})-[:Has*1..10]->(porta:Port)
            OPTIONAL MATCH (porta)<-[r0:Connected_to]-(cable)  // Needed to get cable with just one endpoint
            OPTIONAL MATCH (porta)<-[r0:Connected_to]-(cable)-[r1:Connected_to]->(portb:Port)
            OPTIONAL MATCH (portb)<-[:Has*1..10]-(end)
            WITH  porta, r0, cable, portb, r1, last(collect(end)) as end
            OPTIONAL MATCH (end)-[:Located_in]->(location)
            OPTIONAL MATCH (location)<-[:Has]-site
            RETURN porta, r0, cable, r1, portb, end, location, site
            """
        return core.query_to_list(self.manager, q, handle_id=self.handle_id)


class SubEquipmentModel(PhysicalModel):

    def get_location_path(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})<-[:Has]-(parent)
            OPTIONAL MATCH p=()-[:Has*0..20]->(r)<-[:Located_in]-()-[:Has*0..20]->(parent)
            WITH COLLECT(nodes(p)) as paths, MAX(length(nodes(p))) AS maxLength
            WITH FILTER(path IN paths WHERE length(path)=maxLength) AS longestPaths
            UNWIND(longestPaths) as location_path
            RETURN location_path
            """
        return core.query_to_dict(self.manager, q, handle_id=self.handle_id)

    def get_placement_path(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})<-[:Has]-(parent)
            OPTIONAL MATCH p=()-[:Has*0..20]->(parent)
            WITH COLLECT(nodes(p)) as paths, MAX(length(nodes(p))) AS maxLength
            WITH FILTER(path IN paths WHERE length(path)=maxLength) AS longestPaths
            UNWIND(longestPaths) as placement_path
            RETURN placement_path
            """
        return core.query_to_dict(self.manager, q, handle_id=self.handle_id)

    def get_connections(self):
        q = """
            MATCH (porta:Node {handle_id: {handle_id}})<-[r0:Connected_to]-(cable)
            OPTIONAL MATCH (porta)<-[r0:Connected_to]-(cable)-[r1:Connected_to]->(portb)
            OPTIONAL MATCH (portb)<-[:Has*1..10]-(end)
            WITH  porta, r0, cable, portb, r1, last(collect(end)) as end
            OPTIONAL MATCH (end)-[:Located_in]->(location)
            OPTIONAL MATCH (location)<-[:Has]-site
            RETURN porta, r0, cable, r1, portb, end, location, site
            """
        return core.query_to_list(self.manager, q, handle_id=self.handle_id)


class HostModel(CommonQueries):

    def get_dependent_as_types(self):  # Does not return Host_Service as a direct dependent
        q = """
            MATCH (node:Node {handle_id: {handle_id}})<-[:Depends_on]-(d)
            WITH node, filter(n in collect(DISTINCT d) WHERE NOT(n:Host_Service)) as direct
            MATCH (node)<-[:Depends_on*1..20]-(dep)
            WITH direct, collect(DISTINCT dep) as deps
            WITH direct, deps, filter(n in deps WHERE n:Service) as services
            WITH direct, deps, services, filter(n in deps WHERE n:Optical_Path) as paths
            WITH direct, deps, services, paths, filter(n in deps WHERE n:Optical_Multiplex_Section) as oms
            WITH direct, deps, services, paths, oms, filter(n in deps WHERE n:Optical_Link) as links
            RETURN direct, services, paths, oms, links
            """
        return core.query_to_dict(self.manager, q, handle_id=self.handle_id)

    def get_host_services(self):
        q = """
            MATCH (host:Node {handle_id: {handle_id}})<-[r:Depends_on]-(service:Host_Service)
            RETURN type(r), id(r), r, service.handle_id
            """
        return self._basic_read_query_to_dict(q)

    def get_host_service(self, service_handle_id, ip_address, port, protocol):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})<-[r:Depends_on]-(host_service:Node {handle_id: {service_handle_id}})
            WHERE r.ip_address={ip_address} AND r.port={port} AND r.protocol={protocol}
            RETURN type(r), id(r), r, host_service.handle_id
            """
        return self._basic_read_query_to_dict(q, service_handle_id=service_handle_id, ip_address=ip_address, port=port,
                                              protocol=protocol)

    def set_host_service(self, service_handle_id, ip_address, port, protocol):
        q = """
            MATCH (n:Node {handle_id: {handle_id}}), (host_service:Node {handle_id: {service_handle_id}})
            CREATE (n)<-[r:Depends_on {ip_address:{ip_address}, port:{port}, protocol:{protocol}}]-(host_service)
            RETURN true as created, type(r), id(r), r, host_service.handle_id
            """
        return self._basic_write_query_to_dict(q, service_handle_id=service_handle_id, ip_address=ip_address,
                                               port=port, protocol=protocol)


class PhysicalHostModel(HostModel, EquipmentModel):
    pass


class LogicalHostModel(HostModel, LogicalModel):
    pass


class PortModel(SubEquipmentModel):

    def get_units(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})<-[r:Part_of]-(unit:Unit)
            RETURN type(r), id(r), r, unit.handle_id
            """
        return self._basic_read_query_to_dict(q)

    def get_unit(self, unit_name):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})<-[r:Part_of]-(unit:Unit)
            WHERE unit.name = {unit_name}
            RETURN type(r), id(r), r, unit.handle_id
            """
        return self._basic_read_query_to_dict(q, unit_name=unit_name)

    def get_connected_to(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})<-[r:Connected_to]-(cable:Cable)
            RETURN type(r), id(r), r, cable.handle_id
            """
        return self._basic_read_query_to_dict(q)

    def get_connection_path(self):
        q = """
            MATCH (n:Port {handle_id: {handle_id}})-[:Connected_to*0..10]-(port:Port)
            OPTIONAL MATCH path=(port)-[:Connected_to*]-()
            WITH nodes(path) AS parts, length(path) AS len
            ORDER BY len DESC
            LIMIT 1
            UNWIND parts AS part
            OPTIONAL MATCH (part)<-[:Has*1..10]-(parent)
            WHERE NOT (parent)<-[:Has]-()
            RETURN part, parent
            """
        return core.query_to_list(self.manager, q, handle_id=self.handle_id)


class OpticalNodeModel(EquipmentModel):
    pass


class RouterModel(EquipmentModel):

    def get_child_form_data(self, node_type):
        if node_type:
            type_filter = ':{node_type}'.format(node_type)
        else:
            type_filter = ':Port'
        q = """
            MATCH (parent:Node {{handle_id:{{handle_id}}}})
            MATCH parent-[:Has*]->(child{type_filter})
            RETURN child.handle_id as handle_id, labels(child) as labels, child.name as name,
                   child.description as description
            ORDER BY child.name
            """.format(type_filter=type_filter)
        return core.query_to_list(self.manager, q, handle_id=self.handle_id)


class PeeringPartnerModel(RelationModel):

    def get_peering_groups(self):
        q = """
            MATCH (host:Node {handle_id: {handle_id}})-[r:Uses]->(group:Peering_Group)
            RETURN type(r), id(r), r, group.handle_id
            """
        return self._basic_read_query_to_dict(q)

    def get_peering_group(self, group_handle_id, ip_address):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})-[r:Uses]->(group:Node {handle_id: {group_handle_id}})
            WHERE r.ip_address={ip_address}
            RETURN type(r), id(r), r, group.handle_id
            """
        return self._basic_read_query_to_dict(q, group_handle_id=group_handle_id, ip_address=ip_address)

    def set_peering_group(self, group_handle_id, ip_address):
        q = """
            MATCH (n:Node {handle_id: {handle_id}}), (group:Node {handle_id: {group_handle_id}})
            CREATE (n)-[r:Uses {ip_address:{ip_address}}]->(group)
            RETURN true as created, type(r), id(r), r, group.handle_id
            """
        return self._basic_write_query_to_dict(q, group_handle_id=group_handle_id, ip_address=ip_address)


class PeeringGroupModel(LogicalModel):

    def get_group_dependency(self, dependency_handle_id, ip_address):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})-[r:Depends_on]->(dependency:Node {handle_id: {dependency_handle_id}})
            WHERE r.ip_address={ip_address}
            RETURN type(r), id(r), r, dependency.handle_id
            """
        return self._basic_read_query_to_dict(q, dependency_handle_id=dependency_handle_id, ip_address=ip_address)

    def set_group_dependency(self, dependency_handle_id, ip_address):
        q = """
            MATCH (n:Node {handle_id: {handle_id}}), (dependency:Node {handle_id: {dependency_handle_id}})
            CREATE (n)-[r:Depends_on {ip_address:{ip_address}}]->(dependency)
            RETURN true as created, type(r), id(r), r, dependency.handle_id
            """
        return self._basic_write_query_to_dict(q, dependency_handle_id=dependency_handle_id, ip_address=ip_address)


class CableModel(PhysicalModel):

    def get_connected_equipment(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})-[rel:Connected_to]->(port)
            OPTIONAL MATCH (port)<-[:Has*1..10]-(end)
            WITH  rel, port, last(collect(end)) as end
            OPTIONAL MATCH (end)-[:Located_in]->(location)
            OPTIONAL MATCH (location)<-[:Has]-(site)
            RETURN id(rel) as rel_id, rel, port, end, location, site
            ORDER BY end.name, port.name
            """
        return core.query_to_list(self.manager, q, handle_id=self.handle_id)

    def get_dependent_as_types(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})-[:Connected_to*1..20]-(equip)
            WITH DISTINCT equip
            MATCH (equip)<-[:Depends_on*1..10]-(dep)
            WITH collect(DISTINCT dep) as deps
            WITH deps, filter(n in deps WHERE n:Service) as services
            WITH deps, services, filter(n in deps WHERE n:Optical_Path) as paths
            WITH deps, services, paths, filter(n in deps WHERE n:Optical_Multiplex_Section) as oms
            WITH deps, services, paths, oms, filter(n in deps WHERE n:Optical_Link) as links
            RETURN services, paths, oms, links
            """
        return core.query_to_dict(self.manager, q, handle_id=self.handle_id)

    def get_services(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})
            MATCH (n)-[:Connected_to*1..20]-(equip)
            WITH equip
            MATCH (equip)<-[:Depends_on*1..10]-(service)
            WHERE service:Service
            WITH distinct service
            OPTIONAL MATCH service<-[:Uses]-user
            RETURN service, collect(user) as users
            """
        return core.query_to_list(self.manager, q, handle_id=self.handle_id)

    def get_connection_path(self):
        q = """
            MATCH (n:Cable {handle_id: {handle_id}})-[:Connected_to*1..10]-(port:Port)
            OPTIONAL MATCH path=(port)-[:Connected_to*]-()
            WITH nodes(path) AS parts, length(path) AS len
            ORDER BY len DESC
            LIMIT 1
            UNWIND parts AS part
            OPTIONAL MATCH (part)<-[:Has*1..10]-(parent)
            WHERE NOT (parent)<-[:Has]-()
            RETURN part, parent
            """
        return core.query_to_list(self.manager, q, handle_id=self.handle_id)

    def set_connected_to(self, connected_to_handle_id):
        q = """
            MATCH (n:Node {handle_id: {handle_id}}), (part:Node {handle_id: {connected_to_handle_id}})
            WITH n, part, NOT EXISTS((n)-[:Connected_to]->(part)) as created
            MERGE (n)-[r:Connected_to]->(part)
            RETURN created, type(r), id(r), r, part.handle_id
            """
        return self._basic_write_query_to_dict(q, connected_to_handle_id=connected_to_handle_id)


class UnitModel(LogicalModel):

    def get_placement_path(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})-[:Part_of]->(parent)
            OPTIONAL MATCH p=()-[:Has*0..20]->(parent)
            WITH COLLECT(nodes(p)) as paths, MAX(length(nodes(p))) AS maxLength
            WITH FILTER(path IN paths WHERE length(path)=maxLength) AS longestPaths
            UNWIND(longestPaths) as placement_path
            RETURN placement_path
            """
        return core.query_to_dict(self.manager, q, handle_id=self.handle_id)

    def get_location_path(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})-[:Part_of]->(parent)
            OPTIONAL MATCH p=()-[:Has*0..20]->(r)<-[:Located_in]-()-[:Has*0..20]->(parent)
            WITH COLLECT(nodes(p)) as paths, MAX(length(nodes(p))) AS maxLength
            WITH FILTER(path IN paths WHERE length(path)=maxLength) AS longestPaths
            UNWIND(longestPaths) as location_path
            RETURN location_path
            """
        return core.query_to_dict(self.manager, q, handle_id=self.handle_id)


class ServiceModel(LogicalModel):

    def get_customers(self):
        q = """
            MATCH (n:Node {handle_id: {handle_id}})<-[r:Owns|Uses]-(customer:Customer)
            RETURN "customers", id(r), r, customer.handle_id
            """
        return self._basic_read_query_to_dict(q)


class ExternalEquipmentModel(EquipmentModel):
    pass


class ODFModel(EquipmentModel):
    pass

class OpticalFilterModel(EquipmentModel):
    pass

class SwitchModel(EquipmentModel, HostModel):
    pass


class FirewallModel(EquipmentModel, HostModel):
    pass


class PDUModel(EquipmentModel, HostModel):
    pass


class PICModel(SubEquipmentModel):
    pass


class FPCModel(SubEquipmentModel):
    pass
