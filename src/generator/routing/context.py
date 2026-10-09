"""Resolve a recipe from context (language + lifecycle) instead of prompt text.

Backs ``personetta route --json --repo <path> --language ... --lifecycle ...``.
Pure functions: language detection reads the repo tree, resolution reads recipe
names; nothing is written.
"""

from __future__ import annotations

import fnmatch
import os
import subprocess  # nosec B404 - fixed git invocation, no shell
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
    "node_modules",
    "bin",
    "obj",
    "venv",
    "__pycache__",
    "dist",
    "build",
    "site-packages",
}
# Safety nets for the non-git walk only; git checkouts are counted from the index.
MAX_DEPTH = 40
MAX_FILES = 200_000
GIT_TIMEOUT_SECONDS = 60

_EXTENSION_LANGUAGE = {
    ext: lang for lang, exts in SOURCE_EXTENSIONS.items() for ext in exts
}


def language_for_name(name: str) -> str | None:
    """Canonical language of a file name by extension, or ``None`` if unknown."""
    return _EXTENSION_LANGUAGE.get(os.path.splitext(name)[1].lower())


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
    return scan_languages(repo)[0]


def scan_languages(repo: Path) -> tuple[list[str], dict[str, int]]:
    """(languages most files first, source-file count per language) for ``repo``.

    A git checkout is counted from ``git ls-files`` (honours .gitignore, never
    sees untracked agent worktrees); anything else is walked, skipping every
    dot-folder and whatever the root .gitignore names.
    """
    scores = {lang: 0 for lang in LANGUAGES}
    present: set[str] = set()
    tracked = _git_tracked_files(repo)
    names = tracked if tracked is not None else _walk_files(repo)
    for fname in names:
        _score_file(fname, scores, present)
    found = [lang for lang in LANGUAGES if lang in present]
    ordered = sorted(found, key=lambda lang: -scores[lang])
    return ordered, {lang: scores[lang] for lang in ordered}


def _git_tracked_files(repo: Path) -> list[str] | None:
    """Base names of tracked files, or ``None`` when git is absent or unusable."""
    try:
        proc = subprocess.run(  # nosec B603 B607 - fixed args, no shell
            ["git", "-C", str(repo), "ls-files", "-z"],
            capture_output=True,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0 or not proc.stdout:
        return None
    paths = proc.stdout.decode("utf-8", errors="replace").split("\0")
    return [p.rsplit("/", 1)[-1] for p in paths if p]


def _gitignore_matcher(repo: Path):
    """Predicate (name, rel_path, is_dir) for the root .gitignore's simple patterns."""
    rules: list[tuple[str, bool, bool]] = []
    try:
        lines = (repo / ".gitignore").read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        lines = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith(("#", "!")):
            continue
        dir_only = line.endswith("/")
        anchored = "/" in line.strip("/")
        rules.append((line.strip("/"), dir_only, anchored))

    def ignored(name: str, rel: str, is_dir: bool) -> bool:
        for pattern, dir_only, anchored in rules:
            if dir_only and not is_dir:
                continue
            target = rel if anchored else name
            if fnmatch.fnmatch(target, pattern):
                return True
        return False

    return ignored


def _walk_files(repo: Path) -> list[str]:
    """File names under ``repo`` outside dot-folders, vendored dirs and .gitignore."""
    ignored = _gitignore_matcher(repo)
    names: list[str] = []
    for dirpath, dirnames, filenames in os.walk(repo):
        rel_dir = Path(dirpath).relative_to(repo).as_posix()
        prefix = "" if rel_dir == "." else rel_dir + "/"
        dirnames[:] = sorted(
            d
            for d in dirnames
            if not d.startswith(".")
            and d not in SKIP_DIRS
            and not d.endswith(".egg-info")
            and not ignored(d, prefix + d, True)
        )
        if prefix.count("/") >= MAX_DEPTH:
            dirnames[:] = []
        names.extend(f for f in filenames if not ignored(f, prefix + f, False))
        if len(names) >= MAX_FILES:
            break
    return names


def _score_file(fname: str, scores: dict[str, int], present: set[str]) -> None:
    ext = os.path.splitext(fname)[1].lower()
    for lang in LANGUAGES:
        if fname in MANIFESTS[lang] or ext in MANIFESTS[lang]:
            present.add(lang)
        if ext in SOURCE_EXTENSIONS[lang]:
            present.add(lang)
            scores[lang] += 1


def languages_for_paths(repo: Path, paths: list[str]) -> dict[str, int]:
    """Matching-path count per language for ``paths`` (relative to ``repo``).

    Uses the extension rule of the file-routed hook; unmatched paths are ignored.
    Result is ordered most paths first.
    """
    counts: dict[str, int] = {}
    for raw in paths:
        lang = language_for_name((repo / raw.strip()).name) if raw.strip() else None
        if lang is not None:
            counts[lang] = counts.get(lang, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


def recipe_family(recipe: str) -> tuple[str | None, str | None]:
    """(language, lifecycle) of a ``<lifecycle>-<language>`` family recipe.

    Recipes outside that naming (``general``, ``implement-csharp-backend``,
    ``design-diagram`` ...) are not what ``route`` resolves to, so both are ``None``.
    """
    lifecycle, _, language = recipe.partition("-")
    if lifecycle in LIFECYCLES and language in LANGUAGES:
        return language, lifecycle
    return None, None


def _format_counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{lang} {n}" for lang, n in counts.items())


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
    paths: list[str] | None = None,
) -> ContextResult:
    """Pick the recipe for (languages, lifecycle); never raises for no-match.

    Language comes from ``language_spec`` if given, else from ``paths`` when any
    matches a language, else from the repo itself.
    """
    if lifecycle not in LIFECYCLES:
        return ContextResult(False, f"unknown lifecycle '{lifecycle}'")

    if language_spec:
        languages, unknown = parse_languages(language_spec)
        if unknown or not languages:
            names = ", ".join(unknown) or language_spec
            return ContextResult(False, f"unsupported language: {names}")
        source = "language " + ",".join(languages)
    else:
        path_counts = languages_for_paths(repo, paths) if paths else {}
        if path_counts:
            languages = list(path_counts)
            source = "paths " + _format_counts(path_counts)
        else:
            if not repo.is_dir():
                return ContextResult(False, f"repo path not found: {repo}")
            languages, counts = scan_languages(repo)
            if not languages:
                return ContextResult(False, f"no supported language detected in {repo}")
            source = "detected " + _format_counts(counts)
            if paths:
                source = "no --paths entry matched a language; " + source

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
