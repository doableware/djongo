from django.db.models import QuerySet

from . import TestCase
from djongo import models


class Blog(models.Model):
    title = models.CharField(max_length=100)


class Author(models.Model):
    name = models.CharField(max_length=100)


class Entry(models.Model):
    blog = models.ForeignKey(Blog,
                             on_delete=models.CASCADE,
                             null=True)
    author = models.ForeignKey(Author,
                               on_delete=models.CASCADE,
                               null=True)
    content = models.CharField(max_length=100)


class TestCanvas(TestCase):

    def test_canvas(self):
        qs = Entry.objects.filter(author__name='hi')\
            .select_related('blog')
        print(qs.query)
        L = list(qs)
        l = [{
                '$match': {
                    'author_id': {
                        '$ne': None,
                        '$exists': True
                    }
                }
            },
            {
                '$lookup': {
                    'from': 'xtest_app_author',
                    'localField': 'author_id',
                    'foreignField': 'id',
                    'as': 'xtest_app_author'
                }
            },
            {
                '$unwind': '$xtest_app_author'
            },
            {
                '$lookup': {
                    'from': 'xtest_app_blog',
                    'localField': 'blog_id',
                    'foreignField': 'id',
                    'as': 'xtest_app_blog'
                }
            },
            {
                '$unwind': {
                    'path': '$xtest_app_blog',
                    'preserveNullAndEmptyArrays': True
                }
            },
            {
                '$addFields': {
                    'xtest_app_blog': {
                        '$ifNull': ['$xtest_app_blog', {
                            'id': None,
                            'title': None
                        }]
                    }
                }
            },
            {
                '$match': {
                    'xtest_app_author.name': {
                        '$eq': 'hi'
                    }
                }
            },
            {
                '$project': {
                    'id': True,
                    'blog_id': True,
                    'author_id': True,
                    'content': True,
                    'xtest_app_blog.id': True,
                    'xtest_app_blog.title': True
                }
            }]
