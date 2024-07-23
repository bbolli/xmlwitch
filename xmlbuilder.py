from types import TracebackType
import typing as t
from xml.sax.saxutils import escape, quoteattr

__all__ = ['__author__', '__license__', 'Builder', 'XMLBuilder', 'HTMLBuilder', 'Safe', 'Element']
__author__ = ('Beat Bolli', 'me+python@drbeat.li', 'https://drbeat.li/py/')
__license__ = "GPL3+"

# prepare the keyword unmangling dictionary
import keyword
kwunmangle = {k + '_': k for k in keyword.kwlist}
del keyword


def nameprep(name: str) -> str:
    """Undo keyword and colon mangling"""
    name = kwunmangle.get(name, name)
    return name.replace('__', ':')


class Safe(str):
    """A class that holds "safe" content that is not escaped when used"""
    pass


def safevalue(value: str) -> Safe:
    """Escape unsafe values as HTML content"""
    return value if isinstance(value, Safe) else t.cast(Safe, escape(value))


def safeattr(value: str) -> Safe:
    """Escape unsafe attribute values.
    Safe values must include the enclosing quotes, if needed."""
    return value if isinstance(value, Safe) else t.cast(Safe, quoteattr(value))


class XMLBuilder:
    """The "document" class for generating XML content.

    It supports different accessors to generate content:

    XMLBuilder.element returns a new Element with its own accessors.

    XMLBuilder[content] emits content.
    """

    _end_empty_tag = '/>'
    _empty_tags: set[str] = set()

    _document: list[str]
    _encoding: str
    _indentation: int
    _indent: str | None
    __write: t.Any  # doesn't work: t.Callable[[str], t.Any]

    def __init__(self, version: str = '1.0', encoding: str = 'utf-8',
                 indent: str | None = '  ', stream: t.TextIO | None = None) -> None:
        """Initialize a new XML document. The XML header is only written if both
        `version` and `encoding` are not empty.
        `indent` can be None to output everything on one line, the empty string to
        output multiple lines without indentation, or a whitespace string that is repeated
        for each indentation level.
        If a `stream` is passed, content is output directly to the stream, and __str__()
        will return an empty string.
        """
        self._document = ['']
        self._encoding = encoding
        self._indentation = 0
        self._indent = indent
        self.__write = stream.write if stream else self._document.append
        if version and encoding:
            self._write(f'<?xml version="{version}" encoding="{encoding}"?>')

    def __getattr__(self, name: str) -> 'Element':
        """Return a new element with tag `name`. If `name` is a Python keyword, append
        an underline character '_'. If `name` should contain a colon ':', use two
        underlines '__' instead."""
        return Element(name, self)

    def __getitem__(self, value: str) -> 'XMLBuilder':
        """Output `value` as content."""
        self._write(safevalue(value))
        return self

    def __str__(self) -> str:
        """Return the document so far, unless a stream was passed to __init__()"""
        return ''.join(self._document)

    def __bytes__(self) -> bytes:
        """Return the document so far as bytes in the desired encoding, with
        non-representable entities replaced by their character references."""
        return str(self).encode(self._encoding, 'xmlcharrefreplace')

    def _attr(self, attr: str, value: str | bool) -> Safe:
        """Handle the quoting of one attribute and its value. True values are
        written as `attr="attr"`, False values suppress the whole attribute."""
        if isinstance(value, bool):
            if not value:
                return Safe('')
            value = attr
        return Safe(nameprep(attr) + '=' + safeattr(value))

    def _write(self, line: str, indent: int = 0) -> None:
        """Write a new line of the document. Indentation can be adjusted."""
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
    # see https://developer.mozilla.org/en-US/docs/Glossary/Void_element
    _empty_tags = set('area base br col embed hr img input link meta source track wbr'.split())

    def __init__(self, encoding: str = 'utf-8', indent: str | None = '  ',
                 stream: t.TextIO | None = None) -> None:
        """Initialize a new HTML document. The HTML header is only written if
        `encoding` is not empty.
        `indent` can be None to output everything on one line, the empty string to
        output multiple lines without indentation, or a whitespace string that is repeated
        for each indentation level.
        If a `stream` is passed, content is output directly to the stream, and __str__()
        will return an empty string.
        """
        super().__init__(version='', encoding=encoding, indent=indent, stream=stream)
        if encoding:
            self._write('<!DOCTYPE html>')
            self.meta(charset=encoding)

    def _attr(self, attr: str, value: str | bool) -> Safe:
        """Handle one attribute and its value.
        `True` values and values that match the attribute name are written in
        "empty attribute syntax", i.e. just the attribute name; `False` values are suppressed.
        Values that don't need to be quoted are written as-is."""
        if isinstance(value, bool) and value or attr == value:
            return Safe(nameprep(attr))
        # https://dev.w3.org/html5/spec-LC/syntax.html#attributes-0
        if not value or any(c in value for c in ' "\'=<>`'):
            return super()._attr(attr, value)
        return Safe(f'{nameprep(attr)}={value}')


class Element:

    class Empty:
        pass

    _empty = Empty()

    _name: str
    _builder: XMLBuilder
    _attrs: str

    def __init__(self, name: str, builder: XMLBuilder) -> None:
        """Initialize a new Element."""
        self._name = nameprep(name)
        self._builder = builder
        self._attrs = ''

    def __getattr__(self, name: str) -> 'Element':
        """Return a new subelement of this Element with tag `name`."""
        return Element(name, self._builder)

    def __enter__(self) -> 'Element':
        """Open this Element. On exit from the context manager, it will be closed."""
        self._builder._write(f'<{self._name}{self._attrs}>', +1)
        return self

    def __exit__(self, typ: t.Type[BaseException] | None,
                 val: BaseException | None, tb: TracebackType | None) -> bool:
        if typ:
            return False  # reraise exceptions
        self._builder._write(f'</{self._name}>', -1)
        return True

    def __call__(self, _value: str | Empty | None = _empty, /,
                 _pre: str = '', _post: str = '', **attrs: str | bool | None) -> 'Element':
        """Output this Element, optionally with content.
        If `_value` is a string, it becomes the content. If it is None, an empty tag is produced.
        If it is `_empty`, nothing at all is output. This is mainly used with `__enter__()`.
        `_pre` and `_post` is content that is prefixed or postfixed to the element without intervening whitespace.
        Other keyword arguments become attributes of the element.
        """
        self._attrs = ''.join(
            ' ' + self._builder._attr(attr, value)
            for attr, value in attrs.items() if value is not None and value is not False
        )
        if self._attrs.endswith('/'):
            self._attrs += ' '
        if _value is None or self._name in self._builder._empty_tags:
            var = self._builder._end_empty_tag
        elif not isinstance(_value, self.Empty):
            var = f'>{safevalue(_value)}</{self._name}>'
        else:
            return self
        self._builder._write(f'{safevalue(_pre)}<{self._name}{self._attrs}{var}{safevalue(_post)}')
        return self

    def __getitem__(self, value: str) -> 'Element':
        """Output `value` as text content."""
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
            xml.safe(Safe("<em> &amp; </em> ' \""), attr=Safe("'&lt; &gt; &amp;'"))
            xml.str("¡Thìs ïs å tést!", attr='“—”')
            xml.title('Atom-Powered Robots Run Amok')
            xml.link(None, href='http://example.org/2003/12/13/atom03')
            xml.id('urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a')
            xml.updated('2003-12-13T18:30:02Z', utc=True, local=False)
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
