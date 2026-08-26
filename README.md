# ClaimPilot — Working Prototype

A real, running implementation of the 3-agent insurance-claim pipeline:
**Intake Agent → Decision Agent → Execution Agent**, with a live agent
activity log, PDF claim-form generation, and an async status-tracking
simulation.

This is not a mockup — every piece actually runs: real regex/heuristic
document extraction, a real deterministic eligibility rules engine, real
PDF generation with `reportlab`, and a real background thread that
simulates the Pub/Sub → Cloud Run polling loop.

## Run it

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Then open `frontend/index.html` directly in a browser (double-click it, or
`open frontend/index.html` / `xdg-open frontend/index.html`). No build step
needed — it's a single static file that talks to `http://localhost:8000`.

**Demo flow:** click **Load sample bill** → **Run Intake Agent** → **Run
Decision Agent** → **Run Execution Agent** → **Approve & Submit**. Watch the
pipeline rail light up and the agent log stream on the right. After
approving, the tracking status will cycle through
`Submitted → Under Review by TPA → Query Raised → Approved` over about
15 seconds (compressed from what would be days in production) so the async
behavior is visible without waiting.

## What's real vs. what's a labeled stand-in

Everything runs end-to-end. Three spots are intentionally built as clean,
swappable stand-ins for services this sandbox can't reach (no internet
access to Vertex AI / GCP from here) — each is marked `PRODUCTION SWAP
POINT` in the code with the exact replacement:

| Component | Prototype implementation | Production swap |
|---|---|---|
| Document extraction (`agents/intake_agent.py`) | Regex/heuristic parsing of bill text, with confidence scoring | Gemini 3.5 (Vertex AI) multimodal call on the bill image/PDF — same `{field: {value, confidence}}` contract |
| Ambiguous exclusion-clause reasoning (`agents/decision_agent.py`) | Substring match against the exclusion list | Gemini reasoning over free-text policy wording |
| Claim store (`main.py`) | In-memory Python dict | Firestore |
| Async tracking (`services/async_tracker.py`) | Background thread + `time.sleep` | Pub/Sub topic + Cloud Run scheduled job polling the TPA API |
| Form submission (`agents/execution_agent.py: submit_to_tpa`) | Logs a simulated submission | Real HTTP call to the insurer/TPA portal API |

The eligibility math itself (waiting period, co-pay, sum-insured cap,
filing-window deadline) is **deliberately not an LLM call** — it's a
deterministic rules engine reading `data/policy_rules.json`, because
eligibility amounts need to be reproducible and auditable, not generated.
This is worth saying explicitly in a demo/judging Q&A.

## What's genuinely production-shaped already

- **3 cleanly separated agents**, each independently testable, matching
  the architecture diagram
- **Confidence-scored extraction** with a review flag — the frontend
  visibly highlights low-confidence fields rather than silently trusting
  the extraction
- **Human-approval gate** before any "submission" happens
- **Append-only audit log** per claim, streamed live to the UI — maps
  directly onto a Firestore subcollection
- **Idempotent async publish** — `async_tracker.publish()` is a no-op if
  the claim is already tracked, so a duplicate Pub/Sub delivery can't
  double-submit
- **Real generated artifact** — the claim-form PDF is an actual filled
  document you can open, not a placeholder

## Project layout

```
claimpilot/
├── backend/
│   ├── main.py                  # FastAPI orchestration + endpoints
│   ├── agents/
│   │   ├── intake_agent.py      # extraction + confidence scoring
│   │   ├── decision_agent.py    # deterministic eligibility rules engine
│   │   └── execution_agent.py   # PDF form generation + checklist
│   ├── services/
│   │   ├── audit_log.py         # append-only per-claim event log
│   │   └── async_tracker.py     # Pub/Sub + Cloud Run job stand-in
│   ├── data/
│   │   ├── policy_rules.json    # 2 sample insurer policies
│   │   └── sample_bill.txt      # synthetic hospital bill for the demo
│   └── generated/               # claim form PDFs land here at runtime
└── frontend/
    └── index.html               # single-file dashboard (no build step)
```

## Next build steps, in priority order

1. Swap `intake_agent.extract_fields_heuristic()` for a real Gemini 3.5
   Vertex AI multimodal call — this is the highest-leverage change for
   both real accuracy and demo credibility, since judges will ask about it.
2. Move `CLAIMS` and `audit_log` from in-memory dicts to Firestore so state
   survives a restart and multiple claims can be reviewed side by side.
3. Replace `async_tracker`'s thread-based simulation with an actual
   Pub/Sub topic + a Cloud Run job on a Cloud Scheduler trigger.
4. Add a second sample bill/policy pair (ideally one that deliberately
   fails a rule — expired filing window or an excluded diagnosis) so the
   demo can show both the happy path and a graceful rejection with a clear
   reason, which is often more convincing to judges than an all-success run.
