import json
import sys

from django.core.exceptions import SuspiciousFileOperation
from django.test import SimpleTestCase, ignore_warnings
from django.utils import text
from django.utils.deprecation import RemovedInDjango40Warning
from django.utils.functional import lazystr
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy, override

IS_WIDE_BUILD = (len('\U0001F4A9') == 1)


class TestUtilsText(SimpleTestCase):

    def test_get_text_list(self):
        self.assertEqual(text.get_text_list(['a', 'b', 'c', 'd']), 'a, b, c or d')
        self.assertEqual(text.get_text_list(['a', 'b', 'c'], 'and'), 'a, b and c')
        self.assertEqual(text.get_text_list(['a', 'b'], 'and'), 'a and b')
        self.assertEqual(text.get_text_list(['a']), 'a')
        self.assertEqual(text.get_text_list([]), '')
        with override('ar'):
            self.assertEqual(text.get_text_list(['a', 'b', 'c']), "a، b أو c")

    def test_smart_split(self):
        testdata = [
            ('This is "a person" test.',
                ['This', 'is', '"a person"', 'test.']),
            ('This is "a person\'s" test.',
                ['This', 'is', '"a person\'s"', 'test.']),
            ('This is "a person\\"s" test.',
                ['This', 'is', '"a person\\"s"', 'test.']),
            ('"a \'one',
                ['"a', "'one"]),
            ('all friends\' tests',
                ['all', 'friends\'', 'tests']),
            ('url search_page words="something else"',
                ['url', 'search_page', 'words="something else"']),
            ("url search_page words='something else'",
                ['url', 'search_page', "words='something else'"]),
            ('url search_page words "something else"',
                ['url', 'search_page', 'words', '"something else"']),
            ('url search_page words-"something else"',
                ['url', 'search_page', 'words-"something else"']),
            ('url search_page words=hello',
                ['url', 'search_page', 'words=hello']),
            ('url search_page words="something else',
                ['url', 'search_page', 'words="something', 'else']),
            ("cut:','|cut:' '",
                ["cut:','|cut:' '"]),
            (lazystr("a b c d"),  # Test for #20231
                ['a', 'b', 'c', 'd']),
        ]
        for test, expected in testdata:
            with self.subTest(value=test):
                self.assertEqual(list(text.smart_split(test)), expected)

    def test_truncate_chars(self):
        truncator = text.Truncator('The quick brown fox jumped over the lazy dog.')
        self.assertEqual('The quick brown fox jumped over the lazy dog.', truncator.chars(100)),
        self.assertEqual('The quick brown fox …', truncator.chars(21)),
        self.assertEqual('The quick brown fo.....', truncator.chars(23, '.....')),
        self.assertEqual('.....', truncator.chars(4, '.....')),

        nfc = text.Truncator('o\xfco\xfco\xfco\xfc')
        nfd = text.Truncator('ou\u0308ou\u0308ou\u0308ou\u0308')
        self.assertEqual('oüoüoüoü', nfc.chars(8))
        self.assertEqual('oüoüoüoü', nfd.chars(8))
        self.assertEqual('oü…', nfc.chars(3))
        self.assertEqual('oü…', nfd.chars(3))

        # Ensure the final length is calculated correctly when there are
        # combining characters with no precomposed form, and that combining
        # characters are not split up.
        truncator = text.Truncator('-B\u030AB\u030A----8')
        self.assertEqual('-B\u030A…', truncator.chars(3))
        self.assertEqual('-B\u030AB\u030A-…', truncator.chars(5))
        self.assertEqual('-B\u030AB\u030A----8', truncator.chars(8))

        # Ensure the length of the end text is correctly calculated when it
        # contains combining characters with no precomposed form.
        truncator = text.Truncator('-----')
        self.assertEqual('---B\u030A', truncator.chars(4, 'B\u030A'))
        self.assertEqual('-----', truncator.chars(5, 'B\u030A'))

        # Make a best effort to shorten to the desired length, but requesting
        # a length shorter than the ellipsis shouldn't break
        self.assertEqual('…', text.Truncator('asdf').chars(0))
        # lazy strings are handled correctly
        self.assertEqual(text.Truncator(lazystr('The quick brown fox')).chars(10), 'The quick…')

    def test_truncate_chars_html(self):
        perf_test_values = [
            (('</a' + '\t' * 50000) + '//>', None),
            ('&' * 50000, '&' * 9 + '…'),
            ('_X<<<<<<<<<<<>', None),
        ]
        for value, expected in perf_test_values:
            with self.subTest(value=value):
                truncator = text.Truncator(value)
                self.assertEqual(expected if expected else value, truncator.chars(10, html=True))

    def test_truncate_words(self):
        truncator = text.Truncator('The quick brown fox jumped over the lazy dog.')
        self.assertEqual('The quick brown fox jumped over the lazy dog.', truncator.words(10))
        self.assertEqual('The quick brown fox…', truncator.words(4))
        self.assertEqual('The quick brown fox[snip]', truncator.words(4, '[snip]'))
        # lazy strings are handled correctly
        truncator = text.Truncator(lazystr('The quick brown fox jumped over the lazy dog.'))
        self.assertEqual('The quick brown fox…', truncator.words(4))

    def test_truncate_html_words(self):
        truncator = text.Truncator(
            '<p id="par"><strong><em>The quick brown fox jumped over the lazy dog.</em></strong></p>'
        )
        self.assertEqual(
            '<p id="par"><strong><em>The quick brown fox jumped over the lazy dog.</em></strong></p>',
            truncator.words(10, html=True)
        )
        self.assertEqual(
            '<p id="par"><strong><em>The quick brown fox…</em></strong></p>',
            truncator.words(4, html=True)
        )
        self.assertEqual(
            '<p id="par"><strong><em>The quick brown fox....</em></strong></p>',
            truncator.words(4, '....', html=True)
        )
        self.assertEqual(
            '<p id="par"><strong><em>The quick brown fox</em></strong></p>',
            truncator.words(4, '', html=True)
        )

        # Test with new line inside tag
        truncator = text.Truncator(
            '<p>The quick <a href="xyz.html"\n id="mylink">brown fox</a> jumped over the lazy dog.</p>'
        )
        self.assertEqual(
            '<p>The quick <a href="xyz.html"\n id="mylink">brown…</a></p>',
            truncator.words(3, html=True)
        )

        # Test self-closing tags
        truncator = text.Truncator('<br/>The <hr />quick brown fox jumped over the lazy dog.')
        self.assertEqual('<br/>The <hr />quick brown…', truncator.words(3, html=True))
        truncator = text.Truncator('<br>The <hr/>quick <em>brown fox</em> jumped over the lazy dog.')
        self.assertEqual('<br>The <hr/>quick <em>brown…</em>', truncator.words(3, html=True))

        # Test html entities
        truncator = text.Truncator('<i>Buenos d&iacute;as! &#x00bf;C&oacute;mo est&aacute;?</i>')
        self.assertEqual('<i>Buenos d&iacute;as! &#x00bf;C&oacute;mo…</i>', truncator.words(3, html=True))
        truncator = text.Truncator('<p>I &lt;3 python, what about you?</p>')
        self.assertEqual('<p>I &lt;3 python,…</p>', truncator.words(3, html=True))

        perf_test_values = [
            ('</a' + '\t' * 50000) + '//>',
            '&' * 50000,
            '_X<<<<<<<<<<<>',
        ]
        for value in perf_test_values:
            with self.subTest(value=value):
                truncator = text.Truncator(value)
                self.assertEqual(value, truncator.words(50, html=True))

    def test_wrap(self):
        digits = '1234 67 9'
        self.assertEqual(text.wrap(digits, 100), '1234 67 9')
        self.assertEqual(text.wrap(digits, 9), '1234 67 9')
        self.assertEqual(text.wrap(digits, 8), '1234 67\n9')

        self.assertEqual(text.wrap('short\na long line', 7), 'short\na long\nline')
        self.assertEqual(text.wrap('do-not-break-long-words please? ok', 8), 'do-not-break-long-words\nplease?\nok')

        long_word = 'l%sng' % ('o' * 20)
        self.assertEqual(text.wrap(long_word, 20), long_word)
        self.assertEqual(text.wrap('a %s word' % long_word, 10), 'a\n%s\nword' % long_word)
        self.assertEqual(text.wrap(lazystr(digits), 100), '1234 67 9')

    def test_normalize_newlines(self):
        self.assertEqual(text.normalize_newlines("abc\ndef\rghi\r\n"), "abc\ndef\nghi\n")
        self.assertEqual(text.normalize_newlines("\n\r\r\n\r"), "\n\n\n\n")
        self.assertEqual(text.normalize_newlines("abcdefghi"), "abcdefghi")
        self.assertEqual(text.normalize_newlines(""), "")
        self.assertEqual(text.normalize_newlines(lazystr("abc\ndef\rghi\r\n")), "abc\ndef\nghi\n")

    def test_phone2numeric(self):
        numeric = text.phone2numeric('0800 flowers')
        self.assertEqual(numeric, '0800 3569377')
        lazy_numeric = lazystr(text.phone2numeric('0800 flowers'))
        self.assertEqual(lazy_numeric, '0800 3569377')

    def test_slugify(self):
        items = (
            # given - expected - Unicode?
            ('Hello, World!', 'hello-world', False),
            ('spam & eggs', 'spam-eggs', False),
            (' multiple---dash and  space ', 'multiple-dash-and-space', False),
            ('\t whitespace-in-value \n', 'whitespace-in-value', False),
            ('underscore_in-value', 'underscore_in-value', False),
            ('__strip__underscore-value___', 'strip__underscore-value', False),
            ('--strip-dash-value---', 'strip-dash-value', False),
            ('__strip-mixed-value---', 'strip-mixed-value', False),
            ('_ -strip-mixed-value _-', 'strip-mixed-value', False),
            ('spam & ıçüş', 'spam-ıçüş', True),
            ('foo ıç bar', 'foo-ıç-bar', True),
            ('    foo ıç bar', 'foo-ıç-bar', True),
            ('你好', '你好', True),
            ('İstanbul', 'istanbul', True),
        )
        for value, output, is_unicode in items:
            with self.subTest(value=value):
                self.assertEqual(text.slugify(value, allow_unicode=is_unicode), output)
        # Interning the result may be useful, e.g. when fed to Path.
        with self.subTest('intern'):
            self.assertEqual(sys.intern(text.slugify('a')), 'a')

    @ignore_warnings(category=RemovedInDjango40Warning)
    def test_unescape_entities(self):
        items = [
            ('', ''),
            ('foo', 'foo'),
            ('&amp;', '&'),
            ('&am;', '&am;'),
            ('&#x26;', '&'),
            ('&#xk;', '&#xk;'),
            ('&#38;', '&'),
            ('foo &amp; bar', 'foo & bar'),
            ('foo & bar', 'foo & bar'),
        ]
        for value, output in items:
            with self.subTest(value=value):
                self.assertEqual(text.unescape_entities(value), output)
                self.assertEqual(text.unescape_entities(lazystr(value)), output)

    def test_unescape_entities_deprecated(self):
        msg = (
            'django.utils.text.unescape_entities() is deprecated in favor of '
            'html.unescape().'
        )
        with self.assertWarnsMessage(RemovedInDjango40Warning, msg):
            text.unescape_entities('foo')

    def test_unescape_string_literal(self):
        items = [
            ('"abc"', 'abc'),
            ("'abc'", 'abc'),
            ('"a \"bc\""', 'a "bc"'),
            ("'\'ab\' c'", "'ab' c"),
        ]
        for value, output in items:
            with self.subTest(value=value):
                self.assertEqual(text.unescape_string_literal(value), output)
                self.assertEqual(text.unescape_string_literal(lazystr(value)), output)

    def test_get_valid_filename(self):
        filename = "^&'@{}[],$=!-#()%+~_123.txt"
        self.assertEqual(text.get_valid_filename(filename), "-_123.txt")
        self.assertEqual(text.get_valid_filename(lazystr(filename)), "-_123.txt")
        msg = "Could not derive file name from '???'"
        with self.assertRaisesMessage(SuspiciousFileOperation, msg):
            text.get_valid_filename('???')
        # After sanitizing this would yield '..'.
        msg = "Could not derive file name from '$.$.$'"
        with self.assertRaisesMessage(SuspiciousFileOperation, msg):
            text.get_valid_filename('$.$.$')

    def test_compress_sequence(self):
        data = [{'key': i} for i in range(10)]
        seq = list(json.JSONEncoder().iterencode(data))
        seq = [s.encode() for s in seq]
        actual_length = len(b''.join(seq))
        out = text.compress_sequence(seq)
        compressed_length = len(b''.join(out))
        self.assertLess(compressed_length, actual_length)

    def test_format_lazy(self):
        self.assertEqual('django/test', format_lazy('{}/{}', 'django', lazystr('test')))
        self.assertEqual('django/test', format_lazy('{0}/{1}', *('django', 'test')))
        self.assertEqual('django/test', format_lazy('{a}/{b}', **{'a': 'django', 'b': 'test'}))
        self.assertEqual('django/test', format_lazy('{a[0]}/{a[1]}', a=('django', 'test')))

        t = {}
        s = format_lazy('{0[a]}-{p[a]}', t, p=t)
        t['a'] = lazystr('django')
        self.assertEqual('django-django', s)
        t['a'] = 'update'
        self.assertEqual('update-update', s)

        # The format string can be lazy. (string comes from contrib.admin)
        s = format_lazy(
            gettext_lazy('Added {name} “{object}”.'),
            name='article', object='My first try',
        )
        with override('fr'):
            self.assertEqual('Ajout de article «\xa0My first try\xa0».', s)
