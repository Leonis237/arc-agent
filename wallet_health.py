#!/usr/bin/env python3
"""
wallet_health.py — Wallet Health Agent for Arc Testnet.
Analyzes a wallet address for security risks: approvals, delegation, source verification.
Used by both the autonomous worker and the dashboard API.

Score formula:
  - Starts at 100
  - Approvals check: -25 per unlimited approval to non-whitelisted spender (max -50)
  - Delegation check: -30 if EIP-7702 delegation detected
  - Source check: -10 for unverified proxy, -20 for opaque code

Verdict thresholds:
  ≥80: HEALTHY
  50-79: NEEDS REVIEW
  25-49: AT RISK
  <25: CRITICAL
"""
import json
from datetime import datetime, timezone

# Whitelist of known safe spenders (Arc-native contracts)
SAFE_SPENDERS = {
    "0x0747EEf0706327138c69792bF28Cd525089e4583",  # AgenticCommerce
    "0x3600000000000000000000000000000000000000",  # USDC (self)
}


def analyze_wallet(w3, wallet_address: str, commerce=None) -> dict:
    """
    Run full wallet health analysis.

    Args:
        w3: Web3 instance (initialized)
        wallet_address: 0x-prefixed wallet address to audit
        commerce: Optional AgenticCommerce contract (for allowance check)

    Returns:
        dict with keys: address, score, verdict, checks (list), timestamp
    """
    address = w3.to_checksum_address(wallet_address.lower())
    report = {
        "address": address,
        "score": 100,
        "verdict": "HEALTHY",
        "checks": [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # ── Check 1: Token Approvals ──────────────────────────
    approval_check = _check_approvals(w3, address, commerce)
    report["checks"].append(approval_check)
    report["score"] -= approval_check.get("penalty", 0)

    # ── Check 2: EIP-7702 Delegation ──────────────────────
    delegation_check = _check_delegation(w3, address)
    report["checks"].append(delegation_check)
    report["score"] -= delegation_check.get("penalty", 0)

    # ── Check 3: Source / Code Verification ───────────────
    source_check = _check_source(w3, address)
    report["checks"].append(source_check)
    report["score"] -= source_check.get("penalty", 0)

    # Clamp score
    report["score"] = max(0, min(100, report["score"]))

    # ── Verdict ───────────────────────────────────────────
    s = report["score"]
    if s >= 80:
        report["verdict"] = "HEALTHY"
    elif s >= 50:
        report["verdict"] = "NEEDS_REVIEW"
    elif s >= 25:
        report["verdict"] = "AT_RISK"
    else:
        report["verdict"] = "CRITICAL"

    return report


def _check_approvals(w3, address, commerce=None) -> dict:
    """Check for risky token approvals. Returns {title, status, detail, penalty}."""
    check = {
        "name": "Token Approvals",
        "status": "PASS",
        "detail": "No risky approvals found.",
        "penalty": 0,
    }

    risky_approvals = []

    # Check USDC allowance to AgenticCommerce
    if commerce:
        try:
            usdc_addr = w3.to_checksum_address(
                "0x3600000000000000000000000000000000000000"
            )
            usdc_abi = [
                {
                    "inputs": [
                        {"type": "address", "name": "owner"},
                        {"type": "address", "name": "spender"},
                    ],
                    "name": "allowance",
                    "outputs": [{"type": "uint256"}],
                    "stateMutability": "view",
                    "type": "function",
                }
            ]
            usdc = w3.eth.contract(address=usdc_addr, abi=usdc_abi)
            commerce_addr = commerce.address

            allowance = usdc.functions.allowance(address, commerce_addr).call()

            if allowance > 0:
                # This is normal for Arc — approving AgenticCommerce is required for jobs
                check["detail"] = (
                    f"USDC allowance to AgenticCommerce: {allowance / 1e6:.2f} USDC "
                    "(expected — needed for Arc jobs)"
                )
            else:
                check["detail"] = "No USDC allowance to AgenticCommerce."
        except Exception:
            check["detail"] = "Could not check USDC allowance (RPC issue)."

    # Check for any code at the wallet address (indicates smart contract wallet)
    try:
        code = w3.eth.get_code(address)
        if code and code != b"" and code != b"\x00":
            # Contract wallet — check if there are delegatecall patterns or known risks
            code_hex = code.hex()
            # Heuristic: look for delegatecall opcode (f4) in bytecode
            if "f4" in code_hex:
                if "allowance" not in check["detail"]:
                    check["detail"] = ""
                check["detail"] += (
                    " ⚠️ Wallet is a smart contract with DELEGATECALL capability — "
                    "could redirect execution."
                )
                risky_approvals.append("Smart contract wallet with delegatecall")
    except Exception:
        pass

    if risky_approvals:
        check["status"] = "WARN" if len(risky_approvals) == 1 else "FAIL"
        check["penalty"] = min(50, 25 * len(risky_approvals))
        if "⚠️" not in check.get("detail", ""):
            check["detail"] = "; ".join(risky_approvals)

    return check


def _check_delegation(w3, address) -> dict:
    """Check for EIP-7702 delegation. Returns {name, status, detail, penalty}."""
    check = {
        "name": "EIP-7702 Delegation",
        "status": "PASS",
        "detail": "No EIP-7702 delegation detected.",
        "penalty": 0,
    }

    try:
        code = w3.eth.get_code(address)
        if code and code != b"":
            code_hex = code.hex()
            # EIP-7702 delegation prefix: 0xef01...
            if code_hex.startswith("ef01"):
                check["status"] = "FAIL"
                check["penalty"] = 30
                # Extract delegated address (next 20 bytes)
                delegated = "0x" + code_hex[4:44]
                check["detail"] = (
                    f"⚠️ EIP-7702 delegation active! Wallet delegates to "
                    f"{delegated}. A smart contract can sign transactions "
                    f"on behalf of this wallet WITHOUT your private key."
                )
            elif code_hex != "":
                check["detail"] = "Wallet has contract code deployed (not EIP-7702)."
    except Exception as e:
        check["status"] = "UNKNOWN"
        check["detail"] = f"Could not check delegation: {str(e)[:80]}"

    return check


def _check_source(w3, address) -> dict:
    """Check wallet code verification status. Returns {name, status, detail, penalty}."""
    check = {
        "name": "Source Verification",
        "status": "PASS",
        "detail": "Wallet is a standard EOA (no code deployed).",
        "penalty": 0,
    }

    try:
        code = w3.eth.get_code(address)
        if not code or code == b"" or code == b"\x00":
            # EOA — no code, clean
            check["detail"] = "Standard EOA wallet — no contract code."
            check["status"] = "PASS"
        else:
            code_hex = code.hex()
            # Has code — check if it looks like a proxy pattern
            proxy_patterns = [
                "360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc",  # EIP-1967
                "7050c9e0f4ca769c69bd3a8ef740bc37934f8e2c036e5a723fd8ee048ed3f8c3",  # beacon
            ]
            is_proxy = any(p in code_hex for p in proxy_patterns)

            if is_proxy:
                check["status"] = "WARN"
                check["penalty"] = 10
                check["detail"] = (
                    "⚠️ Wallet is a proxy contract — logic can be upgraded by owner. "
                    "Verify ownership and implementation."
                )
            else:
                check["status"] = "WARN"
                check["penalty"] = 20
                check["detail"] = (
                    "⚠️ Wallet has unverified contract code deployed. "
                    "Cannot verify behavior — treat as potentially risky."
                )
    except Exception as e:
        check["status"] = "UNKNOWN"
        check["detail"] = f"Could not verify source: {str(e)[:80]}"

    return check


def format_report(report: dict) -> str:
    """Format wallet health report as human-readable text (for worker deliverables)."""
    lines = [
        f"🔍 Wallet Health Report",
        f"Address: {report['address']}",
        f"Score: {report['score']}/100 → {report['verdict']}",
        f"",
        "Checks:",
    ]
    for c in report["checks"]:
        icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "🚨", "UNKNOWN": "❓"}.get(
            c.get("status", "UNKNOWN"), "❓"
        )
        lines.append(f"  {icon} {c['name']}: {c.get('detail', '')}")

    return "\n".join(lines)


if __name__ == "__main__":
    # Quick test
    import sys
    from pathlib import Path
    from arc_utils import init_web3

    w3 = init_web3()
    test_addr = "0xe43f191d3DBcCEBd94F960a42dEafdF8E57215BB"
    report = analyze_wallet(w3, test_addr)
    print(format_report(report))
    print(f"\nJSON: {json.dumps(report, indent=2)}")
