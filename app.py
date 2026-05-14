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
    return render_template("index.html", agent_id=AGENT_ID, agent_address=AGENT_ADDRESS, chain_id=CHAIN_ID)


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
