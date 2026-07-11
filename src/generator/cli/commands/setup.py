"""Setup command - extract and run Setup-Personetta.ps1 script."""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess  # nosec B404 — invoking the bundled Setup-Personetta.ps1 script is this command's purpose
import sys
from pathlib import Path


def _get_scripts_dir() -> Path:
    """Get the location of bundled scripts directory."""
    # Try to find scripts in the package installation
    try:
        import scripts

        scripts_path = Path(scripts.__file__).parent
        if scripts_path.exists():
            return scripts_path
    except ImportError:
        pass

    # Fallback: check if we're in the repo
    repo_scripts = Path(__file__).parent.parent.parent.parent.parent / "scripts"
    if repo_scripts.exists():
        return repo_scripts

    raise FileNotFoundError(
        "Could not locate scripts directory. "
        "This may indicate the package was not installed correctly."
    )


def setup_command(args: argparse.Namespace) -> int:
    """
    Extract and optionally run Setup-Personetta.ps1.

    For feed installations, this makes setup identical to repo installations.
    """
    try:
        scripts_dir = _get_scripts_dir()
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    setup_script = scripts_dir / "Setup-Personetta.ps1"
    if not setup_script.exists():
        print(f"Error: Setup script not found at: {setup_script}", file=sys.stderr)
        return 1

    # Determine output location
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path.cwd() / "Setup-Personetta.ps1"

    # Extract script
    if args.extract_only:
        try:
            shutil.copy2(setup_script, output_path)
            print(f"✓ Extracted Setup-Personetta.ps1 to: {output_path}")
            print()
            print("Run it with:")
            if platform.system() == "Windows":
                print(f"  .\\{output_path.name}")
            else:
                print(f"  ./{output_path.name}")
            return 0
        except Exception as e:
            print(f"Error extracting script: {e}", file=sys.stderr)
            return 1

    # Run the setup script
    if platform.system() != "Windows":
        print("Error: Setup script requires Windows PowerShell", file=sys.stderr)
        print(
            "Extract the script with --extract-only and adapt for your platform",
            file=sys.stderr,
        )
        return 1

    print("Running Setup-Personetta.ps1...")
    print()

    # Build PowerShell command
    ps_args = [
        "powershell",
        "-ExecutionPolicy",
        "RemoteSigned",
        "-File",
        str(setup_script),
    ]

    # Pass through arguments
    if args.from_feed:
        ps_args.append("-FromFeed")
    if args.from_local:
        ps_args.append("-FromLocal")
    if args.pat:
        ps_args.extend(["-Pat", args.pat])
    if args.skip_profile:
        ps_args.append("-SkipProfile")
    if args.skip_path_check:
        ps_args.append("-SkipPathCheck")

    try:
        #  ps_args is built from package-internal paths plus argparse-validated flags;
        #  shell=False (default), no user-controlled string concatenation.
        result = subprocess.run(ps_args, check=False)  # nosec B603
        return result.returncode
    except Exception as e:
        print(f"Error running setup script: {e}", file=sys.stderr)
        return 1


def add_setup_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add setup command parser."""
    parser = subparsers.add_parser(
        "setup",
        help="Extract or run Setup-Personetta.ps1 (same experience as repo users)",
        description=(
            "For feed installations: Extract and run the same Setup-Personetta.ps1 "
            "that repository users use. This ensures identical setup experience."
        ),
    )

    parser.add_argument(
        "--extract-only",
        action="store_true",
        help="Only extract the script, don't run it",
    )

    parser.add_argument(
        "--output",
        "-o",
        help="Where to extract the script (default: ./Setup-Personetta.ps1)",
    )

    parser.add_argument(
        "--from-feed",
        action="store_true",
        help="Force feed installation mode",
    )

    parser.add_argument(
        "--from-local",
        action="store_true",
        help="Force local repository installation mode",
    )

    parser.add_argument(
        "--pat",
        help="Azure DevOps Personal Access Token for feed access",
    )

    parser.add_argument(
        "--skip-profile",
        action="store_true",
        help="Don't add helper functions to PowerShell profile",
    )

    parser.add_argument(
        "--skip-path-check",
        action="store_true",
        help="Skip checking/fixing PATH configuration (NOT RECOMMENDED - shows warnings)",
    )
