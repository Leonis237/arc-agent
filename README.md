# ☤ Arc Agent

**Live autonomous AI agent on Arc Testnet** — ERC-8004 identity + ERC-8183 job contracts running on-chain.

[![Live Dashboard](https://img.shields.io/badge/dashboard-arc.leonisforge.com-blue)](https://arc.leonisforge.com)
[![Arc Testnet](https://img.shields.io/badge/network-Arc%20Testnet-7baeff)](https://docs.arc.network)
[![Python](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/)
[![Tests](https://github.com/Leonis237/arc-agent/workflows/Tests/badge.svg)](https://github.com/Leonis237/arc-agent/actions)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## What is this?

An on-chain AI agent deployed on **Arc** (Circle's L1) that:

- 🔍 **Scans** any Arc token address — instant scam detection via the dashboard
- 🩺 **Audits** wallet health — token approvals, EIP-7702 delegation, source verification
- 🔍 **Audits** contract transparency — owner privileges, supply concentration, proxy risk, liquidity traps
- 🪂 **Checks** airdrop safety — phishing detection, brand impersonation, URL analysis + contract extraction
- 🧠 **Runs** an ONNX scam detection model on token addresses autonomously
- 📤 **Picks up** ERC-8183 jobs from the marketplace autonomously
- 📤 **Submits** results on-chain as verifiable deliverables
- 💰 **Earns** USDC for completed work

**No testnet farming. Real product. Live on-chain.**

## Architecture

```
┌──────────────────────────────────────────────────┐
│                  Arc Testnet                     │
│  ┌──────────────┐  ┌──────────────┐             │
│  │  ERC-8004    │  │  ERC-8183    │             │
│  │  Identity    │  │  Job Market  │             │
│  │  ID: 9138    │  │  16,500+ jobs│             │
│  └──────┬───────┘  └──────┬───────┘             │
│         │                 │                     │
│    Agent Card        Jobs + USDC                │
└─────────┼─────────────────┼─────────────────────┘
          │                 │
    ┌─────▼─────────────────▼──────┐
    │        Agent Worker          │
    │  ┌───────────────────────┐   │
    │  │ ONNX Scam Detector    │   │
    │  │ Token Analysis Engine │   │
    │  │ Transaction Signer    │   │
    │  └───────────────────────┘   │
    │        │                     │
    │    Flask Dashboard           │
    │    arc.leonisforge.com       │
    │    ┌─────────────────────┐   │
    │    │ 🔍 SCAN.TOKEN       │   │
    │    │ 🩺 WALLET.HEALTH    │   │
    │    │ 🔍 CONTRACT.AUDIT   │   │
    │    │ 🪂 AIRDROP.SAFETY   │   │
    │    │ 🪪 Agent Identity   │   │
    │    │ 📋 Job Marketplace  │   │
    │    │ 🌐 Ecosystem Stats  │   │
    │    └─────────────────────┘   │
    │    Leonis Sketch Design      │
    └──────────────────────────────┘
```

## Live Dashboard

👉 **[arc.leonisforge.com](https://arc.leonisforge.com)**

**Leonis Sketch design** — hand-drawn zine aesthetic with paper texture, wobbly borders, handwritten fonts (Kalam + Patrick Hand).

**🛡️ Security Suite** — 4 on-chain safety tools:
- 🔍 **SCAN.TOKEN** (red) — Instant Arc token scanner: scam probability + red flags via heuristic + ONNX
- 🩺 **WALLET.HEALTH** (blue) — Wallet audit: token approvals, EIP-7702 delegation, source verification
- 🔍 **CONTRACT.AUDIT** (gold) — Contract transparency: owner privileges, supply, proxy risk, liquidity traps
- 🪂 **AIRDROP.SAFETY** (green) — Link safety: phishing detection, brand impersonation, URL analysis + contract extraction

**Other dashboard sections:**
- 🪪 **Agent identity card** — ERC-8004 agent ID, wallet, live USDC balance
- 🌐 **Ecosystem snapshot** (featured) — live count of registered agents + total jobs on Arc
- 📋 **Job marketplace** — ALL | OPEN | MINE filters, click-to-expand detail, post.job form
- 🤖 **Worker monitor** — agent status, jobs processed, total USDC earnings
- ⚡ 15-second auto-refresh from on-chain data

## Project Structure

```
.
├── app.py              # Flask dashboard + API endpoints (all 4 security tools)
├── arc_utils.py        # Web3 integration, contract ABIs, tx helpers
├── worker.py           # Autonomous agent worker — 4 capabilities: scam + wallet + contract + airdrop
├── wallet_health.py    # Wallet security audit: approvals, delegation, source
├── contract_audit.py   # Contract transparency audit: owner, supply, proxy, traps
├── airdrop_safety.py   # Airdrop link analysis: phishing, impersonation, contract extraction
├── process_job.py      # Single job: scam detection + submit deliverable
├── complete_job.py     # Complete job + claim USDC payment
├── register_agent.py   # ERC-8004 agent registration
├── create_job.py       # ERC-8183 job creation + USDC funding
├── templates/          # Dashboard HTML (Leonis Sketch design)
├── requirements.txt    # flask, web3, onnxruntime, gunicorn, numpy
├── .env.example        # Template for local config
└── render.yaml         # Render deployment config (Python + gunicorn)
```

## ERC-8004 Agent

| Field | Value |
|---|---|
| **Agent ID** | `9138` |
| **Address** | `0xe43f191d3DBcCEBd94F960a42dEafdF8E57215BB` |
| **Network** | Arc Testnet (chain 5042002) |
| **Gas Token** | USDC |
| **Capabilities** | Token scam detection, wallet health audit, contract transparency audit, airdrop safety analysis |

[View on ArcScan →](https://testnet.arcscan.app/address/0xe43f191d3DBcCEBd94F960a42dEafdF8E57215BB)

## How It Works

### Full Job Lifecycle

1. **Client creates job** → `createJob(provider, evaluator, expiredAt, description, hook)`
2. **Funds escrow** → `setBudget` + USDC `approve` + `fund`
3. **Agent scans** → Worker detects FUNDED jobs matching 4 capability types (scam, wallet health, contract audit, airdrop safety)
4. **Agent executes** → Routes to correct pipeline: ONNX scam detector, wallet health analyzer, contract auditor, or airdrop safety checker
5. **Agent submits** → `submit(jobId, deliverableHash)` — result on-chain
6. **Agent completes** → `complete(jobId, deliverableHash)` — claims USDC payment

### Job States

```
OPEN → FUNDED → IN_PROGRESS → DELIVERED → COMPLETED
  │        │                                  │
  └────────┴────────── CANCELLED ←───────────┘
```

## Arc Testnet Reference

| Config | Value |
|---|---|
| Chain ID | `5042002` |
| RPC | `https://rpc.testnet.arc.network` |
| Explorer | `https://testnet.arcscan.app` |
| Faucet | `https://faucet.circle.com` |
| USDC Token | `0x3600000000000000000000000000000000000000` |
| Identity Registry (ERC-8004) | `0x8004A818BFB912233c491871b3d84c89A494BD9e` |
| AgenticCommerce (ERC-8183) | `0x0747EEf0706327138c69792bF28Cd525089e4583` |

## Quick Start

```bash
# Clone
git clone https://github.com/Leonis237/arc-agent.git
cd arc-agent

# Install
pip install -r requirements.txt

# Set up wallet
cp .env.example .env
# Add your PRIVATE_KEY to .env
# Get testnet USDC: https://faucet.circle.com

# Run dashboard locally
python webapp/app.py
# → http://localhost:5050
```

## Built With

- **Python 3.11** — Core agent logic
- **Flask** — Web dashboard
- **web3.py** — Arc EVM interaction (no Circle SDK needed)
- **ONNX Runtime** — Token scam detection model
- **Gunicorn** — Production WSGI server
- **Render** — Free-tier hosting

## License

MIT — Built by [Leonis Forge](https://leonisforge.com)

---

☤ *Not affiliated with Circle or Arc. Testnet product — ARC token not launched.*
