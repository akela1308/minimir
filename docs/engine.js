/* мини-мир: живой движок в браузере (перенос из Python/numpy).
   Честная оговорка: это переписанная заново реализация, не тот самый
   Python-инструмент из отчёта (RNG и генерация пятён отличаются). Кооперация
   здесь с ПОЧИЩЕННОЙ энергетикой: отдать = столько же, сколько получает другой
   (без «+4 из ниоткуда»), как намечено в следующих шагах отчёта. */
(function (root) {
  "use strict";

  // --- индексы действий ---
  var A_FWD = 0, A_LEFT = 1, A_RIGHT = 2, A_EAT = 3, A_REST = 4,
      A_GIVE = 5, A_TAKE = 6, A_MARK = 7;
  var N_ACT = 8, N_MEM = 2, N_SIGN = 2, N_OUT = 12, N_IN = 25, N_HID = 12;
  var OFF_Y = [-1, -1, 0, 1, 1, 1, 0, -1];
  var OFF_X = [0, 1, 1, 1, 0, -1, -1, -1];

  // соседи для поиска ближайшего, отсортированы по расстоянию (радиус 2)
  var NB = [];
  for (var dy = -2; dy <= 2; dy++) for (var dx = -2; dx <= 2; dx++)
    if (dy || dx) NB.push([dy, dx, Math.hypot(dy, dx)]);
  NB.sort(function (a, b) { return a[2] - b[2]; });

  function mulberry32(a) {
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function defaults() {
    return {
      H: 128, W: 128, regrowth: 0.004, patchFreq: 8, patchThreshold: 0.35,
      seasonPeriod: 5000, seasonAmp: 0.6,
      eMax: 100, eStart: 50, basal: 0.10, moveCost: 0.25, turnCost: 0.05,
      eatCost: 0.05, crowdCost: 0.06, bite: 0.40, energyPerRes: 25, maxAge: 3000,
      reproThreshold: 80, childEnergy: 40, reproOverhead: 5,
      mutationRate: 0.12, mutationSigma: 0.08,
      initPop: 200, maxPop: 1400, foundingSigma: 0.15, initWeightSigma: 0.5,
      // социальный слой (кооперация) — ПОЧИЩЕННАЯ энергетика: give нейтрален
      giveCost: 8, giveGain: 8, takeGain: 6, takeLoss: 10,
      memorySlots: 8, faceTol: 0.15, socialFromTick: 300, actionNoise: 0.02,
      // условие интероцепции: 'self' (лечение) или 'shuffled' (контроль —
      // тот же сигнал энергии, но переставленный между особями: ноль знания о себе)
      interoMode: 'self',
      // знаки
      signsEnabled: true, signDecay: 0.985, markCost: 0.3,
      // пластичность
      hebbRateInit: 0.002, hebbRateSigma: 0.0005, hebbEvery: 5, hebbEnabled: true,
      weightClip: 3.0
    };
  }

  function Engine(seed, cfg, ancestor) {
    this.cfg = Object.assign(defaults(), cfg || {});
    this.seed = seed >>> 0;
    this.ancestor = ancestor || null;   // {W1,b1,W2,b2} — жизнеспособный предок
    this.rng = mulberry32(seed);
    var c = this.cfg, n = c.maxPop, H = c.H, W = c.W;
    this.tick = 0; this.extinctAt = null;
    // мир
    this.capacity = this._makeCapacity();
    this.resource = new Float32Array(H * W);
    for (var i = 0; i < H * W; i++) this.resource[i] = this.capacity[i];
    this.signs = new Float32Array(H * W * 2);
    this.signAuthor = new Float32Array(H * W * 3);
    this.signAge = new Float32Array(H * W);
    // агенты (struct-of-arrays)
    this.alive = new Uint8Array(n);
    this.x = new Int16Array(n); this.y = new Int16Array(n);
    this.heading = new Int8Array(n);
    this.E = new Float32Array(n); this.Elag = new Float32Array(n);
    this.age = new Int32Array(n);
    this.mem = new Float32Array(n * N_MEM);
    this.face = new Float32Array(n * 3);
    this.memFaces = new Float32Array(n * c.memorySlots * 3);
    this.memValid = new Uint8Array(n * c.memorySlots);
    this.memOut = new Float32Array(n * c.memorySlots);
    this.memPtr = new Int32Array(n);
    this.birthTick = new Int32Array(n);
    // мозг
    this.W1 = new Float32Array(n * N_IN * N_HID);
    this.b1 = new Float32Array(n * N_HID);
    this.W2 = new Float32Array(n * N_HID * N_OUT);
    this.b2 = new Float32Array(n * N_OUT);
    this.lr = new Float32Array(n);
    this._free = [];
    for (var s = n - 1; s >= 0; s--) this._free.push(s);
    // метрики
    this.pop = 0; this.births = 0; this.deaths = 0;
    this.coop = 0; this.defect = 0; this.marks = 0;
    this.lifespans = [];
    this.histWin = new Int32Array(10 * N_ACT);   // окно для живой MI
    this.histCum = new Int32Array(10 * N_ACT);   // за весь эпизод (после прогрева)
    this.actionCounts = new Int32Array(N_ACT);
    this._occ = new Int32Array(H * W);
    this._crowd = new Int16Array(H * W);
    // переиспользуемые буферы горячего цикла (иначе аллокация на агента на тик)
    this._X = new Float32Array(N_IN);
    this._hvec = new Float32Array(N_HID);
    this._out = new Float32Array(N_OUT);
    this._lastout = new Float32Array(N_OUT);
    this._seedInitial();
  }

  Engine.prototype._makeCapacity = function () {
    // пятнистая ёмкость через билинейно интерполированный низкочастотный шум
    var c = this.cfg, H = c.H, W = c.W, f = c.patchFreq;
    var cw = f + 1, ch = f + 1, coarse = new Float32Array(cw * ch);
    for (var i = 0; i < cw * ch; i++) coarse[i] = this.rng();
    var cap = new Float32Array(H * W), mn = 1e9, mx = -1e9;
    for (var y = 0; y < H; y++) for (var x = 0; x < W; x++) {
      var gx = x / W * f, gy = y / H * f;
      var x0 = Math.floor(gx), y0 = Math.floor(gy), tx = gx - x0, ty = gy - y0;
      var a = coarse[y0 * cw + x0], b = coarse[y0 * cw + x0 + 1];
      var cc = coarse[(y0 + 1) * cw + x0], d = coarse[(y0 + 1) * cw + x0 + 1];
      var v = a * (1 - tx) * (1 - ty) + b * tx * (1 - ty) + cc * (1 - tx) * ty + d * tx * ty;
      cap[y * W + x] = v; if (v < mn) mn = v; if (v > mx) mx = v;
    }
    var mxc = 0;
    for (var k = 0; k < H * W; k++) {
      var vv = (cap[k] - mn) / (mx - mn + 1e-9) - c.patchThreshold;
      vv = vv > 0 ? vv : 0; cap[k] = vv; if (vv > mxc) mxc = vv;
    }
    if (mxc > 0) for (var m = 0; m < H * W; m++) cap[m] /= mxc;
    return cap;
  };

  Engine.prototype.normal = function () {
    // Бокс–Мюллер
    var u = 1 - this.rng(), v = this.rng();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  };

  Engine.prototype._seedInitial = function () {
    var c = this.cfg, k = Math.min(c.initPop, this._free.length), a;
    if (this.ancestor) {
      a = this.ancestor;
    } else {
      // биасный случайный геном (используется поиском жизнеспособного предка)
      a = { W1: new Float32Array(N_IN * N_HID), b1: new Float32Array(N_HID),
            W2: new Float32Array(N_HID * N_OUT), b2: new Float32Array(N_OUT) };
      for (var i = 0; i < a.W1.length; i++) a.W1[i] = this.normal() * c.initWeightSigma;
      for (var j = 0; j < a.W2.length; j++) a.W2[j] = this.normal() * c.initWeightSigma;
      a.b2[A_FWD] += 0.5; a.b2[A_EAT] += 0.5;
    }
    for (var q = 0; q < k; q++) this._birthFromAncestor(a.W1, a.b1, a.W2, a.b2);
  };

  Engine.prototype._birthFromAncestor = function (aW1, ab1, aW2, ab2) {
    var c = this.cfg, s = this._free.pop(); if (s === undefined) return;
    var fs = c.foundingSigma;
    for (var i = 0; i < N_IN * N_HID; i++) this.W1[s * N_IN * N_HID + i] = aW1[i] + this.normal() * fs;
    for (var j = 0; j < N_HID; j++) this.b1[s * N_HID + j] = ab1[j] + this.normal() * fs;
    for (var p = 0; p < N_HID * N_OUT; p++) this.W2[s * N_HID * N_OUT + p] = aW2[p] + this.normal() * fs;
    for (var r = 0; r < N_OUT; r++) this.b2[s * N_OUT + r] = ab2[r] + this.normal() * fs;
    this.lr[s] = c.hebbRateInit;
    this.alive[s] = 1; this.pop++;
    this.x[s] = (this.rng() * c.W) | 0; this.y[s] = (this.rng() * c.H) | 0;
    this.heading[s] = (this.rng() * 8) | 0;
    this.E[s] = c.eStart; this.Elag[s] = c.eStart; this.age[s] = 0;
    this.mem[s * N_MEM] = 0; this.mem[s * N_MEM + 1] = 0;
    this.memPtr[s] = 0; this.birthTick[s] = this.tick;
    for (var m = 0; m < c.memorySlots; m++) this.memValid[s * c.memorySlots + m] = 0;
    this.face[s * 3] = this.rng(); this.face[s * 3 + 1] = this.rng(); this.face[s * 3 + 2] = this.rng();
  };

  Engine.prototype.season = function () {
    if (this.cfg.seasonPeriod <= 0) return 1;
    return 1 + this.cfg.seasonAmp * Math.sin(2 * Math.PI * this.tick / this.cfg.seasonPeriod);
  };

  // один тик мира
  Engine.prototype.step = function () {
    var c = this.cfg, H = c.H, W = c.W, HW = H * W;
    if (this.pop === 0) { if (this.extinctAt === null) this.extinctAt = this.tick; return false; }
    var social = this.tick >= c.socialFromTick;

    // карта занятости + плотность
    this._occ.fill(-1); this._crowd.fill(0);
    for (var a = 0; a < c.maxPop; a++) if (this.alive[a]) {
      this._occ[this.y[a] * W + this.x[a]] = a;
    }
    // плотность (3x3) через свёртку по занятым — считаем локально по агентам
    // (дешевле: для каждого агента посчитаем соседей в 3x3 по _occ соседям)

    var ids = [];
    for (var b = 0; b < c.maxPop; b++) if (this.alive[b]) ids.push(b);
    var k = ids.length;
    // снимок сигнала энергии до хода: self берёт свой, shuffled — переставленный
    var es = this._es || (this._es = new Float32Array(c.maxPop));
    var des = this._des || (this._des = new Float32Array(c.maxPop));
    for (var qq = 0; qq < k; qq++) {
      var idq = ids[qq];
      es[qq] = this.E[idq] / c.eMax;
      des[qq] = Math.max(-1, Math.min(1, (this.E[idq] - this.Elag[idq]) / 5));
    }
    var eshift = 0;
    if (c.interoMode === 'shuffled' && k > 1) eshift = 1 + ((this.rng() * (k - 1)) | 0);

    var X = this._X;
    for (var ii = 0; ii < ids.length; ii++) {
      var id = ids[ii];
      // ---- сенсоры ----
      X.fill(0);
      var yy = this.y[id], xx = this.x[id], hd = this.heading[id];
      for (var d = 0; d < 8; d++) {
        var dir = (hd + d) % 8;
        var ny = ((yy + OFF_Y[dir]) % H + H) % H, nx = ((xx + OFF_X[dir]) % W + W) % W;
        X[d] = this.resource[ny * W + nx];
      }
      var esi = (ii + eshift) % k;           // self: свой; shuffled: чужой (та же статистика)
      X[8] = es[esi]; X[9] = des[esi];
      X[10] = Math.min(this.age[id] / 1000, 3);
      // ближайший сосед
      var partner = -1, pd = Infinity;
      for (var nbi = 0; nbi < NB.length; nbi++) {
        var py = ((yy + NB[nbi][0]) % H + H) % H, px = ((xx + NB[nbi][1]) % W + W) % W;
        var o = this._occ[py * W + px];
        if (o >= 0 && o !== id) { partner = o; pd = NB[nbi][2]; break; }
      }
      if (partner >= 0) {
        var ddy = ((this.y[partner] - yy + H / 2) % H + H) % H - H / 2;
        var ddx = ((this.x[partner] - xx + W / 2) % W + W) % W - W / 2;
        var ang = Math.atan2(ddx, -ddy) - hd * (Math.PI / 4);
        ang = ((ang + Math.PI) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI) - Math.PI;
        X[11] = ang / Math.PI; X[12] = 1 / (1 + pd);
      }
      X[13] = 1; // bias
      X[14] = this.mem[id * N_MEM]; X[15] = this.mem[id * N_MEM + 1];
      // узнавание
      if (social && partner >= 0) {
        var best = Infinity, bj = -1;
        for (var ms = 0; ms < c.memorySlots; ms++) if (this.memValid[id * c.memorySlots + ms]) {
          var dsum = Math.abs(this.memFaces[(id * c.memorySlots + ms) * 3] - this.face[partner * 3])
            + Math.abs(this.memFaces[(id * c.memorySlots + ms) * 3 + 1] - this.face[partner * 3 + 1])
            + Math.abs(this.memFaces[(id * c.memorySlots + ms) * 3 + 2] - this.face[partner * 3 + 2]);
          if (dsum < best) { best = dsum; bj = ms; }
        }
        if (bj >= 0 && best < c.faceTol) { X[16] = 1; X[17] = this.memOut[id * c.memorySlots + bj]; }
      }
      X[18] = this.resource[yy * W + xx];
      // знаки под собой и впереди
      X[19] = this.signs[(yy * W + xx) * 2]; X[20] = this.signs[(yy * W + xx) * 2 + 1];
      var ay = ((yy + OFF_Y[hd]) % H + H) % H, ax = ((xx + OFF_X[hd]) % W + W) % W;
      X[21] = this.signs[(ay * W + ax) * 2]; X[22] = this.signs[(ay * W + ax) * 2 + 1];
      var present = Math.abs(X[19]) + Math.abs(X[20]) > 1e-3;
      if (present) {
        var mine = Math.abs(this.signAuthor[(yy * W + xx) * 3] - this.face[id * 3])
          + Math.abs(this.signAuthor[(yy * W + xx) * 3 + 1] - this.face[id * 3 + 1])
          + Math.abs(this.signAuthor[(yy * W + xx) * 3 + 2] - this.face[id * 3 + 2]) < c.faceTol;
        X[23] = mine ? 1 : 0;
      }

      // ---- forward pass ----
      var base1 = id * N_IN * N_HID, base2 = id * N_HID * N_OUT;
      var hvec = this._hvec;
      for (var jh = 0; jh < N_HID; jh++) {
        var sum = this.b1[id * N_HID + jh];
        for (var ki = 0; ki < N_IN; ki++) sum += X[ki] * this.W1[base1 + ki * N_HID + jh];
        hvec[jh] = Math.tanh(sum);
      }
      var out = this._out;
      for (var ko = 0; ko < N_OUT; ko++) {
        var so = this.b2[id * N_OUT + ko];
        for (var jj = 0; jj < N_HID; jj++) so += hvec[jj] * this.W2[base2 + jj * N_OUT + ko];
        out[ko] = so;
      }
      // память и содержание метки
      this.mem[id * N_MEM] = Math.tanh(out[N_ACT]); this.mem[id * N_MEM + 1] = Math.tanh(out[N_ACT + 1]);
      var sc0 = Math.tanh(out[N_ACT + N_MEM]), sc1 = Math.tanh(out[N_ACT + N_MEM + 1]);

      // выбор действия (argmax по логитам с масками)
      var act = 0, bestv = -Infinity;
      for (var la = 0; la < N_ACT; la++) {
        if (la === A_MARK && !c.signsEnabled) continue;
        if ((la === A_GIVE || la === A_TAKE) && !social) continue;
        if (out[la] > bestv) { bestv = out[la]; act = la; }
      }
      if (c.actionNoise > 0 && this.rng() < c.actionNoise) {
        var kk = social ? N_ACT : N_ACT - 3;
        act = (this.rng() * kk) | 0;
      }

      // метрики: дециль энергии × действие
      var bin = Math.max(0, Math.min(9, (this.E[id] / c.eMax * 10) | 0));
      this.histWin[bin * N_ACT + act]++; this.actionCounts[act]++;
      if (this.tick > 400) this.histCum[bin * N_ACT + act]++;

      var eBefore = this.E[id];

      // ---- применяем действие + метаболизм ----
      var cost = c.basal;
      // толчея: соседи в 3x3
      var crowd = 0;
      for (var cy = -1; cy <= 1; cy++) for (var cx = -1; cx <= 1; cx++) {
        var qy = ((yy + cy) % H + H) % H, qx = ((xx + cx) % W + W) % W;
        if (this._occ[qy * W + qx] >= 0) crowd++;
      }
      if (crowd > 1) cost += c.crowdCost * (crowd - 1);

      if (act === A_LEFT) { this.heading[id] = (hd + 7) % 8; cost += c.turnCost; }
      else if (act === A_RIGHT) { this.heading[id] = (hd + 1) % 8; cost += c.turnCost; }
      else if (act === A_FWD) {
        var mh = this.heading[id];
        this.y[id] = ((yy + OFF_Y[mh]) % H + H) % H; this.x[id] = ((xx + OFF_X[mh]) % W + W) % W;
        cost += c.moveCost;
      } else if (act === A_EAT) {
        var cell = yy * W + xx, take = Math.min(this.resource[cell], c.bite);
        this.resource[cell] -= take; if (this.resource[cell] < 0) this.resource[cell] = 0;
        this.E[id] += take * c.energyPerRes; cost += c.eatCost;
      } else if (act === A_MARK) {
        var cm = yy * W + xx;
        this.signs[cm * 2] = sc0; this.signs[cm * 2 + 1] = sc1;
        this.signAuthor[cm * 3] = this.face[id * 3]; this.signAuthor[cm * 3 + 1] = this.face[id * 3 + 1];
        this.signAuthor[cm * 3 + 2] = this.face[id * 3 + 2]; this.signAge[cm] = 0;
        cost += c.markCost; this.marks++;
      }

      // социальные действия
      if (social && (act === A_GIVE || act === A_TAKE) && partner >= 0 && pd <= 1.5) {
        if (act === A_GIVE) {
          this.E[id] -= c.giveCost; this.E[partner] += c.giveGain; this.coop++;
          this._remember(id, partner, 1); this._remember(partner, id, 1);
        } else {
          this.E[id] += c.takeGain; this.E[partner] -= c.takeLoss; this.defect++;
          this._remember(id, partner, -1); this._remember(partner, id, -1);
        }
      }

      this.E[id] -= cost;
      if (this.E[id] > c.eMax) this.E[id] = c.eMax; if (this.E[id] < -1) this.E[id] = -1;
      this.Elag[id] += 0.1 * (this.E[id] - this.Elag[id]);
      this.age[id]++;

      // пластичность (модулируется изменением энергии)
      if (c.hebbEnabled && this.tick % c.hebbEvery === 0) {
        var mod = Math.max(-1, Math.min(1, (this.E[id] - eBefore) / 2));
        var lr = this.lr[id] * mod * c.hebbEvery, cl = c.weightClip;
        var lastout = this._lastout;
        for (var lo = 0; lo < N_OUT; lo++) lastout[lo] = Math.tanh(out[lo]);
        for (var hj = 0; hj < N_HID; hj++) for (var ok = 0; ok < N_OUT; ok++) {
          var idx = base2 + hj * N_OUT + ok;
          var w = this.W2[idx] + lr * hvec[hj] * lastout[ok];
          this.W2[idx] = w > cl ? cl : (w < -cl ? -cl : w);
        }
      }
    }

    this._cull(); this._reproduce();
    // мир: отрост + затухание знаков
    var g = c.regrowth * Math.max(this.season(), 0);
    for (var ri = 0; ri < HW; ri++) {
      this.resource[ri] += g * (this.capacity[ri] - this.resource[ri]);
      if (this.resource[ri] < 0) this.resource[ri] = 0; else if (this.resource[ri] > 1) this.resource[ri] = 1;
    }
    if (c.signsEnabled) {
      for (var si = 0; si < HW * 2; si++) this.signs[si] *= c.signDecay;
      for (var sa = 0; sa < HW; sa++) this.signAge[sa] += 1;
    }
    this.tick++;
    return true;
  };

  Engine.prototype._remember = function (who, whom, outcome) {
    var K = this.cfg.memorySlots, p = this.memPtr[who] % K;
    this.memFaces[(who * K + p) * 3] = this.face[whom * 3];
    this.memFaces[(who * K + p) * 3 + 1] = this.face[whom * 3 + 1];
    this.memFaces[(who * K + p) * 3 + 2] = this.face[whom * 3 + 2];
    this.memOut[who * K + p] = outcome; this.memValid[who * K + p] = 1;
    this.memPtr[who] = (p + 1) % K;
  };

  Engine.prototype._cull = function () {
    var c = this.cfg;
    for (var a = 0; a < c.maxPop; a++) if (this.alive[a] && (this.E[a] <= 0 || this.age[a] > c.maxAge)) {
      this.lifespans.push(this.age[a]);
      this.alive[a] = 0; this.pop--; this.deaths++; this._free.push(a);
    }
    // не даём массиву расти бесконечно в «бессмертных» мирах
    if (this.lifespans.length > 8000) this.lifespans = this.lifespans.slice(-6000);
  };

  Engine.prototype._reproduce = function () {
    var c = this.cfg, K = c.memorySlots;
    var cand = [];
    for (var a = 0; a < c.maxPop; a++) if (this.alive[a] && this.E[a] >= c.reproThreshold) cand.push(a);
    for (var i = 0; i < cand.length; i++) {
      var s = this._free.pop(); if (s === undefined) break;
      var par = cand[i];
      this.E[par] -= (c.childEnergy + c.reproOverhead); this.Elag[par] = this.E[par];
      this.alive[s] = 1; this.pop++; this.births++;
      this.E[s] = c.childEnergy; this.Elag[s] = c.childEnergy; this.age[s] = 0;
      this.mem[s * N_MEM] = 0; this.mem[s * N_MEM + 1] = 0; this.memPtr[s] = 0;
      this.x[s] = this.x[par]; this.y[s] = this.y[par]; this.heading[s] = (this.rng() * 8) | 0;
      this.birthTick[s] = this.tick;
      for (var m = 0; m < K; m++) this.memValid[s * K + m] = 0;
      for (var f = 0; f < 3; f++) {
        var v = this.face[par * 3 + f] + this.normal() * 0.02;
        this.face[s * 3 + f] = v < 0 ? 0 : (v > 1 ? 1 : v);
      }
      // наследование мозга с мутацией
      this._inherit(par, s);
    }
  };

  Engine.prototype._inherit = function (par, s) {
    var c = this.cfg;
    this.lr[s] = Math.abs(this.lr[par] + this.normal() * c.hebbRateSigma);
    this._mutArr(this.W1, par * N_IN * N_HID, s * N_IN * N_HID, N_IN * N_HID);
    this._mutArr(this.b1, par * N_HID, s * N_HID, N_HID);
    this._mutArr(this.W2, par * N_HID * N_OUT, s * N_HID * N_OUT, N_HID * N_OUT);
    this._mutArr(this.b2, par * N_OUT, s * N_OUT, N_OUT);
  };
  Engine.prototype._mutArr = function (arr, from, to, len) {
    var c = this.cfg;
    for (var i = 0; i < len; i++) {
      var v = arr[from + i];
      if (this.rng() < c.mutationRate) v += this.normal() * c.mutationSigma;
      arr[to + i] = v;
    }
  };

  // --- метрики ---
  function miFromHist(h, rows, cols) {
    var n = 0, i, j;
    for (i = 0; i < h.length; i++) n += h[i];
    if (n < 500) return null;
    var pe = new Float64Array(rows), pa = new Float64Array(cols);
    for (i = 0; i < rows; i++) for (j = 0; j < cols; j++) { pe[i] += h[i * cols + j]; pa[j] += h[i * cols + j]; }
    var mi = 0;
    for (i = 0; i < rows; i++) for (j = 0; j < cols; j++) {
      var p = h[i * cols + j] / n; if (p <= 0) continue;
      var den = (pe[i] / n) * (pa[j] / n); if (den <= 0) continue;
      mi += p * Math.log2(p / den);
    }
    var r = 0, cc = 0;
    for (i = 0; i < rows; i++) if (pe[i] > 0) r++;
    for (j = 0; j < cols; j++) if (pa[j] > 0) cc++;
    var chance = (r > 1 && cc > 1) ? (r - 1) * (cc - 1) / (2 * n * Math.LN2) : 0;
    return mi - chance;
  }
  Engine.prototype.miWindow = function () { return miFromHist(this.histWin, 10, N_ACT); };
  Engine.prototype.occupiedDeciles = function () {
    var tot = 0, i, j;
    for (i = 0; i < 10 * N_ACT; i++) tot += this.histWin[i];
    if (!tot) return 0;
    var n = 0;
    for (i = 0; i < 10; i++) { var s = 0; for (j = 0; j < N_ACT; j++) s += this.histWin[i * N_ACT + j]; if (s / tot > 0.01) n++; }
    return n;
  };
  Engine.prototype.miEpisode = function () { return miFromHist(this.histCum, 10, N_ACT); };
  Engine.prototype.resetWindow = function () { this.histWin.fill(0); };
  Engine.prototype.coopRate = function () {
    var t = this.coop + this.defect; return t ? this.coop / t : null;
  };
  Engine.prototype.meanE = function () {
    var s = 0, n = 0;
    for (var a = 0; a < this.cfg.maxPop; a++) if (this.alive[a]) { s += this.E[a]; n++; }
    return n ? s / n : 0;
  };
  Engine.prototype.medianLife = function () {
    if (!this.lifespans.length) return 0;
    var a = this.lifespans.slice().sort(function (x, y) { return x - y; });
    return a[a.length >> 1];
  };

  // --- поиск жизнеспособного предка (как в Python) ---
  function gauss(rng) {
    var u = 1 - rng(), v = rng();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  }
  function randomGenome(rng, cfg) {
    var sg = cfg.initWeightSigma;
    var g = { W1: new Float32Array(N_IN * N_HID), b1: new Float32Array(N_HID),
              W2: new Float32Array(N_HID * N_OUT), b2: new Float32Array(N_OUT) };
    for (var i = 0; i < g.W1.length; i++) g.W1[i] = gauss(rng) * sg;
    for (var j = 0; j < g.W2.length; j++) g.W2[j] = gauss(rng) * sg;
    g.b2[A_FWD] += 0.5; g.b2[A_EAT] += 0.5;
    return g;
  }
  function fwdAct(g, X) {
    var h = new Float32Array(N_HID);
    for (var jh = 0; jh < N_HID; jh++) {
      var s = g.b1[jh];
      for (var ki = 0; ki < N_IN; ki++) s += X[ki] * g.W1[ki * N_HID + jh];
      h[jh] = Math.tanh(s);
    }
    var act = 0, best = -Infinity;
    for (var ko = 0; ko < N_ACT; ko++) {
      if (ko === A_GIVE || ko === A_TAKE || ko === A_MARK) continue;
      var so = g.b2[ko];
      for (var jj = 0; jj < N_HID; jj++) so += h[jj] * g.W2[jj * N_OUT + ko];
      if (so > best) { best = so; act = ko; }
    }
    return act;
  }
  function passesSynthetic(g) {
    var X0 = new Float32Array(N_IN); X0[18] = 0.8; X0[8] = 0.5; X0[13] = 1;
    var X1 = new Float32Array(N_IN); X1[0] = 0.8; X1[8] = 0.3; X1[13] = 1;
    return fwdAct(g, X0) === A_EAT && fwdAct(g, X1) === A_FWD;
  }
  function findViableAncestor(seed, cfg, opts) {
    opts = opts || {};
    var maxTries = opts.maxTries || 8000, synthCap = opts.synthCap || 200;
    var rng = mulberry32((seed * 1000003 + 7) >>> 0);
    var mini = Object.assign(defaults(), cfg || {}, {
      H: 48, W: 48, initPop: 24, maxPop: 400, crowdCost: 0, seasonPeriod: 0,
      socialFromTick: 1e9, signsEnabled: false, hebbEnabled: false, actionNoise: 0,
      foundingSigma: 0.05
    });
    var synth = 0;
    for (var attempt = 1; attempt <= maxTries; attempt++) {
      var g = randomGenome(rng, mini);
      if (!passesSynthetic(g)) continue;
      synth++;
      var eng = new Engine(seed, mini, g);
      for (var t = 0; t < 3000; t++) if (!eng.step()) break;
      if (eng.extinctAt === null && eng.pop >= 36) return { genome: g, tries: attempt };
      if (synth > synthCap) break;
    }
    return null;
  }

  var API = { Engine: Engine, miFromHist: miFromHist,
    findViableAncestor: findViableAncestor, randomGenome: randomGenome,
    passesSynthetic: passesSynthetic, defaults: defaults,
    A: { FWD: A_FWD, LEFT: A_LEFT, RIGHT: A_RIGHT, EAT: A_EAT, REST: A_REST, GIVE: A_GIVE, TAKE: A_TAKE, MARK: A_MARK } };
  if (typeof module !== "undefined" && module.exports) module.exports = API;
  root.MiniWorld = API;
})(typeof globalThis !== "undefined" ? globalThis : this);
