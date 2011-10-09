#!/usr/bin/env python

import os
import ast
import sys
import typesystem

if len(sys.argv) > 1:
  with open(sys.argv[1]) as handle:
    print typesystem.wrap(ast.parse(handle.read()))
else:
  with os.popen('locate "*.py" 2>/dev/null') as pipe:
    for line in pipe:
      filename = line.strip()
      if os.path.isfile(filename):
        with open(filename) as handle:
          try:
            print "Parsing", filename, ".."
            tree = ast.parse(handle.read())
          except:
            pass
          else:
            try:
              print "Wrapping AST .."
              our_tree = typesystem.wrap(tree)
            except Exception, e:
              print "Failed to wrap AST: %s" % e
              sys.exit(1)
            try:
              print "Dumping AST .."
              print our_tree
            except Exception, e:
              print "Failed to dump AST: %s" % e
              sys.exit(1)
