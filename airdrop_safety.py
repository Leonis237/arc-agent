#!/usr/bin/env python3
"""
airdrop_safety.py — Arc Airdrop Safety Agent.
Analyzes airdrop claim links for phishing, wallet drainers, and scam patterns.

Checks:
  1. URL Structure — suspicious TLDs, shorteners, typosquatting, IPFS links
  2. Domain Heuristics — homoglyphs, brand-impersonation, punycode
  3. Contract Extraction — find 0x address in URL, run contract audit on Arc
  4. Combined Safety Score — weighted scoring with clear verdict

Score: 100 = completely safe link, 0 = confirmed phishing/drainer
"""
import re
from datetime import datetime, timezone
from urllib.parse import urlparse


# ── Suspicious TLDs commonly used for phishing ──
SUSPICIOUS_TLDS = {
    ".xyz", ".top", ".tk", ".ml", ".cf", ".ga", ".gq",
    ".cc", ".pw", ".club", ".work", ".click", ".link",
    ".site", ".online", ".fun", ".space", ".tech",
}

# ── URL shorteners (obscure destination) ──
URL_SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "ow.ly", "buff.ly",
    "shorturl.at", "rb.gy", "cutt.ly", "is.gd", "shorte.st",
}

# ── Patterns for typosquatting detection ──
TYPO_PATTERNS = [
    ("uniswap", ["unisvvap", "uniswaap", "unlswap", "un1swap"]),
    ("metamask", ["metamasl", "metamaskk", "metamaskk", "rnetamask"]),
    ("pancakeswap", ["pancakesvvap", "pancakeeswap"]),
    ("opensea", ["0pensea"]),
    ("aave", ["aave"]),
    ("curve", ["cur\/e"]),
    ("circle", ["circl", "c1rcle", "circie"]),
    ("arc.network", ["arc.netvvork", "arc-netvvork", "arc-network"]),
    ("sushi", ["sushl"]),
]

# ── Suspicious path keywords ──
SUSPICIOUS_PATH_WORDS = [
    "claim", "free", "reward", "giveaway", "bonus",
    "exclusive", "urgent", "verify", "restore", "migrate",
    "airdrop", "drop", "whitelist", "presale", "allocation",
]

# ── Known phishing domains (expandable) ──
KNOWN_PHISHING = [
    "claim-uniswap.org",
    "uniswap-airdrop.xyz",
    "metamask-verify.com",
    "walletconnect-sync.xyz",
    "opensea-claim.com",
    "pancakeswap-airdrop.fun",
    "token-airdrop.xyz",
    "free-claim.xyz",
    "airdrop-reward.xyz",
]


def analyze_airdrop(url: str, w3=None) -> dict:
    """
    Analyze an airdrop claim link for safety.

    Args:
        url: The airdrop/claim URL to analyze
        w3: Optional Web3 instance for contract audit (if contract found in URL)

    Returns: dict with {url, score, verdict, checks, extracted_contract, timestamp}
    """
    url = url.strip()
    # Normalize: add https:// if missing
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    report = {
        "url": url,
        "score": 100,
        "verdict": "SAFE",
        "checks": [],
        "extracted_contract": None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        parsed = urlparse(url)
    except Exception:
        report["checks"].append({
            "name": "URL Parse",
            "status": "FAIL",
            "detail": "Could not parse URL — malformed.",
            "penalty": 100,
        })
        report["score"] = 0
        report["verdict"] = "INVALID_URL"
        return report

    hostname = parsed.hostname or ""
    path = parsed.path or ""

    # ── Check 1: https enforcement ──
    https_check = _check_https(parsed)
    report["checks"].append(https_check)
    report["score"] -= https_check.get("penalty", 0)

    # ── Check 2: TLD reputation ──
    tld_check = _check_tld(hostname)
    report["checks"].append(tld_check)
    report["score"] -= tld_check.get("penalty", 0)

    # ── Check 3: URL shortener ──
    shortener_check = _check_shortener(hostname)
    report["checks"].append(shortener_check)
    report["score"] -= shortener_check.get("penalty", 0)

    # ── Check 4: Typosquatting ──
    typo_check = _check_typosquatting(hostname)
    report["checks"].append(typo_check)
    report["score"] -= typo_check.get("penalty", 0)

    # ── Check 5: Domain heuristics ──
    domain_check = _check_domain_heuristics(hostname)
    report["checks"].append(domain_check)
    report["score"] -= domain_check.get("penalty", 0)

    # ── Check 6: Suspicious path keywords ──
    path_check = _check_path_keywords(path)
    report["checks"].append(path_check)
    report["score"] -= path_check.get("penalty", 0)

    # ── Check 7: IPFS / non-standard links ──
    ipfs_check = _check_ipfs_links(hostname)
    report["checks"].append(ipfs_check)
    report["score"] -= ipfs_check.get("penalty", 0)

    # ── Check 8: Known phishing domain ──
    known_check = _check_known_phishing(hostname)
    report["checks"].append(known_check)
    report["score"] -= known_check.get("penalty", 0)

    # ── Check 9: Contract extraction + Arc audit (bonus) ──
    contract_check = _extract_and_audit_contract(url, w3)
    report["checks"].append(contract_check)
    penalty = contract_check.get("penalty", 0)
    # If we found a contract and it scores poorly, that's a strong negative signal
    # If we found a contract and it scores well, reduce some risk
    if contract_check.get("contract_found"):
        # The contract audit score is scaled: bad contract = up to 40 penalty
        report["score"] -= penalty
        report["extracted_contract"] = contract_check.get("contract_address")

    # Clamp
    report["score"] = max(0, min(100, round(report["score"])))

    # Verdict
    s = report["score"]
    if s >= 80:
        report["verdict"] = "SAFE"
    elif s >= 60:
        report["verdict"] = "LIKELY_SAFE"
    elif s >= 40:
        report["verdict"] = "SUSPICIOUS"
    elif s >= 20:
        report["verdict"] = "HIGH_RISK"
    else:
        report["verdict"] = "CONFIRMED_SCAM"

    return report


def _check_https(parsed) -> dict:
    check = {"name": "HTTPS", "status": "PASS", "detail": "", "penalty": 0}
    if parsed.scheme and parsed.scheme not in ("https",):
        check["status"] = "FAIL"
        check["penalty"] = 25
        check["detail"] = "⚠️ Not using HTTPS — connection is not encrypted."
    else:
        check["detail"] = "Secure connection (HTTPS)."
    return check


def _check_tld(hostname: str) -> dict:
    check = {"name": "TLD Reputation", "status": "PASS", "detail": "", "penalty": 0}
    if not hostname:
        return check

    suspicious = []
    for tld in SUSPICIOUS_TLDS:
        if hostname.endswith(tld) or f".{tld}" in hostname:
            suspicious.append(tld)

    if suspicious:
        check["status"] = "WARN"
        check["penalty"] = 15
        check["detail"] = f"⚠️ Suspicious TLD(s): {', '.join(suspicious)}. Common in phishing."
    else:
        check["detail"] = "TLD not flagged."
    return check


def _check_shortener(hostname: str) -> dict:
    check = {"name": "URL Shortener", "status": "PASS", "detail": "", "penalty": 0}
    host_lower = hostname.lower()
    for shortener in URL_SHORTENERS:
        if shortener in host_lower:
            check["status"] = "WARN"
            check["penalty"] = 10
            check["detail"] = f"⚠️ URL shortener ({shortener}) — destination is obscured."
            return check
    check["detail"] = "Direct URL (no shortener)."
    return check


def _check_typosquatting(hostname: str) -> dict:
    check = {"name": "Brand Impersonation", "status": "PASS", "detail": "", "penalty": 0}
    parts = hostname.lower().split(".")

    # Check if domain contains a brand name but isn't the official domain
    official_domains = {
        "uniswap": "uniswap.org",
        "metamask": "metamask.io",
        "opensea": "opensea.io",
        "aave": "aave.com",
        "circle": "circle.com",
        "pancakeswap": "pancakeswap.finance",
        "sushi": "sushi.com",
        "curve": "curve.fi",
    }

    # Suspicious prefixes/suffixes commonly paired with brand names in phishing
    SUSPICIOUS_AFFIXES = [
        "claim", "free", "airdrop", "reward", "bonus",
        "verify", "secure", "official", "giveaway", "migrate",
        "restore", "connect", "sync", "wallet",
    ]

    issues = []
    total_penalty = 0

    # Build full hostname string
    host_str = ".".join(parts)

    # Check TLD impersonation: uniswap.xyz, uniswap.top, etc.
    for brand, official in official_domains.items():
        # Check if hostname is the official domain or a subdomain of it
        if host_str == official or host_str.endswith("." + official):
            continue  # It's the real thing or a subdomain

        # Check if brand name appears as an exact domain component
        if any(p == brand for p in parts):
            issues.append(f"{brand} impersonation (not {official})")
            total_penalty = 25
            break

        # Check if brand name appears as substring within a domain part
        # (e.g., "claim-uniswap.xyz" → "uniswap" inside "claim-uniswap")
        # Only flag if paired with a suspicious affix (claim-, free-, -airdrop, etc.)
        # to avoid false positives on legit community sites like myuniswapblog.com
        for p in parts:
            if brand in p and p != brand:
                # Detect suspicious prefix/suffix around the brand
                affix_found = []
                for affix in SUSPICIOUS_AFFIXES:
                    if p.startswith(affix + "-") or p.startswith(affix):
                        affix_found.append(f"'{affix}-' prefix")
                    if p.endswith("-" + affix) or p.endswith(affix):
                        affix_found.append(f"'-{affix}' suffix")

                if affix_found:
                    issues.append(
                        f"{brand} in '{p}' with {', '.join(affix_found[:2])} "
                        f"(not {official})"
                    )
                    total_penalty = 20
                    break
                # No suspicious affix — skip (could be legit community site)
                break
        if total_penalty > 0:
            break

    # Check for homoglyphs / typosquatting via character patterns
    if not issues:
        for brand, typos in TYPO_PATTERNS:
            for typo_variant in typos:
                if typo_variant in hostname.lower():
                    issues.append(f"typosquatting: looks like '{brand}'")
                    total_penalty = 25
                    break
            if total_penalty > 0:
                break

    if issues:
        check["status"] = "FAIL" if total_penalty >= 20 else "WARN"
        check["penalty"] = total_penalty
        check["detail"] = "🚨 " + "; ".join(issues) + "."
    else:
        check["detail"] = "No brand impersonation detected."
    return check


def _check_domain_heuristics(hostname: str) -> dict:
    check = {"name": "Domain Patterns", "status": "PASS", "detail": "", "penalty": 0}
    issues = []

    # Long domains
    if len(hostname) > 40:
        issues.append(f"unusually long ({len(hostname)} chars)")
        check["penalty"] += 5

    # Many hyphens
    hyphen_count = hostname.count("-")
    if hyphen_count >= 3:
        issues.append(f"{hyphen_count} hyphens (looks auto-generated)")
        check["penalty"] += 5

    # Many digits in domain
    digit_count = sum(1 for c in hostname if c.isdigit())
    if digit_count > 5:
        issues.append(f"{digit_count} digits")
        check["penalty"] += 3

    # Check for punycode (xn-- prefix = internationalized domain, often abused)
    if "xn--" in hostname.lower():
        issues.append("punycode domain (homoglyph risk)")
        check["penalty"] += 20

    # Subdomain depth (excessive subdomains)
    parts = hostname.split(".")
    if len(parts) > 4:
        issues.append(f"deep subdomain nesting ({len(parts)} levels)")
        check["penalty"] += 5

    if issues:
        check["status"] = "WARN" if check["penalty"] < 10 else "FAIL"
        check["detail"] = "⚠️ " + "; ".join(issues) + "."
    else:
        check["detail"] = "Domain structure looks normal."
    return check


def _check_path_keywords(path: str) -> dict:
    check = {"name": "Path Keywords", "status": "PASS", "detail": "", "penalty": 0}
    if not path or path == "/":
        check["detail"] = "Clean path (no suspicious keywords)."
        return check

    path_lower = path.lower()
    found = [w for w in SUSPICIOUS_PATH_WORDS if w in path_lower]

    if found:
        # Individual keywords are minor, but many together = strong signal
        score = min(3 * len(found), 15)
        check["penalty"] = score
        check["detail"] = f"⚠️ Contains {len(found)} suspicious keyword(s): {', '.join(found[:5])}."
        check["status"] = "WARN" if score < 8 else "FAIL"
    else:
        check["detail"] = "No suspicious keywords in path."
    return check


def _check_ipfs_links(hostname: str) -> dict:
    check = {"name": "Direct/P2P Link", "status": "PASS", "detail": "", "penalty": 0}
    host_lower = hostname.lower()

    ipfs_patterns = ["ipfs.", "ipns.", ".infura-ipfs", "gateway.ipfs", "gateway.pinata"]
    if any(p in host_lower for p in ipfs_patterns):
        check["status"] = "WARN"
        check["penalty"] = 10
        check["detail"] = "⚠️ IPFS/IPNS link — content can be changed or contain malicious scripts."
        return check

    if host_lower.endswith(".eth"):
        check["status"] = "WARN"
        check["penalty"] = 5
        check["detail"] = "⚠️ .eth domain — DNS resolution handled differently, harder to verify."
        return check

    check["detail"] = "Standard web URL."
    return check


def _check_known_phishing(hostname: str) -> dict:
    check = {"name": "Known Phishing", "status": "PASS", "detail": "", "penalty": 0}
    host_lower = hostname.lower()

    for known in KNOWN_PHISHING:
        if host_lower == known or host_lower.endswith("." + known):
            check["status"] = "FAIL"
            check["penalty"] = 50
            check["detail"] = f"🚨 Matches known phishing domain: {known}."
            return check

    check["detail"] = "Not in known phishing database."
    return check


def _extract_and_audit_contract(url: str, w3) -> dict:
    """Extract 0x address from URL and run Arc contract audit."""
    check = {
        "name": "Contract Audit (Arc)",
        "status": "INFO",
        "detail": "",
        "penalty": 0,
        "contract_found": False,
        "contract_address": None,
    }

    # Extract all 0x addresses from URL
    matches = re.findall(r"0x[a-fA-F0-9]{40}", url)
    if not matches:
        check["detail"] = "No contract address found in URL — skipped."
        return check

    # Take the first one
    contract_addr = matches[0]
    check["contract_found"] = True
    check["contract_address"] = contract_addr

    if w3 is None:
        check["detail"] = f"Found 0x...{contract_addr[-6:]} but no Web3 connection to audit."
        return check

    # Run contract audit
    try:
        from contract_audit import audit_contract
        audit_result = audit_contract(w3, contract_addr)

        audit_score = audit_result["score"]
        # Scale: a perfect audit (100) = 0 penalty, a terrible audit (0) = 40 penalty
        # This makes contract audit a significant but not dominant signal
        penalty = round((100 - audit_score) * 0.4)
        check["penalty"] = max(0, min(40, penalty))

        verdict = audit_result["verdict"]
        check["detail"] = (
            f"Contract {contract_addr[:10]}...{contract_addr[-6:]} found. "
            f"Arc audit: {audit_score}/100 ({verdict}). "
            f"Penalty: -{check['penalty']}."
        )

        if audit_score < 40:
            check["status"] = "FAIL"
        elif audit_score < 70:
            check["status"] = "WARN"
        else:
            check["status"] = "PASS"
    except Exception as e:
        check["detail"] = f"Contract found but audit failed: {str(e)[:100]}"
        check["status"] = "UNKNOWN"

    return check


def format_report(report: dict) -> str:
    """Format airdrop safety report as human-readable text."""
    lines = [
        f"🪂 Airdrop Safety Analysis",
        f"URL: {report['url']}",
        f"Score: {report['score']}/100 → {report['verdict']}",
    ]
    if report.get("extracted_contract"):
        lines.append(f"Contract: {report['extracted_contract']}")

    lines.extend(["", "Checks:"])

    for c in report["checks"]:
        icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "🚨", "INFO": "ℹ️", "UNKNOWN": "❓"}.get(
            c.get("status", "UNKNOWN"), "❓"
        )
        lines.append(f"  {icon} {c['name']}: {c.get('detail', '')}")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    test_urls = [
        "https://claim-uniswap.xyz/airdrop",
        "https://app.uniswap.org/swap",
        "https://bit.ly/3abc123",
        "https://ipfs.io/ipfs/QmXoyp...",
        "https://metamask-verify.com/restore",
    ]

    for u in test_urls:
        print("=" * 60)
        print(f"Testing: {u}")
        r = analyze_airdrop(u)
        print(format_report(r))
        print()
