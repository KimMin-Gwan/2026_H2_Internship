// ERD image generator (docs/images/erd.png full, docs/images/erd-brief.png for slides)
const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const G = "#00835F", INK = "#12241F", LINE = "#5F6F69";
const T = {
  users: { pos: [40, 40], cols: [["id", "PK", "INT"], ["email", "UQ", "VARCHAR"], ["password_hash", "", "VARCHAR"], ["nickname", "", "VARCHAR"], ["created_at", "", "DATETIME"]] },
  receipts: { pos: [440, 40], cols: [["id", "PK", "INT"], ["user_id", "FK", "INT"], ["image_key", "", "VARCHAR"], ["status", "", "VARCHAR"], ["merchant", "", "VARCHAR"], ["purchased_on", "", "DATE"], ["total_amount", "", "INT"], ["parsed_json", "", "TEXT"], ["confidence", "", "VARCHAR"], ["created_at", "", "DATETIME"]] },
  categories: { pos: [840, 40], cols: [["id", "PK", "INT"], ["name", "UQ", "VARCHAR"], ["type", "", "VARCHAR"]] },
  transactions: { pos: [440, 400], cols: [["id", "PK", "INT"], ["user_id", "FK", "INT"], ["receipt_id", "FK", "INT"], ["category_id", "FK", "INT"], ["type", "", "VARCHAR"], ["amount", "", "INT"], ["title", "", "VARCHAR"], ["merchant", "", "VARCHAR"], ["memo", "", "VARCHAR"], ["occurred_on", "", "DATE"], ["created_at", "", "DATETIME"], ["updated_at", "", "DATETIME"]] },
};
const BRIEF = {
  users: ["id", "email", "password_hash", "nickname"],
  receipts: ["id", "user_id", "status", "merchant", "total_amount", "parsed_json"],
  categories: ["id", "name", "type"],
  transactions: ["id", "user_id", "receipt_id", "category_id", "type", "amount", "title", "occurred_on"],
};

function html(brief) {
  const RH = brief ? 34 : 26, HH = brief ? 42 : 34, W = brief ? 300 : 280, FS = brief ? 17 : 14;
  const pos = brief
    ? { users: [40, 40], receipts: [440, 40], categories: [840, 40], transactions: [440, 380] }
    : Object.fromEntries(Object.entries(T).map(([k, v]) => [k, v.pos]));
  const cols = (k) => T[k].cols.filter((c) => !brief || BRIEF[k].includes(c[0]));
  const height = (k) => HH + cols(k).length * RH;
  const boxes = Object.keys(T).map((k) => {
    const [x, y] = pos[k];
    const rows = cols(k).map(([n, key, ty]) => `<div style="display:flex;align-items:center;height:${RH}px;padding:0 12px;border-top:1px solid #DCE5E0;font-size:${FS}px;color:${INK}">
      <span style="width:34px;font-weight:800;font-size:${FS - 3}px;color:${key === "PK" ? "#B45309" : key === "FK" ? "#1D4ED8" : "#5F6F69"}">${key}</span>
      <span style="flex:1;font-weight:${key ? 700 : 500}">${n}</span><span style="color:#5F6F69;font-size:${FS - 3}px">${ty}</span></div>`).join("");
    return `<div style="position:absolute;left:${x}px;top:${y}px;width:${W}px;background:#fff;border:2px solid ${G};border-radius:14px;overflow:hidden">
      <div style="height:${HH}px;background:${G};color:#fff;font-weight:800;font-size:${FS + 2}px;display:flex;align-items:center;padding:0 14px">${k}</div>${rows}</div>`;
  }).join("");
  const R = (k) => ({ x: pos[k][0], y: pos[k][1], w: W, h: height(k) });
  const u = R("users"), r = R("receipts"), c = R("categories"), t = R("transactions");
  const lines = [];
  const L = (pts, a, b) => lines.push({ pts, a, b });
  L([[u.x + W, u.y + HH + RH * 0.5 + 4], [r.x, u.y + HH + RH * 0.5 + 4]], "1", "N");
  L([[u.x + W, u.y + HH + RH * 3.5], [u.x + W + 60, u.y + HH + RH * 3.5], [u.x + W + 60, t.y + HH + RH * 1.5], [t.x, t.y + HH + RH * 1.5]], "1", "N");
  L([[r.x + W / 2, r.y + r.h], [t.x + W / 2, t.y]], "1", "N");
  L([[c.x + W / 2, c.y + c.h], [c.x + W / 2, t.y + HH + RH * 3.5], [t.x + W, t.y + HH + RH * 3.5]], "1", "N");
  const svg = lines.map(({ pts, a, b }) => {
    const d = pts.map((p, i) => (i ? "L" : "M") + p[0] + " " + p[1]).join(" ");
    const f = pts[0], l = pts[pts.length - 1], f2 = pts[1], l2 = pts[pts.length - 2];
    const off = (p, q) => { const dx = q[0] - p[0], dy = q[1] - p[1], n = Math.hypot(dx, dy) || 1, ux = dx / n, uy = dy / n; return [p[0] + ux * 20 - uy * 14, p[1] + uy * 20 + ux * 14 - 4]; };
    const A = off(f, f2), B = off(l, l2);
    return `<path d="${d}" fill="none" stroke="${LINE}" stroke-width="2.5"/>
      <text x="${A[0]}" y="${A[1] + 4}" font-size="${FS}" font-weight="800" fill="${G}" text-anchor="middle">${a}</text>
      <text x="${B[0]}" y="${B[1] + 4}" font-size="${FS}" font-weight="800" fill="${G}" text-anchor="middle">${b}</text>`;
  }).join("");
  const Wc = 1180, Hc = t.y + t.h + 40;
  return { w: Wc, h: Hc, html: `<html><body style="margin:0;background:#fff;font-family:'Pretendard','Noto Sans KR','Malgun Gothic',sans-serif">
    <div style="position:relative;width:${Wc}px;height:${Hc}px">
    <svg style="position:absolute;left:0;top:0" width="${Wc}" height="${Hc}">${svg}</svg>${boxes}</div></body></html>` };
}

(async () => {
  const out = path.resolve(__dirname, "../../docs/images");
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  for (const [name, brief] of [["erd", false], ["erd-brief", true]]) {
    const { w, h, html: h5 } = html(brief);
    const ctx = await browser.newContext({ deviceScaleFactor: 2, viewport: { width: w, height: h } });
    const page = await ctx.newPage();
    await page.setContent(h5);
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(out, name + ".png"), clip: { x: 0, y: 0, width: w, height: h } });
    console.log(name, w, h);
  }
  await browser.close();
})();
