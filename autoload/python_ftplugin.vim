" Vim autoload script
" Authors:
"  - Peter Odding <peter@peterodding.com>
"  - Bart kroon <bart@tarmack.eu>
" Last Change: August 7, 2011
" URL: https://github.com/tarmack/vim-python-ftplugin

let g:python_ftplugin_version = '0.5.10'
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
    return s:find_start('module')
  else
    " TODO Always scan current directory?
    let starttime = xolox#misc#timer#start()
    let candidates = s:add_modules(a:base, [])
    call xolox#misc#timer#stop("python.vim %s: Found %s completion candidates in %s.", g:python_ftplugin_version, len(candidates), starttime)
    return candidates
  endif
endfunction

function! s:find_module(base) " {{{1
  let todo = []
  let fromstr = matchstr(getline('.'), '\<\(from\s\+\)\@<=[A-Za-z0-9_.]\+\(\s\+import\([A-Za-z0-9_,]\s*\)*\)\@=')
  let from = split(fromstr, '\.')
  call extend(todo, from)
  call extend(todo, split(a:base, '\.'))
  let done = []
  let node = python_ftplugin#get_modules([], s:module_completion_cache)
  while !empty(todo)
    if has_key(node, todo[0])
      let name = remove(todo, 0)
      call add(done, name)
      let node = python_ftplugin#get_modules(done, node[name])
    else
      break
    endif
  endwhile
  if len(from) > len(done)
    let node = {}
  endif
    let done = done[len(from) :]
  return [todo, done, node]
endfunction

function! s:find_start(type) " {{{2
  let prefix = getline('.')[0 : col('.')-2]
  let ident = matchstr(prefix, '[A-Za-z0-9_.]\+$')
  call xolox#misc#msg#debug("python.vim %s: Completing %s `%s'.", g:python_ftplugin_version, a:type, ident)
  return col('.') - len(ident) - 1
endfunction

function! python_ftplugin#get_modules(base, node) " {{{2
  let start_load = xolox#misc#timer#start()
  call xolox#misc#msg#info("python.vim %s: Caching list of installed Python modules ..", g:python_ftplugin_version)

  call s:load_python_script()
  redir => listing
  silent python complete_modules(vim.eval("join(a:base, '.')"))
  redir END
  let lines = split(listing, '\n')
  call xolox#misc#timer#stop("python.vim %s: Found %i module names in %s.", g:python_ftplugin_version, len(lines), start_load)
  let start_tree = xolox#misc#timer#start()
  for token in lines
    if !has_key(a:node, token)
      let a:node[token] = {}
    endif
  endfor
  call xolox#misc#timer#stop("python.vim %s: Build tree of module names in %s.", g:python_ftplugin_version, start_tree)
  return a:node
endfunction

let s:module_completion_cache = {}

function! s:load_python_script() " {{{2
  if !exists('s:python_script_loaded')
    python import vim
    let scriptfile = s:profile_dir . '/misc/python-ftplugin/support.py'
    execute 'pyfile' fnameescape(scriptfile)
    let s:python_script_loaded = 1
  endif
endfunction

function! python_ftplugin#complete_variables(findstart, base) " {{{1
  if a:findstart
    return s:find_start('variable')
  else
    let starttime = xolox#misc#timer#start()
    let candidates = []
    if s:do_variable_completion(a:base[-1:])
      let from = matchstr(getline('.'), '\<\(from\s\+\)\@<=[A-Za-z0-9_.]\+\(\s\+import\s\+\([A-Za-z0-9_,]\s*\)*\)\@=')
      if empty(from)
        let base = a:base
      else
        let base = from . '.' . a:base
      endif
      call s:load_python_script()
      redir => listing
      silent python complete_variables(vim.eval('base'))
      redir END
      call extend(candidates, split(listing, '\n'))
      if !empty(from)
        call map(candidates, 'v:val[len(from) + 1 :]')
      endif
    endif
    let candidates = s:add_modules(a:base, candidates)
    call xolox#misc#timer#stop("python.vim %s: Found %s completion candidates in %s.", g:python_ftplugin_version, len(candidates), starttime)
    return candidates
  endif
endfunction

function! s:add_modules(base, candidates) " {{{1
  if s:do_module_completion(a:base[-1:])
    let [todo, done, node] = s:find_module(a:base)
    for key in keys(node)
      call add(a:candidates, join(done + [key], '.'))
    endfor
    let pattern = '^' . xolox#misc#escape#pattern(a:base)
    call filter(a:candidates, 'v:val =~# pattern')
  endif
  return sort(a:candidates, 's:friendly_sort')
endfunction

function! s:friendly_sort(a, b) " {{{1
  let a = substitute(a:a, '_', '', 'g')
  let b = substitute(a:b, '_', '', 'g')
  return a < b ? -1 : a > b ? 1 : 0
endfunction

function! python_ftplugin#auto_complete(chr) " {{{1
  if xolox#misc#option#get('python_auto_complete_variables', 0)
        \ && s:do_variable_completion(a:chr)
    " Automatic completion of canonical variable names.
    let type = 'variable'
    let result = "\<C-x>\<C-o>\<C-n>"
  elseif xolox#misc#option#get('python_auto_complete_modules', 1)
        \ && s:do_module_completion(a:chr)
    " Automatic completion of canonical module names,
    " only when variable name completion is not available.
    let type = 'module'
    let result = "\<C-x>\<C-u>\<C-n>"
  endif
  if exists('result')
    call xolox#misc#msg#debug("python.vim %s: %s %s completion.", g:python_ftplugin_version, pumvisible() ? "Continuing" : "Starting", type)
    " Make sure Vim opens the menu but doesn't enter the first match.
    let b:python_cot_save = &completeopt
    set cot+=menu cot+=menuone cot+=longest
    " Restore &completeopt after completion.
    augroup PluginFileTypePython
      autocmd! CursorHold,CursorHoldI <buffer> call s:restore_completeopt()
    augroup END
    " Enter character and start completion.
    return a:chr . result
  endif
  return a:chr
endfunction

function! s:do_module_completion(chr) " {{{1
  " Complete module names when at the end of a from XX import YY line.
  " But do check for comma separators.
  if search('\<from\s\+[A-Za-z0-9_.]\+\.\@<!\s\+import\(\s*[A-Za-z0-9_]\+\s*,\)*\s*[A-Za-z0-9_]*\%#', 'bcn', line('.'))
    if a:chr == ' ' && !search('\(\<import\|,\)\s*\%#', 'bcn', line('.'))
      return 0
    elseif a:chr == '.'
      return 0
    endif
    return 1

  elseif search('\<from\s*\(\s\+[A-Za-z0-9_.]*\s\@!\)\=\%#', 'bcn', line('.'))
    if a:chr == ' ' && search('\<from\s\+[A-Za-z0-9_.]\+\s*\%#', 'bcn', line('.'))
      return 0
    endif
    return 1

  elseif search('\<import\s*\(\s\+[A-Za-z0-9_.]*\s*,\)*\s*[A-Za-z0-9_.]*\s\@!\%#', 'bcn', line('.'))
        \ && !search('\<from.\{-}import.\{-}\%#', 'bcn', line('.'))
    if a:chr == ' ' && !search('\(import\|,\)\s*\%#', 'bcn', line('.'))
      return 0
    endif
    return 1
  endif
  return 1
endfunction

function! s:do_variable_completion(chr) " {{{1
  if search('\<from\s\+[A-Za-z0-9_.]\+\.\@<!\s\+import\(\s*[A-Za-z0-9_]\+\s*,\)*\s*[A-Za-z0-9_]*\%#', 'bcn', line('.'))
    if a:chr == ' ' && !search('\(\<import\|,\)\s*\%#', 'bcn', line('.'))
      return 0
    elseif a:chr == '.'
      return 0
    endif
    return 1

  elseif a:chr != ' '
        \ && search('\<from\@!.\{-}import\s\+[A-Za-z0-9_.].\@!\%#', 'bcn', line('.'))
        \ && search('\<\(from\|import\)\s*[A-Za-z0-9_.]*\s\@!\%#', 'bcn', line('.')) 
    return 1
  elseif a:chr != ' '
        \ && search('\<from\s\+[A-Za-z0-9_.]\+\s\+import\(\s*[A-Za-z0-9_]\+\s*,\)*\s*[A-Za-z0-9_]*\s\@!\%#', 'bcn', line('.'))
    return 1

  elseif search('\<\(from\|import\).*\%#', 'bcn', line('.'))
    return 0
  endif
  return 1
endfunction

function! s:restore_completeopt() " {{{1
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
