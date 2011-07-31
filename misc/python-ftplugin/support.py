# Supporting functions for the Python file type plug-in for Vim.
# Authors:
#  - Peter Odding <peter@peterodding.com>
#  - Bart kroon <bart@tarmack.eu>
# Last Change: July 31, 2011
# URL: https://github.com/tarmack/vim-python-ftplugin

import __builtin__
import os
import platform
import re
import sys

def complete_modules():
  '''
  Find the names of the built-in, binary and source modules available on the
  user's system without executing any Python code except for this function (in
  other words, module name completion is completely safe).
  '''
  # Start with the names of the built-in modules.
  modulenames = set(sys.builtin_module_names)
  # Find the installed binary modules (*.so or *.dll files).
  sharedlibs = '%s/lib/python%s/lib-dynload' % (sys.exec_prefix, sys.version[:3])
  sharedext = platform.system() == 'Windows' and '.dll' or '.so'
  for soname in os.listdir(sharedlibs):
    basename, extension = os.path.splitext(soname)
    if extension.lower() == sharedext:
      modulenames.add(basename)
  # Find the installed source modules (*.py, *.pyc, *.pyo files).
  for root in sys.path:
    scan_modules(root, '', modulenames)
  # Sort the module list ignoring case and underscores.
  for modname in friendly_sort(list(modulenames)):
    print modname

def scan_modules(directory, expr, modulenames):
  if os.path.isdir(directory):
    for name in os.listdir(directory):
      pathname = '%s/%s' % (directory, name)
      if os.path.isdir(pathname):
        if re.match('^[A-Za-z0-9_]+$', name):
          scan_modules(pathname, expr and expr + '.' + name or name, modulenames)
      elif re.search(r'^[A-Za-z0-9_]+\.py[co]?$', name):
        name = os.path.splitext(name)[0]
        if expr:
          name = expr if name == '__init__' else expr + '.' + name
          name = re.sub('^(dist|site)-packages.', '', name)
        modulenames.add(name)

def complete_variables(expr):
  '''
  Use __import__() and dir() to get the functions and/or variables available in
  the given module or submodule.
  '''
  todo = [x for x in expr.split('.') if x]
  done = []
  module = load_module(todo, done)
  subject = module
  while todo:
    try:
      subject = getattr(subject, todo[0])
      done.append(todo.pop(0))
    except AttributeError:
      break
  if subject:
    expr = ('.'.join(done) + '.') if done else ''
    for entry in friendly_sort(dir(subject)):
      print expr + entry

def load_module(todo, done):
  '''
  Find the most specific valid Python module given a tokenized identifier
  expression (e.g. `os.path' for `os.path.islink').
  '''
  path = []
  module = __builtin__
  while todo:
    path.append(todo[0])
    try:
      temp = __import__('.'.join(path))
      if temp.__name__ == '.'.join(path):
        module = temp
      else:
        break
    except ImportError:
      break
    done.append(todo.pop(0))
  return module

def find_module_path(name):
  '''
  Look for a Python module on the module search path (used for "gf" and
  searching in imported modules).
  '''
  fname = name.replace('.', '/')
  for directory in sys.path:
    scriptfile = directory + '/' + fname + '.py'
    if os.path.isfile(scriptfile):
      print scriptfile
      break

def friendly_sort(identifiers):
  '''
  Sort identifiers ignoring case and underscores (human friendly sorting).
  '''
  identifiers.sort(key=lambda n: n.lower().replace('_', ''))
  return identifiers

# vim: ts=2 sw=2 sts=2 et
