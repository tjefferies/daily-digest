Next Steps: Follow-On Work and Production Path
================================================

This document outlines recommended follow-on work after the EverCurrent
prototype is delivered. It expands upon the recommendations in the
design document (sections 8, 10.2, 11) and includes additional
observations from building the prototype.

1. Stakeholder Questions
-------------------------

These questions, expanded from design document section 11, should be
answered before production scoping begins. Each answer materially
changes the architecture.

**1.1 IP Classification (Highest Priority)**

Does the Slack content contain trade secrets, ITAR-controlled data, or
other IP that prohibits cloud LLM processing? This is the single most
impactful question for production cost and quality:

- **Cloud OK** (standard enterprise agreement): Use Anthropic API
  directly. Cost: ~$150-$450/month for 300-500 messages/day.
- **On-prem required**: Self-hosted inference (vLLM + open-weight model).
  Significantly higher infra cost, lower extraction quality, requires
  ML ops team.

**1.2 PM Tool Integration**

Does the team use Jira, Linear, or Asana for phase-gate tracking? If
yes, phase transitions can be detected automatically from ticket status
changes rather than relying on manual phase toggle or language inference.
This eliminates the biggest UX friction in the current design.

**1.3 Multi-Source Ingestion**

Is Slack the sole communication channel, or do decisions also occur in:

- Email threads
- Google Docs / Confluence comments
- Onshape / Fusion 360 revision notes
- PLM system change orders

If multi-source, the ingestion layer needs a plugin architecture with
per-source adapters. The current channel-based routing assumes Slack
exclusively.

**1.4 User Research**

Have user interviews or surveys been conducted? Concrete failure stories
("I missed X and it cost us Y") are the most valuable input for:

- Tuning the atom type taxonomy (are there information types we miss?)
- Calibrating scoring weights (is urgency too low? too high?)
- Validating the three-persona approach vs. per-user configuration

**1.5 Organizational Structure**

Are roles cleanly defined, or do people routinely operate across
multiple functional areas? If engineers frequently wear multiple hats,
the persona model should use learned behavior profiles (which channels
do they read, which threads do they respond to) rather than static role
archetypes.


2. Live Data Integration
-------------------------

The prototype uses a synthetic 150+ message dataset. Moving to live
data requires:

**2.1 Slack App Setup**

- Create a Slack App with OAuth 2.0 bot token
- Request scopes: ``channels:history``, ``channels:read``,
  ``groups:history``, ``groups:read``, ``users:read``
- Handle workspace installation and token refresh

**2.2 Ingestion Strategy**

- **Webhook (preferred)**: Use Slack Events API to receive messages in
  real-time. Lower latency, no polling overhead. Requires a publicly
  accessible endpoint or Slack Socket Mode.
- **Polling (fallback)**: ``conversations.history`` API with cursor-based
  pagination. Simpler to implement but higher API rate limit risk.

**2.3 Message Deduplication**

Messages can arrive via both webhook and catch-up polling. Deduplicate
on ``(channel_id, message_ts)`` composite key. Handle message edits
(``message_changed`` subtype) and deletes (``message_deleted`` subtype)
by updating or tombstoning the corresponding atoms.

**2.4 Incremental Processing**

Rather than re-processing all messages daily, maintain a high-water mark
per channel and only process new messages since the last run. This
reduces API cost linearly as the team grows.


3. Configuration Interface
---------------------------

The YAML config files (``config/``) work well for developer tuning but
are not accessible to non-technical users. A configuration UI would
enable:

**3.1 Scoring Weight Editor**

- Web form for adjusting the five dimension weights (sliders that
  enforce sum-to-1.0 constraint)
- Real-time preview: show how weight changes affect the current
  persona's digest ranking
- A/B comparison: side-by-side view of digest with old vs. new weights

**3.2 Persona Manager**

- CRUD interface for personas (add/edit/remove)
- Workstream affinity editor with visual heatmap
- Collaborator graph editor (who does this person work closely with?)
- Phase context editor per workstream

**3.3 Scoring Matrix Editor**

- Editable role-type alignment matrix (5x8 grid)
- Visual feedback showing which cells have the biggest impact
- Versioning: save and compare different matrix configurations


4. Adaptive Feedback Loop
--------------------------

Design document section 5.4 describes an adaptive weight learning
mechanism that is currently stubbed. Implementation path:

**4.1 Implicit Signals**

Track user behavior without requiring explicit feedback:

- **Dismissals**: User swipes away or collapses a digest item
- **Pins**: User pins or stars an item for follow-up
- **Forwards**: User shares a digest item to a channel or DM
- **Dwell time**: How long the user spends reading each section
- **Click-through**: User clicks the source link to read the original
  thread

**4.2 Weight Learning**

Use the implicit signals to adjust per-user scoring weights over time:

- Start with role-archetype defaults (current behavior)
- After N interactions, blend in learned adjustments
- Exponential moving average to adapt to changing interests
- Guardrails: weights cannot deviate more than ±0.15 from defaults to
  prevent runaway personalization

**4.3 A/B Testing Framework**

- Random assignment of users to scoring variants
- Measure engagement rate, click-through rate, and missed-signal rate
  per variant
- Statistical significance testing before rolling out changes


5. Production Hardening
------------------------

The prototype prioritizes correctness and demo-ability over production
resilience. For deployment:

**5.1 Persistent Storage**

- Replace in-memory state with PostgreSQL
- Store: extracted atoms (with embeddings for future semantic search),
  generated digests (for audit trail), user feedback events, phase
  history timeline

**5.2 Authentication and Authorization**

- Slack OAuth for user identity
- RBAC: admin (edit configs, manage personas), user (view own digest)
- API key management for programmatic access

**5.3 Observability**

- Structured logging (JSON) with correlation IDs per pipeline run
- Metrics: extraction latency, scoring distribution, generation time,
  API error rate, cache hit rate
- Distributed tracing (OpenTelemetry) across pipeline stages
- Alerting on: extraction failure rate > 5%, generation timeout,
  coverage drop below 90%

**5.4 Error Handling and Retry**

- Exponential backoff for Anthropic API rate limits
- Dead letter queue for failed extractions
- Circuit breaker for upstream service failures
- Graceful degradation: serve stale digest if generation fails

**5.5 Caching**

- Cache extracted atoms for 24 hours (messages don't change retroactively)
- Cache scored atoms per persona until phase vector changes
- Cache generated digest HTML until new atoms arrive
- Invalidation: phase override clears scoring cache for that persona


6. Scaling Path
----------------

Design document section 8.2 outlines three tiers:

**6.1 Small Tier (current prototype scope)**

- 10-30 people, 200-500 msgs/day
- Nightly batch, SQLite or Postgres
- Single Anthropic API key

**6.2 Medium Tier**

- 50-100 people, 1K-3K msgs/day
- Parallelized extraction with asyncio worker pool
- Message deduplication and channel prioritization
- Redis cache layer for scoring results

**6.3 Large Tier**

- 100-500 people, 5K-20K msgs/day
- Stream processor (Kafka) for real-time ingestion
- Searchable atom index (Elasticsearch) for historical queries
- Multiple LLM accounts or self-hosted inference cluster
- Sharded persona scoring across workers


7. Additional Integrations
---------------------------

**7.1 PLM / ERP Connectors**

Hardware teams often track bill-of-materials changes and ECOs in PLM
systems (Arena, Teamcenter). A PLM connector could:

- Auto-detect spec changes from ECO notifications
- Cross-reference atom mentions of part numbers with PLM records
- Flag atoms that mention parts with pending ECOs

**7.2 CAD Comment Monitoring**

Onshape and Fusion 360 support threaded comments on 3D models. These
comments often contain implicit decisions about geometry changes that
never reach Slack.

**7.3 Ticket System Synchronization**

Bidirectional sync with Jira/Linear:

- Create tickets from "Requires Your Action" digest items
- Update phase context from ticket board status transitions
- Link atoms to existing tickets for traceability


8. Phase Transition Detection
------------------------------

The current design requires manual phase toggle (frontend) or
``phase_override`` query parameter. Automated detection would use:

**8.1 Language Pattern Analysis**

Detect phase transitions from Slack messages:

- Milestone language: "DVT units arrived", "passed gate review",
  "production tooling ordered"
- Status updates: "moving to DVT next week", "EVT complete"

**8.2 Atom Type Distribution Shift**

A shift from design-focused atoms (SPEC_CHANGE, DECISION) to
test-focused atoms (TEST_RESULT, RISK) suggests an EVT → DVT
transition. Track the rolling 7-day distribution of atom types per
workstream and flag when it crosses a threshold.

**8.3 PM Tool Integration**

If the team uses Jira/Linear with phase-gate workflows, phase
transitions can be detected from ticket status changes with 100%
accuracy.


9. Evaluation in Production
-----------------------------

Design document section 10.2 defines four production metrics:

**9.1 Time-to-Awareness**

Target: same-day awareness for high-impact atoms. Measure the time
delta between a message being posted and the recipient reading the
relevant digest item. Requires click-through tracking.

**9.2 Missed-Signal Rate**

Target: zero missed ``SPEC_CHANGE`` and ``DECISION`` atoms above
critical threshold. Periodically audit by comparing digest content
against a manually curated "ground truth" set of important atoms.

**9.3 Digest Engagement Rate**

Target: 70%+ daily open rate. Below 50% signals insufficient value.
Measure by tracking digest view events per user per day.

**9.4 False Positive Rate**

Target: <15% irrelevant items in "Requires Your Action" section.
Measure via user dismissal rate of action items. High false positive
rate erodes trust faster than missing items.


10. Model-Agnostic Client Harness
-----------------------------------

The pipeline now uses a model-agnostic ``LLMClient`` protocol
(``src/evercurrent/llm/``) with adapters for Anthropic, OpenAI, and
Google Gemini. Provider selection is driven by ``config/pipeline.yml``.
This abstraction enables several follow-on capabilities:

**10.1 On-Premises / Self-Hosted Models**

For teams where data sensitivity prohibits sending Slack content to
cloud LLM providers (ITAR, trade secrets, export controls), the client
harness can be extended with adapters for self-hosted inference:

- **vLLM**: High-throughput serving of open-weight models (Llama 3,
  Mistral, Qwen). Exposes an OpenAI-compatible API, so the existing
  ``OpenAIAdapter`` works with a custom ``base_url`` pointed at the
  local vLLM endpoint.
- **Ollama**: Single-binary local inference for development and small
  deployments. Useful for engineers who want to run the full pipeline
  on a laptop without network egress.
- **Text Generation Inference (TGI)**: Hugging Face's production
  serving stack with continuous batching and quantization support.
  Requires a dedicated adapter due to its unique streaming API.

**10.2 Provider Failover and Load Balancing**

The adapter pattern enables transparent failover between providers:

- Primary: Anthropic Claude (highest extraction quality)
- Fallback: OpenAI GPT-4o (if Anthropic rate-limited or down)
- Cost tier: Google Gemini Flash (for low-priority batch processing)

A ``FallbackAdapter`` could wrap multiple adapters and try each in
order, with circuit breaker logic to avoid hammering a failing provider.

**10.3 Model Evaluation Harness**

With a common interface, the same evaluation suite can compare
extraction quality across providers:

- Run the same test corpus through each provider
- Compare atom extraction precision/recall
- Measure cost per 1000 atoms extracted
- Track latency percentiles (p50, p95, p99)

This data directly informs provider selection decisions and contract
negotiations.


11. Security and Compliance
-----------------------------

**11.1 On-Premises Inference**

For teams with strict IP policies, deploy a self-hosted inference stack:

- vLLM or TGI serving an open-weight model (Llama 3, Mistral)
- Local GPU cluster or cloud VPC with no external network egress
- Model fine-tuning on domain-specific extraction examples

**11.2 Data Retention**

- Define retention policies per data type (messages: 90 days, atoms:
  1 year, digests: 30 days)
- Implement TTL-based cleanup for expired records
- Support right-to-delete for individual user data (GDPR/CCPA)

**11.3 Audit Logging**

- Log all data access events (who viewed which digest, when)
- Log all configuration changes (who changed scoring weights, when)
- Immutable audit trail for compliance review

**11.4 SOC 2 Considerations**

For enterprise deployment, address SOC 2 Type II requirements:

- Access controls and least-privilege authentication
- Encryption at rest (database) and in transit (TLS)
- Incident response procedures for data breach
- Regular penetration testing and vulnerability scanning (the GitHub
  Actions pipeline already includes semgrep, bandit, and SBOM scanning
  as a foundation)
