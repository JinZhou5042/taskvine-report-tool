"""Large tier: 4,000 short tasks while workers are killed and replaced, with failures and retries mixed in.

Every 8 s one worker is SIGKILLed and a new one started, so running tasks are retried elsewhere.  One task in 20
exits nonzero, one in 50 exceeds its time limit, and one in 100 asks for more memory than any worker has after
its first allocation is exhausted.
"""
# scale: large
import time
import _common as c
from ndcctools.taskvine import Task

N = 4_000
m = c.manager()
workers = [c.start_worker(cores=2, memory=2000, disk=4000) for _ in range(4)]
started = len(workers)
tasks = []
for i in range(N):
    if i % 50 == 7:
        t = Task("sleep 5")
        t.set_time_max(1)
    elif i % 20 == 3:
        t = Task(f"echo failing {i} >&2; exit {i % 7 + 1}")
    else:
        t = Task(f"sleep 0.0{i % 10}; echo {i}")
    t.set_cores(1)
    t.set_retries(2 if i % 50 == 7 else 10)
    m.submit(t)
    tasks.append(t)
next_kill = time.time() + 8


def churn():
    global next_kill, started
    if time.time() >= next_kill and len(c._returned) < N - 200:
        victim = workers.pop(0)
        c.kill_worker(victim)
        workers.append(c.start_worker(cores=2, memory=2000, disk=4000))
        started += 1
        next_kill = time.time() + 8


c.wait_all(m, tasks, timeout=1500, step=churn)
c.expect(tasks=N, outcomes=c.outcome_counts(tasks), workers=started, worker_loss_attempts_min=1,
         exit_codes=c.exit_codes([t for t in tasks if t.exit_code]))
