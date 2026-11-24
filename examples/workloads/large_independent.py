"""Large tier: 10,000 independent trivial tasks on four workers of two cores."""
# scale: large
import _common as c
from ndcctools.taskvine import Task

N = 10_000
m = c.manager()
for _ in range(4):
    c.start_worker(cores=2, memory=2000, disk=4000)
tasks = []
for i in range(N):
    t = Task(f"echo {i}")
    t.set_cores(1)
    m.submit(t)
    tasks.append(t)
c.wait_all(m, tasks, timeout=1500)
c.expect(tasks=N, outcomes=c.outcome_counts(tasks), workers=4)
