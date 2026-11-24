"""Large tier, vine_graph: 5,000 graph tasks in layers with small and large results, checkpoints, and releases.

Layers of 250 tasks each read two results of the layer before, so most intermediate results are released once their
readers finish.  One result in 25 is 300 KB (a connection checkpoint), the rest are small (inline checkpoints).
"""
# producers: vine-graph
# scale: large
import _common as c
from ndcctools.taskvine import vine_graph as vg


def step(i, *parents):
    return bytes([i % 256]) * (300_000 if i % 25 == 0 else 200)


def total(*parts):
    return sum(len(p) for p in parts)


LAYERS, WIDTH = 20, 250
for _ in range(4):
    c.start_worker(cores=2, memory=2000, disk=8000)
with c.executor() as ex:
    previous = []
    for layer in range(LAYERS):
        previous = [vg.Function(step, layer * WIDTH + j, *([previous[j], previous[(j + 1) % WIDTH]] if previous else []))
                    for j in range(WIDTH)]
    last = vg.Function(total, *previous)
    ex.run(last)
    assert last.result() == sum(len(step(j)) for j in range((LAYERS - 1) * WIDTH, LAYERS * WIDTH))
c.expect(graph_tasks_min=LAYERS * WIDTH + 1, workers=4, checkpoints_min=1, inline_checkpoints_min=1)
