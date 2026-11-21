def check_ast(code: str) -> list[str]
    # Rejects dunder attribute access (__subclasses__, __globals__, __builtins__, __code__, __mro__...)
    # and imports not on the allowlist (static check; the runtime hook checks again).

def is_import_allowed(name: str, allowlist: list[str]) -> bool
    # Exact match, or "pkg.*" covering pkg.sub.

def make_import(allowlist) -> Callable          # replaces __import__
def make_open(allowed_dirs) -> Callable         # realpath, then must sit under an allowed dir
def safe_builtins(cfg, extra) -> dict           # removes eval, exec, compile, open, input, breakpoint,
                                                # globals, vars, memoryview..., then adds the safe versions
def audit_hook(allowed_dirs) -> Callable[[str, tuple], None]
    # Second line of defence: socket.*, subprocess.Popen, os.system, os.exec*, os.fork, ctypes.*, open outside.
