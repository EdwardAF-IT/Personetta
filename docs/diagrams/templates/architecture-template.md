# Architecture Diagram Template

Use this template for system architecture and component relationship diagrams.

## Template

```mermaid
graph TB
    subgraph "Layer 1: [Name]"
        L1A[Component A]
        L1B[Component B]
    end
    
    subgraph "Layer 2: [Name]"
        L2A[Component C]
        L2B[Component D]
    end
    
    subgraph "Layer 3: [Name]"
        L3A[Component E]
        L3B[Component F]
    end
    
    L1A --> L2A
    L1B --> L2B
    L2A --> L3A
    L2B --> L3B
    
    style L1A fill:#F8E71C,color:#000
    style L1B fill:#F8E71C,color:#000
    style L2A fill:#9013FE,color:#fff
    style L2B fill:#9013FE,color:#fff
    style L3A fill:#7ED321,color:#000
    style L3B fill:#7ED321,color:#000
```

## Customization Guide

1. **Layers:** Replace `Layer 1/2/3` with actual layer names (e.g., "Input", "Processing", "Output")
2. **Components:** Rename `Component A/B/C` to actual component names
3. **Colors:** 
   - Yellow (`#F8E71C`) for input/data
   - Purple (`#9013FE`) for processing
   - Green (`#7ED321`) for output/results
   - Gray (`#50555C`) for infrastructure
4. **Arrows:** Add labels with `-->|label text|` if flow needs clarification
5. **Icons:** Add emoji to component labels for visual cues

## When to Use

- Showing system structure
- Illustrating component relationships
- Explaining data flow through layers
- Documenting module dependencies
