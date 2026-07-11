"""
Constants used across Personetta generator modules.

Centralizes magic strings, file extensions, directory names, and error message templates
to reduce duplication and improve maintainability.
"""

from __future__ import annotations

# ━━━ Product Identity (single source of truth) ━━━
# The rename flips these four values; every name-bearing constant below derives
# from them so the product name lives in exactly one place.
PRODUCT_NAME = "Personetta"  # display form for headings and prose
PRODUCT_SLUG = "personetta"  # CLI command and PyPI package name
ENV_PREFIX = "PERSONETTA"  # routing env-var namespace
CACHE_DIR_NAME = f".{PRODUCT_SLUG}"  # user cache directory name

# ━━━ File Extensions ━━━
MD_EXTENSION = ".md"
YAML_EXTENSION = ".yaml"
JSON_EXTENSION = ".json"
COPILOT_INSTRUCTIONS_SUFFIX = ".instructions.md"

# ━━━ Directory Names ━━━
PERSONETTA_DIR = CACHE_DIR_NAME

# Format-specific directories
CURSOR_DIR = ".cursor"
COPILOT_DIR = ".copilot"
CLAUDE_DIR = ".claude"
CLINE_DIR = ".clinerules"

# Subdirectories
CURSOR_RULES_SUBDIR = "rules"
COPILOT_INSTRUCTIONS_SUBDIR = "instructions"
CLAUDE_RULES_SUBDIR = "rules"
CLINE_RULES_SUBDIR = (
    None  # Cline uses Documents/Cline/Rules for global, .clinerules for project
)

# Skills subdirectories
SKILLS_SUBDIR = "skills"
COPILOT_WORKSPACE_SKILLS_DIR = ".github"  # Copilot uses .github/skills/ for workspace
BUNDLED_SKILLS_ROOT = (
    "bundled-skills"  # Repository bundled skills (copied to user/workspace on install)
)

# Cache subdirectories (under .personetta/)
CURSOR_RECIPES_SUBDIR = "cursor-recipes"
COPILOT_RECIPES_SUBDIR = "copilot-recipes"
CLAUDE_RECIPES_SUBDIR = "claude-recipes"
CLINE_RECIPES_SUBDIR = "cline-recipes"

# ━━━ State Files ━━━
CURSOR_STATE_FILE = "cursor-active.json"
COPILOT_STATE_FILE = "copilot-active.json"
CLAUDE_STATE_FILE = "claude-active.json"
CLINE_STATE_FILE = "cline-active.json"

# ━━━ Generated Rule File Names ━━━ (derived from PRODUCT_SLUG)
BASELINE_FILENAME = f"{PRODUCT_SLUG}-baseline"
ROUTER_FILENAME = f"{PRODUCT_SLUG}-router"
ACTIVE_FILENAME = f"{PRODUCT_SLUG}-active"

# Cursor-specific (with .md)
CURSOR_BASELINE_FILENAME = f"{BASELINE_FILENAME}.md"
CURSOR_ROUTER_FILENAME = f"{ROUTER_FILENAME}.md"
CURSOR_ACTIVE_FILENAME = f"{ACTIVE_FILENAME}.md"

# Claude/Cline-specific (with .md)
CLAUDE_BASELINE_FILENAME = f"{BASELINE_FILENAME}.md"
CLAUDE_ROUTER_FILENAME = f"{ROUTER_FILENAME}.md"
CLAUDE_ACTIVE_FILENAME = f"{ACTIVE_FILENAME}.md"

CLINE_BASELINE_FILENAME = f"{BASELINE_FILENAME}.md"
CLINE_ROUTER_FILENAME = f"{ROUTER_FILENAME}.md"
CLINE_ACTIVE_FILENAME = f"{ACTIVE_FILENAME}.md"

# Copilot-specific (with .instructions.md)
COPILOT_BASELINE_FILENAME = f"{BASELINE_FILENAME}.instructions.md"
COPILOT_ROUTER_FILENAME = f"{ROUTER_FILENAME}.instructions.md"
COPILOT_ACTIVE_FILENAME = f"{ACTIVE_FILENAME}.instructions.md"

# Copilot stems (without extension)
COPILOT_BASELINE_STEM = BASELINE_FILENAME
COPILOT_ROUTER_STEM = ROUTER_FILENAME
COPILOT_ACTIVE_STEM = ACTIVE_FILENAME

# ━━━ Error Message Templates ━━━
ERROR_NO_CACHED_RECIPE = (
    "No cached {format_title} recipe '{recipe}' at {path}. "
    f"Run: {PRODUCT_SLUG} install '*' --format {{format}}"
)

ERROR_NO_SOURCE_DIRECTORY = (
    "Source directory does not exist: {source}\n"
    f"Run \"{PRODUCT_SLUG} install '*' --format {{format}} --target global\" first."
)

ERROR_LINK_TARGET_EXISTS = (
    "Cannot create link at {link_path}: path already exists and is not a symlink/junction.\n"
    "Remove it first or use a different project directory."
)

# CLI help messages
CLI_INSTALL_HINT = f"{PRODUCT_SLUG} install '*' --format {{format}}"
CLI_INSTALL_HINT_CONSOLE = f"{PRODUCT_SLUG} install '*' --format {{format}}"

# ━━━ Glob Patterns ━━━
MARKDOWN_GLOB = "*.md"
YAML_GLOB = "*.yaml"

# ━━━ Merge Config ━━━
MERGE_CONFIG_PATH = "config/merge-config.yaml"

# ━━━ Model Recommendation Constants ━━━
# These define when guideline count forces tier/reasoning bumps
GUIDELINE_COUNT_FORCE_STANDARD_TIER = 30
GUIDELINE_COUNT_FORCE_STANDARD_REASONING = 50

# ━━━ Format Names ━━━
FORMAT_CURSOR = "cursor"
FORMAT_COPILOT = "copilot"
FORMAT_CLAUDE = "claude"
FORMAT_CLINE = "cline"

ALL_FORMATS = (FORMAT_CURSOR, FORMAT_COPILOT, FORMAT_CLAUDE, FORMAT_CLINE)
