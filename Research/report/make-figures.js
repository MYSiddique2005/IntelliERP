// Writes the report's diagrams and charts as HTML pages in figures/; render.js turns them into PNGs.
// Every number in a chart comes from a results file in LLM/evaluation/results (see the comment above each chart).
//   node make-figures.js && node render.js
const fs = require('fs');
const path = require('path');
const DIR = path.join(__dirname, 'figures');
fs.mkdirSync(DIR, { recursive: true });

const CSS = `body{margin:0;background:#fff;font-family:Arial,Helvetica,sans-serif;color:#111}
#fig{display:inline-block;padding:18px;background:#fff}
.box{border:2px solid #1f3b73;border-radius:8px;padding:10px 12px;background:#f3f6fc;font-size:18px;text-align:center}
.title{font-weight:bold;font-size:20px;margin-bottom:5px}
.small{font-size:16.5px;color:#222;line-height:1.35}
.phase{border:2px solid var(--c);border-radius:12px;background:var(--bg);padding:12px 14px}
.phase h3{margin:0 0 10px;font-size:22px;color:var(--c)}
.cards{display:grid;gap:10px}
.card{background:#fff;border:1.5px solid #c9d3e6;border-radius:8px;padding:9px 10px;text-align:center;font-size:16.5px;line-height:1.3}
.card b{display:block;font-size:17.5px;margin-bottom:3px;color:#111}
.down{text-align:center;font-size:30px;color:#1f3b73;line-height:1.1;margin:4px 0}
#fig svg .relationshipLabel, #fig svg .edgeLabel, #fig svg .edgeLabel p, #fig svg .edgeLabel span{font-size:19px !important}`;

function page(name, body, script = '') {
  fs.writeFileSync(path.join(DIR, name + '.html'), `<!doctype html><html><head><meta charset="utf-8"><style>${CSS}</style>
<script src="../node_modules/mermaid/dist/mermaid.min.js"></script>
<script src="../node_modules/chart.js/dist/chart.umd.js"></script></head>
<body><div id="fig">${body}</div><script>${script}</script></body></html>`);
}

function mermaidPage(name, def, width = 1100) {
  page(name, `<div style="min-width:${Math.min(width, 700)}px;display:inline-block"><pre class="mermaid" style="margin:0">${def}</pre></div>`,
    `window.__ready=false; mermaid.initialize({startOnLoad:false, theme:'neutral', fontFamily:'Arial', themeVariables:{fontSize:'21px'},
       flowchart:{htmlLabels:true, nodeSpacing:30, rankSpacing:38, padding:12, useMaxWidth:false, wrappingWidth:260},
       sequence:{useMaxWidth:false, actorFontSize:20, messageFontSize:19, noteFontSize:18, actorMargin:28, width:170, boxMargin:6, messageMargin:30, mirrorActors:false, wrap:true},
       class:{useMaxWidth:false}, er:{fontSize:20, useMaxWidth:false}, state:{useMaxWidth:false}});
     mermaid.run().then(()=>{window.__ready=true});`);
}

function chartPage(name, config, width = 900, height = 480) {
  page(name, `<div style="width:${width}px;height:${height}px"><canvas id="c"></canvas></div>`,
    `Chart.defaults.font.family='Arial'; Chart.defaults.font.size=20; Chart.defaults.plugins.title.font={size:22,weight:'bold'}; Chart.defaults.color='#111';
     const cfg=${JSON.stringify(config)};
     cfg.options=Object.assign({animation:false,responsive:true,maintainAspectRatio:false},cfg.options||{});
     cfg.plugins=[{id:'labels',afterDatasetsDraw(chart){const {ctx}=chart;ctx.save();ctx.font='bold 17px Arial';ctx.fillStyle='#111';
       chart.data.datasets.forEach((ds,i)=>{chart.getDatasetMeta(i).data.forEach((bar,j)=>{const v=ds.data[j];if(v==null)return;
       const horiz=chart.options.indexAxis==='y';const t=(ds.labelSuffix!==undefined?v+ds.labelSuffix:v+'%');
       if(horiz){ctx.textAlign='left';ctx.textBaseline='middle';ctx.fillText(t,bar.x+4,bar.y);}else{ctx.textAlign='center';ctx.textBaseline='bottom';ctx.fillText(t,bar.x,bar.y-3);}});});ctx.restore();}}];
     new Chart(document.getElementById('c'),cfg);`);
}

const BLUE = '#2f5597', ORANGE = '#c55a11', GREY = '#8c8c8c', GREEN = '#548235', LIGHT = '#9dc3e6';

// ---------------------------------------------------------------- Chapter 3: methodology and design
// Figure 1.1: the research methodology (design science), one row out and one row back with a feedback arrow
page('fig-research-method', `<div style="width:780px;position:relative">
<div style="display:grid;grid-template-columns:1fr 34px 1fr 34px 1fr;row-gap:44px;align-items:stretch">
 <div class="box"><div class="title">1. Problem</div><div class="small">False statements by ERP assistants; literature review of 61 papers</div></div>
 <div class="down" style="align-self:center">➜</div>
 <div class="box"><div class="title">2. Requirements</div><div class="small">From the literature, the dataset, the roles and 86 test questions</div></div>
 <div class="down" style="align-self:center">➜</div>
 <div class="box"><div class="title">3. Design and build</div><div class="small">Nine phases, each built, tested and reviewed</div></div>
 <div class="box" style="background:#eef6ea;border-color:#548235"><div class="title">6. Results</div><div class="small">Report, conference paper and journal article</div></div>
 <div class="down" style="align-self:center">⬅</div>
 <div class="box" style="background:#eef6ea;border-color:#548235"><div class="title">5. Evaluate</div><div class="small">Controlled experiments with statistics</div></div>
 <div class="down" style="align-self:center">⬅</div>
 <div class="box" style="background:#eef6ea;border-color:#548235"><div class="title">4. Test</div><div class="small">272 automated tests; verifier frozen before its test</div></div>
</div>
<div style="position:absolute;right:120px;top:118px;font-size:30px;color:#1f3b73">⬇</div>
<div style="margin-top:16px;text-align:center;font-size:17px;color:#1f3b73;border-top:2px dashed #1f3b73;padding-top:8px">
 Feedback: results of steps 4 and 5 returned to steps 2 and 3 (five failures led to five design changes; the limits of the pattern checker led to TRACE)</div>
</div>`);

// Figure 2.1: how the literature review is organised
page('fig-litmap', `<div style="width:780px">
<div class="phase" style="--c:#1f3b73;--bg:#f3f6fc"><h3>Six research areas reviewed</h3>
 <div class="cards" style="grid-template-columns:1fr 1fr 1fr">
  <div class="card"><b>AI in ERP</b>2.1</div><div class="card"><b>LLMs over enterprise data</b>2.2</div><div class="card"><b>Agents in supply chain and ERP</b>2.3</div>
  <div class="card"><b>Grounding and tool use</b>2.4</div><div class="card"><b>Hallucination detection</b>2.5</div><div class="card"><b>Claim verification and run-time checking</b>2.6–2.8</div>
 </div></div>
<div class="down">⬇</div>
<div class="phase" style="--c:#c55a11;--bg:#fff6ee"><h3>Four research gaps (2.10)</h3>
 <div class="cards" style="grid-template-columns:1fr 1fr">
  <div class="card"><b>Gap 1</b>Statements are not verified against the system of record</div><div class="card"><b>Gap 2</b>Verdicts depend on another model</div>
  <div class="card"><b>Gap 3</b>Business rules and permissions are not checked</div><div class="card"><b>Gap 4</b>Natural errors and end-to-end effect rarely measured</div>
 </div></div>
<div class="down">⬇</div>
<div class="phase" style="--c:#548235;--bg:#eef6ea"><h3>How IntelliERP answers them</h3>
 <div class="cards" style="grid-template-columns:1fr 1fr">
  <div class="card"><b>Grounding</b>Data only through permission-checked tools; company rules from a knowledge base built from the code</div>
  <div class="card"><b>TRACE</b>Every statement becomes a typed assertion, decided by the system's own code (state, derived results, rules and permissions)</div>
 </div></div>
</div>`);

// Figure 3.1: main methodology and system development lifecycle (four phases, top to bottom)
page('fig-methodology', `<div style="width:780px">
<div class="phase" style="--c:#1f3b73;--bg:#f3f6fc"><h3>Phase 1 — Fact-finding and requirements</h3>
 <div class="cards" style="grid-template-columns:1fr 1fr 1fr">
  <div class="card"><b>Literature review</b>61 verified papers, four research gaps</div>
  <div class="card"><b>Dataset analysis</b>Wide World Importers: 227 products, 72,696 sales lines</div>
  <div class="card"><b>Roles and test questions</b>4 roles, 12 permissions, 86 questions</div>
 </div>
 <div class="card" style="margin-top:10px;background:#e8eef9"><b>Output</b>11 functional and 8 non-functional requirements</div></div>
<div class="down">⬇</div>
<div class="phase" style="--c:#7030a0;--bg:#f6f0fb"><h3>Phase 2 — System design (UML)</h3>
 <div class="cards" style="grid-template-columns:1fr 1fr">
  <div class="card"><b>Context and behaviour</b>Rich picture, use case, activity and sequence diagrams</div>
  <div class="card"><b>Structure</b>Class diagram, entity-relationship diagram, purchase-order states</div>
 </div></div>
<div class="down">⬇</div>
<div class="phase" style="--c:#2f7d4f;--bg:#eef7f1"><h3>Phase 3 — Iterative development (nine phases)</h3>
 <div class="cards" style="grid-template-columns:1fr 1fr 1fr">
  <div class="card"><b>Phases 1–3</b>ERP foundation, PostgreSQL, analytics</div>
  <div class="card"><b>Phases 4–7</b>AI assistant, grounding, insights, AI-drafted orders</div>
  <div class="card"><b>Phases 8–9</b>Evaluation, typed run-time verification (TRACE)</div>
 </div>
 <div style="text-align:center;font-size:17px;margin-top:8px;color:#2f7d4f">each phase: build → automated tests → review</div></div>
<div class="down">⬇</div>
<div class="phase" style="--c:#c55a11;--bg:#fff6ee"><h3>Phase 4 — Testing and evaluation</h3>
 <div class="cards" style="grid-template-columns:1fr 1fr 1fr">
  <div class="card"><b>Automated testing</b>272 tests passed; integration tests</div>
  <div class="card"><b>Grounding (RQ1)</b>86 questions, 3 runs, 2 models</div>
  <div class="card"><b>Verification (RQ2, RQ3)</b>Held-out, natural-error, false-premise, harm and repeatability tests</div>
 </div></div>
<div style="margin-top:12px;text-align:center;font-size:17px;color:#1f3b73;border:2px dashed #1f3b73;border-radius:8px;padding:8px">
 ↺ Results of Phase 4 fed back into Phases 1 to 3: five failures in the first evaluation led to five design changes, and the limits of the pattern checker led to TRACE</div>
</div>`);

// Figure 3.2: rich picture (top to bottom)
page('fig-context', `<div style="width:780px">
<div class="cards" style="grid-template-columns:1fr 1fr 1fr 1fr">
 ${['Administrator', 'Inventory Manager', 'Procurement Manager', 'Employee (read-only)'].map(r => `<div class="card" style="font-size:17px">👤<br><b>${r}</b></div>`).join('')}
</div>
<div class="down" style="font-size:22px">⇅ web browser</div>
<div style="display:grid;grid-template-columns:1fr 70px 230px;align-items:center">
 <div>
  <div class="box" style="background:#e8eef9"><div class="title">IntelliERP web application (React)</div>
   <div class="small">Dashboard · Sales · Inventory · Procurement · Suppliers · Analytics · Approvals · AI Insights · AI Assistant · Audit log</div></div>
  <div class="down" style="font-size:22px">⇅ REST API + JWT</div>
  <div class="box"><div class="title">FastAPI back end</div>
   <div class="small">Role-based access control · ERP services · Analytics (fixed rules)<br>AI assistant: 15 permission-checked tools · Knowledge base (41 passages)<br>
   <b>Verification: figures and typed assertions (TRACE)</b><br>Draft-only actions · Audit log</div></div>
  <div class="down" style="font-size:22px">⇅ SQLAlchemy</div>
  <div class="box"><div class="title">PostgreSQL database</div><div class="small">227 products, 7 suppliers, 72,696 sales lines, 5,443 purchase-order lines</div></div>
 </div>
 <div class="down" style="font-size:34px">⇄</div>
 <div class="box" style="background:#fff4e5;border-color:#c55a11"><div class="title">LLM provider (external)</div>
  <div class="small">Google Gemini API (free tier): gemini-3.5-flash-lite, Gemma 4 31B<br><br>Receives the question, tool results and knowledge passages; <b>never the database</b></div></div>
</div></div>`);

// Use case diagram drawn as SVG
(() => {
  const actors = [['Administrator', 110], ['Inventory Manager', 260], ['Procurement Manager', 410], ['Employee', 560]];
  const cases = [
    ['Log in', 50, [0, 1, 2, 3]], ['View dashboard and ERP records', 108, [0, 1, 2, 3]], ['View analytics and risk', 166, [0, 1, 2]],
    ['Ask the AI assistant', 224, [0, 1, 2]], ['Review AI insights', 282, [0, 1, 2]], ['Create / submit purchase order', 340, [0, 2]],
    ['Draft order from AI recommendation', 398, [0, 2]], ['Approve or reject purchase order', 456, [0, 2]], ['View audit log', 514, [0]],
  ];
  const actor = (x, y, n) => `<g><circle cx="${x}" cy="${y - 28}" r="10" fill="none" stroke="#111"/><line x1="${x}" y1="${y - 18}" x2="${x}" y2="${y + 6}" stroke="#111"/>
    <line x1="${x - 14}" y1="${y - 10}" x2="${x + 14}" y2="${y - 10}" stroke="#111"/><line x1="${x}" y1="${y + 6}" x2="${x - 11}" y2="${y + 24}" stroke="#111"/>
    <line x1="${x}" y1="${y + 6}" x2="${x + 11}" y2="${y + 24}" stroke="#111"/><text x="${x}" y="${y + 46}" font-size="17" text-anchor="middle">${n}</text></g>`;
  let s = '';
  s += `<rect x="195" y="10" width="430" height="570" fill="none" stroke="#1f3b73" stroke-width="2"/><text x="410" y="36" text-anchor="middle" font-weight="bold" font-size="19">IntelliERP</text>`;
  cases.forEach(([n, y, who]) => {
    s += `<ellipse cx="410" cy="${y + 20}" rx="205" ry="24" fill="#f3f6fc" stroke="#1f3b73" stroke-width="1.5"/><text x="410" y="${y + 26}" text-anchor="middle" font-size="17">${n}</text>`;
    who.forEach(a => { s += `<line x1="110" y1="${actors[a][1]}" x2="225" y2="${y + 20}" stroke="#999" stroke-width="0.8"/>`; });
  });
  actors.forEach(([n, y]) => { s += actor(70, y, n); });
  s += actor(720, 250, 'LLM provider');
  [224, 282, 398].forEach(y => { s += `<line x1="615" y1="${y + 20}" x2="700" y2="240" stroke="#c55a11" stroke-dasharray="5,4" stroke-width="1.5"/>`; });
  s += `<ellipse cx="410" cy="510" rx="0" ry="0"/>`;
  s += `<text x="720" y="320" text-anchor="middle" font-size="15" fill="#555">«system», secondary</text>`;
  page('fig-usecase', `<svg width="800" height="595" font-family="Arial">${s}</svg>`);
})();

mermaidPage('fig-activity', `flowchart TD
  A([User asks a question]) --> B[Retrieve 4 knowledge passages<br/>BM25 over the 41-passage knowledge base]
  B --> C[Offer the model only the tools<br/>the user's role permits]
  C --> D{Model calls a tool?}
  D -- yes --> E[Check permission again,<br/>run the tool through the ERP services] --> D
  D -- "no (answer drafted, max 8 rounds)" --> F[Verify the draft answer:<br/>every figure traced to a source;<br/>every factual statement checked by TRACE]
  F --> G{Contradicted<br/>or untraced?}
  G -- "yes, first time" --> H[Send back once with the<br/>contradicted statements and the data] --> F
  G -- no --> I[Show answer with sources,<br/>passages used and check results]
  G -- "yes, after correction" --> J[Show answer with the remaining<br/>statements flagged as warnings]
  I --> K([Audit log entry])
  J --> K`, 900);

// Class diagram drawn as SVG in three columns, so that it stays readable at page width
(() => {
  const W = 240, X = [5, 302, 599];
  const box = (col, y, name, members) => ({ x: X[col], y, name, members, h: 40 + members.length * 23 + 8 });
  const B = {
    insight: box(1, 10, 'InsightService', ['+run_scan(trigger)', '+review(id, status)']),
    kb: box(0, 140, 'KnowledgeBase', ['+search(query, k)']),
    ai: box(1, 140, 'AIService', ['+chat(message, user, history)']),
    audit: box(2, 140, 'AuditService', ['+record(event)']),
    toolbox: box(0, 290, 'Toolbox', ['+tools_for(user)', '+run(call, user)']),
    rec: box(1, 290, 'RecommendationChecker', ['+check(recommendation)', '+product_facts(id)', '+supplier_facts(id)']),
    trace: box(2, 290, 'TraceVerifier', ['+check(text, subject)', '+rule_verdicts(text)', '+model_verdicts(assertions)']),
    analytics: box(0, 470, 'AnalyticsService', ['+stock_risk(product)', '+forecast(product)', '+supplier_performance()', '+what_if(scenario)']),
    action: box(1, 470, 'AIActionService', ['+draft_from_recommendation()']),
    assertion: box(2, 470, 'Assertion', ['family: state | derived | policy', 'attribute, subject', 'comparator, value']),
    proc: box(1, 620, 'ProcurementService', ['+create_draft()', '+submit()']),
    verdict: box(2, 640, 'Verdict', ['status: supported |', '  contradicted | unverifiable', 'quote, reason']),
    approval: box(1, 790, 'ApprovalService', ['+approve()', '+reject()']),
  };
  let svg = `<defs><marker id="ar" markerWidth="12" markerHeight="10" refX="11" refY="5" orient="auto"><path d="M0,0 L12,5 L0,10 z" fill="#1f3b73"/></marker></defs>`;
  for (const b of Object.values(B)) {
    svg += `<rect x="${b.x}" y="${b.y}" width="${W}" height="${b.h}" fill="#f3f6fc" stroke="#1f3b73" stroke-width="1.8"/>
      <text x="${b.x + W / 2}" y="${b.y + 26}" text-anchor="middle" font-weight="bold" font-size="18">${b.name}</text>
      <line x1="${b.x}" y1="${b.y + 38}" x2="${b.x + W}" y2="${b.y + 38}" stroke="#1f3b73"/>
      ${b.members.map((m, i) => `<text x="${b.x + 10}" y="${b.y + 60 + i * 23}" font-size="15" xml:space="preserve">${m}</text>`).join('')}`;
  }
  const edge = (pts, label, lx, ly, anchor = 'middle') => {
    svg += `<polyline points="${pts.map(p => p.join(',')).join(' ')}" fill="none" stroke="#1f3b73" stroke-width="1.6" marker-end="url(#ar)"/>`;
    if (label) svg += `<text x="${lx}" y="${ly}" font-size="15" fill="#c55a11" text-anchor="${anchor}" font-style="italic">${label}</text>`;
  };
  const bot = b => b.y + b.h, cx = b => b.x + W / 2;
  edge([[cx(B.insight), bot(B.insight)], [cx(B.ai), B.ai.y]], 'asks', cx(B.ai) + 8, 128, 'start');
  edge([[B.ai.x, 175], [B.kb.x + W, 175]], 'grounds', 273, 166, 'middle');
  edge([[B.ai.x + W, 175], [B.audit.x, 175]], 'logs', 570, 166);
  edge([[B.ai.x + 30, bot(B.ai)], [cx(B.toolbox), B.toolbox.y]], 'uses', 200, 250);
  edge([[cx(B.ai), bot(B.ai)], [cx(B.rec), B.rec.y]], 'checks figures', cx(B.ai) + 8, 262, 'start');
  edge([[B.ai.x + W - 30, bot(B.ai)], [cx(B.trace), B.trace.y]], 'verifies', 660, 250);
  edge([[B.trace.x, 345], [B.rec.x + W, 345]], 'facts', 570, 336);
  edge([[cx(B.toolbox), bot(B.toolbox)], [cx(B.analytics), B.analytics.y]], 'reads', cx(B.toolbox) + 8, 445, 'start');
  edge([[B.toolbox.x + W - 20, bot(B.toolbox)], [B.action.x + 40, B.action.y]], 'draft only', 282, 455, 'end');
  edge([[cx(B.trace), bot(B.trace)], [cx(B.assertion), B.assertion.y]], 'extracts', cx(B.trace) + 8, 455, 'start');
  edge([[B.trace.x + W, 330], [848, 330], [848, 700], [B.verdict.x + W, 700]], 'returns', 840, 620, 'end');
  edge([[cx(B.action), bot(B.action)], [cx(B.proc), B.proc.y]], 'creates draft', cx(B.action) + 8, 600, 'start');
  edge([[cx(B.proc), bot(B.proc)], [cx(B.approval), B.approval.y]], 'second person decides', cx(B.proc) + 8, 775, 'start');
  edge([[B.proc.x + W, 670], [570, 670], [570, 236], [B.audit.x + 30, 236], [B.audit.x + 30, bot(B.audit)]], 'logs', 574, 660, 'start');
  page('fig-class', `<svg width="860" height="${bot(B.approval) + 12}" font-family="Arial">${svg}</svg>`);
})();

mermaidPage('fig-sequence', `sequenceDiagram
  autonumber
  actor U as User
  participant UI as React UI
  participant AI as Back end (AIService)
  participant LLM as Gemini
  participant T as Tools + Analytics
  participant V as TRACE
  U->>UI: types a question
  UI->>AI: POST /ai/chat (JWT)
  AI->>AI: retrieve passages, select permitted tools
  AI->>LLM: question, passages, tool list
  LLM-->>AI: tool call
  AI->>T: run tool (permission checked)
  T-->>AI: facts by module
  AI->>LLM: tool result
  LLM-->>AI: draft answer
  AI->>V: check draft answer
  V->>LLM: extract typed assertions
  LLM-->>V: assertions (JSON)
  V->>T: evaluate each assertion
  V-->>AI: verdicts
  alt a statement is contradicted
    AI->>LLM: send back once with the data
    LLM-->>AI: corrected answer
  end
  AI-->>UI: answer, sources, checks
  UI-->>U: answer with check results`, 900);

// ---------------------------------------------------------------- Chapter 5: development
mermaidPage('fig-architecture', `flowchart TB
  subgraph FE[Frontend: React 19 + TypeScript + Vite + Tailwind]
    P[Pages: Dashboard, Sales, Inventory, Procurement,<br/>Analytics, Approvals, AI Insights, AI Assistant, Audit]
    S[Services: Axios clients, AuthContext, JWT storage]
  end
  subgraph BE[Backend: Python + FastAPI]
    R[API routers /api/v1: one per module]
    SEC[Security: JWT, bcrypt, role to permission map]
    SV[Services: business logic and workflows]
    AN[Analytics: demand, forecast, stock risk,<br/>supplier performance, what-if]
    LL[LLM layer: providers, 15 tools, knowledge base,<br/>recommendation checks, TRACE verifier]
    RP[Repositories: PostgreSQL / in-memory]
  end
  DB[(PostgreSQL 11 tables)]
  EXT[[Gemini API]]
  P --> S --> R
  R --> SEC
  R --> SV --> RP --> DB
  SV --> AN
  SV --> LL --> EXT
  LL --> AN`, 1000);

mermaidPage('fig-trace', `flowchart TD
  A[Assistant's draft answer] --> B[LLM extractor<br/>prompt trace-extract-3<br/>JSON assertions]
  A --> C[Rule extractor<br/>12 claim patterns]
  B --> D{Schema validation<br/>64 attributes, 3 families}
  D -- invalid --> X[dropped and counted]
  D -- valid --> E[Grounding and type checks<br/>subject named in text,<br/>ambiguous terms, units, dates]
  C --> F
  E --> F[Deterministic verifier:<br/>evaluates each assertion with<br/>the system's own tested code]
  F --> G[supported]
  F --> H[contradicted]
  F --> I[unverifiable]
  H --> J[sent back once for correction,<br/>then shown as a warning]`, 1250);

mermaidPage('fig-po-states', `stateDiagram-v2
  direction TB
  [*] --> Draft: created by a user or drafted by the AI
  Draft --> Draft: edited (procurement:create)
  Draft --> PendingApproval: submitted
  Draft --> [*]: deleted
  PendingApproval --> Approved: approved by a different user (procurement:approve)
  PendingApproval --> Rejected: rejected
  Approved --> [*]
  Rejected --> [*]`, 1100);

mermaidPage('fig-erd', `erDiagram
  direction TB
  SUPPLIERS ||--o{ SUPPLIER_PRODUCTS : supplies
  PRODUCTS ||--o{ SUPPLIER_PRODUCTS : "supplied by"
  PRODUCTS ||--o{ INVENTORY : "stocked as"
  PRODUCTS ||--o{ SALES_ORDERS : "sold in"
  PRODUCTS ||--o{ PURCHASE_ORDERS : "ordered in"
  SUPPLIERS ||--o{ PURCHASE_ORDERS : receives
  PURCHASE_ORDERS ||--o| APPROVALS : "decided by"
  USERS ||--o{ APPROVALS : decides
  USERS ||--o{ AUDIT_LOGS : performs
  AI_SCANS ||--o{ AI_INSIGHTS : produces
  AI_INSIGHTS |o--o{ PURCHASE_ORDERS : "drafted from"
  PRODUCTS { string id PK
    string name
    float price
    float unit_cost }
  INVENTORY { string id PK
    string product_id FK
    string warehouse
    int current_stock
    int safety_stock
    int reorder_level }
  PURCHASE_ORDERS { string id PK
    string product_id FK
    string supplier_id FK
    int quantity
    string status
    string origin
    json ai_recommendation }
  SALES_ORDERS { string id PK
    string product_id FK
    int quantity
    date order_date
    string status }`, 1100);

// ---------------------------------------------------------------- Chapter 6: results (charts)
// LLM/evaluation/results/fixed-summary.md, gemma4-summary.md, extended-1
chartPage('chart-runs', { type: 'bar', data: { labels: ['E1 (before fixes)', 'F1', 'F2', 'F3', 'G (Gemma 4 31B)'],
  datasets: [{ label: 'Questions passed with grounding (of 86)', data: [81, 84, 86, 86, 86], backgroundColor: [GREY, BLUE, BLUE, BLUE, GREEN], labelSuffix: '' }] },
  options: { plugins: { legend: { display: false }, title: { display: true, text: 'Questions passed with grounding (of 86)' } }, scales: { y: { min: 0, max: 90 } } } });

chartPage('chart-grounding', { type: 'bar', data: { labels: ['E1', 'F1', 'F2', 'F3', 'G (Gemma)'],
  datasets: [{ label: 'With knowledge base', data: [32, 32, 32, 32, 32], backgroundColor: BLUE, labelSuffix: '' },
             { label: 'Without knowledge base', data: [9, 8, 9, 9, 6], backgroundColor: ORANGE, labelSuffix: '' }] },
  options: { plugins: { title: { display: true, text: '32 paired questions answered correctly' } }, scales: { y: { min: 0, max: 36 } } } });

// LLM/evaluation/results/claims/summary.md
chartPage('chart-verifier-versions', { type: 'bar', data: { labels: ['v1 (mutation estimate)', 'v2 (n=25)', 'v3 set 1 (n=31)', 'v3 set 2 (n=31)', 'v3 both (n=62)'],
  datasets: [{ data: [48, 60, 81, 74, 77], backgroundColor: [GREY, LIGHT, BLUE, BLUE, BLUE] }] },
  options: { indexAxis: 'y', plugins: { legend: { display: false }, title: { display: true, text: 'Pattern verifier: in-scope injected errors detected (%)' } }, scales: { x: { min: 0, max: 100 } } } }, 900, 360);

// LLM/evaluation/results/trace/dev-report.md (final prompt)
chartPage('chart-dev', { type: 'bar', data: { labels: ['Patterns (v3)', 'TRACE-rule', 'TRACE-model', 'TRACE-hybrid'],
  datasets: [{ label: 'Errors detected', data: [38, 43, 61, 69], backgroundColor: BLUE },
             { label: 'False alarms on paraphrases', data: [1, 1, 5, 7], backgroundColor: ORANGE }] },
  options: { plugins: { title: { display: true, text: 'Development sets: 183 errors, 182 paraphrases (%)' } }, scales: { y: { min: 0, max: 100 } } } });

// LLM/evaluation/results/trace/heldout-report.md
chartPage('chart-heldout', { type: 'bar', data: { labels: ['Patterns (v3)', 'TRACE-rule', 'TRACE-model', 'TRACE-hybrid', 'LLM judge (Gemini)', 'LLM judge (Gemma)', 'MiniCheck'],
  datasets: [{ label: 'Errors detected (of 102)', data: [15, 20, 65, 69, 78, 75, 37], backgroundColor: BLUE },
             { label: 'False alarms (of 103 paraphrases)', data: [2, 2, 3, 4, 17, 7, 21], backgroundColor: ORANGE }] },
  options: { plugins: { title: { display: true, text: 'Held-out test, written after TRACE was frozen (%)' } }, scales: { y: { min: 0, max: 100 } } } }, 950, 430);

chartPage('chart-errortype', { type: 'bar', data: { labels: ['Derived (15)', 'Existence (18)', 'Figure (26)', 'Permission (9)', 'Qualitative (20)', 'Rule (14)'],
  datasets: [{ label: 'TRACE-hybrid', data: [87, 50, 81, 22, 70, 79], backgroundColor: BLUE },
             { label: 'LLM judge (Gemini)', data: [73, 89, 77, 33, 85, 93], backgroundColor: GREY },
             { label: 'LLM judge (Gemma)', data: [67, 72, 77, 44, 75, 100], backgroundColor: GREEN }] },
  options: { plugins: { title: { display: true, text: 'Held-out errors detected by error type (%)' } }, scales: { y: { min: 0, max: 100 } } } }, 950, 430);

// LLM/evaluation/results/trace/natural/report.md
chartPage('chart-natural', { type: 'bar', data: { labels: ['Patterns (v3)', 'TRACE-hybrid', 'Gemini judge', 'Gemma judge (203 answers)', 'MiniCheck'],
  datasets: [{ label: 'Recall on the false sentences of the sample', data: [11, 21, 53, 79, 74], backgroundColor: BLUE },
             { label: 'Precision of flags', data: [100, 15, 24, 17, 8], backgroundColor: ORANGE }] },
  options: { plugins: { title: { display: true, text: "The assistant's own errors (%)" } }, scales: { y: { min: 0, max: 110 } } } }, 900, 420);

// LLM/evaluation/results/fpq-report.md (both models complete)
chartPage('chart-fpq', { type: 'bar', data: { labels: ['Verifier off', 'Patterns', 'TRACE'],
  datasets: [{ label: 'gemini-3.5-flash-lite (44 questions)', data: [89, 84, 93], backgroundColor: BLUE },
             { label: 'gemma-4-31b-it (44 questions)', data: [93, 93, 93], backgroundColor: GREEN }] },
  options: { plugins: { title: { display: true, text: 'False-premise questions: answers that rebut the premise (%)' } }, scales: { y: { min: 0, max: 100 } } } }, 900, 400);

// LLM/evaluation/results/trace/harm-report.md
chartPage('chart-harm', { type: 'bar', data: { labels: ['fixed-1 (patterns)', 'fixed-2 (patterns)', 'fixed-3 (patterns)', 'trace-1 (TRACE)'],
  datasets: [{ label: 'Questions passed (of 86)', data: [84, 86, 86, 84], backgroundColor: [BLUE, BLUE, BLUE, ORANGE], labelSuffix: '' }] },
  options: { plugins: { legend: { display: false }, title: { display: true, text: 'Harm check: the 86 evaluation questions with each verifier' } }, scales: { y: { min: 0, max: 90 } } } }, 900, 380);

// ---------------------------------------------------------------- Appendix: Gantt chart
(() => {
  // weeks of a 16-week semester; the repository's commit dates fix weeks 6-14 (5 Oct to 11 Nov 2026)
  const rows = [
    ['Topic, supervisor meeting, scope', 1, 2, 'plan'], ['Literature review (first 30 papers)', 2, 5, 'plan'],
    ['Requirements and system design', 3, 5, 'plan'], ['Phases 1-3: ERP core, PostgreSQL, analytics', 3, 6, 'plan'],
    ['Phases 4-7: AI assistant, grounding, insights, AI drafts', 6, 6, 'git'], ['Phase 8: evaluation, 86 questions x 3 runs', 6, 7, 'git'],
    ['Claim verifier and held-out tests; research paper', 7, 7, 'git'], ['Second model (Gemma); 31 further papers', 8, 9, 'git'],
    ['TRACE design, development sets, freeze', 9, 10, 'git'], ['Held-out test, baselines, natural errors', 10, 13, 'git'],
    ['Harm check, repeatability, journal paper', 13, 14, 'git'], ['Final report, poster, viva preparation', 14, 16, 'plan'],
  ];
  const meetings = [1, 2, 4, 6, 7, 9, 10];  // 03/09, 10/09, 24/09, 09/10, 16/10, 30/10 and 05/11/2026
  const cells = w => Array.from({ length: 16 }, (_, i) => i + 1).map(i => {
    const on = i >= w[1] && i <= w[2];
    return `<td style="border:1px solid #bbb;width:32px;height:22px;background:${on ? (w[3] === 'git' ? '#2f5597' : '#9dc3e6') : '#fff'}"></td>`;
  }).join('');
  page('fig-gantt', `<table style="border-collapse:collapse;font-size:16px">
   <tr><th style="border:1px solid #bbb;padding:4px 8px;text-align:left;background:#1f3b73;color:#fff">Task</th>${Array.from({ length: 16 }, (_, i) => `<th style="border:1px solid #bbb;background:#1f3b73;color:#fff;font-weight:normal">W${i + 1}</th>`).join('')}</tr>
   ${rows.map(r => `<tr><td style="border:1px solid #bbb;padding:4px 8px;white-space:nowrap">${r[0]}</td>${cells(r)}</tr>`).join('')}
   <tr><td style="border:1px solid #bbb;padding:4px 8px;font-weight:bold">Supervisory meetings</td>${Array.from({ length: 16 }, (_, i) => `<td style="border:1px solid #bbb;text-align:center;color:#c55a11;font-size:18px">${meetings.includes(i + 1) ? '●' : ''}</td>`).join('')}</tr>
  </table>
  <div style="margin-top:8px;font-size:15px"><span style="display:inline-block;width:14px;height:12px;background:#2f5597"></span> dated by the repository's commit history (week 1 = 31 Aug, week 6 = 5 Oct 2026)
  &nbsp;&nbsp;<span style="display:inline-block;width:14px;height:12px;background:#9dc3e6"></span> planned (before the repository, or still to come) &nbsp;&nbsp;<span style="color:#c55a11">●</span> supervisory meeting</div>`);
})();

console.log('figures written to', DIR);
