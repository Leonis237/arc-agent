#!/usr/bin/env python3
"""
register_agent.py — Register an AI agent identity on Arc Testnet (ERC-8004).

Usage:
    python3 register_agent.py

Before running:
    1. Copy .env.example → .env
    2. Set PRIVATE_KEY (wallet with Arc Testnet USDC)
    3. Set AGENT_METADATA_URI (IPFS URI with agent metadata JSON)
    4. Get testnet USDC: https://faucet.circle.com
"""
from arc_utils import (
    init_web3, get_account, get_identity_registry,
    send_tx, log_balance, IDENTITY_REGISTRY,
)

# ── Agent Metadata ────────────────────────────────────────────
# This is a minimal inline metadata JSON — for production, upload to IPFS
# and set AGENT_METADATA_URI in .env
AGENT_METADATA = {
    "name": "Hermes Scam Detector Agent",
    "description": "Onchain AI agent that analyzes crypto tokens for scam patterns using ONNX model inference. Built on Arc by Leonis Forge.",
    "image": "ipfs://bafkreibdi6623n3xpf7ymk62ckb4bo75o3qemwkpfvp5i25j66itxvsoei",
    "agent_type": "security",
    "capabilities": [
        "token_scam_detection",
        "rugpull_analysis",
        "honeypot_detection",
        "multi_chain_support"
    ],
    "version": "1.0.0",
    "created_by": "Leonis Forge (leonisforge.com)",
    "model": "scam_detector_v3.onnx",
    "supported_chains": ["ethereum", "bsc", "base", "arbitrum", "polygon"],
}

METADATA_URI = "data:application/json," + __import__("json").dumps(AGENT_METADATA)


def register_agent():
    w3 = init_web3()
    account = get_account(w3)
    
    print(f"🔗 Arc Testnet | Chain ID: {w3.eth.chain_id}")
    print(f"📋 Identity Registry: {IDENTITY_REGISTRY}")
    log_balance(w3, account)
    print()

    # ── Register ──────────────────────────────────────────
    contract = get_identity_registry(w3)
    
    print(f"🤖 Registering agent: {AGENT_METADATA['name']}")
    print(f"   Type: {AGENT_METADATA['agent_type']}")
    print(f"   Capabilities: {', '.join(AGENT_METADATA['capabilities'])}")
    print(f"   Metadata URI: {METADATA_URI[:80]}...")
    print()

    try:
        receipt = send_tx(w3, account, contract.functions.register(METADATA_URI))
        print(f"✅ Registered! TX: https://testnet.arcscan.app/tx/{receipt.transactionHash.hex()}")

        # ── Extract Agent ID from event ───────────────────
        agent_id = None
        for log in receipt.logs:
            try:
                decoded = contract.events.AgentRegistered().process_log(log)
                agent_id = decoded.args.agentId
                print(f"🆔 Agent ID: {agent_id}")
                break
            except Exception:
                pass
        
        if not agent_id:
            # Try getAgentId fallback
            try:
                agent_id = contract.functions.getAgentId(account.address).call()
                print(f"🆔 Agent ID (fallback): {agent_id}")
            except Exception:
                print("⚠️ Could not extract agent ID from receipt. Check explorer.")

        print()
        print("=" * 55)
        print("Next steps:")
        print("  1. Save your Agent ID for job creation")
        print("  2. Run: python3 create_job.py")
        print("=" * 55)

    except Exception as e:
        print(f"❌ Registration failed: {e}")
        print()
        print("Troubleshooting:")
        print("  - Do you have enough USDC for gas? Get it: https://faucet.circle.com")
        print("  - Is PRIVATE_KEY set correctly in .env?")
        print("  - Is the Identity Registry address correct on Arc Testnet?")
        raise


if __name__ == "__main__":
    register_agent()
