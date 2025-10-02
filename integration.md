# Panda AGI UI ↔ Wine Marketing Analytics Integration Contract

This document defines the baseline contract for embedding the **Panda AGI chat UI**
(`examples/ui` in `panda-agi`) on top of the **Wine Marketing Analytics platform**
(`/Users/andreyzherditskiy/work/bc/omt-pai-4`). The goal is to let end users run
the existing marketing agents through the Panda chat experience without changing
either product’s core business logic.

---

## 1. Scope & Responsibilities

- **Panda UI Package** – Owns the React frontend, FastAPI bridge, streaming
  protocol, file workspace, and optional authentication middleware.
- **Marketing Analytics Platform** – Owns customer/transaction data, the
  `MarketingService` orchestration layer, Streamlit app, CLI, and Flask API
  (`/marketing/*` endpoints secured by `API_KEY`).
- **Integration Layer** – A new adapter that runs inside the Panda FastAPI backend
  and calls into the marketing service (direct Python import or HTTP call). This
  layer must translate between the Panda streaming contract and the analytics
  responses.

Anything outside these systems (e.g., deployment scripts, UI theming changes,
expanding datasets) is out-of-scope for this contract.

---

## 2. Runtime Modes

| Mode | `CHAT_RUNTIME` | Behavior |
|------|----------------|----------|
| Panda default | `panda-agent` (or unset) | Uses the bundled Panda agent tooling. Not used for the integration pathway. |
| Marketing bridge | `bridge` / `bridge-mediator` | Activates `AgentMediator` (see `examples/ui/backend/services/mediator.py`) so we can plug in the marketing adapter without instantiating `panda_agi.Agent`. |

When the bridge mode is active the legacy Panda file tooling raises 500s; the
integration must either replace those routes or keep the UI’s file features
hidden/disabled.

---

## 3. End-to-End Request Flow

### 3.1 Client → Panda Backend

- **Endpoint**: `POST /agent/run`
- **Headers**: `Content-Type: application/json`, optional `X-Authorization:
  Bearer <token>` if auth is enabled.
- **Body**:

  ```json
  {
    "query": "List VIP customers",
    "conversation_id": "optional"
  }
  ```

- **Behavior**: FastAPI route forwards the payload to `event_stream()` in
  `examples/ui/backend/services/agent.py`, which selects the mediator runtime and
  starts streaming `<event>{json}</event>` chunks over the HTTP response.

### 3.2 Panda Backend → Marketing Platform

Two supported wiring strategies (choose one per deployment):

1. **In-process import** – Import `CustomerAnalyticsAgent` and `MarketingService`
   directly, reusing the existing virtualenv. Recommended for co-located
   deployments because it avoids HTTP overhead and keeps access to cached data.

2. **HTTP bridge** – Call the Flask API endpoints (`/marketing/filters`,
   `/marketing/filter`, `/marketing/customers/<id>`) using `requests`/`httpx` with
   the platform’s `API_KEY`. Required when the analytics service runs in a
   separate container or managed environment.

The adapter must normalize the marketing responses into the streaming contract
below.

---

## 4. Streaming Event Contract

Each chunk sent to the UI **must** follow this envelope because
`event_list.tsx` only renders events whose top-level `event_type` equals
`tool_end` (see `examples/ui/backend/utils/event_processing.py`).

```json
{
  "event_type": "tool_end",
  "timestamp": "<ISO8601 UTC>",
  "data": {
    "type": "marketing_response",        // semantic label
    "tool_name": "omt.marketing.filter",  // used for card title
    "id": "<uuid>",
    "payload": {
      "query": "List VIP customers",
      "engine_used": "fast_path",
      "tokens_used": 0,
      "execution_time": 0.54,
      "count": 42,
      "customer_ids": ["CUST-001", "CUST-002"],
      "customers": [ { ...CustomerRecord... } ],
      "sql": "SELECT ...",
      "metadata": { ...original response metadata... }
    }
  }
}
```

- **`type`** – Free-form tag surfaced in the UI subtitle. Use
  `marketing_response`, `marketing_error`, etc.
- **`tool_name`** – Controls the renderer. Unknown names fall back to
  `ToolUseEvent`, which shows the payload JSON with a toggle. If richer visuals
  are needed later, add a dedicated component and register it in
  `EVENT_COMPONENTS`.
- **`payload`** – Embed the original marketing response so advanced users can see
  SQL, statistics, token counts, etc. Preserve the six-field
  `CustomerRecord` (id, name, segment, lifetime_value, total_purchases,
  avg_order_value, last_purchase_date) defined in `agent/services.py`.

### 4.1 Conversation lifecycle

1. Immediately send the `conversation_started` envelope that Panda already emits
   so the UI stores the conversation ID.
2. Echo the user’s prompt as a `user_send_message` event (the mediator already
   fabricates this; reuse or extend it so the adapter owns the payload).
3. Stream the marketing response as described above. Multiple data events per
   query are allowed (e.g., summary card first, followed by detailed records).
4. On completion, optionally emit a `marketing_completed` event with final
   metrics. If omitted, the UI simply notices no more chunks.

### 4.2 Error channel

For recoverable issues, emit an error envelope:

```json
{
  "event_type": "tool_end",
  "timestamp": "...",
  "data": {
    "type": "error",
    "tool_name": "omt.marketing.error",
    "error": "Failed to reach /marketing/filter (401 Unauthorized)",
    "payload": { "status": 401, "details": "Invalid API key" }
  }
}
```

The UI will display the message using `UserMessageEvent` because `type=error`.
Also return HTTP 4xx/5xx from `/agent/run` if initialization fails before the
stream starts.

---

## 5. Authentication & Secrets

| Component | Requirement |
|-----------|-------------|
| Panda backend | Optional OAuth-style auth (GitHub) via `AuthMiddleware`. If disabled, the UI hits the backend anonymously. |
| Marketing API | Requires `API_KEY` env var (`API_KEY=...`) and expects the same value in either `X-API-Key` or `Authorization: Bearer`. |

**Adapter rules**:

- When running in-process, ensure the marketing environment variables (`API_KEY`,
  OpenAI keys, `USE_CAMPAIGNS`, etc.) are loaded before instantiating
  `CustomerAnalyticsAgent`.
- When calling over HTTP, forward the configured `MARKETING_API_KEY` to the Flask
  service, and make the upstream base URL configurable via `MARKETING_API_URL`.
- Never log full API keys. Use structured logging with request IDs instead.

---

## 6. Configuration Matrix

| Variable | Location | Description |
|----------|----------|-------------|
| `CHAT_RUNTIME` | Panda backend | Set to `bridge` (or `bridge-mediator`) to activate the adapter. |
| `MARKETING_MODE` | Panda backend (new) | `local` (import Python modules) or `http`. Default `local`. |
| `MARKETING_API_URL` | Panda backend (http mode) | Base URL of Flask API, e.g. `http://localhost:5001`. |
| `MARKETING_API_KEY` | Panda backend (http mode) | Credential forwarded as `X-API-Key`. |
| `OPENAI_API_KEY` | Marketing platform | Required by PandasAI 2.4.2. Keep separate from Panda credentials. |
| `USE_CAMPAIGNS` | Marketing platform | Optional toggle for advanced ML pathways; surface via payload metadata if enabled. |

Document the final values in deployment runbooks (Docker Compose, Helm, etc.).

---

## 7. Non-Functional Requirements

- **Latency** – Provide first byte within 2 s for cached/simple queries. The
  analytics service already has a fast-path detector; surface `engine_used` so we
  can monitor fallback to LLM.
- **Throughput** – Single user streaming allowed. Concurrency controls (worker
  pool, rate limiting) should be handled at the API gateway level.
- **Observability** – Log one line per request with fields: `conversation_id`,
  `query`, `engine_used`, `execution_time`, `result_count`, `status`. 4xx/5xx
  logs must include upstream response codes.
- **Resilience** – Retry one time on transient 5xx/timeout when in HTTP mode.
  For persistent failures emit an error event and terminate the stream.
- **Data Residency** – All customer data is synthetic but must remain inside the
  analytics environment. If Panda backend runs separately, use TLS for HTTP
  calls and restrict network access.

---

## 8. File & Attachment Handling

- The marketing platform does not expose a workspace abstraction. Until a
  compatible endpoint exists, hide upload controls in the UI or short-circuit the
  `/files/*` routes with a `501 Not Implemented` response when `CHAT_RUNTIME`
  indicates bridge mode.
- If future requirements include exporting CSVs, define a dedicated event type
  (e.g., `marketing_export`) that links to a presigned download URL rather than
  relying on the Panda workspace download route.

---

## 9. Testing & Acceptance

Before handoff, run the following checks:

1. **Adapter unit tests** – Mock the marketing service (local + HTTP) and assert
   the event envelopes match this spec.
2. **End-to-end manual session** – Launch the Panda UI with
   `CHAT_RUNTIME=bridge`, submit:
   - Preset filter (e.g., "VIP customers only")
   - Custom NL query that triggers PandasAI
   - Invalid API key scenario
   Confirm streamed events render correctly and errors surface in the chat.
3. **Parity regression** – Execute existing marketing parity pytest suite
   (`tests/integration/test_interface_parity.py`) to validate the adapter does
   not modify service behavior.
4. **Performance smoke** – Measure response time for fast-path vs. LLM queries;
   capture metrics in logs.

Sign-off requires screenshots or recordings of the UI session plus log excerpts
showing the expected telemetry fields.

---

## 10. Open Items

- Decide whether the adapter should expose additional auxiliary endpoints (e.g.,
  list of preset filters) so the UI can surface structured filter pickers.
- Confirm which authentication mechanism the client prefers (reuse Panda GitHub
  auth vs. reuse marketing API key vs. new SSO).
- Determine the roadmap for file export/import so the UI buttons can be hidden or
  re-routed consistently.

---

**Primary Contacts**

- Panda UI integration owner: _TBD_
- Marketing platform owner: _TBD_

Please update this document as requirements evolve.
