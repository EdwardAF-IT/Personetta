"""Provision command - apply optional, non-persona capabilities (provisions).

    personetta provision list                     # show provisions + bundles
    personetta provision apply                     # apply all enabled provisions/bundles
    personetta provision apply status-line         # apply one named provision
    personetta provision apply --bundle economy    # apply a whole bundle in order
    personetta provision enable status-line        # flip on in the user override file
    personetta provision disable status-line
    personetta provision enable --bundle economy

Add ``--dry-run`` to any ``apply`` to preview without writing. Provisions carry
their own ``targets``, so no ``--format`` is needed; unsupported tools are
reported with a reason rather than silently skipped.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from generator.cli.commands._helpers import get_base_dir, resolve_install_target
from generator.paths import provisions_user_path
from generator.provisions import (
    apply_bundle,
    apply_enabled,
    apply_provision,
    load_provisions,
    validate_bundle,
)
from generator.provisions.models import STATUS_FAILED


def _print_results(results: list) -> int:
    """Print a result table; return 1 when any application failed."""
    if not results:
        print("No provisions applied (nothing enabled or selected).")
        return 0
    failed = 0
    for res in results:
        print(
            "  {0:24s} {1:8s} {2:18s} {3}".format(
                res.provision, res.target, res.status, res.detail
            )
        )
        if res.status == STATUS_FAILED:
            failed += 1
    return 1 if failed else 0


def _do_list(args: argparse.Namespace, config, target: Path) -> int:
    """Print every provision and bundle with its enabled state and targets."""
    print("Provisions (install root: {0})".format(target))
    for name, prov in config.provisions.items():
        state = "enabled" if prov.enabled else "disabled"
        targets = ",".join(prov.targets) or "-"
        print(
            "  {0:24s} {1:12s} {2:9s} targets={3}".format(name, prov.kind, state, targets)
        )
    if config.bundles:
        print("\nBundles:")
        for name, bundle in config.bundles.items():
            state = "enabled" if bundle.enabled else "disabled"
            members = ",".join(bundle.ordered_members())
            print("  {0:24s} {1:9s} members={2}".format(name, state, members))
    return 0


def _apply_bundle_action(args: argparse.Namespace, config, target: Path) -> int:
    """Apply a named bundle, surfacing any ordering/coverage warnings first."""
    bundle = config.bundles.get(args.bundle)
    if bundle is None:
        print("Unknown bundle: {0}".format(args.bundle), file=sys.stderr)
        return 1
    for warning in validate_bundle(config, bundle):
        print("[WARNING] bundle '{0}': {1}".format(bundle.name, warning), file=sys.stderr)
    results = apply_bundle(config, bundle, target, dry_run=args.dry_run)
    return _print_results(results)


def _apply_named(args: argparse.Namespace, config, target: Path) -> int:
    """Apply a single named provision."""
    prov = config.get(args.name)
    if prov is None:
        print("Unknown provision: {0}".format(args.name), file=sys.stderr)
        return 1
    results = apply_provision(prov, target, dry_run=args.dry_run)
    return _print_results(results)


def _do_apply(args: argparse.Namespace, config, target: Path) -> int:
    """Apply a bundle, a named provision, or all enabled provisions/bundles."""
    if args.bundle:
        return _apply_bundle_action(args, config, target)
    if args.name:
        return _apply_named(args, config, target)
    results = apply_enabled(config, target, dry_run=args.dry_run)
    return _print_results(results)


def _read_user_doc(path: Path) -> dict:
    """Read the user override document, returning ``{}`` when absent/invalid."""
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _set_enabled(target: Path, name: str, enabled: bool, *, is_bundle: bool) -> None:
    """Persist an enabled flag for one provision/bundle in the user override file."""
    path = provisions_user_path(target)
    doc = _read_user_doc(path)
    section = "bundles" if is_bundle else "provisions"
    doc.setdefault(section, {}).setdefault(name, {})["enabled"] = enabled
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")


def _toggle(args: argparse.Namespace, config, target: Path, *, enabled: bool) -> int:
    """Enable or disable a provision/bundle in the user override file."""
    is_bundle = bool(args.bundle)
    name = args.bundle if is_bundle else args.name
    if not name:
        print("Specify a provision name or --bundle <name>.", file=sys.stderr)
        return 1
    known = config.bundles if is_bundle else config.provisions
    if name not in known:
        print(
            "Unknown {0}: {1}".format("bundle" if is_bundle else "provision", name),
            file=sys.stderr,
        )
        return 1
    _set_enabled(target, name, enabled, is_bundle=is_bundle)
    verb = "Enabled" if enabled else "Disabled"
    print("{0} {1} (run 'personetta provision apply' to apply).".format(verb, name))
    return 0


def _do_enable(args: argparse.Namespace, config, target: Path) -> int:
    """Enable a provision or bundle."""
    return _toggle(args, config, target, enabled=True)


def _do_disable(args: argparse.Namespace, config, target: Path) -> int:
    """Disable a provision or bundle."""
    return _toggle(args, config, target, enabled=False)


_ACTIONS = {
    "list": _do_list,
    "apply": _do_apply,
    "enable": _do_enable,
    "disable": _do_disable,
}


def cmd_provision(args: argparse.Namespace) -> int:
    """Dispatch a provisions action (list/apply/enable/disable)."""
    base_dir = get_base_dir()
    target = resolve_install_target(args.target)
    config = load_provisions(base_dir, target)
    return _ACTIONS[args.action](args, config, target)


def add_provision_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``provision`` subcommand."""
    parser = subparsers.add_parser(
        "provision",
        help="Apply optional, non-persona capabilities (status line, plugins, behaviors)",
    )
    parser.add_argument(
        "action",
        choices=["list", "apply", "enable", "disable"],
        help="list provisions, apply enabled/selected ones, or enable/disable one",
    )
    parser.add_argument(
        "name",
        nargs="?",
        help="Provision name (for apply/enable/disable of a single provision)",
    )
    parser.add_argument(
        "--bundle",
        "-b",
        help="Operate on a named bundle instead of a single provision",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing (apply only)",
    )
    parser.add_argument(
        "--target",
        "-t",
        nargs="+",
        help="Install root: 'global' (default) or 'project [path]'",
    )
