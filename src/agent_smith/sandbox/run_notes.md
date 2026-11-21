PARENT (host.py)                                CHILD (worker.py, python -I, env={})
────────────────                                ────────────────────────────────────
start once: Popen(start_new_session=True) ───►  startup:
                                                  setrlimit AS=max_mem, CPU, NPROC=0, FSIZE, CORE=0
                                                  sys.addaudithook(deny socket/subprocess/os.system/open-outside)
                                                  namespace = {"__builtins__": safe_builtins,
                                                               "final_answer": ..., <tool stubs>}
                                                  replace fds 0/1 with /dev/null, keep private pipe fds
send {"type":"exec","code":...} ────────────►   policy.check_ast(code) → policy_violation / syntax_error
deadline = now + timeout                         redirect sys.stdout/stderr → streaming writer
loop on select(pipe, deadline):                  exec(compile(code), namespace)
  "stdout"/"stderr" chunk  ◄──────────────────     print(...) → {"type":"stdout","data":...}
  "tool_call" {name,kwargs} ◄─────────────────     read_file(path=...) stub → sends message, waits
     pause deadline, call tools[name](**kw)
     {"type":"tool_result",...} ──────────────►     stub returns the string
     resume deadline
  "final_answer" {value}   ◄──────────────────     final_answer(x)
  "done" {status, error}   ◄──────────────────   catches Exception → formatted traceback
                                                 SystemExit / KeyboardInterrupt → reported as such
deadline passed → os.killpg(SIGKILL), keep the partial stdout,
                  status=TIMEOUT, restart worker, namespace_reset=True
pipe EOF / exit by signal → CRASHED or MEMORY, restart worker
