#!/usr/bin/env python3
"""
contract_audit.py — Arc Contract Transparency Audit Agent.
Analyzes token contracts on Arc for transparency, owner risk, and hidden traps.

Checks:
  1. Owner Privileges — dangerous functions (mint, pause, tax, blacklist)
  2. Ownership Status — renounced vs active owner
  3. Supply Concentration — owner/deployer share of total supply
  4. Proxy Risk — upgradeable proxy patterns
  5. Deployer History — how many contracts from this deployer
  6. Liquidity Traps — maxTx, tax settings, exclude lists

Score: 100 = fully transparent/renounced, 0 = dangerous centralized control
"""
import json
from datetime import datetime, timezone
try:
    from web3 import Web3
except ImportError:
    pass


# ── Dangerous function signature hashes (keccak first 4 bytes) ──

DANGEROUS_SIGS = {
    "mint": [
        "40c10f19",  # mint(address,uint256)
        "a0712d68",  # mint(uint256)
        "449a52f8",  # mint(address,uint256)
    ],
    "burn": [
        "42966c68",  # burn(uint256)
        "9dc29fac",  # burn(address,uint256)
    ],
    "pause": [
        "8456cb59",  # pause()
        "3f4ba83a",  # unpause()
    ],
    "blacklist": [
        "f9f92be4",  # setBlacklist(address,bool)
        "f8210073",  # addBlackList(address)
        "ec211840",  # removeBlackList(address)
        "d01dd6f4",  # blacklist(address)
    ],
    "tax": [
        "c2b7bbb1",  # setTaxFeePercent(uint256)
        "adc82ce6",  # setSellTax(uint256)
        "0603c4ea",  # setBuyTax(uint256)
        "89c1a76e",  # setFee(uint256)
    ],
    "transfer_restrict": [
        "a2e6f807",  # setMaxTxAmount(uint256)
        "3c84b7c2",  # excludeFromFee(address)
        "3b6d0a2c",  # includeInFee(address)
        "f8437a5a",  # setMaxWallet(uint256)
        "a10f5848",  # enableTrading()
        "1a2d80d3",  # setSwapEnabled(bool)
    ],
    "owner_restricted": [
        "b95459e4",  # setAutomatedMarketMakerPair(address,bool)
        "2d061b10",  # excludeFromMaxTransaction(address,bool)
        "a5f7f466",  # setSwapAndLiquifyEnabled(bool)
    ],
}

# ── Proxy bytecode signatures ──

PROXY_SLOTS = [
    "360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc",  # EIP-1967 implementation
    "b53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103",  # EIP-1967 admin
    "7050c9e0f4ca769c69bd3a8ef740bc37934f8e2c036e5a723fd8ee048ed3f8c3",  # beacon
]

TRUSTED_CONTRACTS = {
    "0x3600000000000000000000000000000000000000",  # USDC
    "0x0747EEf0706327138c69792bF28Cd525089e4583",  # AgenticCommerce
    "0x8004A818BFB912233c491871b3d84c89A494BD9e",  # Identity Registry
}

MINIMAL_ERC20_ABI = [
    {"inputs": [], "name": "totalSupply", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "decimals", "outputs": [{"type": "uint8"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "symbol", "outputs": [{"type": "string"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "name", "outputs": [{"type": "string"}], "stateMutability": "view", "type": "function"},
    {"inputs": [{"type": "address"}], "name": "balanceOf", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
    {"inputs": [], "name": "owner", "outputs": [{"type": "address"}], "stateMutability": "view", "type": "function"},
]


def audit_contract(w3, contract_address: str, deployer: str = None) -> dict:
    """
    Run full contract transparency audit.

    Args:
        w3: Initialized Web3 instance
        contract_address: Token contract address to audit
        deployer: Optional deployer address (if known, for history check)

    Returns: dict with {address, name, symbol, score, verdict, checks, timestamp}
    """
    addr = w3.to_checksum_address(contract_address.lower())
    report = {
        "address": addr,
        "name": "",
        "symbol": "",
        "score": 100,
        "verdict": "TRANSPARENT",
        "checks": [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if addr in TRUSTED_CONTRACTS:
        report["name"] = "Trusted Arc Contract"
        report["symbol"] = "ARC"
        report["score"] = 100
        report["verdict"] = "TRANSPARENT"
        report["checks"].append({
            "name": "Trusted",
            "status": "PASS",
            "detail": "Verified Arc core contract — fully trusted.",
            "penalty": 0,
        })
        return report

    # Get bytecode
    try:
        code = w3.eth.get_code(addr)
        code_hex = code.hex() if code and code != b"" else ""
    except Exception:
        code_hex = ""

    if not code_hex:
        report["score"] = 0
        report["verdict"] = "NOT_A_CONTRACT"
        report["checks"].append({
            "name": "Contract Exists",
            "status": "FAIL",
            "detail": "No contract code at this address — EOA or empty account.",
            "penalty": 100,
        })
        return report

    # Contracts with code exist
    report["checks"].append({
        "name": "Contract Exists",
        "status": "PASS",
        "detail": "Contract bytecode found.",
        "penalty": 0,
    })

    # Try to read ERC-20 metadata
    try:
        token = w3.eth.contract(address=addr, abi=MINIMAL_ERC20_ABI)
        report["name"] = token.functions.name().call()
        report["symbol"] = token.functions.symbol().call()
    except Exception:
        pass

    # ── Check 1: Owner Privileges (bytecode scan) ──
    owner_check = _check_owner_privileges(code_hex)
    report["checks"].append(owner_check)
    report["score"] -= owner_check.get("penalty", 0)

    # ── Check 2: Ownership Status ──
    ownership = _check_ownership(w3, addr)
    report["checks"].append(ownership)
    report["score"] -= ownership.get("penalty", 0)

    # ── Check 3: Supply Concentration ──
    supply = _check_supply(w3, addr, ownership.get("owner_addr"))
    report["checks"].append(supply)
    report["score"] -= supply.get("penalty", 0)

    # ── Check 4: Proxy Risk ──
    proxy = _check_proxy(code_hex)
    report["checks"].append(proxy)
    report["score"] -= proxy.get("penalty", 0)

    # ── Check 5: Deployer History ──
    if deployer:
        deployer_check = _check_deployer(w3, deployer)
    else:
        deployer_check = {
            "name": "Deployer History",
            "status": "UNKNOWN",
            "detail": "No deployer address provided for analysis.",
            "penalty": 0,
        }
    report["checks"].append(deployer_check)
    report["score"] -= deployer_check.get("penalty", 0)

    # ── Check 6: Liquidity Traps ──
    traps = _check_liquidity_traps(code_hex)
    report["checks"].append(traps)
    report["score"] -= traps.get("penalty", 0)

    # Clamp
    report["score"] = max(0, min(100, report["score"]))

    # Verdict
    s = report["score"]
    if s >= 80:
        report["verdict"] = "TRANSPARENT"
    elif s >= 60:
        report["verdict"] = "MOSTLY_TRANSPARENT"
    elif s >= 40:
        report["verdict"] = "MODERATE_RISK"
    elif s >= 20:
        report["verdict"] = "OPAQUE"
    else:
        report["verdict"] = "HIDDEN_DANGER"

    return report


def _check_owner_privileges(code_hex: str) -> dict:
    """Scan bytecode for dangerous function signatures."""
    check = {
        "name": "Owner Privileges",
        "status": "PASS",
        "detail": "",
        "penalty": 0,
    }
    found = {}
    for category, sigs in DANGEROUS_SIGS.items():
        matched = [s for s in sigs if s in code_hex]
        if matched:
            found[category] = len(matched)

    if not found:
        check["detail"] = "No dangerous owner functions detected in bytecode."
        return check

    total_risk = 0
    details = []
    risk_scores = {
        "mint": 15, "pause": 10, "blacklist": 10,
        "tax": 12, "transfer_restrict": 8, "owner_restricted": 5,
    }

    for cat, count in found.items():
        penalty = min(risk_scores.get(cat, 5), 15)
        total_risk += penalty
        details.append(f"{cat}({count})")

    check["status"] = "WARN" if total_risk <= 20 else "FAIL"
    check["penalty"] = min(40, total_risk)
    check["detail"] = f"⚠️ Dangerous functions found: {', '.join(details)}. "
    if "mint" in found:
        check["detail"] += "Owner can create unlimited tokens. "
    if "tax" in found:
        check["detail"] += "Owner can change sell/buy tax. "

    return check


def _check_ownership(w3, addr: str) -> dict:
    """Check if contract has an active owner or is renounced."""
    check = {
        "name": "Ownership Status",
        "status": "PASS",
        "detail": "",
        "penalty": 0,
        "owner_addr": None,
    }
    try:
        token = w3.eth.contract(address=addr, abi=MINIMAL_ERC20_ABI)
        owner = token.functions.owner().call()
        check["owner_addr"] = owner

        if owner == "0x0000000000000000000000000000000000000000":
            check["status"] = "PASS"
            check["detail"] = "✅ Ownership renounced — no central control."
        elif owner == "0x000000000000000000000000000000000000dEaD":
            check["status"] = "PASS"
            check["detail"] = "✅ Ownership sent to dead address — effectively renounced."
        else:
            check["status"] = "WARN"
            check["penalty"] = 15
            check["detail"] = f"⚠️ Active owner: {owner[:10]}...{owner[-6:]}. "
            check["detail"] += "Owner can modify contract (taxes, pause, blacklist)."
    except Exception:
        check["status"] = "UNKNOWN"
        check["detail"] = "No owner() function — contract may use different ownership pattern."

    return check


def _check_supply(w3, addr: str, owner_addr: str = None) -> dict:
    """Check if owner holds a large percentage of total supply."""
    check = {
        "name": "Supply Concentration",
        "status": "PASS",
        "detail": "",
        "penalty": 0,
    }
    try:
        token = w3.eth.contract(address=addr, abi=MINIMAL_ERC20_ABI)
        total = token.functions.totalSupply().call()
        if total == 0:
            check["detail"] = "Total supply is zero — contract may not be initialized."
            check["status"] = "WARN"
            check["penalty"] = 5
            return check

        if owner_addr and owner_addr != "0x0000000000000000000000000000000000000000":
            try:
                owner_bal = token.functions.balanceOf(owner_addr).call()
                pct = (owner_bal / total) * 100
                if pct > 50:
                    check["status"] = "FAIL"
                    check["penalty"] = 20
                    check["detail"] = f"🚨 Owner holds {pct:.0f}% of supply — extreme centralization."
                elif pct > 10:
                    check["status"] = "WARN"
                    check["penalty"] = 10
                    check["detail"] = f"⚠️ Owner holds {pct:.1f}% of supply — significant concentration."
                else:
                    check["detail"] = f"Owner holds {pct:.1f}% of supply — reasonable."
            except Exception:
                check["detail"] = "Could not read owner balance."
        else:
            check["detail"] = "No active owner to check supply against."
    except Exception:
        check["status"] = "UNKNOWN"
        check["detail"] = "Could not read totalSupply() — may not be ERC-20."

    return check


def _check_proxy(code_hex: str) -> dict:
    """Check for upgradeable proxy patterns."""
    check = {
        "name": "Proxy / Upgradeable",
        "status": "PASS",
        "detail": "",
        "penalty": 0,
    }
    is_proxy = any(slot in code_hex for slot in PROXY_SLOTS)

    if is_proxy:
        # Check if delegatecall present (definitive proxy indicator)
        has_delegate = "f4" in code_hex  # DELEGATECALL opcode
        if has_delegate:
            check["status"] = "WARN"
            check["penalty"] = 15
            check["detail"] = "⚠️ Upgradeable proxy detected — implementation can be changed by admin. "
            check["detail"] += "Current logic may differ from deployed code."
        else:
            check["detail"] = "Proxy storage slots detected but no delegatecall — may be false positive."
    else:
        check["detail"] = "Not a proxy — contract logic is fixed."

    return check


def _check_deployer(w3, deployer: str) -> dict:
    """Check deployer wallet history for red flags."""
    check = {
        "name": "Deployer History",
        "status": "PASS",
        "detail": "",
        "penalty": 0,
    }
    addr = w3.to_checksum_address(deployer.lower())
    try:
        nonce = w3.eth.get_transaction_count(addr)
        if nonce == 0:
            check["detail"] = "Deployer has 0 transactions — fresh wallet."
        elif nonce <= 10:
            check["detail"] = f"Deployer has {nonce} transactions — relatively new wallet."
        elif nonce <= 100:
            check["detail"] = f"Deployer has {nonce} transactions — active but not mass deployer."
        else:
            check["status"] = "WARN"
            check["penalty"] = 8
            check["detail"] = f"⚠️ Deployer has {nonce} transactions — high activity, potential mass deployer."
    except Exception:
        check["detail"] = "Could not query deployer transaction count."

    return check


def _check_liquidity_traps(code_hex: str) -> dict:
    """Check for liquidity traps: maxTx, trading toggle, exclude lists."""
    check = {
        "name": "Liquidity Traps",
        "status": "PASS",
        "detail": "",
        "penalty": 0,
    }
    # Check max transaction limit
    has_max_tx = "a2e6f807" in code_hex or "3c84b7c2" in code_hex
    # Check trading enable/disable
    has_trading_toggle = "1a2d80d3" in code_hex or "a10f5848" in code_hex
    # Check exclude from max
    has_exclude = "2d061b10" in code_hex

    issues = []
    if has_max_tx:
        issues.append("maxTx limit (can block large sells)")
    if has_trading_toggle:
        issues.append("trading can be enabled/disabled")
    if has_exclude:
        issues.append("exclude lists (selective restrictions)")

    if issues:
        check["status"] = "WARN"
        check["penalty"] = min(15, 5 * len(issues))
        check["detail"] = "⚠️ " + "; ".join(issues) + "."
    else:
        check["detail"] = "No liquidity trap patterns detected."

    return check


def format_report(report: dict) -> str:
    """Format audit report as human-readable text."""
    lines = [
        f"🔍 Contract Transparency Audit",
        f"Address: {report['address']}",
        f"Name: {report['name'] or 'Unknown'} ({report['symbol'] or '?'})",
        f"Score: {report['score']}/100 → {report['verdict']}",
        "",
        "Checks:",
    ]
    for c in report["checks"]:
        icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "🚨", "UNKNOWN": "❓"}.get(
            c.get("status", "UNKNOWN"), "❓"
        )
        lines.append(f"  {icon} {c['name']}: {c.get('detail', '')}")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    from pathlib import Path
    from arc_utils import init_web3

    w3 = init_web3()

    # Test with USDC (trusted) and a random address
    usdc = "0x3600000000000000000000000000000000000000"
    print("=" * 60)
    print("Testing: USDC (trusted Arc contract)")
    r = audit_contract(w3, usdc)
    print(format_report(r))

    print("\n" + "=" * 60)
    print("Testing: Agent wallet (EOA)")
    eoa = "0xe43f191d3DBcCEBd94F960a42dEafdF8E57215BB"
    r2 = audit_contract(w3, eoa)
    print(format_report(r2))
