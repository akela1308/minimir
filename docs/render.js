/* mini-world: общий слой отрисовки живых миров.
   Семантика не меняется ни на пиксель: это тот же вид сверху, одна клетка
   поля это одна клетка данных. Меняется только то, чем клетка нарисована.

   Что рисуется и что это значит:
     фон плитки      служебный шум, чтобы пол не был плоским, данных не несёт
     цвет клетки     тип еды (мир B) или плодородность (мир A)
     яркость клетки  количество ресурса в клетке
     ореол вокруг    тот же ресурс, размазанный на соседей, чтобы еда светилась
     существо        один агент, цвет это его энергия, форма одна на всех
     сетка линий     каждые 8 и 32 клетки, чтобы читался масштаб

   Сетка, рамка, сканлайны и виньетка это оформление, данных в них нет.       */
(function (global) {
  'use strict';

  // ---------- палитра ----------
  // Тот же градиент энергии, что был: янтарный голодный, голубой сытый.
  function energyRGB(t) {
    var r, g, b, u;
    if (t < 0.5) { u = t / 0.5; r = 0xe8 + (0xd9 - 0xe8) * u; g = 0x73 + (0xc2 - 0x73) * u; b = 0x4a + (0x6a - 0x4a) * u; }
    else { u = (t - 0.5) / 0.5; r = 0xd9 + (0x46 - 0xd9) * u; g = 0xc2 + (0xc6 - 0xc2) * u; b = 0x6a + (0xd0 - 0x6a) * u; }
    return [r | 0, g | 0, b | 0];
  }
  function mix(a, b, k) { return [a[0] + (b[0] - a[0]) * k | 0, a[1] + (b[1] - a[1]) * k | 0, a[2] + (b[2] - a[2]) * k | 0]; }
  function scal(a, k) { return [a[0] * k | 0, a[1] * k | 0, a[2] * k | 0]; }

  // ---------- масштаб ----------
  // Целое число пикселей на клетку, иначе пиксель-арт плывёт при растягивании.
  function fit(cv, W) {
    var dpr = Math.min(global.devicePixelRatio || 1, 2);
    var css = cv.clientWidth || cv.width || 512;
    var cell = Math.round(css * dpr / W);
    if (cell < 2) cell = 2; if (cell > 14) cell = 14;
    var px = cell * W;
    if (cv.width !== px) { cv.width = px; cv.height = px; }
    return cell;
  }

  // ---------- спрайт существа ----------
  // 1 тело, 2 блик купола, 3 тень, 4 глаз. Две фазы, щупальца шевелятся.
  var ART_A = [
    '..2222..',
    '.222222.',
    '22111122',
    '21141412',
    '21111112',
    '.311113.',
    '.3.11.3.',
    '..1..1..'
  ];
  var ART_B = [
    '..2222..',
    '.222222.',
    '22111122',
    '21141412',
    '21111112',
    '.311113.',
    '..311.3.',
    '.1..1..1'
  ];
  var ART_S = [
    '.22.',
    '2442',
    '2112',
    '.1.1'
  ];

  function atlas(cell) {
    var phases = cell >= 5 ? [ART_A, ART_B] : [ART_S, ART_S];
    var n = phases[0].length;
    var k = Math.round((cell + 2) / n); if (k < 1) k = 1;
    var body = n * k;
    var pad = Math.round(body * 0.45); if (pad < 2) pad = 2;
    var size = body + pad * 2;
    var levels = 8;
    var sheet = document.createElement('canvas');
    sheet.width = size * levels; sheet.height = size * phases.length;
    var c = sheet.getContext('2d');
    for (var p = 0; p < phases.length; p++) {
      for (var l = 0; l < levels; l++) {
        var rgb = energyRGB(l / (levels - 1));
        var ox = l * size, oy = p * size, cx = ox + size / 2, cy = oy + size / 2;
        var g = c.createRadialGradient(cx, cy, 0, cx, cy, size / 2);
        g.addColorStop(0, 'rgba(' + rgb + ',0.46)');
        g.addColorStop(0.5, 'rgba(' + rgb + ',0.15)');
        g.addColorStop(1, 'rgba(' + rgb + ',0)');
        c.fillStyle = g; c.fillRect(ox, oy, size, size);
        var hi = mix(rgb, [255, 255, 255], 0.45), dk = scal(rgb, 0.48), eye = [8, 12, 14];
        var rows = phases[p];
        for (var y = 0; y < rows.length; y++) {
          var row = rows[y];
          for (var x = 0; x < row.length; x++) {
            var ch = row.charAt(x); if (ch === '.') continue;
            c.fillStyle = 'rgb(' + (ch === '1' ? rgb : ch === '2' ? hi : ch === '3' ? dk : eye) + ')';
            c.fillRect(ox + pad + x * k, oy + pad + y * k, k, k);
          }
        }
      }
    }
    return { sheet: sheet, size: size, half: (size / 2) | 0, levels: levels, phases: phases.length };
  }

  function agent(ctx, A, px, py, t01, phase) {
    var l = (t01 * (A.levels - 1) + 0.5) | 0;
    if (l < 0) l = 0; else if (l >= A.levels) l = A.levels - 1;
    ctx.drawImage(A.sheet, l * A.size, (phase % A.phases) * A.size, A.size, A.size,
      px - A.half, py - A.half, A.size, A.size);
  }

  // ---------- пол ----------
  // Шум плитки считается один раз на размер мира: география не меняется.
  var noiseCache = {};
  function tileNoise(W, H) {
    var key = W + 'x' + H, a = noiseCache[key];
    if (a) return a;
    a = new Int8Array(W * H);
    for (var y = 0; y < H; y++) for (var x = 0; x < W; x++) {
      var h = (Math.imul(x, 73856093) ^ Math.imul(y, 19349663)) >>> 0;
      h = (h ^ (h >>> 13)) >>> 0;
      var v = (h % 9) - 4;
      var s = (Math.imul(x >> 2, 83492791) ^ Math.imul(y >> 2, 2971215)) >>> 0;
      s = (s ^ (s >>> 11)) >>> 0;
      a[y * W + x] = v + ((s % 7) - 3);
    }
    noiseCache[key] = a; return a;
  }

  // Ореол: максимум ресурса по кресту 3x3, двумя проходами. Нужен только
  // затем, чтобы кормовое пятно светилось, а не обрывалось по краю клетки.
  var haloBuf = {};
  function halo(res, W, H) {
    var key = W + 'x' + H, b = haloBuf[key];
    if (!b) b = haloBuf[key] = { h: new Float32Array(W * H), v: new Float32Array(W * H) };
    var h = b.h, v = b.v, i, x, y, o, m;
    for (y = 0; y < H; y++) {
      o = y * W;
      for (x = 0; x < W; x++) {
        m = res[o + x];
        if (x > 0 && res[o + x - 1] > m) m = res[o + x - 1];
        if (x < W - 1 && res[o + x + 1] > m) m = res[o + x + 1];
        h[o + x] = m;
      }
    }
    for (y = 0; y < H; y++) {
      o = y * W;
      for (x = 0; x < W; x++) {
        i = o + x; m = h[i];
        if (y > 0 && h[i - W] > m) m = h[i - W];
        if (y < H - 1 && h[i + W] > m) m = h[i + W];
        v[i] = m;
      }
    }
    return v;
  }

  // Мир B: два цвета еды, один из них сейчас ядовит и потому пригашен.
  // 0 и 1 съедобные цвета, 2 и 3 они же в ядовитом состоянии: тусклее и
  // обесцвеченнее, чтобы смена правила читалась сразу всем экраном.
  var HUE_B = [[0xe6, 0xa2, 0x4e], [0x34, 0xbc, 0xd4], [0x5c, 0x4e, 0x42], [0x3c, 0x4e, 0x56]];
  function floorB(img, eng) {
    var W = eng.cfg.W, H = eng.cfg.H, d = img.data, res = eng.resource,
      ft = eng.foodType, gt = eng.goodType, nz = tileNoise(W, H), hl = halo(res, W, H);
    for (var i = 0, n = W * H; i < n; i++) {
      var good = ft[i] === gt, hue = good ? HUE_B[ft[i]] : HUE_B[ft[i] + 2], dim = good ? 1 : 0.5, z = nz[i];
      var core = res[i] * 1.7; if (core > 1) core = 1;
      var glow = hl[i] * 1.7; if (glow > 1) glow = 1;
      var k = core > glow * 0.34 ? core : glow * 0.34;
      k *= dim;
      var w = core > 0.74 ? (core - 0.74) * 5.0 * dim : 0;   // кристалл в центре пятна
      var j = i * 4;
      d[j] = 10 + z + hue[0] * k + 60 * w;
      d[j + 1] = 14 + z + hue[1] * k + 60 * w;
      d[j + 2] = 17 + z + hue[2] * k + 60 * w;
      d[j + 3] = 255;
    }
  }

  // Мир A: одна еда, фон это плодородность почвы.
  function floorA(img, eng) {
    var W = eng.cfg.W, H = eng.cfg.H, d = img.data, res = eng.resource,
      cap = eng.capacity, nz = tileNoise(W, H), hl = halo(res, W, H);
    for (var i = 0, n = W * H; i < n; i++) {
      var c = cap[i], z = nz[i];
      var core = res[i] * 1.7; if (core > 1) core = 1;
      var glow = hl[i] * 1.7; if (glow > 1) glow = 1;
      var k = core > glow * 0.34 ? core : glow * 0.34;
      var w = core > 0.74 ? (core - 0.74) * 5.0 : 0;
      var j = i * 4;
      d[j] = 10 + z + 14 * c + 22 * k + 48 * w;
      d[j + 1] = 15 + z + 28 * c + 118 * k + 52 * w;
      d[j + 2] = 18 + z + 22 * c + 62 * k + 50 * w;
      d[j + 3] = 255;
    }
  }

  // ---------- сетка ----------
  // Пол выкладывается плиткой по 4 клетки: светлая фаска сверху слева, тень
  // снизу справа. Это оформление, границы плиток ничего не значат.
  var patCache = {};
  function tilePattern(ctx, cell) {
    var t = cell * 4, key = 't' + t, p = patCache[key];
    if (p) return p;
    var cv = document.createElement('canvas'); cv.width = cv.height = t;
    var c = cv.getContext('2d');
    c.fillStyle = 'rgba(190,225,240,0.030)'; c.fillRect(0, 0, t, 1); c.fillRect(0, 0, 1, t);
    c.fillStyle = 'rgba(0,0,0,0.26)'; c.fillRect(0, t - 1, t, 1); c.fillRect(t - 1, 0, 1, t);
    p = ctx.createPattern(cv, 'repeat'); patCache[key] = p; return p;
  }
  function gridlines(ctx, cell, W, H) {
    var x, y, w = W * cell, h = H * cell;
    ctx.fillStyle = tilePattern(ctx, cell);
    ctx.fillRect(0, 0, w, h);
    var s = cell * 32;
    ctx.fillStyle = 'rgba(160,210,225,0.085)';
    for (x = s; x < w; x += s) ctx.fillRect(x, 0, 1, h);
    for (y = s; y < h; y += s) ctx.fillRect(0, y, w, 1);
  }

  global.MiniRender = {
    energyRGB: energyRGB, fit: fit, atlas: atlas, agent: agent,
    floorA: floorA, floorB: floorB, gridlines: gridlines, halo: halo, tileNoise: tileNoise
  };
})(window);
