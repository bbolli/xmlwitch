from __future__ import with_statement
from StringIO import StringIO
from xml.sax.saxutils import escape, quoteattr

__all__ = ['__author__', '__license__', 'builder', 'element']
__author__ = ('Jonas Galvez', 'jonas@codeazur.com.br', 'http://jonasgalvez.com.br')
__license__ = "GPL"

# prepare the keyword unmangling dictionary
import keyword
kwunmangle = dict([(k + '_', k) for k in keyword.kwlist])
del keyword, k

def nameprep(name):
    """Undo keyword and colon mangling"""
    name = kwunmangle.get(name, name)
    return name.replace('__', ':')

class builder:
  def __init__(self, version='1.0', encoding='utf-8'):
    self._document = StringIO()
    if version and encoding:
      self._document.write('<?xml version="%s" encoding="%s"?>\n' % (version, encoding))
    self._unicode = (encoding == 'utf-8')
    self._indentation = 0
    self._indent = '  '
  def __getattr__(self, name):
    return element(name, self)
  __getitem__ = __getattr__
  def __str__(self):
    if self._unicode:
      return self._document.getvalue().encode('utf-8')
    return self._document.getvalue()
  def __unicode__(self):
    return self._document.getvalue().decode('utf-8')
  def _write(self, line):
    if self._unicode:
      line = line.decode('utf-8')
    self._document.write('%s%s\n' % (self._indentation * self._indent, line))

_dummy = {}

class element:
  def __init__(self, name, builder, outer=None):
    self.name = nameprep(name)
    self.builder = builder
    self.outer = outer
    self.serialized_attrs = ''
  def __getattr__(self, name):
    self.__enter__()
    return element(name, self.builder, self)
  def __enter__(self):
    self.builder._write('<%s%s>' % (self.name, self.serialized_attrs))
    self.builder._indentation += 1
    return self
  def __exit__(self, type, value, tb):
    if type: return False  # reraise exceptions
    self.builder._indentation -= 1
    self.builder._write('</%s>' % self.name)
    if self.outer is not None:
      self.outer.__exit__(None, None, None)
  def __call__(self, _value=_dummy, **kargs):
    self.serialized_attrs = self.serialize_attrs(kargs)
    if _value is None:
      self.builder._write('<%s%s />' % (self.name, self.serialized_attrs))
    elif _value is not _dummy:
      self.builder._write('<%s%s>%s</%s>' % (self.name, self.serialized_attrs, escape(_value), self.name))
      return
    return self
  def serialize_attrs(self, attrs):
    return ''.join([
        ' %s=%s' % (nameprep(attr), quoteattr(value))
        for attr, value in attrs.items()
    ])
  def text(self, value):
    self.builder._write(escape(value))

if __name__ == "__main__":
  xml = builder()
  with xml.feed(xmlns='http://www.w3.org/2005/Atom'):
    xml.title('Example Feed')
    xml.link(None, href='http://example.org/')
    xml.updated('2003-12-13T18:30:02Z')
    with xml.author:
      xml.name('John Doe')
    xml.id('urn:uuid:60a76c80-d399-11d9-b93C-0003939e0af6')
    with xml.entry:
      xml.my__elem("Hello these are namespaces!", xmlns__my='http://example.org/ns/', my__attr='what?')
      xml.quoting("< > & ' \"", attr="< > & ' \"")
      xml.title('Atom-Powered Robots Run Amok')
      xml.link(None, href='http://example.org/2003/12/13/atom03')
      xml.id('urn:uuid:1225c695-cfb8-4ebb-aaaa-80da344efa6a')
      xml.updated('2003-12-13T18:30:02Z')
      xml.summary('Some text.')
      with xml.content(type='xhtml').div(xmlns='http://www.w3.org/1999/xhtml') as div:
        xml.label('Some label', for_='some_field')
        div.text(':')
        xml.input(None, type='text', value='')
  print xml
