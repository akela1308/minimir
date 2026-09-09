// Предвычислить пул жизнеспособных предков МИРА B («когда выгодно учиться»)
// для живого браузерного движка. Предок мира B: тот же случайный кормящийся
// геном, что в мире A (тот же поток случайных чисел на тот же seed),
// ослеплённый к цвету, с врождённым вкусом к цвету +1, и отбором на
// жизнеспособность уже в мире B (см. PREREGISTRATION_B.md §3).
// Пишем инкрементально, чтобы не терять прогресс.
const fs = require("fs");
const MW = require("../docs/engine.js");

// Мир B богаче мира A (regrowth 0.008 вместо 0.004): питательна в каждый
// момент только половина клеток, и без этого предок не находится.
// ВАЖНО про порог. Генератор пятён здесь другой, чем в Python (билинейный
// шум вместо спектрального), и один и тот же patch_threshold означает в них
// разную плодородность. Сравнивать надо не число, а энергетический бюджет:
// в Python при patch_threshold=0.0 суммарная ёмкость 1776 и мир кормит ~710
// особей. Тому же бюджету здесь соответствует patchThreshold 0.61 (при 0.0
// мир вышел бы впятеро богаче, популяция упиралась бы в потолок, поколения
// сменялись бы редко, и к первой смене правила разброс гена скорости не
// успевал бы накопиться: тогда вымирают ВСЕ семена). Та же поправка уже
// сделана в мире A: 0.62 в браузере против 0.35 в Python.
const LIVE_CFG_B = { maxPop: 1000, crowdCost: 0.07, regrowth: 0.008,
                     patchThreshold: 0.61, foodTypes: 2, taste: true };
const N = 8;

function b64(f32) { return Buffer.from(f32.buffer, f32.byteOffset, f32.byteLength).toString("base64"); }
function packGenome(g) {
  const a = new Float32Array(g.W1.length + g.b1.length + g.W2.length + g.b2.length);
  let o = 0; a.set(g.W1, o); o += g.W1.length; a.set(g.b1, o); o += g.b1.length;
  a.set(g.W2, o); o += g.W2.length; a.set(g.b2, o); return b64(a);
}
function save(pool, seeds) {
  fs.writeFileSync("docs/ancestors_b.json",
    JSON.stringify({ cfg: LIVE_CFG_B, genomeFloats: 468, seeds: seeds, ancestors: pool }));
}

const pool = [], seeds = [];
let searchSeed = 1;
const t0 = Date.now();
while (pool.length < N && searchSeed < 400) {
  const res = MW.findViableAncestorB(searchSeed, LIVE_CFG_B, { maxTries: 6000, synthCap: 120 });
  searchSeed++;
  if (!res) continue;
  pool.push(packGenome(res.genome)); seeds.push(searchSeed - 1);
  save(pool, seeds);   // инкрементально
  console.log(`предок #${pool.length}: seed=${searchSeed - 1} tries=${res.tries} (${((Date.now() - t0) / 1000).toFixed(0)}s)`);
}
console.log(`\nготово: ${pool.length} предков за ${((Date.now() - t0) / 1000).toFixed(0)}s, docs/ancestors_b.json`);
