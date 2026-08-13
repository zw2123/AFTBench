# Data Card

## Overview

All data in AFTBench is synthetically generated for benchmark purposes. No real user data is used.

## Synthetic Data Categories

### Enterprise Records (CRM)
- **Contacts**: 5+ fictional contacts across 2 accounts (Acme Corp, Globex Inc)
- **Records**: Versioned contact records with name, phone, email, account, role fields
- **Entity ambiguity**: Two contacts named "Alex Chen" in different accounts
- **Generation**: Hand-crafted to test entity resolution, versioning, and permission scenarios

### Long-Running Jobs
- **Jobs**: Multi-stage report generation, data processing, and export tasks
- **Stages**: 3-5 stages per job with deterministic progress tracking
- **Generation**: Structured templates with configurable stage counts

### Tool Catalogs
- **Sizes**: 10, 50, 200, 1000 capabilities
- **Domains**: CRM, ticketing, storage, CI/CD, reports, messaging, scheduling, publications
- **Distractors**: Near-miss tool descriptions with overlapping names and input shapes
- **Generation**: Deterministic seeded generation with domain-specific templates

### External Actions
- **Entities**: Calendar events, messages, publications, notifications
- **Effect types**: Reversible, compensatable, irreversible
- **Generation**: Predefined scenarios with known oracle outcomes

## Fault Schedules
- **Types**: 10 fault types covering entity ambiguity, failure timing, response loss, partial completion, interruption, stale state, permission drift, event loss, handle expiration, tool evolution
- **Seeds**: Deterministic given seed value
- **Oracle**: Independent ground truth tracking

## Policies
- **Roles**: admin, support_lead, user
- **Scopes**: Per-resource read/write/approve permissions
- **Approval requirements**: Declared per-operation
- **Generation**: Hand-crafted deterministic policies

## Limitations
- Data does not model real-world distribution of entity names or tool usage patterns
- Catalog distractors are designed to be challenging but not adversarial
- Fault timing is simplified (discrete stages rather than continuous time)
- No personal, financial, or health information is represented
