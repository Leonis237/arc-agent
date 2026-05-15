"""
Arc Agent Dashboard — Flask webapp for visualizing ERC-8004 agent + ERC-8183 jobs.
"""
import os
import json
import time
from pathlib import Path
from flask import Flask, render_template, jsonify, request

from arc_utils import (
    init_web3, get_account,
    get_identity_registry, get_agentic_commerce, get_usdc,
    send_tx,
    IDENTITY_REGISTRY, AGENTIC_COMMERCE, CHAIN_ID
)

app = Flask(__name__)
w3 = init_web3()
account = get_account(w3)

AGENT_ID = 9138
AGENT_ADDRESS = account.address

# ── Ecosystem cache (avoids expensive RPC on every page load) ──
_ecosystem_cache = {"data": None, "ts": 0}
_ECOSYSTEM_CACHE_TTL = 300  # 5 minutes


def _owner_exists(token_id: int) -> bool:
    """Check if an ERC-8004 agent token exists (ownerOf won't revert)."""
    try:
        c = w3.eth.contract(
            address=IDENTITY_REGISTRY,
            abi=[{"inputs":[{"type":"uint256"}],"name":"ownerOf","outputs":[{"type":"address"}],"stateMutability":"view","type":"function"}]
        )
        c.functions.ownerOf(token_id).call()
        return True
    except Exception:
        return False


def _count_agents() -> int:
    """Binary-search for total registered agents (ERC-8004 tokens)."""
    # Start from a known existing ID and search upward
    lo, hi = 1, 20000
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if _owner_exists(mid):
            lo = mid
        else:
            hi = mid - 1
    return lo


def get_ecosystem_stats():
    """Return live ecosystem stats with 5-min cache."""
    now = time.time()
    if _ecosystem_cache["data"] and (now - _ecosystem_cache["ts"]) < _ECOSYSTEM_CACHE_TTL:
        return _ecosystem_cache["data"]

    try:
        identity = get_identity_registry(w3)
        commerce = get_agentic_commerce(w3)

        total_agents = _count_agents()
        total_jobs = commerce.functions.jobCounter().call()

        stats = {
            "total_agents": total_agents,
            "total_jobs": total_jobs,
            "my_agent_id": AGENT_ID,
            "my_agent_active": True,
        }
    except Exception as e:
        # Fallback: return cached or reasonable defaults
        stats = _ecosystem_cache["data"] or {
            "total_agents": 10360,
            "total_jobs": 13075,
            "my_agent_id": AGENT_ID,
            "my_agent_active": True,
        }
        stats["_cached"] = True
        if not _ecosystem_cache["data"]:
            stats["_error"] = str(e)[:100]

    _ecosystem_cache["data"] = stats
    _ecosystem_cache["ts"] = now
    return stats


@app.route("/")
def index():
    """Main dashboard."""
    try:
        return render_template("index.html", agent_id=AGENT_ID, agent_address=AGENT_ADDRESS, chain_id=CHAIN_ID)
    except Exception:
        return _simple_dashboard()


def _simple_dashboard():
    """Minimal HTML dashboard that works without template files."""
    block = w3.eth.block_number
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Arc Agent — On-chain AI Agent Dashboard</title>
<meta name="description" content="Live Arc testnet dashboard — ERC-8004 AI agent identity + ERC-8183 job contracts running on-chain. Built on Arc by Circle.">
<meta property="og:title" content="Arc Agent — On-chain AI Agent Dashboard">
<meta property="og:description" content="Live Arc testnet data: AI agent identity, job marketplace, USDC gas. Built on Arc by Circle.">
<meta name="twitter:card" content="summary">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0a0a0a;color:#f0a830;font-family:system-ui,sans-serif;padding:20px;min-height:100vh}}
.container{{max-width:640px;margin:0 auto}}
.card{{border:1px solid #f0a830;border-radius:8px;padding:28px;margin-bottom:20px}}
h1{{font-size:1.5rem;margin-bottom:4px}}h2{{font-size:0.85rem;color:#b07820;font-weight:400}}
.row{{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #1a1a1a}}
.label{{color:#b07820}}.val{{font-weight:600}}
.links{{margin-top:20px;display:flex;gap:10px;flex-wrap:wrap}}
.links a{{color:#f0a830;text-decoration:none;border:1px solid #f0a830;padding:6px 14px;border-radius:4px;font-size:0.85rem}}
.links a:hover{{background:#f0a830;color:#0a0a0a}}
.why{{margin-top:24px}}
.why h3{{font-size:1rem;margin-bottom:12px;color:#ffe080}}
.why p{{font-size:0.85rem;color:#c09040;line-height:1.6;margin-bottom:10px}}
.layer{{display:flex;gap:10px;margin-bottom:8px;font-size:0.82rem}}
.layer .tag{{background:#1a1a1a;color:#f0a830;padding:2px 8px;border-radius:3px;font-size:0.75rem;flex-shrink:0;min-width:80px;text-align:center}}
.layer .desc{{color:#b07820}}
.footer{{margin-top:20px;text-align:center;color:#553800;font-size:0.7rem}}
</style></head>
<body>
<div class="container">

<div class="card">
<h1>☤ Arc Agent</h1>
<h2 style="margin-bottom:20px">Testnet Dashboard · Chain {CHAIN_ID}</h2>
<div class="row"><span class="label">Block</span><span class="val">{block:,}</span></div>
<div class="row"><span class="label">Agent ID</span><span class="val">{AGENT_ID}</span></div>
<div class="row"><span class="label">Address</span><span class="val">{AGENT_ADDRESS[:10]}...{AGENT_ADDRESS[-6:]}</span></div>
<div class="row"><span class="label">Gas</span><span class="val">USDC</span></div>
<div class="row"><span class="label">Finality</span><span class="val">Sub-second</span></div>
<div class="row"><span class="label">Status</span><span class="val" style="color:#7cfc00">● Live</span></div>
<div class="links">
<a href="/api/status">📡 API Status</a>
<a href="/api/jobs">💼 API Jobs</a>
<a href="https://docs.arc.network" target="_blank">📖 Docs</a>
<a href="https://testnet.arcscan.app" target="_blank">🔍 Explorer</a>
</div>
</div>

<div class="card">
<div class="why">
<h3>⚡ What is this?</h3>
<p>This is a <strong>live on-chain dashboard</strong> running on <strong>Arc</strong> — Circle's new L1 where AI agents have real identities and get paid in USDC.</p>
<p>Every number you see above is pulled directly from the Arc testnet RPC. No mockups, no simulations — real blocks, real agent identity, real USDC on chain.</p>
<div class="layer"><span class="tag">ERC-8004</span><span class="desc">AI agent identity — this agent (#{AGENT_ID}) exists on-chain with a verifiable address</span></div>
<div class="layer"><span class="tag">ERC-8183</span><span class="desc">Job marketplace — agents post jobs, get funded in USDC, deliver on-chain</span></div>
<div class="layer"><span class="tag">Arc L1</span><span class="desc">USDC as gas, sub-second finality, EVM compatible. Built by Circle</span></div>
<p style="margin-top:16px;font-size:0.8rem;color:#885500">🔗 <a href="https://github.com/Leonis237/arc-agent" target="_blank" style="color:#f0a830">Fork this on GitHub</a> to build your own Arc agent.</p>
</div>
</div>

<div class="footer">☤ Leonis Forge · arc-agent.onrender.com</div>
</div></body></html>"""


@app.route("/api/status")
def api_status():
    """Agent + wallet status."""
    try:
        usdc = get_usdc(w3)
        balance = usdc.functions.balanceOf(AGENT_ADDRESS).call()
        decimals = usdc.functions.decimals().call()
        return jsonify({
            "agent_id": AGENT_ID,
            "address": AGENT_ADDRESS,
            "balance_usdc": balance / 10**decimals,
            "chain_id": CHAIN_ID,
            "rpc": w3.provider.endpoint_uri if hasattr(w3.provider, 'endpoint_uri') else "connected",
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/jobs")
def api_jobs():
    """List recent jobs from AgenticCommerce. Shows our job + recent network jobs."""
    try:
        commerce = get_agentic_commerce(w3)
        job_counter = commerce.functions.jobCounter().call()
        
        # Always include our known job IDs + last 20 network jobs
        our_jobs = {11374}  # add more as we create them
        job_ids = sorted(set(our_jobs) | set(range(max(1, job_counter - 20), job_counter + 1)))
        
        state_names = {0: "NONEXISTENT", 1: "OPEN", 2: "FUNDED", 3: "IN_PROGRESS", 4: "DELIVERED", 5: "COMPLETED", 6: "CANCELLED"}
        jobs = []
        for jid in job_ids:
            try:
                # jobs() returns: (jobId, client, provider, evaluator, description, budget, expiredAt, state, hook)
                j = commerce.functions.jobs(jid).call()
                jobs.append({
                    "job_id": j[0],
                    "client": j[1],
                    "provider": j[2],
                    "evaluator": j[3],
                    "description": j[4][:120],
                    "budget": j[5] / 1e6,
                    "expired_at": j[6],
                    "state": state_names.get(j[7], f"UNKNOWN({j[7]})"),
                    "hook": j[8],
                })
            except Exception:
                continue
        
        return jsonify({"job_counter": job_counter, "jobs": jobs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/worker")
def api_worker():
    """Worker status + earnings from autonomous agent."""
    try:
        state_path = Path(__file__).parent.parent / ".worker_state.json"
        if not state_path.exists():
            return jsonify({
                "status": "not_initialized",
                "agent_id": AGENT_ID,
                "processed_jobs": 0,
                "total_earnings_usdc": 0,
            })
        
        import json
        state = json.loads(state_path.read_text())
        return jsonify({
            "status": "active",
            "agent_id": state.get("agent_id", AGENT_ID),
            "processed_jobs": len(state.get("processed_jobs", {})),
            "total_earnings_usdc": state.get("total_earnings_usdc", 0),
            "last_updated": state.get("updated_at"),
            "recent_jobs": dict(list(state.get("processed_jobs", {}).items())[-5:]),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/ecosystem")
def api_ecosystem():
    """Ecosystem snapshot: total agents, total jobs, agent status."""
    try:
        stats = get_ecosystem_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/scan", methods=["POST"])
def api_scan():
    """Arc-native token scanner — on-chain heuristic checks on Arc testnet."""

    try:
        data = request.get_json(force=True)
        address = data.get("address", "").strip()

        if not address.startswith("0x") or len(address) != 42:
            return jsonify({"error": "invalid token address"}), 400

        checksum = w3.to_checksum_address(address)
        code = w3.eth.get_code(checksum).hex()

        if code == "0x" or len(code) < 10:
            return jsonify({"error": "not a contract on Arc — check the address"}), 200

        bytecode_size = len(code) // 2
        is_proxy = _detect_proxy(code)

        # Read token metadata via ERC-20
        abi_token = json.loads('[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"}]')
        contract = w3.eth.contract(address=checksum, abi=abi_token)
        try:
            token_name = contract.functions.name().call()
        except Exception:
            token_name = "Unknown"
        try:
            token_symbol = contract.functions.symbol().call()
        except Exception:
            token_symbol = "???"

        # Heuristic risk scoring (Arc-native, no Honeypot.is dependency)
        red_flags = []
        score = 0

        if is_proxy:
            score += 10
            red_flags.append("Proxy contract — owner can upgrade logic (common for major tokens)")
        if bytecode_size < 200:
            score += 30
            red_flags.append(f"Suspiciously tiny bytecode ({bytecode_size} bytes) — likely a minimal scam token")
        elif bytecode_size < 800:
            score += 10
            red_flags.append(f"Small bytecode ({bytecode_size} bytes) — simple contract")

        # Known trusted tokens on Arc testnet
        TRUSTED = {
            "0x3600000000000000000000000000000000000000",  # USDC
        }
        if address.lower() in {t.lower() for t in TRUSTED}:
            score = min(score, 5)  # cap at 5% for trusted tokens

        score = min(score, 99)
        if score >= 70:
            verdict, verdict_label = "scam", "🚨 LIKELY SCAM / RUGPULL"
        elif score >= 40:
            verdict, verdict_label = "suspicious", "⚠️ SUSPICIOUS — DYOR"
        else:
            verdict, verdict_label = "safe", "✅ LIKELY SAFE"

        return jsonify({
            "status": "success",
            "address": address,
            "token_name": token_name,
            "token_symbol": token_symbol,
            "score": score,
            "verdict": verdict,
            "verdict_label": verdict_label,
            "bytecode_size": f"{bytecode_size:,} bytes",
            "is_verified": False,  # Arcscan API not available
            "is_proxy": is_proxy,
            "red_flags": red_flags,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _detect_proxy(code_hex: str) -> bool:
    """Heuristic proxy detection: delegatecall pattern or EIP-1967 slot."""
    code_lower = code_hex.lower()
    # delegatecall opcode (f4) in context
    if "f4" in code_lower:
        return True
    # EIP-1967 implementation slot
    eip1967 = "360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
    if eip1967 in code_lower:
        return True
    return False


@app.route("/api/jobs/create", methods=["POST"])
def api_create_job():
    """Create + fund an ERC-8183 job on-chain (marketplace)."""
    try:
        data = request.get_json(force=True)
        description = data.get("description", "").strip()
        provider_addr = data.get("provider", "").strip()
        budget_usdc = float(data.get("budget", 0))
        expire_hours = int(data.get("expire_hours", 24))

        if not description or not provider_addr:
            return jsonify({"error": "description and provider address required"}), 400
        if budget_usdc <= 0:
            return jsonify({"error": "budget must be > 0 USDC"}), 400
        if not provider_addr.startswith("0x") or len(provider_addr) != 42:
            return jsonify({"error": "invalid provider address"}), 400

        commerce = get_agentic_commerce(w3)
        usdc = get_usdc(w3)
        decimals = usdc.functions.decimals().call()

        # Check balance
        balance = usdc.functions.balanceOf(AGENT_ADDRESS).call()
        budget_raw = int(budget_usdc * 10**decimals)
        if balance < budget_raw + 100000:
            return jsonify({"error": f"insufficient USDC. Balance: {balance / 10**decimals:.2f}"}), 402

        # 1. Create job
        expired_at = int(time.time()) + expire_hours * 3600
        receipt = send_tx(w3, account,
            commerce.functions.createJob(
                w3.to_checksum_address(provider_addr),
                AGENT_ADDRESS,  # evaluator = us
                expired_at,
                description,
                "0x0000000000000000000000000000000000000000",  # hook
            )
        )
        # Extract job ID from JobCreated event
        job_id = None
        for log in receipt.logs:
            try:
                decoded = commerce.events.JobCreated().process_log(log)
                job_id = decoded.args.jobId
                break
            except Exception:
                continue
        if job_id is None:
            return jsonify({"error": "job created but could not extract job ID"}), 500

        # 2. Set budget
        send_tx(w3, account,
            commerce.functions.setBudget(job_id, budget_raw, b"")
        )

        # 3. Approve USDC
        send_tx(w3, account,
            usdc.functions.approve(AGENTIC_COMMERCE, budget_raw)
        )

        # 4. Fund job
        send_tx(w3, account,
            commerce.functions.fund(job_id, b"")
        )

        # Read back final state
        time.sleep(2)
        job = commerce.functions.jobs(job_id).call()
        state_names = {0: "NONEXISTENT", 1: "OPEN", 2: "FUNDED", 3: "IN_PROGRESS", 4: "DELIVERED", 5: "COMPLETED", 6: "CANCELLED"}

        return jsonify({
            "success": True,
            "job_id": job_id,
            "description": description,
            "budget": budget_usdc,
            "state": state_names.get(job[7], f"UNKNOWN({job[7]})"),
            "explorer_url": f"https://testnet.arcscan.app/address/{AGENTIC_COMMERCE}",
            "message": f"Job #{job_id} created + funded with {budget_usdc:.2f} USDC. Agent will pick it up.",
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
