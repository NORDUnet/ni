# -*- coding: utf-8 -*-
from django.db import models, utils
from django.contrib.auth.models import User
from django.contrib.comments.signals import comment_was_posted, comment_was_flagged
from django.dispatch import receiver
from django.contrib.comments import Comment
from actstream import action

import norduni_client as nc


NODE_META_TYPE_CHOICES = (
    ('logical', 'Logical'),
    ('physical', 'Physical'),
    ('relation', 'Relation'),
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
    def get_absolute_url(self):
        return('niweb.apps.noclook.views.list_by_type', (), {
            'slug': self.slug})
            
    def delete(self, **kwargs):
        """
        Delete the NodeType object with all associated NodeHandles.
        """
        for nh in NodeHandle.objects.filter(node_type=self.pk):
            nh.delete() 
        super(NodeType, self).delete()
        return True
    delete.alters_data = True

class NodeHandle(models.Model):
    # Handle <-> Node data
    handle_id = models.AutoField(primary_key=True)
    node_id = models.BigIntegerField(null=True, blank=True, unique=True,
        editable=False)
    # Data shared with the node
    node_name = models.CharField(max_length=200)
    node_type = models.ForeignKey(NodeType)
    node_meta_type = models.CharField(max_length=255,
        choices=NODE_META_TYPE_CHOICES)
    # Meta information
    creator = models.ForeignKey(User, related_name='creator')
    created = models.DateTimeField(auto_now_add=True)
    modifier = models.ForeignKey(User, related_name='modifier')
    modified = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return '%s %s' % (self.node_type, self.node_name)
        
    def get_node(self):
        """
        Returns the NodeHandles node.
        """
        return nc.get_node_by_id(nc.neo4jdb, self.node_id)

    @models.permalink
    def get_absolute_url(self):
        """
        Should we instead import neo4jclient here and traverse the node
        to to root? That way we can do urls like se-tug/fpc/pic/port or
        dk-ore-lm-01/rack/sub_rack/.
        """
        #return '%s/%d/' % (self.node_type, self.handle_id)
        return('niweb.apps.noclook.views.generic_detail', (), {
            'slug': self.node_type.get_slug(),
            'handle_id': self.handle_id})

    def save(self, create_node=False, *args, **kwargs):
        """
        Create a new node and associate it to the handle.
        """
        if self.node_id and not create_node: # Don't create a node
            super(NodeHandle, self).save(*args, **kwargs)
            return self
        node = nc.create_node(nc.neo4jdb, self.node_name, str(self.node_type))
        self.node_id = node.id
        try:
            super(NodeHandle, self).save(*args, **kwargs)
        except utils.IntegrityError as e:
            print e
            print 'Node ID: %d' % node.id
            raise Exception(e)
        meta_node = nc.get_meta_node(nc.neo4jdb, str(self.node_meta_type))
        node = nc.get_node_by_id(nc.neo4jdb, self.node_id)
        with nc.neo4jdb.transaction:
            node['handle_id'] = int(self.handle_id)
            meta_node.Contains(node)
        return self
    
    save.alters_data = True

    def delete(self, **kwargs):
        """
        Delete that node handle and the handles node.
        """
        try:
            node = self.get_node()
            nc.delete_node(nc.neo4jdb, node)
        except (KeyError, TypeError):
            # Node already deleted or None was passed as node id
            pass
        Comment.objects.filter(object_pk=self.pk).delete()
        super(NodeHandle, self).delete()
        return True
        
    delete.alters_data = True


class UniqueIdGenerator(models.Model):
    """
    Model that provides a base id counter, prefix, suffix and id length. When a new
    id is generated the base id counter will increase by 1.
    """
    name = models.CharField(max_length=256, unique=True)
    base_id = models.IntegerField(default=1)
    zfill = models.BooleanField()
    base_id_length = models.IntegerField(default=0,
                                         help_text="Base id will be filled with leading zeros to this length if zfill is checked.")
    prefix = models.CharField(max_length=256, null=True, blank=True)
    suffix = models.CharField(max_length=256, null=True, blank=True)
    last_id = models.CharField(max_length=256, editable=False)
    next_id = models.CharField(max_length=256, editable=False)
    # Meta
    creator = models.ForeignKey(User, related_name='unique_id_creator')
    created = models.DateTimeField(auto_now_add=True)
    modifier = models.ForeignKey(User, null=True, blank=True, related_name='unique_id_modifier')
    modified = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.name

    def get_id(self):
        """
        Returns the next id and increments the base_id field.
        """
        base_id = self.base_id
        if self.zfill:
            base_id = str(self.base_id).zfill(self.base_id_length)
        prefix = suffix = ''
        if self.prefix: prefix = self.prefix
        if self.suffix: suffix = self.suffix
        unique_id = '%s%s%s' % (prefix, base_id, suffix)
        self.last_id = unique_id
        self.base_id += 1
        self.save()
        return unique_id

    def save(self, *args, **kwargs):
        """
        Increments the base_id.
        """
        base_id = self.base_id
        if self.zfill:
            base_id = str(self.base_id).zfill(self.base_id_length)
        prefix = suffix = ''
        if self.prefix: prefix = self.prefix
        if self.suffix: suffix = self.suffix
        self.next_id = '%s%s%s' % (prefix, base_id, suffix)
        super(UniqueIdGenerator, self).save(*args, **kwargs)

    save.alters_data = True


class UniqueId(models.Model):
    """
    Table for reserving ids and to help ensuring uniqueness across the
    different node types.
    """
    unique_id = models.CharField(max_length=256, unique=True)
    reserved = models.BooleanField(default=False)
    reserve_message = models.CharField(max_length=512, null=True, blank=True)
    reserver = models.ForeignKey(User, null=True, blank=True)
    # Meta
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    def __unicode__(self):
        return unicode(self.unique_id)


class NordunetUniqueId(UniqueId):
    """
    Collection of all NORDUnet IDs to ensure uniqueness.
    """

    def __unicode__(self):
        return unicode('NORDUnet: %s' % self.unique_id)


## Signals
@receiver(comment_was_posted, dispatch_uid="apps.noclook.models")
def comment_posted_handler(sender, comment, request, **kwargs):
    action.send(
        comment.user,
        verb='create',
        action_object=comment,
        target=comment.content_object,
        noclook={
            'action_type': 'comment',
        }
    )

@receiver(comment_was_flagged, dispatch_uid="apps.noclook.models")
def comment_removed_handler(sender, comment, flag, created, request, **kwargs):
    action.send(
        comment.user,
        verb='delete',
        action_object=comment,
        target=comment.content_object,
        noclook={
            'action_type': 'comment',
            }
    )