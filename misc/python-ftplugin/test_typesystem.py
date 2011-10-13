#!/usr/bin/env python

import typesystem

import ast

SOURCE_PATH = 'source_for_test.py'

with open(SOURCE_PATH) as handle:
  source = handle.read()

class TestTypeInferenceEngine(object):
  def setup_method(self, method):
    self.tie = typesystem.TypeInferenceEngine(source)

  def teardown_method(self, method):
    del self.tie

  def _iterate(self, tree):
    yield tree
    for node in tree:
      for sub_node in self._iterate(node):
        yield sub_node

  def test_iterator(self, tree=None):
    ''' Check if all items that got yielded by _iterate() are only yielded once.'''
    if tree is None:
      tree = self.tie.tree
    for node in tree:
      assert isinstance(node, typesystem.Node), '%s\'s %s \'%s\' is not a Node object.' % (type(tree), type(node), node)
      assert not hasattr(node, '_test_mark'),\
          'The following tie node has been visited more than once.\n{0}\n{1}'.format(type(node), node)
      node._test_mark = True
      self.test_iterator(node)

  def test_wrapping(self):
    ''' Check to see if all objects from the ast tree are getting wrapped.'''
    for node in ast.walk(ast.parse(source)):
      if id(type(node)) in typesystem.type_mapping:
        line = getattr(node, 'lineno', None)
        col = getattr(node, 'col_offset', None)
        if line is not None and col is not None:
          for tie_node in self._iterate(self.tie.tree):
            if tie_node.line == line and tie_node.column == col:
              node._test_mark = True
              tie_node._test_mark = True
              break
          assert hasattr(node, '_test_mark'),\
               'A {0} was not wrapped. Line: {1} Col: {2}\n{3}'.format(type(node), line, col, ast.dump(node))

