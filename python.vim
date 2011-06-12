" Vim file type plug-in
" Language: Python
" Maintainer: Peter Odding <peter@peterodding.com> (syntax check)
" Maintainer: Bart kroon <bart@tarmack.eu> (folding)
" Last Change: February 19, 2011
" URL: https://github.com/tarmack/Vim-Python-FT-Plugin
" Uses: http://pypi.python.org/pypi/pyflakes
" Inspired By: http://vim.wikia.com/wiki/Python_-_check_syntax_and_run_script
"
" Options:
"
" All options are enabled by default. To disable an option do:
"   let OPTION_NAME = 0
"
" Option names:
"   For syntax based folding:
"     python_syntax_fold
"
"   For folding of docstrings and multiline strings:
"     python_fold_docstrings
"
"   For docstring display in function fold text:
"     python_docstring_in_foldtext
"
"   For syntax checking on buffer write:
"     python_check_syntax
" 
" Define configuration defaults. {{{1

if !exists("python_syntax_fold")
  let python_syntax_fold = 1
endif
if !exists("python_fold_docstrings")
  let python_fold_docstrings = 1
endif
if !exists("python_docstring_in_foldtext")
  let python_docstring_in_foldtext = 1
endif
if !exists('python_check_syntax')
	let python_check_syntax = 1
endif


" Set folding to syntax. {{{1
if exists("python_syntax_fold") && python_syntax_fold
  setlocal foldmethod=syntax

  " Match all docstrings that span more than one line.
  if exists("python_fold_docstrings") && python_fold_docstrings
    syn region  pythonStringFold  start=+[Bb]\=[Rr]\=[Uu]\=\z("""\|'''\)+ end=+.*\z1+ fold transparent contained
          \ containedin=pythonString,pythonUniString,pythonUniRawString,pythonRawString
  endif

  " Match all function and class definitions. 
  syn region  pythonFunctionFold	start="^\(\s*\)\%(def\|class\)\s\+\_.\{-\}:\%(\s*\|\s*#.*\)\n\%(\s*\n\)*\z(\1\s\+\)"
        \ skip="\%(^\s*\n\|^\z1.*\|^\s*#.*\)"
        \ end="^\ze\%(\%(\z1.*\)\@!\|\z1\)" fold transparent
  " Match all Comments that span more than one line.
  syn region  pythonCommentFold	start="^\z(\s*\)#\%(!\|\s*-\*-\)\@!.*$" 
        \ end="^\%(\z1\#.*$\)\@!" fold contains=ALLBUT,pythonCommentFold
endif

" Alternate foldtext generating function. {{{1
" This looks for the first text in comments to get some meaningfull text in
" for block comments.
" It also looks for the first Docstring line and appends it to the text.
if exists("python_docstring_in_foldtext") && python_docstring_in_foldtext
  set foldtext=PythonFoldText()
  function! PythonFoldText()
    for i in range(v:foldstart, v:foldend)
      let line = getline(i)
      if match(line, "[:alphanum:]") >= 0
        break
      endif
    endfor
    if i == v:foldend
      let line = getline(v:foldstart)
    endif

    let lineCount = v:foldend-v:foldstart+1
    let line = substitute(line, '^\s*\|/\*\|\*/\|{\{{\d\=', '', 'g')

    let doc = ""
    if exists("g:python_docstring_in_foldtext") && g:python_docstring_in_foldtext != 0
      for i in range(v:foldstart+1, v:foldstart+3)
        let str = getline(i)
        if strlen(substitute(str, '^\s*\(.\{-}\)\s*$', '\1', '')) > 0
          let id = synID(i, match(str, "[:graph:]"), 0)
          if match(synIDattr(id, "name"), "String") >= 0
            let doc = doc . substitute(str, '^\s*\(.\{-}\)\s*$', '\1', '')
            if match(str, "[:alphanum:]") >= 0
              break
            endif
          else
            let doc = ""
            break
          endif
        endif
      endfor
    endif
    let format = "+%s %" . len(line('$')) . "d lines %s  %s"
    return printf(format, v:folddashes, lineCount, line, doc)
  endfunction
endif

" Create variables for Python syntax check. {{{1
if exists('python_check_syntax') && python_check_syntax
    if !exists('python_makeprg') && !exists('python_error_format')
        if executable('pyflakes')
            " let python_makeprg = 'pyflakes "%:p" | grep -v "unable to detect undefined names"'
            let python_makeprg = 'pyflakes "%:p"'
            let python_error_format = '%A%f:%l: %m,%C%s,%Z%p^,%f:%l: %m'
        else
            let python_makeprg = 'python -c "import py_compile,sys; sys.stderr = sys.stdout; py_compile.compile(r''%'')"'
            let python_error_format = "SyntaxError: ('%m'\\, ('%f'\\, %l\\, %c\\, '%s'))"
        endif
    endif

    " Enable plug-in for current buffer without reloading? {{{1
    " Enable automatic command to check for syntax errors when saving buffers.
    augroup PluginFileTypePython
        autocmd! BufWritePost <buffer> call s:SyntaxCheck()
    augroup END


    " Finish loading the plug-in when it's already loaded.
    if exists('loaded_python_ftplugin')
        finish
    else
        let loaded_python_ftplugin = 1
    endif

    " Check for syntax errors when saving buffers. {{{1

    function s:SyntaxCheck()
        if exists('g:python_check_syntax') && g:python_check_syntax
            if exists('g:python_makeprg') && exists('g:python_error_format')
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
                        echo 'Checking Python script syntax ..'
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
        endif
    endfunction
endif
