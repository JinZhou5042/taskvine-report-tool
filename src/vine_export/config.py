"""
General configuration for vine_export plots.

Shared defaults and helpers for all plot modules.
Aligns with vine_report processing where applicable.
"""

# --- Plot defaults ---
# Default output DPI for saved PNG images.
# Final pixel size = figure inches * DPI.
DPI_DEFAULT = 150
# Matplotlib backend used in headless/server environments.
MATPLOTLIB_BACKEND = "Agg"

# Fixed canvas size (inches) - output pixels = size * dpi
# Figure width in inches for all exported plots.
CANVAS_WIDTH_INCHES = 12.8
# Figure height in inches for all exported plots.
CANVAS_HEIGHT_INCHES = 8.0

# --- Typography / layout defaults ---
# Font size for chart title text.
TITLE_SIZE = 20
# Extra vertical spacing (points) between title and plotting area.
TITLE_PAD = 14
# Font size for axis title text (x/y labels).
LABEL_SIZE = 18
# Axis label padding (distance from axis to x/y label title)
# Horizontal axis title offset from x-axis (points).
X_LABEL_PAD = 10
# Vertical axis title offset from y-axis (points).
Y_LABEL_PAD = 10
# Font size for tick labels on both axes.
TICK_LABEL_SIZE = 16
# Legend label font size.
LEGEND_FONT_SIZE = 16
# Marker size for scatter/point-based charts.
MARKER_SIZE = 7
# Default line width for line charts.
LINE_WIDTH = 2.5
# Grid line transparency (0=transparent, 1=opaque).
GRID_ALPHA = 0.18

# Layout: use constrained_layout so title/labels stay inside canvas when font size changes
# Units are inches. Keep small for compact output while avoiding clipping.
# Outer figure padding applied by constrained_layout.
LAYOUT_PAD = 0.04
# Extra horizontal spacing between sub-layout elements (if any).
LAYOUT_W_PAD = 0.005
# Extra vertical spacing between sub-layout elements (if any).
LAYOUT_H_PAD = 0.005

# --- Axis / ticks ---
# Default number of ticks for continuous numeric axes.
DEFAULT_LINEAR_TICK_COUNT = 5
# Default number of ticks for index/discrete axes.
DEFAULT_DISCRETE_TICK_COUNT = 10
# Decimal places used when rounding time-axis tick values.
TIME_TICK_ROUND_DIGITS = 2

# --- Rendering limits for dense multi-series charts ---
# Keep these configurable for performance/readability trade-offs.
# Max number of overlaid series lines to render for dense plots.
MAX_MULTI_SERIES_LINES = 140
# Transparency for each line in dense multi-series rendering.
MULTI_SERIES_LINE_ALPHA = 0.22
# Line width for dense multi-series rendering.
MULTI_SERIES_LINE_WIDTH = 1.8

# --- Common colors ---
# Color for successful/normal states.
COLOR_SUCCESS = "steelblue"
# Color for failure/error states.
COLOR_FAILURE = "#E3314F"
# Neutral fallback color.
COLOR_NEUTRAL = "#888888"
# Color for waiting phase/state.
COLOR_WAITING = "#f39c12"
# Color for committing phase/state.
COLOR_COMMITTING = "#0ecfc8"
# Color for executing phase/state.
COLOR_EXECUTING = "steelblue"
# Color for retrieving phase/state.
COLOR_RETRIEVING = "#cc5a12"
# Color for completed/done state.
COLOR_DONE = "#2ca02c"

# Task downsampling (same default as vine_report DOWNSAMPLE_TASK_BARS=100000)
# Upper bound of tasks plotted per task type to avoid huge render cost.
MAX_TASKS_PER_TYPE = 100000


def downsample_tasks(tasks, key="execution_time", max_tasks=MAX_TASKS_PER_TYPE):
    """
    Downsample task records for plotting performance.

    Args:
        tasks: List[dict] of task records.
        key: Field used for ranking (higher first).
        max_tasks: Maximum tasks kept after downsampling.

    Returns:
        Original list if already small enough; otherwise top max_tasks sorted by key descending.
    """
    if len(tasks) <= max_tasks:
        return tasks
    # Same as vine_report: sort by execution_time descending, take top max_tasks
    tasks = sorted(tasks, key=lambda x: x.get(key) if x.get(key) is not None else 0, reverse=True)
    return tasks[:max_tasks]


def figsize_fixed():
    """Return default fixed figure size: (CANVAS_WIDTH_INCHES, CANVAS_HEIGHT_INCHES)."""
    return (CANVAS_WIDTH_INCHES, CANVAS_HEIGHT_INCHES)


def figsize_from_height(height, aspect_ratio=1.6):
    """
    Build figure size from height with configurable aspect ratio.

    Args:
        height: Figure height in inches.
        aspect_ratio: width / height ratio.
    """
    return (aspect_ratio * height, height)


def figsize_from_bands(num_bands, aspect_ratio=1.6):
    """
    Deprecated compatibility helper for band plots.

    Args:
        num_bands: Unused; kept only for API compatibility.
        aspect_ratio: Unused; kept only for API compatibility.
    """
    return figsize_fixed()
