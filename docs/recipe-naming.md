# Recipe naming grammar

Personetta recipe names follow a small, enforced grammar so the catalogue stays
predictable as it grows:

```
<lifecycle>-<domain>[-<facet>]
```

- **lifecycle** (closed set): `design`, `implement`, `review`, `test`, `debug`,
  `document`, `write`, `edit`.
- **domain** (closed set): a language (`csharp`, `powershell`, `python`, `tsql`,
  `javascript`) **or** an area (`devops`, `game`, `config`, `agent`, `web`, `data`,
  `api`).
- **facet** (closed set, **at most one**): e.g. `backend`, `frontend`, `infra`,
  `secure`, `perf`, `scale`, `automation`, `database`, `unity`, plus domain
  sub-types like `balance`/`mechanics`/`levels` (game) or `roles`/`prompts` (agent).

The full vocabularies live in `data/config/recipe-naming.yaml`.

## The one-facet rule

Compound needs are expressed by **composition / mixins**, not by stacking facets in
the name. So instead of `implement-csharp-backend-secure`, the canonical form is
`implement-csharp-backend` composed with the `security-aware` mixin. This keeps names
short and prevents the combinatorial explosion of `*-backend-secure-perf-…`.

## Enforcement (ratchet) and migration

`tests/quality/workspace/test_conventions.py::test_recipe_names_follow_grammar`
validates every shipped recipe name against the grammar. It **ratchets**:

- A **new** recipe whose name violates the grammar fails the test.
- **Legacy** names that predate the grammar are listed under `grandfathered` in
  `recipe-naming.yaml` and are tolerated until renamed.

When you rename a legacy recipe to the canonical form:

1. Rename the file and update the recipe `name`.
2. Add the old name as an **alias** (aliases persist indefinitely — no forced
   removal window; see `docs/cli-reference.md`).
3. Remove the old name from `grandfathered`.

## Adding to the vocabulary

If a genuinely new domain or facet is needed, add it to the appropriate closed set
in `data/config/recipe-naming.yaml`. Prefer reusing an existing term; the closed sets
exist to resist drift, so expand them deliberately.
