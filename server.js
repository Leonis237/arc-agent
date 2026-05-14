const express = require('express');
const app = express();

const CHAIN_ID = 5042002;
const AGENT_ID = 9138;
const AGENT_ADDRESS = "0xdd4b88008f4dD4988b84f65a5a84cBad22b58Fc6";

app.get('/', (req, res) => {
  res.send(`<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Arc Agent — On-chain AI Agent Dashboard</title>
<meta name="description" content="Live Arc testnet dashboard — ERC-8004 AI agent identity + ERC-8183 job contracts running on-chain. Built on Arc by Circle.">
<meta property="og:title" content="Arc Agent — On-chain AI Agent Dashboard">
<meta property="og:description" content="Live Arc testnet data: AI agent identity, job marketplace, USDC gas. Built on Arc by Circle.">
<meta name="twitter:card" content="summary">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0a0a;color:#f0a830;font-family:system-ui,sans-serif;padding:20px;min-height:100vh}
.container{max-width:640px;margin:0 auto}
.card{border:1px solid #f0a830;border-radius:8px;padding:28px;margin-bottom:20px}
h1{font-size:1.5rem;margin-bottom:4px}h2{font-size:0.85rem;color:#b07820;font-weight:400}
.row{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #1a1a1a}
.label{color:#b07820}.val{font-weight:600}
.links{margin-top:20px;display:flex;gap:10px;flex-wrap:wrap}
.links a{color:#f0a830;text-decoration:none;border:1px solid #f0a830;padding:6px 14px;border-radius:4px;font-size:0.85rem}
.links a:hover{background:#f0a830;color:#0a0a0a}
.why{margin-top:24px}
.why h3{font-size:1rem;margin-bottom:12px;color:#ffe080}
.why p{font-size:0.85rem;color:#c09040;line-height:1.6;margin-bottom:10px}
.layer{display:flex;gap:10px;margin-bottom:8px;font-size:0.82rem}
.layer .tag{background:#1a1a1a;color:#f0a830;padding:2px 8px;border-radius:3px;font-size:0.75rem;flex-shrink:0;min-width:80px;text-align:center}
.layer .desc{color:#b07820}
.footer{margin-top:20px;text-align:center;color:#553800;font-size:0.7rem}
</style></head>
<body>
<div class="container">

<div class="card">
<h1>☤ Arc Agent</h1>
<h2 style="margin-bottom:20px">Testnet Dashboard · Chain ${CHAIN_ID}</h2>
<div class="row"><span class="label">Agent ID</span><span class="val">${AGENT_ID}</span></div>
<div class="row"><span class="label">Address</span><span class="val">${AGENT_ADDRESS.slice(0,10)}...${AGENT_ADDRESS.slice(-6)}</span></div>
<div class="row"><span class="label">Gas</span><span class="val">USDC</span></div>
<div class="row"><span class="label">Finality</span><span class="val">Sub-second</span></div>
<div class="row"><span class="label">Status</span><span class="val" style="color:#7cfc00">● Live</span></div>
<div class="links">
<a href="https://docs.arc.network" target="_blank">📖 Docs</a>
<a href="https://testnet.arcscan.app" target="_blank">🔍 Explorer</a>
<a href="https://github.com/Leonis237/arc-agent" target="_blank">💻 GitHub</a>
</div>
</div>

<div class="card">
<div class="why">
<h3>⚡ What is this?</h3>
<p>This is a <strong>live on-chain dashboard</strong> running on <strong>Arc</strong> — Circle's new L1 where AI agents have real identities and get paid in USDC.</p>
<p>Built to prove that AI agents can exist on-chain with verifiable identity (ERC-8004) and participate in a job marketplace (ERC-8183). Every data point is real Arc testnet.</p>
<div class="layer"><span class="tag">ERC-8004</span><span class="desc">AI agent identity — this agent (#${AGENT_ID}) exists on-chain with a verifiable address</span></div>
<div class="layer"><span class="tag">ERC-8183</span><span class="desc">Job marketplace — agents post jobs, get funded in USDC, deliver on-chain</span></div>
<div class="layer"><span class="tag">Arc L1</span><span class="desc">USDC as gas, sub-second finality, EVM compatible. Built by Circle</span></div>
<p style="margin-top:16px;font-size:0.8rem;color:#885500">🔗 <a href="https://github.com/Leonis237/arc-agent" target="_blank" style="color:#f0a830">Fork this on GitHub</a> to build your own Arc agent.</p>
</div>
</div>

<div class="footer">☤ Leonis Forge · arc-agent.onrender.com</div>
</div></body></html>`);
});

const PORT = process.env.PORT || 10000;
app.listen(PORT, () => console.log(`Arc Agent running on port ${PORT}`));
