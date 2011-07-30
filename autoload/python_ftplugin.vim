" Vim autoload script
" Authors:
"  - Peter Odding <peter@peterodding.com>
"  - Bart kroon <bart@tarmack.eu>
" Last Change: July 30, 2011
" URL: https://github.com/tarmack/vim-python-ftplugin

let g:python_ftplugin_version = '0.4.5'
let s:profile_dir = expand('<sfile>:p:h:h')

function! python_ftplugin#fold_text() " {{{1
  let line = getline(v:foldstart)
  if line =~ '^\s*#'
    " Comment block.
    let text = ['#']
    for line in getline(v:foldstart, v:foldend)
      call extend(text, split(line)[1:])
    endfor
  else
    let text = []
    let lnum = v:foldstart
    if line =~ '^\s*\(def\|class\)\>'
      " Class or function body.
      let line = xolox#misc#str#trim(line)
      call add(text, substitute(line, ':$', '', ''))
      " Fall through.
      let lnum += 1
    endif
    if xolox#misc#option#get('python_docstring_in_foldtext', 1)
      " Show joined lines from docstring in fold text (can be slow).
      let haystack = join(getline(lnum, v:foldend))
      let docstr = matchstr(haystack, '^\_s*\("""\|''\{3}\)\zs\_.\{-}\ze\1')
      if docstr =~ '\S'
        if lnum > v:foldstart
          call add(text, '-')
        endif
        call extend(text, split(docstr))
      endif
    else
      " Show first actual line of docstring.
      for line in getline(lnum, lnum + 5)
        if line =~ '\w'
          call add(text, xolox#misc#str#trim(line))
          break
        endif
      endfor
    endif
  endif
  let numlines = v:foldend - v:foldstart + 1
  let format = "+%s %" . len(line('$')) . "d lines: %s "
  return printf(format, v:folddashes, numlines, join(text))
endfunction

function! python_ftplugin#syntax_check() " {{{1
  if xolox#misc#option#get('python_check_syntax', 1)
    " Enable the user to override python_makeprg and python_error_format.
    let makeprg = xolox#misc#option#get('python_makeprg', '')
    let error_format = xolox#misc#option#get('python_error_format', '')
    " Use reasonable defaults for python_makeprg and python_error_format.
    if makeprg == '' || error_format == ''
      " Use pyflakes when available, fall-back to the Python compiler.
      if executable('pyflakes')
        let default_makeprg = 'pyflakes "%:p"'
        let default_error_format = '%A%f:%l: %m,%C%s,%Z%p^,%f:%l: %m'
      else
        let default_makeprg = 'python -c "import os, sys, py_compile; sys.stderr = sys.stdout; py_compile.compile(r''%:p''); os.path.isfile(''%:pc'') and os.unlink(''%:pc'')"'
        let default_error_format = "SyntaxError: ('%m'\\, ('%f'\\, %l\\, %c\\, '%s'))"
      endif
    endif
    " Make sure the syntax checker is installed.
    let progname = matchstr(makeprg, '^\S\+')
    if !executable(progname)
      let message = "python.vim %s: The configured syntax checker"
      let message .= " doesn't seem to be available! I'm disabling"
      let message .= " automatic syntax checking for Python scripts."
      if exists('b:python_makeprg') && b:python_makeprg == makeprg
        let b:python_check_syntax = 0
      else
        let g:python_check_syntax = 0
      endif
      call xolox#misc#msg#warn(message)
    else
      let mp_save = &makeprg
      let efm_save = &errorformat
      try
        let &makeprg = makeprg
        let &errorformat = error_format
        let winnr = winnr()
        call xolox#misc#msg#info('python.vim %s: Checking Python script syntax ..', g:python_ftplugin_version)
        execute 'silent make!'
        cwindow
        if winnr() != winnr
          let w:quickfix_title = 'Issues reported by ' . progname
          execute winnr . 'wincmd w'
        endif
        redraw
        echo ''
      finally
        let &makeprg = mp_save
        let &errorformat = efm_save
      endtry
    endif
  endif
endfunction

function! python_ftplugin#jump(motion) range " {{{1
    let cnt = v:count1
    let save = @/    " save last search pattern
    mark '
    while cnt > 0
    silent! exe a:motion
    let cnt = cnt - 1
    endwhile
    call histdel('/', -1)
    let @/ = save    " restore last search pattern
endfun

function! python_ftplugin#include_expr(fname) " {{{1
  redir => output
  silent python <<EOF
import os, sys, vim
fname = vim.eval('a:fname').replace('.', '/')
for directory in sys.path:
  scriptfile = directory + '/' + fname + '.py'
  if os.path.exists(scriptfile):
    print scriptfile
    break
EOF
  redir END
  return xolox#misc#str#trim(output)
endfunction

function! python_ftplugin#complete_modules(findstart, base) " {{{1
  if a:findstart
    let prefix = getline('.')[0 : col('.')-2]
    let ident = matchstr(prefix, '[A-Za-z0-9_.]\+$')
    let col = col('.') - len(ident) - 1
    return col
  else
    if !exists('s:modulenames')
      let starttime = xolox#misc#timer#start()
      call xolox#misc#msg#info("python.vim %s: Caching list of installed Python modules ..", g:python_ftplugin_version)
      redir => listing
        let scriptfile = s:profile_dir . '/misc/python-ftplugin/modulenames.py'
        silent execute 'pyfile' fnameescape(scriptfile)
      redir END
      let s:modulenames = split(listing, '\n')
      call xolox#misc#timer#stop("python.vim %s: Found %i module names in %s.", g:python_ftplugin_version, len(s:modulenames), starttime)
    endif
    let pattern = '^' . a:base
    return filter(copy(s:modulenames), 'v:val =~ pattern')
  endif
endfunction
