import unittest
from functools import partial

from jinja2 import escape, Markup, Environment

from flask import appcontext_pushed, url_for
from app import app

from arxiv.base.urls import links, urlizer, urlize
from browse.filters import line_feed_to_br, tex_to_utf, entity_to_utf


class Jinja_Custom_Fitlers_Test(unittest.TestCase):
    def test_with_jinja(self):
        jenv = Environment(autoescape=True)
        jenv.filters['urlize'] = urlizer(
            ['doi'], {'doi': (
                links.doi_patterns,
                links.doi_substituter,
                links.url_for_doi
            )}
        )
        self.assertEqual(
            jenv.from_string(
                '{{"something 10.1103/PhysRevD.76.013009 or other"|urlize}}'
            ).render(),
            'something <a href="https://dx.doi.org/10.1103/PhysRevD.76.013009">10.1103/PhysRevD.76.013009</a> or other'
        )


    def test_with_jinja_escapes(self):
        jenv = Environment(autoescape=True)
        jenv.filters['urlize'] = urlizer(
            ['arxiv_id', 'doi'], {'doi': (
                links.doi_patterns,
                links.doi_substituter,
                links.url_for_doi
            )}
        )
        self.assertEqual(
            jenv.from_string(
                '{{"something 10.1103/PhysRevD.76.013009 or other"|urlize}}'
            ).render(),
            'something <a href="https://dx.doi.org/10.1103/PhysRevD.76.013009">10.1103/PhysRevD.76.013009</a> or other'
        )

        self.assertEqual(
            jenv.from_string(
                '{{"<script>bad junk</script> something 10.1103/PhysRevD.76.013009"|urlize}}'
            ).render(),
            '&lt;script&gt;bad junk&lt;/script&gt; something <a href="https://dx.doi.org/10.1103/PhysRevD.76.013009">10.1103/PhysRevD.76.013009</a>'
        )

    def test_doi_filter(self):
        s = 'some test string 23$6#$5<>&456 http://google.com/notadoi'
        urlize_dois = urlizer(
            ['doi'], {'doi': (
                links.doi_patterns,
                links.doi_substituter,
                links.url_for_doi
            )}
        )
        self.assertEqual(urlize_dois(s), str(escape(s)))

        doi = '10.1103/PhysRevD.76.013009'
        doiurl = urlize_dois(doi)
        self.assertRegex(doiurl, r'^<a', 'should start with a tag')
        self.assertEqual(
            doiurl,
            str(Markup('<a href="https://dx.doi.org/10.1103/PhysRevD.76.013009">10.1103/PhysRevD.76.013009</a>'))
        )

        s = f'something something {doi} endthing'
        doiurl = urlize_dois(s)
        self.assertRegex(doiurl, r'<a href=', 'Have an A tag')
        self.assertRegex(doiurl, '^something something ')
        self.assertRegex(doiurl, ' endthing$')

        txt = '10.1103/PhysRevA.99.013009 10.1103/PhysRevZ.44.023009 10.1103/PhysRevX.90.012309 10.1103/BioRevX.44.123456'
        self.assertEqual(
            urlize_dois(txt),
            str(Markup(
                '<a href="https://dx.doi.org/10.1103/PhysRevA.99.013009">10.1103/PhysRevA.99.013009</a>'
                ' <a href="https://dx.doi.org/10.1103/PhysRevZ.44.023009">10.1103/PhysRevZ.44.023009</a>'
                ' <a href="https://dx.doi.org/10.1103/PhysRevX.90.012309">10.1103/PhysRevX.90.012309</a>'
                ' <a href="https://dx.doi.org/10.1103/BioRevX.44.123456">10.1103/BioRevX.44.123456</a>'
            ))
        )

        txt = '<script>Im from the user and Im bad</script>'
        self.assertEqual(
            urlize_dois(f'{doi} {txt}'),
            str(Markup(f'<a href="https://dx.doi.org/10.1103/PhysRevD.76.013009">10.1103/PhysRevD.76.013009</a> {escape(txt)}'))
        )

    def test_arxiv_id_urls_basic(self):
        h = 'arxiv.org'  # Totally bogus setup for testing, at least url_for returns something
        app.config['SERVER_NAME'] = h

        with app.app_context():
            self.assertEqual(urlize('', ['arxiv_id']), '')
            s = 'some text 134#%$$%&^^%*^&(()*_)_<>?:;[}}'
            self.assertEqual(urlize(s), str(escape(s)),
                             'filters should return escaped text')
            self.assertEqual(
                urlize('hep-th/9901001'),
                f'<a href="https://arxiv.org/abs/hep-th/9901001">hep-th/9901001</a>',
            )
            self.assertEqual(
                urlize('hep-th/9901001 hep-th/9901002'),
                f'<a href="https://arxiv.org/abs/hep-th/9901001">hep-th/9901001</a> <a href="https://arxiv.org/abs/hep-th/9901002">hep-th/9901002</a>'
                )

    def test_arxiv_id_urls_3(self):
        h = 'sosmooth.org'
        app.config['SERVER_NAME'] = h

        with app.app_context():
            self.assertEqual(
                urlize('hep-th/9901002'),
                f'<a href="https://arxiv.org/abs/hep-th/9901002">hep-th/9901002</a>',
            )
            self.assertEqual(
                urlize('hep-th/9901002\n'),
                f'<a href="https://arxiv.org/abs/hep-th/9901002">hep-th/9901002</a>\n'
            )
            self.assertEqual(
                urlize('arXiv:dg-ga/9401001 hep-th/9901001 hep-th/9901002'),
                f'<a href="https://arxiv.org/abs/dg-ga/9401001">arXiv:dg-ga/9401001</a> <a href="https://arxiv.org/abs/hep-th/9901001">hep-th/9901001</a> <a href="https://arxiv.org/abs/hep-th/9901002">hep-th/9901002</a>'
            )

    def test_arxiv_id_urls_punct(self):
        h = 'sosmooth.org'
        app.config['SERVER_NAME'] = h

        with app.app_context():
            self.assertEqual(
                urlize('hep-th/9901002.'),
                f'<a href="https://arxiv.org/abs/hep-th/9901002">hep-th/9901002</a>.',
                'followed by period')
            self.assertEqual(
                urlize('0702.0003.'),
                f'<a href="https://arxiv.org/abs/0702.0003">0702.0003</a>.',
                'followed by period')
            self.assertEqual(
                urlize('hep-th/9901001,hep-th/9901002'),
                f'<a href="https://arxiv.org/abs/hep-th/9901001">hep-th/9901001</a>,<a href="https://arxiv.org/abs/hep-th/9901002">hep-th/9901002</a>',
                'filter_urls_ids_escape (ID linking) 3/7')
            self.assertEqual(
                urlize('0702.0003, something'),
                f'<a href="https://arxiv.org/abs/0702.0003">0702.0003</a>, something',
                'followed by comma')
            self.assertEqual(
                urlize('(0702.0003) something'),
                f'(<a href="https://arxiv.org/abs/0702.0003">0702.0003</a>) something',
                'in parens')

    def test_arxiv_id_urls_more(self):
        h = 'sosmooth.org'
        app.config['SERVER_NAME'] = h

        with app.app_context():
            self.assertEqual(
                urlize('arXiv:dg-ga/9401001 hep-th/9901001 0704.0001'),
                f'<a href="https://arxiv.org/abs/dg-ga/9401001">arXiv:dg-ga/9401001</a> <a href="https://arxiv.org/abs/hep-th/9901001">hep-th/9901001</a> <a href="https://arxiv.org/abs/0704.0001">0704.0001</a>',
                'filter_urls_ids_escape (ID linking) 5/7')

    def test_arxiv_id_v(self):
        h = 'sosmooth.org'
        app.config['SERVER_NAME'] = h
        with app.app_context():
            self.assertEqual(
                urlize('arXiv:dg-ga/9401001v12 hep-th/9901001v2 0704.0001v1'),
                f'<a href="https://arxiv.org/abs/dg-ga/9401001v12">arXiv:dg-ga/9401001v12</a> <a href="https://arxiv.org/abs/hep-th/9901001v2">hep-th/9901001v2</a> <a href="https://arxiv.org/abs/0704.0001v1">0704.0001v1</a>',
                'arxiv ids with version numbers')

    def test_vixra(self):
        h = 'sosmooth.org'
        app.config['SERVER_NAME'] = h

        with app.app_context():
            self.assertEqual(urlize('viXra:0704.0001 viXra:1003.0123'),
                             'viXra:0704.0001 viXra:1003.0123')

            # this is what was expected in legacy, but it doesn't seem right:
            # self.assertEqual(
            #     urlize('vixra:0704.0001'),
            #     f'vixra:<a href="https://arxiv.org/abs/0704.0001">0704.0001</a>')

    def test_arxiv_id_urls_escaping(self):
        h = 'sosmooth.org'
        app.config['SERVER_NAME'] = h
        with app.app_context():
            ax_id = 'hep-th/9901002'

            user_entered_txt = ' <div>div should be escaped</div>'
            ex_txt = escape(user_entered_txt).__html__()
            self.assertEqual(
                urlize(ax_id + user_entered_txt),
                f'<a href="https://arxiv.org/abs/hep-th/9901002">hep-th/9901002</a>{ex_txt}',
                'Dealing with user entered text with html that should be escaped for safety'
            )

            jinja_escaped_txt = Markup(
                ' <div>div should already be escaped by jinja2</div>')
            self.assertEqual(
                urlize(ax_id + jinja_escaped_txt),
                f'<a href="https://arxiv.org/abs/hep-th/9901002">hep-th/9901002</a>{jinja_escaped_txt}',
                'Dealing with text that has been escaped by Jinja2 already')

    def test_arxiv_id_jinja_escapes(self):
        h = 'sosmooth.org'
        app.config['SERVER_NAME'] = h
        with app.app_context():

            jenv = Environment(autoescape=True)
            jenv.filters['urlize'] = jenv.filters['urlize'] = urlizer(
                ['arxiv_id', 'doi', 'url'], {'doi': (
                    links.doi_patterns,
                    links.doi_substituter,
                    links.url_for_doi
                )}
            )

            self.assertEqual(
                jenv.from_string(
                    '{{"something hep-th/9901002 or other"|urlize|safe}}').
                render(),
                f'something <a href="https://arxiv.org/abs/hep-th/9901002">hep-th/9901002</a> or other'
            )

            self.assertEqual(
                jenv.from_string(
                    '{{"<script>bad junk</script> something 10.1103/PhysRevD.76.013009"|urlize|safe}}'
                ).render(),
                '&lt;script&gt;bad junk&lt;/script&gt; something <a href="https://dx.doi.org/10.1103/PhysRevD.76.013009">10.1103/PhysRevD.76.013009</a>'
            )

            self.assertEqual(
                jenv.from_string(
                    '{{"<script>bad junk</script> http://google.com bla bla '
                    'hep-th/9901002 bla"|urlize|safe}}').
                render(),
                '&lt;script&gt;bad junk&lt;/script&gt; '
                '<a href="http://google.com">this http URL</a> bla bla '
                f'<a href="https://arxiv.org/abs/hep-th/9901002">hep-th/9901002</a> bla',
                'should not double escape')

    def test_line_break(self):
        self.assertEqual(line_feed_to_br('blal\n  bla'), 'blal\n<br />bla')

        self.assertEqual(line_feed_to_br('\nblal\n  bla'), '\nblal\n<br />bla')

        self.assertEqual(line_feed_to_br('\n blal\n  bla'),
                         '\n blal\n<br />bla',
                         'need to not do <br /> on first line')
        self.assertEqual(line_feed_to_br('blal\n\nbla'), 'blal\nbla',
                         'skip blank lines')

    def test_line_break_jinja(self):
        h = 'sosmooth.org'
        app.config['SERVER_NAME'] = h
        with app.app_context():
            jenv = Environment(autoescape=True)
            jenv.filters['urlize'] = urlize
            jenv.filters['line_break'] = line_feed_to_br

            self.assertEqual(
                jenv.from_string(
                    '{{"<script>bad junk</script> http://google.com something or \n'
                    '\n'
                    'no double \\n'
                    ' should have br\n'
                    'hep-th/9901002 other"|line_break|urlize|safe}}'
                ).render(),
                '&lt;script&gt;bad junk&lt;/script&gt; '
                '<a href="http://google.com">this http URL</a>'
                ' something or \n'
                'no double \n'
                '<br />should have br\n'
                '<a href="https://arxiv.org/abs/hep-th/9901002">hep-th/9901002</a> other',
                'line_break and arxiv_id_urls should work together'
            )

    def test_tex_to_utf(self):
        h = 'sosmooth.org'
        app.config['SERVER_NAME'] = h
        with app.app_context():
            jenv = Environment(autoescape=True)
            jenv.filters['urlize'] = urlize
            jenv.filters['line_break'] = line_feed_to_br
            jenv.filters['tex_to_utf'] = tex_to_utf

            self.assertEqual(
                jenv.from_string('{{""|tex_to_utf|urlize|safe}}').render(),
                ''
            )

            title = jenv.from_string(
                '{{"Finite-Size and Finite-Temperature Effects in the Conformally Invariant O(N) Vector Model for 2<d<4"|tex_to_utf|urlize|safe}}'
            ).render()
            self.assertEqual(
                title,
                'Finite-Size and Finite-Temperature Effects in the Conformally Invariant O(N) Vector Model for 2&lt;d&lt;4',
                'tex_to_utf and arxiv_id_urls should handle < and > ARXIVNG-1227'
            )

            self.assertEqual(tex_to_utf('Lu\\\'i'), 'Luí')
            self.assertEqual(tex_to_utf(Markup('Lu\\\'i')), 'Luí')
            self.assertEqual(tex_to_utf(Markup(escape('Lu\\\'i'))), 'Luí')

    def test_entity_to_utf(self):
        h = 'sosmooth.org'
        app.config['SERVER_NAME'] = h
        with app.app_context():
            jenv = Environment(autoescape=True)
            jenv.filters['entity_to_utf'] = entity_to_utf
            self.assertEqual(
                jenv.from_string('{{ "Mart&#xED;n"|entity_to_utf }}').render(),
                'Martín', 'entity_to_utf should work')
            self.assertEqual(
                jenv.from_string(
                    '{{ "<Mart&#xED;n>"|entity_to_utf }}').render(),
                '&lt;Martín&gt;',
                'entity_to_utf should work even with < or >')

    def test_arxiv_urlize_no_email_links(self):
        h = 'sosmooth.org'
        app.config['SERVER_NAME'] = h
        with app.app_context():
            jenv = Environment(autoescape=True)
            jenv.filters['urlize'] = urlize

            self.assertEqual(
                jenv.from_string('{{ "bob@example.com"|urlize|safe }}').render(),
                'bob@example.com',
                'arxiv_urlize should not turn emails into links')
            self.assertEqual(
                jenv.from_string('{{ "<bob@example.com>"|urlize|safe }}').render(),
                '&lt;bob@example.com&gt;',
                'arxiv_urlize should work even with < or >')

    def test_arxiv_urlize(self):
        h = 'sosmooth.org'
        app.config['SERVER_NAME'] = h
        with app.app_context():
            self.assertEqual(
                urlize('http://example.com/'),
                '<a href="http://example.com/">this http URL</a>',
                'urlize (URL linking) 1/6')
            self.assertEqual(
                urlize('https://example.com/'),
                '<a href="https://example.com/">this https URL</a>',
                'urlize (URL linking) 2/6')
            self.assertEqual(
                urlize('ftp://example.com/'),
                '<a href="ftp://example.com/">this ftp URL</a>',
                'urlize (URL linking) 3/6')
            self.assertEqual(
                urlize('http://example.com/.hep-th/9901001'),
                '<a href="http://example.com/.hep-th/9901001">this http URL</a>',
                'urlize (URL linking) 4/6')
            self.assertEqual(
                urlize(
                    'http://projecteuclid.org/euclid.bj/1151525136'
                ),
                '<a href="http://projecteuclid.org/euclid.bj/1151525136">this http URL</a>',
                'urlize (URL linking) 6/6')
            self.assertEqual(
                urlize('  Correction to Bernoulli (2006), 12, 551--570 http://projecteuclid.org/euclid.bj/1151525136'),
                Markup('  Correction to Bernoulli (2006), 12, 551--570 <a href="http://projecteuclid.org/euclid.bj/1151525136">this http URL</a>'),
                'urlize (URL linking) 6/6')
            # shouldn't match
            self.assertEqual(
                urlize('2448446.4710(5)'), '2448446.4710(5)',
                'urlize (should not match) 1/9')
            self.assertEqual(
                urlize('HJD=2450274.4156+/-0.0009'),
                'HJD=2450274.4156+/-0.0009',
                'urlize (should not match) 2/9')
            self.assertEqual(
                urlize('T_min[HJD]=49238.83662(14)+0.146352739(11)E.'),
                'T_min[HJD]=49238.83662(14)+0.146352739(11)E.',
                'urlize (should not match) 3/9')
            self.assertEqual(
                urlize('Pspin=1008.3408s'), 'Pspin=1008.3408s',
                'urlize (should not match) 4/9')
            self.assertEqual(
                urlize('2453527.87455^{+0.00085}_{-0.00091}'),
                '2453527.87455^{+0.00085}_{-0.00091}',
                'urlize (should not match) 5/9')
            self.assertEqual(
                urlize('2451435.4353'), '2451435.4353',
                'urlize (should not match) 6/9')
            self.assertEqual(
                urlize('cond-mat/97063007'),
                '<a href="https://arxiv.org/abs/cond-mat/9706300">cond-mat/9706300</a>7',
                'urlize (should match) 7/9')

            self.assertEqual(
                urlize('[http://onion.com/something-funny-about-arxiv-1234]'),
                '[<a href="http://onion.com/something-funny-about-arxiv-1234">this http URL</a>]')

            self.assertEqual(
                urlize('[http://onion.com/?q=something-funny-about-arxiv.1234]'),
                '[<a href="http://onion.com/?q=something-funny-about-arxiv.1234">this http URL</a>]')

            self.assertEqual(
                urlize('http://onion.com/?q=something funny'),
                '<a href="http://onion.com/?q=something">this http URL</a> funny',
                'Spaces CANNOT be expected to be part of URLs')

            self.assertEqual(
                urlize('"http://onion.com/something-funny-about-arxiv-1234"'),
                Markup('&#34;<a href="http://onion.com/something-funny-about-arxiv-1234">this http URL</a>&#34;'),
                'Should handle URL surrounded by double quotes')
