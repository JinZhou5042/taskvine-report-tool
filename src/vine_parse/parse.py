#!/usr/bin/env python3
"""
vine_parse command - Parse TaskVine execution logs

This command parses TaskVine execution logs and generates analysis data.
"""

import argparse
import os
import sys
import fnmatch
import traceback as tb
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.vine_parse.data_parser import DataParser
from src.vine_parse.csv_manager import CSVManager
from src.utils import check_pip_updates
from src import __version__


def remove_duplicates_preserve_order(seq):
    seen = set()
    result = []
    for item in seq:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def normalize_template_pattern(raw_pattern):
    """Normalize template input to rightmost name-only pattern."""
    cleaned = str(raw_pattern).strip().strip("'\"")
    normalized_path = os.path.normpath(cleaned.rstrip("/"))
    return os.path.basename(normalized_path)


def find_matching_directories(root_dir, patterns):
    try:
        all_dirs = [d for d in os.listdir(root_dir) 
                   if os.path.isdir(os.path.join(root_dir, d))]
        
        matched_dirs = []
        for pattern in patterns:
            # Always match by rightmost name under --logs-dir only.
            cleaned_pattern = normalize_template_pattern(pattern)
            
            # check for glob pattern matching
            pattern_matches = [d for d in all_dirs if fnmatch.fnmatch(d, cleaned_pattern)]
            
            if pattern_matches:
                matched_dirs.extend(pattern_matches)
            else:
                print(f"⚠️  Pattern '{cleaned_pattern}' matched no directories")
        
        if not matched_dirs:
            print(f"❌ No directories matched any of the provided patterns in {root_dir}")
            sys.exit(1)
            
        return matched_dirs
        
    except Exception as e:
        print(f"❌ Error scanning directory {root_dir}: {e}")
        sys.exit(1)


def find_valid_dirs(root_dir: str):
    required = {"debug", "performance", "taskgraph", "transactions", "workflow.json"}
    root = Path(root_dir)
    results = []

    for path in root.rglob("*"):
        if path.is_dir():
            vine_logs = path / "vine-logs"
            if vine_logs.is_dir():
                entries = {p.name for p in vine_logs.iterdir()}
                if required.issubset(entries):
                    results.append(str(path))
    return results


def main():
    parser = argparse.ArgumentParser(
        prog='vine_parse',
        description='Parse TaskVine execution logs and generate analysis data'
    )

    parser.add_argument(
        '--logs-dir',
        default=os.getcwd(),
        help='Base directory containing log folders (default: current directory)'
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--templates', 
        type=str, 
        nargs='+',
        help='List of log directory names/patterns (matched under --logs-dir). '
             'Each item is normalized to its rightmost name. '
             'Use quotes to avoid shell pre-expansion, e.g. --templates "exp*" "test*" "checkpoint_*".'
    )

    parser.add_argument(
        '--checkpoint-pkl-files',
        action='store_true',
        help='Checkpoint pkl files'
    )

    parser.add_argument(
        '--load-pkl-files',
        action='store_true',
        help='Load pkl files'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )

    group.add_argument(
        '-R', '--recursive',
        action='store_true',
        help='Enable recursive mode'
    )

    parser.add_argument(
        '-v', '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )

    parser.add_argument(
        '--downsampling',
        type=int,
        default=1,
        help='Enable downsampling (default: 1)'
    )

    parser.add_argument(
        '--downsample-task-count',
        type=int,
        default=100000,
        help='Downsample tasks (default: 100000)'
    )

    parser.add_argument(
        '--downsample-point-count',
        type=int,
        default=10000,
        help='Downsample point count (default: 10000)'
    )

    args = parser.parse_args()

    check_pip_updates()

    root_dir = os.path.abspath(args.logs_dir)

    if args.recursive:
        full_paths = find_valid_dirs(root_dir)
    else:
        matched_dirs = find_matching_directories(root_dir, args.templates)
        deduped_names = remove_duplicates_preserve_order(matched_dirs)
        full_paths = [os.path.join(root_dir, name) for name in deduped_names]

    # resolve symlinks and deduplicate again after resolution
    full_paths = [str(Path(p).resolve()) for p in full_paths]
    full_paths = remove_duplicates_preserve_order(full_paths)

    # check if all directories exist and have vine-logs subdirectory
    missing = []
    no_vine_logs = []
    for path in full_paths:
        if not os.path.exists(path):
            missing.append(path)
        elif not os.path.exists(os.path.join(path, 'vine-logs')):
            no_vine_logs.append(path)

    if missing:
        print("❌ The following directories do not exist:")
        for m in missing:
            print(f"  - {m}")
        sys.exit(1)

    if no_vine_logs:
        print("⚠️  The following directories do not contain 'vine-logs' subdirectory:")
        for m in no_vine_logs:
            print(f"  - {m}")
        # filter out directories without vine-logs
        full_paths = [p for p in full_paths if p not in no_vine_logs]

    if not full_paths:
        print("❌ No valid log directories found to process")
        sys.exit(1)

    print(f"\n✅ The following {len(full_paths)} log directories will be processed:")
    for path in full_paths:
        print(f"  - {path}")

    # process each directory
    success = 0
    failed = 0

    for template in full_paths:
        print(f"\n=== Start parsing: {template}")
        try:
            data_parser = DataParser(template, debug_mode=args.debug, 
                                     enablee_checkpoint_pkl_files=args.checkpoint_pkl_files, 
                                    )
            if args.load_pkl_files:
                data_parser.load_pkl_files()
            else:
                data_parser.parse_logs()

            csv_manager = CSVManager(template,
                                     data_parser=data_parser,
                                     downsampling=args.downsampling > 0,
                                     downsample_task_count=args.downsample_task_count,
                                     downsample_point_count=args.downsample_point_count)
            csv_manager.generate_csv_files()
            success += 1
            print(f"✅ Successfully processed: {template}")
        except Exception as e:
            print(f"❌ Error processing {template}")
            failed += 1
            print(tb.format_exc())

    if success > 0:
        print(f"\n🎉 {success} log {'directory' if success == 1 else 'directories'} processed successfully!")
    if failed > 0:
        print(f"❌ {failed} log {'directory' if failed == 1 else 'directories'} failed to process")


if __name__ == '__main__':
    main() 