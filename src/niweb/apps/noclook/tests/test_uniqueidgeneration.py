# -*- coding: utf-8 -*-
"""
Created on 2014-06-26 1:40 PM

@author: lundberg
"""

from django.test import TestCase
from django.db import connection, transaction, IntegrityError
from django.contrib.auth.models import User
from apps.noclook.models import UniqueIdGenerator, NordunetUniqueId
from apps.noclook import unique_ids


class UniqueIdGeneration(TestCase):

    def setUp(self):
        # Set up a user
        self.username = 'TestUser'
        self.password = 'password'
        self.user, created = User.objects.get_or_create(username=self.username, password=self.password)
        # Set up an ID generator
        self.id_generator, created = UniqueIdGenerator.objects.get_or_create(
            name='Test ID Generator',
            base_id_length=6,
            zfill=True,
            prefix='TEST-',
            creator=self.user
        )
        self.id_collection = NordunetUniqueId

    def test_id_generation(self):
        new_id = self.id_generator.get_id()
        self.assertEqual(new_id, self.id_generator.last_id)
        unique_id = self.id_collection.objects.create(unique_id=new_id)
        self.assertEqual(unique_id.unique_id, new_id)

    def test_helper_functions_basics(self):
        new_id = self.id_generator.get_id()
        return_value = unique_ids.register_unique_id(self.id_collection, new_id)
        self.assertEqual(return_value, True)
        next_id = self.id_generator.next_id
        new_id = unique_ids.get_collection_unique_id(self.id_generator, self.id_collection)
        self.assertEqual(new_id, next_id)

    def test_reserve_range(self):
        unique_ids.bulk_reserve_id_range(1, 100, self.id_generator, self.id_collection, 'Reserve message', self.user)
        num_objects = self.id_collection.objects.count()
        self.assertEqual(num_objects, 100)
        new_id = unique_ids.get_collection_unique_id(self.id_generator, self.id_collection)
        self.assertEqual(new_id, 'TEST-000101')

    def test_reserve_sequence(self):
        unique_ids.reserve_id_sequence(100, self.id_generator, self.id_collection, 'Reserve message', self.user)
        num_objects = self.id_collection.objects.count()
        self.assertEqual(num_objects, 100)
        new_id = unique_ids.get_collection_unique_id(self.id_generator, self.id_collection)
        self.assertEqual(new_id, 'TEST-000101')

    def test_get_unique_id_jump(self):
        unique_ids.bulk_reserve_id_range(1, 99, self.id_generator, self.id_collection, 'Reserve message', self.user)
        self.assertEqual(self.id_generator.next_id, 'TEST-000001')
        new_id = unique_ids.get_collection_unique_id(self.id_generator, self.id_collection)
        self.assertEqual(new_id, 'TEST-000100')
        unique_ids.bulk_reserve_id_range(101, 150, self.id_generator, self.id_collection, 'Reserve message', self.user)
        seq = unique_ids.reserve_id_sequence(100, self.id_generator, self.id_collection, 'Reserve message', self.user)
        self.assertEqual(len(seq), 100)
        new_id = unique_ids.get_collection_unique_id(self.id_generator, self.id_collection)
        self.assertEqual(new_id, 'TEST-000201')

    def test_register_reserved_id(self):
        unique_ids.bulk_reserve_id_range(1, 99, self.id_generator, self.id_collection, 'Reserve message', self.user)
        result = unique_ids.register_unique_id(self.id_collection, 'TEST-000001')
        self.assertTrue(result)

    def test_register_unreserved_id(self):
        result = unique_ids.register_unique_id(self.id_collection, 'TEST-000001')
        self.assertTrue(result)

    def test_register_used_id(self):
        result = unique_ids.register_unique_id(self.id_collection, 'TEST-000001')
        self.assertTrue(result)
        try:
            sid = transaction.savepoint()
            unique_ids.register_unique_id(self.id_collection, 'TEST-000001')
            transaction.savepoint_commit(sid)
        except IntegrityError as e:
            transaction.savepoint_rollback(sid)
            self.assertIsInstance(e, IntegrityError)

    def test_is_free_unique_id(self):
        result = unique_ids.is_free_unique_id(self.id_collection, 'TEST-000001')
        self.assertTrue(result)
        unique_ids.register_unique_id(self.id_collection, 'TEST-000001')
        result = unique_ids.is_free_unique_id(self.id_collection, 'TEST-000001')
        self.assertFalse(result)

