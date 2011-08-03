# Vim file type plug-in for the Python programming language

The Python file type plug-in for Vim helps you while developing in Python by providing the following features:

 * Automatic syntax checking using [pyflakes] [pyflakes].
 * Syntax based folding for classes, functions, comment blocks and multi line strings (the fold text includes the docstring if found).
 * You can use `gf` to jump to imported files (searches the Python path).
 * You can search imported files using mappings such as `[i`.
 * Control-X Control-U completes all available module names.
   * Module name completion starts automatically after typing `import` or `from` (automatic completion can be disabled if you find it is too intrusive).
 * Control-X Control-O completes variable names, for example after `os` or `os.` it would complete `os.path` (and others). *Be aware that this imports modules to perform introspection and assumes that importing a module does not have serious side effects (although it might, however it shouldn't).*
   * You can enable automatic variable completion after typing a dot or if you type a space after `import` on a `from <module> import <variable>` line. (*this is not enabled by default because of the side effect issue mentioned above*).

## Installation

To use this file, simply add it to your `$VIM/ftplugin` directory. 

To use the syntax check, please make sure pyflakes is installed. It can be found in most Linux distributions.

To enable folds for classes and functions defined without leading whitespace, make sure your Python syntax file uses a match rather than a keyword statement for the def and class keywords.

Change the line to say something like:

    syn match  [group]  "\<\%(def\|class\)\>" [options]

I can recommend you [Dmitry Vasiliev's] [extsyntax] adaptation of the default Python syntax file. In this file you will need to replace the following line:

    syn keyword  pythonStatement  def class nextgroup=pythonFunction skipwhite

with:

    syn match  pythonStatement  "\<\%(def\|class\)\>" nextgroup=pythonFunction skipwhite

## Options

All options are enabled by default. To disable an option do:

    let g:OPTION_NAME = 0

### The `g:python_syntax_fold` option

Enables syntax based folding for classes, functions and comments.

### The `g:python_fold_strings` option

Enables syntax based folding for strings that span multiple lines.

### The `g:python_docstring_in_foldtext` option

To display the docstring of a class/function in the fold text.

### The `g:python_check_syntax` option

Enables automatic syntax checking when saving Python buffers. This uses [pyflakes] [pyflakes] when available but falls back on the standard Python compiler for syntax checking.

### The `g:python_auto_complete_modules` option

Controls automatic completion of module names after typing `import<Space>` or `from<Space>`. Enabled by default.

### The `g:python_auto_complete_variables` option

Controls automatic completion of variables after typing a dot or `from <module> import<Space>`. Disabled by default.

## Contact

If you have questions, bug reports, suggestions, etc. you can contact Bart at <bart@tarmack.eu> or Peter at <peter@peterodding.com>. The latest version is available at <http://peterodding.com/code/vim/python-ftplugin> and <https://github.com/tarmack/vim-python-ftplugin>.

## License

This software is licensed under the [MIT license](http://en.wikipedia.org/wiki/MIT_License).
© 2011 Peter Odding &lt;<peter@peterodding.com>&gt; and Bart Kroon &lt;<bart@tarmack.eu>&gt;.


[pyflakes]: http://pypi.python.org/pypi/pyflakes
[extsyntax]: http://www.vim.org/scripts/script.php?script_id=790
