import collections.abc
from datetime import datetime
from math import ceil
from operator import attrgetter

from django.core.exceptions import FieldError
from django.db import connection, models
from django.db.models import Exists, Max, OuterRef
from django.db.models.functions import Substr
from django.test import TestCase, skipUnlessDBFeature
from django.test.utils import isolate_apps
from django.utils.deprecation import RemovedInDjango40Warning

from .models import (
    Article, Author, Freebie, Game, IsNullWithNoneAsRHS, Player, Season, Tag,
)


class LookupTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Create a few Authors.
        cls.au1 = Author.objects.create(name='Author 1', alias='a1')
        cls.au2 = Author.objects.create(name='Author 2', alias='a2')
        # Create a few Articles.
        cls.a1 = Article.objects.create(
            headline='Article 1',
            pub_date=datetime(2005, 7, 26),
            author=cls.au1,
            slug='a1',
        )
        cls.a2 = Article.objects.create(
            headline='Article 2',
            pub_date=datetime(2005, 7, 27),
            author=cls.au1,
            slug='a2',
        )
        cls.a3 = Article.objects.create(
            headline='Article 3',
            pub_date=datetime(2005, 7, 27),
            author=cls.au1,
            slug='a3',
        )
        cls.a4 = Article.objects.create(
            headline='Article 4',
            pub_date=datetime(2005, 7, 28),
            author=cls.au1,
            slug='a4',
        )
        cls.a5 = Article.objects.create(
            headline='Article 5',
            pub_date=datetime(2005, 8, 1, 9, 0),
            author=cls.au2,
            slug='a5',
        )
        cls.a6 = Article.objects.create(
            headline='Article 6',
            pub_date=datetime(2005, 8, 1, 8, 0),
            author=cls.au2,
            slug='a6',
        )
        cls.a7 = Article.objects.create(
            headline='Article 7',
            pub_date=datetime(2005, 7, 27),
            author=cls.au2,
            slug='a7',
        )
        # Create a few Tags.
        cls.t1 = Tag.objects.create(name='Tag 1')
        cls.t1.articles.add(cls.a1, cls.a2, cls.a3)
        cls.t2 = Tag.objects.create(name='Tag 2')
        cls.t2.articles.add(cls.a3, cls.a4, cls.a5)
        cls.t3 = Tag.objects.create(name='Tag 3')
        cls.t3.articles.add(cls.a5, cls.a6, cls.a7)

    def test_exists(self):
        # We can use .exists() to check that there are some
        self.assertTrue(Article.objects.exists())
        for a in Article.objects.all():
            a.delete()
        # There should be none now!
        self.assertFalse(Article.objects.exists())

    def test_lookup_int_as_str(self):
        # Integer value can be queried using string
        self.assertSequenceEqual(
            Article.objects.filter(id__iexact=str(self.a1.id)),
            [self.a1],
        )

    @skipUnlessDBFeature('supports_date_lookup_using_string')
    def test_lookup_date_as_str(self):
        # A date lookup can be performed using a string search
        self.assertSequenceEqual(
            Article.objects.filter(pub_date__startswith='2005'),
            [self.a5, self.a6, self.a4, self.a2, self.a3, self.a7, self.a1],
        )

    def test_iterator(self):
        # Each QuerySet gets iterator(), which is a generator that "lazily"
        # returns results using database-level iteration.
        self.assertIsInstance(Article.objects.iterator(), collections.abc.Iterator)

        self.assertQuerysetEqual(
            Article.objects.iterator(),
            [
                'Article 5',
                'Article 6',
                'Article 4',
                'Article 2',
                'Article 3',
                'Article 7',
                'Article 1',
            ],
            transform=attrgetter('headline')
        )
        # iterator() can be used on any QuerySet.
        self.assertQuerysetEqual(
            Article.objects.filter(headline__endswith='4').iterator(),
            ['Article 4'],
            transform=attrgetter('headline'))

    def test_count(self):
        # count() returns the number of objects matching search criteria.
        self.assertEqual(Article.objects.count(), 7)
        self.assertEqual(Article.objects.filter(pub_date__exact=datetime(2005, 7, 27)).count(), 3)
        self.assertEqual(Article.objects.filter(headline__startswith='Blah blah').count(), 0)

        # count() should respect sliced query sets.
        articles = Article.objects.all()
        self.assertEqual(articles.count(), 7)
        self.assertEqual(articles[:4].count(), 4)
        self.assertEqual(articles[1:100].count(), 6)
        self.assertEqual(articles[10:100].count(), 0)

        # Date and date/time lookups can also be done with strings.
        self.assertEqual(Article.objects.filter(pub_date__exact='2005-07-27 00:00:00').count(), 3)

    def test_in_bulk(self):
        # in_bulk() takes a list of IDs and returns a dictionary mapping IDs to objects.
        arts = Article.objects.in_bulk([self.a1.id, self.a2.id])
        self.assertEqual(arts[self.a1.id], self.a1)
        self.assertEqual(arts[self.a2.id], self.a2)
        self.assertEqual(
            Article.objects.in_bulk(),
            {
                self.a1.id: self.a1,
                self.a2.id: self.a2,
                self.a3.id: self.a3,
                self.a4.id: self.a4,
                self.a5.id: self.a5,
                self.a6.id: self.a6,
                self.a7.id: self.a7,
            }
        )
        self.assertEqual(Article.objects.in_bulk([self.a3.id]), {self.a3.id: self.a3})
        self.assertEqual(Article.objects.in_bulk({self.a3.id}), {self.a3.id: self.a3})
        self.assertEqual(Article.objects.in_bulk(frozenset([self.a3.id])), {self.a3.id: self.a3})
        self.assertEqual(Article.objects.in_bulk((self.a3.id,)), {self.a3.id: self.a3})
        self.assertEqual(Article.objects.in_bulk([1000]), {})
        self.assertEqual(Article.objects.in_bulk([]), {})
        self.assertEqual(Article.objects.in_bulk(iter([self.a1.id])), {self.a1.id: self.a1})
        self.assertEqual(Article.objects.in_bulk(iter([])), {})
        with self.assertRaises(TypeError):
            Article.objects.in_bulk(headline__startswith='Blah')

    def test_in_bulk_lots_of_ids(self):
        test_range = 2000
        max_query_params = connection.features.max_query_params
        expected_num_queries = ceil(test_range / max_query_params) if max_query_params else 1
        Author.objects.bulk_create([Author() for i in range(test_range - Author.objects.count())])
        authors = {author.pk: author for author in Author.objects.all()}
        with self.assertNumQueries(expected_num_queries):
            self.assertEqual(Author.objects.in_bulk(authors), authors)

    def test_in_bulk_with_field(self):
        self.assertEqual(
            Article.objects.in_bulk([self.a1.slug, self.a2.slug, self.a3.slug], field_name='slug'),
            {
                self.a1.slug: self.a1,
                self.a2.slug: self.a2,
                self.a3.slug: self.a3,
            }
        )

    def test_in_bulk_meta_constraint(self):
        season_2011 = Season.objects.create(year=2011)
        season_2012 = Season.objects.create(year=2012)
        Season.objects.create(year=2013)
        self.assertEqual(
            Season.objects.in_bulk(
                [season_2011.year, season_2012.year],
                field_name='year',
            ),
            {season_2011.year: season_2011, season_2012.year: season_2012},
        )

    def test_in_bulk_non_unique_field(self):
        msg = "in_bulk()'s field_name must be a unique field but 'author' isn't."
        with self.assertRaisesMessage(ValueError, msg):
            Article.objects.in_bulk([self.au1], field_name='author')

    @skipUnlessDBFeature('can_distinct_on_fields')
    def test_in_bulk_distinct_field(self):
        self.assertEqual(
            Article.objects.order_by('headline').distinct('headline').in_bulk(
                [self.a1.headline, self.a5.headline],
                field_name='headline',
            ),
            {self.a1.headline: self.a1, self.a5.headline: self.a5},
        )

    @skipUnlessDBFeature('can_distinct_on_fields')
    def test_in_bulk_multiple_distinct_field(self):
        msg = "in_bulk()'s field_name must be a unique field but 'pub_date' isn't."
        with self.assertRaisesMessage(ValueError, msg):
            Article.objects.order_by('headline', 'pub_date').distinct(
                'headline', 'pub_date',
            ).in_bulk(field_name='pub_date')

    @isolate_apps('lookup')
    def test_in_bulk_non_unique_meta_constaint(self):
        class Model(models.Model):
            ean = models.CharField(max_length=100)
            brand = models.CharField(max_length=100)
            name = models.CharField(max_length=80)

            class Meta:
                constraints = [
                    models.UniqueConstraint(
                        fields=['ean'],
                        name='partial_ean_unique',
                        condition=models.Q(is_active=True)
                    ),
                    models.UniqueConstraint(
                        fields=['brand', 'name'],
                        name='together_brand_name_unique',
                    ),
                ]

        msg = "in_bulk()'s field_name must be a unique field but '%s' isn't."
        for field_name in ['brand', 'ean']:
            with self.subTest(field_name=field_name):
                with self.assertRaisesMessage(ValueError, msg % field_name):
                    Model.objects.in_bulk(field_name=field_name)

    def test_values(self):
        # values() returns a list of dictionaries instead of object instances --
        # and you can specify which fields you want to retrieve.
        self.assertSequenceEqual(
            Article.objects.values('headline'),
            [
                {'headline': 'Article 5'},
                {'headline': 'Article 6'},
                {'headline': 'Article 4'},
                {'headline': 'Article 2'},
                {'headline': 'Article 3'},
                {'headline': 'Article 7'},
                {'headline': 'Article 1'},
            ],
        )
        self.assertSequenceEqual(
            Article.objects.filter(pub_date__exact=datetime(2005, 7, 27)).values('id'),
            [{'id': self.a2.id}, {'id': self.a3.id}, {'id': self.a7.id}],
        )
        self.assertSequenceEqual(
            Article.objects.values('id', 'headline'),
            [
                {'id': self.a5.id, 'headline': 'Article 5'},
                {'id': self.a6.id, 'headline': 'Article 6'},
                {'id': self.a4.id, 'headline': 'Article 4'},
                {'id': self.a2.id, 'headline': 'Article 2'},
                {'id': self.a3.id, 'headline': 'Article 3'},
                {'id': self.a7.id, 'headline': 'Article 7'},
                {'id': self.a1.id, 'headline': 'Article 1'},
            ],
        )
        # You can use values() with iterator() for memory savings,
        # because iterator() uses database-level iteration.
        self.assertSequenceEqual(
            list(Article.objects.values('id', 'headline').iterator()),
            [
                {'headline': 'Article 5', 'id': self.a5.id},
                {'headline': 'Article 6', 'id': self.a6.id},
                {'headline': 'Article 4', 'id': self.a4.id},
                {'headline': 'Article 2', 'id': self.a2.id},
                {'headline': 'Article 3', 'id': self.a3.id},
                {'headline': 'Article 7', 'id': self.a7.id},
                {'headline': 'Article 1', 'id': self.a1.id},
            ],
        )
        # The values() method works with "extra" fields specified in extra(select).
        self.assertSequenceEqual(
            Article.objects.extra(select={'id_plus_one': 'id + 1'}).values('id', 'id_plus_one'),
            [
                {'id': self.a5.id, 'id_plus_one': self.a5.id + 1},
                {'id': self.a6.id, 'id_plus_one': self.a6.id + 1},
                {'id': self.a4.id, 'id_plus_one': self.a4.id + 1},
                {'id': self.a2.id, 'id_plus_one': self.a2.id + 1},
                {'id': self.a3.id, 'id_plus_one': self.a3.id + 1},
                {'id': self.a7.id, 'id_plus_one': self.a7.id + 1},
                {'id': self.a1.id, 'id_plus_one': self.a1.id + 1},
            ],
        )
        data = {
            'id_plus_one': 'id+1',
            'id_plus_two': 'id+2',
            'id_plus_three': 'id+3',
            'id_plus_four': 'id+4',
            'id_plus_five': 'id+5',
            'id_plus_six': 'id+6',
            'id_plus_seven': 'id+7',
            'id_plus_eight': 'id+8',
        }
        self.assertSequenceEqual(
            Article.objects.filter(id=self.a1.id).extra(select=data).values(*data),
            [{
                'id_plus_one': self.a1.id + 1,
                'id_plus_two': self.a1.id + 2,
                'id_plus_three': self.a1.id + 3,
                'id_plus_four': self.a1.id + 4,
                'id_plus_five': self.a1.id + 5,
                'id_plus_six': self.a1.id + 6,
                'id_plus_seven': self.a1.id + 7,
                'id_plus_eight': self.a1.id + 8,
            }],
        )
        # You can specify fields from forward and reverse relations, just like filter().
        self.assertSequenceEqual(
            Article.objects.values('headline', 'author__name'),
            [
                {'headline': self.a5.headline, 'author__name': self.au2.name},
                {'headline': self.a6.headline, 'author__name': self.au2.name},
                {'headline': self.a4.headline, 'author__name': self.au1.name},
                {'headline': self.a2.headline, 'author__name': self.au1.name},
                {'headline': self.a3.headline, 'author__name': self.au1.name},
                {'headline': self.a7.headline, 'author__name': self.au2.name},
                {'headline': self.a1.headline, 'author__name': self.au1.name},
            ],
        )
        self.assertSequenceEqual(
            Author.objects.values('name', 'article__headline').order_by('name', 'article__headline'),
            [
                {'name': self.au1.name, 'article__headline': self.a1.headline},
                {'name': self.au1.name, 'article__headline': self.a2.headline},
                {'name': self.au1.name, 'article__headline': self.a3.headline},
                {'name': self.au1.name, 'article__headline': self.a4.headline},
                {'name': self.au2.name, 'article__headline': self.a5.headline},
                {'name': self.au2.name, 'article__headline': self.a6.headline},
                {'name': self.au2.name, 'article__headline': self.a7.headline},
            ],
        )
        self.assertSequenceEqual(
            (
                Author.objects
                .values('name', 'article__headline', 'article__tag__name')
                .order_by('name', 'article__headline', 'article__tag__name')
            ),
            [
                {'name': self.au1.name, 'article__headline': self.a1.headline, 'article__tag__name': self.t1.name},
                {'name': self.au1.name, 'article__headline': self.a2.headline, 'article__tag__name': self.t1.name},
                {'name': self.au1.name, 'article__headline': self.a3.headline, 'article__tag__name': self.t1.name},
                {'name': self.au1.name, 'article__headline': self.a3.headline, 'article__tag__name': self.t2.name},
                {'name': self.au1.name, 'article__headline': self.a4.headline, 'article__tag__name': self.t2.name},
                {'name': self.au2.name, 'article__headline': self.a5.headline, 'article__tag__name': self.t2.name},
                {'name': self.au2.name, 'article__headline': self.a5.headline, 'article__tag__name': self.t3.name},
                {'name': self.au2.name, 'article__headline': self.a6.headline, 'article__tag__name': self.t3.name},
                {'name': self.au2.name, 'article__headline': self.a7.headline, 'article__tag__name': self.t3.name},
            ],
        )
        # However, an exception FieldDoesNotExist will be thrown if you specify
        # a nonexistent field name in values() (a field that is neither in the
        # model nor in extra(select)).
        msg = (
            "Cannot resolve keyword 'id_plus_two' into field. Choices are: "
            "author, author_id, headline, id, id_plus_one, pub_date, slug, tag"
        )
        with self.assertRaisesMessage(FieldError, msg):
            Article.objects.extra(select={'id_plus_one': 'id + 1'}).values('id', 'id_plus_two')
        # If you don't specify field names to values(), all are returned.
        self.assertSequenceEqual(
            Article.objects.filter(id=self.a5.id).values(),
            [{
                'id': self.a5.id,
                'author_id': self.au2.id,
                'headline': 'Article 5',
                'pub_date': datetime(2005, 8, 1, 9, 0),
                'slug': 'a5',
            }],
        )

    def test_values_list(self):
        # values_list() is similar to values(), except that the results are
        # returned as a list of tuples, rather than a list of dictionaries.
        # Within each tuple, the order of the elements is the same as the order
        # of fields in the values_list() call.
        self.assertSequenceEqual(
            Article.objects.values_list('headline'),
            [
                ('Article 5',),
                ('Article 6',),
                ('Article 4',),
                ('Article 2',),
                ('Article 3',),
                ('Article 7',),
                ('Article 1',),
            ],
        )
        self.assertSequenceEqual(
            Article.objects.values_list('id').order_by('id'),
            [(self.a1.id,), (self.a2.id,), (self.a3.id,), (self.a4.id,), (self.a5.id,), (self.a6.id,), (self.a7.id,)],
        )
        self.assertSequenceEqual(
            Article.objects.values_list('id', flat=True).order_by('id'),
            [self.a1.id, self.a2.id, self.a3.id, self.a4.id, self.a5.id, self.a6.id, self.a7.id],
        )
        self.assertSequenceEqual(
            Article.objects.extra(select={'id_plus_one': 'id+1'}).order_by('id').values_list('id'),
            [(self.a1.id,), (self.a2.id,), (self.a3.id,), (self.a4.id,), (self.a5.id,), (self.a6.id,), (self.a7.id,)],
        )
        self.assertSequenceEqual(
            Article.objects.extra(select={'id_plus_one': 'id+1'}).order_by('id').values_list('id_plus_one', 'id'),
            [
                (self.a1.id + 1, self.a1.id),
                (self.a2.id + 1, self.a2.id),
                (self.a3.id + 1, self.a3.id),
                (self.a4.id + 1, self.a4.id),
                (self.a5.id + 1, self.a5.id),
                (self.a6.id + 1, self.a6.id),
                (self.a7.id + 1, self.a7.id)
            ],
        )
        self.assertSequenceEqual(
            Article.objects.extra(select={'id_plus_one': 'id+1'}).order_by('id').values_list('id', 'id_plus_one'),
            [
                (self.a1.id, self.a1.id + 1),
                (self.a2.id, self.a2.id + 1),
                (self.a3.id, self.a3.id + 1),
                (self.a4.id, self.a4.id + 1),
                (self.a5.id, self.a5.id + 1),
                (self.a6.id, self.a6.id + 1),
                (self.a7.id, self.a7.id + 1)
            ],
        )
        args = ('name', 'article__headline', 'article__tag__name')
        self.assertSequenceEqual(
            Author.objects.values_list(*args).order_by(*args),
            [
                (self.au1.name, self.a1.headline, self.t1.name),
                (self.au1.name, self.a2.headline, self.t1.name),
                (self.au1.name, self.a3.headline, self.t1.name),
                (self.au1.name, self.a3.headline, self.t2.name),
                (self.au1.name, self.a4.headline, self.t2.name),
                (self.au2.name, self.a5.headline, self.t2.name),
                (self.au2.name, self.a5.headline, self.t3.name),
                (self.au2.name, self.a6.headline, self.t3.name),
                (self.au2.name, self.a7.headline, self.t3.name),
            ],
        )
        with self.assertRaises(TypeError):
            Article.objects.values_list('id', 'headline', flat=True)

    def test_get_next_previous_by(self):
        # Every DateField and DateTimeField creates get_next_by_FOO() and
        # get_previous_by_FOO() methods. In the case of identical date values,
        # these methods will use the ID as a fallback check. This guarantees
        # that no records are skipped or duplicated.
        self.assertEqual(repr(self.a1.get_next_by_pub_date()), '<Article: Article 2>')
        self.assertEqual(repr(self.a2.get_next_by_pub_date()), '<Article: Article 3>')
        self.assertEqual(repr(self.a2.get_next_by_pub_date(headline__endswith='6')), '<Article: Article 6>')
        self.assertEqual(repr(self.a3.get_next_by_pub_date()), '<Article: Article 7>')
        self.assertEqual(repr(self.a4.get_next_by_pub_date()), '<Article: Article 6>')
        with self.assertRaises(Article.DoesNotExist):
            self.a5.get_next_by_pub_date()
        self.assertEqual(repr(self.a6.get_next_by_pub_date()), '<Article: Article 5>')
        self.assertEqual(repr(self.a7.get_next_by_pub_date()), '<Article: Article 4>')

        self.assertEqual(repr(self.a7.get_previous_by_pub_date()), '<Article: Article 3>')
        self.assertEqual(repr(self.a6.get_previous_by_pub_date()), '<Article: Article 4>')
        self.assertEqual(repr(self.a5.get_previous_by_pub_date()), '<Article: Article 6>')
        self.assertEqual(repr(self.a4.get_previous_by_pub_date()), '<Article: Article 7>')
        self.assertEqual(repr(self.a3.get_previous_by_pub_date()), '<Article: Article 2>')
        self.assertEqual(repr(self.a2.get_previous_by_pub_date()), '<Article: Article 1>')

    def test_escaping(self):
        # Underscores, percent signs and backslashes have special meaning in the
        # underlying SQL code, but Django handles the quoting of them automatically.
        a8 = Article.objects.create(headline='Article_ with underscore', pub_date=datetime(2005, 11, 20))

        self.assertSequenceEqual(
            Article.objects.filter(headline__startswith='Article'),
            [a8, self.a5, self.a6, self.a4, self.a2, self.a3, self.a7, self.a1],
        )
        self.assertSequenceEqual(
            Article.objects.filter(headline__startswith='Article_'),
            [a8],
        )
        a9 = Article.objects.create(headline='Article% with percent sign', pub_date=datetime(2005, 11, 21))
        self.assertSequenceEqual(
            Article.objects.filter(headline__startswith='Article'),
            [a9, a8, self.a5, self.a6, self.a4, self.a2, self.a3, self.a7, self.a1],
        )
        self.assertSequenceEqual(
            Article.objects.filter(headline__startswith='Article%'),
            [a9],
        )
        a10 = Article.objects.create(headline='Article with \\ backslash', pub_date=datetime(2005, 11, 22))
        self.assertSequenceEqual(
            Article.objects.filter(headline__contains='\\'),
            [a10],
        )

    def test_exclude(self):
        pub_date = datetime(2005, 11, 20)
        a8 = Article.objects.create(headline='Article_ with underscore', pub_date=pub_date)
        a9 = Article.objects.create(headline='Article% with percent sign', pub_date=pub_date)
        a10 = Article.objects.create(headline='Article with \\ backslash', pub_date=pub_date)
        # exclude() is the opposite of filter() when doing lookups:
        self.assertSequenceEqual(
            Article.objects.filter(headline__contains='Article').exclude(headline__contains='with'),
            [self.a5, self.a6, self.a4, self.a2, self.a3, self.a7, self.a1],
        )
        self.assertSequenceEqual(
            Article.objects.exclude(headline__startswith="Article_"),
            [a10, a9, self.a5, self.a6, self.a4, self.a2, self.a3, self.a7, self.a1],
        )
        self.assertSequenceEqual(
            Article.objects.exclude(headline="Article 7"),
            [a10, a9, a8, self.a5, self.a6, self.a4, self.a2, self.a3, self.a1],
        )

    def test_none(self):
        # none() returns a QuerySet that behaves like any other QuerySet object
        self.assertQuerysetEqual(Article.objects.none(), [])
        self.assertQuerysetEqual(Article.objects.none().filter(headline__startswith='Article'), [])
        self.assertQuerysetEqual(Article.objects.filter(headline__startswith='Article').none(), [])
        self.assertEqual(Article.objects.none().count(), 0)
        self.assertEqual(Article.objects.none().update(headline="This should not take effect"), 0)
        self.assertQuerysetEqual(Article.objects.none().iterator(), [])

    def test_in(self):
        self.assertSequenceEqual(
            Article.objects.exclude(id__in=[]),
            [self.a5, self.a6, self.a4, self.a2, self.a3, self.a7, self.a1],
        )

    def test_in_empty_list(self):
        self.assertSequenceEqual(Article.objects.filter(id__in=[]), [])

    def test_in_different_database(self):
        with self.assertRaisesMessage(
            ValueError,
            "Subqueries aren't allowed across different databases. Force the "
            "inner query to be evaluated using `list(inner_query)`."
        ):
            list(Article.objects.filter(id__in=Article.objects.using('other').all()))

    def test_in_keeps_value_ordering(self):
        query = Article.objects.filter(slug__in=['a%d' % i for i in range(1, 8)]).values('pk').query
        self.assertIn(' IN (a1, a2, a3, a4, a5, a6, a7) ', str(query))

    def test_in_ignore_none(self):
        with self.assertNumQueries(1) as ctx:
            self.assertSequenceEqual(
                Article.objects.filter(id__in=[None, self.a1.id]),
                [self.a1],
            )
        sql = ctx.captured_queries[0]['sql']
        self.assertIn('IN (%s)' % self.a1.pk, sql)

    def test_in_ignore_solo_none(self):
        with self.assertNumQueries(0):
            self.assertSequenceEqual(Article.objects.filter(id__in=[None]), [])

    def test_in_ignore_none_with_unhashable_items(self):
        class UnhashableInt(int):
            __hash__ = None

        with self.assertNumQueries(1) as ctx:
            self.assertSequenceEqual(
                Article.objects.filter(id__in=[None, UnhashableInt(self.a1.id)]),
                [self.a1],
            )
        sql = ctx.captured_queries[0]['sql']
        self.assertIn('IN (%s)' % self.a1.pk, sql)

    def test_error_messages(self):
        # Programming errors are pointed out with nice error messages
        with self.assertRaisesMessage(
            FieldError,
            "Cannot resolve keyword 'pub_date_year' into field. Choices are: "
            "author, author_id, headline, id, pub_date, slug, tag"
        ):
            Article.objects.filter(pub_date_year='2005').count()

    def test_unsupported_lookups(self):
        with self.assertRaisesMessage(
            FieldError,
            "Unsupported lookup 'starts' for CharField or join on the field "
            "not permitted, perhaps you meant startswith or istartswith?"
        ):
            Article.objects.filter(headline__starts='Article')

        with self.assertRaisesMessage(
            FieldError,
            "Unsupported lookup 'is_null' for DateTimeField or join on the field "
            "not permitted, perhaps you meant isnull?"
        ):
            Article.objects.filter(pub_date__is_null=True)

        with self.assertRaisesMessage(
            FieldError,
            "Unsupported lookup 'gobbledygook' for DateTimeField or join on the field "
            "not permitted."
        ):
            Article.objects.filter(pub_date__gobbledygook='blahblah')

    def test_relation_nested_lookup_error(self):
        # An invalid nested lookup on a related field raises a useful error.
        msg = 'Related Field got invalid lookup: editor'
        with self.assertRaisesMessage(FieldError, msg):
            Article.objects.filter(author__editor__name='James')
        msg = 'Related Field got invalid lookup: foo'
        with self.assertRaisesMessage(FieldError, msg):
            Tag.objects.filter(articles__foo='bar')

    def test_regex(self):
        # Create some articles with a bit more interesting headlines for testing field lookups:
        for a in Article.objects.all():
            a.delete()
        now = datetime.now()
        Article.objects.bulk_create([
            Article(pub_date=now, headline='f'),
            Article(pub_date=now, headline='fo'),
            Article(pub_date=now, headline='foo'),
            Article(pub_date=now, headline='fooo'),
            Article(pub_date=now, headline='hey-Foo'),
            Article(pub_date=now, headline='bar'),
            Article(pub_date=now, headline='AbBa'),
            Article(pub_date=now, headline='baz'),
            Article(pub_date=now, headline='baxZ'),
        ])
        # zero-or-more
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'fo*'),
            Article.objects.filter(headline__in=['f', 'fo', 'foo', 'fooo']),
        )
        self.assertQuerysetEqual(
            Article.objects.filter(headline__iregex=r'fo*'),
            Article.objects.filter(headline__in=['f', 'fo', 'foo', 'fooo', 'hey-Foo']),
        )
        # one-or-more
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'fo+'),
            Article.objects.filter(headline__in=['fo', 'foo', 'fooo']),
        )
        # wildcard
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'fooo?'),
            Article.objects.filter(headline__in=['foo', 'fooo']),
        )
        # leading anchor
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'^b'),
            Article.objects.filter(headline__in=['bar', 'baxZ', 'baz']),
        )
        self.assertQuerysetEqual(
            Article.objects.filter(headline__iregex=r'^a'),
            Article.objects.filter(headline='AbBa'),
        )
        # trailing anchor
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'z$'),
            Article.objects.filter(headline='baz'),
        )
        self.assertQuerysetEqual(
            Article.objects.filter(headline__iregex=r'z$'),
            Article.objects.filter(headline__in=['baxZ', 'baz']),
        )
        # character sets
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'ba[rz]'),
            Article.objects.filter(headline__in=['bar', 'baz']),
        )
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'ba.[RxZ]'),
            Article.objects.filter(headline='baxZ'),
        )
        self.assertQuerysetEqual(
            Article.objects.filter(headline__iregex=r'ba[RxZ]'),
            Article.objects.filter(headline__in=['bar', 'baxZ', 'baz']),
        )

        # and more articles:
        Article.objects.bulk_create([
            Article(pub_date=now, headline='foobar'),
            Article(pub_date=now, headline='foobaz'),
            Article(pub_date=now, headline='ooF'),
            Article(pub_date=now, headline='foobarbaz'),
            Article(pub_date=now, headline='zoocarfaz'),
            Article(pub_date=now, headline='barfoobaz'),
            Article(pub_date=now, headline='bazbaRFOO'),
        ])

        # alternation
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'oo(f|b)'),
            Article.objects.filter(headline__in=[
                'barfoobaz',
                'foobar',
                'foobarbaz',
                'foobaz',
            ]),
        )
        self.assertQuerysetEqual(
            Article.objects.filter(headline__iregex=r'oo(f|b)'),
            Article.objects.filter(headline__in=[
                'barfoobaz',
                'foobar',
                'foobarbaz',
                'foobaz',
                'ooF',
            ]),
        )
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'^foo(f|b)'),
            Article.objects.filter(headline__in=['foobar', 'foobarbaz', 'foobaz']),
        )

        # greedy matching
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'b.*az'),
            Article.objects.filter(headline__in=[
                'barfoobaz',
                'baz',
                'bazbaRFOO',
                'foobarbaz',
                'foobaz',
            ]),
        )
        self.assertQuerysetEqual(
            Article.objects.filter(headline__iregex=r'b.*ar'),
            Article.objects.filter(headline__in=[
                'bar',
                'barfoobaz',
                'bazbaRFOO',
                'foobar',
                'foobarbaz',
            ]),
        )

    @skipUnlessDBFeature('supports_regex_backreferencing')
    def test_regex_backreferencing(self):
        # grouping and backreferences
        now = datetime.now()
        Article.objects.bulk_create([
            Article(pub_date=now, headline='foobar'),
            Article(pub_date=now, headline='foobaz'),
            Article(pub_date=now, headline='ooF'),
            Article(pub_date=now, headline='foobarbaz'),
            Article(pub_date=now, headline='zoocarfaz'),
            Article(pub_date=now, headline='barfoobaz'),
            Article(pub_date=now, headline='bazbaRFOO'),
        ])
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'b(.).*b\1').values_list('headline', flat=True),
            ['barfoobaz', 'bazbaRFOO', 'foobarbaz'],
        )

    def test_regex_null(self):
        """
        A regex lookup does not fail on null/None values
        """
        Season.objects.create(year=2012, gt=None)
        self.assertQuerysetEqual(Season.objects.filter(gt__regex=r'^$'), [])

    def test_regex_non_string(self):
        """
        A regex lookup does not fail on non-string fields
        """
        s = Season.objects.create(year=2013, gt=444)
        self.assertQuerysetEqual(Season.objects.filter(gt__regex=r'^444$'), [s])

    def test_regex_non_ascii(self):
        """
        A regex lookup does not trip on non-ASCII characters.
        """
        Player.objects.create(name='\u2660')
        Player.objects.get(name__regex='\u2660')

    def test_nonfield_lookups(self):
        """
        A lookup query containing non-fields raises the proper exception.
        """
        msg = "Unsupported lookup 'blahblah' for CharField or join on the field not permitted."
        with self.assertRaisesMessage(FieldError, msg):
            Article.objects.filter(headline__blahblah=99)
        with self.assertRaisesMessage(FieldError, msg):
            Article.objects.filter(headline__blahblah__exact=99)
        msg = (
            "Cannot resolve keyword 'blahblah' into field. Choices are: "
            "author, author_id, headline, id, pub_date, slug, tag"
        )
        with self.assertRaisesMessage(FieldError, msg):
            Article.objects.filter(blahblah=99)

    def test_lookup_collision(self):
        """
        Genuine field names don't collide with built-in lookup types
        ('year', 'gt', 'range', 'in' etc.) (#11670).
        """
        # 'gt' is used as a code number for the year, e.g. 111=>2009.
        season_2009 = Season.objects.create(year=2009, gt=111)
        season_2009.games.create(home="Houston Astros", away="St. Louis Cardinals")
        season_2010 = Season.objects.create(year=2010, gt=222)
        season_2010.games.create(home="Houston Astros", away="Chicago Cubs")
        season_2010.games.create(home="Houston Astros", away="Milwaukee Brewers")
        season_2010.games.create(home="Houston Astros", away="St. Louis Cardinals")
        season_2011 = Season.objects.create(year=2011, gt=333)
        season_2011.games.create(home="Houston Astros", away="St. Louis Cardinals")
        season_2011.games.create(home="Houston Astros", away="Milwaukee Brewers")
        hunter_pence = Player.objects.create(name="Hunter Pence")
        hunter_pence.games.set(Game.objects.filter(season__year__in=[2009, 2010]))
        pudge = Player.objects.create(name="Ivan Rodriquez")
        pudge.games.set(Game.objects.filter(season__year=2009))
        pedro_feliz = Player.objects.create(name="Pedro Feliz")
        pedro_feliz.games.set(Game.objects.filter(season__year__in=[2011]))
        johnson = Player.objects.create(name="Johnson")
        johnson.games.set(Game.objects.filter(season__year__in=[2011]))

        # Games in 2010
        self.assertEqual(Game.objects.filter(season__year=2010).count(), 3)
        self.assertEqual(Game.objects.filter(season__year__exact=2010).count(), 3)
        self.assertEqual(Game.objects.filter(season__gt=222).count(), 3)
        self.assertEqual(Game.objects.filter(season__gt__exact=222).count(), 3)

        # Games in 2011
        self.assertEqual(Game.objects.filter(season__year=2011).count(), 2)
        self.assertEqual(Game.objects.filter(season__year__exact=2011).count(), 2)
        self.assertEqual(Game.objects.filter(season__gt=333).count(), 2)
        self.assertEqual(Game.objects.filter(season__gt__exact=333).count(), 2)
        self.assertEqual(Game.objects.filter(season__year__gt=2010).count(), 2)
        self.assertEqual(Game.objects.filter(season__gt__gt=222).count(), 2)

        # Games played in 2010 and 2011
        self.assertEqual(Game.objects.filter(season__year__in=[2010, 2011]).count(), 5)
        self.assertEqual(Game.objects.filter(season__year__gt=2009).count(), 5)
        self.assertEqual(Game.objects.filter(season__gt__in=[222, 333]).count(), 5)
        self.assertEqual(Game.objects.filter(season__gt__gt=111).count(), 5)

        # Players who played in 2009
        self.assertEqual(Player.objects.filter(games__season__year=2009).distinct().count(), 2)
        self.assertEqual(Player.objects.filter(games__season__year__exact=2009).distinct().count(), 2)
        self.assertEqual(Player.objects.filter(games__season__gt=111).distinct().count(), 2)
        self.assertEqual(Player.objects.filter(games__season__gt__exact=111).distinct().count(), 2)

        # Players who played in 2010
        self.assertEqual(Player.objects.filter(games__season__year=2010).distinct().count(), 1)
        self.assertEqual(Player.objects.filter(games__season__year__exact=2010).distinct().count(), 1)
        self.assertEqual(Player.objects.filter(games__season__gt=222).distinct().count(), 1)
        self.assertEqual(Player.objects.filter(games__season__gt__exact=222).distinct().count(), 1)

        # Players who played in 2011
        self.assertEqual(Player.objects.filter(games__season__year=2011).distinct().count(), 2)
        self.assertEqual(Player.objects.filter(games__season__year__exact=2011).distinct().count(), 2)
        self.assertEqual(Player.objects.filter(games__season__gt=333).distinct().count(), 2)
        self.assertEqual(Player.objects.filter(games__season__year__gt=2010).distinct().count(), 2)
        self.assertEqual(Player.objects.filter(games__season__gt__gt=222).distinct().count(), 2)

    def test_chain_date_time_lookups(self):
        self.assertCountEqual(
            Article.objects.filter(pub_date__month__gt=7),
            [self.a5, self.a6],
        )
        self.assertCountEqual(
            Article.objects.filter(pub_date__day__gte=27),
            [self.a2, self.a3, self.a4, self.a7],
        )
        self.assertCountEqual(
            Article.objects.filter(pub_date__hour__lt=8),
            [self.a1, self.a2, self.a3, self.a4, self.a7],
        )
        self.assertCountEqual(
            Article.objects.filter(pub_date__minute__lte=0),
            [self.a1, self.a2, self.a3, self.a4, self.a5, self.a6, self.a7],
        )

    def test_exact_none_transform(self):
        """Transforms are used for __exact=None."""
        Season.objects.create(year=1, nulled_text_field='not null')
        self.assertFalse(Season.objects.filter(nulled_text_field__isnull=True))
        self.assertTrue(Season.objects.filter(nulled_text_field__nulled__isnull=True))
        self.assertTrue(Season.objects.filter(nulled_text_field__nulled__exact=None))
        self.assertTrue(Season.objects.filter(nulled_text_field__nulled=None))

    def test_exact_sliced_queryset_limit_one(self):
        self.assertCountEqual(
            Article.objects.filter(author=Author.objects.all()[:1]),
            [self.a1, self.a2, self.a3, self.a4]
        )

    def test_exact_sliced_queryset_limit_one_offset(self):
        self.assertCountEqual(
            Article.objects.filter(author=Author.objects.all()[1:2]),
            [self.a5, self.a6, self.a7]
        )

    def test_exact_sliced_queryset_not_limited_to_one(self):
        msg = (
            'The QuerySet value for an exact lookup must be limited to one '
            'result using slicing.'
        )
        with self.assertRaisesMessage(ValueError, msg):
            list(Article.objects.filter(author=Author.objects.all()[:2]))
        with self.assertRaisesMessage(ValueError, msg):
            list(Article.objects.filter(author=Author.objects.all()[1:]))

    def test_custom_field_none_rhs(self):
        """
        __exact=value is transformed to __isnull=True if Field.get_prep_value()
        converts value to None.
        """
        season = Season.objects.create(year=2012, nulled_text_field=None)
        self.assertTrue(Season.objects.filter(pk=season.pk, nulled_text_field__isnull=True))
        self.assertTrue(Season.objects.filter(pk=season.pk, nulled_text_field=''))

    def test_pattern_lookups_with_substr(self):
        a = Author.objects.create(name='John Smith', alias='Johx')
        b = Author.objects.create(name='Rhonda Simpson', alias='sonx')
        tests = (
            ('startswith', [a]),
            ('istartswith', [a]),
            ('contains', [a, b]),
            ('icontains', [a, b]),
            ('endswith', [b]),
            ('iendswith', [b]),
        )
        for lookup, result in tests:
            with self.subTest(lookup=lookup):
                authors = Author.objects.filter(**{'name__%s' % lookup: Substr('alias', 1, 3)})
                self.assertCountEqual(authors, result)

    def test_custom_lookup_none_rhs(self):
        """Lookup.can_use_none_as_rhs=True allows None as a lookup value."""
        season = Season.objects.create(year=2012, nulled_text_field=None)
        query = Season.objects.get_queryset().query
        field = query.model._meta.get_field('nulled_text_field')
        self.assertIsInstance(query.build_lookup(['isnull_none_rhs'], field, None), IsNullWithNoneAsRHS)
        self.assertTrue(Season.objects.filter(pk=season.pk, nulled_text_field__isnull_none_rhs=True))

    def test_exact_exists(self):
        qs = Article.objects.filter(pk=OuterRef('pk'))
        seasons = Season.objects.annotate(
            pk_exists=Exists(qs),
        ).filter(
            pk_exists=Exists(qs),
        )
        self.assertCountEqual(seasons, Season.objects.all())

    def test_nested_outerref_lhs(self):
        tag = Tag.objects.create(name=self.au1.alias)
        tag.articles.add(self.a1)
        qs = Tag.objects.annotate(
            has_author_alias_match=Exists(
                Article.objects.annotate(
                    author_exists=Exists(
                        Author.objects.filter(alias=OuterRef(OuterRef('name')))
                    ),
                ).filter(author_exists=True)
            ),
        )
        self.assertEqual(qs.get(has_author_alias_match=True), tag)

    def test_exact_query_rhs_with_selected_columns(self):
        newest_author = Author.objects.create(name='Author 2')
        authors_max_ids = Author.objects.filter(
            name='Author 2',
        ).values(
            'name',
        ).annotate(
            max_id=Max('id'),
        ).values('max_id')
        authors = Author.objects.filter(id=authors_max_ids[:1])
        self.assertEqual(authors.get(), newest_author)

    def test_isnull_non_boolean_value(self):
        # These tests will catch ValueError in Django 4.0 when using
        # non-boolean values for an isnull lookup becomes forbidden.
        # msg = (
        #     'The QuerySet value for an isnull lookup must be True or False.'
        # )
        msg = (
            'Using a non-boolean value for an isnull lookup is deprecated, '
            'use True or False instead.'
        )
        tests = [
            Author.objects.filter(alias__isnull=1),
            Article.objects.filter(author__isnull=1),
            Season.objects.filter(games__isnull=1),
            Freebie.objects.filter(stock__isnull=1),
        ]
        for qs in tests:
            with self.subTest(qs=qs):
                with self.assertWarnsMessage(RemovedInDjango40Warning, msg):
                    qs.exists()
