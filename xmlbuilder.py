from xml.sax.saxutils import escape, quoteattr

__all__ = ['__author__', '__license__', 'Builder', 'Safe', 'Element']
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


def safevalue(value):
    return value.content if isinstance(value, Safe) else escape(value)


class Builder:

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
        self._write(escape(value))

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


class Safe:

    def __init__(self, v):
        self.content = v.content if isinstance(v, Safe) else v

    def apply(self, fn):
        self.content = fn(self.content)
        return self


class Element:
    _empty = object()

    def __init__(self, name, builder):
        self._name = nameprep(name)
        self._builder = builder
        self._serialized_attrs = ''

    def __getattr__(self, name):
        return Element(name, self._builder)

    def __enter__(self):
        self._builder._write(f'<{self._name}{self._serialized_attrs}>', +1)
        return self

    def __exit__(self, typ, value, tb):
        if typ:
            return False  # reraise exceptions
        self._builder._write(f'</{self._name}>', -1)

    def __call__(self, _value=_empty, **attrs):
        self._serialized_attrs = ''.join(
            f' {nameprep(attr)}={quoteattr(value)}'
            for attr, value in attrs.items() if value is not None
        )
        if _value is None:
            self._builder._write(f'<{self._name}{self._serialized_attrs}/>')
        elif _value is not self._empty:
            self._builder._write(f'<{self._name}{self._serialized_attrs}>{safevalue(_value)}</{self._name}>')
        return self

    def __getitem__(self, value):
        self._builder._write(safevalue(value))
        return self


if __name__ == "__main__":
    import sys
    xml = Builder(stream=sys.stdout)
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
            xml.quoting(Safe("<em> &amp; </em> ' \""), attr="< > & ' \"")
            xml.str("¡Thìs ïs å tést!", attr='“—”')
            xml.title('Atom-Powered Robots Run Amok')
            xml.link(None, href='http://example.org/2003/12/13/atom03')
            xml.id('urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a')
            xml.updated('2003-12-13T18:30:02Z')
            xml.summary('Some text.')
            with xml.content(type='xhtml').div(xmlns='http://www.w3.org/1999/xhtml'):
                xml.label('Some label', for_='some_field')[':'].input(None, type='text', value='')
