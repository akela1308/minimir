// Предвычислить пул жизнеспособных предков для живого браузерного движка.
// Разнообразие эпизодов даёт пул × разные семена мира × дрейф мутаций, поэтому
// характеризацию не гоняем — берём любого жизнеспособного предка. Пишем
// инкрементально, чтобы не терять прогресс.
const fs = require("fs");
const MW = require("../docs/engine.js");

const LIVE_CFG = { maxPop: 1000, crowdCost: 0.07, regrowth: 0.0038, patchThreshold: 0.40 };
const N = 6;

function b64(f32) { return Buffer.from(f32.buffer, f32.byteOffset, f32.byteLength).toString("base64"); }
function packGenome(g) {
  const a = new Float32Array(g.W1.length + g.b1.length + g.W2.length + g.b2.length);
  let o = 0; a.set(g.W1, o); o += g.W1.length; a.set(g.b1, o); o += g.b1.length;
  a.set(g.W2, o); o += g.W2.length; a.set(g.b2, o); return b64(a);
}
function save(pool) {
  fs.writeFileSync("docs/ancestors.json", JSON.stringify({ cfg: LIVE_CFG, genomeFloats: 468, ancestors: pool }));
}

const pool = [];
let searchSeed = 1;
const t0 = Date.now();
while (pool.length < N && searchSeed < 400) {
  const res = MW.findViableAncestor(searchSeed, {}, { maxTries: 6000, synthCap: 120 });
  searchSeed++;
  if (!res) continue;
  pool.push(packGenome(res.genome));
  save(pool);   // инкрементально
  console.log(`предок #${pool.length}: seed=${searchSeed - 1} tries=${res.tries} (${((Date.now() - t0) / 1000).toFixed(0)}s)`);
}
console.log(`\nготово: ${pool.length} предков за ${((Date.now() - t0) / 1000).toFixed(0)}s, docs/ancestors.json`);
