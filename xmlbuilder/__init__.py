"""xmlbuilder is a BSD-licensed, Python 3.10+ library that offers \
idiomatic XML and HTML5 generation through context managers."""

from __future__ import annotations
import re
from types import TracebackType
import typing as t
from xml.sax.saxutils import escape, quoteattr

__version__ = '1.0'
__all__ = ['Builder', 'XMLBuilder', 'HTMLBuilder', 'Safe', 'Element']

# prepare the keyword unmangling dictionary
import keyword
kwunmangle = {k + '_': k for k in keyword.kwlist}
del keyword


def nameprep(name: str) -> str:
    """Undo keyword and colon mangling."""
    name = kwunmangle.get(name, name)
    return name.replace('__', ':')


class Safe(str):
    """A class that holds "safe" content that is not escaped when used."""

    @classmethod
    def text(cls, value: str) -> t.Self:
        """Escape text to make it safe."""
        return cls(escape(value))

    @classmethod
    def attr(cls, value: str) -> t.Self:
        """Escape an attribute value to make it safe."""
        return cls(quoteattr(value))


def safetext(value: str) -> Safe:
    """Escape unsafe values as HTML content"""
    return value if isinstance(value, Safe) else Safe.text(value)


def safeattr(value: str) -> Safe:
    """Escape unsafe attribute values.
    Safe values must include the enclosing quotes, if needed."""
    return value if isinstance(value, Safe) else Safe.attr(value)


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
                 indent: str | None = '  ', stream: t.TextIO | None = None,
                 empty_tags: t.Iterable | None = None) -> None:
        """Initialize a new XML document. The XML header is only written if both
        `version` and `encoding` are not empty.
        `indent` can be None to output everything on one line, the empty string to
        output multiple lines without indentation, or a whitespace string that is repeated
        for each indentation level.
        If a `stream` is passed, content is output directly to the stream, and __str__()
        will return an empty string.
        `empty_tags` is a sequence of "void elements" that have no content.
        """
        self._document = ['']
        self._encoding = encoding
        self._indentation = 0
        self._indent = indent
        if empty_tags is not None:
            self._empty_tags = set(empty_tags)
        self.__write = stream.write if stream else self._document.append
        if version and encoding:
            self._write(f'<?xml version="{version}" encoding="{encoding}"?>')

    def __getattr__(self, name: str) -> Element:
        """Return a new element with tag `name`. If `name` is a Python keyword, append
        an underline character '_'. Note that `hash`, `id` and `type` are not keywords,
        but predefined functions. If `name` needs to contain a colon ':', use two
        underlines `__` instead."""
        return Element(name, self)

    def __getitem__(self, value: str) -> t.Self:
        """Output `value` as content."""
        self._write(safetext(value))
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
        written as `attr="attr"`, `False` and `None` values suppress the whole attribute."""
        if value is True:
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
    # see https://dev.w3.org/html5/spec-LC/syntax.html#attributes-0
    _attr_quote = re.compile('[ "\'=<>`]')

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
        Values that are `True` or that match the attribute name are written in
        "empty attribute syntax", i.e. just the attribute name; `False` and `None` values
        suppress the whole attribute. The value is put between quotes only if necessary."""
        if value is True or attr == value:
            return Safe(nameprep(attr))
        if not value or self._attr_quote.search(value):
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

    def __getattr__(self, name: str) -> t.Self:
        """Return a new subelement of this Element with tag `name`."""
        return self.__class__(name, self._builder)

    def __enter__(self) -> t.Self:
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
                 _pre: str = '', _post: str = '', **attrs: str | bool | None) -> t.Self:
        """Output this Element, optionally with content.
        If `_value` is a string, it becomes the content. If it is None, an empty tag is produced.
        If it is `_empty`, nothing at all is output. This is mainly used with `__enter__()`.
        `_pre` and `_post` is content that is prefixed or postfixed to the element without
        intervening whitespace. Other keyword arguments become attributes of the element.
        """
        self._attrs = ''.join(
            ' ' + self._builder._attr(attr, value)
            for attr, value in attrs.items() if value not in (None, False)
        )
        if self._attrs.endswith('/'):
            self._attrs += ' '
        if _value is None or self._name in self._builder._empty_tags:
            var = self._builder._end_empty_tag
        elif not isinstance(_value, self.Empty):
            var = f'>{safetext(_value)}</{self._name}>'
        else:
            return self
        self._builder._write(f'{safetext(_pre)}<{self._name}{self._attrs}{var}{safetext(_post)}')
        return self

    def __getitem__(self, value: str) -> t.Self:
        """Output `value` as text content."""
        self._builder._write(safetext(value))
        return self
