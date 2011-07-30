" Vim autoload script
" Authors:
"  - Peter Odding <peter@peterodding.com>
"  - Bart kroon <bart@tarmack.eu>
" Last Change: July 31, 2011
" URL: https://github.com/tarmack/vim-python-ftplugin

let g:python_ftplugin_version = '0.5.3'
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
        let makeprg = 'pyflakes "%:p"'
        let error_format = '%A%f:%l: %m,%C%s,%Z%p^,%f:%l: %m'
      else
        let makeprg = 'python -c "import os, sys, py_compile; sys.stderr = sys.stdout; py_compile.compile(r''%:p''); os.path.isfile(''%:pc'') and os.unlink(''%:pc'')"'
        let error_format = "SyntaxError: ('%m'\\, ('%f'\\, %l\\, %c\\, '%s'))"
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
      call xolox#misc#msg#warn(message, g:python_ftplugin_version)
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
  call s:load_python_script()
  redir => output
  silent python find_module_path(vim.eval('a:fname'))
  redir END
  return xolox#misc#str#trim(output)
endfunction

function! python_ftplugin#complete_modules(findstart, base) " {{{1
  if a:findstart
    return s:find_start()
  else
    " TODO Always scan current directory?
    if !exists('s:modulenames')
      let starttime = xolox#misc#timer#start()
      call xolox#misc#msg#info("python.vim %s: Caching list of installed Python modules ..", g:python_ftplugin_version)
      call s:load_python_script()
      redir => listing
      silent python complete_modules()
      redir END
      let s:modulenames = split(listing, '\n')
      call xolox#misc#timer#stop("python.vim %s: Found %i module names in %s.", g:python_ftplugin_version, len(s:modulenames), starttime)
    endif
    let pattern = '^' . a:base
    return filter(copy(s:modulenames), 'v:val =~ pattern')
  endif
endfunction

function! s:find_start()
  let prefix = getline('.')[0 : col('.')-2]
  let ident = matchstr(prefix, '[A-Za-z0-9_.]\+$')
  return col('.') - len(ident) - 1
endfunction

function! s:load_python_script()
  if !exists('s:python_script_loaded')
    python import vim
    let scriptfile = s:profile_dir . '/misc/python-ftplugin/support.py'
    execute 'pyfile' fnameescape(scriptfile)
    let s:python_script_loaded = 1
  endif
endfunction

function! python_ftplugin#complete_variables(findstart, base) " {{{1
  if a:findstart
    return s:find_start()
  else
    call s:load_python_script()
    redir => listing
    silent python complete_variables(vim.eval('a:base'))
    redir END
    let variables = split(listing, '\n')
    let pattern = '^' . a:base
    return filter(variables, 'v:val =~ pattern')
  endif
endfunction

function! python_ftplugin#auto_complete(chr) " {{{1
  if a:chr == ' ' && xolox#misc#option#get('python_auto_complete_modules', 1)
          \ && search('\<\(from\|import\)\%#', 'bc', line('.'))
    let result = "\<C-x>\<C-u>\<Down>"
  elseif a:chr == '.' && xolox#misc#option#get('python_auto_complete_variables', 0)
          \ && search('[A-Za-z0-9_]\%#', 'bc', line('.'))
          \ && !(pumvisible() && getline('.') =~ '\<import\>')
    " The last condition ensures that variable completion doesn't trigger when
    " we are currently inside module name completion.
    let result = "\<C-x>\<C-o>\<Down>"
  endif
  if exists('result')
    " Make sure Vim opens the menu but doesn't enter the first match.
    let b:python_cot_save = &completeopt
    set completeopt+=menu,menuone,longest
    " Restore &completeopt after completion.
    augroup PluginFileTypePython
      autocmd! CursorHold,CursorHoldI <buffer> call s:restore_completeopt()
    augroup END
    " Enter character and start completion.
    return a:chr . result
  endif
  return a:chr
endfunction

function! s:restore_completeopt()
  " Restore the original value of &completeopt.
  if exists('b:python_cot_save')
    let &completeopt = b:python_cot_save
    unlet b:python_cot_save
  endif
  " Disable the automatic command that called us.
  augroup PluginFileTypePython
    autocmd! CursorHold,CursorHoldI <buffer>
  augroup END
endfunction
