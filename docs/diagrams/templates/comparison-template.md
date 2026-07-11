# Comparison Diagram Template

Use this template for side-by-side comparisons and before/after scenarios.

## Template

```mermaid
graph TB
    subgraph "Option A"
        A1[Feature 1]
        A2[Feature 2]
        A3[Feature 3]
        Result1[Outcome A]
    end
    
    subgraph "Option B"
        B1[Feature 1]
        B2[Feature 4]
        B3[Feature 5]
        Result2[Outcome B]
    end
    
    A1 --> Result1
    A2 --> Result1
    A3 --> Result1
    
    B1 --> Result2
    B2 --> Result2
    B3 --> Result2
    
    style A1 fill:#4A90E2,color:#fff
    style A2 fill:#4A90E2,color:#fff
    style A3 fill:#4A90E2,color:#fff
    style Result1 fill:#7ED321,color:#000
    
    style B1 fill:#F5A623,color:#fff
    style B2 fill:#F5A623,color:#fff
    style B3 fill:#F5A623,color:#fff
    style Result2 fill:#7ED321,color:#000
```

## Customization Guide

1. **Labels:** Replace "Option A/B" with actual comparison subjects
2. **Features:** List the distinguishing characteristics
3. **Colors:** Use consistent colors for each option throughout docs
4. **Outcomes:** Show what each option leads to
5. **Add notes:** Use Mermaid notes to highlight key differences

## Variations

### Before/After
```mermaid
graph LR
    subgraph "Before"
        B1[Manual Setup]
        B2[Copy Files]
        B3[Edit Config]
    end
    
    subgraph "After"
        A1[Run Command]
        A2[Automatic Setup]
    end
    
    B1 --> B2 --> B3
    A1 --> A2
    
    style B1 fill:#D0021B,color:#fff
    style B2 fill:#D0021B,color:#fff
    style B3 fill:#D0021B,color:#fff
    style A1 fill:#7ED321,color:#000
    style A2 fill:#7ED321,color:#000
```

### Global vs Project
```mermaid
graph TB
    Decision{Choose Install Type}
    
    Decision -->|Global| Global[~/.cursor/rules/<br/>Available everywhere]
    Decision -->|Project| Project[.cursor/rules/<br/>This repo only]
    
    Global --> UseGlobal[Use across<br/>all workspaces]
    Project --> UseProject[Use in<br/>this workspace only]
    
    style Decision fill:#F5A623,color:#fff
    style Global fill:#4A90E2,color:#fff
    style Project fill:#9013FE,color:#fff
    style UseGlobal fill:#7ED321,color:#000
    style UseProject fill:#7ED321,color:#000
```

## When to Use

- Comparing different approaches
- Showing global vs project installation
- Illustrating before/after improvements
- Contrasting tool formats
