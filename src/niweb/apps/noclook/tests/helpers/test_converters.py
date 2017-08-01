from django.test import TestCase
from apps.noclook import helpers


class FileExportHelperTest(TestCase):
    def setUp(self):
        self.dicts = [
            {u'Test': u'hest', u'Foo': u'bar'},
            {u'Test': u'best of all', u'Foo': u'baz'},
            {u'Test': u'fest', u'Foo': u'yay'},
        ]

    def test_dicts_to_xls_response(self):
        resp = helpers.dicts_to_xls_response(self.dicts)
        self.assertEqual(resp['content-type'], 'application/excel')
        self.assertEqual(resp['Content-Disposition'], 'attachment; filename=result.xls;')
        # to test the content we would need to read xls files :(

    def test_dicts_to_csv_response(self):
        resp = helpers.dicts_to_csv_response(self.dicts, [u'Test', u'Foo'])
        self.assertEqual(resp['content-type'], 'text/csv')
        self.assertEqual(resp['Content-Disposition'], 'attachment; filename=result.csv; charset=utf-8;')

        self.assertContains(resp, '"Test","Foo"')
        self.assertContains(resp, '"hest","bar"')
        self.assertContains(resp, '"best of all","baz"')
        self.assertContains(resp, '"fest","yay"')
