#!/usr/bin/env python3
"""
create_job.py — Create an ERC-8183 job on Arc Testnet.

A client creates a job, sets a budget, approves USDC, and funds escrow.
The job is then ready for an agent (provider) to pick up.

Usage:
    python3 create_job.py [--agent-id AGENT_ID] [--budget USDC_AMOUNT]
"""
import time
import argparse
from arc_utils import (
    init_web3, get_account, get_agentic_commerce, get_usdc,
    send_tx, log_balance, AGENTIC_COMMERCE, USDC_TOKEN,
)


def create_job(agent_address: str, budget_usdc: float = 1.0):
    """Full ERC-8183 job lifecycle: create → set budget → fund."""
    w3 = init_web3()
    account = get_account(w3)
    commerce = get_agentic_commerce(w3)
    usdc = get_usdc(w3)

    print(f"🔗 Arc Testnet | Chain ID: {w3.eth.chain_id}")
    print(f"📋 AgenticCommerce: {AGENTIC_COMMERCE}")
    log_balance(w3, account)
    print()

    # Convert USDC amount to raw (6 decimals) — but Arc native uses 18 decimals
    # The USDC ERC-20 interface uses 6 decimals
    decimals = usdc.functions.decimals().call()
    budget_raw = int(budget_usdc * 10**decimals)

    # ── Step 1: Create Job ────────────────────────────────
    expired_at = int(time.time()) + 86400  # 24 hours from now
    description = (
        f"Token Scam Analysis: Run scam detection model on a given token address. "
        f"Return risk score (0-100) and detailed report. "
        f"Agent: Hermes Scam Detector v1.0 by Leonis Forge."
    )

    print(f"📝 Creating job...")
    print(f"   Provider:       {agent_address}")
    print(f"   Evaluator:      {account.address} (same as client)")
    print(f"   Expires in:     24 hours")
    print(f"   Description:    {description[:80]}...")

    receipt = send_tx(
        w3, account,
        commerce.functions.createJob(
            agent_address,          # provider
            account.address,        # evaluator (same as client for demo)
            expired_at,
            description,
            "0x0000000000000000000000000000000000000000",  # no hook
        )
    )
    print(f"✅ Job created! TX: https://testnet.arcscan.app/tx/{receipt.transactionHash.hex()}")

    # Extract job ID from event
    job_id = None
    for log in receipt.logs:
        try:
            decoded = commerce.events.JobCreated().process_log(log)
            job_id = decoded.args.jobId
            print(f"🆔 Job ID: {job_id}")
            break
        except Exception:
            pass

    if not job_id:
        raise RuntimeError("Could not extract job ID from receipt")

    # ── Step 2: Set Budget ────────────────────────────────
    print(f"\n💰 Setting budget: {budget_usdc} USDC")
    receipt = send_tx(
        w3, account,
        commerce.functions.setBudget(job_id, budget_raw, b"")
    )
    print(f"✅ Budget set! TX: https://testnet.arcscan.app/tx/{receipt.transactionHash.hex()}")

    # ── Step 3: Approve USDC ──────────────────────────────
    print(f"\n🔓 Approving USDC spend...")
    receipt = send_tx(
        w3, account,
        usdc.functions.approve(AGENTIC_COMMERCE, budget_raw)
    )
    print(f"✅ USDC approved! TX: https://testnet.arcscan.app/tx/{receipt.transactionHash.hex()}")

    # ── Step 4: Fund Escrow ───────────────────────────────
    print(f"\n💸 Funding escrow with {budget_usdc} USDC...")
    receipt = send_tx(
        w3, account,
        commerce.functions.fund(job_id, b"")
    )
    print(f"✅ Escrow funded! TX: https://testnet.arcscan.app/tx/{receipt.transactionHash.hex()}")

    # ── Summary ───────────────────────────────────────────
    log_balance(w3, account)
    print()
    print("=" * 55)
    print("🎯 Job ready for agent to process!")
    print(f"   Job ID: {job_id}")
    print(f"   Budget: {budget_usdc} USDC (in escrow)")
    print(f"   Provider: {agent_address}")
    print()
    print("Next step:")
    print(f"   python3 process_job.py --job-id {job_id}")
    print("=" * 55)

    return job_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create an ERC-8183 job on Arc Testnet")
    parser.add_argument("--agent-id", type=int, help="ERC-8004 agent ID (unused for now, pass address)")
    parser.add_argument("--agent-address", type=str, required=True, 
                        help="Provider wallet address (the agent's wallet)")
    parser.add_argument("--budget", type=float, default=1.0,
                        help="Job budget in USDC (default: 1.0)")
    args = parser.parse_args()
    create_job(args.agent_address, args.budget)
