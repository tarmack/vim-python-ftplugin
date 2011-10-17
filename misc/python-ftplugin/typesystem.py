'''
Custom type hierarchy wrapping the Python AST

Authors:
 - Peter Odding <peter@peterodding.com>
 - Bart Kroon <bart@tarmack.eu>
Last Change: October 15, 2011
URL: https://github.com/tarmack/vim-python-ftplugin

The type inference engine is turning into a royal mess because we get these
huge if/elif/else chains that switch on AST types. I was thinking maybe it
would be better to divide such blocks over methods in a type hierarchy of our
own, to hide the uncomfortable parts of the Python AST. The problem is that
we have to write a lot of boilerplate code and the runtime end result will be a
bit wasteful because we're wrapping the full abstract syntax tree.

This is a work in progress, not integrated into the Vim plug-in yet.
'''

# TODO (Ab)use scope awareness to complete variables valid in scope?
# TODO Decorators are missing from the pretty printed output.

import ast
import sys
import os
import numbers
import collections

type_mapping = {}

def wraps(*ast_types):
  '''
  Class decorator used to initialize the dictionary mapping
  between the ast.* classes and our own type hierarchy.
  '''
  def decorator(cls):
    for ast_type in ast_types:
        type_mapping[id(ast_type)] = cls
    return cls
  return decorator

def log(msg, *args):
  '''
  When the type inference engine is used to suggest completion candidates we
  use "print" to return the candidates to Vim. This means we cannot write
  logging messages using "print", instead the messages should go to a file.
  '''
  print msg % args

class Node(object):

  '''
  Abstract root class for our type hierarchy of AST nodes.
  '''

  def __init__(self, node, parent):
    self.parent = parent
    self.column = getattr(node, 'col_offset', 0)
    self.line = getattr(node, 'lineno', 0)

  def __iter__(self):
    '''
    Iterate over the direct child nodes of the current node.
    '''
    return iter(())

  @property
  def statements(self):
    '''
    Iterate over the direct child statements of the current node.
    '''
    for node in self:
      if isinstance(node, Statement):
        yield node

  @property
  def expressions(self):
    '''
    Iterate over the direct child expressions of the current node.
    '''
    for node in self:
      if isinstance(node, Expression):
        yield node

  def walk(self, match=(), exclude=(), one_scope=False):
    '''
    Recursively walk the child nodes of the current node. If {types} is given
    only nodes of the given types are returned.
    '''
    if one_scope:
      exclude = (Module, ClassDef, FunctionDef, Lambda)
    if not match or isinstance(self, match):
      yield self
    for node in self:
      if exclude and isinstance(node, exclude):
        yield node
      else:
        for child in node.walk(match, exclude, one_scope):
          yield child

  def locate(self, line, column):
    '''
    Find the node at the given (line, column) in the AST.
    '''
    last_node = None
    for node in self.walk():
      if node.line > line or (node.line == line and node.column > column):
        if not last_node:
          last_node = node
        break
      last_node = node
    return last_node

  @property
  def tree(self):
    '''
    Find the root node of the AST.
    '''
    return self._find_parent()

  @property
  def containing_class(self):
    '''
    Find the innermost class definition that contains the current node.
    '''
    return self._find_parent(ClassDef)

  @property
  def containing_scope(self):
    '''
    Find the innermost module/class that contains the current node.
    '''
    return self._find_parent(Module, ClassDef, FunctionDef, Lambda)

  @property
  def containing_function(self):
    '''
    Find the innermost function definition that contains the current node.
    '''
    return self._find_parent(FunctionDef)

  @property
  def containing_module(self):
    '''
    Find the module that contains the current node.
    '''
    return self._find_parent(Module)

  def _find_parent(self, *types):
    '''
    Internal method that recurses upwards to find parents of the given type(s).
    If no types are given it recurses all the way up to the root of the AST.
    '''
    if self.parent is None:
      return self
    elif isinstance(self.parent, types):
      return self.parent
    else:
      return self.parent._find_parent(*types)

class Statement(Node):
  '''
  Abstract root class for all statement node types.
  '''
  pass

class Expression(Node):
  '''
  Abstract root class for all expression node types.
  '''
  pass

class LiteralValue(Expression):

  '''
  Abstract class for literal values in the parse tree.
  '''

  @property
  def type_name(self):
    return self.python_type.__name__

  @property
  def attrs(self):
    return dir(self.python_type)

@wraps(ast.Expr)
class Expr(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.value = wrap(node.value, self)

  @property
  def attrs(self):
    return self.value.attrs

  def __iter__(self):
    yield self.value

  def __str__(self):
    return str(self.value)

@wraps(ast.Module)
class Module(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.body = wrap(node.body, self)

  @property
  def attrs(self):
    result = []
    for node in self.walk((ClassDef, FunctionDef, Assign, Alias), one_scope=True):
      if isinstance(node, (ClassDef, FunctionDef)):
        result.append(node.name)
      elif isinstance(node, Assign):
        result.extend([name.value for name in flatten(node.targets)])
      elif isinstance(node, Alias):
        result.append(node.asname or node.name)
    return result

  def __iter__(self):
    return iter(self.body)

  def __str__(self):
    return 'module:\n' + indent(self.body)

@wraps(ast.ClassDef)
class ClassDef(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.decorator_list = wrap(node.decorator_list, self)
    self.name = node.name
    self.bases = wrap(node.bases)
    self.body = wrap(node.body, self)

  @property
  def attrs(self):
    # TODO Also check the base classes! And maybe decorators?!
    results = set()
    for node in self:
      if isinstance(node, FunctionDef):
        # Name of class/instance method.
        results.add(node.name)
        # Names of attributes in method that receive assignments.
        for child in node.walk(Assign):
          for n in flatten(child.targets):
            if isinstance(n, Attribute) and n.value.value == 'self':
              results.add(n.attr)
      elif isinstance(node, Assign):
        # Class/instance attribute(s).
        results.update(t.value for t in node.targets)
    return results

  def __iter__(self):
    return iter(self.decorator_list + self.bases + self.body)

  def __str__(self):
    text = 'class %s' % self.name
    if self.bases:
      text += '(%s)' % ', '.join(str(b) for b in self.bases)
    return text + ':\n%s' % indent(self.body)

@wraps(ast.FunctionDef)
class FunctionDef(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.name = node.name
    self.decorator_list = wrap(node.decorator_list, self)
    self.args = wrap(node.args.args, self)
    self.defaults = wrap(node.args.defaults, self)
    self.vararg = node.args.vararg
    self.kwarg = node.args.kwarg
    self.body = wrap(node.body, self)

  @property
  def attrs(self):
    results = []
    for obj in self.body:
      if isinstance(obj, Return):
        results.extend(obj.attrs)
    return results

  def __iter__(self):
    return iter(self.decorator_list + self.args + self.defaults + self.body)

  def __str__(self):
    args = []
    args.extend(self.args)
    args.extend(self.defaults)
    if self.vararg:
      args.append('*' + str(self.vararg))
    if self.kwarg:
      args.append('**' + str(self.kwarg))
    return 'def %s(%s):\n%s' % (
        self.name,
        ', '.join(str(a) for a in args),
        indent(self.body))

@wraps(ast.Import, ast.ImportFrom)
class Import(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.module = getattr(node, 'module', None)
    self.names = wrap(node.names, self)

  def __iter__(self):
    return iter(self.names)

  def __str__(self):
    text = ''
    if self.module:
      text += "from "+self.module+" "
    text +=  'import ' + ', '.join(str(n) for n in self.names)
    return text

@wraps(ast.alias)
class Alias(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.name = node.name
    self.asname = node.asname

  @property
  def module(self):
    module_name = self.parent.module or self.name
    module_path = module_name.replace('.', '/')
    for root in sys.path:
      path = '%s/%s.py' % (root, module_path)
      if os.path.isfile(path):
        with open(path) as handle:
          return parse(handle.read())

  @property
  def attrs(self):
    return self.module.attrs

  def __str__(self):
    text = str(self.name)
    if self.asname:
      text += ' as ' + str(self.asname)
    return text

@wraps(ast.If)
class If(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.test = wrap(node.test, self)
    self.body = wrap(node.body, self)
    self.orelse = wrap(node.orelse, self)

  def __iter__(self):
    return iter([self.test] + self.body + self.orelse)

  def __str__(self):
    lines = ['if %s:' % self.test]
    lines.append(indent(self.body))
    if self.orelse:
      lines.append('else:')
      lines.append(indent(self.orelse))
    return '\n'.join(lines)

@wraps(ast.For)
class For(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.target = wrap(node.target, self)
    self.iter = wrap(node.iter, self)
    self.body = wrap(node.body, self)
    self.orelse = wrap(node.orelse, self)

  def __iter__(self):
    return iter([self.target, self.iter] + self.body + self.orelse)

  def __str__(self):
    lines = ['for %s in %s:' % (self.target, self.iter)]
    lines.append(indent(self.body))
    if self.orelse:
      lines.append('else:')
      lines.append(indent(self.body))
    return '\n'.join(lines)

@wraps(ast.While)
class While(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.test = wrap(node.test, self)
    self.body = wrap(node.body, self)
    self.orelse = wrap(node.orelse, self)

  def __iter__(self):
    return iter([self.test] + self.body + self.orelse)

  def __str__(self):
    lines = ['while %s:' % self.test]
    lines.append(indent(self.body))
    if self.orelse:
      lines.append('else:')
      lines.append(indent(self.orelse))
    return '\n'.join(lines)

@wraps(ast.Print)
class Print(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.values = wrap(node.values, self)

  def __iter__(self):
    return iter(self.values)

  def __str__(self):
    return 'print %s' % ', '.join(str(v) for v in self.values)

@wraps(ast.Return)
class Return(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.value = wrap(node.value, self)

  @property
  def attrs(self):
    return self.value.attrs

  def __iter__(self):
    if self.value:
      yield self.value

  def __str__(self):
    return 'return %s' % self.value

@wraps(ast.Yield)
class Yield(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.value = wrap(node.value, self)

  def __iter__(self):
    yield self.value

  def __str__(self):
    return 'yield %s' % self.value

@wraps(ast.Continue)
class Continue(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    pass

  def __str__(self):
    return 'continue'

@wraps(ast.Pass)
class Pass(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    pass

  def __str__(self):
    return 'pass'

@wraps(ast.Assert)
class Assert(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.test = wrap(node.test, self)
    self.msg = wrap(node.msg, self)

  def __iter__(self):
    yield self.test
    if self.msg is not None:
      yield self.msg

  def __str__(self):
    return 'assert %s, %s' % (self.test, self.msg)

@wraps(ast.Assign)
class Assign(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.targets = wrap(node.targets, self)
    self.value = wrap(node.value, self)

  @property
  def attrs(self):
    return self.value.attrs

  def __iter__(self):
    return iter(self.targets + [self.value])

  def __str__(self):
    return '%s = %s' % (', '.join(str(t) for t in self.targets), str(self.value))

@wraps(ast.AugAssign)
class AugAssign(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.target = wrap(node.target, self)
    self.value = wrap(node.value, self)
    self.op = node.op

  def __iter__(self):
    yield self.target
    yield self.value

  def __str__(self):
    return '%s %s= %s' % (self.target, operator_to_symbol(self.op), self.value)

@wraps(ast.BinOp)
class BinOp(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.left = wrap(node.left, self)
    self.right = wrap(node.right, self)
    self.op = node.op

  def __iter__(self):
    yield self.left
    yield self.right

  def __str__(self):
    return '%s %s %s' % (self.left, operator_to_symbol(self.op), self.right)

@wraps(ast.IfExp)
class IfExp(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.test = wrap(node.test, self)
    self.body = wrap(node.body, self)
    self.orelse = wrap(node.orelse, self)

  def __iter__(self):
    items = [self.test]
    # In inline if/else expressions body and orelse are not lists.
    if isinstance(self.body, collections.Iterator):
      items.extend(self.body)
    else:
      items.append(self.body)
    if isinstance(self.orelse, collections.Iterator):
      items.extend(self.orelse)
    else:
      items.append(self.orelse)
    return iter(items)

  def __str__(self):
    return '%s if %s else %s' % (self.body, self.test, self.orelse)

@wraps(ast.GeneratorExp)
class GeneratorExp(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.elt = wrap(node.elt, self)
    self.generators = wrap(node.generators, self)

  def __iter__(self):
    return iter([self.elt] + self.generators)

  def __str__(self):
    return '(%s for %s)' % (self.elt,
        ', '.join(str(g) for g in self.generators))

@wraps(ast.comprehension)
class Comprehension(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.ifs = wrap(node.ifs, self)
    self.target = wrap(node.target, self)
    self.iter = wrap(node.iter, self)

  def __iter__(self):
    return iter([self.target, self.iter] + self.ifs)

  def __str__(self):
    return '%s in %s' % (self.target, self.iter)

@wraps(ast.ListComp)
class ListComprehension(LiteralValue):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.python_type = list
    self.elt = wrap(node.elt, self)
    self.generators = wrap(node.generators, self)
    # self.ifs = wrap(node.ifs, self)

  def __iter__(self):
    return iter([self.elt] + self.generators)

  def __str__(self):
    return '[%s for %s]' % (self.elt,
        ', '.join(str(g) for g in self.generators))

@wraps(ast.Tuple)
class Tuple(LiteralValue):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.python_type = tuple
    self.elts = wrap(node.elts, self)

  def __iter__(self):
    return iter(self.elts)

  def __str__(self):
    return '(%s)' % ', '.join(str(e) for e in self.elts)

@wraps(ast.Call)
class Call(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.func = wrap(node.func, self)
    self.args = wrap(node.args, self)
    self.keywords = wrap(node.keywords, self)
    self.starargs = wrap(node.starargs, self)
    self.kwargs = wrap(node.kwargs, self)

  @property
  def attrs(self):
    result = []
    for obj in self.definitions:
      result.extend(obj.attrs)
    return result

  @property
  def definitions(self):
    ''' Yield the function definitions that might be related to a node. '''
    found = False
    name = self.func.value
    scope = self
    while not found and scope.parent:
      for node in scope.containing_scope:
        if isinstance(node, (FunctionDef, ClassDef, Lambda)) and node.name == name:
          found = True
          yield node
        else:
          scope = scope.containing_scope

  def __iter__(self):
    items = [self.func] + self.args + self.keywords
    if self.starargs:
      items.append(self.starargs)
    if self.kwargs:
      items.append(self.kwargs)
    return iter(items)

  def __str__(self):
    args = [str(a) for a in self.args]
    args.extend(str(k) for k in self.keywords)
    if self.starargs:
      args.append('*' + str(self.starargs))
    if self.kwargs:
      args.append('**' + str(self.kwargs))
    return '%s(%s)' % (self.func, ', '.join(args))

@wraps(ast.keyword)
class Keyword(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.arg = node.arg
    self.value = wrap(node.value, self)

  def __iter__(self):
    yield self.value

  def __str__(self):
    return '%s=%s' % (self.arg, self.value)

@wraps(ast.Exec)
class Exec(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.body = wrap(node.body)
    self.globals = wrap(node.globals)
    self.locals = wrap(node.locals)

  def __iter__(self):
    return iter([self.globals, self.locals] + self.body)

  def __str__(self):
    text = 'exec %s' % self.body
    if self.globals:
      text += ' in %s' % self.globals
      if self.locals:
        text += ', %s' % self.locals
    return text

@wraps(ast.Attribute)
class Attribute(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.value = wrap(node.value, self)
    self.attr = node.attr

  @property
  def attrs(self):
    pass
    
  @property
  def path(self):
    if isinstance(self.value, Name):
      return [self.attr, self.value.value]
    while isinstance(self.value, Attribute):
      return [self.attr] + self.value.path

  def __iter__(self):
    yield self.value

  def __str__(self):
    return str(self.value) + '.' + str(self.attr)

@wraps(ast.Name)
class Name(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.value = node.id

  @property
  def attrs(self):
    if self.value == 'self':
      return(self.containing_class.attrs)
    result = []
    path = self.path
    for node in self.sources:
      if isinstance(node, Alias):
        node = node.module
        while path:
          name = path.pop(0)
          for n in node.walk((ClassDef, FunctionDef, Assign, Alias), one_scope=True):
            if isinstance(n, (ClassDef, FunctionDef)) and n.name == name:
              node = n
            elif isinstance(n, Assign) and name in flatten(n.targets):
              node = n
            elif isinstance(n, Alias) and (n.asname or n.name) == name:
              node = n
      result.extend(node.attrs)
    return result

  @property
  def path(self):
    path = []
    node = self
    while isinstance(node.parent, Attribute):
      path.append(node.parent.attr)
      node = node.parent
    return path

  @property
  def sources(self):
    # TODO This doesn't take shadowed variables into account yet! (might get annoying :-)
    node = self
    while node.parent:
      for source in node.containing_scope.walk((Assign, Alias), one_scope=True):
        if isinstance(source, Assign):
          for name in flatten(source.targets):
            if name.value == self.value:
              yield source
        elif isinstance(source, Alias):
          if (source.asname or source.name) == self.value:
            yield source
      node = node.containing_scope

  def __str__(self):
    return str(self.value)

@wraps(ast.Dict)
class Dictionary(LiteralValue):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.python_type = dict
    self.keys = wrap(node.keys, self)
    self.values = wrap(node.values, self)

  def __iter__(self):
    return iter(self.keys + self.values)

  def __str__(self):
    return '{%s}' % ', '.join(
        str(self.keys[i]) + ': ' + str(self.values[i])
        for i in xrange(len(self.keys)))

@wraps(ast.List)
class List(LiteralValue):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.python_type = list
    self.elts = wrap(node.elts, self)

  def __iter__(self):
    return iter(self.elts)

  def __str__(self):
    return '[%s]' % ', '.join(str(e) for e in self.elts)

@wraps(ast.Str)
class Str(LiteralValue):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.python_type = str
    self.value = node.s

  def __str__(self):
    return '%r' % self.value

@wraps(ast.Num)
class Num(LiteralValue):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.python_type = type(node.n)
    self.value = node.n

  def __str__(self):
    return str(self.value)

@wraps(ast.Subscript)
class Subscript(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.value = wrap(node.value, self)
    self.slice = wrap(node.slice, self) # ast.Index

  def __iter__(self):
    yield self.value
    yield self.slice

  def __str__(self):
    return '%s[%s]' % (self.value, self.slice)

@wraps(ast.Index)
class Index(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.value = wrap(node.value, self)

  def __iter__(self):
    yield self.value

  def __str__(self):
    return str(self.value)

@wraps(ast.BoolOp)
class BoolOp(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.op = node.op
    self.values = wrap(node.values, self)

  def __iter__(self):
    return iter(self.values)

  def __str__(self):
    if isinstance(self.op, ast.And):
      return ' and '.join(str(v) for v in self.values)
    elif isinstance(self.op, ast.Or):
      return ' or '.join(str(v) for v in self.values)
    else:
      assert False, "Unsupported boolean operator %s" % self.op

@wraps(ast.UnaryOp)
class UnaryOp(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.op = node.op
    self.operand = wrap(node.operand, self)

  def __iter__(self):
    yield self.operand

  def __str__(self):
    op = operator_to_symbol(self.op)
    return '%s %s' % (op, self.operand)

@wraps(ast.Compare)
class Compare(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.left = wrap(node.left, self)
    self.ops = node.ops
    self.comparators = wrap(node.comparators, self)

  def __iter__(self):
    return iter([self.left] + self.comparators)

  def __str__(self):
    text = str(self.left)
    for i in xrange(len(self.ops)):
      op = operator_to_symbol(self.ops[i])
      subject = self.comparators[i]
      text += ' %s %s' % (op, subject)
    return text

@wraps(ast.Break)
class Break(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    pass

  def __str__(self):
    return 'break'

@wraps(ast.Global)
class Global(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.names = node.names

  def __str__(self):
    return 'global %s' % ', '.join(str(g) for g in self.names)

@wraps(ast.Delete)
class Delete(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.targets = wrap(node.targets)

  def __iter__(self):
    return iter(self.targets)

  def __str__(self):
    return 'delete %s' % ', '.join(str(t) for t in self.targets)

@wraps(ast.Ellipsis)
class Ellipsis(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    pass

  def __str__(self):
    return '...'

@wraps(ast.Lambda)
class Lambda(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.args = wrap(node.args.args)
    self.defaults = wrap(node.args.defaults)
    self.vararg = node.args.vararg
    self.kwarg = node.args.kwarg
    self.body = wrap(node.body)

  def __iter__(self):
    return iter(self.args + self.defaults + [self.body])

  def __str__(self):
    args = []
    args.extend(self.args)
    args.extend(self.defaults)
    if self.vararg:
      args.append('*' + str(self.vararg))
    if self.kwarg:
      args.append('**' + str(self.kwarg))
    return 'lambda %s: %s' % (', '.join(str(a) for a in args), self.body)

@wraps(ast.Raise)
class Raise(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.type = wrap(node.type)
    self.inst = wrap(node.inst)

  def __iter__(self):
    if self.type:
      yield self.type
    if self.inst:
      yield self.inst

  def __str__(self):
    args = []
    if self.type:
      args.append(str(self.type))
    if self.inst:
      args.append(str(self.inst))
    words = ['raise']
    if args:
      words.append(', '.join(args))
    return ' '.join(words)

@wraps(ast.Slice)
class Slice(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.lower = wrap(node.lower)
    self.upper = wrap(node.upper)
    self.step = wrap(node.step)

  def __iter__(self):
    if self.lower:
      yield self.lower
    if self.upper:
      yield self.upper
    if self.step:
      yield self.step

  def __str__(self):
    parts = []
    parts.append(str(self.lower) if self.lower is not None else '')
    parts.append(str(self.upper) if self.upper is not None else '')
    parts.append(str(self.step) if self.step is not None else '')
    return ':'.join(parts)

@wraps(ast.ExtSlice)
class ExtSlice(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.dims = wrap(node.dims)

  def __iter__(self):
    return iter(self.dims)

  def __str__(self):
    return ', '.join(str(d) for d in self.dims)

@wraps(ast.TryExcept)
class TryExcept(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.body = wrap(node.body)
    self.handlers = wrap(node.handlers)
    self.orelse = wrap(node.orelse)

  def __iter__(self):
    return iter(self.body + self.handlers + self.orelse)

  def __str__(self):
    text = 'try:\n' + indent(self.body)
    for handler in self.handlers:
      text += '\n' + str(handler)
    if self.orelse:
      text += 'else:\n' + indent(self.orelse)
    return text

@wraps(ast.TryFinally)
class TryFinally(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.body = wrap(node.body)
    self.finalbody = wrap(node.finalbody)

  def __iter__(self):
    return iter(self.body + self.finalbody)

  def __str__(self):
    return '%s\nfinally:\n%s' % (self.body, indent(self.finalbody))

@wraps(ast.Repr)
class Repr(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.value = wrap(node.value)

  def __iter__(self):
    yield self.value

  def __str__(self):
    return 'repr(%s)' % self.value

@wraps(ast.ExceptHandler)
class ExceptHandler(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.type = wrap(node.type)
    self.name = wrap(node.name)
    self.body = wrap(node.body)

  def __iter__(self):
    items = []
    if self.type:
      items.append(self.type)
    if self.name:
      items.append(self.name)
    items += self.body
    return iter(items)

  def __str__(self):
    text = 'except'
    if self.type:
      text += ' %s' % self.type
      if self.name:
        text += ', %s' % self.name
    return text + ':\n' + indent(self.body)

@wraps(ast.With)
class With(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.context_expr = wrap(node.context_expr, self)
    self.optional_vars = wrap(node.optional_vars, self)
    self.body = wrap(node.body, self)

  def __iter__(self):
    return iter([self.context_expr, self.optional_vars] + self.body)

  def __str__(self):
    text = 'with %s' % self.context_expr
    if self.optional_vars:
      text += ' as %s' % self.optional_vars
    return '%s:\n%s' % (text, indent(self.body))

def parse(source):
  '''
  Parse some Python source code using the ast module and convert the resulting
  tree into objects of our type hierarchy.
  '''
  return wrap(ast.parse(source))

def flatten(nested, flat=None):
  ''' Squash a nested sequence into a flat list of nodes. '''
  if flat is None:
    flat = []
  if isinstance(nested, (Tuple, List)):
    for node in nested.elts:
      flatten(node, flat)
  elif isinstance(nested, (tuple, list)):
    for node in nested:
      flatten(node, flat)
  else:
    flat.append(nested)
  return flat

def wrap(value, parent=None):
  '''
  Convert an AST generated by ast.parse() into a tree of objects from our own
  type hierarchy.
  '''
  if not value or isinstance(value, (numbers.Number, basestring)):
    # Nothing to wrap.
    return value
  if isinstance(value, ast.AST):
    type_id = id(type(value))
    if type_id in type_mapping:
      # Found a mapped type.
      return type_mapping[type_id](value, parent)
  if isinstance(value, collections.Iterable):
    # Map a sequence of values.
    return [wrap(v, parent) for v in value]
  assert False, "Failed to map %s (%s, %s)" % (value, type(value), ast.dump(value))
  return value

def operator_to_symbol(op):
  '''
  Return the string representation of an ast.* operator node.
  '''
  if isinstance(op, ast.Add): return '+'
  if isinstance(op, ast.UAdd): return '+'
  if isinstance(op, ast.FloorDiv): return '//'
  if isinstance(op, ast.BitAnd): return '&'
  if isinstance(op, ast.BitOr): return '|'
  if isinstance(op, ast.BitXor): return '^'
  if isinstance(op, ast.LShift): return '<<'
  if isinstance(op, ast.RShift): return '>>'
  if isinstance(op, ast.Div): return '/'
  if isinstance(op, ast.Eq): return '=='
  if isinstance(op, ast.Gt): return '>'
  if isinstance(op, ast.GtE): return '>='
  if isinstance(op, ast.In): return 'in'
  if isinstance(op, ast.Invert): return '~'
  if isinstance(op, ast.Lt): return '<'
  if isinstance(op, ast.USub): return '-'
  if isinstance(op, ast.Pow): return '**'
  if isinstance(op, ast.LtE): return '<='
  if isinstance(op, ast.IsNot): return 'is not'
  if isinstance(op, ast.Is): return 'is'
  if isinstance(op, ast.Mod): return '%'
  if isinstance(op, ast.Mult): return '*'
  if isinstance(op, ast.Not): return 'not'
  if isinstance(op, ast.NotEq): return '!='
  if isinstance(op, ast.NotIn): return 'not in'
  if isinstance(op, ast.Sub): return '-'
  assert False, "Operator %s not yet supported! (%s)" % (op, ast.dump(op))

def indent(block):
  '''
  Indent every line in a multi line string with two spaces.
  '''
  if isinstance(block, list):
    block = '\n'.join(str(n) for n in block)
  return '  ' + block.replace('\n', '\n  ')

if __name__ == '__main__':
  with open(__file__) as handle:
    print wrap(ast.parse(handle.read()))
