#!/usr/bin/env node
/* tvt-create-explainer renderer
 * Markdown (+ figure DSL) -> styled HTML -> PDF via headless Chrome.
 *
 * Usage: node render.js <input.md> [output.pdf]
 *
 * The Markdown may contain YAML-ish front matter:
 *   ---
 *   title: Mortgage Insurance Lifecycle
 *   kicker: CONSOLIDATED VIEW
 *   parts: Origination · Servicing · Claims
 *   subtitle: One view of the three MI business processes...
 *   companion: Companion to the three domain ontologies
 *   tag: Origination · Servicing · Claims
 *   ---
 *
 * Figures are fenced blocks: ```figure:swimlane | venn | chain | callout
 * (see SKILL.md "Figure DSL"). Plain Markdown tables become styled tables.
 */
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const COLORS = { blue: "#2D6CB5", green: "#2E8B7F", purple: "#7B4EA8", navy: "#1B3A6B" };

function die(m) { console.error("render.js: " + m); process.exit(1); }

const inPath = process.argv[2];
if (!inPath) die("usage: node render.js <input.md> [output.pdf]");
const outPath = process.argv[3] || inPath.replace(/\.md$/i, "") + ".pdf";
let src = fs.readFileSync(inPath, "utf8");

/* ---------- front matter ---------- */
const meta = { title: "", kicker: "", parts: "", subtitle: "", companion: "", tag: "" };
const fm = src.match(/^---\n([\s\S]*?)\n---\n?/);
if (fm) {
  fm[1].split("\n").forEach((l) => {
    const m = l.match(/^(\w+):\s*(.*)$/);
    if (m && meta.hasOwnProperty(m[1])) meta[m[1]] = m[2].trim();
  });
  src = src.slice(fm[0].length);
}
if (!meta.tag) meta.tag = meta.parts;
if (!meta.title) meta.title = path.basename(inPath, ".md");

/* ---------- parse simple YAML-ish figure body ---------- */
function kv(body) {
  const o = {}; let key = null;
  body.split("\n").forEach((raw) => {
    const line = raw.replace(/\s+$/, "");
    if (!line.trim()) return;
    const top = line.match(/^(\w[\w ]*?):\s*(.*)$/);
    if (top && !/^\s/.test(raw)) { key = top[1]; o[key] = top[2]; o["_sub_" + key] = []; }
    else if (/^\s+/.test(raw) && key) { o["_sub_" + key].push(line.trim()); }
  });
  return o;
}
function colorOf(label) {
  const m = label.match(/\[(\w+)\]/);
  return m ? m[1] : "blue";
}
function stripColor(label) { return label.replace(/\s*\[\w+\]\s*/, "").trim(); }
function esc(s){return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");}

/* ---------- figure renderers ---------- */
function fig(inner, caption) {
  const cap = caption ? `<figcaption>${esc(caption)}</figcaption>` : "";
  return `<figure>${inner}${cap}</figure>`;
}

function swimlane(o) {
  const lanes = (o._sub_columns || []).concat(
    Object.keys(o).filter(k => !k.startsWith("_") && k !== "caption" && k !== "columns")
      .map(k => `${k}: ${o[k]}`)
  );
  // Support both "columns:" sub-list and top-level "Name [color]: a | b | c"
  const defs = (o._sub_columns && o._sub_columns.length) ? o._sub_columns : lanes;
  const html = defs.map(line => {
    const m = line.match(/^(.*?):\s*(.*)$/); if (!m) return "";
    const c = colorOf(m[1]); const name = stripColor(m[1]);
    const cells = m[2].split("|").map(s => s.trim()).filter(Boolean)
      .map(s => `<div class="cell">${esc(s)}</div>`).join("");
    return `<div class="lane" data-c="${c}"><div class="lane-head">${esc(name)}</div>${cells}</div>`;
  }).join("");
  return fig(`<div class="swim">${html}</div>`, o.caption);
}

function chain(o) {
  const steps = o._sub_steps || [];
  const nodes = steps.map(line => {
    const m = line.match(/^(.*?):\s*(.*)$/); if (!m) return null;
    return `<div class="node"><div class="node-head">${esc(m[1])}</div><div class="node-body">${esc(m[2])}</div></div>`;
  }).filter(Boolean);
  const joined = nodes.join('<div class="arrow">&#9656;</div>');
  return fig(`<div class="chain">${joined}</div>`, o.caption);
}

function callout(o) {
  return `<div class="callout"><div class="callout-title">${esc(o.title||"The one-line takeaway")}</div><div class="callout-body">${esc(o.body||"")}</div></div>`;
}

function venn(o) {
  const circles = (o.circles||"").split("|").map(s => s.trim()).filter(Boolean);
  const cols = circles.map(c => COLORS[colorOf(c)] || COLORS.blue);
  const names = circles.map(stripColor);
  const seams = (o._sub_seams || []).map(l => { const m=l.match(/^(.*?):\s*(.*)$/); return m?{k:m[1],v:m[2]}:null; }).filter(Boolean);
  const seam = (a,b) => { const f = seams.find(s => s.k.includes(a.slice(0,4)) && s.k.includes(b.slice(0,4))); return f?f.v:""; };
  // three-circle layout
  const W=520,H=460,r=150;
  const c1={x:200,y:175}, c2={x:320,y:175}, c3={x:260,y:285};
  const wrap=(t,x,y,fill="#1B3A6B",size=12,weight=400)=>`<text x="${x}" y="${y}" text-anchor="middle" font-size="${size}" font-weight="${weight}" fill="${fill}">${t.split("\n").map((ln,i)=>`<tspan x="${x}" dy="${i?14:0}">${esc(ln)}</tspan>`).join("")}</text>`;
  const center = (o.center||"").split(";").map(s=>s.trim());
  const svg = `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">
    <circle cx="${c1.x}" cy="${c1.y}" r="${r}" fill="${cols[0]}22" stroke="${cols[0]}" stroke-width="2"/>
    <circle cx="${c2.x}" cy="${c2.y}" r="${r}" fill="${cols[1]||cols[0]}22" stroke="${cols[1]||cols[0]}" stroke-width="2"/>
    ${circles.length>2?`<circle cx="${c3.x}" cy="${c3.y}" r="${r}" fill="${cols[2]}22" stroke="${cols[2]}" stroke-width="2"/>`:""}
    ${wrap(names[0],c1.x-70,40,cols[0],13,700)}
    ${wrap(names[1]||"",c2.x+70,40,cols[1]||cols[0],13,700)}
    ${circles.length>2?wrap(names[2],c3.x,H-20,cols[2],13,700):""}
    ${wrap("SHARED\n"+center.join("\n"),260,200,"#1B3A6B",10,700)}
    ${wrap(seam(names[0],names[1]),260,120,"#1B3A6B",10)}
    ${circles.length>2?wrap(seam(names[1],names[2]),360,260,"#1B3A6B",10):""}
    ${circles.length>2?wrap(seam(names[0],names[2]),160,260,"#1B3A6B",10):""}
  </svg>`;
  return fig(`<div class="venn">${svg}</div>`, o.caption);
}

/* ---------- replace figure fences with placeholders (protect HTML from the
   line-by-line Markdown pass; swapped back in after) ---------- */
const figs = [];
src = src.replace(/```figure:(\w+)\n([\s\S]*?)```/g, (_, type, body) => {
  const o = kv(body);
  let html;
  if (type === "swimlane") html = swimlane(o);
  else if (type === "chain")    html = chain(o);
  else if (type === "venn")     html = venn(o);
  else if (type === "callout")  html = callout(o);
  else html = `<pre>${esc(body)}</pre>`;
  figs.push(html);
  return `\n@@FIG${figs.length - 1}@@\n`;
});

/* ---------- minimal Markdown -> HTML (headings, tables, bullets, bold, cover) ---------- */
function mdInline(s){
  return esc(s)
    .replace(/\*\*(.+?)\*\*/g,"<strong>$1</strong>")
    .replace(/\*(.+?)\*/g,"<em>$1</em>")
    .replace(/`(.+?)`/g,"<code>$1</code>")
    .replace(/-&gt;|→/g,"&#8594;");
}
function mdTables(block){
  const lines = block.split("\n");
  let out=[], i=0;
  while(i<lines.length){
    if(/^\s*\|.*\|\s*$/.test(lines[i]) && /^\s*\|[\s:|-]+\|\s*$/.test(lines[i+1]||"")){
      const head = lines[i].split("|").slice(1,-1).map(s=>s.trim());
      i+=2; const rows=[];
      while(i<lines.length && /^\s*\|.*\|\s*$/.test(lines[i])){ rows.push(lines[i].split("|").slice(1,-1).map(s=>s.trim())); i++; }
      out.push(`<table><thead><tr>${head.map(h=>`<th>${mdInline(h)}</th>`).join("")}</tr></thead><tbody>${rows.map(r=>`<tr>${r.map(c=>`<td>${mdInline(c)}</td>`).join("")}</tr>`).join("")}</tbody></table>`);
    } else { out.push(lines[i]); i++; }
  }
  return out.join("\n");
}
function mdBlocks(text){
  text = mdTables(text);
  const lines=text.split("\n"); let html=[], inUl=false;
  const closeUl=()=>{ if(inUl){html.push("</ul>");inUl=false;} };
  for(const line of lines){
    if(/^##\s+/.test(line)){ closeUl(); html.push(`<h2>${mdInline(line.replace(/^##\s+/,""))}</h2>`); }
    else if(/^\s*[-*]\s+/.test(line)){ if(!inUl){html.push("<ul>");inUl=true;} html.push(`<li>${mdInline(line.replace(/^\s*[-*]\s+/,""))}</li>`); }
    else if(/^@@FIG\d+@@$/.test(line.trim())){ closeUl(); html.push(line.trim()); }
    else if(/^\s*<(figure|div|table|svg)/.test(line) || /^\s*<\/?(figure|div|table)/.test(line)){ closeUl(); html.push(line); }
    else if(line.trim()===""){ closeUl(); html.push(""); }
    else { closeUl(); html.push(`<p>${mdInline(line)}</p>`); }
  }
  closeUl();
  return html.join("\n");
}

const cover = `<section class="cover">
  ${meta.kicker?`<div class="kicker">${esc(meta.kicker)}</div>`:""}
  <h1>${esc(meta.title)}</h1>
  ${meta.parts?`<div class="parts">${mdInline(meta.parts)}</div>`:""}
  <hr/>
  ${meta.subtitle?`<div class="subtitle">${esc(meta.subtitle)}</div>`:""}
  ${meta.companion?`<div class="companion">${esc(meta.companion)}</div>`:""}
</section>`;

let body = mdBlocks(src);
body = body.replace(/@@FIG(\d+)@@/g, (_, i) => figs[+i]);
const css = fs.readFileSync(path.join(__dirname, "explainer.css"), "utf8");

const html = `<!doctype html><html><head><meta charset="utf-8">
<style>
:root{--doc-title:"${meta.title}";--doc-tag:"${meta.tag}";--doc-companion:"${meta.companion}";}
${css}
</style></head><body>
${cover}
${body}
</body></html>`;

const htmlPath = outPath.replace(/\.pdf$/i, "") + ".explainer.html";
fs.writeFileSync(htmlPath, html);
console.log("wrote " + htmlPath);

/* ---------- print to PDF ---------- */
function chromePath(){
  const cands = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome","chromium","chromium-browser"
  ];
  for(const c of cands){ try{ if(c.startsWith("/")){ fs.accessSync(c); return c; } else { execFileSync("which",[c]); return c; } }catch(e){} }
  return null;
}
const chrome = chromePath();
try {
  if (chrome) {
    execFileSync(chrome, [
      "--headless","--disable-gpu","--no-sandbox",
      "--print-to-pdf=" + outPath, "--no-pdf-header-footer",
      "file://" + path.resolve(htmlPath)
    ], { stdio: "inherit" });
    console.log("wrote " + outPath + " (headless Chrome)");
  } else {
    execFileSync("npx", ["md-to-pdf", htmlPath], { stdio: "inherit" });
    console.log("wrote PDF via md-to-pdf fallback");
  }
} catch (e) {
  die("PDF print failed: " + e.message + "\nHTML is at " + htmlPath + " — open in a browser and Print to PDF.");
}
