import os
import platform
import re
import sys

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
        name = modname and modname + '.' + name or name
        name = re.sub('^(dist|site)-packages.', '', name)
        modulenames.add(name)

# Sort the module list ignoring case and underscores.
results = list(modulenames)
results.sort(key=lambda n: n.lower().replace('_', ''))
for modname in results:
  print modname

# vim: ts=2 sw=2 et
