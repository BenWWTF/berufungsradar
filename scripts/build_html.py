#!/usr/bin/env python3
"""
Build the index.html for the Berufungsradar dashboard.

Reads:
  - dashboard_data_2025.json (the enriched data)
  - index.html (the template, with placeholders)

Generates:
  - index.html (replaces DATA array + JS functions)
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "dashboard_data_2025.json"
HTML_PATH = ROOT / "index.html"

# ─────────────────────────────────────────────────────────────────
# 1. Load data
# ─────────────────────────────────────────────────────────────────
with DATA_PATH.open() as f:
    DATA = json.load(f)


# ─────────────────────────────────────────────────────────────────
# 2. Generate the embedded DATA array
# ─────────────────────────────────────────────────────────────────
def data_to_js(d):
    """One entry → JS object literal (no trailing comma)."""
    fields = []
    for k, v in d.items():
        key = k
        if v is None:
            val = "null"
        elif isinstance(v, bool):
            val = "true" if v else "false"
        elif isinstance(v, (int, float)):
            val = str(v)
        elif isinstance(v, list):
            if not v:
                val = "[]"
            else:
                items = ", ".join(json.dumps(x, ensure_ascii=False) for x in v)
                val = f"[{items}]"
        elif isinstance(v, str):
            val = json.dumps(v, ensure_ascii=False)
        else:
            val = json.dumps(v, ensure_ascii=False)
        fields.append(f"        {key}: {val}")
    return "      {\n" + ",\n".join(fields) + "\n      }"


data_js = ",\n".join(data_to_js(d) for d in DATA)

# ─────────────────────────────────────────────────────────────────
# 3. Build the new <script> block
# ─────────────────────────────────────────────────────────────────
NEW_SCRIPT = r"""const MONATEN = ['JÄNNER','FEBRUAR','MÄRZ','APRIL','MAI','JUNI',
                 'JULI','AUGUST','SEPTEMBER','OKTOBER','NOVEMBER','DEZEMBER'];

const UNIS = ["TU Wien", "Uni Wien", "MedUni Wien",
              "WU Wien", "BOKU", "mdw", "Angewandte", "Vetmeduni Wien"];

const UNI_COLORS = {
  "TU Wien": "#003366",
  "Universität Wien": "#0055A4",
  "Medizinische Universität Wien": "#DC2626",
  "WU Wien": "#059669",
  "BOKU": "#84CC16",
  "mdw": "#7C3AED",
  "Angewandte": "#DB2777",
  "Vetmeduni Wien": "#D97706",
};

// ÖFOS Bereiche (1-stellig)
const OFOS_BEREICH = {
  1: { label: "Naturwissenschaften",   color: "#2563EB" },
  2: { label: "Technische Wiss.",      color: "#D97706" },
  3: { label: "Medizin & Gesundheit",  color: "#DC2626" },
  4: { label: "Agrar & Veterinärmed.", color: "#65A30D" },
  5: { label: "Sozialwissenschaften",  color: "#059669" },
  6: { label: "Geisteswissenschaften", color: "#7C3AED" },
};

const DATA = [
__DATA__
];

// ─── HELPERS ─────────────────────────────────────────────
function inferBereich(d) {
  return d.ofos_bereich_code || String(Math.floor(parseInt(d.ofos_code || 999) / 100));
}

function bereichColor(code) {
  return (OFOS_BEREICH[code] || {}).color || "#9CA3AF";
}

function bereichLabel(code) {
  return (OFOS_BEREICH[code] || {}).label || "Andere";
}

function uniColor(uni) {
  return UNI_COLORS[uni] || "#6B7280";
}

function parseMetrics(bio) {
  const m = {};
  if (!bio) return m;
  const h = bio.match(/h-Index:\s*(\d+)/i);
  const p = bio.match(/Publikationen:\s*(\d+)/i);
  const z = bio.match(/Zitierungen:\s*(\d+)/i);
  if (h) m.hIndex = parseInt(h[1]);
  if (p) m.pubs = parseInt(p[1]);
  if (z) m.cites = parseInt(z[1]);
  return m;
}

const TOOLTIP = document.getElementById("tooltip");
function showTooltip(html, event) {
  TOOLTIP.innerHTML = html;
  TOOLTIP.classList.add("visible");
  moveTooltip(event);
}
function moveTooltip(event) {
  const x = event.clientX + 14, y = event.clientY + 14;
  TOOLTIP.style.left = Math.min(x, window.innerWidth - 280) + "px";
  TOOLTIP.style.top  = Math.min(y, window.innerHeight - 120) + "px";
}
function hideTooltip() { TOOLTIP.classList.remove("visible"); }

// ─── KPI ROW ─────────────────────────────────────────────
function initKPIs() {
  const total = DATA.length;
  const frauen = DATA.filter(d => d.geschlecht === 'W').length;
  const maenner = DATA.filter(d => d.geschlecht === 'M').length;
  const extern = DATA.filter(d => d.art_berufung === '§98').length;
  const intern = DATA.filter(d => d.art_berufung === '§99(4)').length;

  document.getElementById("kpi-total").textContent = total;
  document.getElementById("kpi-total-sub").textContent =
    `${UNIS.length} Wiener Universitäten · 2025`;
  document.getElementById("kpi-frauen").textContent = frauen;
  document.getElementById("kpi-frauen-pct").textContent =
    Math.round(frauen / total * 100) + "% aller Berufungen";
  document.getElementById("kpi-maenner").textContent = maenner;
  document.getElementById("kpi-maenner-pct").textContent =
    Math.round(maenner / total * 100) + "% aller Berufungen";
  document.getElementById("kpi-extern").textContent = extern;
  document.getElementById("kpi-intern").textContent = intern;

  // Header badge
  document.getElementById("header-badge").textContent =
    `${total} Berufungen · ${UNIS.length} Universitäten`;
}

// ─── CHART: GENDER × UNI (stacked bar, all unis) ─────────
function initGenderChart() {
  const unis = UNIS;
  const frauen = unis.map(u => DATA.filter(d => d.universitat === u && d.geschlecht === 'W').length);
  const maenner = unis.map(u => DATA.filter(d => d.universitat === u && d.geschlecht === 'M').length);

  new Chart(document.getElementById("chart-gender"), {
    type: "bar",
    data: {
      labels: unis,
      datasets: [
        { label: "Frauen", data: frauen, backgroundColor: "#9D174D", borderRadius: 4 },
        { label: "Männer", data: maenner, backgroundColor: "#4C1D95", borderRadius: 4 }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: true,
      plugins: { legend: { position: "bottom" } },
      scales: { x: { stacked: true, ticks: { font: { size: 10 } } }, y: { stacked: true, ticks: { stepSize: 5 } } }
    }
  });
}

// ─── CHART: TIMELINE (by month) ──────────────────────────
function initTimelineChart() {
  const counts = MONATEN.map(m => DATA.filter(d => d.monat === m).length);
  new Chart(document.getElementById("chart-timeline"), {
    type: "bar",
    data: {
      labels: MONATEN.map(m => m.substring(0,3)),
      datasets: [{
        label: "Berufungen",
        data: counts,
        backgroundColor: "#0055A4",
        borderRadius: 4
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: true,
      plugins: { legend: { display: false } },
      scales: { y: { ticks: { stepSize: 1 } } }
    }
  });
}

// ─── CHART: ÖFOS BEREICH (1-stellig) ─────────────────────
function initBereichChart() {
  const counts = {};
  DATA.forEach(d => {
    const b = inferBereich(d);
    counts[b] = (counts[b] || 0) + 1;
  });
  const sorted = Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .map(([k, v]) => ({ key: k, label: bereichLabel(k), value: v, color: bereichColor(k) }));

  new Chart(document.getElementById("chart-bereich"), {
    type: "bar",
    data: {
      labels: sorted.map(e => e.label),
      datasets: [{
        label: "Anzahl Berufungen",
        data: sorted.map(e => e.value),
        backgroundColor: sorted.map(e => e.color),
        borderRadius: 4
      }]
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { x: { ticks: { stepSize: 1 } } }
    }
  });
}

// ─── HEATMAP: Universität × ÖFOS-Bereich ──────────────────
function initHeatmap() {
const container = document.getElementById("heatmap-container");
const W = container.clientWidth || 700;
const H = 380;
const margin = { top: 50, right: 30, bottom: 30, left: 130 };
  const innerW = W - margin.left - margin.right;
  const innerH = H - margin.top - margin.bottom;

  // Compute matrix
  const bereichKeys = Object.keys(OFOS_BEREICH).sort();
  const matrix = {};
  let max = 0;
  UNIS.forEach(u => {
    matrix[u] = {};
    bereichKeys.forEach(b => { matrix[u][b] = 0; });
  });
  DATA.forEach(d => {
    const u = d.universitat;
    const b = inferBereich(d);
    if (matrix[u] && matrix[u][b] !== undefined) {
      matrix[u][b]++;
      if (matrix[u][b] > max) max = matrix[u][b];
    }
  });

  const cellW = innerW / bereichKeys.length;
  const cellH = innerH / UNIS.length;

  // Color scale
  const colorScale = (v) => {
    if (v === 0) return "#F3F4F6";
    const t = v / Math.max(1, max);
    // Light blue to deep blue
    const r = Math.round(229 - t * 200);
    const g = Math.round(231 - t * 200);
    const b = Math.round(235 - t * 150);
    return `rgb(${r}, ${g}, ${b})`;
  };

  const svg = d3.select(container).append("svg")
    .attr("width", "100%").attr("height", H)
    .attr("viewBox", `0 0 ${W} ${H}`);

  const g = svg.append("g").attr("transform", `translate(${margin.left}, ${margin.top})`);

  // Cells
  UNIS.forEach((u, i) => {
    bereichKeys.forEach((b, j) => {
      const v = matrix[u][b];
      g.append("rect")
        .attr("class", "heatmap-cell")
        .attr("x", j * cellW).attr("y", i * cellH)
        .attr("width", cellW - 2).attr("height", cellH - 2)
        .attr("rx", 3)
        .attr("fill", colorScale(v))
        .on("mouseover", (event) => {
          showTooltip(
            `<strong>${u}</strong> · ${bereichLabel(b)}<br>${v} Berufung${v !== 1 ? 'en' : ''}`,
            event
          );
        })
        .on("mousemove", moveTooltip)
        .on("mouseout", hideTooltip);
      if (v > 0) {
        g.append("text")
          .attr("class", "heatmap-value")
          .attr("x", j * cellW + (cellW - 2) / 2)
          .attr("y", i * cellH + (cellH - 2) / 2 + 4)
          .attr("fill", v > max * 0.5 ? "white" : "#1A1A2E")
          .text(v);
      }
    });
  });

  // X labels (Bereich) — two lines: number + category name
  bereichKeys.forEach((b, j) => {
    g.append("text")
      .attr("class", "heatmap-label")
      .attr("x", j * cellW + (cellW - 2) / 2)
      .attr("y", -28)
      .attr("text-anchor", "middle")
      .attr("font-weight", "700")
      .attr("fill", bereichColor(b))
      .text(b);
    g.append("text")
      .attr("class", "heatmap-label")
      .attr("x", j * cellW + (cellW - 2) / 2)
      .attr("y", -12)
      .attr("text-anchor", "middle")
      .attr("font-size", "10px")
      .attr("fill", "#6B7280")
      .text(bereichLabel(b));
  });

  // Y labels (Uni)
  UNIS.forEach((u, i) => {
    g.append("text")
      .attr("class", "heatmap-label")
      .attr("x", -10)
      .attr("y", i * cellH + (cellH - 2) / 2 + 4)
      .attr("text-anchor", "end")
      .text(u.length > 18 ? u.replace("Universität Wien", "Uni Wien").replace("Medizinische Universität Wien", "MedUni") : u);
  });
}

// ─── CHART: ÖFOS 3-STELLIG TOP 15 ────────────────────────
function initOFOSChart() {
  const counts = {};
  DATA.forEach(d => {
    const lbl = d.ofos_label || "Andere";
    counts[lbl] = (counts[lbl] || 0) + 1;
  });
  const sorted = Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 15);

  new Chart(document.getElementById("chart-ofos"), {
    type: "bar",
    data: {
      labels: sorted.map(e => e[0]),
      datasets: [{
        label: "Anzahl",
        data: sorted.map(e => e[1]),
        backgroundColor: sorted.map(e => {
          const d = DATA.find(x => (x.ofos_label || "Andere") === e[0]);
          return d ? bereichColor(inferBereich(d)) : "#9CA3AF";
        }),
        borderRadius: 4
      }]
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { x: { ticks: { stepSize: 1 } } }
    }
  });
}

// ─── D3 SANKEY (Herkunft → Universität) ───────────────────
let sankeyInitialized = false;
function initSankey() {
  if (sankeyInitialized) return;
  sankeyInitialized = true;

  const container = document.getElementById("sankey-container");
  const W = container.clientWidth || 1000;
  const H = Math.max(600, W * 0.6);

  // Group origins
  // left = Herkunft (Land, oder "Intern"), right = Universität
  const nodeNames = [];
  const flows = {};

  DATA.forEach(d => {
    let origin;
    if (d.herkunft === "intern") {
      origin = "Intern (Wien)";
    } else if (d.herkunft_land) {
      origin = d.herkunft_land;
    } else {
      origin = "Herkunft unbekannt";
    }
    const dest = d.universitat;
    const key = `${origin}→${dest}`;
    flows[key] = flows[key] || { origin, dest, count: 0 };
    flows[key].count++;
    if (!nodeNames.includes(origin)) nodeNames.push(origin);
    if (!nodeNames.includes(dest)) nodeNames.push(dest);
  });

  const nodeIndex = {};
  nodeNames.forEach((n, i) => nodeIndex[n] = i);

  const nodes = nodeNames.map(n => ({ name: n }));
  const links = Object.values(flows).map(f => ({
    source: nodeIndex[f.origin],
    target: nodeIndex[f.dest],
    value: f.count
  }));

  const svg = d3.select(container).append("svg")
    .attr("width", "100%")
    .attr("height", H)
    .attr("viewBox", `0 0 ${W} ${H}`);

  const sankey = d3.sankey()
    .nodeWidth(24)
    .nodePadding(12)
    .extent([[10, 10], [W - 10, H - 20]]);

  const graph = sankey({
    nodes: nodes.map(d => Object.assign({}, d)),
    links: links.map(d => Object.assign({}, d))
  });

  // Origin colors
  const originColors = {
    "Intern (Wien)": "#92400E",
    "Herkunft unbekannt": "#9CA3AF",
  };

  // Links
  svg.append("g").selectAll("path")
    .data(graph.links)
    .join("path")
    .attr("d", d3.sankeyLinkHorizontal())
    .attr("fill", "none")
    .attr("stroke", d => originColors[d.source.name] || "#6B7280")
    .attr("stroke-width", d => Math.max(1, d.width))
    .attr("opacity", 0.35)
    .on("mouseover", (event, d) => {
      showTooltip(
        `<strong>${d.source.name}</strong> → <strong>${d.target.name}</strong><br>${d.value} Berufung${d.value > 1 ? "en" : ""}`,
        event
      );
    })
    .on("mousemove", moveTooltip)
    .on("mouseout", hideTooltip);

  // Nodes
  svg.append("g").selectAll("rect")
    .data(graph.nodes)
    .join("rect")
    .attr("x", d => d.x0)
    .attr("y", d => d.y0)
    .attr("height", d => Math.max(1, d.y1 - d.y0))
    .attr("width", d => d.x1 - d.x0)
    .attr("rx", 3)
    .attr("fill", d => originColors[d.name] || uniColor(d.name))
    .on("mouseover", (event, d) => showTooltip(
      `<strong>${d.name}</strong><br>${d.value} Berufung${d.value > 1 ? "en" : ""}`,
      event
    ))
    .on("mousemove", moveTooltip)
    .on("mouseout", hideTooltip);

  // Labels
  svg.append("g").selectAll("text")
    .data(graph.nodes)
    .join("text")
    .attr("x", d => d.x0 < W / 2 ? d.x1 + 8 : d.x0 - 8)
    .attr("y", d => (d.y1 + d.y0) / 2)
    .attr("dy", "0.35em")
    .attr("text-anchor", d => d.x0 < W / 2 ? "start" : "end")
    .attr("fill", "#1A1A2E")
    .attr("font-size", "13px")
    .attr("font-weight", "500")
    .text(d => `${d.name} (${d.value})`);
}

// ─── D3 FORCE GRAPH (colored by university) ──────────────
let forceInitialized = false;
function initForceGraph() {
  if (forceInitialized) return;
  forceInitialized = true;

  const container = document.getElementById("force-container");
  const W = container.clientWidth || 800;
  const H = 540;

  const nodes = DATA.map((d, i) => {
    const metrics = parseMetrics(d.bio_text);
    return {
      id: i,
      name: d.name,
      uni: d.universitat,
      research: d.forschungsbereich,
      ofos_code: d.ofos_code,
      bereich: inferBereich(d),
      h: metrics.hIndex || 0,
      r: 7 + (metrics.hIndex || 0) * 0.25
    };
  });

  const svg = d3.select(container).append("svg")
    .attr("width", "100%")
    .attr("height", H)
    .attr("viewBox", `0 0 ${W} ${H}`);

  // Group by ÖFOS Bereich (1-6) — 6 cluster centers
  const bereichCenters = {
    1: [W * 0.18, H * 0.32],
    2: [W * 0.78, H * 0.20],
    3: [W * 0.50, H * 0.78],
    4: [W * 0.20, H * 0.78],
    5: [W * 0.50, H * 0.20],
    6: [W * 0.82, H * 0.78],
  };

  const simulation = d3.forceSimulation(nodes)
    .force("charge", d3.forceManyBody().strength(-80))
    .force("collision", d3.forceCollide(d => d.r + 4))
    .force("x", d3.forceX(d => (bereichCenters[d.bereich] || [W*0.5, H*0.5])[0]).strength(0.45))
    .force("y", d3.forceY(d => (bereichCenters[d.bereich] || [W*0.5, H*0.5])[1]).strength(0.45));

  // Cluster labels (positioned at the very top of each cluster, with margin)
  const clusterLabels = [
    { key: 1, label: "1 — Naturwiss.",    cx: W*0.18, cy: H*0.10 },
    { key: 2, label: "2 — Technik",       cx: W*0.78, cy: H*0.06 },
    { key: 3, label: "3 — Medizin",       cx: W*0.50, cy: H*0.96 },
    { key: 4, label: "4 — Agrar/Vetmed.",  cx: W*0.20, cy: H*0.96 },
    { key: 5, label: "5 — Sozialwiss.",   cx: W*0.50, cy: H*0.06 },
    { key: 6, label: "6 — Geisteswiss.",  cx: W*0.82, cy: H*0.96 },
  ];
  svg.append("g").selectAll("text.cluster-lbl")
    .data(clusterLabels)
    .join("text")
    .attr("x", d => d.cx).attr("y", d => d.cy)
    .attr("text-anchor", "middle")
    .attr("fill", d => bereichColor(d.key))
    .attr("font-size", "12px")
    .attr("font-weight", "700")
    .attr("opacity", 0.7)
    .text(d => d.label);

  const circle = svg.append("g").selectAll("circle")
    .data(nodes)
    .join("circle")
    .attr("r", d => d.r)
    .attr("fill", d => uniColor(d.uni))
    .attr("stroke", "#fff")
    .attr("stroke-width", 1.5)
    .attr("opacity", 0.82)
    .style("cursor", "pointer")
    .on("mouseover", (event, d) => {
      showTooltip(
        `<strong>${d.name}</strong><br>${d.uni}<br><em>${d.research}</em><br>ÖFOS: ${bereichLabel(d.bereich)}` +
        (d.h ? `<br>h-Index: ${d.h}` : ""),
        event
      );
      d3.select(event.currentTarget).attr("stroke", "#003366").attr("stroke-width", 2.5);
    })
    .on("mousemove", moveTooltip)
    .on("mouseout", (event) => {
      hideTooltip();
      d3.select(event.currentTarget).attr("stroke", "#fff").attr("stroke-width", 1.5);
    })
    .on("click", (event, d) => {
      switchTab("alle");
      setTimeout(() => {
        document.getElementById("search-input").value = d.name;
        applyFilters();
      }, 80);
    })
    .call(d3.drag()
      .on("start", (event, d) => { if (!event.active) simulation.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; })
      .on("drag",  (event, d) => { d.fx=event.x; d.fy=event.y; })
      .on("end",   (event, d) => { if (!event.active) simulation.alphaTarget(0); d.fx=null; d.fy=null; })
    );

  simulation.on("tick", () => {
    circle
      .attr("cx", d => Math.max(d.r, Math.min(W - d.r, d.x)))
      .attr("cy", d => Math.max(d.r, Math.min(H - d.r, d.y)));
  });

  // Legend: by university
  const legendEl = document.getElementById("force-legend");
  const entries = UNIS.map(u => ({ label: u, color: uniColor(u) }));
  legendEl.innerHTML = entries.map(e =>
    `<div class="legend-item"><div class="legend-dot" style="background:${e.color}"></div>${e.label}</div>`
  ).join("");
}

// ─── OVERLAP MATRIX: Uni × Uni ────────────────────────────
let overlapInitialized = false;
function initOverlapMatrix() {
  if (overlapInitialized) return;
  overlapInitialized = true;

  const container = document.getElementById("overlap-container");
  const W = container.clientWidth || 600;
  const H = 480;
  const size = 50;
  const labelOffset = 130;
  const margin = { top: labelOffset, left: labelOffset };
  const innerW = W - margin.left - 20;
  const innerH = H - margin.top - 20;
  const cell = Math.min(innerW / UNIS.length, innerH / UNIS.length, size);

  // Compute overlap = number of shared 3-stellige ÖFOS codes between two unis
  const ofosByUni = {};
  UNIS.forEach(u => { ofosByUni[u] = new Set(); });
  DATA.forEach(d => {
    if (ofosByUni[d.universitat] && d.ofos_code) {
      ofosByUni[d.universitat].add(d.ofos_code);
    }
  });

  const overlap = {};
  let max = 0;
  UNIS.forEach(a => {
    overlap[a] = {};
    UNIS.forEach(b => {
      if (a === b) {
        overlap[a][b] = ofosByUni[a].size; // self = total
      } else {
        const inter = new Set([...ofosByUni[a]].filter(x => ofosByUni[b].has(x)));
        overlap[a][b] = inter.size;
        if (inter.size > max) max = inter.size;
      }
    });
  });

  const svg = d3.select(container).append("svg")
    .attr("width", "100%")
    .attr("height", H)
    .attr("viewBox", `0 0 ${W} ${H}`);

  const g = svg.append("g").attr("transform", `translate(${margin.left}, ${margin.top})`);

  // Cells
  UNIS.forEach((a, i) => {
    UNIS.forEach((b, j) => {
      const v = overlap[a][b];
      const t = v / Math.max(1, max);
      const r = Math.round(243 - t * 200);
      const gr = Math.round(244 - t * 200);
      const bl = Math.round(246 - t * 100);
      g.append("rect")
        .attr("class", "overlap-cell")
        .attr("x", j * cell)
        .attr("y", i * cell)
        .attr("width", cell - 2)
        .attr("height", cell - 2)
        .attr("rx", 3)
        .attr("fill", v === 0 ? "#F9FAFB" : `rgb(${r}, ${gr}, ${bl})`)
        .on("mouseover", (event) => {
          const text = a === b
            ? `${a}: ${v} ÖFOS-3-Steller insgesamt`
            : `${a} ↔ ${b}: ${v} ÖFOS-3-Steller gemeinsam`;
          showTooltip(text, event);
        })
        .on("mousemove", moveTooltip)
        .on("mouseout", hideTooltip);

      if (v > 0) {
        g.append("text")
          .attr("class", "overlap-label")
          .attr("x", j * cell + cell / 2)
          .attr("y", i * cell + cell / 2 + 4)
          .attr("text-anchor", "middle")
          .attr("fill", v > max * 0.5 ? "white" : "#1A1A2E")
          .text(v);
      }
    });
  });

  // X labels (top)
  UNIS.forEach((u, j) => {
    const text = u.length > 12 ? u.replace("Universität Wien", "Uni Wien").replace("Medizinische Universität Wien", "MedUni") : u;
    g.append("text")
      .attr("class", "overlap-label")
      .attr("x", j * cell + cell / 2)
      .attr("y", -10)
      .attr("text-anchor", "start")
      .attr("transform", `rotate(-45, ${j * cell + cell / 2}, -10)`)
      .attr("fill", uniColor(u))
      .text(text);
  });

  // Y labels (left)
  UNIS.forEach((u, i) => {
    g.append("text")
      .attr("class", "overlap-label")
      .attr("x", -10)
      .attr("y", i * cell + cell / 2 + 4)
      .attr("text-anchor", "end")
      .attr("fill", uniColor(u))
      .text(u);
  });
}

// ─── PROFESSOR CARDS ─────────────────────────────────────
function badgeArt(art) {
  if (art === "§98")    return `<span class="badge badge-98">§98 Univ.Prof</span>`;
  if (art === "§99(4)") return `<span class="badge badge-99">§99 Abs. 4</span>`;
  if (art === "§99(1)") return `<span class="badge badge-99">§99 Abs. 1</span>`;
  if (art && art.startsWith("§99(5)")) return `<span class="badge badge-99">§99 Abs. 5 BEST</span>`;
  return `<span class="badge badge-unk">Unbekannt</span>`;
}
function badgeGeschlecht(g) {
  if (g === "W") return `<span class="badge badge-f">Frau</span>`;
  if (g === "M") return `<span class="badge badge-m">Mann</span>`;
  return "";
}
function badgeHerkunft(h, inst, land) {
  if (h === "intern") {
    const tail = inst ? `: ${inst.length > 25 ? inst.substring(0, 25) + "…" : inst}` : "";
    return `<span class="badge badge-intern" title="${inst || ''}">Intern${tail}</span>`;
  }
  if (h === "extern") {
    return `<span class="badge badge-extern" title="${inst || ''}${land ? ', ' + land : ''}">Extern${land ? ' (' + land + ')' : ''}</span>`;
  }
  return `<span class="badge badge-unk">Herkunft unbekannt</span>`;
}

function renderCards(data) {
  const grid = document.getElementById("cards-grid");
  document.getElementById("filter-count").textContent =
    `${data.length} von ${DATA.length} Einträgen`;

  if (data.length === 0) {
    grid.innerHTML = '<div style="padding:40px; text-align:center; color:var(--muted); grid-column:1/-1">Keine Einträge gefunden.</div>';
    return;
  }

  grid.innerHTML = data.map((d, i) => {
    const metrics = parseMetrics(d.bio_text);
    const bioPreview = d.bio_text
      ? d.bio_text.replace(/h-Index:[^|]+\|[^|]+\|[^|]+/i, '').trim().substring(0, 200)
      : '';
    const metricsHtml = (metrics.hIndex || metrics.pubs)
      ? `<div class="card-metrics">
          ${metrics.hIndex ? `<span>h-Index: <strong>${metrics.hIndex}</strong></span>` : ''}
          ${metrics.pubs   ? `<span>Publ.: <strong>${metrics.pubs}</strong></span>` : ''}
          ${metrics.cites  ? `<span>Zit.: <strong>${metrics.cites.toLocaleString('de-AT')}</strong></span>` : ''}
        </div>` : '';

    const ofosBadge = d.ofos_label
      ? `<span class="badge badge-ofos" title="${bereichLabel(inferBereich(d))}">${d.ofos_label}</span>`
      : '';

    const herkunftDetail = d.herkunft_institution
      ? `<div class="card-bio" style="margin-top:4px">Von: ${d.herkunft_institution}${d.herkunft_land ? ', ' + d.herkunft_land : ''}</div>`
      : '';

    return `
    <div class="prof-card" id="card-${i}">
      <div class="card-header">
        <div class="card-name">${d.name}</div>
        <div class="card-meta">${d.universitat} · ${d.monat} ${d.year}${d.fakultat_institut ? ' · ' + d.fakultat_institut : ''}</div>
      </div>
      <div class="card-body">
        <div class="card-research">${d.forschungsbereich}</div>
        <div class="badges">
          ${badgeArt(d.art_berufung)}
          ${badgeGeschlecht(d.geschlecht)}
          ${badgeHerkunft(d.herkunft, d.herkunft_institution, d.herkunft_land)}
          ${ofosBadge}
        </div>
        ${metricsHtml}
        ${bioPreview ? `<div class="card-bio">${bioPreview}${d.bio_text.length > 200 ? '…' : ''}</div>` : ''}
        ${herkunftDetail}
        <div class="card-footer">
          <button class="card-expand-btn" onclick="toggleWerdegang(this, ${i})">▶ Werdegang anzeigen</button>
          ${d.profil_url ? `<a class="card-link" href="${d.profil_url}" target="_blank" rel="noopener">Profil →</a>` : ''}
        </div>
        <div class="card-werdegang" id="wg-${i}">${d.werdegang || 'Keine weiteren Angaben.'}</div>
      </div>
    </div>`;
  }).join('');
}

function toggleWerdegang(btn, i) {
  const el = document.getElementById(`wg-${i}`);
  const open = el.classList.toggle('open');
  btn.textContent = open ? '▼ Werdegang ausblenden' : '▶ Werdegang anzeigen';
}

// ─── FILTER LOGIC ────────────────────────────────────────
function applyFilters() {
  const q       = document.getElementById('search-input').value.toLowerCase();
  const uni     = document.getElementById('filter-uni').value;
  const gesch   = document.getElementById('filter-geschlecht').value;
  const herk    = document.getElementById('filter-herkunft').value;
  const art     = document.getElementById('filter-art').value;
  const bereich = document.getElementById('filter-bereich').value;
  const land    = document.getElementById('filter-land').value;

  const filtered = DATA.filter(d => {
    if (q && !JSON.stringify(d).toLowerCase().includes(q)) return false;
    if (uni && d.universitat !== uni) return false;
    if (gesch && d.geschlecht !== gesch) return false;
    if (herk && d.herkunft !== herk) return false;
    if (art && d.art_berufung !== art) return false;
    if (bereich && String(inferBereich(d)) !== bereich) return false;
    if (land && d.herkunft_land !== land) return false;
    return true;
  });
  renderCards(filtered);
}

function resetFilters() {
  document.getElementById('search-input').value = '';
  document.getElementById('filter-uni').value = '';
  document.getElementById('filter-geschlecht').value = '';
  document.getElementById('filter-herkunft').value = '';
  document.getElementById('filter-art').value = '';
  document.getElementById('filter-bereich').value = '';
  document.getElementById('filter-land').value = '';
  renderCards(DATA);
}

function populateLandFilter() {
  const sel = document.getElementById('filter-land');
  const laender = new Set();
  DATA.forEach(d => { if (d.herkunft_land) laender.add(d.herkunft_land); });
  // Sort: Österreich first, then alphabetical
  const sorted = Array.from(laender).sort((a, b) => {
    if (a === "Österreich") return -1;
    if (b === "Österreich") return 1;
    return a.localeCompare(b, "de");
  });
  sorted.forEach(l => {
    const opt = document.createElement("option");
    opt.value = l;
    opt.textContent = l;
    sel.appendChild(opt);
  });
}

// ─── TAB SWITCHING ───────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll('.tab-panel').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));

  document.getElementById(`tab-${name}`).classList.add('active');
  document.querySelectorAll('.tab-btn').forEach(btn => {
    if (btn.getAttribute('onclick').includes(`'${name}'`)) btn.classList.add('active');
  });

  if (name === 'mobilitaet') initSankey();
  if (name === 'cluster') { initForceGraph(); initOverlapMatrix(); }
  if (name === 'alle') renderCards(DATA);
}

// ─── INIT ────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initKPIs();
  initGenderChart();
  initTimelineChart();
  initBereichChart();
  initOFOSChart();
  initHeatmap();
  populateLandFilter();
  renderCards(DATA);
});
"""

# Replace placeholder
NEW_SCRIPT_FINAL = NEW_SCRIPT.replace("__DATA__", data_js)

# ─────────────────────────────────────────────────────────────────
# 4. Read current HTML and replace script + data
# ─────────────────────────────────────────────────────────────────
with HTML_PATH.open() as f:
    html = f.read()

# Find the <script> tag opening
m = re.search(r"<script>\s*\n", html)
if not m:
    raise SystemExit("No <script> tag found in index.html")
start = m.end()

# Find the </script> closing
m2 = re.search(r"</script>\s*</body>", html)
if not m2:
    raise SystemExit("No </script> closing tag found")
end = m2.start()

new_html = html[:start] + NEW_SCRIPT_FINAL + "\n" + html[end:]

with HTML_PATH.open("w") as f:
    f.write(new_html)

print(f"✓ Built {HTML_PATH} ({len(new_html)} bytes)")
print(f"  DATA entries: {len(DATA)}")
