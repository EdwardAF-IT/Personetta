from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx

from generator.audit_freshness import write_audit_stamp
from generator.project_layout import ProjectLayout
from generator.validator import load_schema
from tooling.apply_obsolete import merge_proposed_obsolete
from tooling.apply_roles import (
    ApplyValidationError,
    collect_role_patches,
    unified_diff_for_patches,
    write_role_patches,
)
from tooling.config import resolve_config_dir
from tooling.report import write_reports
from tooling.scan import run_scan

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_ABORT = 2


def _build_parser() -> argparse.ArgumentParser:
    epilog = """
Examples:
  python -m tooling --repo-root . --output-dir .personetta/audit-reports
  python -m tooling --apply --yes --apply-obsolete
  python -m tooling --diff --output-dir .personetta/audit-reports
  python -m tooling --tier3-readme
  python -m tooling --apply --apply-registry-removals

Exit codes:
  0  Success
  1  Validation error, I/O error, or HTTP failure during scan
  2  User declined an interactive prompt (obsolete merge)
""".strip()
    p = argparse.ArgumentParser(
        prog="python -m tooling",
        description="Tool-corpus auditor: scan role YAML for policy and registry lifecycle signals; optional apply.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )
    p.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="Repository root (default: current directory)",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path(".personetta/audit-reports"),
        help="Directory for audit-report.json, audit-report.md, and optional diff",
    )
    p.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Override tooling data directory (default: <repo-root>/tooling/data or package data)",
    )
    p.add_argument(
        "--apply",
        action="store_true",
        help="Remove tools from role YAML per findings (ruamel round-trip); validate before write",
    )
    p.add_argument(
        "--apply-obsolete",
        action="store_true",
        help="Merge proposed obsolete entries into tooling/data/obsolete.yaml (with --yes, prompt, or non-TTY skip)",
    )
    p.add_argument(
        "--yes",
        action="store_true",
        help="Non-interactive confirmation for --apply-obsolete",
    )
    p.add_argument(
        "--no",
        action="store_true",
        help="Skip obsolete merge without prompting",
    )
    p.add_argument(
        "--skip-obsolete-merge",
        action="store_true",
        help="Do not write obsolete.yaml even if --apply-obsolete is set",
    )
    p.add_argument(
        "--diff",
        action="store_true",
        help="Write audit-diff.patch (unified diff for role files that would change)",
    )
    p.add_argument(
        "--apply-registry-removals",
        action="store_true",
        help="With --apply, also remove tools flagged npm_deprecated or nuget_deprecated (not default)",
    )
    p.add_argument(
        "--tier3-readme",
        action="store_true",
        help="Enable Tier-3 GitHub README lifecycle phrase scan (overrides domains.yaml when set)",
    )
    p.add_argument(
        "--no-tier3-readme",
        action="store_true",
        help="Disable Tier-3 README scan even if enabled in domains.yaml",
    )
    return p


def _confirm_obsolete_merge(count: int) -> bool:
    try:
        reply = input(
            f"Apply {count} proposed obsolete entries to tooling/data/obsolete.yaml? [y/N] "
        )
    except EOFError:
        return False
    return reply.strip().lower() in {"y", "yes"}


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    repo_root: Path = args.repo_root.resolve()
    output_dir: Path = args.output_dir
    config_dir = resolve_config_dir(repo_root, args.config_dir)

    if args.yes and args.no:
        print("--yes and --no cannot be used together", file=sys.stderr)
        return EXIT_ERROR
    if args.tier3_readme and args.no_tier3_readme:
        print(
            "--tier3-readme and --no-tier3-readme cannot be used together",
            file=sys.stderr,
        )
        return EXIT_ERROR

    # Use ProjectLayout to get correct schema path
    layout = ProjectLayout(repo_root)
    role_schema_path = layout.schemas / "base-role.schema.json"
    if not role_schema_path.is_file():
        print(f"Missing role schema: {role_schema_path}", file=sys.stderr)
        return EXIT_ERROR

    try:
        role_schema = load_schema(role_schema_path)
    except OSError as e:
        print(f"Cannot read schema: {e}", file=sys.stderr)
        return EXIT_ERROR

    tier3_kw: dict[str, bool] = {}
    if args.tier3_readme:
        tier3_kw["tier3_readme"] = True
    elif args.no_tier3_readme:
        tier3_kw["no_tier3_readme"] = True

    try:
        with httpx.Client(follow_redirects=True) as client:
            report = run_scan(repo_root, client, config_dir=config_dir, **tier3_kw)
    except httpx.HTTPError as e:
        print(f"Scan failed (HTTP): {e}", file=sys.stderr)
        return EXIT_ERROR
    except OSError as e:
        print(f"Scan failed: {e}", file=sys.stderr)
        return EXIT_ERROR

    output_dir.mkdir(parents=True, exist_ok=True)
    write_reports(report, output_dir)

    if args.diff:
        diff_text = unified_diff_for_patches(
            repo_root,
            report,
            apply_registry_removals=args.apply_registry_removals,
        )
        (output_dir / "audit-diff.patch").write_text(diff_text, encoding="utf-8")

    if args.apply:
        try:
            patches = collect_role_patches(
                repo_root,
                report,
                role_schema,
                apply_registry_removals=args.apply_registry_removals,
            )
        except ApplyValidationError as e:
            for msg in e.errors:
                print(f"{e.path}: {msg}", file=sys.stderr)
            return EXIT_ERROR
        write_role_patches(patches)
        try:
            write_audit_stamp(repo_root)
        except OSError as e:
            print(f"Could not write audit stamp: {e}", file=sys.stderr)
            return EXIT_ERROR

    if args.apply_obsolete and not args.skip_obsolete_merge:
        proposals = report.proposed_obsolete_additions
        if proposals:
            do_merge = False
            if args.yes:
                do_merge = True
            elif args.no:
                do_merge = False
            elif sys.stdin.isatty():
                do_merge = _confirm_obsolete_merge(len(proposals))
                if not do_merge:
                    return EXIT_ABORT
            else:
                print(
                    "Skipping obsolete.yaml merge (non-interactive stdin; use --yes to apply).",
                    file=sys.stderr,
                )
                do_merge = False

            if do_merge:
                obsolete_path = config_dir / "obsolete.yaml"
                try:
                    new_text = merge_proposed_obsolete(obsolete_path, proposals)
                    obsolete_path.parent.mkdir(parents=True, exist_ok=True)
                    obsolete_path.write_text(new_text, encoding="utf-8")
                except OSError as e:
                    print(f"Failed to write {obsolete_path}: {e}", file=sys.stderr)
                    return EXIT_ERROR

    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
