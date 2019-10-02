# -*- coding: utf-8 -*-
from apps.noclook.tests.neo4j_base import NeoTestCase
from apps.noclook.models import Context, AuthzAction, GroupContextAuthzAction, NodeHandleContext
import apps.noclook.vakt.rules as srirules
from django.contrib.auth.models import User, Group


class SRIVaktRulesTest(NeoTestCase):
    def setUp(self):
        super(SRIVaktRulesTest, self).setUp()

        # create users
        self.user1 = User(
            first_name="Kate", last_name="Svensson", email="ksvensson@sunet.se",
            is_staff=False, is_active=True, username="ksvensson",
        )
        self.user1.save()

        self.user2 = User(
            first_name="Jane", last_name="Atkins", email="jatkins@sunet.se",
            is_staff=False, is_active=True, username="jatkins",
        )
        self.user2.save()

        self.user3 = User(
            first_name="Sven", last_name="Svensson", email="ssvensson@sunet.se",
            is_staff=False, is_active=True, username="ssvensson",
        )
        self.user3.save()

        # create authzactions
        self.authzaction1 = AuthzAction(name="Read action")
        self.authzaction2 = AuthzAction(name="Write action")
        self.authzaction3 = AuthzAction(name="Admin action")

        self.authzaction1.save()
        self.authzaction2.save()
        self.authzaction3.save()

        # create groups
        self.group1 = Group( name="Group with 2 contexts" )
        self.group2 = Group( name="Group with 1 context" )
        self.group3 = Group( name="Group without contexts" )

        self.group1.save()
        self.group2.save()
        self.group3.save()

        # add users to groups
        self.group1.user_set.add(self.user1)
        self.group2.user_set.add(self.user2)
        self.group3.user_set.add(self.user3)

        # create contexts
        self.context1 = Context( name="Context 1" )
        self.context2 = Context( name="Context 2" )

        self.context1.save()
        self.context2.save()

        # associate context and groups
        # first group can read/write/admin in the first context
        GroupContextAuthzAction(
            group = self.group1,
            authzprofile = self.authzaction1,
            context = self.context1
        ).save()

        GroupContextAuthzAction(
            group = self.group1,
            authzprofile = self.authzaction2,
            context = self.context1
        ).save()

        GroupContextAuthzAction(
            group = self.group1,
            authzprofile = self.authzaction3,
            context = self.context1
        ).save()

        # first group can read/write/admin in the second context
        GroupContextAuthzAction(
            group = self.group1,
            authzprofile = self.authzaction1,
            context = self.context2
        ).save()

        GroupContextAuthzAction(
            group = self.group1,
            authzprofile = self.authzaction2,
            context = self.context2
        ).save()

        GroupContextAuthzAction(
            group = self.group1,
            authzprofile = self.authzaction3,
            context = self.context2
        ).save()

        # second group read/write in the first context
        GroupContextAuthzAction(
            group = self.group2,
            authzprofile = self.authzaction1,
            context = self.context1
        ).save()

        GroupContextAuthzAction(
            group = self.group2,
            authzprofile = self.authzaction2,
            context = self.context1
        ).save()

        # second group reads in the second context
        GroupContextAuthzAction(
            group = self.group2,
            authzprofile = self.authzaction1,
            context = self.context2
        ).save()

        # the third group can only read in the first context
        GroupContextAuthzAction(
            group = self.group3,
            authzprofile = self.authzaction1,
            context = self.context1
        ).save()

        # create some nodes
        self.organization = self.create_node('organization1', 'organization', meta='Logical')
        self.contact1 = self.create_node('contact1', 'contact', meta='Relation')
        self.contact2 = self.create_node('contact2', 'contact', meta='Relation')

        # the organization belongs to both modules
        NodeHandleContext(
            nodehandle=self.organization,
            context = self.context1
        ).save()

        NodeHandleContext(
            nodehandle=self.organization,
            context = self.context2
        ).save()

        # the first contact belongs to the first module
        NodeHandleContext(
            nodehandle=self.contact1,
            context = self.context1
        ).save()

        # the second contact belongs to the first module
        NodeHandleContext(
            nodehandle=self.contact2,
            context = self.context2
        ).save()

    def test_has_auth_action(self):
        ### rule creation
        # rule: read in context1
        self.rule11 = srirules.HasAuthAction(
            self.authzaction1,
            self.context1
        )

        # rule: write in context1
        self.rule21 = srirules.HasAuthAction(
            self.authzaction2,
            self.context1
        )

        # rule: admin in context1
        self.rule31 = srirules.HasAuthAction(
            self.authzaction3,
            self.context1
        )

        # rule: read in context2
        self.rule12 = srirules.HasAuthAction(
            self.authzaction1,
            self.context2
        )

        # rule: write in context2
        self.rule22 = srirules.HasAuthAction(
            self.authzaction2,
            self.context2
        )

        # rule: admin in context2
        self.rule32 = srirules.HasAuthAction(
            self.authzaction3,
            self.context2
        )

        ### test: all users should read in context1
        user1_readsc1 = self.rule11.satisfied(self.user1)
        user2_readsc1 = self.rule11.satisfied(self.user2)
        user3_readsc1 = self.rule11.satisfied(self.user3)

        self.assertTrue(user1_readsc1)
        self.assertTrue(user2_readsc1)
        self.assertTrue(user3_readsc1)

        ### test: only users 1 and 2 should be able to write in context1
        user1_writec1 = self.rule21.satisfied(self.user1)
        user2_writec1 = self.rule21.satisfied(self.user2)
        user3_writec1 = self.rule21.satisfied(self.user3)

        self.assertTrue(user1_writec1)
        self.assertTrue(user2_writec1)
        self.assertFalse(user3_writec1)

        ### test: only user 1 should be able to admin in context1
        user1_adminc1 = self.rule31.satisfied(self.user1)
        user2_adminc1 = self.rule31.satisfied(self.user2)
        user3_adminc1 = self.rule31.satisfied(self.user3)

        self.assertTrue(user1_adminc1)
        self.assertFalse(user2_adminc1)
        self.assertFalse(user3_adminc1)

        ### test: only users 1 and 2 should read in context2
        user1_readsc2 = self.rule12.satisfied(self.user1)
        user2_readsc2 = self.rule12.satisfied(self.user2)
        user3_readsc2 = self.rule12.satisfied(self.user3)

        self.assertTrue(user1_readsc2)
        self.assertTrue(user2_readsc2)
        self.assertFalse(user3_readsc2)

        ### test: only user 1 should be able to write in context2
        user1_writec2 = self.rule22.satisfied(self.user1)
        user2_writec2 = self.rule22.satisfied(self.user2)
        user3_writec2 = self.rule22.satisfied(self.user3)

        self.assertTrue(user1_writec2)
        self.assertFalse(user2_writec2)
        self.assertFalse(user3_writec2)

        ### test: only user 1 should be able to admin in context2
        user1_adminc2 = self.rule32.satisfied(self.user1)
        user2_adminc2 = self.rule32.satisfied(self.user2)
        user3_adminc2 = self.rule32.satisfied(self.user3)

        self.assertTrue(user1_adminc2)
        self.assertFalse(user2_adminc2)
        self.assertFalse(user3_adminc2)

    def test_belongs_tocontext(self):
        ### rule creation
        self.resource_rule1 = srirules.BelongsContext(self.context1)
        self.resource_rule2 = srirules.BelongsContext(self.context2)

        # test: organization belongs to both contexts
        rule1_satisfied = self.resource_rule1.satisfied(self.organization)
        rule2_satisfied = self.resource_rule2.satisfied(self.organization)

        self.assertTrue(rule1_satisfied)
        self.assertTrue(rule2_satisfied)

        # test: contact1 belong only to the first context
        rule1_satisfied = self.resource_rule1.satisfied(self.contact1)
        rule2_satisfied = self.resource_rule2.satisfied(self.contact1)

        self.assertTrue(rule1_satisfied)
        self.assertFalse(rule2_satisfied)

        # test: contact2 belong only to the second context
        rule1_satisfied = self.resource_rule1.satisfied(self.contact2)
        rule2_satisfied = self.resource_rule2.satisfied(self.contact2)

        self.assertFalse(rule1_satisfied)
        self.assertTrue(rule2_satisfied)

    def test_contains_rule(self):
        contains_1 = srirules.ContainsElement('needle')

        haystack1 = ('hay', 'fork', 'needle', 'grass')
        haystack2 = ('sand', 'water', 'sun', 'sky')

        rule_satisfied1 = contains_1.satisfied(haystack1)
        rule_satisfied2 = contains_1.satisfied(haystack2)

        self.assertTrue(rule_satisfied1)
        self.assertFalse(rule_satisfied2)
