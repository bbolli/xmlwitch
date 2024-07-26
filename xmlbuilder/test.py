import sys

from . import XMLBuilder, HTMLBuilder, Safe

xml = XMLBuilder(stream=sys.stdout)
with xml.feed(xmlns='http://www.w3.org/2005/Atom'):
    xml.title('Example Feed')
    # None is required for empty elements
    xml.link(None, href='http://example.org/')
    xml.updated('2003-12-13T18:30:02Z')
    with xml.author:
        xml.name('John Doe').email('jd@example.org')
    xml.id('urn:uuid:60a76c80-d399-11d9-b93C-0003939e0af6')
    with xml.entry:
        xml.my__elem("Hello these are namespaces!", xmlns__my='http://example.org/ns/', my__attr='what?')
        xml.quoting("< > & ' \"", attr="< > & ' \"")
        xml.safe(Safe("<em> &amp; </em> ' \""), attr=Safe("'&lt; &gt; &amp;'"))
        xml.str("¡Thìs ïs å tést!", attr='“—”')
        xml.title('Atom-Powered Robots Run Amok')
        xml.link(None, href='http://example.org/2003/12/13/atom03')
        xml.id('urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a')
        xml.updated('2003-12-13T18:30:02Z', utc=True, local=False)
        xml.summary('Some text.')
        with xml.content(type='xhtml'):
            with xml.div(xmlns='http://www.w3.org/1999/xhtml'):
                xml.label('Some label', for_='some_field', _post=':')
                xml.input(None, type='text', value='', id='some_field')

xml = XMLBuilder(encoding='iso-8859-1')
xml.tag('€')
assert '€' in str(xml)
assert b'&#8364;' in bytes(xml)

print()
html = HTMLBuilder()
with html.html(lang='en'):
    html.p('p1', class_='c1 c2')
    html.br(_pre="<br> next:")
    with html.p(class_='c3'):
        html.label('Some label', for_='some_field', _post=':')
        html.input(type='text', value='', id='some_field', disabled=True, hidden='hidden', max_length='10')
actual = str(html)
print(actual)
assert '<p class="c1 c2">p1</p>' in actual
assert '&lt;br&gt; next:<br>' in actual
assert '<p class=c3>' in actual
assert ' disabled hidden ' in actual
