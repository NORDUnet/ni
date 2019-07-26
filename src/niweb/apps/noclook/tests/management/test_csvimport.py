# -*- coding: utf-8 -*-

from django.core.management import call_command

import norduniclient as nc
from norduniclient.exceptions import UniqueNodeError, NodeNotFound
import norduniclient.models as ncmodels

from apps.noclook.models import NodeHandle, NodeType, User, Role, DEFAULT_ROLE_KEY

from ..neo4j_base import NeoTestCase

import tempfile

__author__ = 'ffuentes'

class CsvImportTest(NeoTestCase):
    cmd_name = 'csvimport'

    organizations_str = """"account_id";"account_name";"description";"phone";"website";"customer_id";"type";"parent_account"
1;"Tazz";;"453-896-3068";"https://studiopress.com";"DRIVE";"University, College";
2;"Wikizz";;"531-584-0224";"https://ihg.com";"DRIVE";"University, College";
3;"Browsecat";;"971-875-7084";"http://skyrock.com";"ROAD";"University, College";"Tazz"
4;"Dabfeed";;"855-843-6570";"http://merriam-webster.com";"LANE";"University, College";"Wikizz"
    """

    contacts_str = """"salutation";"first_name";"last_name";"title";"contact_role";"contact_type";"mailing_street";"mailing_city";"mailing_zip";"mailing_state";"mailing_country";"phone";"mobile";"fax";"email";"other_email";"PGP_fingerprint";"account_name"
"Honorable";"Caesar";"Newby";;"Computer Systems Analyst III";"Person";;;;;"China";"897-979-7799";"501-503-1550";;"cnewby0@joomla.org";;;"Gabtune"
"Mr";"Zilvia";"Linnard";;"Analog Circuit Design manager";"Person";;;;;"Indonesia";"205-934-3477";"473-256-5648";;"zlinnard1@wunderground.com";;;"Babblestorm"
"Honorable";"Reamonn";"Scriviner";;"Tax Accountant";"Person";;;;;"China";"200-111-4607";"419-639-2648";;"rscriviner2@moonfruit.com";;;"Babbleblab"
"Mrs";"Jessy";"Bainton";;"Software Consultant";"Person";;;;;"China";"877-832-9647";"138-608-6235";;"fbainton3@si.edu";;;"Mudo"
"Rev";"Theresa";"Janosevic";;"Physical Therapy Assistant";"Person";;;;;"China";"568-690-1854";"118-569-1303";;"tjanosevic4@umich.edu";;;"Youspan"
"Mrs";"David";"Janosevic";;;"Person";;;;;"United Kingdom";"568-690-1854";"118-569-1303";;"djanosevic4@afaa.co.uk";;;"AsFastAsAFAA"
    """

    secroles_str = """"Organisation";"Contact";"Role"
"Chalmers";"CTH Abuse";"Abuse"
"Chalmers";"CTH IRT";"IRT Gruppfunktion"
"Chalmers";"Hans Nilsson";"Övrig incidentkontakt"
"Chalmers";"Stefan Svensson";"Övrig incidentkontakt"
"Chalmers";"Karl Larsson";"Primär incidentkontakt"
    """

    def setUp(self):
        super(CsvImportTest, self).setUp()
        # write organizations csv file to disk
        self.organizations_file = self.write_string_to_disk(self.organizations_str)

        # write contacts csv file to disk
        self.contacts_file = self.write_string_to_disk(self.contacts_str)

        # write contacts csv file to disk
        self.secroles_file = self.write_string_to_disk(self.secroles_str)

        # create noclook user
        User.objects.get_or_create(username="noclook")[0]

    def tearDown(self):
        super(CsvImportTest, self).tearDown()
        # close organizations csv file
        self.organizations_file.close()

        # close contacts csv file
        self.contacts_file.close()

        # close contacts csv file
        self.secroles_file.close()

    def test_organizations_import(self):
        # call csvimport command (verbose 0)
        call_command(
            self.cmd_name,
            organizations=self.organizations_file,
            verbosity=0,
        )
        # check one of the organizations is present
        qs = NodeHandle.objects.filter(node_name='Browsecat')
        self.assertIsNotNone(qs)
        organization1 = qs.first()
        self.assertIsNotNone(organization1)
        self.assertIsInstance(organization1.get_node(), ncmodels.OrganizationModel)

        # check if one of them has a parent organization
        relations = organization1.get_node().get_relations()
        parent_relation = relations.get('Parent_of', None)
        self.assertIsNotNone(parent_relation)
        self.assertIsInstance(relations['Parent_of'][0]['node'], ncmodels.RelationModel)

    def test_contacts_import(self):
        # call csvimport command (verbose 0)
        call_command(
            self.cmd_name,
            contacts=self.contacts_file,
            verbosity=0,
        )
        # check one of the contacts is present
        full_name = '{} {}'.format('Caesar', 'Newby')
        qs = NodeHandle.objects.filter(node_name=full_name)
        self.assertIsNotNone(qs)
        contact1 = qs.first()
        self.assertIsNotNone(contact1)
        self.assertIsInstance(contact1.get_node(), ncmodels.ContactModel)

        # check if works for an organization
        qs = NodeHandle.objects.filter(node_name='Gabtune')
        self.assertIsNotNone(qs)
        organization1 = qs.first()
        self.assertIsNotNone(organization1)
        self.assertIsInstance(organization1.get_node(), ncmodels.OrganizationModel)

        # check if role is created
        role1 = ncmodels.RoleRelationship(nc.core.GraphDB.get_instance().manager)
        role1.load_from_nodes(contact1.handle_id, organization1.handle_id)
        self.assertIsNotNone(role1)
        self.assertEquals(role1.name, 'Computer Systems Analyst III')

        roleqs = Role.objects.filter(name=role1.name)
        self.assertIsNotNone(roleqs)
        self.assertIsNotNone(roleqs.first)

        # check for empty role and if it has the role employee
        qs = NodeHandle.objects.filter(node_name='David Janosevic')
        self.assertIsNotNone(qs)
        contact_employee = qs.first()
        self.assertIsNotNone(contact_employee)
        employee_role = Role.objects.get(slug=DEFAULT_ROLE_KEY)
        relations = contact_employee.get_node().get_outgoing_relations()
        self.assertEquals(employee_role.name, relations['Works_for'][0]['relationship']['name'])

    def test_secroles_import(self):
        # call csvimport command (verbose 0)
        call_command(
            self.cmd_name,
            secroles=self.secroles_file,
            verbosity=0,
        )

        # check if the organization is present
        qs = NodeHandle.objects.filter(node_name='Chalmers')
        self.assertIsNotNone(qs)
        organization1 = qs.first()
        self.assertIsNotNone(organization1)

        # check a contact is present
        qs = NodeHandle.objects.filter(node_name='Hans Nilsson')
        self.assertIsNotNone(qs)
        contact1 = qs.first()
        self.assertIsNotNone(contact1)

        # check if role is created
        role1 = ncmodels.RoleRelationship(nc.core.GraphDB.get_instance().manager)
        role1.load_from_nodes(contact1.handle_id, organization1.handle_id)
        self.assertIsNotNone(role1)
        self.assertEquals(role1.name, 'Övrig incidentkontakt')

    def write_string_to_disk(self, string):
        # get random file
        tf = tempfile.NamedTemporaryFile(mode='w+')

        # write text
        tf.write(string)
        tf.flush()
        # return file descriptor
        return tf
