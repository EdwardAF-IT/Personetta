# Flow Diagram Template

Use this template for sequential processes, workflows, and decision trees.

## Template

```mermaid
graph LR
    Start((Start)) --> Action1[First Action]
    Action1 --> Decision{Decision Point?}
    Decision -->|yes| Action2[Path A]
    Decision -->|no| Action3[Path B]
    Action2 --> End((Complete))
    Action3 --> End
    
    style Start fill:#4A90E2,color:#fff
    style Action1 fill:#9013FE,color:#fff
    style Decision fill:#F5A623,color:#fff
    style Action2 fill:#9013FE,color:#fff
    style Action3 fill:#9013FE,color:#fff
    style End fill:#7ED321,color:#000
```

## Customization Guide

1. **Direction:** Change `LR` (left-right) to `TB` (top-bottom), `RL`, or `BT` as needed
2. **Actions:** Replace with actual process steps
3. **Decisions:** Add more diamond nodes `{text}` for branching logic
4. **Colors:**
   - Blue (`#4A90E2`) for user actions
   - Purple (`#9013FE`) for system processes
   - Orange (`#F5A623`) for decisions
   - Green (`#7ED321`) for success/completion
   - Red (`#D0021B`) for errors/failures
5. **Labels:** Add text to arrows with `-->|label text|`

## Variations

### Simple Linear Flow
```mermaid
graph LR
    A[Step 1] --> B[Step 2] --> C[Step 3] --> D[Step 4]
    
    style A fill:#4A90E2,color:#fff
    style B fill:#9013FE,color:#fff
    style C fill:#9013FE,color:#fff
    style D fill:#7ED321,color:#000
```

### Complex Decision Tree
```mermaid
graph TB
    Start{Check Config}
    Start -->|valid| Path1[Process A]
    Start -->|invalid| Error[Show Error]
    Path1 --> Check2{Check Dependencies}
    Check2 -->|ok| Success[Continue]
    Check2 -->|missing| Install[Install Dependencies]
    Install --> Success
    Error --> End((Stop))
    Success --> End((Complete))
    
    style Start fill:#F5A623,color:#fff
    style Path1 fill:#9013FE,color:#fff
    style Error fill:#D0021B,color:#fff
    style Check2 fill:#F5A623,color:#fff
    style Success fill:#7ED321,color:#000
    style Install fill:#9013FE,color:#fff
    style End fill:#7ED321,color:#000
```

## When to Use

- Documenting step-by-step processes
- Showing decision logic
- Illustrating user workflows
- Explaining command execution flow
