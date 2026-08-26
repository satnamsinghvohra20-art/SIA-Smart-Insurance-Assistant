"""
ASYNC TRACKER SERVICE
---------------------
Simulates the production pattern:
  1. After human approval, a message ("claim.submitted") is published to a Pub/Sub topic.
  2. A Cloud Run worker container polls the TPA / Insurer claims portal API on a schedule.
  3. Proactive WhatsApp / SMS notifications are dispatched to the claimant on state change.
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
        "whatsapp_msg": "🔔 ClaimPilot Alert: Your claim (Ref: {claim_id}) has been submitted to Star Health TPA. Claim form and cross-verified hospital bills are attached.",
    },
    {
        "status": "Initial Document Scrutiny Passed",
        "description": "Hospital bill authenticity, discharge summary and active policy coverage confirmed.",
        "badge_color": "cyan",
        "whatsapp_msg": "📋 TPA Status: Initial document scrutiny passed! Hospital GSTIN and clinical discharge summary verified.",
    },
    {
        "status": "Medical Adjudication Complete",
        "description": "Doctor diagnosis and line items approved against room rent and procedure sub-limits.",
        "badge_color": "amber",
        "whatsapp_msg": "🩺 TPA Status: Medical Adjudication complete. Laparoscopic Appendectomy approved with zero itemized deductions.",
    },
    {
        "status": "TPA Query: Pre-auth Match Verified",
        "description": "Cross-referenced with hospital admission records. All checks cleared autonomously.",
        "badge_color": "purple",
        "whatsapp_msg": "⚡ ClaimPilot Agent: TPA raised hospital pre-auth query. Resolved autonomously via hospital admission API matching.",
    },
    {
        "status": "Approved — NEFT Settlement Initiated",
        "description": "Final settlement advice generated. Bank transfer in progress to claimant account.",
        "badge_color": "emerald",
        "whatsapp_msg": "🎉 Settlement Approved! ₹69,750 transferred via NEFT to your bank account. Settlement advice PDF sent to your email.",
    },
]


def publish(claim_id: str):
    """Idempotent Pub/Sub event dispatcher."""
    with _lock:
        if claim_id in _tracking_state:
            return
        stage0 = TRACKING_STAGES[0]
        _tracking_state[claim_id] = {
            "claim_id": claim_id,
            "status": stage0["status"],
            "description": stage0["description"],
            "step": 0,
            "total_steps": len(TRACKING_STAGES),
            "started_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "notifications": [
                {
                    "step": 0,
                    "type": "whatsapp",
                    "sender": "ClaimPilot Assistant",
                    "text": stage0["whatsapp_msg"].format(claim_id=claim_id),
                    "timestamp": datetime.utcnow().strftime("%I:%M %p"),
                }
            ],
            "history": [
                {
                    "step": 0,
                    "status": stage0["status"],
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            ],
        }

    log_event(
        claim_id,
        "execution_agent",
        "tracking_started",
        "Pub/Sub message published: topic='claims.submission.v1', dedup_id='" + claim_id + "'. WhatsApp notification sent.",
        tool_call="pubsub_publish_topic",
        payload={"topic": "claims.submission.v1", "idempotency_key": claim_id},
    )

    thread = threading.Thread(target=_simulate_polling_worker, args=(claim_id,), daemon=True)
    thread.start()


def _simulate_polling_worker(claim_id: str):
    """Simulates Cloud Run async status polling worker."""
    for step in range(1, len(TRACKING_STAGES)):
        time.sleep(3.5)
        stage = TRACKING_STAGES[step]
        now_iso = datetime.utcnow().isoformat() + "Z"
        now_time_str = datetime.utcnow().strftime("%I:%M %p")

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
            _tracking_state[claim_id]["notifications"].append({
                "step": step,
                "type": "whatsapp",
                "sender": "ClaimPilot Assistant",
                "text": stage["whatsapp_msg"].format(claim_id=claim_id),
                "timestamp": now_time_str,
            })

        log_event(
            claim_id,
            "execution_agent",
            "status_update",
            f"Cloud Run Poller: TPA status progressed to '{stage['status']}'. WhatsApp notification dispatched.",
            tool_call="cloud_run_tpa_poller",
            payload={"step": step, "stage": stage["status"], "whatsapp_sent": True},
        )


def get_status(claim_id: str) -> dict | None:
    with _lock:
        state = _tracking_state.get(claim_id)
        return dict(state) if state else None
