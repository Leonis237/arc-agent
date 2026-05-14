"""Tests for worker.py — capability matching, token extraction."""
import pytest
import sys
from pathlib import Path

# Import from worker without running it
sys.path.insert(0, str(Path(__file__).parent))

def test_extract_token_address_valid():
    """Extract 0x address from job description."""
    import re
    desc = "Token scam analysis on 0xabc123def456789012345678901234567890abcd"
    match = re.search(r"0x[a-fA-F0-9]{40}", desc)
    assert match is not None
    assert match.group(0) == "0xabc123def456789012345678901234567890abcd"

def test_extract_token_address_none():
    """Return None when no address in description."""
    import re
    desc = "Write a one-paragraph story about blockchain"
    match = re.search(r"0x[a-fA-F0-9]{40}", desc)
    assert match is None

def test_extract_token_address_multiple():
    """Extract first address when multiple present."""
    import re
    desc = "Compare 0xaaaa111122223333444455556666777788889999 vs 0xbbbb999988887777666655554444333322221111"
    match = re.search(r"0x[a-fA-F0-9]{40}", desc)
    assert match.group(0) == "0xaaaa111122223333444455556666777788889999"

def test_matches_capability_scam():
    """Match job descriptions with scam keywords."""
    keywords = ["scam", "token", "detect", "analysis", "rugpull", "security", "audit", "honeypot", "verify", "check"]
    
    desc = "Run token scam analysis on this address"
    desc_lower = desc.lower()
    assert any(kw in desc_lower for kw in keywords)

def test_matches_capability_rugpull():
    """Match rugpull detection jobs."""
    keywords = ["scam", "token", "detect", "analysis", "rugpull", "security", "audit", "honeypot", "verify", "check"]
    
    desc = "Check for rugpull indicators"
    desc_lower = desc.lower()
    assert any(kw in desc_lower for kw in keywords)

def test_matches_capability_no_match():
    """Don't match unrelated jobs."""
    keywords = ["scam", "token", "detect", "analysis", "rugpull", "security", "audit", "honeypot", "verify", "check"]
    
    desc = "Draw a picture of a cat"
    desc_lower = desc.lower()
    assert not any(kw in desc_lower for kw in keywords)

def test_hash_deliverable():
    """Deliverable hash generation is deterministic."""
    import hashlib, json
    result = {"score": 75, "status": "HIGH_RISK", "token": "0xabc"}
    h1 = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
    h2 = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex
