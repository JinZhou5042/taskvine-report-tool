#!/usr/bin/env python3
"""
vine_export command - Export TaskVine report to static PNG and PDF

Reads CSV output from vine_parse, generates static plots (PNG) for each section,
saves to png-files/, and combines into a single PDF in pdf-files/.
"""

import argparse
import base64
import os
import sys
import fnmatch
import traceback as tb
from datetime import datetime
from html import escape
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.utils import check_pip_updates, ensure_dir, create_progress_bar
from src.vine_export.config import (
    CANVAS_HEIGHT_INCHES,
    CANVAS_WIDTH_INCHES,
    DPI_DEFAULT,
    MAX_TASKS_PER_TYPE,
    HTML_DEFAULT_CONTENT_WIDTH_PERCENT,
    HTML_MIN_CONTENT_WIDTH_PERCENT,
    HTML_MAX_CONTENT_WIDTH_PERCENT,
    HTML_MAX_CONTENT_WIDTH_VIEWPORT_PERCENT,
    HTML_WRAP_PADDING,
    HTML_H1_FONT_SIZE_PX,
    HTML_SUBTEXT_FONT_SIZE_PX,
    HTML_SECTION_TITLE_FONT_SIZE_PX,
    HTML_CARD_BORDER_RADIUS_PX,
    HTML_CARD_BORDER_COLOR,
    HTML_CARD_BG_COLOR,
    HTML_KNOB_PADDING,
    HTML_KNOB_MARGIN_BOTTOM_PX,
    HTML_KNOB_ROW_GAP_PX,
    HTML_SLIDER_MAX_WIDTH_PX,
    HTML_SECTION_CARD_PADDING,
    HTML_SECTION_CARD_MARGIN_Y_PX,
    HTML_IMAGE_BORDER_RADIUS_PX,
    HTML_IMAGE_BORDER_COLOR,
    HTML_TOC_COLUMNS,
)
from src import __version__


class ExportHelpFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawTextHelpFormatter):
    """Keep defaults + preserve line breaks in help text."""
    pass


def remove_duplicates_preserve_order(seq):
    seen = set()
    result = []
    for item in seq:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def find_matching_directories(root_dir, patterns):
    """Find directories matching given patterns under root_dir."""
    try:
        all_dirs = [
            d for d in os.listdir(root_dir)
            if os.path.isdir(os.path.join(root_dir, d))
        ]
        matched_dirs = []
        for pattern in patterns:
            pattern = pattern.rstrip("/")
            pattern = os.path.basename(pattern)
            pattern = pattern.strip("'\"")
            pattern_matches = [d for d in all_dirs if fnmatch.fnmatch(d, pattern)]
            if pattern_matches:
                matched_dirs.extend(pattern_matches)
            else:
                print(f"⚠️  Pattern '{pattern}' matched no directories")
        if not matched_dirs:
            print(f"❌ No directories matched any of the provided patterns in {root_dir}")
            sys.exit(1)
        return matched_dirs
    except Exception as e:
        print(f"❌ Error scanning directory {root_dir}: {e}")
        sys.exit(1)


def has_csv_files(path):
    """Check if directory contains vine_parse output (csv-files subdir)."""
    csv_dir = os.path.join(path, "csv-files")
    return os.path.isdir(csv_dir)


def get_export_dirs(runtime_template):
    """Return paths for png-files and pdf-files (same level as svg-files)."""
    base = Path(runtime_template)
    return {
        "png_files": base / "png-files",
        "pdf_files": base / "pdf-files",
        "html_files": base / "html-files",
        "csv_files": base / "csv-files",
    }


# --- Plot section IDs (aligned with vine_serve modules) ---
EXPORT_SECTIONS = [
    "task-execution-details",
    "task-concurrency",
    "task-response-time",
    "task-execution-time",
    "task-retrieval-time",
    "worker-concurrency",
    "worker-storage-consumption",
    "worker-incoming-transfers",
    "worker-outgoing-transfers",
    "worker-executing-tasks",
    "worker-lifetime",
    "file-sizes",
    "file-concurrent-replicas",
    "file-retention-time",
    "file-transferred-size",
    "file-created-size",
]


def generate_plot_png(section_id, csv_files_dir, png_files_dir, **kwargs):
    """
    Generate a single plot PNG for the given section.

    Reads CSV from csv_files_dir, produces PNG in png_files_dir.
    """
    from src.vine_export.plot_sections import (
        plot_task_concurrency,
        plot_task_response_time,
        plot_task_execution_time,
        plot_task_retrieval_time,
        plot_worker_concurrency,
        plot_worker_storage_consumption,
        plot_worker_incoming_transfers,
        plot_worker_outgoing_transfers,
        plot_worker_executing_tasks,
        plot_worker_lifetime,
        plot_file_sizes,
        plot_file_concurrent_replicas,
        plot_file_retention_time,
        plot_file_transferred_size,
        plot_file_created_size,
    )
    from src.vine_export.plot_task_execution_details import plot_task_execution_details

    dpi = kwargs.get("dpi", DPI_DEFAULT)
    max_tasks = kwargs.get("max_tasks", MAX_TASKS_PER_TYPE)
    width = kwargs.get("width")
    height = kwargs.get("height")

    plotters = {
        "task-concurrency": lambda: plot_task_concurrency(csv_files_dir, png_files_dir, dpi=dpi, width=width, height=height),
        "task-response-time": lambda: plot_task_response_time(csv_files_dir, png_files_dir, dpi=dpi, width=width, height=height),
        "task-execution-time": lambda: plot_task_execution_time(csv_files_dir, png_files_dir, dpi=dpi, width=width, height=height),
        "task-retrieval-time": lambda: plot_task_retrieval_time(csv_files_dir, png_files_dir, dpi=dpi, width=width, height=height),
        "worker-concurrency": lambda: plot_worker_concurrency(csv_files_dir, png_files_dir, dpi=dpi, width=width, height=height),
        "worker-storage-consumption": lambda: plot_worker_storage_consumption(csv_files_dir, png_files_dir, dpi=dpi, width=width, height=height),
        "worker-incoming-transfers": lambda: plot_worker_incoming_transfers(csv_files_dir, png_files_dir, dpi=dpi, width=width, height=height),
        "worker-outgoing-transfers": lambda: plot_worker_outgoing_transfers(csv_files_dir, png_files_dir, dpi=dpi, width=width, height=height),
        "worker-executing-tasks": lambda: plot_worker_executing_tasks(csv_files_dir, png_files_dir, dpi=dpi, width=width, height=height),
        "worker-lifetime": lambda: plot_worker_lifetime(csv_files_dir, png_files_dir, dpi=dpi, width=width, height=height),
        "file-sizes": lambda: plot_file_sizes(csv_files_dir, png_files_dir, dpi=dpi, width=width, height=height),
        "file-concurrent-replicas": lambda: plot_file_concurrent_replicas(csv_files_dir, png_files_dir, dpi=dpi, width=width, height=height),
        "file-retention-time": lambda: plot_file_retention_time(csv_files_dir, png_files_dir, dpi=dpi, width=width, height=height),
        "file-transferred-size": lambda: plot_file_transferred_size(csv_files_dir, png_files_dir, dpi=dpi, width=width, height=height),
        "file-created-size": lambda: plot_file_created_size(csv_files_dir, png_files_dir, dpi=dpi, width=width, height=height),
        "task-execution-details": lambda: plot_task_execution_details(
            csv_files_dir,
            png_files_dir,
            dpi=dpi,
            max_tasks=max_tasks,
            width=width,
            height=height,
        ),
    }
    if section_id in plotters:
        return plotters[section_id]()
    return None


def combine_pngs_to_pdf(png_paths, pdf_path, **kwargs):
    """
    Combine multiple PNG files into a single PDF.

    TODO: Implement using reportlab, img2pdf, or similar.
    """
    # Placeholder - actual implementation will merge PNGs into one PDF
    pass


def _section_title(section_id):
    return section_id.replace("-", " ").title()


def build_self_contained_html_report(items, html_path, template_name):
    """
    Build a single self-contained HTML report.

    items: list of dicts with keys {"section_id", "png_path"}.
    """
    ensure_dir(str(Path(html_path).parent), replace=False)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    repo_url = "https://github.com/cooperative-computing-lab/taskvine-report-tool"

    toc_rows = []
    section_blocks = []
    for idx, item in enumerate(items, start=1):
        section_id = item["section_id"]
        png_path = item["png_path"]
        anchor = f"sec-{idx}"
        title = _section_title(section_id)
        try:
            with open(png_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
        except OSError:
            # Skip broken image paths to keep report generation robust.
            continue

        toc_rows.append(f'<li><a href="#{anchor}">{escape(title)}</a></li>')
        section_blocks.append(
            f"""
            <section class="card" id="{anchor}">
              <h2>{escape(title)}</h2>
              <img src="data:image/png;base64,{b64}" alt="{escape(title)}"/>
            </section>
            """
        )

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>TaskVine Report - {escape(template_name)}</title>
  <style>
    :root {{
      --content-width-percent: {HTML_DEFAULT_CONTENT_WIDTH_PERCENT};
    }}
    body {{
      margin: 0;
      background: #f6f8fb;
      color: #1f2937;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
      line-height: 1.45;
    }}
    .wrap {{
      width: min(calc(var(--content-width-percent) * 1vw), {HTML_MAX_CONTENT_WIDTH_VIEWPORT_PERCENT}vw);
      margin: 0 auto;
      padding: {HTML_WRAP_PADDING};
    }}
    .layout-knob {{
      background: {HTML_CARD_BG_COLOR};
      border: 1px solid {HTML_CARD_BORDER_COLOR};
      border-radius: {HTML_CARD_BORDER_RADIUS_PX}px;
      padding: {HTML_KNOB_PADDING};
      margin-bottom: {HTML_KNOB_MARGIN_BOTTOM_PX}px;
      font-size: {HTML_SUBTEXT_FONT_SIZE_PX}px;
    }}
    .layout-knob .row {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: {HTML_KNOB_ROW_GAP_PX}px;
      flex-wrap: nowrap;
    }}
    .layout-knob input[type="range"] {{
      width: min({HTML_SLIDER_MAX_WIDTH_PX}px, 80vw);
    }}
    .layout-knob .value {{
      min-width: 56px;
      color: #1d4ed8;
      font-weight: 600;
      white-space: nowrap;
      display: inline-block;
    }}
    h1 {{
      margin: 0 0 4px;
      font-size: {HTML_H1_FONT_SIZE_PX}px;
      font-weight: 700;
    }}
    .sub {{
      color: #667085;
      font-size: {HTML_SUBTEXT_FONT_SIZE_PX}px;
      margin-bottom: 16px;
    }}
    .repo {{
      margin: 0 0 16px;
      font-size: {HTML_SUBTEXT_FONT_SIZE_PX}px;
    }}
    .repo a {{
      color: #1d4ed8;
      text-decoration: none;
    }}
    .repo a:hover {{
      text-decoration: underline;
    }}
    .toc {{
      background: {HTML_CARD_BG_COLOR};
      border: 1px solid {HTML_CARD_BORDER_COLOR};
      border-radius: {HTML_CARD_BORDER_RADIUS_PX}px;
      padding: 12px 14px;
      margin-bottom: 16px;
    }}
    .toc ul {{
      margin: 8px 0 0;
      padding-left: 18px;
      columns: {HTML_TOC_COLUMNS};
    }}
    .toc a {{
      color: #1d4ed8;
      text-decoration: none;
    }}
    .toc a:hover {{
      text-decoration: underline;
    }}
    .card {{
      background: {HTML_CARD_BG_COLOR};
      border: 1px solid {HTML_CARD_BORDER_COLOR};
      border-radius: {HTML_CARD_BORDER_RADIUS_PX}px;
      padding: {HTML_SECTION_CARD_PADDING};
      margin: {HTML_SECTION_CARD_MARGIN_Y_PX}px 0;
    }}
    .card h2 {{
      margin: 0 0 4px;
      font-size: {HTML_SECTION_TITLE_FONT_SIZE_PX}px;
    }}
    img {{
      display: block;
      width: 100%;
      height: auto;
      border: 1px solid {HTML_IMAGE_BORDER_COLOR};
      border-radius: {HTML_IMAGE_BORDER_RADIUS_PX}px;
      background: #fff;
    }}
  </style>
</head>
<body>
  <main class="wrap">
    <div class="layout-knob">
      <div class="row">
        <strong>Content Width</strong>
        <input id="width-slider" type="range" min="{HTML_MIN_CONTENT_WIDTH_PERCENT}" max="{HTML_MAX_CONTENT_WIDTH_PERCENT}" step="1" value="{HTML_DEFAULT_CONTENT_WIDTH_PERCENT}"/>
        <span class="value" id="width-value">{HTML_DEFAULT_CONTENT_WIDTH_PERCENT}%</span>
      </div>
    </div>
    <h1>TaskVine Export Report</h1>
    <div class="sub">Template: {escape(template_name)}</div>
    <div class="sub">Generated: {escape(generated_at)}</div>
    <div class="repo">GitHub: <a href="{repo_url}" target="_blank" rel="noopener noreferrer">{repo_url}</a></div>
    <nav class="toc">
      <strong>Sections</strong>
      <ul>
        {''.join(toc_rows)}
      </ul>
    </nav>
    {''.join(section_blocks)}
  </main>
  <script>
    (function () {{
      const slider = document.getElementById('width-slider');
      const valueText = document.getElementById('width-value');
      if (!slider || !valueText) return;
      let pendingValue = slider.value;
      const apply = (v) => {{
        document.documentElement.style.setProperty('--content-width-percent', String(v));
        valueText.textContent = `${{v}}%`;
      }};
      apply(pendingValue);
      // During dragging, only update label; apply layout change on release.
      slider.addEventListener('input', (e) => {{
        pendingValue = e.target.value;
        valueText.textContent = `${{pendingValue}}%`;
      }});
      const commit = () => apply(pendingValue);
      slider.addEventListener('change', commit);     // fallback
      slider.addEventListener('mouseup', commit);    // desktop mouse
      slider.addEventListener('touchend', commit);   // mobile touch
      slider.addEventListener('pointerup', commit);  // pointer devices
    }})();
  </script>
</body>
</html>
"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    return html_path


def export_single_template(template_path, args, sections_to_export):
    """Export one runtime template: PNGs + PDF."""
    dirs = get_export_dirs(template_path)
    ensure_dir(str(dirs["pdf_files"]), replace=False)

    csv_files_dir = dirs["csv_files"]
    # Use --png-dir if specified, else default to {template}/png-files/
    if getattr(args, "png_dir", None):
        png_base = Path(args.png_dir).resolve()
        png_files_dir = png_base / Path(template_path).name
        html_files_dir = png_base / Path(template_path).name / "html-files"
    else:
        png_files_dir = dirs["png_files"]
        html_files_dir = dirs["html_files"]
    ensure_dir(str(png_files_dir), replace=False)
    ensure_dir(str(html_files_dir), replace=False)
    pdf_files_dir = dirs["pdf_files"]

    if not csv_files_dir.exists():
        print(f"  ⚠️  csv-files not found, skipping: {template_path}")
        return False

    png_items = []
    with create_progress_bar() as progress:
        section_task = progress.add_task(
            f"[green]Exporting sections ({Path(template_path).name})",
            total=len(sections_to_export),
        )
        for section_id in sections_to_export:
            try:
                section_kwargs = {
                    "dpi": getattr(args, "dpi", DPI_DEFAULT),
                    "max_tasks": getattr(args, "max_tasks", MAX_TASKS_PER_TYPE),
                    "width": getattr(args, "width", CANVAS_WIDTH_INCHES),
                    "height": getattr(args, "height", CANVAS_HEIGHT_INCHES),
                }
                png_path = generate_plot_png(
                    section_id,
                    str(csv_files_dir),
                    str(png_files_dir),
                    **section_kwargs,
                )
                if png_path and os.path.exists(png_path):
                    png_items.append({"section_id": section_id, "png_path": png_path})
            except Exception as e:
                print(f"  ⚠️  Failed to generate {section_id}: {e}")
            finally:
                progress.advance(section_task)

    # PDF generation disabled for now (only Task Execution Details supported)
    # if png_paths:
    #     pdf_name = Path(template_path).name + ".pdf"
    #     pdf_path = pdf_files_dir / pdf_name
    #     try:
    #         combine_pngs_to_pdf(...)
    #     except Exception as e:
    #         ...

    if png_items:
        html_path = html_files_dir / f"{Path(template_path).name}.html"
        build_self_contained_html_report(png_items, str(html_path), Path(template_path).name)
        print(f"  ✅ PNG saved to directory: {png_files_dir}")
        print(f"  ✅ HTML saved to: {html_path}")
    else:
        print("  ⚠️  No PNG generated for this template")

    return True


def main():
    sections_with_all = sorted(EXPORT_SECTIONS + ["all"])
    sections_help_lines = "\n".join([f"  - {s}" for s in sections_with_all])

    parser = argparse.ArgumentParser(
        prog="vine_export",
        description="Export TaskVine report to static PNG and PDF from vine_parse CSV output",
        formatter_class=ExportHelpFormatter,
    )

    parser.add_argument(
        "--logs-dir",
        default=os.getcwd(),
        help="Base directory containing parsed log folders (default: current directory)",
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--templates",
        type=str,
        nargs="+",
        help="List of log directory names/patterns (must have csv-files from vine_parse)",
    )
    group.add_argument(
        "-R",
        "--recursive",
        action="store_true",
        help="Recursively find all directories with csv-files",
    )

    parser.add_argument(
        "--png-dir",
        type=str,
        default=None,
        help="Output directory for PNG files (default: {template}/png-files/ under logs-dir)",
    )

    parser.add_argument(
        "--dpi",
        type=int,
        default=DPI_DEFAULT,
        help="DPI for PNG/PDF output",
    )

    parser.add_argument(
        "--max-tasks",
        type=int,
        default=MAX_TASKS_PER_TYPE,
        help="Max tasks per type to plot (reduce if OOM)",
    )

    parser.add_argument(
        "--width",
        type=float,
        default=CANVAS_WIDTH_INCHES,
        help="Canvas width in inches",
    )
    parser.add_argument(
        "--height",
        type=float,
        default=CANVAS_HEIGHT_INCHES,
        help="Canvas height in inches",
    )

    parser.add_argument(
        "--sections",
        type=str,
        nargs="+",
        default=["all"],
        metavar="SECTION",
        help=(
            "Only export these section IDs (default: all).\n"
            "Use 'all' to export all sections.\n"
            "Available sections:\n"
            f"{sections_help_lines}"
        ),
    )

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args()
    # Resolve selected sections
    if args.sections == ["all"]:
        selected_sections = EXPORT_SECTIONS[:]
    else:
        normalized = [s.strip() for s in args.sections]
        if "all" in normalized:
            selected_sections = EXPORT_SECTIONS[:]
        else:
            invalid = [s for s in normalized if s not in EXPORT_SECTIONS]
            if invalid:
                print(f"❌ Unknown section(s): {', '.join(invalid)}")
                print(f"   Valid sections: {', '.join(sorted(EXPORT_SECTIONS))}")
                sys.exit(1)
            # Keep export arrangement consistent with front-end section order.
            selected_sections = [s for s in EXPORT_SECTIONS if s in set(normalized)]

    check_pip_updates()

    root_dir = os.path.abspath(args.logs_dir)

    if args.recursive:
        full_paths = [
            str(p.parent)
            for p in Path(root_dir).rglob("csv-files")
            if p.is_dir()
        ]
        full_paths = remove_duplicates_preserve_order(full_paths)
    else:
        matched_dirs = find_matching_directories(root_dir, args.templates)
        deduped = remove_duplicates_preserve_order(matched_dirs)
        full_paths = [os.path.join(root_dir, name) for name in deduped]

    full_paths = [str(Path(p).resolve()) for p in full_paths]
    full_paths = remove_duplicates_preserve_order(full_paths)

    # Filter: only dirs that have csv-files (vine_parse output)
    valid_paths = [p for p in full_paths if has_csv_files(p)]
    missing_csv = [p for p in full_paths if not has_csv_files(p)]

    if missing_csv:
        print("⚠️  The following directories do not contain csv-files (run vine_parse first):")
        for m in missing_csv:
            print(f"  - {m}")

    if not valid_paths:
        print("❌ No valid directories with csv-files found to export")
        sys.exit(1)

    print(f"\n✅ Exporting {len(valid_paths)} log director{'y' if len(valid_paths) == 1 else 'ies'}:")
    for path in valid_paths:
        print(f"  - {path}")

    success = 0
    failed = 0

    for template in valid_paths:
        print(f"\n=== Exporting: {template}")
        try:
            export_single_template(template, args, selected_sections)
            success += 1
            print(f"✅ Successfully exported: {template}")
        except Exception as e:
            failed += 1
            print(f"❌ Error exporting {template}")
            print(tb.format_exc())

    if success > 0:
        print(f"\n🎉 {success} director{'y' if success == 1 else 'ies'} exported successfully!")
    if failed > 0:
        print(f"❌ {failed} director{'y' if failed == 1 else 'ies'} failed to export")


if __name__ == "__main__":
    main()
