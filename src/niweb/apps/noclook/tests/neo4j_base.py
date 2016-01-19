from django.test import TestCase, Client
from django.contrib.auth.models import User
import norduniclient as nc

# Use test instance of the neo4j db
nc.neo4jdb = nc.init_db('http://localhost:7475')

class NeoTestCase(TestCase):

    def setUp(self):
        # Create user
        user = User.objects.create_user(username='test user', email='test@localhost', password='test')
        user.is_staff = True
        user.save()
        self.user = user
        # Set up client
        self.client = Client()
        self.client.login(username='test user', password='test')

    def tearDown(self):
        with nc.neo4jdb.transaction as t:
            t.execute("MATCH (a:Node) OPTIONAL MATCH (a)-[r]-(b) DELETE a, b, r").fetchall()
        super(NeoTestCase, self).tearDown()

    def get_full_url(self, path):
        return 'http://testserver{}'.format(path)
