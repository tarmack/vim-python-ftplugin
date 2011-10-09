# The type inference engine is turning into a royal mess because we get these
# huge if/elif/else chains that switch on AST types. I was thinking maybe it
# would be better to divide such blocks over methods in a type hierarchy of our
# own, to hide the uncomfortable parts of the Python AST. The problem is that
# we have to write a lot of boilerplate code and the runtime end result will be
# a bit wasteful because we're wrapping the full abstract syntax tree.
#
# TODO (Ab)use scope awareness to complete variables valid in scope?
# TODO Decorators are missing from the pretty printed output.

import ast
import numbers
import collections

DEBUG = True

type_mapping = {}

def wraps(ast_type):
  def decorator(cls):
    type_mapping[id(ast_type)] = cls
    return cls
  return decorator

def log(msg, *args):
  print msg % args

class Node(object):

  def __init__(self, node, parent):
    self.parent = parent
    self.column = getattr(node, 'col_offset', 0)
    self.line = getattr(node, 'lineno', 0)

  @property
  def tree(self):
    return self._find_parent()

  @property
  def containing_class(self):
    return self._find_parent(ClassDef)

  @property
  def containing_scope(self):
    return self._find_parent(ClassDef, Module)

  @property
  def containing_function(self):
    return self._find_parent(FunctionDef)

  @property
  def containing_module(self):
    return self._find_parent(Module)

  def _find_parent(self, *types):
    if self.parent is None:
      return self
    elif isinstance(self.parent, types):
      return self.parent
    else:
      return self.parent._find_parent(*types)

class Statement(Node):
  pass

@wraps(ast.Expr)
class Expression(Node):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.value = wrap(node.value, self)

  @property
  def attrs(self):
    return self.value.attrs

  def __iter__(self):
    return iter([self.value])

  def __str__(self):
    return str(self.value)

@wraps(ast.Module)
class Module(Statement):

  def __init__(self, node, parent):
    #log("Constructing module ..")
    Node.__init__(self, node, parent)
    self.body = wrap(node.body, self)

  def __iter__(self):
    return iter(self.body)

  def __str__(self):
    return 'module:\n' + indent(self.body)

@wraps(ast.ClassDef)
class ClassDef(Statement):

  def __init__(self, node, parent):
    #log("Constructing class from %s ..", ast.dump(node))
    Node.__init__(self, node, parent)
    self.name = wrap(node.name, self)
    self.bases = wrap(node.bases)
    self.body = wrap(node.body, self)

  @property
  def attrs(self):
    # TODO Implement.
    results = []
    for node in self:
      if isinstance(node, FunctionDef):
        results.append(node.name)
      elif isinstance(node, Attribute) and str(node.value) == 'self':
        results.append(node.attr)
      elif isinstance(node, Assign):
        results.extend([t.value for t in node.targets])
    return results

  def __iter__(self):
    yield self.name
    for base in self.bases:
      yield base
    for node in self.body:
      yield node

  def __str__(self):
    text = 'class %s' % self.name
    if self.bases:
      text += '(%s)' % ', '.join(str(b) for b in self.bases)
    return text + ':\n%s' % indent(self.body)

@wraps(ast.FunctionDef)
class FunctionDef(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.name = wrap(node.name, self)
    #log("Constructing function %s ..", self.name)
    self.args = wrap(node.args.args, self)
    self.defaults = wrap(node.args.defaults, self)
    self.vararg = wrap(node.args.vararg, self) if node.args.vararg else None
    self.kwarg = wrap(node.args.kwarg, self) if node.args.kwarg else None
    self.body = wrap(node.body, self)

  @property
  def attrs(self):
    results = []
    for obj in self.body:
      if isinstance(obj, Return):
        results.extend(obj.attrs)
    return results

  def __iter__(self):
    for argument in self.args:
      yield argument
    for default in self.defaults:
      yield default
    if self.vararg:
      yield self.vararg
    if self.kwarg:
      yield self.kwarg
    for child in self.body:
      yield child

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

@wraps(ast.Import)
class Import(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    #log("Constructing import statement from %s ..", ast.dump(node))
    self.names = wrap(node.names, self)

  def __iter__(self):
    return iter(self.names)

  def __str__(self):
    return 'import ' + ', '.join(str(n) for n in self.names)

@wraps(ast.ImportFrom)
class ImportFrom(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    #log("Constructing ImportFrom statement from %s", ast.dump(node))
    self.module = wrap(node.module, self)
    self.names = wrap(node.names, self)

  def __iter__(self):
    return iter([self.module] + self.names)

  def __str__(self):
    return "from %s import %s" % (self.module,
        ', '.join(str(n) for n in self.names))

@wraps(ast.alias)
class Alias(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    self.name = wrap(node.name, self)
    self.asname = wrap(node.asname, self)

  def __iter__(self):
    return iter([self.name, self.asname])

  def __str__(self):
    text = str(self.name)
    if self.asname:
      text += ' as ' + str(self.asname)
    return text

@wraps(ast.If)
class If(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    #log("Constructing if statement ..")
    self.test = wrap(node.test, self)
    self.body = wrap(node.body, self)
    self.orelse = wrap(node.orelse, self)

  def __iter__(self):
    yield self.test
    for child in self.body:
      yield child
    for child in self.orelse:
      yield child

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
    #log("Constructing for loop statement from %s", ast.dump(node))
    self.target = wrap(node.target, self)
    self.iter = wrap(node.iter, self)
    self.body = wrap(node.body, self)
    self.orelse = wrap(node.orelse, self)

  def __iter__(self):
    yield self.target
    yield self.iter
    for node in self.body:
      yield node
    for node in self.orelse:
      yield node

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
    #log("Constructing while loop statement from %s", ast.dump(node))
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
    #log("Constructing print statement from %s", ast.dump(node))
    self.values = wrap(node.values, self)

  def __iter__(self):
    return iter(self.values)

  def __str__(self):
    return 'print %s' % ', '.join(str(v) for v in self.values)

@wraps(ast.Return)
class Return(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    #log("Constructing return statement ..")
    self.value = wrap(node.value, self)

  @property
  def attrs(self):
    return self.value.attrs

  def __iter__(self):
    return iter([self.value])

  def __str__(self):
    return 'return %s' % self.value

@wraps(ast.Yield)
class Yield(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    #log("Constructing yield statement ..")
    self.value = wrap(node.value, self)

  def __iter__(self):
    return iter([self.value])

  def __str__(self):
    return 'yield %s' % self.value

@wraps(ast.Continue)
class Continue(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    #log("Constructing continue statement ..")
    pass

  def __iter__(self):
    return iter([])

  def __str__(self):
    return 'continue'

@wraps(ast.Pass)
class Pass(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    #log("Constructing pass statement ..")
    pass

  def __iter__(self):
    return iter([])

  def __str__(self):
    return 'pass'

@wraps(ast.Assert)
class Assert(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    #log("Constructing assert statement from %s", ast.dump(node))
    self.test = wrap(node.test, self)
    self.msg = wrap(node.msg, self)

  def __iter__(self):
    return iter([self.test, self.msg])

  def __str__(self):
    return 'assert %s, %s' % (self.test, self.msg)

@wraps(ast.Assign)
class Assign(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    #log("Constructing assignment statement ..")
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
    #log("Constructing augmented assignment statement ..")
    self.target = wrap(node.target, self)
    self.value = wrap(node.value, self)
    self.op = node.op

  def __iter__(self):
    return iter([self.target, self.value])

  def __str__(self):
    return '%s %s= %s' % (self.target, operator_to_symbol(self.op), self.value)

@wraps(ast.BinOp)
class BinOp(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    #log("Constructing binary operator expression from %s ..", ast.dump(node))
    self.left = wrap(node.left, self)
    self.right = wrap(node.right, self)
    self.op = node.op

  def __iter__(self):
    return iter([self.left, self.right])

  def __str__(self):
    return '%s %s %s' % (self.left, operator_to_symbol(self.op), self.right)

@wraps(ast.IfExp)
class IfExp(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    #log("Constructing if expression from %s ..", ast.dump(node))
    self.test = wrap(node.test, self)
    self.body = wrap(node.body, self)
    self.orelse = wrap(node.orelse, self)

  def __iter__(self):
    return iter([self.test] + self.body + self.orelse)

  def __str__(self):
    return '%s if %s else %s' % (self.body, self.test, self.orelse)

@wraps(ast.GeneratorExp)
class GeneratorExp(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    #log("Constructing generator expression from %s ..", ast.dump(node))
    self.elt = wrap(node.elt, self)
    self.generators = wrap(node.generators, self)

  def __iter__(self):
    yield self.elt
    for node in self.generators:
      yield node

  def __str__(self):
    return '(%s for %s)' % (self.elt,
        ', '.join(str(g) for g in self.generators))

@wraps(ast.comprehension)
class Comprehension(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    #log("Constructing comprehension from %s ..", ast.dump(node))
    self.target = wrap(node.target, self)
    self.iter = wrap(node.iter, self)

  def __iter__(self):
    yield self.target
    yield self.iter

  def __str__(self):
    return '%s in %s' % (self.target, self.iter)

@wraps(ast.ListComp)
class ListComprehension(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    #log("Constructing list comprehension from %s ..", ast.dump(node))
    self.elt = wrap(node.elt, self)
    self.generators = wrap(node.generators, self)
    # self.ifs = wrap(node.ifs, self)

  def __iter__(self):
    return iter([self.elt] + self.generators)

  def __str__(self):
    return '[%s for %s]' % (self.elt,
        ', '.join(str(g) for g in self.generators))

@wraps(ast.Tuple)
class Tuple(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    #log("Constructing tuple expression ..")
    self.elts = wrap(node.elts, self)

  @property
  def attrs(self):
    return dir(tuple)

  def __iter__(self):
    return iter(self.elts)

  def __str__(self):
    return '(%s)' % ', '.join(str(e) for e in self.elts)

@wraps(ast.Call)
class Call(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    #log("Constructing call expression ..")
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
      scope = scope.containing_scope
      for node in scope:
        if isinstance(node, (FunctionDef, ClassDef, Lambda)) and node.name == name:
          found = True
          yield node

  def __iter__(self):
    for node in self.func:
      yield node
    for node in self.args:
      yield node
    for node in self.keywords:
      yield node
    if self.starargs:
      yield self.starargs
    if self.kwargs:
      yield self.kwargs

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
    self.arg = wrap(node.arg, self)
    self.value = wrap(node.value, self)

  def __iter__(self):
    return iter([self.arg, self.value])

  def __str__(self):
    return '%s=%s' % (self.arg, self.value)

@wraps(ast.Exec)
class Exec(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    #log("Constructing exec statement from %s ..", ast.dump(node))
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
    #log("Constructing attribute expression ..")
    self.value = wrap(node.value, self)
    self.attr = wrap(node.attr, self)

  @property
  def attrs(self):
    pass

  def __iter__(self):
    return iter([self.value, self.attr])

  def __str__(self):
    return str(self.value) + '.' + str(self.attr)

@wraps(ast.Name)
class Name(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    #log("Constructing name expression %s from %s ..", node.id, ast.dump(node))
    self.value = node.id

  @property
  def attrs(self):
    result = []
    for node in self.assignments:
      result.extend(node.attrs)
    return result

  @property
  def assignments(self):
    found = False
    name = self.value
    scope = self
    while not found and scope.parent:
      scope = scope.containing_scope
      for node in scope:
        if isinstance(node, Assign):
          for n in flatten(node.targets):
            if n.value == name:
              found = True
              yield node

  def __iter__(self):
    return iter([self.value])

  def __str__(self):
    return str(self.value)

@wraps(ast.Dict)
class Dictionary(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    #log("Constructing dictionary expression ..")
    self.keys = wrap(node.keys, self)
    self.values = wrap(node.values, self)

  @property
  def attrs(self):
    return dir(dict)

  def __iter__(self):
    return iter(self.keys + self.values)

  def __str__(self):
    return '{%s}' % ', '.join(
        str(self.keys[i]) + ': ' + str(self.values[i])
        for i in xrange(len(self.keys)))

@wraps(ast.List)
class List(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    #log("Constructing list expression ..")
    self.elts = wrap(node.elts, self)

  @property
  def attrs(self):
    return dir(list)

  def __iter__(self):
    return iter(self.elts)

  def __str__(self):
    return '[%s]' % ', '.join(str(e) for e in self.elts)

@wraps(ast.Str)
class Str(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    #log("Constructing string expression ..")
    self.value = node.s

  @property
  def attrs(self):
    return dir(str)

  def __iter__(self):
    return iter([self.value])

  def __str__(self):
    if DEBUG:
      # Don't dump long strings completely.
      return '%r' % self.value[:25]
    else:
      return '%r' % self.value

@wraps(ast.Num)
class Num(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    #log("Constructing number expression ..")
    self.value = node.n

  @property
  def attrs(self):
    return dir(self.value)

  def __iter__(self):
    return iter([self.value])

  def __str__(self):
    return str(self.value)

@wraps(ast.Subscript)
class Subscript(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    #log("Constructing subscript expression from %s", ast.dump(node))
    self.value = wrap(node.value, self)
    self.slice = wrap(node.slice, self) # ast.Index

  def __iter__(self):
    return iter([self.value, self.slice])

  def __str__(self):
    return '%s[%s]' % (self.value, self.slice)

@wraps(ast.Index)
class Index(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    #log("Constructing index expression from %s", ast.dump(node))
    self.value = wrap(node.value, self)

  def __iter__(self):
    return iter([self.value])

  def __str__(self):
    return str(self.value)

@wraps(ast.BoolOp)
class BoolOp(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    #log("Constructing boolean operator expression from %s", ast.dump(node))
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
    #log("Constructing unary operator expression from %s", ast.dump(node))
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
    #log("Constructing comparison operator expression from %s", ast.dump(node))
    self.left = wrap(node.left, self)
    self.ops = node.ops
    self.comparators = wrap(node.comparators, self)

  def __iter__(self):
    yield self.left
    for node in self.comparators:
      yield node

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
    #log("Constructing break statement from %s", ast.dump(node))
    pass

  def __iter__(self):
    return iter([])

  def __str__(self):
    return 'break'

@wraps(ast.Global)
class Global(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    #log("Constructing global statement from %s", ast.dump(node))
    self.names = wrap(node.names)

  def __iter__(self):
    return iter(self.names)

  def __str__(self):
    return 'global %s' % ', '.join(str(g) for g in self.names)

@wraps(ast.Delete)
class Delete(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    #log("Constructing delete statement from %s", ast.dump(node))
    self.targets = wrap(node.targets)

  def __iter__(self):
    return iter(self.targets)

  def __str__(self):
    return 'delete %s' % ', '.join(str(t) for t in self.targets)

@wraps(ast.Ellipsis)
class Ellipsis(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    #log("Constructing ellipsis expression from %s", ast.dump(node))
    pass

  def __iter__(self):
    return iter([])

  def __str__(self):
    return '...'

@wraps(ast.Lambda)
class Lambda(Expression):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    #log("Constructing lambda expression from %s", ast.dump(node))
    self.args = wrap(node.args.args)
    self.defaults = wrap(node.args.defaults)
    self.vararg = wrap(node.args.vararg) if node.args.vararg else None
    self.kwarg = wrap(node.args.kwarg) if node.args.kwarg else None
    self.body = wrap(node.body)

  def __iter__(self):
    for argument in self.args:
      yield argument
    for default in self.defaults:
      yield default
    if self.vararg:
      yield self.vararg
    if self.kwarg:
      yield self.kwarg
    for child in self.body:
      yield child

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
    #log("Constructing raise statement from %s", ast.dump(node))
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
    #log("Constructing slice expression from %s", ast.dump(node))
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

    if self.lower and self.upper and self.step:
      return '%s:%s:%s' % (self.lower, self.upper, self.step)
    elif self.lower and self.upper and not self.step:
      return '%s:%s' % (self.lower, self.upper)
    elif self.lower and not self.upper and not self.step:
      return '%s:' % self.lower
    elif self.lower and self.step and not self.upper:
      return '%s::%s' % (self.lower, self.step)
    elif self.upper and not self.lower and not self.step:
      return ':%s' % self.upper
    elif self.step and not self.upper and not self.lower:
      return '::%s' % self.step
    elif not (self.lower or self.upper or self.step):
      return ':'
    else:
      log("Failed to pretty print slice! lower=%s, upper=%s, step=%s",
          self.lower, self.upper, self.step)
      assert False, "Should not happen?!"

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
    #log("Constructing try/except statement from %s", ast.dump(node))
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
    #log("Constructing try/finally statement from %s", ast.dump(node))
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
    #log("Constructing repr() expression from %s", ast.dump(node))
    self.value = wrap(node.value)

  def __iter__(self):
    return iter([self.value])

  def __str__(self):
    return 'repr(%s)' % self.value

@wraps(ast.ExceptHandler)
class ExceptHandler(Statement):

  def __init__(self, node, parent):
    Node.__init__(self, node, parent)
    #log("Constructing try/except handler statement from %s", ast.dump(node))
    self.type = wrap(node.type)
    self.name = wrap(node.name)
    self.body = wrap(node.body)

  def __iter__(self):
    if self.type:
      yield self.type
    if self.name:
      yield self.name
    for node in self.body:
      yield node

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
    #log("Constructing with statement from %s", ast.dump(node))
    self.context_expr = wrap(node.context_expr, self)
    self.optional_vars = wrap(node.optional_vars, self)
    self.body = wrap(node.body, self)

  def __iter__(self):
    yield self.context_expr
    yield self.optional_vars
    for node in self.body:
      yield node

  def __str__(self):
    text = 'with %s' % self.context_expr
    if self.optional_vars:
      text += ' as %s' % self.optional_vars
    return '%s:\n%s' % (text, indent(self.body))

class TypeInferenceEngine(object):
  def __init__(self, source):
    assert isinstance(source, basestring)
    self.tree = wrap(ast.parse(source))

  def complete(self, line, column):
    node = self.find_node(self.tree, line, column)
    if node:
      candidates = list()
      candidates.extend(node.attrs)
      return set(candidates)

  def find_node(self, tree, line, column):
    ''' Find the node at the given (line, column) in the AST. '''
    last_node = None
    for node in tree:
      if node.line == line:
        node_id = str(getattr(node, 'value', ''))
        if node.column <= column <= node.column + len(node_id):
          return node
      elif node.line >= line and last_node and last_node.line <= line:
        return self.find_node(last_node, line, column)
      else:
        last_node = node

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
  if isinstance(block, list):
    block = '\n'.join(str(n) for n in block)
  return '  ' + block.replace('\n', '\n  ')


if __name__ == '__main__':
  with open(__file__) as handle:
    print wrap(ast.parse(handle.read()))

