# The type inference engine is turning into a royal mess because we get these
# huge if/elif/else chains that switch on AST types. I was thinking maybe it
# would be better to divide such blocks over methods in a type hierarchy of our
# own, to hide the uncomfortable parts of the Python AST. The problem is that
# we have to write a lot of boilerplate code and the runtime end result will be
# a bit wasteful because we're wrapping the full abstract syntax tree.

import ast
import numbers
import collections
import sys

def log(msg, *args):
  print msg % args

class Node(object):
  pass

class Statement(Node):
  pass

class Expression(Node):

  def __init__(self, node, parent=None):
    self.parent = parent
    self.value = wrap(node.value, self)

  def __iter__(self):
    return iter([self.value])

  def __str__(self):
    return str(self.value)

class Module(Statement):

  def __init__(self, node, parent=None):
    #log("Constructing module ..")
    self.parent = parent
    self.body = wrap(node.body, self)

  def __iter__(self):
    return iter(self.body)

  def __str__(self):
    return 'module:\n' + indent(self.body)

class ClassDef(Statement):

  def __init__(self, node, parent=None):
    self.parent = parent
    self.name = wrap(node.name, self)
    #log("Constructing class %s ..", self.name)
    self.body = wrap(node.body, self)

  def __iter__(self):
    return iter(self.body)

  def __str__(self):
    return 'class %s:\n%s' % (self.name, indent(self.body))

class FunctionDef(Statement):

  def __init__(self, node, parent=None):
    self.parent = parent
    self.name = wrap(node.name, self)
    #log("Constructing function %s ..", self.name)
    self.args = wrap(node.args.args, self)
    self.defaults = wrap(node.args.defaults, self)
    self.vararg = wrap(node.args.vararg, self) if node.args.vararg else None
    self.kwarg = wrap(node.args.kwarg, self) if node.args.kwarg else None
    self.body = wrap(node.body, self)

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
    return 'function %s(%s):\n%s' % (
        self.name,
        ', '.join(str(a) for a in args),
        indent(self.body))

class Import(Statement):

  def __init__(self, node, parent=None):
    self.parent = parent
    #log("Constructing import statement from %s ..", ast.dump(node))
    self.names = wrap(node.names, self)

  def __iter__(self):
    return iter(self.names)

  def __str__(self):
    return 'import ' + ', '.join(str(n) for n in self.names)

class ImportFrom(Statement):

  def __init__(self, node, parent=None):
    self.parent = parent
    #log("Constructing ImportFrom statement from %s", ast.dump(node))
    self.module = wrap(node.module, self)
    self.names = wrap(node.names, self)

  def __iter__(self):
    return iter([self.module] + self.names)

  def __str__(self):
    return "from %s import %s" % (self.module,
        ', '.join(str(n) for n in self.names))

class Alias(Expression):

  def __init__(self, node, parent=None):
    self.parent = parent
    self.name = wrap(node.name, self)
    self.asname = wrap(node.asname, self)

  def __iter__(self):
    return iter([self.name, self.asname])

  def __str__(self):
    text = str(self.name)
    if self.asname:
      text += ' as ' + str(self.asname)
    return text

class If(Statement):

  def __init__(self, node, parent=None):
    self.parent = parent
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

class For(Statement):

  def __init__(self, node, parent=None):
    self.parent = parent
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

class While(Statement):

  def __init__(self, node, parent=None):
    self.parent = parent
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

class Print(Statement):

  def __init__(self, node, parent=None):
    self.parent = parent
    #log("Constructing print statement from %s", ast.dump(node))
    self.values = wrap(node.values, self)

  def __iter__(self):
    return iter(self.values)

  def __str__(self):
    return 'print %s' % ', '.join(str(v) for v in self.values)

class Return(Statement):

  def __init__(self, node, parent=None):
    self.parent = parent
    #log("Constructing return statement ..")
    self.value = wrap(node.value, self)

  def __iter__(self):
    return iter([self.value])
  
  def __str__(self):
    return 'return %s' % self.value

class Yield(Statement):

  def __init__(self, node, parent=None):
    self.parent = parent
    #log("Constructing yield statement ..")
    self.value = wrap(node.value, self)

  def __iter__(self):
    return iter([self.value])
  
  def __str__(self):
    return 'yield %s' % self.value

class Pass(Statement):

  def __init__(self, node, parent=None):
    self.parent = parent
    #log("Constructing pass statement ..")
    pass

  def __iter__(self):
    return iter([])
  
  def __str__(self):
    return 'pass'

class Assert(Statement):

  def __init__(self, node, parent=None):
    self.parent = parent
    #log("Constructing assert statement from %s", ast.dump(node))
    self.test = wrap(node.test, self)
    self.msg = wrap(node.msg, self)

  def __iter__(self):
    return iter([self.test, self.msg])

  def __str__(self):
    return 'assert %s, %s' % (self.test, self.msg)

class Assign(Statement):

  def __init__(self, node, parent=None):
    self.parent = parent
    #log("Constructing assignment statement ..")
    self.targets = wrap(node.targets, self)
    self.value = wrap(node.value, self)

  def __iter__(self):
    return iter(self.targets + [self.value])

  def __str__(self):
    return '%s = %s' % (', '.join(str(t) for t in self.targets), str(self.value))

class AugAssign(Statement):

  def __init__(self, node, parent=None):
    self.parent = parent
    #log("Constructing augmented assignment statement ..")
    self.target = wrap(node.target, self)
    self.value = wrap(node.value, self)
    self.op = node.op

  def __iter__(self):
    return iter([self.target, self.value])

  def __str__(self):
    return '%s %s= %s' % (self.target, operator_to_symbol(self.op), self.value)

class BinOp(Expression):

  def __init__(self, node, parent=None):
    self.parent = parent
    #log("Constructing binary operator expression from %s ..", ast.dump(node))
    self.left = wrap(node.left, self)
    self.right = wrap(node.right, self)
    self.op = node.op

  def __iter__(self):
    return iter([self.left, self.right])

  def __str__(self):
    return '%s %s %s' % (self.left, operator_to_symbol(self.op), self.right)

class IfExp(Expression):

  def __init__(self, node, parent=None):
    self.parent = parent
    #log("Constructing if expression from %s ..", ast.dump(node))
    self.test = wrap(node.test, self)
    self.body = wrap(node.body, self)
    self.orelse = wrap(node.orelse, self)

  def __iter__(self):
    return iter([self.test] + self.body + self.orelse)

  def __str__(self):
    return '%s if %s else %s' % (self.body, self.test, self.orelse)

class GeneratorExp(Expression):

  def __init__(self, node, parent=None):
    self.parent = parent
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

class Comprehension(Expression):

  def __init__(self, node, parent=None):
    self.parent = parent
    #log("Constructing comprehension from %s ..", ast.dump(node))
    self.target = wrap(node.target, self)
    self.iter = wrap(node.iter, self)

  def __iter__(self):
    yield self.target
    yield self.iter

  def __str__(self):
    return '%s in %s' % (self.target, self.iter)

class ListComprehension(Expression):

  def __init__(self, node, parent=None):
    self.parent = parent
    #log("Constructing list comprehension from %s ..", ast.dump(node))
    self.elt = wrap(node.elt, self)
    self.generators = wrap(node.generators, self)
    # self.ifs = wrap(node.ifs, self)

  def __iter__(self):
    return iter([self.elt] + self.generators)

  def __str__(self):
    return '[%s for %s]' % (self.elt,
        ', '.join(str(g) for g in self.generators))

class Tuple(Expression):

  def __init__(self, node, parent=None):
    self.parent = parent
    #log("Constructing tuple expression ..")
    self.elts = wrap(node.elts, self)

  def __iter__(self):
    return iter(self.elts)

  def __str__(self):
    return '(%s)' % ', '.join(str(e) for e in self.elts)

class Call(Expression):

  def __init__(self, node, parent=None):
    self.parent = parent
    #log("Constructing call expression ..")
    self.func = wrap(node.func, self)
    self.args = wrap(node.args, self)
    self.keywords = wrap(node.keywords, self)
    self.starargs = wrap(node.starargs, self)
    self.kwargs = wrap(node.kwargs, self)

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

class Keyword(Expression):

  def __init__(self, node, parent=None):
    self.parent = parent
    self.arg = wrap(node.arg, self)
    self.value = wrap(node.value, self)

  def __iter__(self):
    return iter([self.arg, self.value])

  def __str__(self):
    return '%s=%s' % (self.arg, self.value)

class Attribute(Expression):

  def __init__(self, node, parent=None):
    self.parent = parent
    #log("Constructing attribute expression ..")
    self.value = wrap(node.value, self)
    self.attr = wrap(node.attr, self)

  def __iter__(self):
    return iter([self.value, self.attr])

  def __str__(self):
    return str(self.value) + '.' + str(self.attr)

class Name(Expression):

  def __init__(self, node, parent=None):
    self.parent = parent
    #log("Constructing name expression %s from %s ..", node.id, ast.dump(node))
    self.value = node.id

  def __iter__(self):
    return iter([self.value])

  def __str__(self):
    return str(self.value)

class Dictionary(Expression):

  def __init__(self, node, parent=None):
    self.parent = parent
    #log("Constructing dictionary expression ..")
    self.keys = wrap(node.keys, self)
    self.values = wrap(node.values, self)

  def __iter__(self):
    return iter(self.keys + self.values)

  def __str__(self):
    return '{%s}' % ', '.join(
        str(self.keys[i]) + ': ' + str(self.values[i])
        for i in xrange(len(self.keys)))

class List(Expression):

  def __init__(self, node, parent=None):
    self.parent = parent
    #log("Constructing list expression ..")
    self.elts = wrap(node.elts, self)

  def __iter__(self):
    return iter(self.elts)

  def __str__(self):
    return '[%s]' % ', '.join(str(e) for e in self.elts)

class Str(Expression):

  def __init__(self, node, parent=None):
    self.parent = parent
    #log("Constructing string expression ..")
    self.value = node.s

  def __iter__(self):
    return iter([self.value])

  def __str__(self):
    return '%r' % self.value

class Num(Expression):

  def __init__(self, node, parent=None):
    self.parent = parent
    #log("Constructing number expression ..")
    self.value = node.n

  def __iter__(self):
    return iter([self.value])

  def __str__(self):
    return str(self.value)

class Subscript(Expression):

  def __init__(self, node, parent=None):
    self.parent = parent
    #log("Constructing subscript expression from %s", ast.dump(node))
    self.value = wrap(node.value, self)
    self.slice = wrap(node.slice, self) # ast.Index

  def __iter__(self):
    return iter([self.value, self.slice])

  def __str__(self):
    return '%s[%s]' % (self.value, self.slice)

class Index(Expression):

  def __init__(self, node, parent=None):
    self.parent = parent
    #log("Constructing index expression from %s", ast.dump(node))
    self.value = wrap(node.value, self)

  def __iter__(self):
    return iter([self.value])

  def __str__(self):
    return str(self.value)

class BoolOp(Expression):

  def __init__(self, node, parent=None):
    self.parent = parent
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

class UnaryOp(Expression):

  def __init__(self, node, parent=None):
    self.parent = parent
    #log("Constructing unary operator expression from %s", ast.dump(node))
    self.op = node.op
    self.operand = wrap(node.operand, self)

  def __iter__(self):
    yield self.operand

  def __str__(self):
    if isinstance(self.op, ast.Not):
      return 'not %s' % self.operand
    else:
      assert False, "Unsupported unary operator %s" % self.op

class Compare(Expression):

  def __init__(self, node, parent=None):
    self.parent = parent
    #log("Constructing comparison operator expression from %s", ast.dump(node))
    self.left = wrap(node.left, self)
    self.ops = node.ops
    self.comparators = wrap(node.comparators, self)

  def __iter__(self):
    yield self.left
    for node in self.comparators:
      yield node

  def __str__(self):
    # TODO str(Compare)
    return 'COMPARISON OF %s' % self.left

class With(Statement):

  def __init__(self, node, parent=None):
    self.parent = parent
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

type_mapping = {
    id(ast.Module): Module,
    id(ast.BoolOp): BoolOp,
    id(ast.UnaryOp): UnaryOp,
    id(ast.Compare): Compare,
    id(ast.With): With,
    id(ast.ClassDef): ClassDef,
    id(ast.FunctionDef): FunctionDef,
    id(ast.Import): Import,
    id(ast.ImportFrom): ImportFrom,
    id(ast.alias): Alias,
    id(ast.If): If,
    id(ast.For): For,
    id(ast.Index): Index,
    id(ast.While): While,
    id(ast.Print): Print,
    id(ast.Return): Return,
    id(ast.Yield): Yield,
    id(ast.Expr): Expression,
    id(ast.IfExp): IfExp,
    id(ast.GeneratorExp): GeneratorExp,
    id(ast.comprehension): Comprehension,
    id(ast.ListComp): ListComprehension,
    id(ast.BinOp): BinOp,
    id(ast.Pass): Pass,
    id(ast.AugAssign): AugAssign,
    id(ast.Subscript): Subscript,
    id(ast.Assign): Assign,
    id(ast.Assert): Assert,
    id(ast.Tuple): Tuple,
    id(ast.Call): Call,
    id(ast.keyword): Keyword,
    id(ast.Attribute): Attribute,
    id(ast.Name): Name,
    id(ast.Dict): Dictionary,
    id(ast.List): List,
    id(ast.Str): Str,
    id(ast.Num): Num,
}

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
  if isinstance(op, ast.Sub): return '-'
  if isinstance(op, ast.Mult): return '*'
  if isinstance(op, ast.Div): return '/'
  if isinstance(op, ast.Mod): return '%'
  assert False, "Operator %s not yet supported!" % op

def indent(block):
  if isinstance(block, list):
    block = '\n'.join(str(n) for n in block)
  return '  ' + block.replace('\n', '\n  ')

if __name__ == __file__:
  with open(__file__) as handle:
    print wrap(ast.parse(handle.read()))
