#!/usr/bin/env python

import ast
from textwrap import dedent
from typesystem import *

SOURCE_PATH = 'source_for_test.py'

with open(SOURCE_PATH) as handle:
  SOURCE_TEXT = handle.read()
  EXAMPLE_TREE = parse(SOURCE_TEXT)

def test_iterator(tree=None):
  ''' Check if all items that got yielded by __iter__() are only yielded once.'''
  if tree is None:
    tree = EXAMPLE_TREE
  for node in tree:
    print "Marking", type(node), "with id", id(node), ".."
    assert isinstance(node, Node), '%s\'s %s %r is not a Node object.' % (type(tree), type(node), node)
    assert not hasattr(node, '_test_mark'),\
        'The following tree node has been visited more than once.\n{0}\n{1}'.format(type(node), node)
    node._test_mark = True
    test_iterator(node)

def test_wrapping():
  ''' Check to see if all objects from the ast tree are getting wrapped.'''
  for i, node in enumerate(ast.walk(ast.parse(SOURCE_TEXT))):
    if id(type(node)) in type_mapping:
      line = getattr(node, 'lineno', None)
      col = getattr(node, 'col_offset', None)
      if line is not None and col is not None:
        print "Looking for node", i, ".."
        for tie_node in EXAMPLE_TREE.walk():
          if tie_node.line == line and tie_node.column == col:
            node._test_mark = True
            tie_node._test_mark = True
            break
        assert hasattr(node, '_test_mark'),\
             'A {0} was not wrapped. Line: {1} Col: {2}\n{3}'.format(type(node), line, col, ast.dump(node))

def test_string_literal_completion():
  root = parse("''")
  node = root.locate(1, 0)
  assert isinstance(node, Str)
  assert 'capitalize' in node.attrs

def test_dictionary_completion():
  root = parse("{}")
  node = root.locate(1, 0)
  assert isinstance(node, Dictionary)
  assert 'keys' in node.attrs
  node = root.locate(1, 2)
  assert isinstance(node, Dictionary)
  assert 'keys' in node.attrs

def test_follow_assignments():
  root = parse(dedent('''
    module_var = []
    module_var
    var1, var2 = 1, ''
    def func():
      module_var
      var1
      var2
  ''').strip())
  node = root.locate(2, 3)
  assert isinstance(node, Name)
  print list(node.sources)
  assert 'append' in node.attrs
  node = root.locate(5, 3)
  assert isinstance(node, Name)
  assert 'append' in node.attrs
  node = root.locate(6, 3)
  assert isinstance(node, Name)
  assert 'imag' in node.attrs
  node = root.locate(7, 3)
  assert isinstance(node, Name)
  assert 'capitalize' in node.attrs

def est_follow_tuple_unpacking():
  root = parse(dedent('''
    var1, var2 = 2, []
    var1
    var2
    ''').strip())

  node1 = root.locate

def test_completion_of_user_defined_classes():

  root = parse(dedent('''
    class ExampleClass:
      class_attr = 42
      def __init__(self):
        self.dynamic_attr = []
        self
  ''').strip())

  node = root.locate(1, 7)
  assert isinstance(node, ClassDef)
  assert len(node.attrs) == 3
  assert 'class_attr' in node.attrs
  assert '__init__' in node.attrs
  assert 'dynamic_attr' in node.attrs

  node2 = root.locate(5, 5)
  assert isinstance(node2, Name)
  assert len(node2.attrs) == 3
  assert 'class_attr' in node2.attrs
  assert '__init__' in node2.attrs
  assert 'dynamic_attr' in node2.attrs

def test_attribute_path():
  root = parse('foo.bar.baz.bla.he.ho')
  node = root.locate(1, 10)
  assert isinstance(node, Name)
  print 'Name node.path gave:', node.path
  assert node.path == ['bar', 'baz', 'bla', 'he', 'ho']
  node = node.parent.parent.parent.parent
  print 'Attribute node.path gave:', node.path
  assert node.path == ['he', 'bla', 'baz', 'bar', 'foo']

def test_import_follow():
  source = dedent('''
    import mpd
    mpd
    mpd.MPDClient

    import xmllib
    xmllib.string

    xmllib
    mpd
    import ast as tree
    tree
    from logging import handlers
    handlers
    from logging.config import DictConfigurator
    DictConfigurator
  ''').strip()
  root = parse(source)
  # Test modulelevel completion.
  node = root.locate(2, 3)
  assert isinstance(node, Name)
  assert 'MPDClient' in node.attrs
  # Test completion from class in module
  node = root.locate(3, 6)
  assert isinstance(node, Name)
  assert 'mpd_version' in node.attrs
  # Test recursive module following.
  node = root.locate(6, 12)
  assert isinstance(node, Name)
  assert 'ascii_letters' in node.attrs
  node = root.locate(8, 6)
  assert isinstance(node, Name)
  assert 'attrfind' in node.attrs
  node = root.locate(9, 3)
  assert isinstance(node, Name)
  assert 'MPDClient' in node.attrs
  # Test import as.
  node = root.locate(11, 8)
  assert isinstance(node, Name)
  assert 'parse' in node.attrs
  assert 'walk' in node.attrs
  # Test import from package.
  node = root.locate(13, 8)
  assert isinstance(node, Name)
  assert 'HTTPHandler' in node.attrs
  assert 'MemoryHandler' in node.attrs
  # Test import from dotted module name while importing an attribute from the module.
  node = root.locate(15, 9)
  assert isinstance(node, Name)
  print node.attrs
  assert 'add_filters' in node.attrs
  # Test following of base classes.
  assert 'as_tuple' in node.attrs
