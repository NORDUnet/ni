# -*- coding: utf-8 -*-
from django.test import SimpleTestCase
from apps.noclook.forms import common as forms


class CsvFormTest(SimpleTestCase):

    @skip('Django 2.2 seems to have done away with utf8 decoding')
    def test_utf8_support(self):
        data = {
            u'csv_data': u'æg,høne\npølse,gris'.encode('utf-8')
        }
        form = forms.CsvForm(('product', 'animal'), data)

        self.assertTrue(form.is_valid(), 'The csv form should always be vaild. Errors: {}'.format(form.errors))
        rows = form.csv_parse_list(lambda x: x)
        self.assertEqual(u'æg', rows[0].get('product'))
        self.assertEqual(u'høne', rows[0].get('animal'))

    def test_unicode_support(self):
        data = {
            u'csv_data': u'æg,høne\npølse,gris',
        }

        form = forms.CsvForm((u'product', u'animal'), data)

        self.assertTrue(form.is_valid(), 'The csv form should always be vaild. Errors: {}'.format(form.errors))

        rows = form.csv_parse_list(lambda x: x)
        self.assertEqual(u'æg', rows[0].get('product'))
        self.assertEqual(u'høne', rows[0].get('animal'))
