from .neo4j_base import NeoTestCase
from apps.noclook.helpers import set_user, set_noclook_auto_manage
from apps.noclook import forms
from django.urls import reverse


class ViewTest(NeoTestCase):
    """
    Excercises the view fiels, by running at least one of the views in them.
    """

    def test_router_list_view(self):
        router1 = self.create_node('awesome-router.test.dev', 'router')
        router2 = self.create_node('fine.test.dev', 'router')
        router3 = self.create_node('different-router.test.dev', 'router')

        resp = self.client.get('/router/')
        self.assertContains(resp, router1.node_name)
        self.assertContains(resp, router2.node_name)
        self.assertContains(resp, router3.node_name)
        table_rows = resp.context['table'].rows
        self.assertEqual(table_rows[0].cols[0].get('handle_id'), router1.handle_id)
        self.assertEqual(table_rows[2].cols[0].get('handle_id'), router2.handle_id)
        self.assertEqual(table_rows[1].cols[0].get('handle_id'), router3.handle_id)

    def test_host_detail_view(self):
        host = self.create_node('sweet-host.nordu.net', 'host')

        resp = self.client.get(reverse('detail_host', args=[host.handle_id]))
        self.assertContains(resp, host.node_name)
        self.assertEqual(resp.context['node_handle'].handle_id, host.handle_id)

    def test_router_edit_view(self):
        router = self.create_node('awesome-router.test.dev', 'router')

        resp = self.client.get(reverse('generic_edit', args=['router', router.handle_id]))
        self.assertContains(resp, router.node_name)
        self.assertEqual(resp.context['node_handle'].handle_id, router.handle_id)
        self.assertIsInstance(resp.context['form'], forms.EditRouterForm)

    def test_debug_view(self):
        something = self.create_node('fancy.test.dev', 'magic-device')
        resp = self.client.get(reverse('debug', args=[something.handle_id]))
        self.assertContains(resp, something.node_name)
        self.assertEqual(resp.context['node_handle'].handle_id, something.handle_id)

    def test_create_view(self):
        resp = self.client.get(reverse('create_node', args=['host']))

        self.assertIsInstance(resp.context['form'], forms.NewHostForm)

    def test_other_view(self):
        router = self.create_node('nice.test.dev', 'router')
        resp = self.client.get(reverse('visualize', args=['router', router.handle_id]))

        self.assertEqual(resp.context['slug'], 'router')
        self.assertEqual(resp.context['node_handle'].handle_id, router.handle_id)

    def test_redirect_view(self):
        router = self.create_node('nice.test.dev', 'router')
        resp = self.client.get(reverse('node_redirect', args=[router.handle_id]))
        self.assertRedirects(resp, router.url())

    def test_report_view(self):
        host_user = self.create_node('AwesomeCo', 'host-user', 'Relation')
        host = self.create_node('sweet-host.nordu.net', 'host', 'Logical')
        host_node = host.get_node()
        set_noclook_auto_manage(host_node, True) 
        set_user(self.user, host.get_node(), host_user.handle_id)

        url = reverse('host_users_report')
        resp = self.client.get(url)

        self.assertContains(resp, host.node_name)

    # import nodes? it is tested seperatly

