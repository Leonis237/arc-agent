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
<title>Arc Agent — Testnet Dashboard</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0a0a0a;color:#f0a830;font-family:system-ui,sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;padding:20px}}
.card{{border:1px solid #f0a830;border-radius:8px;padding:32px;max-width:520px;width:100%}}
h1{{font-size:1.6rem;margin-bottom:4px}}h2{{font-size:0.85rem;color:#b07820;font-weight:400;margin-bottom:24px}}
.row{{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #1a1a1a}}
.label{{color:#b07820}}.val{{font-weight:600}}
.links{{margin-top:24px;display:flex;gap:12px;flex-wrap:wrap}}
.links a{{color:#f0a830;text-decoration:none;border:1px solid #f0a830;padding:6px 14px;border-radius:4px;font-size:0.85rem}}
.links a:hover{{background:#f0a830;color:#0a0a0a}}
.footer{{margin-top:20px;text-align:center;color:#b07820;font-size:0.75rem}}
</style></head>
<body>
<div class="card">
<h1>☤ Arc Agent</h1>
<h2>Testnet Dashboard · Chain {CHAIN_ID}</h2>
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
