#!/usr/bin/env python3
"""
complete_job.py — Evaluator verifies deliverable and completes the ERC-8183 job.

Completing the job releases escrowed USDC from the contract to the provider (agent).

Usage:
    python3 complete_job.py --job-id JOB_ID

This should be run by the EVALUATOR (same wallet that created the job).
"""
import argparse
from arc_utils import (
    init_web3, get_account, get_agentic_commerce,
    send_tx, log_balance, JOB_STATES,
)


def complete_job(job_id: int):
    w3 = init_web3()
    account = get_account(w3)
    commerce = get_agentic_commerce(w3)

    print(f"✅ Completing Job #{job_id}")
    log_balance(w3, account)
    print()

    # ── Read Job State ────────────────────────────────────
    print("📖 Reading job state...")
    try:
        # jobs() returns: (jobId, client, provider, evaluator, description, budget, expiredAt, state, hook)
        job = commerce.functions.jobs(job_id).call()
    except Exception as e:
        print(f"❌ Cannot read job #{job_id}: {e}")
        return

    state = JOB_STATES.get(job[7], f"UNKNOWN({job[7]})")
    print(f"   Description:      {job[4][:80]}")
    print(f"   Budget:           {job[5] / 1e6:.2f} USDC")
    print(f"   Current state:    {state}")
    print(f"   Provider:         {job[2]}")
    print(f"   Client:           {job[1]}")

    if state != "DELIVERED":
        print(f"\n⚠️ Job must be in 'DELIVERED' state to complete. Current: {state}")
        print("   Run process_job.py first to submit the deliverable.")
        return

    # ── Complete Job ──────────────────────────────────────
    print(f"\n🔓 Completing job — releasing {job[5] / 1e6:.2f} USDC to provider...")
    print(f"   Provider address: {job[2]}")

    try:
        receipt = send_tx(w3, account, commerce.functions.complete(job_id, b'\x00' * 32, b''))
        print(f"✅ Job completed!")
        print(f"   TX: https://testnet.arcscan.app/tx/{receipt.transactionHash.hex()}")

        # Verify final state — jobs() returns (jobId, client, provider, evaluator, description, budget, expiredAt, state, hook)
        job = commerce.functions.jobs(job_id).call()
        final_state = JOB_STATES.get(job[7], f"UNKNOWN({job[7]})")
        print(f"   Final state: {final_state}")

    except Exception as e:
        print(f"❌ Completion failed: {e}")
        return

    log_balance(w3, account)
    print()
    print("=" * 55)
    print("🎉 Full agent job lifecycle complete!")
    print(f"   Job #{job_id}: Created → Funded → Processed → Completed")
    print(f"   Provider earned: {job[5] / 1e6:.2f} USDC")
    print("=" * 55)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Complete an ERC-8183 job on Arc Testnet")
    parser.add_argument("--job-id", type=int, required=True, help="Job ID to complete")
    args = parser.parse_args()
    complete_job(args.job_id)
