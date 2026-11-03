#!/usr/bin/env node
// Stufe 3 der Fachprofile: Textvektor je Person für die semantische Suche.
//
// Dasselbe Modell wie im Browser (Xenova/multilingual-e5-small, ONNX q8 über
// transformers.js), damit Anfrage- und Personenvektoren im selben Raum liegen.
// Je Person werden bis zu 40 Arbeiten (30 meistzitierte + 10 jüngste) als
// "passage: Titel. Abstract…" eingebettet und gemittelt; der Mittelwert wird
// normiert und als int8 (×127) base64-kodiert nach fachprofile_emb.json
// geschrieben. 1012 Personen × 384 Dimensionen ≈ 0,5 MB.
//
// Einzelvektoren liegen in scripts/.fachprofil_cache/emb/<id>.json, damit ein
// Neulauf nur neue Personen rechnet.
//
// Aufruf:  cd scripts && npm install && node fachprofil_embed.mjs [--refresh]

import { readFileSync, writeFileSync, existsSync, mkdirSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { pipeline } from "@huggingface/transformers";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, "..");
const CACHE = join(HERE, ".fachprofil_cache");
const EMB_CACHE = join(CACHE, "emb");
const OUT = join(ROOT, "fachprofile_emb.json");
const MODELL = "Xenova/multilingual-e5-small";
const DIM = 384;
const REFRESH = process.argv.includes("--refresh");

const data = JSON.parse(readFileSync(join(ROOT, "dashboard_data_2025.json"), "utf8"));
const ids = [...new Set(data.map(d => d.openalex_id).filter(Boolean))].sort();
mkdirSync(EMB_CACHE, { recursive: true });

function passagen(werke) {
  const brauchbar = werke.filter(w => w.titel && !["paratext", "erratum", "retraction"].includes(w.typ));
  const zitiert = [...brauchbar].sort((a, b) => b.zit - a.zit).slice(0, 30);
  const juengst = [...brauchbar].sort((a, b) => (b.jahr || 0) - (a.jahr || 0)).slice(0, 10);
  const gesehen = new Set();
  const auswahl = [...zitiert, ...juengst].filter(w => !gesehen.has(w.id) && gesehen.add(w.id));
  return auswahl.map(w => {
    const inhalt = w.abstract
      ? w.abstract.slice(0, 1200)
      : (w.topics || []).slice(0, 3).map(t => t.name).join("; ");
    return `passage: ${w.titel}. ${inhalt}`;
  });
}

function normiere(v) {
  const n = Math.hypot(...v) || 1;
  return v.map(x => x / n);
}

function int8b64(v) {
  const q = new Int8Array(v.map(x => Math.max(-127, Math.min(127, Math.round(x * 127)))));
  return Buffer.from(q.buffer).toString("base64");
}

const offen = ids.filter(id => existsSync(join(CACHE, `${id}.json`)) &&
  (REFRESH || !existsSync(join(EMB_CACHE, `${id}.json`))));
console.log(`${ids.length} Personen, ${offen.length} zu rechnen`);

let extractor = null;
if (offen.length) {
  const t0 = Date.now();
  extractor = await pipeline("feature-extraction", MODELL, { dtype: "q8" });
  console.log(`Modell geladen in ${((Date.now() - t0) / 1000).toFixed(0)} s`);
}

let n = 0;
for (const id of offen) {
  const werke = JSON.parse(readFileSync(join(CACHE, `${id}.json`), "utf8")).werke;
  const texte = passagen(werke);
  if (!texte.length) continue;
  const mittel = new Array(DIM).fill(0);
  for (let i = 0; i < texte.length; i += 16) {
    const out = await extractor(texte.slice(i, i + 16), { pooling: "mean", normalize: true });
    const liste = out.tolist();
    for (const v of liste) for (let k = 0; k < DIM; k++) mittel[k] += v[k];
  }
  writeFileSync(join(EMB_CACHE, `${id}.json`), JSON.stringify({
    id, n: texte.length, v: normiere(mittel.map(x => x / texte.length)),
  }));
  if (++n % 50 === 0) console.log(`  ${n}/${offen.length}`);
}

// Zusammenführen
const personen = {};
for (const f of readdirSync(EMB_CACHE)) {
  if (!f.endsWith(".json")) continue;
  const e = JSON.parse(readFileSync(join(EMB_CACHE, f), "utf8"));
  if (ids.includes(e.id)) personen[e.id] = int8b64(e.v);
}
writeFileSync(OUT, JSON.stringify({
  modell: MODELL, dtype: "q8", dim: DIM, skala: 127, praefix_query: "query: ",
  stand: new Date().toISOString().slice(0, 10), personen,
}));
console.log(`✓ ${Object.keys(personen).length} Vektoren → fachprofile_emb.json`);

// Selbstcheck: Anfrage zur Herztransplantation muss Zuckermann weit oben einordnen
if (extractor && personen["A5033263383"]) {
  const q = (await extractor("query: heart transplantation immunosuppression", { pooling: "mean", normalize: true })).tolist()[0];
  const score = id => {
    const b = Buffer.from(personen[id], "base64");
    let s = 0;
    for (let k = 0; k < DIM; k++) s += q[k] * (b.readInt8(k) / 127);
    return s;
  };
  const rang = Object.keys(personen).map(id => [id, score(id)]).sort((a, b) => b[1] - a[1]);
  const pos = rang.findIndex(([id]) => id === "A5033263383");
  console.log(`  Selbstcheck: Zuckermann auf Rang ${pos + 1} von ${rang.length} (Score ${rang[pos][1].toFixed(3)})`);
  if (pos > 5) { console.error("✗ Selbstcheck fehlgeschlagen"); process.exit(1); }
}
