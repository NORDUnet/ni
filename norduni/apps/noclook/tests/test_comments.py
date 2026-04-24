from .neo4j_base import NeoTestCase
from django_comments.forms import CommentForm
from django_comments.models import Comment


class CommentsTest(NeoTestCase):

    def test_adding_a_comment(self):
        router = self.create_node('test.router.dev', 'router')

        f = CommentForm(router)
        data = f.initial

        data['comment'] = 'Neat comment yay'
        data['next'] = router.get_absolute_url()

        response = self.client.post('/comments/post/', data)
        self.assertRedirects(
            response,
            router.get_absolute_url() + '?c={}'.format(Comment.objects.latest('id').pk),
        )
        # check that the comment is shown on the details page
        resp2 = self.client.get(router.get_absolute_url())
        self.assertContains(resp2, 'Neat comment yay')
