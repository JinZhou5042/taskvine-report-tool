#!/usr/bin/env python3
"""
vine_export command - Export TaskVine report to static PNG and PDF

Reads CSV output from vine_parse, generates static plots (PNG) for each section,
saves to png-files/, and combines into a single PDF in pdf-files/.
"""

import argparse
import os
import sys
import fnmatch
import traceback as tb
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.utils import check_pip_updates, ensure_dir
from src import __version__


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
        "csv_files": base / "csv-files",
    }


# --- Plot section IDs (aligned with vine_report modules) ---
EXPORT_SECTIONS = [
    "task-execution-details",
    "task-concurrency",
    "task-response-time",
    "task-execution-time",
    "task-retrieval-time",
    "task-completion-percentiles",
    "task-dependencies",
    "task-dependents",
    "task-subgraphs",
    "worker-concurrency",
    "worker-storage-consumption",
    "worker-incoming-transfers",
    "worker-outgoing-transfers",
    "worker-executing-tasks",
    "worker-waiting-retrieval-tasks",
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

    TODO: Implement in src.vine_export.export_plots or similar.
    Reads CSV from csv_files_dir, produces PNG in png_files_dir.
    """
    # Placeholder - actual implementation will use matplotlib/plotly/etc.
    png_path = os.path.join(png_files_dir, f"{section_id}.png")
    # Stub: create empty file or skip for now
    return png_path


def combine_pngs_to_pdf(png_paths, pdf_path, **kwargs):
    """
    Combine multiple PNG files into a single PDF.

    TODO: Implement using reportlab, img2pdf, or similar.
    """
    # Placeholder - actual implementation will merge PNGs into one PDF
    pass


def export_single_template(template_path, args):
    """Export one runtime template: PNGs + PDF."""
    dirs = get_export_dirs(template_path)
    ensure_dir(str(dirs["png_files"]), replace=False)
    ensure_dir(str(dirs["pdf_files"]), replace=False)

    csv_files_dir = dirs["csv_files"]
    png_files_dir = dirs["png_files"]
    pdf_files_dir = dirs["pdf_files"]

    if not csv_files_dir.exists():
        print(f"  ⚠️  csv-files not found, skipping: {template_path}")
        return False

    png_paths = []
    for section_id in EXPORT_SECTIONS:
        try:
            png_path = generate_plot_png(
                section_id,
                str(csv_files_dir),
                str(png_files_dir),
                dpi=getattr(args, "dpi", 150),
            )
            if png_path and os.path.exists(png_path):
                png_paths.append(png_path)
        except Exception as e:
            print(f"  ⚠️  Failed to generate {section_id}: {e}")

    if png_paths:
        pdf_name = Path(template_path).name + ".pdf"
        pdf_path = pdf_files_dir / pdf_name
        try:
            combine_pngs_to_pdf(
                png_paths,
                str(pdf_path),
                **{"dpi": getattr(args, "dpi", 150)},
            )
            print(f"  ✅ PDF: {pdf_path}")
        except Exception as e:
            print(f"  ⚠️  Failed to create PDF: {e}")
    else:
        print(f"  ⚠️  No PNGs generated, skipping PDF")

    return True


def main():
    parser = argparse.ArgumentParser(
        prog="vine_export",
        description="Export TaskVine report to static PNG and PDF from vine_parse CSV output",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
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
        "--dpi",
        type=int,
        default=150,
        help="DPI for PNG/PDF output",
    )

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args()

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
            export_single_template(template, args)
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
