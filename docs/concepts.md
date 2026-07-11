# Core Concepts

This guide explains how Personetta works under the hood. Understanding these concepts will help you use Personetta effectively and extend it when needed.

---

## Table of Contents

- [System Architecture](#system-architecture)
- [The Three-File Pattern](#the-three-file-pattern)
- [Recipe Composition](#recipe-composition)
- [Layers and Mixins](#layers-and-mixins)
- [Merge Strategies](#merge-strategies)
- [The Generation Pipeline](#the-generation-pipeline)
- [Multi-Tool Support](#multi-tool-support)
- [Cache and State](#cache-and-state)

---

## System Architecture

Personetta transforms YAML recipes into tool-specific configuration files. Here's the complete flow:

```mermaid
graph TB
    subgraph "📄 Input: YAML Definitions"
        Recipe[<b>Recipe YAML</b><br/>implement-python.yaml<br/><br/>compose:<br/>- base/lifecycle/implementation<br/>- language-specific/python<br/><br/>mixins:<br/>- readability-focused<br/>- performance-focused]
        Base[<b>Base Layers</b><br/>data/base/<br/><br/>Core behaviors:<br/>- lifecycle patterns<br/>- system prompts<br/>- tool preferences]
        Lang[<b>Language Layers</b><br/>data/language_specific/<br/><br/>Language knowledge:<br/>- Python<br/>- C#<br/>- PowerShell]
        Mixin[<b>Mixins</b><br/>Cross-cutting:<br/>- performance-focused<br/>- security-aware<br/>- readability-focused]
    end
    
    subgraph "🔄 Processing: Generation Engine"
        Loader[<b>loader.py</b><br/>📥 Load & Validate<br/><br/>- Read YAML files<br/>- Validate against schema<br/>- Resolve references]
        Merger[<b>merger.py</b><br/>🔀 Compose Layers<br/><br/>- Apply merge strategies<br/>- Deduplicate content<br/>- Handle conflicts]
        Pipeline[<b>pipeline.py</b><br/>⚙️ Generate Output<br/><br/>- Format for each tool<br/>- Apply templates<br/>- Write files]
    end
    
    subgraph "📤 Output: Format Generators"
        Cursor[<b>cursor_layout.py</b><br/>Cursor Rules<br/><br/>- .cursor/rules/<br/>- User Rules sync<br/>- Skills copy]
        Copilot[<b>copilot_layout.py</b><br/>Copilot Instructions<br/><br/>- .copilot/instructions/<br/>- YAML frontmatter<br/>- applyTo patterns]
        Claude[<b>claude_layout.py</b><br/>Claude Rules<br/><br/>- .claude/rules/<br/>- Markdown format<br/>- Session loading]
        Cline[<b>cline_layout.py</b><br/>Cline Rules<br/><br/>- ~/Documents/Cline/<br/>- Global rules<br/>- Per-session load]
    end
    
    subgraph "📂 Output: Installed Files"
        CursorOut[~/.cursor/rules/<br/>✓ baseline.md<br/>✓ router.md<br/>✓ active.md<br/>+ cache/]
        CopilotOut[~/.copilot/instructions/<br/>✓ baseline.instructions.md<br/>✓ router.instructions.md<br/>✓ active.instructions.md<br/>+ cache/]
        ClaudeOut[~/.claude/rules/<br/>✓ baseline.md<br/>✓ router.md<br/>✓ active.md<br/>+ cache/]
        ClineOut[~/Documents/Cline/Rules/<br/>✓ baseline.md<br/>✓ router.md<br/>✓ active.md<br/>+ cache/]
    end
    
    Recipe --> Loader
    Base --> Loader
    Lang --> Loader
    Mixin --> Loader
    
    Loader --> Merger
    Merger --> Pipeline
    
    Pipeline --> Cursor
    Pipeline --> Copilot
    Pipeline --> Claude
    Pipeline --> Cline
    
    Cursor --> CursorOut
    Copilot --> CopilotOut
    Claude --> ClaudeOut
    Cline --> ClineOut
    
    style Recipe fill:#F8E71C,color:#000,stroke:#C4B519,stroke-width:3px
    style Base fill:#F8E71C,color:#000,stroke:#C4B519,stroke-width:2px
    style Lang fill:#F8E71C,color:#000,stroke:#C4B519,stroke-width:2px
    style Mixin fill:#F8E71C,color:#000,stroke:#C4B519,stroke-width:2px
    
    style Loader fill:#9013FE,color:#fff,stroke:#6A0FB8,stroke-width:2px
    style Merger fill:#9013FE,color:#fff,stroke:#6A0FB8,stroke-width:2px
    style Pipeline fill:#9013FE,color:#fff,stroke:#6A0FB8,stroke-width:2px
    
    style Cursor fill:#4A90E2,color:#fff,stroke:#2E5C8A,stroke-width:2px
    style Copilot fill:#4A90E2,color:#fff,stroke:#2E5C8A,stroke-width:2px
    style Claude fill:#4A90E2,color:#fff,stroke:#2E5C8A,stroke-width:2px
    style Cline fill:#4A90E2,color:#fff,stroke:#2E5C8A,stroke-width:2px
    
    style CursorOut fill:#7ED321,color:#000,stroke:#5FA718,stroke-width:3px
    style CopilotOut fill:#7ED321,color:#000,stroke:#5FA718,stroke-width:3px
    style ClaudeOut fill:#7ED321,color:#000,stroke:#5FA718,stroke-width:3px
    style ClineOut fill:#7ED321,color:#000,stroke:#5FA718,stroke-width:3px
```

### Key Insights

1. **YAML as Source of Truth** (🟡 Yellow) - All recipes start as human-editable YAML files
2. **Composable Layers** - Recipes reference base layers, language knowledge, and mixins
3. **Tool-Agnostic Core** (🟣 Purple) - The merger doesn't know about specific AI tools
4. **Format-Specific Output** (🔵 Blue) - Each tool gets its own specialized generator
5. **Consistent Structure** (🟢 Green) - All tools get the same three-file pattern + cache

---

## The Three-File Pattern

This is **the most important concept** in Personetta. Every tool gets exactly three files plus a cache directory:

```mermaid
graph TB
    subgraph "The Three-File Pattern"
        direction TB
        
        subgraph "1. Baseline (Always On)"
            B["<b>personetta-baseline.md</b><br/><br/>📏 Size: ~100 lines<br/><br/>Purpose: Orchestration<br/><br/>Content:<br/>✓ Check model recommendation<br/>✓ Verify work alignment<br/>✓ Honor active persona<br/>✓ Run verification checks<br/>✓ Report compliance<br/><br/>When loaded: <b>Every conversation</b>"]
        end
        
        subgraph "2. Router (Context-Aware)"
            R["<b>personetta-router.md</b><br/><br/>📏 Size: ~200 lines<br/><br/>Purpose: Discovery & Navigation<br/><br/>Content:<br/>✓ All recipe IDs<br/>✓ Recipe summaries<br/>✓ set-active commands<br/>✓ Activation phrases<br/>✓ When to use each<br/><br/>When loaded: <b>When contextually relevant</b>"]
        end
        
        subgraph "3. Active (Full Persona)"
            A["<b>personetta-active.md</b><br/><br/>📏 Size: 800-1200 lines<br/><br/>Purpose: Complete AI Persona<br/><br/>Content:<br/>✓ All guidelines (30-50+)<br/>✓ All tools (20-40+)<br/>✓ Examples<br/>✓ Verification checklist<br/>✓ Tone & format<br/><br/>When loaded: <b>Every conversation</b>"]
        end
    end
    
    subgraph "Cache Directory"
        Cache["<b>.personetta/tool-recipes/</b><br/><br/>Contains: All recipe bodies<br/>Used for: Fast set-active switching<br/>Updated: During install"]
    end
    
    User[👤 User] -->|Runs CLI| SetActive[personetta set-active<br/>implement-python]
    SetActive -->|Reads from| Cache
    SetActive -->|Replaces| A
    
    AI[🤖 AI Tool] -->|Loads every turn| B
    AI -->|Loads every turn| A
    AI -->|Loads when relevant| R
    
    B -.->|"Instructs: Use active persona"| A
    R -.->|"Lists all recipes + cache paths"| Cache
    
    style B fill:#4A90E2,color:#fff,stroke:#2E5C8A,stroke-width:4px
    style R fill:#F5A623,color:#fff,stroke:#C4851C,stroke-width:4px
    style A fill:#7ED321,color:#000,stroke:#5FA718,stroke-width:4px
    style Cache fill:#50555C,color:#fff,stroke:#3A3F44,stroke-width:2px
    style User fill:#4A90E2,color:#fff
    style SetActive fill:#9013FE,color:#fff,stroke:#6A0FB8,stroke-width:2px
    style AI fill:#50555C,color:#fff
```

### Why This Pattern?

**Problem:** Loading ALL recipes simultaneously wastes context and confuses the AI.

**Solution:** 
- **Baseline** provides thin orchestration (always loaded, minimal tokens)
- **Router** enables discovery without loading full content (loaded when needed)
- **Active** carries ONE complete persona (always loaded)
- **Cache** enables instant switching without regeneration

### Context Efficiency

| Approach | Tokens Used | Result |
|----------|-------------|--------|
| ❌ Load all 27 recipes | ~30,000 tokens | Confused AI, wasted context |
| ❌ Make user choose every time | ~100 tokens | Poor UX, no defaults |
| ✅ Three-file pattern | ~1,500 tokens | Clear role, fast switching |

---

## Recipe Composition

Recipes are built from composable layers. This is how a single recipe YAML becomes a complete AI persona:

```mermaid
graph LR
    subgraph "Base Layer<br/>(Workflow)"
        direction TB
        B1["<b>Guidelines</b><br/>- Use tools first<br/>- Verify work<br/>- Document decisions"]
        B2["<b>Tone</b><br/>Professional"]
        B3["<b>Should Do</b><br/>- Evaluate options<br/>- Test thoroughly"]
    end
    
    subgraph "Language Layer<br/>(Python)"
        direction TB
        L1["<b>Guidelines</b><br/>- PEP 8 style<br/>- Type hints<br/>- Docstrings"]
        L2["<b>Tools</b><br/>- pytest<br/>- black<br/>- mypy"]
        L3["<b>Should Do</b><br/>- Idiomatic code<br/>- Error handling"]
    end
    
    subgraph "Mixin Layer<br/>(Performance)"
        direction TB
        M1["<b>Guidelines</b><br/>- Profile first<br/>- O(n) analysis<br/>- Benchmark"]
        M2["<b>Tools</b><br/>- cProfile<br/>- memory_profiler"]
    end
    
    subgraph "Merged Recipe<br/>(implement-python-backend-perf)"
        direction TB
        R1["<b>All Guidelines</b><br/>✓ Use tools first<br/>✓ Verify work<br/>✓ PEP 8 style<br/>✓ Type hints<br/>✓ Profile first<br/>✓ O(n) analysis<br/><i>(30+ total)</i>"]
        R2["<b>Tone</b><br/>Professional<br/><i>(from base)</i>"]
        R3["<b>All Tools</b><br/>✓ pytest<br/>✓ black<br/>✓ mypy<br/>✓ cProfile<br/>✓ memory_profiler<br/><i>(40+ total)</i>"]
        R4["<b>All Shoulds</b><br/>✓ Evaluate options<br/>✓ Test thoroughly<br/>✓ Idiomatic code<br/>✓ Error handling<br/><i>(15+ total)</i>"]
    end
    
    B1 --> R1
    L1 --> R1
    M1 --> R1
    
    B2 --> R2
    
    L2 --> R3
    M2 --> R3
    
    B3 --> R4
    L3 --> R4
    
    style B1 fill:#4A90E2,color:#fff,stroke:#2E5C8A,stroke-width:2px
    style B2 fill:#4A90E2,color:#fff,stroke:#2E5C8A
    style B3 fill:#4A90E2,color:#fff,stroke:#2E5C8A
    
    style L1 fill:#9013FE,color:#fff,stroke:#6A0FB8,stroke-width:2px
    style L2 fill:#9013FE,color:#fff,stroke:#6A0FB8
    style L3 fill:#9013FE,color:#fff,stroke:#6A0FB8
    
    style M1 fill:#F5A623,color:#fff,stroke:#C4851C,stroke-width:2px
    style M2 fill:#F5A623,color:#fff,stroke:#C4851C
    
    style R1 fill:#7ED321,color:#000,stroke:#5FA718,stroke-width:3px
    style R2 fill:#7ED321,color:#000,stroke:#5FA718
    style R3 fill:#7ED321,color:#000,stroke:#5FA718,stroke-width:3px
    style R4 fill:#7ED321,color:#000,stroke:#5FA718
```

### Composition Benefits

1. **Reusability** - Base layers used across multiple recipes
2. **Maintainability** - Update one layer, all recipes using it benefit
3. **Consistency** - Common patterns stay consistent
4. **Flexibility** - Mix and match to create new personas

---

## Layers and Mixins

Personetta has three types of composable elements:

### 1. Base Layers (`data/base/`)

**Purpose:** Workflow patterns and lifecycle stages

**Categories:**
- **lifecycle/** - Implementation, review, test, design workflows
- **layer/** - Backend developer, frontend developer, infrastructure
- **system/** - Core system prompts
- **mixins/** - Cross-cutting concerns (bundled with base)

**Example:**
```yaml
# data/base/lifecycle/implementation-developer.yaml
name: implementation-developer
guidelines:
  - "Use existing tools and libraries before writing custom code"
  - "Write tests alongside implementation code"
  - "Document non-obvious decisions with comments"
should:
  - "Implement features completely and correctly"
  - "Handle error cases explicitly"
  - "Follow established patterns in the codebase"
```

### 2. Language-Specific Layers (`data/language_specific/`)

**Purpose:** Language and framework knowledge

**Categories:**
- **python/** - PEP 8, type hints, pytest, etc.
- **csharp/** - .NET conventions, xUnit, async/await
- **powershell/** - PowerShell best practices, Pester
- **javascript/** - ESNext, Jest, npm
- **tsql/** - SQL Server, query optimization

**Example:**
```yaml
# data/language_specific/python/python-developer.yaml
name: python-developer
guidelines:
  - "Follow PEP 8 style guide for Python code"
  - "Use type hints for function parameters and return values"
  - "Write docstrings for all public functions and classes"
tools:
  - name: pytest
    when: "Testing Python code"
  - name: black
    when: "Auto-formatting Python code"
  - name: mypy
    when: "Type checking Python code"
```

### 3. Mixins (`compose.mixins` in recipe)

**Purpose:** Cross-cutting concerns that apply regardless of workflow or language

**Available:**
- `readability-focused` - Code clarity and documentation
- `performance-focused` - Optimization and profiling
- `security-aware` - Security best practices
- `maintainability-focused` - Long-term code health
- `scalability-focused` - Horizontal scaling patterns

**Example:**
```yaml
# In recipe YAML
compose:
  - base/lifecycle/implementation-developer
  - language-specific/python/python-developer
mixins:
  - readability-focused
  - performance-focused
```

### Layer Hierarchy

```mermaid
graph TD
    Recipe[Recipe YAML] --> Base[Base Layer<br/>Workflow pattern]
    Recipe --> Lang[Language Layer<br/>Technical knowledge]
    Recipe --> Mixin[Mixins<br/>Cross-cutting concerns]
    
    Base --> Lifecycle[lifecycle/<br/>implement, review, test, design]
    Base --> Layer[layer/<br/>backend, frontend, infra]
    Base --> System[system/<br/>Core prompts]
    
    Lang --> Python[python/<br/>PEP 8, pytest, type hints]
    Lang --> CSharp[csharp/<br/>.NET, xUnit, async]
    Lang --> PowerShell[powershell/<br/>Pester, idiomatic PS]
    Lang --> More[...]
    
    Mixin --> Perf[performance-focused<br/>Profile, optimize]
    Mixin --> Read[readability-focused<br/>Clarity, docs]
    Mixin --> Sec[security-aware<br/>Threat modeling]
    Mixin --> More2[...]
    
    style Recipe fill:#F8E71C,color:#000
    style Base fill:#4A90E2,color:#fff
    style Lang fill:#9013FE,color:#fff
    style Mixin fill:#F5A623,color:#fff
```

---

## Merge Strategies

When layers combine, Personetta uses different strategies for different field types:

```mermaid
graph TB
    subgraph "Append Strategy (Lists)"
        A1[["Base:<br/>[a, b]"]]
        A2[["Layer:<br/>[c, d]"]]
        A1 --> M1[["<b>Result:</b><br/>[a, b, c, d]"]]
        A2 --> M1
    end
    
    subgraph "First Wins (Scalars)"
        S1[["Base:<br/>'Professional'"]]
        S2[["Layer:<br/>'Casual'"]]
        S1 --> M2[["<b>Result:</b><br/>'Professional'"]]
        S2 -.->|ignored| M2
    end
    
    subgraph "Union + Dedupe (Tool Lists)"
        T1[["Base:<br/>[pytest, black]"]]
        T2[["Layer:<br/>[mypy, black]"]]
        T1 --> M3[["<b>Result:</b><br/>[pytest, black, mypy]"]]
        T2 --> M3
        Note[Duplicates removed]
    end
    
    subgraph "Deep Merge (Objects)"
        O1[["Base:<br/>{<br/>  a: 1,<br/>  b: 2<br/>}"]]
        O2[["Layer:<br/>{<br/>  b: 3,<br/>  c: 4<br/>}"]]
        O1 --> M4[["<b>Result:</b><br/>{<br/>  a: 1,<br/>  b: 3,<br/>  c: 4<br/>}"]]
        O2 --> M4
    end
    
    style A1 fill:#4A90E2,color:#fff
    style A2 fill:#9013FE,color:#fff
    style M1 fill:#7ED321,color:#000
    
    style S1 fill:#4A90E2,color:#fff
    style S2 fill:#9013FE,color:#fff
    style M2 fill:#7ED321,color:#000
    
    style T1 fill:#4A90E2,color:#fff
    style T2 fill:#9013FE,color:#fff
    style M3 fill:#7ED321,color:#000
    
    style O1 fill:#4A90E2,color:#fff
    style O2 fill:#9013FE,color:#fff
    style M4 fill:#7ED321,color:#000
```

### Merge Strategy Rules

Defined in `data/config/merge-config.yaml`:

| Field Type | Strategy | Example |
|------------|----------|---------|
| **guidelines** | Append + dedupe | All guidelines from all layers |
| **should** / **should_not** | Append + dedupe | All requirements from all layers |
| **tools** | Union + dedupe by name | Combines tool lists, removes duplicates |
| **examples** | Append | All examples preserved |
| **verification** | Append + dedupe | All verification items |
| **tone** | First wins | Base layer's tone used |
| **output_format** | First wins | Base layer's format used |
| **description** | First wins (recipe) | Recipe's description is primary |

### Why These Strategies?

- **Append for guidelines** - More guidelines = more complete persona
- **First wins for tone** - Avoid conflicting personality traits
- **Union for tools** - All tools available, no conflicts
- **Dedupe everywhere** - Avoid repeating the same guideline

---

## The Generation Pipeline

The pipeline orchestrates the entire generation process:

```mermaid
graph TB
    Start([personetta install]) --> Load[<b>1. Load Phase</b><br/><br/>loader.py reads:<br/>- Recipe YAML<br/>- All referenced layers<br/>- Schema validation]
    
    Load --> Merge[<b>2. Merge Phase</b><br/><br/>merger.py combines:<br/>- Apply merge strategies<br/>- Resolve conflicts<br/>- Deduplicate content]
    
    Merge --> Transform[<b>3. Transform Phase</b><br/><br/>pipeline.py processes:<br/>- Apply templates<br/>- Format for each tool<br/>- Generate all outputs]
    
    Transform --> Write[<b>4. Write Phase</b><br/><br/>layout modules write:<br/>- Baseline file<br/>- Router file<br/>- Active file<br/>- Cache directory]
    
    Write --> Verify[<b>5. Verify Phase</b><br/><br/>Checks:<br/>- Files exist<br/>- Proper format<br/>- Metadata correct]
    
    Verify --> Success{All OK?}
    Success -->|Yes| Done([✅ Complete])
    Success -->|No| Rollback[Rollback changes]
    Rollback --> Error([❌ Error])
    
    style Start fill:#4A90E2,color:#fff,stroke:#2E5C8A,stroke-width:2px
    style Load fill:#9013FE,color:#fff,stroke:#6A0FB8,stroke-width:2px
    style Merge fill:#9013FE,color:#fff,stroke:#6A0FB8,stroke-width:2px
    style Transform fill:#9013FE,color:#fff,stroke:#6A0FB8,stroke-width:2px
    style Write fill:#9013FE,color:#fff,stroke:#6A0FB8,stroke-width:2px
    style Verify fill:#F5A623,color:#fff,stroke:#C4851C,stroke-width:2px
    style Success fill:#F5A623,color:#fff,stroke:#C4851C
    style Done fill:#7ED321,color:#000,stroke:#5FA718,stroke-width:3px
    style Rollback fill:#D0021B,color:#fff
    style Error fill:#D0021B,color:#fff,stroke:#A80117,stroke-width:2px
```

### Phase Details

**1. Load Phase (`loader.py`)**
- Reads recipe YAML from `data/recipes/`
- Resolves `compose` references to base layers
- Resolves `mixins` references
- Validates against JSON schema
- Returns a raw composition tree

**2. Merge Phase (`merger.py`)**
- Applies merge strategies from `merge-config.yaml`
- Handles conflicts (first-wins, append, union)
- Deduplicates guidelines, tools, examples
- Produces a single merged dictionary

**3. Transform Phase (`pipeline.py`)**
- Applies output format templates
- Calls format-specific generators
- Generates baseline content (same for all tools)
- Generates router content (lists all recipes)
- Generates active content (full recipe)

**4. Write Phase (`*_layout.py` modules)**
- `cursor_layout.py` → `~/.cursor/rules/`
- `copilot_layout.py` → `~/.copilot/instructions/`
- `claude_layout.py` → `~/.claude/rules/`
- `cline_layout.py` → `~/Documents/Cline/Rules/`
- Also writes cache and state files

**5. Verify Phase**
- Checks files exist
- Validates file formats
- Ensures cache is complete
- Reports success or rolls back

---

## Multi-Tool Support

Personetta generates tool-specific formats from the same source recipes:

```mermaid
graph TB
    Source[Single Recipe YAML] --> Pipeline[Generation Pipeline]
    
    Pipeline --> Cursor[Cursor Format]
    Pipeline --> Copilot[Copilot Format]
    Pipeline --> Claude[Claude Format]
    Pipeline --> Cline[Cline Format]
    
    Cursor --> COut["Markdown files in<br/>.cursor/rules/<br/><br/>+ User Rules sync<br/>+ Skills copy"]
    Copilot --> CoOut["Markdown with YAML<br/>frontmatter in<br/>.copilot/instructions/<br/><br/>applyTo: '**'"]
    Claude --> ClOut["Markdown files in<br/>.claude/rules/<br/><br/>Loaded per session"]
    Cline --> CliOut["Markdown files in<br/>~/Documents/Cline/Rules/<br/><br/>Global rules"]
    
    style Source fill:#F8E71C,color:#000
    style Pipeline fill:#9013FE,color:#fff
    style Cursor fill:#4A90E2,color:#fff
    style Copilot fill:#4A90E2,color:#fff
    style Claude fill:#4A90E2,color:#fff
    style Cline fill:#4A90E2,color:#fff
    style COut fill:#7ED321,color:#000
    style CoOut fill:#7ED321,color:#000
    style ClOut fill:#7ED321,color:#000
    style CliOut fill:#7ED321,color:#000
```

### Tool-Specific Differences

| Aspect | Cursor | Copilot | Claude | Cline |
|--------|--------|---------|--------|-------|
| **File format** | Markdown | Markdown + YAML frontmatter | Markdown | Markdown |
| **Location** | `.cursor/rules/` | `.copilot/instructions/` | `.claude/rules/` | `~/Documents/Cline/Rules/` |
| **Always-on mechanism** | `alwaysApply: true` | `applyTo: "**"` | Loaded per session | Global rules directory |
| **Extra features** | User Rules sync, Skills | Frontmatter metadata | Session memory | - |
| **File extensions** | `.md` | `.instructions.md` | `.md` | `.md` |

---

## Cache and State

Personetta maintains cache and state for fast operations:

```mermaid
graph TB
    subgraph "Cache Directory<br/>~/.personetta/"
        Cache1["<b>tool-recipes/</b><br/><br/>Full recipe bodies:<br/>- implement-python.md<br/>- review-csharp.md<br/>- test-python.md<br/>- ... (all 27 recipes)"]
        Cache2["<b>tool-active.json</b><br/><br/>Current state:<br/>{<br/>  'active': 'implement-python',<br/>  'timestamp': '2026-04-17',<br/>  'tool': 'cursor'<br/>}"]
    end
    
    Install[personetta install] --> Cache1
    SetActive[personetta set-active] --> Cache1
    SetActive --> Cache2
    
    Cache1 -.->|Read during| SetActive
    Cache2 -.->|Read by| Current[personetta current]
    
    style Cache1 fill:#50555C,color:#fff,stroke:#3A3F44,stroke-width:2px
    style Cache2 fill:#50555C,color:#fff,stroke:#3A3F44,stroke-width:2px
    style Install fill:#9013FE,color:#fff
    style SetActive fill:#9013FE,color:#fff
    style Current fill:#4A90E2,color:#fff
```

### Cache Benefits

1. **Fast Switching** - `set-active` just copies from cache (instant)
2. **No Regeneration** - Don't reprocess YAML unless recipe changed
3. **State Tracking** - Know what's currently active
4. **Offline Work** - No need to reread YAML files

### Cache Invalidation

Cache is regenerated during:
- `personetta install '*'` - Regenerates all cached recipes
- Recipe YAML file modification - Next install detects changes
- Schema changes - Forces full rebuild

---

## Summary

**Key Takeaways:**

1. **Three-File Pattern** is the core architecture (baseline + router + active)
2. **Composition** enables reusable, maintainable recipes
3. **Merge Strategies** handle conflicts intelligently
4. **Generation Pipeline** is tool-agnostic until the very end
5. **Cache** makes switching instant

---

## Next Steps

- **Create your own recipe** - See [Recipe Guide](recipe-guide.md)
- **Understand file layouts** - See [User Guide](user-guide.md)
- **Extend Personetta** - See [Extending Guide](extending.md)
- **Visual reference** - See [All Diagrams](diagrams.md)

---

**Questions?** See [Troubleshooting](troubleshooting.md) | [GitHub Issues](https://github.com/your-org/personetta/issues)
