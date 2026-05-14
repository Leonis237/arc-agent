"""
Arc Agent Framework — Shared utilities.
Interact with ERC-8004 and ERC-8183 contracts on Arc Testnet using web3.py.
"""
import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

load_dotenv(Path(__file__).parent / ".env", override=False)

# ── Arc Testnet ──────────────────────────────────────────────
CHAIN_ID = int(os.getenv("ARC_CHAIN_ID", 5042002))
RPC_URL  = os.getenv("ARC_RPC_URL", "https://rpc.testnet.arc.network")

# ── Contract Addresses ───────────────────────────────────────
IDENTITY_REGISTRY   = os.getenv("IDENTITY_REGISTRY", "0x8004A818BFB912233c491871b3d84c89A494BD9e")
VALIDATOR_REGISTRY  = os.getenv("VALIDATOR_REGISTRY", "0x8004B663056A597Dffe9eCcC1965A193B7388713")
REPUTATION_REGISTRY = os.getenv("REPUTATION_REGISTRY", "0x8004Cb1BF31DAf7788923b405b754f57acEB4272")
AGENTIC_COMMERCE    = os.getenv("AGENTIC_COMMERCE", "0x0747EEf0706327138c69792bF28Cd525089e4583")
USDC_TOKEN          = os.getenv("USDC_TOKEN", "0x3600000000000000000000000000000000000000")

# ── Wallet ───────────────────────────────────────────────────
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

# ── Minimal ABIs (function signatures from Arc docs) ─────────
IDENTITY_REGISTRY_ABI = [
    {
        "inputs": [{"internalType": "string", "name": "metadataURI", "type": "string"}],
        "name": "register",
        "outputs": [{"internalType": "uint256", "name": "agentId", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "owner", "type": "address"}],
        "name": "getAgentId",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "agentId", "type": "uint256"},
            {"indexed": True, "internalType": "address", "name": "owner", "type": "address"},
            {"indexed": False, "internalType": "string", "name": "metadataURI", "type": "string"},
        ],
        "name": "AgentRegistered",
        "type": "event",
    },
]

AGENTIC_COMMERCE_ABI = [
    # ── createJob ────────────────────────────────────────────
    {
        "inputs": [
            {"internalType": "address", "name": "provider", "type": "address"},
            {"internalType": "address", "name": "evaluator", "type": "address"},
            {"internalType": "uint256", "name": "expiredAt", "type": "uint256"},
            {"internalType": "string", "name": "description", "type": "string"},
            {"internalType": "address", "name": "hook", "type": "address"},
        ],
        "name": "createJob",
        "outputs": [{"internalType": "uint256", "name": "jobId", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    # ── setBudget ─────────────────────────────────────────────
    {
        "inputs": [
            {"internalType": "uint256", "name": "jobId", "type": "uint256"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
            {"internalType": "bytes", "name": "optParams", "type": "bytes"},
        ],
        "name": "setBudget",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    # ── fund ──────────────────────────────────────────────────
    {
        "inputs": [
            {"internalType": "uint256", "name": "jobId", "type": "uint256"},
            {"internalType": "bytes", "name": "optParams", "type": "bytes"},
        ],
        "name": "fund",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    # ── jobs (view) ───────────────────────────────────────────
    # Returns: (jobId, client, provider, evaluator, description, budget, expiredAt, state, hook)
    {
        "inputs": [{"internalType": "uint256", "name": "jobId", "type": "uint256"}],
        "name": "jobs",
        "outputs": [
            {"internalType": "uint256", "name": "jobId", "type": "uint256"},
            {"internalType": "address", "name": "client", "type": "address"},
            {"internalType": "address", "name": "provider", "type": "address"},
            {"internalType": "address", "name": "evaluator", "type": "address"},
            {"internalType": "string", "name": "description", "type": "string"},
            {"internalType": "uint256", "name": "budget", "type": "uint256"},
            {"internalType": "uint256", "name": "expiredAt", "type": "uint256"},
            {"internalType": "uint8", "name": "state", "type": "uint8"},
            {"internalType": "address", "name": "hook", "type": "address"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    # ── submit (not submitDeliverable!) ───────────────────────
    {
        "inputs": [
            {"internalType": "uint256", "name": "jobId", "type": "uint256"},
            {"internalType": "bytes32", "name": "deliverableHash", "type": "bytes32"},
            {"internalType": "bytes", "name": "optParams", "type": "bytes"},
        ],
        "name": "submit",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    # ── complete (not completeJob!) ───────────────────────────
    {
        "inputs": [
            {"internalType": "uint256", "name": "jobId", "type": "uint256"},
            {"internalType": "bytes32", "name": "deliverableHash", "type": "bytes32"},
            {"internalType": "bytes", "name": "optParams", "type": "bytes"},
        ],
        "name": "complete",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    # ── jobCounter (view) ──────────────────────────────────────
    {
        "inputs": [],
        "name": "jobCounter",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    # ── JobCreated event (actual signature from deployed contract) ──
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "jobId", "type": "uint256"},
            {"indexed": True, "internalType": "address", "name": "client", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "provider", "type": "address"},
            {"indexed": False, "internalType": "address", "name": "evaluator", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "expiredAt", "type": "uint256"},
            {"indexed": False, "internalType": "address", "name": "hook", "type": "address"},
        ],
        "name": "JobCreated",
        "type": "event",
    },
]

USDC_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "spender", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
        ],
        "name": "approve",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
]

# Job states (from ERC-8183)
JOB_STATES = {
    0: "NONEXISTENT",
    1: "OPEN",
    2: "FUNDED",
    3: "IN_PROGRESS",
    4: "DELIVERED",
    5: "COMPLETED",
    6: "CANCELLED",
}


def init_web3() -> Web3:
    """Initialize web3 connection to Arc Testnet."""
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    if not w3.is_connected():
        raise ConnectionError(f"Cannot connect to Arc RPC: {RPC_URL}")
    return w3


def get_account(w3: Web3):
    """Derive account from private key."""
    if not PRIVATE_KEY or PRIVATE_KEY == "your_private_key_here":
        raise ValueError(
            "PRIVATE_KEY not set. Copy .env.example to .env and set your key.\n"
            "Get testnet USDC: https://faucet.circle.com"
        )
    return w3.eth.account.from_key(PRIVATE_KEY)


def get_identity_registry(w3: Web3):
    return w3.eth.contract(address=IDENTITY_REGISTRY, abi=IDENTITY_REGISTRY_ABI)


def get_agentic_commerce(w3: Web3):
    return w3.eth.contract(address=AGENTIC_COMMERCE, abi=AGENTIC_COMMERCE_ABI)


def get_usdc(w3: Web3):
    return w3.eth.contract(address=USDC_TOKEN, abi=USDC_ABI)


def send_tx(w3: Web3, account, tx_fn, gas_multiplier=1.2):
    """Build, sign, and send a transaction. Wait for receipt."""
    tx = tx_fn.build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "chainId": CHAIN_ID,
    })
    # Gas estimation on Arc
    try:
        tx["gas"] = int(tx_fn.estimate_gas({"from": account.address}) * gas_multiplier)
    except Exception:
        tx["gas"] = 500_000  # fallback for complex calls

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    return receipt


def log_balance(w3: Web3, account):
    """Print USDC balance."""
    try:
        usdc = get_usdc(w3)
        balance = usdc.functions.balanceOf(account.address).call()
        decimals = usdc.functions.decimals().call()
        print(f"  💰 Balance: {balance / 10**decimals:.2f} USDC  ({account.address})")
    except Exception as e:
        print(f"  ⚠️ Could not read balance: {e}")
