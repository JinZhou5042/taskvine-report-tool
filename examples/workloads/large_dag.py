"""Large tier: a layered DAG of temp files with fan-out, fan-in, and peer transfers (6,001 tasks).

Each of 20 layers has 300 tasks.  A task reads the outputs of three tasks of the layer before (fan-in), each output is
read by three tasks of the next layer (fan-out), and one task gathers the last layer.  Temps move between workers by
peer transfer.
"""
# scale: large
import _common as c
from ndcctools.taskvine import Task

LAYERS, WIDTH = 20, 300
m = c.manager()
m.enable_peer_transfers()
for _ in range(4):
    c.start_worker(cores=2, memory=2000, disk=8000)
tasks, previous = [], []
for layer in range(LAYERS):
    current = []
    for j in range(WIDTH):
        out = m.declare_temp()
        parents = [previous[(j + k * 7) % WIDTH] for k in range(3)] if previous else []
        t = Task("cat " + " ".join(f"in{k}" for k in range(len(parents))) + f" 2>/dev/null | head -c 2000 > out; echo {layer}-{j} >> out")
        for k, parent in enumerate(parents):
            t.add_input(parent, f"in{k}")
        t.add_output(out, "out")
        t.set_cores(1)
        m.submit(t)
        tasks.append(t)
        current.append(out)
    previous = current
gather = Task("cat in* | wc -c")
for k, parent in enumerate(previous):
    gather.add_input(parent, f"in{k}")
m.submit(gather)
tasks.append(gather)
c.wait_all(m, tasks, timeout=1500)
c.expect(tasks=len(tasks), outcomes=c.outcome_counts(tasks), workers=4)
