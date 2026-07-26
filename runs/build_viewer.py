"""Собрать самодостаточную HTML-страницу проигрывателя, вшив recording.json.

Данные (base64) вшиваются в разметку программно, чтобы страница не делала
внешних запросов (строгий CSP артефакта). На выход — minimir_viewer.html.
"""
from pathlib import Path

DATA = Path("runs/recording.json").read_text()

TEMPLATE = r"""<title>мини-мир — проигрыватель прогона</title>
<style>
  :root{
    --ground:#0a0e11; --panel:#10161a; --panel2:#0d1317; --hair:#1c262c;
    --ink:#e9f1f2; --dim:#8fa3ab; --faint:#5b6f77;
    --cyan:#46c6d0; --amber:#e8734a; --mark:#e6c14a; --coop:#4fd08a;
    --mono:ui-monospace,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace;
  }
  *{box-sizing:border-box}
  body{
    margin:0;background:
      radial-gradient(1200px 700px at 70% -10%,#101a1f 0%,var(--ground) 55%);
    color:var(--ink);font-family:var(--mono);
    -webkit-font-smoothing:antialiased;line-height:1.5;
  }
  .wrap{max-width:1120px;margin:0 auto;padding:28px 20px 56px}
  header{display:flex;flex-wrap:wrap;align-items:baseline;gap:10px 18px;
    border-bottom:1px solid var(--hair);padding-bottom:16px}
  h1{font-size:22px;font-weight:600;letter-spacing:.5px;margin:0;
    text-wrap:balance}
  h1 .dot{color:var(--cyan)}
  .eyebrow{font-size:11px;letter-spacing:2.5px;text-transform:uppercase;
    color:var(--faint)}
  .thesis{flex-basis:100%;color:var(--dim);font-size:13px;max-width:70ch;
    margin-top:4px}
  .cond{flex-basis:100%;color:var(--cyan);font-size:12px;letter-spacing:.4px}

  .stage{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:22px;
    margin-top:22px;align-items:start}
  @media(max-width:840px){.stage{grid-template-columns:1fr}}

  .screen{position:relative;background:#05080a;border:1px solid var(--hair);
    border-radius:6px;overflow:hidden;box-shadow:inset 0 0 60px #04070980}
  canvas{display:block;width:100%;height:auto;image-rendering:pixelated}
  .scan{position:absolute;inset:0;pointer-events:none;
    background:repeating-linear-gradient(0deg,#0000 0 3px,#00000018 3px 4px)}
  .hud{position:absolute;top:10px;left:12px;font-size:11px;color:var(--dim);
    letter-spacing:.5px;text-shadow:0 1px 2px #000}
  .hud b{color:var(--ink);font-weight:600}

  .rail{display:flex;flex-direction:column;gap:14px}
  .gauge{background:linear-gradient(180deg,var(--panel),var(--panel2));
    border:1px solid var(--hair);border-radius:6px;padding:12px 13px}
  .gauge .lbl{font-size:10px;letter-spacing:1.8px;text-transform:uppercase;
    color:var(--faint);display:flex;justify-content:space-between;align-items:baseline}
  .gauge .val{font-size:26px;font-weight:600;font-variant-numeric:tabular-nums;
    margin-top:2px;letter-spacing:.5px}
  .gauge .unit{font-size:11px;color:var(--dim);font-weight:400;letter-spacing:.5px}
  .gauge canvas{margin-top:8px;border-radius:3px}

  .legend{background:var(--panel2);border:1px solid var(--hair);border-radius:6px;
    padding:12px 13px;font-size:11px;color:var(--dim)}
  .legend .row{display:flex;align-items:center;gap:8px;margin:6px 0}
  .bar{height:10px;flex:1;border-radius:2px;
    background:linear-gradient(90deg,#e8734a,#d9c26a,#46c6d0)}
  .sw{width:11px;height:11px;border-radius:2px;flex:none}

  .transport{margin-top:18px;display:flex;align-items:center;gap:14px;
    background:var(--panel2);border:1px solid var(--hair);border-radius:6px;
    padding:11px 14px;flex-wrap:wrap}
  button{font-family:var(--mono);font-size:13px;color:var(--ground);
    background:var(--cyan);border:0;border-radius:4px;padding:7px 16px;
    cursor:pointer;letter-spacing:.4px;font-weight:600}
  button:hover{filter:brightness(1.12)}
  button:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
  .ghost{background:#17222899;color:var(--ink);border:1px solid var(--hair)}
  input[type=range]{flex:1;min-width:140px;accent-color:var(--cyan);cursor:pointer}
  .tick{font-size:12px;color:var(--dim);font-variant-numeric:tabular-nums;
    letter-spacing:.5px;white-space:nowrap}
  .tick b{color:var(--ink)}
  .speed{display:flex;gap:4px}
  .speed button{padding:5px 9px;font-size:11px;background:#17222899;
    color:var(--dim);border:1px solid var(--hair);font-weight:400}
  .speed button.on{background:var(--cyan);color:var(--ground);font-weight:600;border-color:var(--cyan)}

  footer{margin-top:26px;padding-top:16px;border-top:1px solid var(--hair);
    color:var(--faint);font-size:12px;line-height:1.7}
  footer a{color:var(--cyan);text-decoration:none}
  footer a:hover{text-decoration:underline}
  .flag{color:var(--mark)}

  .toprow{flex-basis:100%;display:flex;justify-content:space-between;align-items:center}
  .about-btn{background:#17222899;color:var(--cyan);border:1px solid #2a3a41;
    border-radius:20px;padding:6px 16px;font-size:12px;letter-spacing:.6px;
    text-transform:uppercase;font-weight:600}
  .about-btn:hover{background:var(--cyan);color:var(--ground);border-color:var(--cyan)}
  .toprow-r{display:flex;align-items:center;gap:8px}
  .langbar{display:flex;gap:3px;background:#0c1216cc;border:1px solid var(--hair);
    border-radius:16px;padding:3px}
  .langbar button{font-family:var(--mono);font-size:11px;color:var(--dim);
    background:none;border:0;border-radius:12px;padding:4px 9px;cursor:pointer;letter-spacing:.4px}
  .langbar button.on{background:var(--cyan);color:var(--ground);font-weight:600}
  .langbar button:hover:not(.on){color:var(--ink)}

  /* попап «о проекте» */
  .overlay{position:fixed;inset:0;background:#04070ccc;backdrop-filter:blur(3px);
    display:none;align-items:flex-start;justify-content:center;z-index:50;
    padding:40px 18px;overflow-y:auto}
  .overlay.open{display:flex}
  .modal{background:linear-gradient(180deg,#11191e,#0c1216);border:1px solid #26333a;
    border-radius:10px;max-width:660px;width:100%;padding:30px 30px 34px;
    box-shadow:0 30px 80px #000a;position:relative}
  .modal h2{font-size:20px;margin:0 0 4px;letter-spacing:.4px;color:var(--ink)}
  .modal .sub{color:var(--faint);font-size:12px;letter-spacing:1.5px;
    text-transform:uppercase;margin-bottom:20px}
  .modal h3{font-size:14px;letter-spacing:.5px;color:var(--cyan);
    margin:22px 0 8px;text-transform:none}
  .modal p{color:var(--dim);font-size:13.5px;line-height:1.65;margin:8px 0}
  .modal b{color:var(--ink);font-weight:600}
  .modal a{color:var(--cyan);text-decoration:none;border-bottom:1px solid #2a4a4f}
  .modal a:hover{border-bottom-color:var(--cyan)}
  .modal ul{margin:8px 0;padding-left:0;list-style:none}
  .modal li{color:var(--dim);font-size:13px;line-height:1.55;margin:9px 0;
    padding-left:16px;position:relative}
  .modal li::before{content:"·";position:absolute;left:2px;color:var(--cyan);
    font-weight:700}
  .verdict{display:flex;gap:9px;align-items:baseline;margin:10px 0}
  .tag{flex:none;font-size:10px;letter-spacing:.8px;text-transform:uppercase;
    padding:2px 8px;border-radius:10px;font-weight:600;margin-top:2px}
  .tag.no{background:#e8734a22;color:#f0956e;border:1px solid #6b3a2a}
  .tag.part{background:#e6c14a22;color:#e6c14a;border:1px solid #6b5b2a}
  .tag.now{background:#46c6d022;color:var(--cyan);border:1px solid #2a4a4f}
  .verdict span{font-size:13px;color:var(--dim);line-height:1.55}
  .modal .close{position:absolute;top:16px;right:18px;background:none;border:0;
    color:var(--dim);font-size:22px;cursor:pointer;padding:4px 8px;line-height:1}
  .modal .close:hover{color:var(--ink)}
  .modal .note{margin-top:24px;padding-top:16px;border-top:1px solid var(--hair);
    font-size:11.5px;color:var(--faint);line-height:1.6}
</style>

<div class="wrap">
  <header>
    <div class="toprow">
      <div class="eyebrow" id="t_eye"></div>
      <div class="toprow-r">
        <div class="langbar" role="group" aria-label="language">
          <button data-set="en">EN</button><button data-set="ru">RU</button><button data-set="de">DE</button><button data-set="zh">中文</button>
        </div>
        <a class="about-btn" id="t_about" href="https://claude.ai/code/artifact/7876772a-43f0-4fb5-b761-db802aa896a9" target="_blank" rel="noopener"></a>
      </div>
    </div>
    <h1 id="t_brand"></h1>
    <div class="thesis" id="t_thesis"></div>
    <div class="cond" id="cond"></div>
  </header>

  <div class="stage">
    <div>
      <div class="screen">
        <canvas id="world" width="512" height="512"></canvas>
        <div class="scan"></div>
        <div class="hud" id="hud"></div>
      </div>
      <div class="transport">
        <button id="play"></button>
        <input type="range" id="scrub" min="0" value="0" step="1">
        <div class="speed" id="speed">
          <button data-s="0.5">0.5×</button>
          <button data-s="1" class="on">1×</button>
          <button data-s="2">2×</button>
          <button data-s="4">4×</button>
        </div>
        <div class="tick"><span id="t_tick"></span> <b id="tick">0</b> · <span id="t_frame"></span> <b id="frame">0</b>/<span id="nframes">0</span></div>
      </div>
    </div>

    <div class="rail" id="rail"></div>
  </div>

  <footer id="t_foot"></footer>
</div>


<script>
const DATA = __DATA__;

// ---- переводы интерфейса (EN по умолчанию; выбор общий со страницей «о проекте») ----
const I18N = {
  en:{eyebrow:"artificial life", about:"about ↗",
    brand:'mini<span class="dot">·</span>world',
    thesis:'<b>A tiny digital world where simple creatures live: they look for food, spend energy, reproduce, and die for good.</b> No one scores them — those who gather enough food leave offspring, the rest vanish. This is not a game but a faithful replay of one such simulation: a creature’s colour shows how much energy it has, green is food, <span class="flag">yellow</span> are marks creatures leave in the world.',
    cond:"this run has everything on at once: foraging, creatures interacting, and marks in the world",
    hud_pop:"pop.",hud_e:"energy",hud_social:"social layer open",hud_warm:"warm-up",
    g_pop_l:"population",g_pop_u:"creatures",g_e_l:"mean energy",g_e_u:"of 100",
    g_mi_l:"I(energy;action)",g_mi_u:"bits/window",g_coop_l:"cooperative acts",g_coop_u:"cumulative",
    leg_title:"reading the screen",leg_hunger:"hungry",leg_full:"full",
    leg_mark:"mark in a cell (sign)",leg_res:"food; dim = fertile soil",
    play:"▶ play",pause:"❚❚ pause",tick_l:"tick",frame_l:"frame",
    foot:'Every frame is a real simulation state (seed 1), not a for-show animation. Marks <span class="flag">are barely used</span> and the field never saturates — a measured stage-3 result, not a visualization artefact. Code, data, report: <a href="https://github.com/akela1308/minimir" target="_blank" rel="noopener">github.com/akela1308/minimir</a>.'},
  ru:{eyebrow:"искусственная жизнь", about:"о проекте ↗",
    brand:'мини<span class="dot">·</span>мир',
    thesis:'<b>Это крошечный цифровой мир, где живут простые существа: они ищут еду, тратят силы, размножаются и умирают насовсем.</b> Никто не ставит им оценок — кто нашёл достаточно еды, оставляет потомство, остальные исчезают. Ниже — не игра, а точное воспроизведение одной такой симуляции: цвет существа показывает, сколько у него сил (энергии), зелёное — еда, <span class="flag">жёлтое</span> — метки, которые существа оставляют в мире.',
    cond:"в этом прогоне включено всё сразу: поиск еды, общение между существами и метки в мире",
    hud_pop:"поп.",hud_e:"энергия",hud_social:"соц.слой открыт",hud_warm:"прогрев",
    g_pop_l:"популяция",g_pop_u:"агентов",g_e_l:"средняя энергия",g_e_u:"из 100",
    g_mi_l:"I(энергия;действие)",g_mi_u:"бит/окно",g_coop_l:"кооперативных актов",g_coop_u:"нарастающе",
    leg_title:"чтение экрана",leg_hunger:"голод",leg_full:"сытость",
    leg_mark:"метка в клетке (знак)",leg_res:"ресурс (еда), тускло = плодородная почва",
    play:"▶ старт",pause:"❚❚ пауза",tick_l:"тик",frame_l:"кадр",
    foot:'Каждый кадр — реальное состояние симуляции (seed 1), а не анимация «для вида». Метки <span class="flag">почти не используются</span> и поле не насыщается — это измеренный результат этапа 3, а не артефакт визуализации. Код, данные, отчёт: <a href="https://github.com/akela1308/minimir" target="_blank" rel="noopener">github.com/akela1308/minimir</a>.'},
  de:{eyebrow:"künstliches Leben", about:"über ↗",
    brand:'mini<span class="dot">·</span>welt',
    thesis:'<b>Eine winzige digitale Welt, in der einfache Wesen leben: Sie suchen Futter, verbrauchen Kraft, pflanzen sich fort und sterben endgültig.</b> Niemand bewertet sie — wer genug Futter sammelt, hinterlässt Nachkommen, der Rest verschwindet. Kein Spiel, sondern die getreue Wiedergabe einer solchen Simulation: die Farbe eines Wesens zeigt seine Kraft (Energie), Grün ist Futter, <span class="flag">Gelb</span> sind Markierungen, die Wesen in der Welt hinterlassen.',
    cond:"in diesem Lauf ist alles zugleich an: Futtersuche, Interaktion der Wesen und Markierungen in der Welt",
    hud_pop:"Pop.",hud_e:"Energie",hud_social:"soziale Schicht offen",hud_warm:"Aufwärmen",
    g_pop_l:"Population",g_pop_u:"Wesen",g_e_l:"mittlere Energie",g_e_u:"von 100",
    g_mi_l:"I(Energie;Handlung)",g_mi_u:"Bit/Fenster",g_coop_l:"kooperative Akte",g_coop_u:"kumulativ",
    leg_title:"was man sieht",leg_hunger:"Hunger",leg_full:"satt",
    leg_mark:"Markierung in einer Zelle (Zeichen)",leg_res:"Futter; blass = fruchtbarer Boden",
    play:"▶ Start",pause:"❚❚ Pause",tick_l:"Tick",frame_l:"Bild",
    foot:'Jedes Bild ist ein echter Simulationszustand (Seed 1), keine Show-Animation. Markierungen <span class="flag">werden kaum genutzt</span> und das Feld sättigt sich nie — ein gemessenes Stufe-3-Ergebnis, kein Visualisierungsartefakt. Code, Daten, Bericht: <a href="https://github.com/akela1308/minimir" target="_blank" rel="noopener">github.com/akela1308/minimir</a>.'},
  zh:{eyebrow:"人工生命", about:"关于 ↗",
    brand:'微<span class="dot">·</span>世界',
    thesis:'<b>一个微小的数字世界，里面住着简单的生物：它们寻找食物、消耗体力、繁殖，并且会彻底死亡。</b>没有谁给它们打分——找到足够食物的留下后代，其余的消失。这不是游戏，而是对一次这样的模拟的忠实重放：生物的颜色表示它的体力（能量），绿色是食物，<span class="flag">黄色</span>是生物留在世界里的记号。',
    cond:"这一运行同时开启了一切：觅食、生物间互动，以及世界里的记号",
    hud_pop:"种群",hud_e:"能量",hud_social:"社会层已开启",hud_warm:"预热",
    g_pop_l:"种群",g_pop_u:"个体",g_e_l:"平均能量",g_e_u:"满分100",
    g_mi_l:"I(能量;行为)",g_mi_u:"比特/窗口",g_coop_l:"合作行为",g_coop_u:"累计",
    leg_title:"如何看画面",leg_hunger:"饥饿",leg_full:"饱足",
    leg_mark:"格子里的记号（符号）",leg_res:"食物（资源）；暗色＝肥沃土壤",
    play:"▶ 播放",pause:"❚❚ 暂停",tick_l:"刻",frame_l:"帧",
    foot:'每一帧都是真实的模拟状态（seed 1），并非“摆拍”动画。记号<span class="flag">几乎不被使用</span>，场也从不饱和——这是被测量到的阶段 3 结果，而非可视化的假象。代码、数据、报告：<a href="https://github.com/akela1308/minimir" target="_blank" rel="noopener">github.com/akela1308/minimir</a>。'},
};
const LKEY='minimir_lang', LDEF='en';
let LANG=(()=>{try{return localStorage.getItem(LKEY)||LDEF}catch(e){return LDEF}})();
if(!I18N[LANG])LANG=LDEF;
function t(k){return (I18N[LANG]||I18N.en)[k];}

// ---- декодирование base64 -> Uint8Array ----
function b64(s){const bin=atob(s);const a=new Uint8Array(bin.length);
  for(let i=0;i<bin.length;i++)a[i]=bin.charCodeAt(i);return a;}
const M=DATA.meta;
const cap=b64(DATA.cap), agents=b64(DATA.agents), marks=b64(DATA.marks), res=b64(DATA.res);
const aCount=DATA.agentCounts, mCount=DATA.markCounts, resFrames=DATA.resFrames;
const N=M.nFrames;

// смещения по кадрам
const aOff=new Array(N), mOff=new Array(N);
let o=0; for(let f=0;f<N;f++){aOff[f]=o;o+=aCount[f]*3;}
o=0; for(let f=0;f<N;f++){mOff[f]=o;o+=mCount[f]*2;}
const resStride=M.rW*M.rH;
function resSnapForFrame(f){ // последний снимок ресурса <= f
  let idx=0; for(let i=0;i<resFrames.length;i++){if(resFrames[i]<=f)idx=i;else break;}
  return idx;
}

// ---- цвет энергии: голод (янтарь) -> сытость (циан) ----
function energyColor(e){ // e in 0..255
  const t=e/255;
  // три опорные точки: 0 #e8734a, .5 #d9c26a, 1 #46c6d0
  let r,g,b;
  if(t<0.5){const u=t/0.5;r=0xe8+(0xd9-0xe8)*u;g=0x73+(0xc2-0x73)*u;b=0x4a+(0x6a-0x4a)*u;}
  else{const u=(t-0.5)/0.5;r=0xd9+(0x46-0xd9)*u;g=0xc2+(0xc6-0xc2)*u;b=0x6a+(0xd0-0x6a)*u;}
  return `rgb(${r|0},${g|0},${b|0})`;
}

// ---- canvas мира ----
const cv=document.getElementById('world'), ctx=cv.getContext('2d');
const SC=cv.width/M.W;               // масштаб клетки -> пиксели (512/128=4)
const off=document.createElement('canvas'); off.width=M.rW; off.height=M.rH;
const octx=off.getContext('2d');
const img=octx.createImageData(M.rW,M.rH);

function drawFrame(f){
  // терраин + ресурс (даунсемпл rW x rH)
  const rs=resSnapForFrame(f)*resStride;
  const d=img.data;
  for(let i=0;i<resStride;i++){
    const c=cap[i]/255;              // плодородность (тёмно-зелёный фон)
    const r=res[rs+i]/255;           // текущий ресурс (ярче)
    const base=18*c;                 // фон
    const g=base + 150*r;            // зелёный от еды
    d[i*4]  = 10 + 20*r;
    d[i*4+1]= 26*c + g*0.9;
    d[i*4+2]= 20*c + 40*r;
    d[i*4+3]= 255;
  }
  octx.putImageData(img,0,0);
  ctx.imageSmoothingEnabled=false;
  ctx.clearRect(0,0,cv.width,cv.height);
  ctx.drawImage(off,0,0,cv.width,cv.height);

  // метки
  const mo=mOff[f], mc=mCount[f];
  ctx.fillStyle='rgba(230,193,74,0.85)';
  for(let i=0;i<mc;i++){
    const x=marks[mo+i*2], y=marks[mo+i*2+1];
    ctx.fillRect(x*SC, y*SC, SC, SC);
  }

  // агенты
  const ao=aOff[f], ac=aCount[f];
  for(let i=0;i<ac;i++){
    const x=agents[ao+i*3], y=agents[ao+i*3+1], e=agents[ao+i*3+2];
    ctx.fillStyle=energyColor(e);
    ctx.fillRect(x*SC-0.5, y*SC-0.5, SC+1, SC+1);
  }

  // HUD
  const social = f>=M.socialFrom;
  hud.innerHTML=`${t('hud_pop')} <b>${DATA.pop[f]}</b> · ${t('hud_e')} <b>${DATA.meanE[f]}</b>`+
    (social?` · <span style="color:var(--coop)">${t('hud_social')}</span>`:` · ${t('hud_warm')}`);
}

// ---- sparkline-приборы ----
const rail=document.getElementById('rail');
const GAUGES=[
  {key:'pop', lk:'g_pop_l', uk:'g_pop_u', color:'#8fd6dd', fmt:v=>v},
  {key:'meanE', lk:'g_e_l', uk:'g_e_u', color:'#e8b06a', fmt:v=>v.toFixed(0)},
  {key:'mi', lk:'g_mi_l', uk:'g_mi_u', color:'#46c6d0', fmt:v=>v.toFixed(3)},
  {key:'coop', lk:'g_coop_l', uk:'g_coop_u', color:'#4fd08a', fmt:v=>v},
];
let gEls=[];
function buildRail(){
  rail.innerHTML=''; gEls=[];
  for(const g of GAUGES){
    const el=document.createElement('div'); el.className='gauge';
    el.innerHTML=`<div class="lbl"><span>${t(g.lk)}</span></div>
      <div class="val"><span data-v>—</span> <span class="unit">${t(g.uk)}</span></div>
      <canvas width="272" height="46"></canvas>`;
    rail.appendChild(el);
    gEls.push({g, val:el.querySelector('[data-v]'), c:el.querySelector('canvas').getContext('2d')});
  }
  const leg=document.createElement('div'); leg.className='legend';
  leg.innerHTML=`<div style="letter-spacing:1.5px;text-transform:uppercase;font-size:10px;color:var(--faint);margin-bottom:8px">${t('leg_title')}</div>
    <div class="row"><span>${t('leg_hunger')}</span><span class="bar"></span><span>${t('leg_full')}</span></div>
    <div class="row"><span class="sw" style="background:#e6c14a"></span> ${t('leg_mark')}</div>
    <div class="row"><span class="sw" style="background:#3fae6e"></span> ${t('leg_res')}</div>`;
  rail.appendChild(leg);
}

function sparkline(gc, arr, f, color){
  const w=272,h=46; gc.clearRect(0,0,w,h);
  let lo=Infinity,hi=-Infinity;
  for(const v of arr){if(v<lo)lo=v;if(v>hi)hi=v;}
  if(hi-lo<1e-9)hi=lo+1;
  const X=i=>i/(arr.length-1)*(w-2)+1;
  const Y=v=>h-3-((v-lo)/(hi-lo))*(h-8);
  // площадь
  gc.beginPath();gc.moveTo(X(0),h);
  for(let i=0;i<arr.length;i++)gc.lineTo(X(i),Y(arr[i]));
  gc.lineTo(X(arr.length-1),h);gc.closePath();
  gc.fillStyle=color+'22';gc.fill();
  // линия
  gc.beginPath();
  for(let i=0;i<arr.length;i++){const x=X(i),y=Y(arr[i]);i?gc.lineTo(x,y):gc.moveTo(x,y);}
  gc.strokeStyle=color;gc.lineWidth=1.4;gc.stroke();
  // курсор
  const cx=X(f),cy=Y(arr[f]);
  gc.strokeStyle=color+'55';gc.beginPath();gc.moveTo(cx,0);gc.lineTo(cx,h);gc.stroke();
  gc.fillStyle=color;gc.beginPath();gc.arc(cx,cy,2.4,0,7);gc.fill();
}
function updateGauges(f){
  for(const {g,val,c} of gEls){
    val.textContent=g.fmt(DATA[g.key][f]);
    sparkline(c,DATA[g.key],f,g.color);
  }
}

// ---- транспорт ----
let cur=0, playing=false, speed=1, acc=0, last=0;
const scrub=document.getElementById('scrub'); scrub.max=N-1;
document.getElementById('nframes').textContent=N;
const playBtn=document.getElementById('play');
const hud=document.getElementById('hud');

function render(f){
  cur=f;
  drawFrame(f); updateGauges(f);
  scrub.value=f;
  document.getElementById('frame').textContent=f;
  document.getElementById('tick').textContent=f*M.stride;
}
function loop(ts){
  if(!playing)return;
  if(!last)last=ts;
  acc+=(ts-last)/1000; last=ts;
  const fps=12*speed;               // база 12 кадров/с × скорость
  if(acc>=1/fps){
    let n=cur+Math.max(1,Math.floor(acc*fps));
    acc=0;
    if(n>=N){n=0;}                    // зациклить
    render(n);
  }
  requestAnimationFrame(loop);
}
function play(){playing=true;last=0;playBtn.textContent=t('pause');requestAnimationFrame(loop);}
function pause(){playing=false;playBtn.textContent=t('play');}
playBtn.onclick=()=>playing?pause():play();
scrub.oninput=e=>{pause();render(+e.target.value);};
document.getElementById('speed').addEventListener('click',e=>{
  const b=e.target.closest('button[data-s]');if(!b)return;
  speed=+b.dataset.s;
  document.querySelectorAll('#speed button').forEach(x=>x.classList.toggle('on',x===b));
});

// ---- язык ----
function applyLang(l){
  if(!I18N[l])l=LDEF; LANG=l;
  try{localStorage.setItem(LKEY,l)}catch(e){}
  document.documentElement.lang=l;
  document.getElementById('t_eye').textContent=t('eyebrow');
  document.getElementById('t_about').textContent=t('about');
  document.getElementById('t_brand').innerHTML=t('brand');
  document.getElementById('t_thesis').innerHTML=t('thesis');
  document.getElementById('cond').textContent=t('cond');
  document.getElementById('t_tick').textContent=t('tick_l');
  document.getElementById('t_frame').textContent=t('frame_l');
  document.getElementById('t_foot').innerHTML=t('foot');
  playBtn.textContent=playing?t('pause'):t('play');
  document.querySelectorAll('.langbar button').forEach(b=>b.classList.toggle('on',b.dataset.set===l));
  buildRail();
  render(cur);
}
document.querySelector('.langbar').addEventListener('click',e=>{
  const b=e.target.closest('button[data-set]'); if(b)applyLang(b.dataset.set);
});

applyLang(LANG);
// автостарт, если пользователь не против движения
if(!matchMedia('(prefers-reduced-motion: reduce)').matches) play();
</script>
"""

html = TEMPLATE.replace("__DATA__", DATA)
Path("minimir_viewer.html").write_text(html)
print(f"minimir_viewer.html: {len(html)/1024:.0f} KB")
