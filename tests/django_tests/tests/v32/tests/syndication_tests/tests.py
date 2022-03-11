import datetime
from xml.dom import minidom

from django.contrib.sites.models import Site
from django.contrib.syndication import views
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings
from django.test.utils import requires_tz_support
from django.utils import timezone
from django.utils.feedgenerator import rfc2822_date, rfc3339_date

from .models import Article, Entry

TZ = timezone.get_default_timezone()


class FeedTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.e1 = Entry.objects.create(
            title='My first entry', updated=datetime.datetime(1980, 1, 1, 12, 30),
            published=datetime.datetime(1986, 9, 25, 20, 15, 00)
        )
        cls.e2 = Entry.objects.create(
            title='My second entry', updated=datetime.datetime(2008, 1, 2, 12, 30),
            published=datetime.datetime(2006, 3, 17, 18, 0)
        )
        cls.e3 = Entry.objects.create(
            title='My third entry', updated=datetime.datetime(2008, 1, 2, 13, 30),
            published=datetime.datetime(2005, 6, 14, 10, 45)
        )
        cls.e4 = Entry.objects.create(
            title='A & B < C > D', updated=datetime.datetime(2008, 1, 3, 13, 30),
            published=datetime.datetime(2005, 11, 25, 12, 11, 23)
        )
        cls.e5 = Entry.objects.create(
            title='My last entry', updated=datetime.datetime(2013, 1, 20, 0, 0),
            published=datetime.datetime(2013, 3, 25, 20, 0)
        )
        cls.a1 = Article.objects.create(
            title='My first article',
            entry=cls.e1,
            updated=datetime.datetime(1986, 11, 21, 9, 12, 18),
            published=datetime.datetime(1986, 10, 21, 9, 12, 18),
        )

    def assertChildNodes(self, elem, expected):
        actual = {n.nodeName for n in elem.childNodes}
        expected = set(expected)
        self.assertEqual(actual, expected)

    def assertChildNodeContent(self, elem, expected):
        for k, v in expected.items():
            self.assertEqual(
                elem.getElementsByTagName(k)[0].firstChild.wholeText, v)

    def assertCategories(self, elem, expected):
        self.assertEqual(
            {i.firstChild.wholeText for i in elem.childNodes if i.nodeName == 'category'},
            set(expected)
        )


@override_settings(ROOT_URLCONF='syndication_tests.urls')
class SyndicationFeedTest(FeedTestCase):
    """
    Tests for the high-level syndication feed framework.
    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # This cleanup is necessary because contrib.sites cache
        # makes tests interfere with each other, see #11505
        Site.objects.clear_cache()

    def test_rss2_feed(self):
        """
        Test the structure and content of feeds generated by Rss201rev2Feed.
        """
        response = self.client.get('/syndication/rss2/')
        doc = minidom.parseString(response.content)

        # Making sure there's only 1 `rss` element and that the correct
        # RSS version was specified.
        feed_elem = doc.getElementsByTagName('rss')
        self.assertEqual(len(feed_elem), 1)
        feed = feed_elem[0]
        self.assertEqual(feed.getAttribute('version'), '2.0')
        self.assertEqual(feed.getElementsByTagName('language')[0].firstChild.nodeValue, 'en')

        # Making sure there's only one `channel` element w/in the
        # `rss` element.
        chan_elem = feed.getElementsByTagName('channel')
        self.assertEqual(len(chan_elem), 1)
        chan = chan_elem[0]

        # Find the last build date
        d = Entry.objects.latest('published').published
        last_build_date = rfc2822_date(timezone.make_aware(d, TZ))

        self.assertChildNodes(
            chan, [
                'title', 'link', 'description', 'language', 'lastBuildDate',
                'item', 'atom:link', 'ttl', 'copyright', 'category',
            ]
        )
        self.assertChildNodeContent(chan, {
            'title': 'My blog',
            'description': 'A more thorough description of my blog.',
            'link': 'http://example.com/blog/',
            'language': 'en',
            'lastBuildDate': last_build_date,
            'ttl': '600',
            'copyright': 'Copyright (c) 2007, Sally Smith',
        })
        self.assertCategories(chan, ['python', 'django'])

        # Ensure the content of the channel is correct
        self.assertChildNodeContent(chan, {
            'title': 'My blog',
            'link': 'http://example.com/blog/',
        })

        # Check feed_url is passed
        self.assertEqual(
            chan.getElementsByTagName('atom:link')[0].getAttribute('href'),
            'http://example.com/syndication/rss2/'
        )

        # Find the pubdate of the first feed item
        d = Entry.objects.get(pk=self.e1.pk).published
        pub_date = rfc2822_date(timezone.make_aware(d, TZ))

        items = chan.getElementsByTagName('item')
        self.assertEqual(len(items), Entry.objects.count())
        self.assertChildNodeContent(items[0], {
            'title': 'My first entry',
            'description': 'Overridden description: My first entry',
            'link': 'http://example.com/blog/%s/' % self.e1.pk,
            'guid': 'http://example.com/blog/%s/' % self.e1.pk,
            'pubDate': pub_date,
            'author': 'test@example.com (Sally Smith)',
            'comments': '/blog/%s/comments' % self.e1.pk,
        })
        self.assertCategories(items[0], ['python', 'testing'])
        for item in items:
            self.assertChildNodes(item, [
                'title',
                'link',
                'description',
                'guid',
                'category',
                'pubDate',
                'author',
                'comments',
            ])
            # Assert that <guid> does not have any 'isPermaLink' attribute
            self.assertIsNone(item.getElementsByTagName(
                'guid')[0].attributes.get('isPermaLink'))

    def test_rss2_feed_guid_permalink_false(self):
        """
        Test if the 'isPermaLink' attribute of <guid> element of an item
        in the RSS feed is 'false'.
        """
        response = self.client.get(
            '/syndication/rss2/guid_ispermalink_false/')
        doc = minidom.parseString(response.content)
        chan = doc.getElementsByTagName(
            'rss')[0].getElementsByTagName('channel')[0]
        items = chan.getElementsByTagName('item')
        for item in items:
            self.assertEqual(
                item.getElementsByTagName('guid')[0].attributes.get(
                    'isPermaLink').value, "false")

    def test_rss2_feed_guid_permalink_true(self):
        """
        Test if the 'isPermaLink' attribute of <guid> element of an item
        in the RSS feed is 'true'.
        """
        response = self.client.get(
            '/syndication/rss2/guid_ispermalink_true/')
        doc = minidom.parseString(response.content)
        chan = doc.getElementsByTagName(
            'rss')[0].getElementsByTagName('channel')[0]
        items = chan.getElementsByTagName('item')
        for item in items:
            self.assertEqual(
                item.getElementsByTagName('guid')[0].attributes.get(
                    'isPermaLink').value, "true")

    def test_rss2_single_enclosure(self):
        response = self.client.get('/syndication/rss2/single-enclosure/')
        doc = minidom.parseString(response.content)
        chan = doc.getElementsByTagName('rss')[0].getElementsByTagName('channel')[0]
        items = chan.getElementsByTagName('item')
        for item in items:
            enclosures = item.getElementsByTagName('enclosure')
            self.assertEqual(len(enclosures), 1)

    def test_rss2_multiple_enclosures(self):
        with self.assertRaisesMessage(
            ValueError,
            "RSS feed items may only have one enclosure, see "
            "http://www.rssboard.org/rss-profile#element-channel-item-enclosure"
        ):
            self.client.get('/syndication/rss2/multiple-enclosure/')

    def test_rss091_feed(self):
        """
        Test the structure and content of feeds generated by RssUserland091Feed.
        """
        response = self.client.get('/syndication/rss091/')
        doc = minidom.parseString(response.content)

        # Making sure there's only 1 `rss` element and that the correct
        # RSS version was specified.
        feed_elem = doc.getElementsByTagName('rss')
        self.assertEqual(len(feed_elem), 1)
        feed = feed_elem[0]
        self.assertEqual(feed.getAttribute('version'), '0.91')

        # Making sure there's only one `channel` element w/in the
        # `rss` element.
        chan_elem = feed.getElementsByTagName('channel')
        self.assertEqual(len(chan_elem), 1)
        chan = chan_elem[0]
        self.assertChildNodes(
            chan, [
                'title', 'link', 'description', 'language', 'lastBuildDate',
                'item', 'atom:link', 'ttl', 'copyright', 'category',
            ]
        )

        # Ensure the content of the channel is correct
        self.assertChildNodeContent(chan, {
            'title': 'My blog',
            'link': 'http://example.com/blog/',
        })
        self.assertCategories(chan, ['python', 'django'])

        # Check feed_url is passed
        self.assertEqual(
            chan.getElementsByTagName('atom:link')[0].getAttribute('href'),
            'http://example.com/syndication/rss091/'
        )

        items = chan.getElementsByTagName('item')
        self.assertEqual(len(items), Entry.objects.count())
        self.assertChildNodeContent(items[0], {
            'title': 'My first entry',
            'description': 'Overridden description: My first entry',
            'link': 'http://example.com/blog/%s/' % self.e1.pk,
        })
        for item in items:
            self.assertChildNodes(item, ['title', 'link', 'description'])
            self.assertCategories(item, [])

    def test_atom_feed(self):
        """
        Test the structure and content of feeds generated by Atom1Feed.
        """
        response = self.client.get('/syndication/atom/')
        feed = minidom.parseString(response.content).firstChild

        self.assertEqual(feed.nodeName, 'feed')
        self.assertEqual(feed.getAttribute('xmlns'), 'http://www.w3.org/2005/Atom')
        self.assertChildNodes(
            feed,
            ['title', 'subtitle', 'link', 'id', 'updated', 'entry', 'rights', 'category', 'author']
        )
        for link in feed.getElementsByTagName('link'):
            if link.getAttribute('rel') == 'self':
                self.assertEqual(link.getAttribute('href'), 'http://example.com/syndication/atom/')

        entries = feed.getElementsByTagName('entry')
        self.assertEqual(len(entries), Entry.objects.count())
        for entry in entries:
            self.assertChildNodes(entry, [
                'title',
                'link',
                'id',
                'summary',
                'category',
                'updated',
                'published',
                'rights',
                'author',
            ])
            summary = entry.getElementsByTagName('summary')[0]
            self.assertEqual(summary.getAttribute('type'), 'html')

    def test_atom_feed_published_and_updated_elements(self):
        """
        The published and updated elements are not
        the same and now adhere to RFC 4287.
        """
        response = self.client.get('/syndication/atom/')
        feed = minidom.parseString(response.content).firstChild
        entries = feed.getElementsByTagName('entry')

        published = entries[0].getElementsByTagName('published')[0].firstChild.wholeText
        updated = entries[0].getElementsByTagName('updated')[0].firstChild.wholeText

        self.assertNotEqual(published, updated)

    def test_atom_single_enclosure(self):
        response = self.client.get('/syndication/atom/single-enclosure/')
        feed = minidom.parseString(response.content).firstChild
        items = feed.getElementsByTagName('entry')
        for item in items:
            links = item.getElementsByTagName('link')
            links = [link for link in links if link.getAttribute('rel') == 'enclosure']
            self.assertEqual(len(links), 1)

    def test_atom_multiple_enclosures(self):
        response = self.client.get('/syndication/atom/multiple-enclosure/')
        feed = minidom.parseString(response.content).firstChild
        items = feed.getElementsByTagName('entry')
        for item in items:
            links = item.getElementsByTagName('link')
            links = [link for link in links if link.getAttribute('rel') == 'enclosure']
            self.assertEqual(len(links), 2)

    def test_latest_post_date(self):
        """
        Both the published and updated dates are
        considered when determining the latest post date.
        """
        # this feed has a `published` element with the latest date
        response = self.client.get('/syndication/atom/')
        feed = minidom.parseString(response.content).firstChild
        updated = feed.getElementsByTagName('updated')[0].firstChild.wholeText

        d = Entry.objects.latest('published').published
        latest_published = rfc3339_date(timezone.make_aware(d, TZ))

        self.assertEqual(updated, latest_published)

        # this feed has an `updated` element with the latest date
        response = self.client.get('/syndication/latest/')
        feed = minidom.parseString(response.content).firstChild
        updated = feed.getElementsByTagName('updated')[0].firstChild.wholeText

        d = Entry.objects.exclude(title='My last entry').latest('updated').updated
        latest_updated = rfc3339_date(timezone.make_aware(d, TZ))

        self.assertEqual(updated, latest_updated)

    def test_custom_feed_generator(self):
        response = self.client.get('/syndication/custom/')
        feed = minidom.parseString(response.content).firstChild

        self.assertEqual(feed.nodeName, 'feed')
        self.assertEqual(feed.getAttribute('django'), 'rocks')
        self.assertChildNodes(
            feed,
            ['title', 'subtitle', 'link', 'id', 'updated', 'entry', 'spam', 'rights', 'category', 'author']
        )

        entries = feed.getElementsByTagName('entry')
        self.assertEqual(len(entries), Entry.objects.count())
        for entry in entries:
            self.assertEqual(entry.getAttribute('bacon'), 'yum')
            self.assertChildNodes(entry, [
                'title',
                'link',
                'id',
                'summary',
                'ministry',
                'rights',
                'author',
                'updated',
                'published',
                'category',
            ])
            summary = entry.getElementsByTagName('summary')[0]
            self.assertEqual(summary.getAttribute('type'), 'html')

    def test_feed_generator_language_attribute(self):
        response = self.client.get('/syndication/language/')
        feed = minidom.parseString(response.content).firstChild
        self.assertEqual(feed.firstChild.getElementsByTagName('language')[0].firstChild.nodeValue, 'de')

    def test_title_escaping(self):
        """
        Titles are escaped correctly in RSS feeds.
        """
        response = self.client.get('/syndication/rss2/')
        doc = minidom.parseString(response.content)
        for item in doc.getElementsByTagName('item'):
            link = item.getElementsByTagName('link')[0]
            if link.firstChild.wholeText == 'http://example.com/blog/4/':
                title = item.getElementsByTagName('title')[0]
                self.assertEqual(title.firstChild.wholeText, 'A &amp; B &lt; C &gt; D')

    def test_naive_datetime_conversion(self):
        """
        Datetimes are correctly converted to the local time zone.
        """
        # Naive date times passed in get converted to the local time zone, so
        # check the received zone offset against the local offset.
        response = self.client.get('/syndication/naive-dates/')
        doc = minidom.parseString(response.content)
        updated = doc.getElementsByTagName('updated')[0].firstChild.wholeText

        d = Entry.objects.latest('published').published
        latest = rfc3339_date(timezone.make_aware(d, TZ))

        self.assertEqual(updated, latest)

    def test_aware_datetime_conversion(self):
        """
        Datetimes with timezones don't get trodden on.
        """
        response = self.client.get('/syndication/aware-dates/')
        doc = minidom.parseString(response.content)
        published = doc.getElementsByTagName('published')[0].firstChild.wholeText
        self.assertEqual(published[-6:], '+00:42')

    @requires_tz_support
    def test_feed_last_modified_time_naive_date(self):
        """
        Tests the Last-Modified header with naive publication dates.
        """
        response = self.client.get('/syndication/naive-dates/')
        self.assertEqual(response.headers['Last-Modified'], 'Tue, 26 Mar 2013 01:00:00 GMT')

    def test_feed_last_modified_time(self):
        """
        Tests the Last-Modified header with aware publication dates.
        """
        response = self.client.get('/syndication/aware-dates/')
        self.assertEqual(response.headers['Last-Modified'], 'Mon, 25 Mar 2013 19:18:00 GMT')

        # No last-modified when feed has no item_pubdate
        response = self.client.get('/syndication/no_pubdate/')
        self.assertFalse(response.has_header('Last-Modified'))

    def test_feed_url(self):
        """
        The feed_url can be overridden.
        """
        response = self.client.get('/syndication/feedurl/')
        doc = minidom.parseString(response.content)
        for link in doc.getElementsByTagName('link'):
            if link.getAttribute('rel') == 'self':
                self.assertEqual(link.getAttribute('href'), 'http://example.com/customfeedurl/')

    def test_secure_urls(self):
        """
        Test URLs are prefixed with https:// when feed is requested over HTTPS.
        """
        response = self.client.get('/syndication/rss2/', **{
            'wsgi.url_scheme': 'https',
        })
        doc = minidom.parseString(response.content)
        chan = doc.getElementsByTagName('channel')[0]
        self.assertEqual(
            chan.getElementsByTagName('link')[0].firstChild.wholeText[0:5],
            'https'
        )
        atom_link = chan.getElementsByTagName('atom:link')[0]
        self.assertEqual(atom_link.getAttribute('href')[0:5], 'https')
        for link in doc.getElementsByTagName('link'):
            if link.getAttribute('rel') == 'self':
                self.assertEqual(link.getAttribute('href')[0:5], 'https')

    def test_item_link_error(self):
        """
        An ImproperlyConfigured is raised if no link could be found for the
        item(s).
        """
        msg = (
            'Give your Article class a get_absolute_url() method, or define '
            'an item_link() method in your Feed class.'
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            self.client.get('/syndication/articles/')

    def test_template_feed(self):
        """
        The item title and description can be overridden with templates.
        """
        response = self.client.get('/syndication/template/')
        doc = minidom.parseString(response.content)
        feed = doc.getElementsByTagName('rss')[0]
        chan = feed.getElementsByTagName('channel')[0]
        items = chan.getElementsByTagName('item')

        self.assertChildNodeContent(items[0], {
            'title': 'Title in your templates: My first entry\n',
            'description': 'Description in your templates: My first entry\n',
            'link': 'http://example.com/blog/%s/' % self.e1.pk,
        })

    def test_template_context_feed(self):
        """
        Custom context data can be passed to templates for title
        and description.
        """
        response = self.client.get('/syndication/template_context/')
        doc = minidom.parseString(response.content)
        feed = doc.getElementsByTagName('rss')[0]
        chan = feed.getElementsByTagName('channel')[0]
        items = chan.getElementsByTagName('item')

        self.assertChildNodeContent(items[0], {
            'title': 'My first entry (foo is bar)\n',
            'description': 'My first entry (foo is bar)\n',
        })

    def test_add_domain(self):
        """
        add_domain() prefixes domains onto the correct URLs.
        """
        prefix_domain_mapping = (
            (('example.com', '/foo/?arg=value'), 'http://example.com/foo/?arg=value'),
            (('example.com', '/foo/?arg=value', True), 'https://example.com/foo/?arg=value'),
            (('example.com', 'http://djangoproject.com/doc/'), 'http://djangoproject.com/doc/'),
            (('example.com', 'https://djangoproject.com/doc/'), 'https://djangoproject.com/doc/'),
            (('example.com', 'mailto:uhoh@djangoproject.com'), 'mailto:uhoh@djangoproject.com'),
            (('example.com', '//example.com/foo/?arg=value'), 'http://example.com/foo/?arg=value'),
        )
        for prefix in prefix_domain_mapping:
            with self.subTest(prefix=prefix):
                self.assertEqual(views.add_domain(*prefix[0]), prefix[1])

    def test_get_object(self):
        response = self.client.get('/syndication/rss2/articles/%s/' % self.e1.pk)
        doc = minidom.parseString(response.content)
        feed = doc.getElementsByTagName('rss')[0]
        chan = feed.getElementsByTagName('channel')[0]
        items = chan.getElementsByTagName('item')

        self.assertChildNodeContent(items[0], {
            'comments': '/blog/%s/article/%s/comments' % (self.e1.pk, self.a1.pk),
            'description': 'Article description: My first article',
            'link': 'http://example.com/blog/%s/article/%s/' % (self.e1.pk, self.a1.pk),
            'title': 'Title: My first article',
            'pubDate': rfc2822_date(timezone.make_aware(self.a1.published, TZ)),
        })

    def test_get_non_existent_object(self):
        response = self.client.get('/syndication/rss2/articles/0/')
        self.assertEqual(response.status_code, 404)
