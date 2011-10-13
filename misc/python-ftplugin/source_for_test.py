'''
File containing code snippets for testing purposes.
'''

global_var = 42
var1, var2 = 1, 2
some_string = ''
shadowed = ''

assert shadowed
assert var1, 'var1 is empty.'

@wraps('something')
class DecoratedClass(object):

  def __init__(self, *args, **kwargs):
    self.some_attr = foo(args) if args else None

  @property
  def attrs(self):
    results = []
    for obj in self.some_attr or []:
      if obj:
        results.extend(obj)
    return results or 'None'


class ExampleClass:
  class_variable = []

  def __init__(self, init_arg, kws=[], kw_indirect=some_string):
    shadowed = []
    print global_var, shadowed, kw_indirect, kws
    if init_arg:
      def fun_inside_if(): pass
    elif 1:
      def fun_inside_elif_1(): pass
    elif 2:
      def fun_inside_elif_2(): pass
    else:
      def fun_inside_else(): pass

  def a(self, example_argument):
    for i in xrange(5):
      print example_argument
    while True:
      def inside_while(): pass

  def b(self):
    def nested():
      print 5
    nested()

cl = ExampleClass('', kwa={}, kw_indirect='')
cl

cl.foo_attr = ''

def newlist():
  return []

l = newlist()
l
def newmaps():
  return set(), dict()

s, d = newmaps()
s
d

nums = [x for x in [1, 2, 3]]
nums_times_2 = [x * 2 for x in range(8) if x in nums]
nums_string = ''.join((num for num in nums if num >= 2))

@func_decor
def bar():
    return

if True:
  variant = []
else:
  variant = ''
print variant

def func(blaat):
  s2 = 0
  print dir(s2)

func(set())
func(list())

