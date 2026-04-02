Production Roadmap
==================

This document outlines the path from working prototype to production
deployment, prioritized by end-user value.

What I Built
-----------------

A working five-layer pipeline that ingests 307 synthetic Slack messages,
extracts 308 structured atoms via the Anthropic Message Batches API,
scores them across five relevance dimensions, and generates personalized
four-section digests for three demo personas. Persistence: Postgres
(bundles, atoms, context windows, batch logs), Neo4j (atom graph),
Facebook AI Similarity Search
(embedding cache). Delta processing ensures re-runs skip unchanged data.
React frontend with instant persona switching and pipeline progress
polling. All prompts and constants externalized to YAML config.

Stakeholder Questions
----------------------

These should be answered before production scoping. Each answer
materially changes the architecture.

**Intellectual Property (IP) Classification (Highest Priority).** Can
Slack content be processed by a cloud LLM API, or
is on-prem inference required? Cloud: around $150
to $450/month. On-prem: higher infra cost, lower extraction quality.

**Project Management Tool Integration.** Does the team use Jira, Linear, or Asana for
phase-gate tracking? Automated phase detection from ticket status changes
eliminates the manual phase toggle.

**Multi-Source Ingestion.** Do decisions also occur in email, Google Docs,
CAD comments, or Product Lifecycle Management (PLM) systems? If so, the ingestion layer needs a plugin
architecture.

**User Research.** Concrete failure stories ("I missed X and it cost us Y")
are the best input for tuning extraction taxonomy and scoring weights.

Priority 1: Live Slack Integration
------------------------------------

**User value:** Replace synthetic data with the team's actual Slack messages.
The tool becomes immediately useful instead of a demo.

**Technical approach:**

- Create a Slack App with OAuth 2.0 bot token (scopes: ``channels:history``,
  ``channels:read``, ``groups:history``, ``users:read``)
- Implement incremental ingestion with high-water mark per channel
  (``conversations.history`` with cursor-based pagination)
- Preferred: Slack Events API (webhook) for real-time message receipt
- Handle message edits (``message_changed``) and deletes
  (``message_deleted``) by updating or tombstoning atoms
- Deduplicate on ``(channel_id, message_ts)`` composite key
- The existing ``SlackMessage`` model and ingestion pipeline require
  zero changes. Only the data source switches from fixture to API.
- Enables deep-linking: each digest item's ``source.channel`` and
  ``source.thread_ts`` become clickable Slack URLs instead of static
  references

Priority 2: PLM / Enterprise Resource Planning Connectors
----------------------------------

**User value:** Phase context and spec baselines come directly from the
system of record instead of being inferred from Slack or manually toggled.
This eliminates the biggest accuracy gap in the current scoring model.

**Technical approach:**

- Poll PLM phase-gate status (Arena, Teamcenter, Windchill) per
  subsystem. Auto-update phase vectors when gates pass, replacing
  the manual toggle and hardcoded ``config/phases.yml``.
- Import spec baselines from PLM bill of materials to distinguish new
  ``SPEC_CHANGE`` atoms from known revisions (reduces false positives)
- Cross-reference extracted atoms against open Engineering Change
  Orders (ECOs) to surface informal decisions not yet formalized
  and ECOs without Slack discussion
- Use per-subsystem phase granularity (assembly/part-level)
  for finer scoring precision than workstream-level approximation

This is a fundamentally different architecture than inferring phase
from message patterns. Direct PLM integration provides the spec
baseline and phase ground truth that inference cannot.

Priority 3: Security Hardening
-------------------------------

**User value:** The digest pipeline handles proprietary engineering
discussions. Hardening the stack protects intellectual property and
satisfies enterprise security review gates before production deployment.

**Technical approach:**

- **Docker images:** run as non-root, switch to distroless/slim bases,
  scan with Trivy or Snyk in CI, pin image digests, mount
  application filesystems read-only
- **API layer:** add authentication (API key or OAuth), rate limiting,
  strict input validation, lock CORS to known origins, terminate TLS
  at the reverse proxy
- **Persistence:** encrypt connections to Neo4j and Postgres (TLS),
  inject credentials via vault or environment (never hardcoded),
  restrict container network exposure to only required ports,
  encrypt backups at rest

Priority 4: Scheduled Pipeline
-------------------------------

**User value:** Digests appear in engineers' inboxes every morning without
anyone pressing a button. The tool becomes a habit, not a novelty.

**Technical approach:**

- Daily cron job (default: 03:00 local time) triggers
  ``POST /pipeline/run``
- Alternative: Slack webhook trigger ("slash command" ``/digest``)
- Pre-cook digests for all personas after pipeline completes
  (already implemented for 3 demo personas)
- Deliver via Slack DM, email, or both (user preference)
- Include a "digest ready" notification in a shared channel

Priority 5: Feedback Loop
---------------------------

**User value:** The digest gets smarter over time. Items the engineer
ignores stop appearing; items they click through get boosted.

**Technical approach:**

- Add thumbs-up/thumbs-down buttons to each digest item
- Track implicit signals: click-through (opened source thread),
  dismissal, pin, forward, dwell time
- Store feedback events in Postgres
- Adjust per-user scoring dimension weights via exponential moving average
  (alpha = 0.05, slow learning rate)
- Guardrails: weights cannot deviate more than +/- 0.15 from role-archetype
  defaults to prevent runaway personalization
- A/B testing framework: random assignment to scoring variants, measure
  engagement rate per variant

Priority 6: Evaluation Framework
----------------------------------

**User value:** Confidence that the system is actually catching the
important things and not hallucinating.

**Technical approach:**

- Golden-set annotations: manually label 50 to 100 atoms from the synthetic
  dataset as ground truth
- Measure extraction precision/recall against golden set
- Track hallucination rate: atoms that fail validation as a percentage
  of total extracted
- Graded scoring beyond binary valid/invalid, assessing whether extracted
  details (numbers, names, dates) match source text exactly
- Automated regression tests: any code change that drops precision below
  baseline fails CI

Priority 7: Multi-Team Support
-------------------------------

**User value:** Generalize from one robotics team to any Slack workspace.
Daily Digest Tool becomes a product, not a bespoke tool.

**Technical approach:**

- Dynamic channel discovery from Slack workspace API
- Workstream inference from channel names and message patterns
  (instead of hardcoded ``config/workstreams.yml``)
- Persona auto-detection from Slack metadata: channel membership for
  workstream affinity, message frequency for topic interest, title/team
  for role archetype
- Self-service onboarding: 3 to 4 question flow generates initial persona
- Multi-tenant Postgres schema with workspace isolation

Priority 8: Configuration UI
-------------------------------

**User value:** Non-technical users can tune the system without editing
YAML files.

**Technical approach:**

- Scoring weight editor: sliders enforcing sum-to-1.0 constraint with
  real-time digest preview
- Persona manager: CRUD interface for personas, workstream affinity
  heatmap, collaborator graph editor
- Scoring matrix editor: visual 5x8 role-type grid with impact feedback
- Phase context editor per workstream

Deferred
---------

These are architecturally understood but not prioritized for near-term:

**Multi-Provider LLM.** The ``AsyncLLMClient`` protocol supports
additional adapters. Re-add when a second provider is needed or when
on-prem inference is required (vLLM, Text Generation Inference with
open-weight models).

**Real-Time Streaming.** Replace batch ingestion with Slack Events API +
Kafka for near-real-time atom extraction. Requires infrastructure beyond
Docker Compose. The current batch model (process yesterday's messages
each morning) is the right approach for the target scale.

**CAD Comment Monitoring.** Onshape and Fusion 360 comments on 3D models
often contain implicit decisions about geometry changes that never reach
Slack.

**Mobile App.** Native digest delivery for engineers on the shop floor
or in the lab. The current web frontend works on mobile browsers but a
native app would improve the daily habit loop.

**On-Prem Inference.** Self-hosted models (Llama, Mistral via vLLM) for
teams with strict IP policies. Higher infra cost, lower extraction
quality, full data sovereignty.
