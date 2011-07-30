" Vim autoload script
" Authors:
"  - Peter Odding <peter@peterodding.com>
"  - Bart kroon <bart@tarmack.eu>
" Last Change: July 30, 2011
" URL: https://github.com/tarmack/Vim-Python-FT-Plugin

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
    if g:python_docstring_in_foldtext
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
  if g:python_check_syntax
    let progname = matchstr(g:python_makeprg, '^\w\+')
    if !executable(progname)
      let message = "Python file type plug-in: The configured syntax checker"
      let message .= " doesn't seem to be available! I'm disabling"
      let message .= " automatic syntax checking for Python scripts."
      let g:python_check_syntax = 0
      echoerr message
    else
      let mp_save = &makeprg
      let efm_save = &errorformat
      try
        let &makeprg = g:python_makeprg
        let &errorformat = g:python_error_format
        let winnr = winnr()
        redraw
        call xolox#misc#msg#info('Checking Python script syntax ..')
        execute 'silent make!'
        redraw
        echo ''
        cwindow
        execute winnr . 'wincmd w'
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
