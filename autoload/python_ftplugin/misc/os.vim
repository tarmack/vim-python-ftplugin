" This Vim script was modified by a Python script that I use to manage the
" inclusion of miscellaneous functions in the plug-ins that I publish to Vim
" Online and GitHub. Please don't edit this file, instead make your changes on
" the 'dev' branch of the git repository (thanks!). This file was generated on
" May 23, 2013 at 22:18.

" Operating system interfaces.
"
" Author: Peter Odding <peter@peterodding.com>
" Last Change: May 20, 2013
" URL: http://peterodding.com/code/vim/misc/

let g:python_ftplugin#misc#os#version = '0.5'

function! python_ftplugin#misc#os#is_win() " {{{1
  " Returns 1 (true) when on Microsoft Windows, 0 (false) otherwise.
  return has('win16') || has('win32') || has('win64')
endfunction

function! python_ftplugin#misc#os#find_vim() " {{{1
  " Returns the program name of Vim as a string. On Windows and UNIX this
  " simply returns [v:progname] [progname] while on Mac OS X there is some
  " special magic to find MacVim's executable even though it's usually not on
  " the executable search path.
  "
  " [progname]: http://vimdoc.sourceforge.net/htmldoc/eval.html#v:progname
  let progname = ''
  if has('macunix')
    " Special handling for Mac OS X where MacVim is usually not on the $PATH.
    call python_ftplugin#misc#msg#debug("os.vim %s: Trying MacVim workaround to find Vim executable ..", g:python_ftplugin#misc#os#version)
    let segments = python_ftplugin#misc#path#split($VIMRUNTIME)
    if segments[-3:] == ['Resources', 'vim', 'runtime']
      let progname = python_ftplugin#misc#path#join(segments[0:-4] + ['MacOS', 'Vim'])
      call python_ftplugin#misc#msg#debug("os.vim %s: The MacVim workaround resulted in the Vim executable %s.", g:python_ftplugin#misc#os#version, string(progname))
    endif
  endif
  if empty(progname)
    call python_ftplugin#misc#msg#debug("os.vim %s: Looking for Vim executable named %s on search path ..", g:python_ftplugin#misc#os#version, string(v:progname))
    let candidates = python_ftplugin#misc#path#which(v:progname)
    if !empty(candidates)
      call python_ftplugin#misc#msg#debug("os.vim %s: Found %i candidate(s) on search path: %s.", g:python_ftplugin#misc#os#version, len(candidates), string(candidates))
      let progname = candidates[0]
    endif
  endif
  call python_ftplugin#misc#msg#debug("os.vim %s: Reporting Vim executable %s.", g:python_ftplugin#misc#os#version, string(progname))
  return progname
endfunction

function! python_ftplugin#misc#os#exec(options) " {{{1
  " Execute an external command (hiding the console on Microsoft Windows when
  " my [vim-shell plug-in] [vim-shell] is installed).
  "
  " Expects a dictionary with the following key/value pairs as the first
  " argument:
  "
  " - **command** (required): The command line to execute
  " - **async** (optional): set this to 1 (true) to execute the command in the
  "   background (asynchronously)
  " - **stdin** (optional): a string or list of strings with the input for the
  "   external command
  " - **check** (optional): set this to 0 (false) to disable checking of the
  "   exit code of the external command (by default an exception will be
  "   raised when the command fails)
  "
  " Returns a dictionary with one or more of the following key/value pairs:
  "
  " - **command** (always available): the generated command line that was used
  "   to run the external command
  " - **exit_code** (only in synchronous mode): the exit status of the
  "   external command (an integer, zero on success)
  " - **stdout** (only in synchronous mode): the output of the command on the
  "   standard output stream (a list of strings, one for each line)
  " - **stderr** (only in synchronous mode): the output of the command on the
  "   standard error stream (as a list of strings, one for each line)
  "
  " [vim-shell]: http://peterodding.com/code/vim/shell/
  try

    " Unpack the options.
    let cmd = a:options['command']
    let async = get(a:options, 'async', 0)

    " Write the input for the external command to a temporary file?
    if has_key(a:options, 'stdin')
      let tempin = tempname()
      if type(a:options['stdin']) == type([])
        let lines = a:options['stdin']
      else
        let lines = split(a:options['stdin'], "\n")
      endif
      call writefile(lines, tempin)
      let cmd .= ' < ' . python_ftplugin#misc#escape#shell(tempin)
    endif

    " Redirect the standard output and standard error streams of the external
    " process to temporary files? (only in synchronous mode, which is the
    " default).
    if !async
      let tempout = tempname()
      let temperr = tempname()
      let cmd = printf('(%s) 1>%s 2>%s', cmd, python_ftplugin#misc#escape#shell(tempout), python_ftplugin#misc#escape#shell(temperr))
    endif

    " If A) we're on Windows, B) the vim-shell plug-in is installed and C) the
    " compiled DLL works, we'll use that because it's the most user friendly
    " method. If the plug-in is not installed Vim will raise the exception
    " "E117: Unknown function" which is caught and handled below.
    try
      if xolox#shell#can_use_dll()
        " Let the user know what's happening (in case they're interested).
        call python_ftplugin#misc#msg#debug("os.vim %s: Executing external command using compiled DLL: %s", g:python_ftplugin#misc#os#version, cmd)
        let exit_code = xolox#shell#execute_with_dll(cmd, async)
      endif
    catch /^Vim\%((\a\+)\)\=:E117/
      call python_ftplugin#misc#msg#debug("os.vim %s: The vim-shell plug-in is not installed, falling back to system() function.", g:python_ftplugin#misc#os#version)
    endtry

    " If we cannot use the DLL, we fall back to the default and generic
    " implementation using Vim's system() function.
    if !exists('exit_code')

      " Enable asynchronous mode (very platform specific).
      if async
        if python_ftplugin#misc#os#is_win()
          let cmd = 'start /b ' . cmd
        elseif has('unix')
          let cmd = '(' . cmd . ') &'
        else
          call python_ftplugin#misc#msg#warn("os.vim %s: I don't know how to run commands asynchronously on your platform! Falling back to synchronous mode.", g:python_ftplugin#misc#os#version)
        endif
      endif

      " Execute the command line using 'sh' instead of the default shell,
      " because we assume that standard output and standard error can be
      " redirected separately, but (t)csh does not support this.
      if has('unix')
        call python_ftplugin#misc#msg#debug("os.vim %s: Generated shell expression: %s", g:python_ftplugin#misc#os#version, cmd)
        let cmd = printf('sh -c %s', python_ftplugin#misc#escape#shell(cmd))
      endif

      " Let the user know what's happening (in case they're interested).
      call python_ftplugin#misc#msg#debug("os.vim %s: Executing external command using system() function: %s", g:python_ftplugin#misc#os#version, cmd)
      call system(cmd)
      let exit_code = v:shell_error

    endif

    " Return the results as a dictionary with one or more key/value pairs.
    let result = {'command': cmd}
    if !async
      let result['exit_code'] = exit_code
      let result['stdout'] = s:readfile(tempout)
      let result['stderr'] = s:readfile(temperr)
      " If we just executed a synchronous command and the caller didn't
      " specifically ask us *not* to check the exit code of the external
      " command, we'll do so now.
      if get(a:options, 'check', 1) && exit_code != 0
        " Prepare an error message with enough details so the user can investigate.
        let msg = printf("os.vim %s: External command failed with exit code %d!", g:python_ftplugin#misc#os#version, result['exit_code'])
        let msg .= printf("\nCommand line: %s", result['command'])
        " If the external command reported an error, we'll include it in our message.
        if !empty(result['stderr'])
          " This is where we would normally expect to find an error message.
          let msg .= printf("\nOutput on standard output stream:\n%s", join(result['stderr'], "\n"))
        elseif !empty(result['stdout'])
          " Exuberant Ctags on Windows XP reports errors on standard output :-x.
          let msg .= printf("\nOutput on standard error stream:\n%s", join(result['stdout'], "\n"))
        endif
        throw msg
      endif
    endif
    return result

  finally
    " Cleanup any temporary files we created.
    for name in ['tempin', 'tempout', 'temperr']
      if exists(name)
        call delete({name})
      endif
    endfor
  endtry

endfunction

function! s:readfile(fname) " {{{1
  " readfile() that swallows errors.
  try
    return readfile(a:fname)
  catch
    return []
  endtry
endfunction

" vim: ts=2 sw=2 et
