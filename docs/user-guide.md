# User Guide

Complete guide to using Personetta for daily work. This covers all workflows, commands, and usage patterns.

---

## Table of Contents

- [Installation Workflows](#installation-workflows)
- [Daily Usage](#daily-usage)
- [Recipe Management](#recipe-management)
- [Advanced Features](#advanced-features)
- [Tool-Specific Features](#tool-specific-features)
- [Best Practices](#best-practices)

---

## Installation Workflows

### Global vs Project Installation

```mermaid
graph TB
    Decision{Where should<br/>recipes be installed?}
    
    Decision -->|Everywhere| Global[<b>Global Install</b><br/><br/>personetta install '*'<br/>--format cursor<br/><br/>Target: User home<br/>~/.cursor/rules/]
    Decision -->|This project only| Project[<b>Project Install</b><br/><br/>personetta install '*'<br/>--format cursor<br/>--target project<br/><br/>Target: Current directory<br/>.cursor/rules/]
    
    Global --> GUse[<b>Benefits:</b><br/>✓ Available in all workspaces<br/>✓ One-time setup<br/>✓ Consistent across projects<br/><br/><b>Use when:</b><br/>- You work on many projects<br/>- Want consistent AI behavior<br/>- Don't need project-specific roles]
    
    Project --> PUse[<b>Benefits:</b><br/>✓ Project-specific personas<br/>✓ Team can share via git<br/>✓ Different rules per project<br/><br/><b>Use when:</b><br/>- Project has unique needs<br/>- Team collaboration<br/>- Override global settings]
    
    style Decision fill:#F5A623,color:#fff,stroke:#C4851C,stroke-width:3px
    style Global fill:#4A90E2,color:#fff,stroke:#2E5C8A,stroke-width:2px
    style Project fill:#9013FE,color:#fff,stroke:#6A0FB8,stroke-width:2px
    style GUse fill:#7ED321,color:#000,stroke:#5FA718
    style PUse fill:#7ED321,color:#000,stroke:#5FA718
```

### Complete Installation Flow

```mermaid
graph TB
    Start([Start Installation]) --> Check{Python 3.11+<br/>installed?}
    
    Check -->|No| InstallPy[Install Python 3.11+]
    Check -->|Yes| InstallRF[Install Personetta<br/>pip install personetta]
    InstallPy --> InstallRF
    
    InstallRF --> ChooseTool{Choose<br/>AI Tool}
    
    ChooseTool -->|Cursor| Cursor[personetta install '*'<br/>--format cursor]
    ChooseTool -->|Copilot| Copilot[personetta install '*'<br/>--format copilot]
    ChooseTool -->|Claude| Claude[personetta install '*'<br/>--format claude]
    ChooseTool -->|Cline| Cline[personetta install '*'<br/>--format cline]
    
    Cursor --> VerifyCursor{Files<br/>created?}
    Copilot --> VerifyCopilot{Files<br/>created?}
    Claude --> VerifyClaude{Files<br/>created?}
    Cline --> VerifyCline{Files<br/>created?}
    
    VerifyCursor -->|Yes| ListRecipes[personetta list]
    VerifyCopilot -->|Yes| ListRecipes
    VerifyClaude -->|Yes| ListRecipes
    VerifyCline -->|Yes| ListRecipes
    
    VerifyCursor -->|No| Debug
    VerifyCopilot -->|No| Debug
    VerifyClaude -->|No| Debug
    VerifyCline -->|No| Debug
    
    Debug[Check troubleshooting.md] --> Retry[Fix issue]
    Retry --> ChooseTool
    
    ListRecipes --> SetActive[personetta set-active<br/>your-recipe --format tool]
    SetActive --> RestartTool[Restart/Reload<br/>AI Tool]
    RestartTool --> Done([✅ Ready!])
    
    style Start fill:#4A90E2,color:#fff,stroke:#2E5C8A,stroke-width:2px
    style Check fill:#F5A623,color:#fff
    style InstallPy fill:#9013FE,color:#fff
    style InstallRF fill:#9013FE,color:#fff,stroke:#6A0FB8,stroke-width:2px
    style ChooseTool fill:#F5A623,color:#fff
    style Done fill:#7ED321,color:#000,stroke:#5FA718,stroke-width:3px
    style Debug fill:#D0021B,color:#fff
```

---

## Daily Usage

### The Set-Active Workflow

This is your most common operation - switching between recipes:

```mermaid
sequenceDiagram
    participant You
    participant CLI
    participant Cache
    participant Active
    participant Tool
    
    You->>CLI: personetta set-active<br/>implement-python --format cursor
    CLI->>Cache: Read cached recipe<br/>.personetta/cursor-recipes/<br/>implement-python.md
    Cache-->>CLI: Full recipe content
    CLI->>Active: Replace active.md<br/>with new recipe
    CLI->>CLI: Update cursor-active.json<br/>with metadata
    Active-->>CLI: ✅ File updated
    CLI-->>You: ✅ Active recipe: implement-python
    
    You->>Tool: Reload window
    Tool->>Active: Load personetta-active.md
    Tool-->>You: 🤖 Python implementation<br/>persona active
    
    Note over You,Tool: Ready to work with<br/>Python implementation guidelines
```

### Recipe Discovery Flow

```mermaid
graph TB
    Start[Need different recipe?] --> List[personetta list]
    
    List --> Browse{Found what<br/>you need?}
    
    Browse -->|Yes| Activate[personetta set-active<br/>recipe-name --format tool]
    Browse -->|No| Search[personetta list '*pattern*']
    
    Search --> Found{Found it?}
    Found -->|Yes| Activate
    Found -->|No| Custom[Create custom recipe<br/>See recipe-guide.md]
    
    Activate --> Reload[Reload AI tool]
    Custom --> Activate
    
    Reload --> Work[Start working!]
    
    style Start fill:#4A90E2,color:#fff
    style List fill:#9013FE,color:#fff
    style Browse fill:#F5A623,color:#fff
    style Activate fill:#9013FE,color:#fff,stroke:#6A0FB8,stroke-width:2px
    style Search fill:#9013FE,color:#fff
    style Found fill:#F5A623,color:#fff
    style Custom fill:#F8E71C,color:#000
    style Reload fill:#9013FE,color:#fff
    style Work fill:#7ED321,color:#000,stroke:#5FA718,stroke-width:2px
```

### Typical Daily Workflow

```mermaid
graph LR
    Morning[🌅 Start Day] --> Impl[Set: implement-python<br/><i>Write new features</i>]
    Impl --> Code1[Code for 2 hours]
    Code1 --> Review[Set: review-python<br/><i>Review PR</i>]
    Review --> CodeReview[Review teammate code]
    CodeReview --> Test[Set: test-python<br/><i>Write tests</i>]
    Test --> Testing[Write test suite]
    Testing --> Design[Set: design-python<br/><i>Plan next feature</i>]
    Design --> Planning[Architecture discussion]
    Planning --> End[🌙 End Day]
    
    style Morning fill:#4A90E2,color:#fff
    style Impl fill:#9013FE,color:#fff
    style Review fill:#9013FE,color:#fff
    style Test fill:#9013FE,color:#fff
    style Design fill:#9013FE,color:#fff
    style Code1 fill:#7ED321,color:#000
    style CodeReview fill:#7ED321,color:#000
    style Testing fill:#7ED321,color:#000
    style Planning fill:#7ED321,color:#000
    style End fill:#4A90E2,color:#fff
```

**Key insight:** Switch recipes as often as your task changes. There's no cost to switching!

---

## Recipe Management

### Listing Recipes

```bash
# List all recipes
personetta list

# List recipes matching pattern
personetta list '*python*'

# List multiple patterns
personetta list '*game*' 'test-*'
```

**Output format:**
```
Available recipes (34 total):

Design Recipes (3):
  design-csharp          Architect C# backend systems
  design-python          Architect Python backend systems
  design-powershell      Architect PowerShell infrastructure

Implementation Recipes (3):
  implement-csharp       Implement C# backend code
  implement-python       Implement Python backend code
  implement-powershell   Implement PowerShell scripts

...
```

### Installing Specific Recipes

```bash
# Install all recipes
personetta install '*' --format cursor

# Install only Python-related recipes
personetta install '*python*' --format cursor

# Install multiple patterns
personetta install 'implement-*' 'test-*' --format cursor

# Install a single recipe
personetta install 'implement-python' --format cursor
```

### Removing Recipes

```bash
# Remove all recipes
personetta remove '*' --format cursor

# Remove game-related recipes
personetta remove '*game*' --format cursor

# Remove multiple patterns
personetta remove 'design-*' 'document-*' --format cursor
```

**Removal flow:**

```mermaid
graph TB
    Remove[personetta remove<br/>'*game*' --format cursor] --> Match[Find matching recipes<br/>in cache]
    Match --> Confirm{Confirm removal?}
    
    Confirm -->|Yes| Delete[Delete cached files]
    Confirm -->|No| Cancel[Operation cancelled]
    
    Delete --> UpdateRouter[Update router.md<br/>Remove from index]
    UpdateRouter --> CheckActive{Was active<br/>recipe removed?}
    
    CheckActive -->|Yes| SetDefault[Set default active<br/>to implement-python]
    CheckActive -->|No| Keep[Keep current active]
    
    SetDefault --> Done
    Keep --> Done
    
    Done([✅ Removal complete])
    Cancel([❌ Cancelled])
    
    style Remove fill:#4A90E2,color:#fff
    style Match fill:#9013FE,color:#fff
    style Confirm fill:#F5A623,color:#fff
    style Delete fill:#D0021B,color:#fff
    style UpdateRouter fill:#9013FE,color:#fff
    style CheckActive fill:#F5A623,color:#fff
    style Done fill:#7ED321,color:#000
    style Cancel fill:#50555C,color:#fff
```

### Checking Current Recipe

```bash
# Show currently active recipe
personetta current

# For specific tool
personetta current --format cursor
```

**Output:**
```
Active recipe: implement-python
Format: cursor
Last activated: 2026-04-17 10:30:45
```

---

## Advanced Features

### Dry Run Mode

Preview changes without writing files:

```bash
# Preview installation
personetta install '*python*' --format cursor --dry-run

# Preview removal
personetta remove '*game*' --format cursor --dry-run
```

**Output shows:**
```
[DRY RUN] Would install 5 recipes:
  - implement-python
  - review-python
  - test-python
  - design-python
  - document-python

[DRY RUN] Would create files:
  - ~/.cursor/rules/personetta-baseline.md
  - ~/.cursor/rules/personetta-router.md
  - ~/.cursor/rules/personetta-active.md
  - ~/.personetta/cursor-recipes/ (5 files)
```

### Verbose Mode

See detailed operation logs:

```bash
personetta install '*' --format cursor --verbose
```

**Output includes:**
```
[DEBUG] Loading recipe: implement-python.yaml
[DEBUG] Resolving compose: base/lifecycle/implementation-developer
[DEBUG] Resolving compose: language-specific/python/python-developer
[DEBUG] Applying mixin: readability-focused
[DEBUG] Merging 3 layers...
[DEBUG] Writing to: ~/.cursor/rules/personetta-baseline.md
[DEBUG] Writing to: ~/.cursor/rules/personetta-router.md
...
```

### Validation

Validate YAML files before installation:

```bash
# Validate all recipes
personetta validate

# Validate specific recipe
personetta validate --recipe implement-python
```

**Checks:**
- YAML syntax
- Schema compliance
- Referenced layers exist
- No circular dependencies
- Tool references are valid

### Recipe Preview

See full composed output without installing:

```bash
# Preview recipe for Cursor
personetta recipe implement-python --format cursor

# Preview for different tool
personetta recipe implement-python --format copilot
```

**Use cases:**
- Debug recipe composition
- Compare different merge results
- Verify changes before installation

### Extending the Catalogue (discover → ingest → provision)

Beyond the shipped recipes, Personetta can pull in external conventions and
capabilities through a repeatable, **report-only** workflow:

> **discover → decide → ingest / provision → catalog**

```bash
# 1. Survey community indexes; see what is new vs already in Personetta
personetta discover

# 2. Re-author a useful convention/skill as native Personetta content (proposal report)
personetta ingest dotnet/skills
personetta ingest superpowers --out build/superpowers-proposal.md

# 3. Or install an external, non-persona capability (deploy-dark, opt-in)
personetta provision list
personetta provision enable claude-mem
personetta provision apply
```

`discover` and `ingest` never write Personetta content or install anything — they produce
reports for you to review. See [discovery.md](discovery.md), [ingest.md](ingest.md),
[recipe-naming.md](recipe-naming.md), and [provisions.md](provisions.md).

---

## Tool-Specific Features

### Cursor-Specific

#### User Rules Sync

Cursor install syncs to **Settings > Rules for AI**:

```bash
# Standard install (syncs User Rules)
personetta install '*' --format cursor

# Skip User Rules sync
PERSONETTA_SKIP_CURSOR_USER_SYNC=1 personetta install '*' --format cursor
```

**When Cursor is open during sync:**
- If DB is locked: Close Cursor, re-run command
- After sync: Run "Reload Window" in Cursor

#### Skills Installation

Agent skills copied to `~/.cursor/skills/` automatically:

```bash
# Skills install happens during normal install
personetta install '*' --format cursor

# Skip skills copy
PERSONETTA_SKIP_CURSOR_SKILLS=1 personetta install '*' --format cursor
```

**Available skills:**
- `/personetta-current` - Show active recipe
- `/personetta-list` - List all recipes  
- `/personetta-set-active` - Switch recipe

### Copilot-Specific

#### Custom Instructions Format

Copilot uses YAML frontmatter in `.instructions.md` files:

```markdown
---
name: 'Personetta - active persona'
description: 'Complete active recipe'
applyTo: '**'
---

# Recipe Content
...
```

#### Skills Installation

Copilot instructions under `~/.copilot/instructions/` with `applyTo: "**"` apply globally.

**Note:** Copilot skills are separate from instructions and not managed by Personetta.

### Claude-Specific

#### Session Memory

Claude loads rules from `~/.claude/rules/` each session.

```bash
# Standard install
personetta install '*' --format claude

# Skills copy to ~/.claude/skills/
# Skip with: PERSONETTA_SKIP_CLAUDE_SKILLS=1
```

### Cline-Specific

#### Global Rules Directory

Cline loads from `~/Documents/Cline/Rules/`:

```bash
# Standard install
personetta install '*' --format cline
```

---

## Best Practices

### 1. Use Global Install for Personal Work

```bash
# One-time setup for all your projects
personetta install '*' --format cursor
```

**Benefits:**
- Consistent AI behavior across projects
- No per-project setup
- Easy to switch recipes

### 2. Use Project Install for Team Projects

```bash
# In project root
personetta install '*python*' --format cursor --target project

# Commit to git
git add .cursor/rules/
git commit -m "Add Personetta Python recipes"
```

**Benefits:**
- Team shares same recipes
- Project-specific guidelines
- Version controlled

### 3. Switch Recipes Frequently

```bash
# Implementing → personetta set-active implement-python
# Reviewing → personetta set-active review-python
# Testing → personetta set-active test-python
# Planning → personetta set-active design-python
```

**Why:** Each recipe optimizes AI for that specific task.

### 4. Use Patterns for Focused Installs

```bash
# Only install what you need
personetta install '*python*' --format cursor

# Keep it focused
personetta install 'implement-*' 'test-*' --format cursor
```

**Benefits:**
- Faster cache generation
- Cleaner recipe list
- Easier to find recipes

### 5. Validate Before Large Changes

```bash
# Always validate after editing YAML
personetta validate

# Preview before installing
personetta install '*' --format cursor --dry-run
```

### 6. Use Verbose Mode for Debugging

```bash
# See exactly what's happening
personetta install '*python*' --format cursor --verbose
```

### 7. Keep Recipes Updated

```bash
# Periodically reinstall to get updates
personetta install '*' --format cursor
```

**When to reinstall:**
- After pulling recipe updates from git
- After creating new recipes
- After modifying existing recipes
- Monthly maintenance

---

## Common Patterns

### Pattern 1: Full Stack Developer

```bash
# Install backend, frontend, and test recipes
personetta install 'implement-*' 'test-*' --format cursor

# Morning: Backend work
personetta set-active implement-python --format cursor

# Afternoon: Frontend work
personetta set-active implement-javascript --format cursor

# Evening: Write tests
personetta set-active test-python --format cursor
```

### Pattern 2: Code Reviewer

```bash
# Install review recipes only
personetta install 'review-*' --format cursor

# Review Python PR
personetta set-active review-python --format cursor

# Review C# PR
personetta set-active review-csharp --format cursor
```

### Pattern 3: Technical Lead

```bash
# Install design and review recipes
personetta install 'design-*' 'review-*' --format cursor

# Architecture planning
personetta set-active design-python --format cursor

# Code review
personetta set-active review-python --format cursor
```

### Pattern 4: Game Developer

```bash
# Install game-specific recipes
personetta install '*game*' 'implement-*unity*' --format cursor

# Design game mechanics
personetta set-active design-game-mechanics --format cursor

# Implement in Unity
personetta set-active implement-game-unity --format cursor

# Test gameplay
personetta set-active test-game-unity --format cursor
```

---

## Troubleshooting

For detailed troubleshooting, see [Troubleshooting Guide](troubleshooting.md).

**Quick fixes:**

| Problem | Solution |
|---------|----------|
| Command not found | Add Python Scripts to PATH |
| Files not created | Check permissions, use `--verbose` |
| Wrong recipe active | Run `personetta current` to verify |
| AI not following guidelines | Reload/restart AI tool |
| Cache out of sync | Run `personetta install '*' --format tool` |

---

## Command Reference

See complete command documentation in [CLI Reference](cli-reference.md).

**Quick reference:**

```bash
# Installation
personetta install '<pattern>' --format <tool> [--target <global|project>]

# Activation
personetta set-active <recipe> --format <tool> [--target <global|project>]

# Management
personetta list ['<pattern>'] [<pattern2>...]
personetta remove '<pattern>' --format <tool>
personetta current [--format <tool>]

# Utilities
personetta validate [--recipe <name>]
personetta recipe <name> --format <tool>
```

---

## Next Steps

- **Create custom recipes** - [Recipe Guide](recipe-guide.md)
- **Understand internals** - [Core Concepts](concepts.md)
- **Extend Personetta** - [Extending Guide](extending.md)
- **See all diagrams** - [Visual Diagrams](diagrams.md)

---

**Questions?** See [Troubleshooting](troubleshooting.md) | [GitHub Issues](https://github.com/your-org/personetta/issues)
