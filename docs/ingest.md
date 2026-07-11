# Ingest

**Ingest** pulls conventions and skills that Personetta lacks from an external
source and helps you **re-author them as native Personetta content**. It is the shared
machinery behind ingesting `dotnet/skills` (Item 3), `obra/superpowers` (Item 5), and
discovering candidates from community indexes (Item 11).

It is **proposal-first and report-only**: ingest never writes Personetta roles/recipes or
auto-commits curated content. It produces a report; a human reviews it, edits the
accepted items into Personetta's voice, and merges them. Ingested items lose their original
identity — they become native Personetta content.

## Pipeline

```
fetch → parse → diff → map → report
```

1. **Fetch** — list files matching the source's `glob` via the GitHub git-trees API
   and download each (contents API). The only networked stage; failures degrade to an
   empty result rather than crashing a scan. (`ingest/fetch.py`)
2. **Parse** — normalize each `SKILL.md` (frontmatter + body) into an `IngestItem`
   (name, description, guidelines). (`ingest/parse.py`)
3. **Diff** — classify each item against existing Personetta roles/recipes as **new** or an
   **overlap** (exact normalized-name match, else token-Jaccard similarity over a
   threshold). (`ingest/diff.py`)
4. **Map** — suggest an Personetta home for each new item: a recipe (lifecycle-led name), a
   `language_specific` role (carries a language token), or a base mixin (cross-cutting
   behavior). (`ingest/mapping.py`)
5. **Report** — render a markdown proposal listing the new items (with proposed homes)
   and overlaps. (`ingest/report.py`)

## Source registry

External sources are registered in `data/tooling/ingest-sources.yaml` so scans are
repeatable and auditable:

```yaml
sources:
  dotnet-skills:
    name: dotnet/skills
    owner: dotnet
    repo: skills
    kind: skills      # skills | recipes | index
    glob: SKILL.md
```

A source is addressable by its registry key (`dotnet-skills`) or its `owner/repo`
name (`dotnet/skills`).

## CLI

```bash
personetta ingest                       # list registered sources
personetta ingest dotnet/skills         # scan, print the proposal report
personetta ingest superpowers --out build/ingest/superpowers-proposal.md
personetta ingest dotnet/skills --threshold 0.6   # stricter overlap matching
```

| Flag | Meaning |
|------|---------|
| `--threshold` | Overlap similarity cutoff, 0.0–1.0 (default 0.5). |
| `--out`, `-o` | Also write the proposal report to a file. |
| `--token` | GitHub token for the API (defaults to `$GITHUB_TOKEN`). |

Set `GITHUB_TOKEN` to raise the API rate limit for large sources.

## Recurring workflow

> discover → decide → ingest/provision → catalog

Use a community index as a discovery front-of-funnel, decide which candidates are
worth ingesting (native re-authoring) or provisioning (external install), run the
ingest scan to produce a proposal, then author the accepted items into Personetta and
regenerate. See also `docs/recipe-naming.md` for the naming grammar applied to any
new recipes.
