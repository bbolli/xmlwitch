from xml.sax.saxutils import escape, quoteattr

__all__ = ['__author__', '__license__', 'Builder', 'XMLBuilder', 'HTMLBuilder', 'Safe', 'Element']
__author__ = ('Beat Bolli', 'me+python@drbeat.li', 'https://drbeat.li/py/')
__license__ = "GPL3+"

# prepare the keyword unmangling dictionary
import keyword
kwunmangle = dict((k + '_', k) for k in keyword.kwlist)
del keyword


def nameprep(name):
    """Undo keyword and colon mangling"""
    name = kwunmangle.get(name, name)
    return name.replace('__', ':')


class Safe(str):
    pass


def safevalue(value):
    return value if isinstance(value, Safe) else escape(value)


def safeattr(value):
    return f'"{value}"' if isinstance(value, Safe) else quoteattr(value)


class XMLBuilder:

    _end_empty_tag = '/>'

    def __init__(self, version='1.0', encoding='utf-8', indent='  ', stream=None):
        self._document = ['']
        self._encoding = encoding
        self._indentation = 0
        self._indent = indent
        self.__write = stream.write if stream else self._document.append
        if version and encoding:
            self._write(f'<?xml version="{version}" encoding="{encoding}"?>')

    def __getattr__(self, name):
        return Element(name, self)

    def __getitem__(self, value):
        self._write(safevalue(value))
        return self

    def __str__(self):
        return ''.join(self._document)

    def __bytes__(self):
        return str(self).encode(self._encoding, 'xmlcharrefreplace')

    def _write(self, line, indent=0):
        if indent < 0:
            self._indentation += indent
        if self._indent is not None:
            line = self._indentation * self._indent + line + '\n'
        self.__write(line)
        if indent > 0:
            self._indentation += indent


Builder = XMLBuilder  # backwards compatibility


class HTMLBuilder(XMLBuilder):

    _end_empty_tag = '>'

    def __init__(self, encoding='utf-8', indent='  ', stream=None):
        super().__init__(version=None, encoding=encoding, indent=indent, stream=stream)
        if encoding:
            self._write('<!DOCTYPE html>')
            self.meta(None, charset=encoding)


class Element:
    _empty = object()

    def __init__(self, name, builder):
        self._name = nameprep(name)
        self._builder = builder
        self._attrs = ''

    def __getattr__(self, name):
        return Element(name, self._builder)

    def __enter__(self):
        self._builder._write(f'<{self._name}{self._attrs}>', +1)
        return self

    def __exit__(self, typ, value, tb):
        if typ:
            return False  # reraise exceptions
        self._builder._write(f'</{self._name}>', -1)

    def __call__(self, _value=_empty, _pre='', _post='', **attrs):
        self._attrs = ''.join(
            f' {nameprep(attr)}={safeattr(value)}'
            for attr, value in attrs.items() if value is not None
        )
        if _value is None:
            self._builder._write(f'{safevalue(_pre)}<{self._name}{self._attrs}{self._builder._end_empty_tag}{safevalue(_post)}')
        elif _value is not self._empty:
            self._builder._write(f'{safevalue(_pre)}<{self._name}{self._attrs}>{safevalue(_value)}</{self._name}>{safevalue(_post)}')
        return self

    def __getitem__(self, value):
        self._builder._write(safevalue(value))
        return self


if __name__ == "__main__":
    import sys
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
            xml.safe(Safe("<em> &amp; </em> ' \""), attr=Safe("&lt; &gt; &amp; '"))
            xml.str("¡Thìs ïs å tést!", attr='“—”')
            xml.title('Atom-Powered Robots Run Amok')
            xml.link(None, href='http://example.org/2003/12/13/atom03')
            xml.id('urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a')
            xml.updated('2003-12-13T18:30:02Z')
            xml.summary('Some text.')
            with xml.content(type='xhtml').div(xmlns='http://www.w3.org/1999/xhtml'):
                xml.label('Some label', for_='some_field', _post=':').input(None, type='text', value='', id='some_field')

    xml = XMLBuilder(encoding='iso-8859-1')
    xml.tag('€')
    assert '€' in str(xml)
    assert b'&#8364;' in bytes(xml)

    print()
    html = HTMLBuilder()
    with html.html(lang='en'):
        html.p('p1')
        html.br(None, _pre="<br> next:")
        html.p('p2')
    actual = str(html)
    assert '<p>p1</p>' in actual
    assert '&lt;br&gt; next:<br>' in actual
    assert '<p>p2</p>' in actual
    print(actual)
