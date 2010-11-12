from django.db import models
from django.contrib.auth.models import User

import neo4jclient

NODE_META_TYPE_CHOICES = (
    ('logical', 'Logical'),
    ('physical', 'Physical'),
    ('organisation', 'Organisation'),
    ('location', 'Location'),
)

class NodeType(models.Model):
    type = models.CharField(unique=True, max_length=255)
    slug = models.SlugField(unique=True, help_text='Suggested value \
        #automatically generated from type. Must be unique.')

    def __unicode__(self):
        return self.type

    def get_slug(self):
        return self.slug

    @models.permalink
    def get_absolute_url(self): # TODO
        return('niweb.noclook.views.list_by_type', (), {
            'slug': self.slug})

class NodeHandle(models.Model):
    # Handle <-> Node data
    handle_id = models.AutoField(primary_key=True)
    node_id = models.BigIntegerField(blank=True, unique=True,
        editable=False)

    # Data shared with the node
    node_name = models.CharField(max_length=200)
    node_type = models.ForeignKey(NodeType)
    node_meta_type = models.CharField(max_length=255,
        choices=NODE_META_TYPE_CHOICES)

    # Meta information
    creator = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return '%s %s' % (self.node_type, self.node_name)

    @models.permalink
    def get_absolute_url(self):
        '''
        Should we instead import neo4jclient here and traverse the node
        to to root? That way we can do urls like se-tug/fpc/pic/port or
        dk-ore-lm-01/rack/sub_rack/.
        '''
        #return '%s/%d/' % (self.node_type, self.handle_id)
        return('niweb.noclook.views.detail', (), {
            'slug': self.node_type.get_slug(),
            'handle_id': self.handle_id})

    def save(self):
        '''
        Create a new node and associate it to the handle.
        '''
        nc = neo4jclient.Neo4jClient()
        node = nc.create_node(self.node_name, str(self.node_type))
        self.node_id = node.id
        meta_node = nc.get_meta_node(str(self.node_meta_type))
        meta_node.Contains(node)
        try:
            super(NodeHandle, self).save()
        except Exception as e:
            # If you cant write to the sql db undo the neo4j change
            print 'test'
            nc.delete_node(node.id)
            print e


