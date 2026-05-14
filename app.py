"""
Arc Agent Dashboard — Flask webapp for visualizing ERC-8004 agent + ERC-8183 jobs.
"""
import os
from pathlib import Path
from flask import Flask, render_template, jsonify

from arc_utils import (
    init_web3, get_account,
    get_agentic_commerce, get_usdc,
    AGENTIC_COMMERCE, CHAIN_ID
)

app = Flask(__name__)
w3 = init_web3()
account = get_account(w3)

AGENT_ID = 9138
AGENT_ADDRESS = account.address


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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
