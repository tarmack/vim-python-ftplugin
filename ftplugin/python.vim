" Vim file type plug-in
" Language: Python
" Authors:
"  - Peter Odding <peter@peterodding.com>
"  - Bart kroon <bart@tarmack.eu>
" Last Change: July 30, 2011
" URL: https://github.com/tarmack/Vim-Python-FT-Plugin
" Uses: http://pypi.python.org/pypi/pyflakes
" Inspired By: http://vim.wikia.com/wiki/Python_-_check_syntax_and_run_script

" Define configuration defaults. {{{1

if !exists('g:python_syntax_fold')
  let g:python_syntax_fold = 1
endif

if !exists('g:python_fold_docstrings')
  let g:python_fold_docstrings = 1
endif

if !exists('g:python_docstring_in_foldtext')
  let g:python_docstring_in_foldtext = 1
endif

if !exists('g:python_check_syntax')
  let g:python_check_syntax = 1
endif

if !exists('g:python_autoindent')
  let g:python_autoindent = 1
endif

" Enable syntax folding. {{{1
if g:python_syntax_fold
  setlocal foldmethod=syntax
  " Match all docstrings that span more than one line.
  if g:python_fold_docstrings
    syn region  pythonFoldedString start=+[Bb]\=[Rr]\=[Uu]\=\z("""\|'''\)+ end=+.*\z1+ fold transparent contained
          \ containedin=pythonString,pythonUniString,pythonUniRawString,pythonRawString
  endif
  " Match all function and class definitions. 
  syntax region  pythonFunctionFold start="^\(\s*\)\%(def\|class\)\s\+\_.\{-\}:\%(\s*\|\s*#.*\)\n\%(\s*\n\)*\z(\1\s\+\)"
        \ skip="\%(^\s*\n\|^\z1.*\|^\s*#.*\)"
        \ end="^\ze\%(\%(\z1.*\)\@!\|\z1\)" fold transparent
  " Match all Comments that span more than one line.
  syntax region  pythonCommentFold start="^\z(\s*\)#\%(!\|\s*-\*-\)\@!.*$" 
        \ end="^\%(\z1\#.*$\)\@!" fold contains=ALLBUT,pythonCommentFold
endif

" Alternate fold text generating function. {{{1
setlocal foldtext=python_ftplugin#fold_text()

" Create variables for Python syntax check. {{{1
if g:python_check_syntax

  if !exists('g:python_makeprg') && !exists('g:python_error_format')
    if executable('pyflakes')
      let g:python_makeprg = 'pyflakes "%:p"'
      let g:python_error_format = '%A%f:%l: %m,%C%s,%Z%p^,%f:%l: %m'
    else
      let g:python_makeprg = 'python -c "import py_compile,sys; sys.stderr = sys.stdout; py_compile.compile(r''%'')"'
      let g:python_error_format = "SyntaxError: ('%m'\\, ('%f'\\, %l\\, %c\\, '%s'))"
    endif
  endif

  " Enable plug-in for current buffer without reloading? {{{1
  " Enable automatic command to check for syntax errors when saving buffers.
  augroup PluginFileTypePython
    autocmd! BufWritePost <buffer> call python_ftplugin#syntax_check()
  augroup END

endif

let g:loaded_python_ftplugin = 1

" vim: ts=2 sw=2 et
