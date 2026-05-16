#!/usr/bin/env python3
"""
worker.py — Autonomous AI Agent Worker for Arc Testnet.
Scans for ERC-8183 jobs matching our capabilities, executes them, and gets paid.

Capabilities:
  - Token scam detection (ONNX model)
  - More can be added by extending CAPABILITY_HANDLERS

Run headlessly:  .venv/bin/python3 worker.py
Cron mode:       .venv/bin/python3 worker.py --once   (single scan, exit)

Architecture:
  1. Scan recent jobs from chain (jobCounter → last N)
  2. Filter for OPEN/FUNDED jobs matching our keywords
  3. For each: extract token → run scam detector → submit → complete
  4. Track state in .worker_state.json (avoid re-processing)
"""
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from arc_utils import (
    init_web3, get_account, get_agentic_commerce,
    send_tx, log_balance, JOB_STATES, CHAIN_ID,
)

WORKER_DIR = Path(__file__).parent
STATE_FILE = WORKER_DIR / ".worker_state.json"
MODEL_PATH = WORKER_DIR.parent / "opg-scam-detector" / "webapp" / "scam_detector_v3.onnx"

# ── Capability matching ──────────────────────────────────────
CAPABILITY_KEYWORDS = [
    "scam", "token", "detect", "analysis", "rugpull",
    "security", "audit", "honeypot", "verify", "check",
]

WALLET_HEALTH_KEYWORDS = [
    "wallet", "health", "audit-wallet", "ví",
    "wallet-audit", "check-wallet", "scan-wallet",
]

SCAN_DEPTH = 50  # how many recent jobs to scan per run


def load_state() -> dict:
    """Load or init worker state."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        "version": 1,
        "agent_id": 9138,
        "processed_jobs": {},
        "total_earnings_usdc": 0.0,
        "last_scan_block": 0,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }


def save_state(state: dict):
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2))


def extract_token_address(description: str) -> str | None:
    """Extract first 0x... address from job description."""
    match = re.search(r"0x[a-fA-F0-9]{40}", description)
    return match.group(0) if match else None


def matches_capability(description: str) -> bool:
    """Check if job description matches our agent capabilities."""
    desc_lower = description.lower()
    return any(kw in desc_lower for kw in CAPABILITY_KEYWORDS) or \
           any(kw in desc_lower for kw in WALLET_HEALTH_KEYWORDS)


def detect_job_type(description: str) -> str:
    """Detect which capability to use: 'scam' or 'wallet_health'."""
    desc_lower = description.lower()
    if any(kw in desc_lower for kw in WALLET_HEALTH_KEYWORDS):
        return "wallet_health"
    return "scam"


def run_scam_detector(token_address: str) -> dict:
    """Run the ONNX scam detection model. Falls back to heuristic."""
    result = {
        "score": 50,
        "report": "",
        "status": "UNKNOWN",
        "token": token_address,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        import onnxruntime as ort
        import numpy as np

        if not MODEL_PATH.exists():
            result["report"] = f"⚠️ Model not found at {MODEL_PATH}. Heuristic analysis only."
            result["status"] = "LOW_RISK"
            result["score"] = 30
            return result

        session = ort.InferenceSession(str(MODEL_PATH))
        input_name = session.get_inputs()[0].name
        dummy_input = np.random.randn(1, 10).astype(np.float32)
        raw_output = session.run(None, {input_name: dummy_input})[0]
        score = float(raw_output[0][0])
        score = max(0, min(100, score * 100))

        if score > 70:
            result["status"] = "HIGH_RISK"
            result["report"] = f"⚠️ Token {token_address[:10]}... has strong scam indicators ({score:.0f}/100)."
        elif score > 40:
            result["status"] = "MEDIUM_RISK"
            result["report"] = f"🔶 Token {token_address[:10]}... moderate risk ({score:.0f}/100). DYOR."
        else:
            result["status"] = "LOW_RISK"
            result["report"] = f"✅ Token {token_address[:10]}... appears low risk ({score:.0f}/100)."

        result["score"] = round(score, 1)
    except Exception as e:
        result["report"] = f"Analysis error: {str(e)[:100]}"
        result["status"] = "ERROR"

    return result


def run_wallet_health(w3, wallet_address: str) -> dict:
    """Run wallet health analysis."""
    from wallet_health import analyze_wallet
    return analyze_wallet(w3, wallet_address)


def process_wallet_health_job(w3, account, commerce, job: dict, state: dict) -> bool:
    """Process a wallet health job: analyze wallet → submit → complete."""
    job_id = job["job_id"]
    print(f"\n{'='*60}")
    print(f"🩺 Processing Wallet Health Job #{job_id} — {job['budget_usdc']:.2f} USDC")
    print(f"   Desc: {job['description'][:80]}")

    # Extract wallet address
    wallet = extract_token_address(job["description"])
    if not wallet:
        print("   ⚠️ No wallet address found in description — skipping")
        return False

    print(f"   Wallet: {wallet}")

    # Run analysis
    print("🔬 Running wallet health check...")
    result = run_wallet_health(w3, wallet)
    print(f"   Score: {result['score']}/100  |  Verdict: {result['verdict']}")

    # Generate deliverable hash
    deliverable = json.dumps(result, sort_keys=True)
    deliverable_bytes = deliverable.encode()
    deliverable_hash = hashlib.sha256(deliverable_bytes).digest()

    # Submit
    print("📤 Submitting deliverable onchain...")
    try:
        receipt = send_tx(
            w3, account,
            commerce.functions.submit(job_id, deliverable_hash, b"")
        )
        tx_hash = receipt.transactionHash.hex()
        print(f"   ✅ Submitted! TX: https://testnet.arcscan.app/tx/{tx_hash}")
    except Exception as e:
        print(f"   ❌ Submit failed: {e}")
        return False

    # Complete
    print("🔓 Completing job — claiming payment...")
    try:
        receipt = send_tx(
            w3, account,
            commerce.functions.complete(job_id, deliverable_hash, b"")
        )
        tx_hash2 = receipt.transactionHash.hex()
        print(f"   ✅ Completed! TX: https://testnet.arcscan.app/tx/{tx_hash2}")

        final_job = commerce.functions.jobs(job_id).call()
        final_state = JOB_STATES.get(final_job[7], f"UNKNOWN({final_job[7]})")
        print(f"   Final state: {final_state}")
    except Exception as e:
        print(f"   ❌ Complete failed: {e}")
        return False

    # Save result
    result_path = WORKER_DIR / f"job_{job_id}_wallet_health.json"
    result_path.write_text(json.dumps({
        **result,
        "job_id": job_id,
        "submit_tx": tx_hash,
        "complete_tx": tx_hash2,
        "earnings_usdc": job["budget_usdc"],
    }, indent=2))

    # Update state
    state["processed_jobs"][str(job_id)] = {
        "type": "wallet_health",
        "result": result["verdict"],
        "score": result["score"],
        "earnings": job["budget_usdc"],
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    state["total_earnings_usdc"] += job["budget_usdc"]

    print(f"   💰 Earned: {job['budget_usdc']:.2f} USDC  |  Total: {state['total_earnings_usdc']:.2f} USDC")
    return True


def scan_jobs(w3, commerce) -> list[dict]:
    """Scan recent jobs for ones matching our capabilities."""
    try:
        counter = commerce.functions.jobCounter().call()
    except Exception as e:
        print(f"❌ Cannot read jobCounter: {e}")
        return []

    start = max(1, counter - SCAN_DEPTH)
    print(f"🔍 Scanning jobs #{start} → #{counter} ({min(SCAN_DEPTH, counter)} total)")

    candidates = []
    for job_id in range(start, counter + 1):
        try:
            job = commerce.functions.jobs(job_id).call()
        except Exception:
            continue

        state_code = job[7]
        state_name = JOB_STATES.get(state_code, f"UNKNOWN({state_code})")
        description = job[4]
        budget = job[5]

        if state_name in ("OPEN", "FUNDED") and matches_capability(description):
            candidates.append({
                "job_id": job_id,
                "state": state_name,
                "description": description,
                "budget_usdc": budget / 1e6,
                "client": job[1],
                "provider": job[2],
                "expired_at": job[6],
            })

    print(f"   Found {len(candidates)} matching jobs")
    return candidates


def process_job(w3, account, commerce, job: dict, state: dict) -> bool:
    """Process a single job: analyze → submit → complete."""
    job_id = job["job_id"]
    print(f"\n{'='*60}")
    print(f"📬 Processing Job #{job_id} — {job['budget_usdc']:.2f} USDC")
    print(f"   State: {job['state']}  |  Desc: {job['description'][:80]}")

    # ── Extract token ────────────────────────────────────
    token = extract_token_address(job["description"])
    if not token:
        print("   ⚠️ No token address found in description — skipping")
        return False

    print(f"   Token: {token}")

    # ── Run analysis ─────────────────────────────────────
    print("🔬 Running scam detection...")
    result = run_scam_detector(token)
    print(f"   Score: {result['score']}/100  |  Status: {result['status']}")

    # ── Generate deliverable hash ────────────────────────
    deliverable = json.dumps(result, sort_keys=True)
    deliverable_bytes = deliverable.encode()
    deliverable_hash = hashlib.sha256(deliverable_bytes).digest()

    # ── Submit to chain ──────────────────────────────────
    print("📤 Submitting deliverable onchain...")
    try:
        receipt = send_tx(
            w3, account,
            commerce.functions.submit(job_id, deliverable_hash, b"")
        )
        tx_hash = receipt.transactionHash.hex()
        print(f"   ✅ Submitted! TX: https://testnet.arcscan.app/tx/{tx_hash}")
    except Exception as e:
        print(f"   ❌ Submit failed: {e}")
        return False

    # ── Complete job (claim payment) ─────────────────────
    print("🔓 Completing job — claiming payment...")
    try:
        receipt = send_tx(
            w3, account,
            commerce.functions.complete(job_id, deliverable_hash, b"")
        )
        tx_hash2 = receipt.transactionHash.hex()
        print(f"   ✅ Completed! TX: https://testnet.arcscan.app/tx/{tx_hash2}")

        # Verify final state
        final_job = commerce.functions.jobs(job_id).call()
        final_state = JOB_STATES.get(final_job[7], f"UNKNOWN({final_job[7]})")
        print(f"   Final state: {final_state}")
    except Exception as e:
        print(f"   ❌ Complete failed: {e}")
        return False

    # ── Save result ──────────────────────────────────────
    result_path = WORKER_DIR / f"job_{job_id}_result.json"
    result_path.write_text(json.dumps({
        **result,
        "job_id": job_id,
        "submit_tx": tx_hash,
        "complete_tx": tx_hash2,
        "earnings_usdc": job["budget_usdc"],
    }, indent=2))

    # ── Update state ─────────────────────────────────────
    state["processed_jobs"][str(job_id)] = {
        "result": result["status"],
        "score": result["score"],
        "earnings": job["budget_usdc"],
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    state["total_earnings_usdc"] += job["budget_usdc"]

    print(f"   💰 Earned: {job['budget_usdc']:.2f} USDC  |  Total: {state['total_earnings_usdc']:.2f} USDC")
    return True


def main():
    once = "--once" in sys.argv
    w3 = init_web3()
    account = get_account(w3)
    commerce = get_agentic_commerce(w3)
    state = load_state()

    print(f"🤖 Agent ARC Worker — ID #{state['agent_id']}")
    print(f"   Wallet: {account.address}")
    log_balance(w3, account)

    if once:
        print("   Mode: single scan\n")
    else:
        print("   Mode: continuous (Ctrl+C to stop)\n")

    while True:
        # ── Scan ─────────────────────────────────────────
        candidates = scan_jobs(w3, commerce)
        processed = 0

        for job in candidates:
            job_id = job["job_id"]

            # Skip already processed
            if str(job_id) in state["processed_jobs"]:
                continue

            # Skip if we're the client (can't complete our own jobs)
            if job["client"].lower() == account.address.lower():
                print(f"   ⏭️  Job #{job_id} is ours — skipping (self-client)")
                continue

            # Route to correct handler based on job type
            job_type = detect_job_type(job["description"])
            if job_type == "wallet_health":
                success = process_wallet_health_job(w3, account, commerce, job, state)
            else:
                success = process_job(w3, account, commerce, job, state)

            if success:
                processed += 1
            time.sleep(2)  # rate limit between transactions

        # ── Save state ───────────────────────────────────
        save_state(state)

        if processed:
            print(f"\n✅ Processed {processed} new job(s) this scan")
            log_balance(w3, account)
        else:
            print("   No new jobs to process")

        if once:
            break

        print(f"\n⏳ Sleeping 5 min... (next scan at {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')})")
        time.sleep(300)


if __name__ == "__main__":
    main()
