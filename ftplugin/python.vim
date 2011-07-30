" Vim file type plug-in
" Language: Python
" Authors:
"  - Peter Odding <peter@peterodding.com>
"  - Bart kroon <bart@tarmack.eu>
" Last Change: July 30, 2011
" URL: https://github.com/tarmack/Vim-Python-FT-Plugin
" Uses: http://pypi.python.org/pypi/pyflakes
" Inspired By: http://vim.wikia.com/wiki/Python_-_check_syntax_and_run_script

if exists('b:did_ftplugin')
  finish
else
  let b:did_ftplugin = 1
endif

" Buffer local options. {{{1

" A list of commands that undo buffer local changes made below.
let s:undo_ftplugin = []

" Make sure "#" doesn't jump to the start of the line.
setlocal cinkeys-=0# indentkeys-=0#
call add(s:undo_ftplugin, 'setlocal cinkeys< indentkeys<')

" Follow import statements.
setlocal include=\s*\\(from\\\|import\\)
setlocal includeexpr=python_ftplugin#include_expr(v:fname)
setlocal suffixesadd=.py
call add(s:undo_ftplugin, 'setlocal include< includeexpr< suffixesadd<')

" Enable formatting of comments.
setlocal comments=b:#
setlocal commentstring=#%s
call add(s:undo_ftplugin, 'setlocal comments< commentstring<')

" Ignore bytecode files during completion.
set wildignore+=*.pyc wildignore+=*.pyo
call add(s:undo_ftplugin, 'setlocal wildignore<')

" Alternate fold text generating function.
setlocal foldtext=python_ftplugin#fold_text()
call add(s:undo_ftplugin, 'setlocal foldtext<')

" Alternate fold text generating function.
setlocal completefunc=python_ftplugin#complete_modules
call add(s:undo_ftplugin, 'setlocal completefunc<')

" File open/save dialog filename filter on Windows.
if has('gui_win32') && !exists('b:browsefilter')
  let b:browsefilter = "Python Files (*.py)\t*.py\nAll Files (*.*)\t*.*\n"
  call add(s:undo_ftplugin, 'unlet! b:browsefilter')
endif

" Mappings to jump between classes and functions. {{{1
nnoremap <silent> <buffer> ]] :call python_ftplugin#jump('/^\(class\\|def\)')<cr>
nnoremap <silent> <buffer> [[ :call python_ftplugin#jump('?^\(class\\|def\)')<cr>
nnoremap <silent> <buffer> ]m :call python_ftplugin#jump('/^\s*\(class\\|def\)')<cr>
nnoremap <silent> <buffer> [m :call python_ftplugin#jump('?^\s*\(class\\|def\)')<cr>
call add(s:undo_ftplugin, 'nunmap <buffer> ]]')
call add(s:undo_ftplugin, 'nunmap <buffer> [[')
call add(s:undo_ftplugin, 'nunmap <buffer> ]m')
call add(s:undo_ftplugin, 'nunmap <buffer> [m')

" Enable syntax folding. {{{1
if xolox#misc#option#get('python_syntax_fold', 1)
  setlocal foldmethod=syntax
  call add(s:undo_ftplugin, 'setlocal foldmethod<')
  " Match docstrings that span more than one line.
  if xolox#misc#option#get('python_fold_docstrings', 1)
    syn region  pythonFoldedString start=+[Bb]\=[Rr]\=[Uu]\=\z("""\|'''\)+ end=+.*\z1+ fold transparent contained
          \ containedin=pythonString,pythonUniString,pythonUniRawString,pythonRawString
  endif
  " Match function and class definitions. 
  syntax region  pythonFunctionFold start="^\(\s*\)\%(def\|class\)\s\+\_.\{-\}:\%(\s*\|\s*#.*\)\n\%(\s*\n\)*\z(\1\s\+\)"
        \ skip="\%(^\s*\n\|^\z1.*\|^\s*#.*\)"
        \ end="^\ze\%(\%(\z1.*\)\@!\|\z1\)" fold transparent
  " Match comments that span more than one line.
  syntax region  pythonCommentFold start="^\z(\s*\)#\%(!\|\s*-\*-\)\@!.*$" 
        \ end="^\%(\z1\#.*$\)\@!" fold contains=ALLBUT,pythonCommentFold
endif

" Automatic syntax checking. {{{1
if xolox#misc#option#get('python_check_syntax', 1)
  if !exists('g:python_makeprg') && !exists('g:python_error_format')
    if executable('pyflakes')
      let g:python_makeprg = 'pyflakes "%:p"'
      let g:python_error_format = '%A%f:%l: %m,%C%s,%Z%p^,%f:%l: %m'
    else
      let g:python_makeprg = 'python -c "import py_compile,sys; sys.stderr = sys.stdout; py_compile.compile(r''%'')"'
      let g:python_error_format = "SyntaxError: ('%m'\\, ('%f'\\, %l\\, %c\\, '%s'))"
    endif
  endif
  augroup PluginFileTypePython
    autocmd! BufWritePost <buffer> call python_ftplugin#syntax_check()
    call add(s:undo_ftplugin, 'autocmd! PluginFileTypePython BufWritePost <buffer>')
  augroup END
endif

" Let Vim know how to disable the plug-in.
call map(s:undo_ftplugin, "'execute ' . string(v:val)")
let b:undo_ftplugin = join(s:undo_ftplugin, ' | ')
unlet s:undo_ftplugin

let g:loaded_python_ftplugin = 1

" vim: ts=2 sw=2 et
