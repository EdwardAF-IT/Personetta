# Missing Role Name Inventory

## Base role names (type: lifecycle)
- systems-administrator
- operations-engineer
- repository-maintainer
- release-manager
- tooling-debugger
- performance-analyst
- security-operator
- migration-planner
- refactoring-specialist
- network-troubleshooter

## Base role names (type: layer)
- windows-platform-operator
- linux-platform-operator
- home-lab-infrastructure-engineer
- network-infrastructure-engineer
- storage-infrastructure-engineer
- identity-access-engineer
- git-governance-engineer
- ci-cd-release-engineer
- api-contract-engineer
- event-integration-engineer

## Language-specific role names (type: language)

### csharp
- csharp-api-contract-specialist
- csharp-database-migration-specialist
- csharp-performance-diagnostics-specialist
- csharp-secrets-governance-specialist

### powershell
- powershell-systems-administrator
- powershell-git-automation-specialist
- powershell-network-diagnostics-specialist
- powershell-environment-recovery-specialist

### python
- python-cli-tooling-developer
- python-workflow-automation-engineer
- python-performance-regression-analyst

### javascript
- javascript-webhook-integration-developer

### tsql
- tsql-migration-specialist
- tsql-release-safety-reviewer

## Base role names (type: mixin)
- observability-focused
- release-safety-focused
- reliability-focused
- operability-focused
- diagnostics-first
- incident-response-focused
- compliance-aware
- cost-aware

## Base role names (type: system)
- none

## Recipe IDs (data/recipes)
- implement-devops-system
- debug-devops-system
- review-devops-system
- test-devops-system
- implement-devops-infra
- debug-devops-infra
- implement-powershell-automation
- debug-powershell-infra
- review-powershell-automation
- design-api-system
- implement-api-system
- test-api-system
- review-api-secure
- implement-data-automation
- debug-data-pipeline
- review-config-system
- debug-config-system
- implement-agent-system

## Provisions names (provisions.kind: tool-setting)
- terminal-default-profile
- terminal-safe-aliases
- git-default-guardrails
- diagnostics-output-retention
- role-switch-status-line

## Provisions names (provisions.kind: plugin)
- git-assistant
- shell-history-inspector
- log-analyzer
- network-diagnostics-toolkit
- release-checklist-helper

## Provisions names (provisions.kind: behavior)
- guarded-force-push
- release-readiness-gate
- branch-protection-aware-flow
- incident-debug-mode
- diagnostics-before-fix

## Provision bundle names (bundles)
- repo-hygiene
- diagnostics-pack
- release-safety
- ops-foundation
- branch-governance

## Glossary

### provisions.kind: tool-setting
- Provision entries that apply settings values to supported target tools.
- Used for configuration-style changes rather than installing new extensions.

### provisions.kind: plugin
- Provision entries that install or manage a plugin/extension for target tools.
- Includes install metadata and optional policy controls.

### bundles
- Named groups of provisions that are enabled/applied together.
- Can define members, install order, and bundle-level overrides.
