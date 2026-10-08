"""Resolve a recipe from context (language + lifecycle) instead of prompt text.

Backs ``personetta route --json --repo <path> --language ... --lifecycle ...``.
Pure functions: language detection reads the repo tree, resolution reads recipe
names; nothing is written.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from generator.recipe_export import export_recipe

LIFECYCLES = ("implement", "review", "test", "debug", "design")
DEFAULT_LIFECYCLE = "implement"

# Canonical language -> recipe-name suffix (recipes are "<lifecycle>-<suffix>").
LANGUAGES = ("csharp", "javascript", "python", "powershell", "tsql")

ALIASES = {
    "csharp": "csharp",
    "c#": "csharp",
    "cs": "csharp",
    "dotnet": "csharp",
    "javascript": "javascript",
    "js": "javascript",
    "typescript": "javascript",
    "ts": "javascript",
    "node": "javascript",
    "python": "python",
    "py": "python",
    "powershell": "powershell",
    "pwsh": "powershell",
    "ps": "powershell",
    "tsql": "tsql",
    "t-sql": "tsql",
    "sql": "tsql",
}

# Files that prove a language is present (manifests count once each).
MANIFESTS = {
    "csharp": {".csproj", ".sln", ".slnx", ".fsproj"},
    "javascript": {"package.json", "tsconfig.json"},
    "python": {"pyproject.toml", "setup.py", "requirements.txt", "setup.cfg"},
    "powershell": {".psd1", ".psm1"},
    "tsql": {".sqlproj"},
}
SOURCE_EXTENSIONS = {
    "csharp": {".cs"},
    "javascript": {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"},
    "python": {".py"},
    "powershell": {".ps1", ".psm1"},
    "tsql": {".sql"},
}

SKIP_DIRS = {
    ".git",
    "node_modules",
    "bin",
    "obj",
    ".venv",
    "venv",
    "__pycache__",
    ".tox",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
    "site-packages",
}
MAX_DEPTH = 4
MAX_FILES = 5000


@dataclass
class ContextResult:
    """Outcome of a context resolution; ``ok`` False means exit code 2."""

    ok: bool
    reason: str
    primary: dict | None = None
    also: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """JSON-ready form: the primary export identity plus ``also`` if any."""
        if not self.ok or self.primary is None:
            return {"recipe": None, "reason": self.reason}
        doc = dict(self.primary)
        doc["reason"] = self.reason
        if self.also:
            doc["also"] = self.also
        return doc


def normalize_language(raw: str) -> str | None:
    """Map a user-supplied language name or alias to its canonical name."""
    return ALIASES.get(raw.strip().lower())


def parse_languages(spec: str) -> tuple[list[str], list[str]]:
    """Split ``a,b,c`` into (canonical languages, unknown names), deduplicated."""
    known: list[str] = []
    unknown: list[str] = []
    for part in spec.split(","):
        if not part.strip():
            continue
        lang = normalize_language(part)
        if lang is None:
            unknown.append(part.strip())
        elif lang not in known:
            known.append(lang)
    return known, unknown


def detect_languages(repo: Path) -> list[str]:
    """Languages present in ``repo``, most source files first (stable on ties)."""
    scores = {lang: 0 for lang in LANGUAGES}
    present: set[str] = set()
    seen = 0
    root_depth = len(repo.parts)
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        if len(Path(dirpath).parts) - root_depth >= MAX_DEPTH:
            dirnames[:] = []
        for fname in filenames:
            seen += 1
            _score_file(fname, scores, present)
        if seen >= MAX_FILES:
            break
    found = [lang for lang in LANGUAGES if lang in present]
    return sorted(found, key=lambda lang: -scores[lang])


def _score_file(fname: str, scores: dict[str, int], present: set[str]) -> None:
    ext = os.path.splitext(fname)[1].lower()
    for lang in LANGUAGES:
        if fname in MANIFESTS[lang] or ext in MANIFESTS[lang]:
            present.add(lang)
        if ext in SOURCE_EXTENSIONS[lang]:
            present.add(lang)
            scores[lang] += 1


def _identity(recipe: str, language: str, base_dir: Path) -> tuple[dict | None, str]:
    """Export identity (recipe/version/hash) for one recipe, or an error reason."""
    doc, _warnings = export_recipe(recipe, base_dir)
    if not doc:
        return None, f"recipe {recipe} failed to compose"
    return {
        "recipe": doc["recipe"],
        "language": language,
        "version": doc["version"],
        "hash": doc["hash"],
    }, ""


def resolve_context(
    *,
    repo: Path,
    language_spec: str | None,
    lifecycle: str,
    recipe_names: set[str],
    base_dir: Path,
) -> ContextResult:
    """Pick the recipe for (languages, lifecycle); never raises for no-match."""
    if lifecycle not in LIFECYCLES:
        return ContextResult(False, f"unknown lifecycle '{lifecycle}'")

    if language_spec:
        languages, unknown = parse_languages(language_spec)
        if unknown or not languages:
            names = ", ".join(unknown) or language_spec
            return ContextResult(False, f"unsupported language: {names}")
        source = "language " + ",".join(languages)
    else:
        if not repo.is_dir():
            return ContextResult(False, f"repo path not found: {repo}")
        languages = detect_languages(repo)
        if not languages:
            return ContextResult(False, f"no supported language detected in {repo}")
        source = "detected " + ",".join(languages)

    found: list[dict] = []
    missing: list[str] = []
    for lang in languages:
        name = f"{lifecycle}-{lang}"
        if name not in recipe_names:
            missing.append(name)
            continue
        identity, err = _identity(name, lang, base_dir)
        if identity is None:
            return ContextResult(False, err)
        found.append(identity)

    if not found:
        return ContextResult(False, f"no recipe fits: {source}, lifecycle {lifecycle}")

    reason = f"{source}, lifecycle {lifecycle}"
    if missing:
        reason += f" (no recipe: {', '.join(missing)})"
    return ContextResult(True, reason, found[0], found[1:])
