from django.db import models
from django.contrib.auth.models import User

import neo4jclient

# Create your models here.

class NodeType(models.Model):
    type = models.CharField(unique=True, max_length=200)
    slug = models.SlugField(unique=True, help_text='Suggested value \
        #automatically generated from type. Must be unique.')

    def __unicode__(self):
        return self.type

    @models.permalink
    def get_absolute_url(self): # TODO
        pass

class NodeHandle(models.Model):
    # Handle <-> Node data
    handle_id = models.AutoField(primary_key=True)
    node_id = models.BigIntegerField(blank=True, unique=True,
        editable=False)

    # Data shared with the node
    node_name = models.CharField(max_length=200)
    node_type = models.ForeignKey(NodeType)

    # Meta information
    creator = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return '%s %s' % (self.node_type, self.node_name)

    @models.permalink
    def get_absolute_url(self): # TODO
        pass

    def save(self):
        '''
        Create a new node and associate it to the handle.
        '''
        nc = neo4jclient.Neo4jClient()
        node = nc.create_node(self.node_name, str(self.node_type))
        self.node_id = node.id
        nc.root.Have(node) # Needs to be changed to the right meta node
        super(NodeHandle, self).save()

