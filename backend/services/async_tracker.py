"""
ASYNC TRACKER SERVICE
---------------------
Simulates the production pattern:
  1. After human approval, a message ("claim.submitted") is published to a Pub/Sub topic.
  2. A Cloud Run worker container (subscribed to the topic or scheduled via Cloud Scheduler)
     polls the TPA / Insurer claims portal API on a schedule.
  3. Status changes and deadline notifications are written back to Firestore and pushed
     to the user via Webhook / WhatsApp notification.

IDEMPOTENCY:
  `publish()` uses the unique claim_id as a deduplication key. Retrying or duplicate
  Pub/Sub deliveries will safely no-op without double-submitting.
"""
import time
import threading
from datetime import datetime
from services.audit_log import log_event

_lock = threading.Lock()
_tracking_state = {}

TRACKING_STAGES = [
    {
        "status": "Submitted to TPA Portal",
        "description": "Claim payload & IRDAI evidence package acknowledged by TPA Gateway.",
        "badge_color": "blue",
    },
    {
        "status": "Initial Document Scrutiny Passed",
        "description": "Hospital bill authenticity and policy active status verified.",
        "badge_color": "cyan",
    },
    {
        "status": "Medical Adjudication Complete",
        "description": "Doctor diagnosis and itemized line items approved against policy sub-limits.",
        "badge_color": "amber",
    },
    {
        "status": "TPA Query: Pre-auth Match Verified",
        "description": "Cross-referenced with hospital admission records. All checks cleared.",
        "badge_color": "purple",
    },
    {
        "status": "Approved — NEFT Settlement Initiated",
        "description": "Final settlement advice generated. Bank transfer in progress to claimant account.",
        "badge_color": "emerald",
    },
]


def publish(claim_id: str):
    """Idempotent Pub/Sub event dispatcher."""
    with _lock:
        if claim_id in _tracking_state:
            return  # Idempotent: ignore duplicate delivery
        _tracking_state[claim_id] = {
            "claim_id": claim_id,
            "status": TRACKING_STAGES[0]["status"],
            "description": TRACKING_STAGES[0]["description"],
            "step": 0,
            "total_steps": len(TRACKING_STAGES),
            "started_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "history": [
                {
                    "step": 0,
                    "status": TRACKING_STAGES[0]["status"],
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            ],
        }

    log_event(
        claim_id,
        "execution_agent",
        "tracking_started",
        "Pub/Sub message published: topic='claims.submission.v1', dedup_id='" + claim_id + "'.",
        tool_call="pubsub_publish_topic",
        payload={"topic": "claims.submission.v1", "idempotency_key": claim_id},
    )

    # Launch background thread to simulate Cloud Run async polling worker
    thread = threading.Thread(target=_simulate_polling_worker, args=(claim_id,), daemon=True)
    thread.start()


def _simulate_polling_worker(claim_id: str):
    """Simulates Cloud Run async status polling worker."""
    for step in range(1, len(TRACKING_STAGES)):
        time.sleep(3.5)  # Demo speed: 3.5 seconds per milestone
        stage = TRACKING_STAGES[step]
        now_iso = datetime.utcnow().isoformat() + "Z"

        with _lock:
            if claim_id not in _tracking_state:
                return
            _tracking_state[claim_id]["status"] = stage["status"]
            _tracking_state[claim_id]["description"] = stage["description"]
            _tracking_state[claim_id]["step"] = step
            _tracking_state[claim_id]["updated_at"] = now_iso
            _tracking_state[claim_id]["history"].append({
                "step": step,
                "status": stage["status"],
                "timestamp": now_iso,
            })

        log_event(
            claim_id,
            "execution_agent",
            "status_update",
            f"Cloud Run Poller: TPA status progressed to '{stage['status']}'. {stage['description']}",
            tool_call="cloud_run_tpa_poller",
            payload={"step": step, "stage": stage["status"]},
        )


def get_status(claim_id: str) -> dict | None:
    with _lock:
        state = _tracking_state.get(claim_id)
        return dict(state) if state else None
