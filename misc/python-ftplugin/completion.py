# Completion functions for the Python file type plug-in for Vim.
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
  path = expr.split('.')
  module = find_one_module(path)
  if module:
    for entry in friendly_sort(dir(module)):
      print '.'.join(path + [entry])

def find_one_module(path):
  while path:
    try:
      return __import__('.'.join(path))
    except ImportError:
      if path:
        path.pop()

def friendly_sort(identifiers):
  identifiers.sort(key=lambda n: n.lower().replace('_', ''))
  return identifiers

# vim: ts=2 sw=2 et
