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
if !exists('python_autoindent')
  let python_autoindent = 1
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

" Load custom auto indent code. {{{1
" Only load this indent file when no other was loaded.
if exists('python_autoindent') && python_autoindent
  if !exists("b:did_indent")

    " Some preliminary settings
    setlocal nolisp		" Make sure lisp indenting doesn't supersede us
    setlocal autoindent	" indentexpr isn't much help otherwise

    setlocal indentexpr=GetPythonIndent(v:lnum)
    setlocal indentkeys+=<:>,=elif,=except

    let s:maxoff = 50	" maximum number of lines to look backwards for ()
    " Only define the function once.
    if !exists("*GetPythonIndent")

      function GetPythonIndent(lnum) "{{{2



        " If this line is explicitly joined: If the previous line was also joined,
        " line it up with that one, otherwise add two 'shiftwidth'
        if getline(a:lnum - 1) =~ '\\$'
          if a:lnum > 1 && getline(a:lnum - 2) =~ '\\$'
            return indent(a:lnum - 1)
          endif
          return indent(a:lnum - 1) + (exists("g:pyindent_continue") ? eval(g:pyindent_continue) : (&sw * 2))
        endif

        " If the start of the line is in a string don't change the indent.
        if has('syntax_items')
              \ && synIDattr(synID(a:lnum, 1, 1), "name") =~ "String$"
          return -1
        endif

        " Search backwards for the previous non-empty line.
        let plnum = prevnonblank(v:lnum - 1)

        if plnum == 0
          " This is the first non-empty line, use zero indent.
          return 0
        endif

        " If the previous line is inside parenthesis, use the indent of the starting
        " line.
        " Trick: use the non-existing "dummy" variable to break out of the loop when
        " going too far back.
        call cursor(plnum, 1)
        let parlnum = searchpair('(\|{\|\[', '', ')\|}\|\]', 'nbW',
              \ "line('.') < " . (plnum - s:maxoff) . " ? dummy :"
              \ . " synIDattr(synID(line('.'), col('.'), 1), 'name')"
              \ . " =~ '\\(Comment\\|String\\)'")
        if parlnum > 0
          let plindent = indent(parlnum)
          let plnumstart = parlnum
        else
          let plindent = indent(plnum)
          let plnumstart = plnum
        endif


        " When inside parenthesis: If at the first line below the parenthesis add
        " two 'shiftwidth', otherwise same as previous line.
        " i = (a
        "       + b
        "       + c)
        call cursor(a:lnum, 1)
        let p = searchpair('(\|{\|\[', '', ')\|}\|\]', 'bW',
              \ "line('.') < " . (a:lnum - s:maxoff) . " ? dummy :"
              \ . " synIDattr(synID(line('.'), col('.'), 1), 'name')"
              \ . " =~ '\\(Comment\\|String\\)'")
        if p > 0
          if p == plnum
            " When the start is inside parenthesis, only indent one 'shiftwidth'.
            let pp = searchpair('(\|{\|\[', '', ')\|}\|\]', 'bW',
                  \ "line('.') < " . (a:lnum - s:maxoff) . " ? dummy :"
                  \ . " synIDattr(synID(line('.'), col('.'), 1), 'name')"
                  \ . " =~ '\\(Comment\\|String\\)'")
            if pp > 0
              return indent(plnum) + (exists("g:pyindent_nested_paren") ? eval(g:pyindent_nested_paren) : &sw)
            endif
            return indent(plnum) + (exists("g:pyindent_open_paren") ? eval(g:pyindent_open_paren) : (&sw * 2))
          endif
          if plnumstart == p
            return indent(plnum)
          endif
          return plindent
        endif


        " Get the line and remove a trailing comment.
        " Use syntax highlighting attributes when possible.
        let pline = getline(plnum)
        let pline_len = strlen(pline)
        let col = 0
        while col < pline_len
          if pline[col] == '#'
            let pline = strpart(pline, 0, col)
            break
          endif
          let col = col + 1
        endwhile

        " If the previous line ended with a colon, indent this line
        if pline =~ ':\s*$'
          return plindent + &sw
        endif

        " If the previous line was a stop-execution statement...
        if getline(plnum) =~ '^\s*\(break\|continue\|raise\|return\|pass\)\>'
          " See if the user has already dedented
          if indent(a:lnum) > indent(plnum) - &sw
            " If not, recommend one dedent
            return indent(plnum) - &sw
          endif
          " Otherwise, trust the user
          return -1
        endif

        " If the current line begins with a keyword that lines up with "try"
        if getline(a:lnum) =~ '^\s*\(except\|finally\)\>'
          let lnum = a:lnum - 1
          while lnum >= 1
            if getline(lnum) =~ '^\s*\(try\|except\)\>'
              let ind = indent(lnum)
              if ind >= indent(a:lnum)
                return -1	" indent is already less than this
              endif
              return ind	" line up with previous try or except
            endif
            let lnum = lnum - 1
          endwhile
          return -1		" no matching "try"!
        endif

        " If the current line begins with a header keyword, dedent
        if getline(a:lnum) =~ '^\s*\(elif\|else\)\>'

          " Unless the previous line was a one-liner
          if getline(plnumstart) =~ '^\s*\(for\|if\|try\)\>'
            return plindent
          endif

          " Or the user has already dedented
          if indent(a:lnum) <= plindent - &sw
            return -1
          endif

          return plindent - &sw
        endif

        " When after a () construct we probably want to go back to the start line.
        " a = (b
        "       + c)
        " here
        if parlnum > 0
          return plindent
        endif

        return -1

    endfunction "}}}

    endif
    let b:did_indent = 1
  endif
endif

" vim:sw=2
