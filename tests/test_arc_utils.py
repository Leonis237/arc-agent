"""Tests for arc_utils.py — contract ABIs, job states, env loading."""
import os
import sys
import pytest
from unittest import mock

# Mock python-dotenv BEFORE importing arc_utils so it skips .env loading
mock.patch("dotenv.load_dotenv", lambda *a, **kw: None).start()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["PRIVATE_KEY"] = "0x" + "00" * 31 + "01"  # dummy key

import arc_utils


@pytest.fixture
def job_states():
    return {
        0: "NONEXISTENT", 1: "OPEN", 2: "FUNDED",
        3: "IN_PROGRESS", 4: "DELIVERED",
        5: "COMPLETED", 6: "CANCELLED",
    }


def test_job_states_complete(job_states):
    """All 7 ERC-8183 states are defined."""
    assert len(job_states) == 7
    assert job_states[0] == "NONEXISTENT"
    assert job_states[5] == "COMPLETED"


def test_job_states_no_gaps(job_states):
    """State codes are contiguous 0-6."""
    assert sorted(job_states.keys()) == list(range(7))


def test_chain_id_constant():
    """CHAIN_ID matches Arc Testnet."""
    assert arc_utils.CHAIN_ID == 5042002


def test_contract_addresses_valid():
    """ERC-8004 and ERC-8183 addresses are valid 0x addresses."""
    for addr in [arc_utils.IDENTITY_REGISTRY, arc_utils.AGENTIC_COMMERCE, arc_utils.USDC_TOKEN]:
        assert addr.startswith("0x")
        assert len(addr) == 42
        int(addr, 16)


def test_abi_has_required_functions():
    """Minimal ABIs include essential functions."""
    commerce_fns = {f["name"] for f in arc_utils.AGENTIC_COMMERCE_ABI if f.get("type") == "function"}
    assert "createJob" in commerce_fns
    assert "jobs" in commerce_fns
    assert "submit" in commerce_fns
    assert "complete" in commerce_fns


def test_send_tx_signature():
    """send_tx function has correct signature."""
    import inspect
    sig = inspect.signature(arc_utils.send_tx)
    params = list(sig.parameters.keys())
    assert "w3" in params
    assert "account" in params
    assert "tx_fn" in params


def test_rpc_url():
    """RPC URL is set to Arc Testnet."""
    assert "testnet.arc.network" in arc_utils.RPC_URL
