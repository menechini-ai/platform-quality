# Datadog RCA Kit - V4 Plan (2026-07-12)

V1: collector + fallback diagnosis ✅
V2: real LLM + APM spans + structured RCA ✅
V3: ReAct agent + runbook + MTTR breakdown ✅

## V4: Vector Search + Auto-Remediation + Notifications

### Core Ideas
1. **Vector search over historical incidents** — embed incident summaries + RCA, query for similar_incidents at investigation time
2. **Auto-remediation playbooks** — executable runbook steps (kubectl rollout restart, scale deployment, flip feature flag)
3. **Notification integrations** — Slack/Telegram/PagerDuty webhook delivery of investigation results
4. **Feedback loop** — human resolution confirmation → re-embed → improve similarity

### Architecture
```
investigate_v4(query, incident_id?)
  → fetch signals (V3)
  → vector_search(similar_incidents)  -- NEW
  → ReAct loop with similar_incidents as context  -- NEW
  → diagnosis + runbook + MTTR
  → if auto_remediate: execute_playbook(runbook.mitigation)  -- NEW
  → notify(slack_webhook, telegram, pagerduty)  -- NEW
  → persist + return
```

### Data Model Additions
- `IncidentEmbedding`: incident_id, summary, root_cause, embedding(vector), resolution_notes, created_at
- `PlaybookStep`: type (kubectl|scale|flag|script), params, confirmation_required, rollback
- `NotificationConfig`: channel, webhook_url, template, severity_filter

### Implementation Order
T1: Vector store (pgvector or SQLite-vec) + embedding pipeline
T2: Similar incident search in ReAct context
T3: Playbook executor (dry-run → confirm → execute)
T4: Notification dispatcher (Slack/Telegram/PagerDuty)
T5: Feedback API (mark resolution, update embeddings)
T6: Feature flags + canary config + E2E test