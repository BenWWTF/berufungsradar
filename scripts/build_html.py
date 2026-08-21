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

const UNIS = ["TU Wien", "Uni Wien", "MedUni Wien", "WU Wien",
              "BOKU", "mdw", "Angewandte", "Akademie", "Vetmeduni Wien"];

const UNI_COLORS = {
  "TU Wien": "#003366",
  "Uni Wien": "#0055A4",
  "MedUni Wien": "#DC2626",
  "WU Wien": "#059669",
  "BOKU": "#84CC16",
  "mdw": "#7C3AED",
  "Angewandte": "#DB2777",
  "Akademie": "#0D9488",
  "Vetmeduni Wien": "#D97706",
};

// WWTF-Programmfelder (heuristische ÖFOS-Zuordnung, siehe scripts/wwtf_enrich.py)
const WWTF_PROG = {
  LS:  { label: "Life Sciences", color: "#DC2626",
         desc: "Biologie, Grundlagen- & klinische Medizin, Biotechnologie, Veterinärmedizin" },
  ICT: { label: "Information & Communication Technology", color: "#2563EB",
         desc: "Informatik, Elektrotechnik, KI, Maschinelles Lernen" },
  CS:  { label: "Cognitive Sciences", color: "#7C3AED",
         desc: "Psychologie, Neurowissenschaften, Kognition" },
  ESR: { label: "Environmental Systems Research", color: "#059669",
         desc: "Umweltsysteme, Ökologie, Wasser, Agrar- & Waldforschung" },
  DH:  { label: "Digital Humanism", color: "#D97706",
         desc: "Digitalisierung & Gesellschaft, Mensch-Maschine-Interaktion, KI-Ethik" },
  MA:  { label: "Mathematik und …", color: "#0891B2",
         desc: "Mathematik in Verbindung mit Anwendungsfeldern" },
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

// ─── JAHRES-SCOPE ────────────────────────────────────────
const YEARS = [...new Set(DATA.map(d => d.year))].sort((a, b) => a - b);
const YEAR_COLORS = ["#0055A4", "#D97706", "#059669", "#7C3AED", "#DC2626", "#0891B2"];
let SELECTED_YEARS = new Set(YEARS);
let VIEW = DATA.slice();

function selectedYears() { return YEARS.filter(y => SELECTED_YEARS.has(y)); }
function yearColor(y)    { return YEAR_COLORS[YEARS.indexOf(y) % YEAR_COLORS.length]; }
function uniCount(rows)  { return new Set(rows.map(d => d.universitat)).size; }
function plural(n, ein, mehr) { return `${n} ${n === 1 ? ein : mehr}`; }

function yearLabel() {
  const ys = selectedYears();
  if (!ys.length) return "keine Auswahl";
  if (ys.length === 1) return String(ys[0]);
  const lueckenlos = ys[ys.length - 1] - ys[0] + 1 === ys.length;
  return lueckenlos ? `${ys[0]}–${ys[ys.length - 1]}` : ys.join(", ");
}

// Chart.js-Instanzen müssen vor dem Neuzeichnen zerstört werden
const CHARTS = {};
function mountChart(key, canvasId, config) {
  if (CHARTS[key]) CHARTS[key].destroy();
  CHARTS[key] = new Chart(document.getElementById(canvasId), config);
}

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

// Strukturierte Metriken (aus wwtf_enrich.py), Fallback: bio_text-Regex
function metricsOf(d) {
  const m = {};
  if (d.h_index != null) m.hIndex = d.h_index;
  if (d.publikationen != null) m.pubs = d.publikationen;
  if (d.zitierungen != null) m.cites = d.zitierungen;
  if (m.hIndex != null || m.pubs != null) return m;
  const bio = d.bio_text;
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
function initKPIs(rows) {
  const total = rows.length;
  const frauen = rows.filter(d => d.geschlecht === 'W').length;
  const maenner = rows.filter(d => d.geschlecht === 'M').length;
  const extern = rows.filter(d => d.art_berufung === '§98').length;
  const intern = rows.filter(d => d.art_berufung === '§99(4)').length;

  document.getElementById("kpi-total").textContent = total;
  document.getElementById("kpi-total-sub").textContent =
    `${uniCount(rows)} Wiener Universitäten · ${yearLabel()}`;
  const pct = v => total ? Math.round(v / total * 100) + "% aller Berufungen" : "–";
  document.getElementById("kpi-frauen").textContent = frauen;
  document.getElementById("kpi-frauen-pct").textContent = pct(frauen);
  document.getElementById("kpi-maenner").textContent = maenner;
  document.getElementById("kpi-maenner-pct").textContent = pct(maenner);
  document.getElementById("kpi-extern").textContent = extern;
  document.getElementById("kpi-intern").textContent = intern;

  // Header badge
  document.getElementById("header-badge").textContent =
    `${plural(total, 'Berufung', 'Berufungen')} · ` +
    `${plural(uniCount(rows), 'Universität', 'Universitäten')} · ${yearLabel()}`;
}

// ─── CHART: GENDER × UNI (stacked bar, all unis) ─────────
function initGenderChart(rows) {
  const unis = UNIS;
  const frauen = unis.map(u => rows.filter(d => d.universitat === u && d.geschlecht === 'W').length);
  const maenner = unis.map(u => rows.filter(d => d.universitat === u && d.geschlecht === 'M').length);

  mountChart("gender", "chart-gender", {
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
function initTimelineChart(rows) {
  const ys = selectedYears();
  const datasets = ys.map(y => ({
    label: String(y),
    data: MONATEN.map(m => rows.filter(d => d.year === y && d.monat === m).length),
    backgroundColor: ys.length === 1 ? "#0055A4" : yearColor(y),
    borderRadius: 4
  }));
  mountChart("timeline", "chart-timeline", {
    type: "bar",
    data: { labels: MONATEN.map(m => m.substring(0,3)), datasets },
    options: {
      responsive: true, maintainAspectRatio: true,
      plugins: { legend: { display: ys.length > 1, position: "bottom" } },
      scales: { y: { ticks: { stepSize: 1 } } }
    }
  });
}

// ─── CHART: BERUFUNGEN PRO JAHR (nur bei Mehrjahresauswahl) ─
function initYearChart(rows) {
  const card = document.getElementById("card-years");
  const ys = selectedYears();
  if (ys.length < 2) {
    card.style.display = "none";
    if (CHARTS.years) { CHARTS.years.destroy(); delete CHARTS.years; }
    return;
  }
  card.style.display = "";
  mountChart("years", "chart-years", {
    type: "bar",
    data: {
      labels: ys.map(String),
      datasets: [{
        label: "Berufungen",
        data: ys.map(y => rows.filter(d => d.year === y).length),
        backgroundColor: ys.map(yearColor),
        borderRadius: 4
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { ticks: { stepSize: 1 } } }
    }
  });
}

// ─── CHART: ÖFOS BEREICH (1-stellig) ─────────────────────
function initBereichChart(rows) {
  const counts = {};
  rows.forEach(d => {
    const b = inferBereich(d);
    counts[b] = (counts[b] || 0) + 1;
  });
  const sorted = Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .map(([k, v]) => ({ key: k, label: bereichLabel(k), value: v, color: bereichColor(k) }));

  mountChart("bereich", "chart-bereich", {
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
function initHeatmap(rows) {
const container = document.getElementById("heatmap-container");
container.innerHTML = "";
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
  rows.forEach(d => {
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
function initOFOSChart(rows) {
  const counts = {};
  rows.forEach(d => {
    const lbl = d.ofos_label || "Andere";
    counts[lbl] = (counts[lbl] || 0) + 1;
  });
  const sorted = Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 15);

  mountChart("ofos", "chart-ofos", {
    type: "bar",
    data: {
      labels: sorted.map(e => e[0]),
      datasets: [{
        label: "Anzahl",
        data: sorted.map(e => e[1]),
        backgroundColor: sorted.map(e => {
          const d = rows.find(x => (x.ofos_label || "Andere") === e[0]);
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
function initSankey(rows) {
  const container = document.getElementById("sankey-container");
  container.innerHTML = "";
  const W = container.clientWidth || 1000;
  const H = Math.max(600, W * 0.6);

  // Group origins
  // left = Herkunft (Land, oder "Intern"), right = Universität
  const nodeNames = [];
  const flows = {};

  rows.forEach(d => {
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

// ─── PROFESSOR CARDS ─────────────────────────────────────
function badgeArt(art) {
  if (art === "§98")    return `<span class="badge badge-98">§98 Univ.Prof</span>`;
  if (art === "§99(4)") return `<span class="badge badge-99">§99 Abs. 4</span>`;
  if (art === "§99(1)") return `<span class="badge badge-99">§99 Abs. 1</span>`;
  if (art && art.startsWith("§99(5)")) return `<span class="badge badge-99">§99 Abs. 5 BEST</span>`;
  return `<span class="badge badge-unk">Unbekannt</span>`;
}
function badgeGeschlecht(g) {
  if (g === "W") return `<span class="badge badge-f">f</span>`;
  if (g === "M") return `<span class="badge badge-m">m</span>`;
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
    `${data.length} von ${VIEW.length} Einträgen`;

  if (data.length === 0) {
    grid.innerHTML = '<div style="padding:40px; text-align:center; color:var(--muted); grid-column:1/-1">Keine Einträge gefunden.</div>';
    return;
  }

  grid.innerHTML = data.map((d, i) => {
    const metrics = metricsOf(d);
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

    const wwtfBadges = (d.wwtf_programme || []).map(p =>
      `<span class="badge badge-grant" title="${WWTF_PROG[p].desc}">WWTF: ${WWTF_PROG[p].label}</span>`
    ).join('');

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
          ${wwtfBadges}
        </div>
        ${metricsHtml}
        ${bioPreview ? `<div class="card-bio">${bioPreview}${d.bio_text.length > 200 ? '…' : ''}</div>` : ''}
        ${herkunftDetail}
        <div class="card-footer">
          ${d.werdegang
            ? `<button class="card-expand-btn" onclick="toggleWerdegang(this, ${i})">▶ Werdegang anzeigen</button>`
            : `<span style="font-size:0.75rem;color:var(--muted)">Kein Werdegang erfasst</span>`}
          ${d.profil_url ? `<a class="card-link" href="${d.profil_url}" target="_blank" rel="noopener">${d.profil_url_auto ? 'OpenAlex' : 'Profil'} →</a>` : ''}
        </div>
        ${d.werdegang ? `<div class="card-werdegang" id="wg-${i}">${d.werdegang}</div>` : ''}
      </div>
    </div>`;
  }).join('');
}

function toggleWerdegang(btn, i) {
  const el = document.getElementById(`wg-${i}`);
  const open = el.classList.toggle('open');
  btn.textContent = open ? '▼ Werdegang ausblenden' : '▶ Werdegang anzeigen';
}

// ─── FILTER + SORT + URL-STATE ───────────────────────────
const FILTER_IDS = ['search-input','filter-uni','filter-geschlecht','filter-herkunft',
                    'filter-art','filter-bereich','filter-land','filter-wwtf','sort-select'];

function currentFilteredData() {
  const q       = document.getElementById('search-input').value.toLowerCase();
  const uni     = document.getElementById('filter-uni').value;
  const gesch   = document.getElementById('filter-geschlecht').value;
  const herk    = document.getElementById('filter-herkunft').value;
  const art     = document.getElementById('filter-art').value;
  const bereich = document.getElementById('filter-bereich').value;
  const land    = document.getElementById('filter-land').value;
  const wwtf    = document.getElementById('filter-wwtf').value;
  const sort    = document.getElementById('sort-select').value;

  const filtered = VIEW.filter(d => {
    if (q && !JSON.stringify(d).toLowerCase().includes(q)) return false;
    if (uni && d.universitat !== uni) return false;
    if (gesch && d.geschlecht !== gesch) return false;
    if (herk && d.herkunft !== herk) return false;
    if (art && d.art_berufung !== art) return false;
    if (bereich && String(inferBereich(d)) !== bereich) return false;
    if (land && d.herkunft_land !== land) return false;
    if (wwtf === 'keins') { if ((d.wwtf_programme || []).length) return false; }
    else if (wwtf && !(d.wwtf_programme || []).includes(wwtf)) return false;
    return true;
  });

  const by = {
    monat:  (a, b) => MONATEN.indexOf(a.monat) - MONATEN.indexOf(b.monat),
    name:   (a, b) => a.name.localeCompare(b.name, 'de'),
    hindex: (a, b) => (metricsOf(b).hIndex || -1) - (metricsOf(a).hIndex || -1),
    uni:    (a, b) => UNIS.indexOf(a.universitat) - UNIS.indexOf(b.universitat),
  };
  return filtered.slice().sort(by[sort] || by.monat);
}

function applyFilters() {
  renderCards(currentFilteredData());
  writeStateToHash();
}

function resetFilters() {
  FILTER_IDS.forEach(id => {
    const el = document.getElementById(id);
    el.value = id === 'sort-select' ? 'monat' : '';
  });
  applyFilters();
}

// Filterzustand in der URL — teilbare Links (#tab=alle&uni=TU+Wien…)
function writeStateToHash() {
  const p = new URLSearchParams();
  const tab = document.querySelector('.tab-panel.active');
  if (tab && tab.id !== 'tab-uebersicht') p.set('tab', tab.id.replace('tab-', ''));
  FILTER_IDS.forEach(id => {
    const v = document.getElementById(id).value;
    if (v && !(id === 'sort-select' && v === 'monat')) p.set(id, v);
  });
  if (SELECTED_YEARS.size !== YEARS.length) p.set('years', selectedYears().join(','));
  history.replaceState(null, '', p.toString() ? '#' + p.toString() : location.pathname);
}

function restoreStateFromHash() {
  if (!location.hash) return;
  const p = new URLSearchParams(location.hash.slice(1));
  const years = (p.get('years') || '').split(',').map(Number).filter(y => YEARS.includes(y));
  if (years.length) SELECTED_YEARS = new Set(years);
  FILTER_IDS.forEach(id => {
    if (p.has(id)) document.getElementById(id).value = p.get(id);
  });
  const tab = p.get('tab');
  if (tab && document.getElementById('tab-' + tab)) {
    document.querySelectorAll('.tab-panel').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(btn => {
      const on = btn.getAttribute('onclick').includes(`'${tab}'`);
      btn.classList.toggle('active', on);
      btn.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    document.getElementById('tab-' + tab).classList.add('active');
  }
}

// ─── CSV-EXPORT (gefilterte Ansicht, Excel-AT-kompatibel) ─
function exportCSV() {
  const cols = [
    ['Name', d => d.name],
    ['Universität', d => d.universitat],
    ['Institut', d => d.fakultat_institut || d.fakultat || ''],
    ['Forschungsbereich', d => d.forschungsbereich || ''],
    ['Art der Berufung', d => d.art_berufung || ''],
    ['Geschlecht', d => d.geschlecht || ''],
    ['Herkunft', d => d.herkunft || ''],
    ['Herkunftsinstitution', d => d.herkunft_institution || ''],
    ['Herkunftsland', d => d.herkunft_land || ''],
    ['ÖFOS-Code', d => d.ofos_code || ''],
    ['ÖFOS-Bezeichnung', d => d.ofos_label || ''],
    ['WWTF-Programmfelder', d => (d.wwtf_programme || []).map(p => WWTF_PROG[p].label).join(', ')],
    ['h-Index', d => metricsOf(d).hIndex ?? ''],
    ['Publikationen', d => metricsOf(d).pubs ?? ''],
    ['Zitierungen', d => metricsOf(d).cites ?? ''],
    ['Monat', d => d.monat || ''],
    ['Jahr', d => d.year || ''],
    ['Profil-URL', d => d.profil_url || ''],
  ];
  const esc = v => {
    const s = String(v);
    return /[";\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  };
  const rows = currentFilteredData();
  const csv = [cols.map(c => c[0]).join(';')]
    .concat(rows.map(d => cols.map(c => esc(c[1](d))).join(';')))
    .join('\r\n');
  // BOM, damit Excel Umlaute korrekt liest
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `berufungsradar_wien_${yearLabel().replace(/[^0-9]+/g, '_')}_${rows.length}_eintraege.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
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

// ─── WWTF-PERSPEKTIVE ────────────────────────────────────
function median(arr) {
  if (!arr.length) return null;
  const s = arr.slice().sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : Math.round((s[mid - 1] + s[mid]) / 2);
}

function initWWTF(rows) {
  const inProg = rows.filter(d => (d.wwtf_programme || []).length > 0);
  const gesamt = Math.max(1, rows.length);
  document.getElementById('wwtf-intro-year').textContent = yearLabel();
  document.getElementById('wwtf-prog-title').textContent =
    `Berufungen ${yearLabel()} nach WWTF-Programmfeld`;
  const extern = inProg.filter(d => d.herkunft === 'extern');
  const ausland = extern.filter(d => d.herkunft_land && d.herkunft_land !== 'Österreich');
  const frauen = inProg.filter(d => d.geschlecht === 'W');
  const hs = inProg.map(d => metricsOf(d).hIndex).filter(h => h != null);

  document.getElementById('kpi-wwtf-total').textContent = inProg.length;
  document.getElementById('kpi-wwtf-total-sub').textContent =
    `von ${rows.length} Berufungen (${Math.round(inProg.length / gesamt * 100)}%)`;
  document.getElementById('kpi-wwtf-extern').textContent = extern.length;
  document.getElementById('kpi-wwtf-extern-sub').textContent =
    `davon ${ausland.length} aus dem Ausland`;
  document.getElementById('kpi-wwtf-frauen').textContent =
    Math.round(frauen.length / Math.max(1, inProg.length) * 100) + '%';
  document.getElementById('kpi-wwtf-hindex').textContent = median(hs) ?? '–';
  document.getElementById('kpi-wwtf-hindex-sub').textContent =
    `${hs.length} von ${inProg.length} mit OpenAlex-Metriken`;

  // Balkendiagramm pro Programmfeld
  const progKeys = Object.keys(WWTF_PROG);
  const counts = progKeys.map(p => inProg.filter(d => d.wwtf_programme.includes(p)).length);
  mountChart("wwtfProg", "chart-wwtf-prog", {
    type: 'bar',
    data: {
      labels: progKeys.map(p => WWTF_PROG[p].label),
      datasets: [{
        data: counts,
        backgroundColor: progKeys.map(p => WWTF_PROG[p].color),
        borderRadius: 4
      }]
    },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { x: { ticks: { stepSize: 2 } } }
    }
  });

  // Programmfeld-Karten mit Personen-Chips
  const grid = document.getElementById('prog-grid');
  grid.innerHTML = progKeys.map(p => {
    const people = inProg
      .filter(d => d.wwtf_programme.includes(p))
      .sort((a, b) => (metricsOf(b).hIndex || -1) - (metricsOf(a).hIndex || -1));
    if (!people.length) return '';
    const chips = people.map(d => {
      const h = metricsOf(d).hIndex;
      const herk = d.herkunft === 'extern'
        ? (d.herkunft_land && d.herkunft_land !== 'Österreich' ? d.herkunft_land : 'extern (AT)')
        : 'intern';
      return `<div class="person-chip" onclick="jumpToPerson('${d.name.replace(/'/g, "\\'")}')" title="${d.forschungsbereich || ''}">
        <span class="chip-name">${d.name}</span>
        <span class="chip-meta">${d.universitat} · ${herk}${h != null ? ' · h ' + h : ''}</span>
      </div>`;
    }).join('');
    return `<div class="prog-card" style="border-top-color:${WWTF_PROG[p].color}">
      <h4>${WWTF_PROG[p].label} <span class="prog-count">${people.length}</span></h4>
      <div class="prog-desc">${WWTF_PROG[p].desc}</div>
      ${chips}
    </div>`;
  }).join('');

  // Kernaussagen
  const uniCounts = {};
  inProg.forEach(d => { uniCounts[d.universitat] = (uniCounts[d.universitat] || 0) + 1; });
  const topUni = Object.entries(uniCounts).sort((a, b) => b[1] - a[1])[0] || ['–', 0];
  const topH = inProg
    .map(d => ({ d, h: metricsOf(d).hIndex || 0 }))
    .sort((a, b) => b.h - a.h)
    .slice(0, 3)
    .filter(x => x.h > 0);
  const laender = new Set(ausland.map(d => d.herkunft_land));

  const items = [
    `<strong>${inProg.length} der ${rows.length} Berufungen</strong> (${Math.round(inProg.length / gesamt * 100)}%) liegen thematisch in WWTF-Programmfeldern — das potenzielle Antragsteller:innen-Reservoir der nächsten Ausschreibungen.`,
    `<strong>${topUni[0]}</strong> stellt mit ${topUni[1]} Berufungen die meisten Neuzugänge in WWTF-Feldern.`,
    `${extern.length} der ${inProg.length} wurden <strong>extern rekrutiert</strong>, ${ausland.length} davon international (${[...laender].join(', ')}) — frisch nach Wien geholte Expertise ohne etablierte lokale Fördernetzwerke.`,
    topH.length ? `Höchste Sichtbarkeit: ${topH.map(x => `<strong>${x.d.name}</strong> (${x.d.universitat}, h-Index ${x.h})`).join(', ')}.` : '',
    `Frauenanteil in WWTF-Feldern: <strong>${Math.round(frauen.length / Math.max(1, inProg.length) * 100)}%</strong> (gesamt: ${Math.round(rows.filter(d => d.geschlecht === 'W').length / gesamt * 100)}%).`,
  ].filter(Boolean);
  document.getElementById('insights-wwtf-list').innerHTML =
    items.map(i => `<li>${i}</li>`).join('');
}

function jumpToPerson(name) {
  switchTab('alle');
  document.getElementById('search-input').value = name;
  applyFilters();
}

// ─── KERNAUSSAGEN (Übersicht + Mobilität) ────────────────
function initInsights(rows) {
  const total = rows.length;
  const frauen = rows.filter(d => d.geschlecht === 'W').length;
  const intern = rows.filter(d => d.herkunft === 'intern').length;
  const monatCounts = MONATEN.map(m => rows.filter(d => d.monat === m).length);
  const topMonat = MONATEN[monatCounts.indexOf(Math.max(...monatCounts))];

  const bereichCounts = {};
  rows.forEach(d => {
    const b = inferBereich(d);
    bereichCounts[b] = (bereichCounts[b] || 0) + 1;
  });
  const topBereiche = Object.entries(bereichCounts).sort((a, b) => b[1] - a[1]).slice(0, 2);
  const bereichText = topBereiche.length === 2
    ? `<strong>${bereichLabel(topBereiche[0][0])}</strong> (${topBereiche[0][1]}) und <strong>${bereichLabel(topBereiche[1][0])}</strong> (${topBereiche[1][1]})`
    : topBereiche.length === 1
      ? `<strong>${bereichLabel(topBereiche[0][0])}</strong> (${topBereiche[0][1]})`
      : '–';

  document.getElementById('insights-uebersicht-list').innerHTML = [
    (() => {
      const perUni = {};
      rows.forEach(d => { perUni[d.universitat] = (perUni[d.universitat] || 0) + 1; });
      const top = Object.entries(perUni).sort((a, b) => b[1] - a[1]).slice(0, 2);
      const kopf = `<strong>${plural(total, 'Berufung', 'Berufungen')}</strong> an ` +
                   `${plural(uniCount(rows), 'Wiener Universität', 'Wiener Universitäten')}, Zeitraum ${yearLabel()}`;
      if (!top.length) return kopf + '.';
      const namen = top.map(([u, c]) => `${u} (${c})`).join(' und ');
      const anteil = top.reduce((sum, [, c]) => sum + c, 0) / Math.max(1, total);
      const verb = top.length === 1 ? 'stellt' : 'stellen';
      return `${kopf} — ${namen}` + (anteil > 0.5 ? ` ${verb} mehr als die Hälfte.` : ' liegen vorn.');
    })(),
    `Frauenanteil: <strong>${Math.round(frauen / Math.max(1, total) * 100)}%</strong> (${frauen} von ${total}) — unter der 50%-Zielmarke des UG-Frauenförderungsgebots.`,
    `Stärkste Bereiche: ${bereichText}.`,
    (() => {
      const spitze = Math.max(...monatCounts);
      if (!spitze) return '';
      const monat = topMonat.charAt(0) + topMonat.slice(1).toLowerCase();
      const zahl = plural(spitze, 'Berufung', 'Berufungen');
      return total >= 5 && spitze / total >= 0.25
        ? `Deutlicher Berufungsgipfel im <strong>${monat}</strong> (${zahl}) — Semesterlogik des Berufungsgeschäfts.`
        : `Häufigster Berufungsmonat: <strong>${monat}</strong> (${zahl}).`;
    })(),
  ].filter(Boolean).map(i => `<li>${i}</li>`).join('');

  const externAusland = rows.filter(d => d.herkunft === 'extern' && d.herkunft_land && d.herkunft_land !== 'Österreich');
  const landCounts = {};
  externAusland.forEach(d => { landCounts[d.herkunft_land] = (landCounts[d.herkunft_land] || 0) + 1; });
  const topLand = Object.entries(landCounts).sort((a, b) => b[1] - a[1])[0] || ['–', 0];

  document.getElementById('insights-mobilitaet-list').innerHTML = [
    `<strong>${intern} von ${total}</strong> Berufungen (${Math.round(intern / Math.max(1, total) * 100)}%) kommen aus der eigenen bzw. einer anderen Wiener Institution — der interne Arbeitsmarkt dominiert.`,
    externAusland.length
      ? `<strong>${externAusland.length} internationale Rekrutierungen</strong> aus ${plural(Object.keys(landCounts).length, 'Land', 'Ländern')}; größtes Herkunftsland: <strong>${topLand[0]}</strong> (${topLand[1]}).`
      : 'Keine internationalen Rekrutierungen im gewählten Zeitraum.',
    `Jede internationale Berufung ist ein Brain-Gain-Signal für den Standort — zugleich zeigt der hohe Intern-Anteil die Bedeutung der Wiener Karrierepipeline (§99 Abs. 4).`,
  ].filter(Boolean).map(i => `<li>${i}</li>`).join('');
}

// ─── TAB SWITCHING ───────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll('.tab-panel').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.remove('active');
    btn.setAttribute('aria-selected', 'false');
  });

  document.getElementById(`tab-${name}`).classList.add('active');
  document.querySelectorAll('.tab-btn').forEach(btn => {
    if (btn.getAttribute('onclick').includes(`'${name}'`)) {
      btn.classList.add('active');
      btn.setAttribute('aria-selected', 'true');
    }
  });

  renderTab(name);
  writeStateToHash();
}

// D3-Grafiken brauchen eine sichtbare Breite, deshalb erst beim Tab-Wechsel
// zeichnen. TAB_DIRTY erzwingt Neuzeichnen nach einer Jahresauswahl.
const TAB_DIRTY = { wwtf: true, mobilitaet: true };

function renderTab(name) {
  if (name === 'wwtf' && TAB_DIRTY.wwtf) { initWWTF(VIEW); TAB_DIRTY.wwtf = false; }
  if (name === 'mobilitaet' && TAB_DIRTY.mobilitaet) { initSankey(VIEW); TAB_DIRTY.mobilitaet = false; }
  if (name === 'alle') renderCards(currentFilteredData());
}

function activeTabName() {
  const t = document.querySelector('.tab-panel.active');
  return t ? t.id.replace('tab-', '') : 'uebersicht';
}

function renderOverview(rows) {
  initKPIs(rows);
  initInsights(rows);
  initGenderChart(rows);
  initTimelineChart(rows);
  initYearChart(rows);
  initBereichChart(rows);
  initOFOSChart(rows);
  initHeatmap(rows);
}

// Einziger Einstiegspunkt: setzt VIEW und zeichnet alles Sichtbare neu
function renderAll() {
  VIEW = DATA.filter(d => SELECTED_YEARS.has(d.year));
  renderOverview(VIEW);
  TAB_DIRTY.wwtf = true;
  TAB_DIRTY.mobilitaet = true;
  renderTab(activeTabName());
  renderYearBar();
}

// ─── JAHRES-PILLS ────────────────────────────────────────
function renderYearBar() {
  const alleAktiv = SELECTED_YEARS.size === YEARS.length;
  document.getElementById('year-pills').innerHTML = [
    `<button class="year-pill${alleAktiv ? ' active' : ''}" onclick="setAllYears()">Alle Jahre</button>`
  ].concat(YEARS.map(y =>
    `<button class="year-pill${SELECTED_YEARS.has(y) ? ' active' : ''}" onclick="toggleYear(${y})">${y}</button>`
  )).join('');
  document.getElementById('year-summary').textContent =
    `${yearLabel()} · ${VIEW.length} von ${DATA.length} Berufungen`;
}

function toggleYear(y) {
  if (SELECTED_YEARS.has(y)) {
    if (SELECTED_YEARS.size === 1) return;   // nie leer auswählen
    SELECTED_YEARS.delete(y);
  } else {
    SELECTED_YEARS.add(y);
  }
  renderAll();
  writeStateToHash();
}

function setAllYears() {
  SELECTED_YEARS = new Set(YEARS);
  renderAll();
  writeStateToHash();
}

// ─── INIT ────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('header-period').textContent =
    YEARS.length > 1
      ? `Suchzeitraum: Berufungsjahre ${YEARS[0]}–${YEARS[YEARS.length - 1]}`
      : `Suchzeitraum: Berufungsjahr ${YEARS[0]}`;
  populateLandFilter();
  restoreStateFromHash();
  renderAll();
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

# ─────────────────────────────────────────────────────────────────
# 5. Selbstcheck: Renderer dürfen nur ihr rows-Argument lesen.
#    Greift ein Renderer wieder aufs globale DATA zu, ignoriert er
#    die Jahresauswahl — das fällt sonst erst im Browser auf.
# ─────────────────────────────────────────────────────────────────
RENDERERS = [
    "initKPIs", "initInsights", "initGenderChart", "initTimelineChart",
    "initYearChart", "initBereichChart", "initOFOSChart", "initHeatmap",
    "initSankey", "initWWTF", "renderCards",
]
for fn in RENDERERS:
    m = re.search(rf"\nfunction {fn}\(", NEW_SCRIPT_FINAL)
    assert m, f"Renderer {fn} nicht gefunden"
    rest = NEW_SCRIPT_FINAL[m.end():]
    nxt = re.search(r"\n(function |// ───|let |const [A-Z])", rest)
    body = rest[: nxt.start() if nxt else len(rest)]
    assert not re.search(r"\bDATA\b", body), (
        f"{fn}() liest das globale DATA statt rows — Jahresauswahl bliebe wirkungslos"
    )
print(f"✓ Selbstcheck: {len(RENDERERS)} Renderer arbeiten auf rows")
print(f"  DATA entries: {len(DATA)}")
