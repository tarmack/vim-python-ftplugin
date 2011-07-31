# Supporting functions for the Python file type plug-in for Vim.
# Authors:
#  - Peter Odding <peter@peterodding.com>
#  - Bart kroon <bart@tarmack.eu>
# Last Change: July 31, 2011
# URL: https://github.com/tarmack/vim-python-ftplugin

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
  todo = [(p, None) for p in sys.path]
  while todo:
    directory, modname = todo.pop(0)
    if os.path.isdir(directory):
      for entry in os.listdir(directory):
        pathname = '%s/%s' % (directory, entry)
        if os.path.isdir(pathname):
          if re.match('^[A-Za-z0-9_]+$', entry):
            todo.append((pathname,
                modname and modname + '.' + entry or entry))
        elif re.search(r'^[A-Za-z0-9_]+\.py[co]?$', entry):
          name = os.path.splitext(entry)[0]
          if modname:
            if name == '__init__':
              name = ''
            else:
              name = '.' + name
            name = modname + name
          name = re.sub('^(dist|site)-packages.', '', name)
          modulenames.add(name)

  # Sort the module list ignoring case and underscores.
  for modname in friendly_sort(list(modulenames)):
    print modname

def complete_variables(expr):
  '''
  Use __import__() and dir() to get the functions and/or variables available in
  the given module or submodule.
  '''
  path = expr.split('.')
  module = load_module(path)
  if module:
    for entry in friendly_sort(dir(module)):
      print '.'.join(path + [entry])

def load_module(path):
  '''
  Find the most specific valid Python module given a tokenized identifier
  expression (e.g. `os.path' for `os.path.islink').
  '''
  while  path:
    try:
      return __import__('.'.join(path))
    except ImportError:
      if path:
        path.pop()

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
