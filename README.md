# Vim filetype plugin for the Python programming language.

This file helps you while developing in Python. It uses 
[pyflakes](http://pypi.python.org/pypi/pyflakes) to check for syntax errors
when saving the file. This file also provides you with syntax based folding for
functions and classes. The fold text includes the docstring if it is found.


## Options.

All options are enabled by default. To disable an option do:
    let OPTION_NAME = 0

### Option names:
For syntax based folding:
  python_syntax_fold

For folding of docstrings and multiline strings:
  python_fold_docstrings

For docstring display in function fold text:
  python_docstring_in_foldtext

For syntax checking on buffer write:
  python_check_syntax


## Installation.

To use this file, simply add it to your $VIM/after/filetype directory. 

To use the syntax check, please make sure pyflakes is installed. It can be
found in most distributions.

To enable folds for classes and functions defined without leading whitespace,
make sure your Python syntax file uses a match rather than a keyword statement
for the def and class keywords.

Change the line to say something like:
    syn match  [group]  "\<\%(def\|class\)\>" [options]

I can recommend you [Dmitry Vasiliev's](http://www.vim.org/scripts/script.php?script_id=790)
adaptation of the default Python syntax file.
In this file you will need to replace the following line:
    syn keyword  pythonStatement  def class nextgroup=pythonFunction skipwhite
with:
    syn match  pythonStatement  "\<\%(def\|class\)\>" nextgroup=pythonFunction skipwhite

