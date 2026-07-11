# Discovery

**Discovery** turns ad-hoc browsing of community indexes (like
`hesreallyhim/awesome-claude-code`) into a repeatable step. It fetches an index,
lists candidate skills/plugins, and **flags which already exist in Personetta** — so you can
see at a glance what is genuinely new.

Discovery is **report-only**: it installs nothing and writes no Personetta content. It is the
front-of-funnel for the recurring workflow:

> **discover → decide → ingest/provision → catalog**

1. **discover** — survey an index for candidates and flag overlaps with Personetta.
2. **decide** — a human picks what is worth pursuing.
3. **ingest / provision** — re-author a convention natively (see
   [ingest.md](ingest.md)) or install an external capability (see
   [provisions.md](provisions.md)).
4. **catalog** — Personetta remains the system of record (`skills-catalog.json`).

## How it works

Discovery reuses the ingest machinery. Index sources (`kind: index` in
`data/tooling/ingest-sources.yaml`) are markdown link lists rather than `SKILL.md`
frontmatter, so they are parsed by `ingest/index_parse.py` (bulleted
`- [Name](url) - description` entries). Candidates are then run through the same
diff as ingest to classify each as **new** or **already in Personetta**.

## CLI

```bash
personetta discover                              # scan all registered index sources
personetta discover --source awesome-claude-code # scan one source
personetta discover --out build/discovery.md     # also write the report
personetta discover --threshold 0.6              # stricter overlap matching
```

| Flag | Meaning |
|------|---------|
| `--source`, `-s` | Index source key or `owner/repo` (default: all `index`-kind sources). |
| `--threshold` | Overlap similarity cutoff, 0.0–1.0 (default 0.5). |
| `--out`, `-o` | Also write the discovery report to a file. |
| `--token` | GitHub token for the API (defaults to `$GITHUB_TOKEN`). |

The report has three parts: a summary count, **new candidates** (with their source
link), and **already in Personetta** (with the Personetta role/recipe each overlaps and a match
score). Set `GITHUB_TOKEN` to raise the API rate limit.
