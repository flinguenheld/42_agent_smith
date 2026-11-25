# Isolated code execution and sandboxing

Are we really calling exec() on parsed code and calling it
secure sandboxing right now ? Whatever happened to this school's
security standards.

Approaches:
- exec() has it's own namespace dict. Runs straight inside our main program.
        everything is parsed...
- same namespace, runs in seperate thread
        resources are set by eponym module, all else is parsed 
- same namespace, runs through subprocess(python -c 'exec()')
        resources are managed with top or resources ? all else is parsed
- docker, although it seems forbidden here ?
        resources are managed in image, paths are bind mounts, network is closed
- secret fifth thing ?

This has to be as lightweight as possible,
    hopefully mimicking real python interpreter.

Right, because the sandbox is a REPL style process which calls exec()
    with stdin as string on newline.
    So parsing has to be done in an optimized manner, whatever that means.

Running this outside of a microVM or bare minimum gVisor seems so stupid and dangerous.

Obviously a module seems appropriate.
```python
from sandbox import sandbox; sanbox()
```
Should load config and start process
```python
python3 -m sandbox
```
Should do the same thing
```python
from sandbox import sandbox
sbx = sandbox()
print sbx.get_ram()
print sbx.get_up_time()
print sbx.stdin(str)
print sbx.get_stdout()
print sbx.get_stderr()
```
Should look smth like this ig

needs proper signals handling, no idea what that is

TO CLARIFY IN A GLOSSARY:

subprocesses
pipes with stdin/out redirection
exec, why it's good and why it's bad
ast and every node type visited in policy
import, \_\_import\_\_, their builtin implementation and signature and what is done here (what is fromlist ?)
globals, locals, namespaces, how they are dangerous and handled here
dangerous dunders and attributes
