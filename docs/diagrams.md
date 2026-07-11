# Personetta Diagrams Gallery

**Visual Reference:** All diagrams used across Personetta documentation

This gallery provides a central reference for all major diagrams. Each diagram links to the documentation where it's explained in detail.

---

## 🏗️ Hero Diagrams

These are the core diagrams that appear across multiple documentation files:

### 1. System Architecture Overview

**Where used:** [concepts.md](concepts.md), [developer-guide.md](developer-guide.md)

**What it shows:** The complete flow from YAML recipes through the generation engine to installed files in different tools.

```mermaid
graph TB
    subgraph "📄 YAML Recipes"
        Recipe[implement-python.yaml<br/>Recipe Definition]
        Base[base/lifecycle/<br/>implementation-developer]
        Lang[language-specific/python/<br/>python-developer]
        Mixin[Mixins:<br/>readability-focused<br/>performance-focused]
    end
    
    subgraph "🔄 Generation Engine"
        Loader[loader.py<br/>📥 Load & Validate YAML]
        Merger[merger.py<br/>🔀 Compose Layers]
        Pipeline[pipeline.py<br/>⚙️ Generate Content]
    end
    
    subgraph "📤 Format-Specific Generators"
        Cursor[cursor_layout.py<br/>Generate .cursor/rules/]
        Copilot[copilot_layout.py<br/>Generate .copilot/instructions/]
        Claude[claude_layout.py<br/>Generate .claude/rules/]
        Cline[cline_layout.py<br/>Generate Cline rules/]
    end
    
    subgraph "📂 Installed Files"
        CursorFiles[.cursor/rules/<br/>✓ baseline.md<br/>✓ router.md<br/>✓ active.md]
        CopilotFiles[~/.copilot/instructions/<br/>✓ baseline.instructions.md<br/>✓ router.instructions.md<br/>✓ active.instructions.md]
        ClaudeFiles[~/.claude/rules/<br/>✓ baseline.md<br/>✓ router.md<br/>✓ active.md]
        ClineFiles[~/Documents/Cline/Rules/<br/>✓ baseline.md<br/>✓ router.md<br/>✓ active.md]
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
    
    Cursor --> CursorFiles
    Copilot --> CopilotFiles
    Claude --> ClaudeFiles
    Cline --> ClineFiles
    
    style Recipe fill:#F8E71C,color:#000,stroke:#C4B519,stroke-width:3px
    style Base fill:#F8E71C,color:#000,stroke:#C4B519
    style Lang fill:#F8E71C,color:#000,stroke:#C4B519
    style Mixin fill:#F8E71C,color:#000,stroke:#C4B519
    
    style Loader fill:#9013FE,color:#fff,stroke:#6A0FB8,stroke-width:2px
    style Merger fill:#9013FE,color:#fff,stroke:#6A0FB8,stroke-width:2px
    style Pipeline fill:#9013FE,color:#fff,stroke:#6A0FB8,stroke-width:2px
    
    style Cursor fill:#4A90E2,color:#fff,stroke:#2E5C8A,stroke-width:2px
    style Copilot fill:#4A90E2,color:#fff,stroke:#2E5C8A,stroke-width:2px
    style Claude fill:#4A90E2,color:#fff,stroke:#2E5C8A,stroke-width:2px
    style Cline fill:#4A90E2,color:#fff,stroke:#2E5C8A,stroke-width:2px
    
    style CursorFiles fill:#7ED321,color:#000,stroke:#5FA718,stroke-width:3px
    style CopilotFiles fill:#7ED321,color:#000,stroke:#5FA718,stroke-width:3px
    style ClaudeFiles fill:#7ED321,color:#000,stroke:#5FA718,stroke-width:3px
    style ClineFiles fill:#7ED321,color:#000,stroke:#5FA718,stroke-width:3px
```

**Key concepts:**
- 🟡 **Yellow**: Input YAML files - your recipe definitions
- 🟣 **Purple**: Internal processing - the generation engine
- 🔵 **Blue**: Format-specific output generators
- 🟢 **Green**: Final installed files ready to use

---

### 2. Recipe Composition Model

**Where used:** [concepts.md](concepts.md), [recipe-guide.md](recipe-guide.md)

**What it shows:** How base layers, language-specific knowledge, and mixins combine to create a complete recipe.

```mermaid
graph LR
    subgraph "Base Layer"
        direction TB
        B1["Guidelines:<br/>✓ Tools first<br/>✓ Verify work<br/>✓ Document decisions"]
        B2["Tone:<br/>Professional"]
        B3["Should:<br/>- Evaluate options<br/>- Test thoroughly"]
    end
    
    subgraph "Language Layer"
        direction TB
        L1["Guidelines:<br/>✓ PEP 8<br/>✓ Type hints<br/>✓ Docstrings"]
        L2["Tools:<br/>✓ pytest<br/>✓ black<br/>✓ mypy"]
        L3["Should:<br/>- Write idiomatic Python<br/>- Handle errors properly"]
    end
    
    subgraph "Mixin Layer"
        direction TB
        M1["Guidelines:<br/>✓ Profile before optimizing<br/>✓ O(n) analysis<br/>✓ Benchmark changes"]
        M2["Tools:<br/>✓ cProfile<br/>✓ memory_profiler"]
    end
    
    subgraph "✅ Merged Recipe"
        direction TB
        R1["<b>All Guidelines Combined</b><br/>Base + Language + Mixin"]
        R2["<b>Tone: Professional</b><br/>From base layer"]
        R3["<b>All Tools Combined</b><br/>pytest, black, mypy<br/>cProfile, memory_profiler"]
        R4["<b>All Shoulds Combined</b><br/>Evaluate + Test + Idiomatic<br/>+ Error handling"]
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
    style R2 fill:#7ED321,color:#000,stroke:#5FA718,stroke-width:3px
    style R3 fill:#7ED321,color:#000,stroke:#5FA718,stroke-width:3px
    style R4 fill:#7ED321,color:#000,stroke:#5FA718,stroke-width:3px
```

**Merge strategy:**
- **Guidelines:** Append all (deduplicated)
- **Tools:** Union of all tools
- **Tone:** First non-empty value wins
- **Shoulds:** Append all

---

### 3. The Three-File Pattern

**Where used:** [concepts.md](concepts.md), [user-guide.md](user-guide.md)

**What it shows:** The baseline + router + active file pattern that makes Personetta work.

```mermaid
graph TB
    subgraph "Personetta File Structure"
        direction LR
        
        subgraph "Baseline (Always On)"
            B["<b>personetta-baseline.md</b><br/><br/>Cross-cutting rules:<br/>✓ Check model recommendation<br/>✓ Verify work alignment<br/>✓ Honor active persona<br/>✓ Run verification<br/>✓ Report compliance<br/><br/>Size: ~100 lines<br/>Purpose: Orchestration"]
        end
        
        subgraph "Router (Context-Aware)"
            R["<b>personetta-router.md</b><br/><br/>Recipe index:<br/>✓ All recipe IDs<br/>✓ Descriptions<br/>✓ set-active commands<br/>✓ Activation phrases<br/><br/>Size: ~200 lines<br/>Purpose: Discovery & switching"]
        end
        
        subgraph "Active (Full Persona)"
            A["<b>personetta-active.md</b><br/><br/>Complete recipe:<br/>✓ All guidelines (30-50+)<br/>✓ All tools (20-40+)<br/>✓ Examples<br/>✓ Verification checklist<br/><br/>Size: 800-1200 lines<br/>Purpose: The actual AI persona"]
        end
    end
    
    User[👤 User] -->|Runs command| CLI[personetta set-active<br/>implement-python]
    CLI -->|Replaces| A
    CLI -->|Uses cache| Cache[.personetta/<br/>tool-recipes/<br/>implement-python.md]
    
    AI[🤖 AI Tool] -->|Loads every turn| B
    AI -->|Loads every turn| R
    AI -->|Loads every turn| A
    
    B -.->|References| A
    R -.->|Lists| Cache
    A -.->|Generated from| Cache
    
    style B fill:#4A90E2,color:#fff,stroke:#2E5C8A,stroke-width:3px
    style R fill:#F5A623,color:#fff,stroke:#C4851C,stroke-width:3px
    style A fill:#7ED321,color:#000,stroke:#5FA718,stroke-width:4px
    style Cache fill:#50555C,color:#fff,stroke:#3A3F44
    style User fill:#4A90E2,color:#fff
    style CLI fill:#9013FE,color:#fff
    style AI fill:#50555C,color:#fff
```

**Why three files?**
- **Baseline:** Small, always-on orchestration logic (context efficiency)
- **Router:** Recipe discovery without loading everything (selective context)
- **Active:** Full recipe loaded when relevant (complete persona)

**Key insight:** Only ONE full recipe loaded at a time, but ALL recipes discoverable.

---

### 4. Complete User Workflow

**Where used:** [user-guide.md](user-guide.md), [quickstart.md](quickstart.md)

**What it shows:** The complete user journey from installation to daily use.

```mermaid
graph TB
    Start((🚀 Start)) --> Install[📦 Install Personetta<br/>pip install personetta]
    Install --> InstallAll[⚙️ Install Recipes<br/>personetta install '*' --format cursor]
    
    InstallAll --> Check{✅ Success?}
    Check -->|No| Error[❌ Check errors<br/>See troubleshooting.md]
    Check -->|Yes| Files[📁 Files Generated<br/>baseline + router + active<br/>+ cached recipes]
    
    Files --> Choose[🎯 Choose Recipe<br/>Browse router.md or<br/>run 'list' command]
    
    Choose --> SetActive[🔄 Activate Recipe<br/>personetta set-active<br/>implement-python --format cursor]
    
    SetActive --> Work[💻 Work in AI Tool<br/>Persona is active!]
    
    Work --> Switch{Switch recipe?}
    Switch -->|Yes| SetActive
    Switch -->|No| Continue[✨ Keep working]
    
    Continue --> Switch2{Need different recipe?}
    Switch2 -->|Yes| SetActive
    Switch2 -->|No| Done((✅ Done))
    
    Error --> Fix[🔧 Fix issue]
    Fix --> InstallAll
    
    style Start fill:#4A90E2,color:#fff,stroke:#2E5C8A,stroke-width:3px
    style Install fill:#9013FE,color:#fff,stroke:#6A0FB8
    style InstallAll fill:#9013FE,color:#fff,stroke:#6A0FB8,stroke-width:2px
    style Check fill:#F5A623,color:#fff,stroke:#C4851C,stroke-width:2px
    style Error fill:#D0021B,color:#fff,stroke:#A80117
    style Files fill:#7ED321,color:#000,stroke:#5FA718
    style Choose fill:#4A90E2,color:#fff,stroke:#2E5C8A
    style SetActive fill:#9013FE,color:#fff,stroke:#6A0FB8,stroke-width:2px
    style Work fill:#7ED321,color:#000,stroke:#5FA718,stroke-width:2px
    style Switch fill:#F5A623,color:#fff,stroke:#C4851C
    style Continue fill:#7ED321,color:#000,stroke:#5FA718
    style Switch2 fill:#F5A623,color:#fff,stroke:#C4851C
    style Done fill:#7ED321,color:#000,stroke:#5FA718,stroke-width:3px
    style Fix fill:#F5A623,color:#fff,stroke:#C4851C
```

**Time to productivity:** ~5 minutes from installation to working with your first recipe.

---

### 5. Extension Points Map

**Where used:** [extending.md](extending.md), [developer-guide.md](developer-guide.md)

**What it shows:** Where and how developers can extend Personetta.

```mermaid
graph TB
    Start{🎯 What do you<br/>want to add?}
    
    Start -->|New Recipe| Recipe[📝 Create YAML<br/>in data/recipes/]
    Start -->|New Base Layer| Base[📁 Add to data/base/]
    Start -->|New Language| Lang[📁 Add to<br/>data/language-specific/]
    Start -->|New Tool Format| Tool[🔧 Multi-step process]
    Start -->|New Command| Cmd[💻 Add CLI command]
    
    Recipe --> RecipeTest[✅ Test:<br/>personetta generate<br/>--recipe new-recipe<br/>--format cursor]
    Base --> RecipeTest
    Lang --> RecipeTest
    
    Tool --> Layout[1️⃣ Create layout.py<br/>src/generator/<br/>new_tool_layout.py]
    Layout --> Formatter[2️⃣ Create formatter<br/>src/generator/formatters/<br/>new_tool.py]
    Formatter --> Register[3️⃣ Register format<br/>output_formats.py]
    Register --> TestTool[✅ Integration tests<br/>tests/integration/]
    
    Cmd --> CmdFile[Create command file<br/>src/generator/cli/commands/<br/>new_command.py]
    CmdFile --> RegCmd[Register in parser.py]
    RegCmd --> TestCmd[✅ Add tests<br/>tests/unit/cli/]
    
    RecipeTest --> Success
    TestTool --> Success
    TestCmd --> Success
    
    Success[🎉 Extension Complete!<br/>Run full test suite<br/>pytest tests/]
    
    style Start fill:#F5A623,color:#fff,stroke:#C4851C,stroke-width:3px
    
    style Recipe fill:#7ED321,color:#000,stroke:#5FA718,stroke-width:2px
    style Base fill:#7ED321,color:#000,stroke:#5FA718,stroke-width:2px
    style Lang fill:#7ED321,color:#000,stroke:#5FA718,stroke-width:2px
    
    style Tool fill:#F5A623,color:#fff,stroke:#C4851C,stroke-width:2px
    style Layout fill:#9013FE,color:#fff,stroke:#6A0FB8
    style Formatter fill:#9013FE,color:#fff,stroke:#6A0FB8
    style Register fill:#9013FE,color:#fff,stroke:#6A0FB8
    
    style Cmd fill:#4A90E2,color:#fff,stroke:#2E5C8A,stroke-width:2px
    style CmdFile fill:#9013FE,color:#fff,stroke:#6A0FB8
    style RegCmd fill:#9013FE,color:#fff,stroke:#6A0FB8
    
    style RecipeTest fill:#4A90E2,color:#fff,stroke:#2E5C8A
    style TestTool fill:#4A90E2,color:#fff,stroke:#2E5C8A
    style TestCmd fill:#4A90E2,color:#fff,stroke:#2E5C8A
    
    style Success fill:#7ED321,color:#000,stroke:#5FA718,stroke-width:3px
```

**Difficulty levels:**
- 🟢 **Green:** Easy - just YAML editing (recipes, base layers, language support)
- 🔵 **Blue:** Moderate - Python code + tests (CLI commands)
- 🟠 **Orange:** Advanced - Multi-file changes + integration (new tool formats)

---

## 📊 Flow Diagrams

### Installation Flow

```mermaid
graph LR
    User[👤 Run install '*'] --> Check{Check format}
    Check -->|cursor| CursorPath[~/.cursor/rules/]
    Check -->|copilot| CopilotPath[~/.copilot/instructions/]
    Check -->|claude| ClaudePath[~/.claude/rules/]
    Check -->|cline| ClinePath[~/Documents/Cline/Rules/]
    
    CursorPath --> Write[Write 3 files]
    CopilotPath --> Write
    ClaudePath --> Write
    ClinePath --> Write
    
    Write --> Baseline[baseline file]
    Write --> Router[router file]
    Write --> Active[active file]
    
    Write --> Cache[Cache all recipe bodies]
    
    Cache --> Done[✅ Installation complete!]
    
    style User fill:#4A90E2,color:#fff
    style Check fill:#F5A623,color:#fff
    style Write fill:#9013FE,color:#fff
    style Done fill:#7ED321,color:#000,stroke:#5FA718,stroke-width:2px
```

### Set-Active Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant Cache
    participant ActiveFile
    participant StateFile
    
    User->>CLI: personetta set-active<br/>implement-python
    CLI->>Cache: Read .personetta/cursor-recipes/<br/>implement-python.md
    Cache-->>CLI: Recipe content
    CLI->>ActiveFile: Replace personetta-active.md<br/>with new recipe
    CLI->>StateFile: Update cursor-active.json<br/>with metadata
    CLI-->>User: ✅ Active recipe updated:<br/>implement-python
    
    Note over User,StateFile: Active file changed,<br/>baseline + router unchanged
```

---

## 🎨 Composition Diagrams

### Merge Strategies Visualized

```mermaid
graph TB
    subgraph "Append Strategy (Lists)"
        A1[["Base: [a, b]"]] --> M1[["Result: [a, b, c, d]"]]
        A2[["Layer: [c, d]"]] --> M1
    end
    
    subgraph "First Wins (Scalars)"
        S1[["Base: 'value1'"]] --> M2[["Result: 'value1'"]]
        S2[["Layer: 'value2'"]] -.->|ignored| M2
    end
    
    subgraph "Union (Tool Lists)"
        T1[["Base: [pytest, black]"]] --> M3[["Result: [pytest, black,<br/>mypy, ruff]"]]
        T2[["Layer: [mypy, ruff, black]"]] --> M3
        Note3[Deduplicated]
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
```

---

## 🗺️ Navigation Diagram

```mermaid
graph LR
    Docs[📚 Documentation Hub] --> Quick[🚀 quickstart.md<br/>5-min setup]
    Docs --> User[📖 user-guide.md<br/>Complete workflows]
    Docs --> Concept[🧠 concepts.md<br/>How it works]
    Docs --> Recipe[📝 recipe-guide.md<br/>Create recipes]
    Docs --> CLI[⌨️ cli-reference.md<br/>All commands]
    Docs --> Dev[🔧 developer-guide.md<br/>Contributing]
    Docs --> Extend[🔌 extending.md<br/>Extension points]
    Docs --> Trouble[🚨 troubleshooting.md<br/>Problem solving]
    Docs --> This[🎨 diagrams.md<br/>Visual reference]
    
    style Docs fill:#4A90E2,color:#fff,stroke:#2E5C8A,stroke-width:3px
    style Quick fill:#7ED321,color:#000
    style User fill:#7ED321,color:#000
    style Concept fill:#9013FE,color:#fff
    style Recipe fill:#9013FE,color:#fff
    style CLI fill:#50555C,color:#fff
    style Dev fill:#F5A623,color:#fff
    style Extend fill:#F5A623,color:#fff
    style Trouble fill:#D0021B,color:#fff
    style This fill:#F8E71C,color:#000
```

---

## 📐 Legend

### Color Meanings

| Color | Meaning | Example |
|-------|---------|---------|
| 🔵 Blue | User actions, inputs | User runs command |
| 🟢 Green | Success, outputs, ready states | Installation complete |
| 🟠 Orange | Decisions, alternatives | Choose option |
| 🔴 Red | Errors, blockers | Build failed |
| 🟣 Purple | Processing, transformations | Merge layers |
| ⚫ Gray | Infrastructure, tools | File system |
| 🟡 Yellow | Configuration, data | YAML files |

### Shape Meanings

- **Rounded Rectangle** → User-facing elements
- **Rectangle** → System processes  
- **Diamond** → Decision points
- **Cylinder** → Data/files
- **Hexagon** → External tools
- **Circle** → Start/end points

---

## 📚 Related Documentation

- [Diagram Style Guide](diagram-style-guide.md) - Visual design system
- [Diagram Templates](diagrams/templates/) - Reusable templates
- [Concepts](concepts.md) - Core concepts explained
- [Architecture](architecture.md) - Technical architecture

---

**Missing a diagram?** Open an issue or PR to add it!
