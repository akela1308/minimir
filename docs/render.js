/* mini-world: общий слой отрисовки живых миров.
   Семантика не меняется ни на пиксель: тот же вид сверху, одна клетка поля
   это одна клетка данных. Меняется только то, чем клетка нарисована, и то,
   какую часть мира видно.

   Что рисуется и что это значит:
     фон плитки      служебный шум, чтобы пол не был плоским, данных не несёт
     цвет клетки     тип еды (мир B) или плодородность почвы (мир A)
     яркость клетки  количество ресурса в клетке
     растение        тот же ресурс, но на близком плане: три стадии роста
     ореол вокруг    тот же ресурс, размазанный на соседей, чтобы еда светилась
     существо        один агент, цвет это его энергия, форма одна на всех
     плитка и рамка  оформление, данных в них нет                              */
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
  function rgb(a) { return 'rgb(' + a[0] + ',' + a[1] + ',' + a[2] + ')'; }

  // ---------- камера ----------
  // Масштаб всегда целое число пикселей на клетку, иначе пиксель-арт плывёт.
  function camera(cv, W, H) {
    var cam = {
      cell: 4, ox: 0, oy: 0, dx: 0, dy: 0, cols: W, rows: H,
      level: 0, levels: [4], W: W, H: H, followFn: null
    };
    function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }

    cam.resize = function () {
      var dpr = Math.min(global.devicePixelRatio || 1, 2);
      var css = cv.clientWidth || cv.width || 512;
      // размер холста кратен числу клеток, тогда на общем виде мир ложится
      // ровно в кадр: ни полей по краям, ни дробного растягивания пикселей
      var fitCell = Math.round(css * dpr / W); if (fitCell < 2) fitCell = 2;
      var px = fitCell * W;
      if (cv.width !== px) { cv.width = px; cv.height = px; }
      var ls = [fitCell], extra = [8, 12, 16, 24];
      for (var i = 0; i < extra.length; i++) if (extra[i] > fitCell * 1.3) ls.push(extra[i]);
      cam.levels = ls;
      if (cam.level >= ls.length) cam.level = ls.length - 1;
      cam.cell = ls[cam.level];
      cam.update();
    };

    cam.update = function () {
      var vw = cv.width, vh = cv.height, c = cam.cell;
      var wpx = W * c, hpx = H * c;
      if (wpx <= vw) { cam.ox = 0; cam.dx = ((vw - wpx) / 2) | 0; cam.cols = W; }
      else { cam.dx = 0; cam.cols = Math.ceil(vw / c) + 1; cam.ox = clamp(cam.ox, 0, W - vw / c); }
      if (hpx <= vh) { cam.oy = 0; cam.dy = ((vh - hpx) / 2) | 0; cam.rows = H; }
      else { cam.dy = 0; cam.rows = Math.ceil(vh / c) + 1; cam.oy = clamp(cam.oy, 0, H - vh / c); }
    };

    cam.fit = function () { cam.level = 0; cam.cell = cam.levels[0]; cam.followFn = null; cam.update(); };
    cam.zoomed = function () { return cam.level > 0; };
    cam.setLevel = function (i, ax, ay) {
      i = clamp(i, 0, cam.levels.length - 1);
      if (i === cam.level) return;
      // точка под курсором остаётся на месте
      var cx = ax == null ? cv.width / 2 : ax, cy = ay == null ? cv.height / 2 : ay;
      var wx = cam.ox + (cx - cam.dx) / cam.cell, wy = cam.oy + (cy - cam.dy) / cam.cell;
      cam.level = i; cam.cell = cam.levels[i];
      cam.ox = wx - (cx - 0) / cam.cell; cam.oy = wy - (cy - 0) / cam.cell;
      if (i === 0) cam.followFn = null;
      cam.update();
    };
    cam.zoom = function (d, ax, ay) { cam.setLevel(cam.level + d, ax, ay); };
    cam.panPx = function (dxp, dyp) {
      if (!cam.zoomed()) return;
      cam.followFn = null;
      cam.ox -= dxp / cam.cell; cam.oy -= dyp / cam.cell; cam.update();
    };
    cam.centerOn = function (wx, wy) {
      cam.ox = wx - cv.width / (2 * cam.cell);
      cam.oy = wy - cv.height / (2 * cam.cell);
      cam.update();
    };
    cam.follow = function (fn) {
      cam.followFn = fn;
      if (fn && cam.level === 0) cam.setLevel(Math.min(2, cam.levels.length - 1));
    };
    cam.tick = function () {
      if (!cam.followFn) return;
      var p = cam.followFn();
      if (p) cam.centerOn(p[0], p[1]); else cam.followFn = null;
    };
    cam.visible = function (wx, wy, pad) {
      pad = pad || 1;
      return wx >= cam.ox - pad && wx <= cam.ox + cv.width / cam.cell + pad &&
        wy >= cam.oy - pad && wy <= cam.oy + cv.height / cam.cell + pad;
    };
    cam.sx = function (wx) { return (wx - cam.ox) * cam.cell + cam.dx; };
    cam.sy = function (wy) { return (wy - cam.oy) * cam.cell + cam.dy; };

    // ---------- ввод: перетаскивание, колесо, щипок ----------
    cam.attach = function (onChange) {
      var pts = {}, last = null, pinch = null, moved = 0;
      function emit() { if (onChange) onChange(); }
      cv.style.touchAction = 'pan-y';
      cv.addEventListener('pointerdown', function (e) {
        pts[e.pointerId] = { x: e.clientX, y: e.clientY };
        var ids = Object.keys(pts);
        if (ids.length === 1) { last = { x: e.clientX, y: e.clientY }; moved = 0; cv.setPointerCapture(e.pointerId); }
        else if (ids.length === 2) {
          var a = pts[ids[0]], b = pts[ids[1]];
          pinch = Math.hypot(a.x - b.x, a.y - b.y);
        }
      });
      cv.addEventListener('pointermove', function (e) {
        if (!pts[e.pointerId]) return;
        pts[e.pointerId] = { x: e.clientX, y: e.clientY };
        var ids = Object.keys(pts);
        if (ids.length === 2 && pinch) {
          var a = pts[ids[0]], b = pts[ids[1]], d = Math.hypot(a.x - b.x, a.y - b.y);
          if (d / pinch > 1.35) { cam.zoom(1); pinch = d; emit(); }
          else if (pinch / d > 1.35) { cam.zoom(-1); pinch = d; emit(); }
          e.preventDefault(); return;
        }
        if (ids.length === 1 && last && cam.zoomed()) {
          var k = cv.width / cv.clientWidth;
          var ddx = (e.clientX - last.x) * k, ddy = (e.clientY - last.y) * k;
          moved += Math.abs(ddx) + Math.abs(ddy);
          cam.panPx(ddx, ddy); last = { x: e.clientX, y: e.clientY };
          e.preventDefault(); emit();
        }
      });
      function up(e) {
        delete pts[e.pointerId];
        if (Object.keys(pts).length < 2) pinch = null;
        if (!Object.keys(pts).length) last = null;
      }
      cv.addEventListener('pointerup', up);
      cv.addEventListener('pointercancel', up);
      cv.addEventListener('dblclick', function (e) {
        var r = cv.getBoundingClientRect(), k = cv.width / r.width;
        cam.zoom(1, (e.clientX - r.left) * k, (e.clientY - r.top) * k); emit();
      });
      // Колесо приближает только когда мир уже приближён или зажат Ctrl,
      // иначе страницу было бы не прокрутить мимо экрана.
      cv.addEventListener('wheel', function (e) {
        if (!cam.zoomed() && !e.ctrlKey && !e.metaKey) return;
        e.preventDefault();
        var r = cv.getBoundingClientRect(), k = cv.width / r.width;
        cam.zoom(e.deltaY < 0 ? 1 : -1, (e.clientX - r.left) * k, (e.clientY - r.top) * k);
        emit();
      }, { passive: false });
      return cam;
    };

    cam.resize();
    return cam;
  }

  // ---------- спрайт существа ----------
  // Купол строится по эллипсу, под ним юбка и четыре щупальца. Размер клетки
  // задаёт и размер существа, и крупность его собственных пикселей.
  function creatureGrid(cell) {
    // на общем виде клетка бывает в два-три пикселя: там существо это точка,
    // медузка туда просто не влезет и залепила бы соседей
    if (cell < 6) { var m = Math.max(3, cell + 1); return { n: m, k: 1, body: m, small: true }; }
    var n = cell <= 9 ? 8 : cell <= 14 ? 12 : 16;
    var k = Math.round((cell + 2) / n); if (k < 1) k = 1;
    return { n: n, k: k, body: n * k, small: false };
  }
  function blobMask(n) {
    var m = new Uint8Array(n * n), c = (n - 1) / 2, r = n / 2;
    for (var y = 0; y < n; y++) for (var x = 0; x < n; x++) {
      var d = Math.hypot(x - c, y - c);
      if (d > r) continue;
      m[y * n + x] = d < r * 0.45 ? 2 : d > r - 0.9 ? 3 : 1;
    }
    return m;
  }
  function creatureMask(n, phase) {
    var m = new Uint8Array(n * n), x, y;
    var domeH = Math.max(3, Math.round(n * 0.56)), cx = (n - 1) / 2, rx = n / 2;
    for (y = 0; y < domeH; y++) {
      var dy = (domeH - 1 - y) / domeH;
      var hw = rx * Math.sqrt(Math.max(0, 1 - dy * dy));
      for (x = 0; x < n; x++) {
        var d = Math.abs(x - cx);
        if (d > hw) continue;
        var v = 1;
        if (y < domeH * 0.34 && d < hw * 0.75) v = 2;          // блик купола
        else if (d > hw - 1.05) v = 3;                          // край
        m[y * n + x] = v;
      }
    }
    // глаза
    var ey = Math.round(domeH * 0.60), ex = Math.round(n * 0.20);
    var es = n >= 12 ? 2 : 1;
    for (y = 0; y < es; y++) for (x = 0; x < es; x++) {
      var l = (cx - ex + x) | 0, r = (cx + ex - es + 1 + x) | 0, yy = ey + y;
      if (yy < n) { if (m[yy * n + l]) m[yy * n + l] = 4; if (m[yy * n + r]) m[yy * n + r] = 4; }
    }
    // юбка: волна по нижнему краю купола
    var sy = domeH, sh = Math.max(1, Math.round(n * 0.08));
    for (y = sy; y < sy + sh && y < n; y++) {
      var dy2 = (y - sy + domeH - 1) / domeH;
      var hw2 = rx * Math.sqrt(Math.max(0, 1 - Math.min(1, dy2 * dy2))) || rx * 0.8;
      for (x = 0; x < n; x++) {
        if (Math.abs(x - cx) > hw2) continue;
        if ((x + phase) % 3 === 0) continue;
        m[y * n + x] = 3;
      }
    }
    // щупальца
    var tN = n >= 12 ? 4 : 3, top = sy + sh, len = n - top;
    for (var i = 0; i < tN; i++) {
      var bx = cx + (i - (tN - 1) / 2) * (n * (tN === 4 ? 0.21 : 0.26));
      for (y = 0; y < len; y++) {
        var t = y / Math.max(1, len - 1);
        var off = Math.sin(t * 3.0 + phase * 1.7 + i * 1.1) * n * 0.07;
        var px = Math.round(bx + off), py = top + y;
        if (px < 0 || px >= n || py >= n) continue;
        m[py * n + px] = t > 0.72 ? 3 : 1;
        if (n >= 14 && t < 0.5 && px + 1 < n) m[py * n + px + 1] = 1;
      }
    }
    return m;
  }
  function atlas(cell) {
    var g = creatureGrid(cell), n = g.n, k = g.k, body = g.body;
    var pad = Math.round(body * 0.40); if (pad < 2) pad = 2;
    var size = body + pad * 2, levels = 8, phases = 3;
    var sheet = document.createElement('canvas');
    sheet.width = size * levels; sheet.height = size * phases;
    var c = sheet.getContext('2d');
    for (var p = 0; p < phases; p++) {
      var m = g.small ? blobMask(n) : creatureMask(n, p);
      for (var l = 0; l < levels; l++) {
        var col = energyRGB(l / (levels - 1));
        var ox = l * size, oy = p * size, ccx = ox + size / 2, ccy = oy + size / 2;
        var gr = c.createRadialGradient(ccx, ccy, 0, ccx, ccy, size / 2);
        gr.addColorStop(0, 'rgba(' + col + ',0.42)');
        gr.addColorStop(0.5, 'rgba(' + col + ',0.13)');
        gr.addColorStop(1, 'rgba(' + col + ',0)');
        c.fillStyle = gr; c.fillRect(ox, oy, size, size);
        var hi = mix(col, [255, 255, 255], 0.45), dk = scal(col, 0.46), eye = [8, 12, 14];
        for (var y = 0; y < n; y++) for (var x = 0; x < n; x++) {
          var v = m[y * n + x]; if (!v) continue;
          c.fillStyle = v === 1 ? rgb(col) : v === 2 ? rgb(hi) : v === 3 ? rgb(dk) : rgb(eye);
          c.fillRect(ox + pad + x * k, oy + pad + y * k, k, k);
        }
      }
    }
    return { sheet: sheet, size: size, half: (size / 2) | 0, levels: levels, phases: phases };
  }
  function agent(ctx, A, px, py, t01, phase) {
    var l = (t01 * (A.levels - 1) + 0.5) | 0;
    if (l < 0) l = 0; else if (l >= A.levels) l = A.levels - 1;
    ctx.drawImage(A.sheet, l * A.size, (phase % A.phases) * A.size, A.size, A.size,
      (px - A.half) | 0, (py - A.half) | 0, A.size, A.size);
  }

  // ---------- растения ----------
  // Три стадии по количеству ресурса в клетке. Рисуются только на близком
  // плане, на общем виде ресурс по-прежнему показан яркостью клетки.
  var PLANT = [[
    '........', '........', '........', '...22...',
    '..1221..', '...11...', '...11...', '..4444..'
  ], [
    '........', '...22...', '..1221..', '.122221.',
    '..1221..', '...11...', '...11...', '..4444..'
  ], [
    '.2....2.', '122..221', '.12..21.', '..1221..',
    '.123321.', '..1221..', '...11...', '..4444..'
  ]];
  function plantSheet(cell, hues) {
    var k = Math.max(1, Math.round(cell / 8)), s = 8 * k, V = 2;
    // ядовитые цвета остаются тусклыми: засохшее растение, а не светлое
    hues = hues.map(function (h, i) { return i >= 2 ? scal(h, 0.70) : h; });
    var cv = document.createElement('canvas');
    cv.width = s * PLANT.length * V; cv.height = s * hues.length;
    var c = cv.getContext('2d');
    for (var h = 0; h < hues.length; h++) {
      var dead = h >= 2;
      var col = hues[h],
        hi = mix(col, [255, 255, 255], dead ? 0.10 : 0.30),
        core = mix(col, [255, 255, 255], dead ? 0.22 : 0.60),
        base = scal(col, 0.34);
      for (var st = 0; st < PLANT.length; st++) {
        for (var v = 0; v < V; v++) {
          var rows = PLANT[st], ox = (st * V + v) * s, oy = h * s;
          for (var y = 0; y < 8; y++) for (var x = 0; x < 8; x++) {
            var ax = v ? 7 - x : x;
            var ch = rows[y].charAt(ax); if (ch === '.') continue;
            c.fillStyle = ch === '1' ? rgb(col) : ch === '2' ? rgb(hi) : ch === '3' ? rgb(core) : rgb(base);
            c.fillRect(ox + x * k, oy + y * k, k, k);
          }
        }
      }
    }
    return { sheet: cv, size: s, stages: PLANT.length, variants: V };
  }
  function plant(ctx, P, hueIdx, stage, variant, px, py) {
    ctx.drawImage(P.sheet, (stage * P.variants + (variant % P.variants)) * P.size, hueIdx * P.size,
      P.size, P.size, px | 0, py | 0, P.size, P.size);
  }

  // ---------- пол ----------
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

  // Мир B: два цвета еды, один сейчас ядовит и потому тусклее и обесцвеченнее.
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
      var w = core > 0.74 ? (core - 0.74) * 5.0 * dim : 0;
      var j = i * 4;
      d[j] = 13 + z + hue[0] * k + 60 * w;
      d[j + 1] = 17 + z + hue[1] * k + 60 * w;
      d[j + 2] = 21 + z + hue[2] * k + 60 * w;
      d[j + 3] = 255;
    }
  }
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

  // Перенос пола на экран с учётом камеры.
  function blitFloor(ctx, off, cam) {
    var c = cam.cell, sx = Math.floor(cam.ox), sy = Math.floor(cam.oy);
    var fx = cam.ox - sx, fy = cam.oy - sy;
    var cols = Math.min(cam.cols, cam.W - sx), rows = Math.min(cam.rows, cam.H - sy);
    ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
    ctx.drawImage(off, sx, sy, cols, rows,
      Math.round(cam.dx - fx * c), Math.round(cam.dy - fy * c), cols * c, rows * c);
  }

  // ---------- сетка ----------
  var patCache = {};
  function tilePattern(ctx, cell) {
    var t = cell * 8, key = 't' + t, p = patCache[key];
    if (p) return p;
    var cv = document.createElement('canvas'); cv.width = cv.height = t;
    var c = cv.getContext('2d'), q = cell * 4, i;
    for (i = 0; i < t; i += q) {
      c.fillStyle = 'rgba(190,225,240,0.034)'; c.fillRect(0, i, t, 1); c.fillRect(i, 0, 1, t);
      c.fillStyle = 'rgba(0,0,0,0.30)'; c.fillRect(0, i + q - 1, t, 1); c.fillRect(i + q - 1, 0, 1, t);
    }
    // крошка на полу: та же фактура, что и шум плитки, просто крупнее
    if (cell >= 8) {
      var r = 1234567;
      for (i = 0; i < 26; i++) {
        r = (Math.imul(r, 1664525) + 1013904223) >>> 0;
        var x = r % t; r = (Math.imul(r, 1664525) + 1013904223) >>> 0;
        var y = r % t; r = (Math.imul(r, 1664525) + 1013904223) >>> 0;
        var sz = 1 + (r % 2) * (cell >= 16 ? 2 : 1);
        c.fillStyle = (r % 3) ? 'rgba(0,0,0,0.26)' : 'rgba(190,225,240,0.055)';
        c.fillRect(x, y, sz, sz);
      }
    }
    p = ctx.createPattern(cv, 'repeat'); patCache[key] = p; return p;
  }
  function gridlines(ctx, cam) {
    var c = cam.cell, w = ctx.canvas.width, h = ctx.canvas.height;
    ctx.save();
    ctx.translate(Math.round(cam.dx - (cam.ox % 8) * c), Math.round(cam.dy - (cam.oy % 8) * c));
    ctx.fillStyle = tilePattern(ctx, c);
    ctx.fillRect(0, 0, w + c * 8, h + c * 8);
    ctx.restore();
    var s = 32, x0 = Math.ceil(cam.ox / s) * s, y0 = Math.ceil(cam.oy / s) * s;
    ctx.fillStyle = 'rgba(160,210,225,0.085)';
    for (var x = x0; x < cam.ox + w / c; x += s) ctx.fillRect(Math.round(cam.sx(x)), 0, 1, h);
    for (var y = y0; y < cam.oy + h / c; y += s) ctx.fillRect(0, Math.round(cam.sy(y)), w, 1);
  }

  global.MiniRender = {
    energyRGB: energyRGB, camera: camera, atlas: atlas, agent: agent,
    plantSheet: plantSheet, plant: plant, floorA: floorA, floorB: floorB,
    blitFloor: blitFloor, gridlines: gridlines, halo: halo, tileNoise: tileNoise,
    HUE_B: HUE_B
  };
})(window);
