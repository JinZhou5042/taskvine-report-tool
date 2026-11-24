"""Large tier: 6,000 function calls through one library on four workers."""
# scale: large
import _common as c
import _library as lib
from ndcctools.taskvine import FunctionCall

N = 6_000
m = c.manager()
for _ in range(4):
    c.start_worker(cores=2, memory=2000, disk=4000)
library = m.create_library_from_functions("ex-large-lib", lib.square, lib.concat, add_env=False, exec_mode="fork")
library.set_cores(2)
library.set_function_slots(2)
m.install_library(library)
calls = []
for i in range(N):
    t = FunctionCall("ex-large-lib", "square", i) if i % 2 else FunctionCall("ex-large-lib", "concat", i, "x")
    m.submit(t)
    calls.append(t)
c.wait_all(m, calls, timeout=1500)
c.expect(tasks=N, outcomes=c.outcome_counts(calls), workers=4, libraries_min=4, function_calls=N)
