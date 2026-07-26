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
      <div class="eyebrow">искусственная жизнь</div>
      <button class="about-btn" id="aboutBtn">о проекте</button>
    </div>
    <h1>мини<span class="dot">·</span>мир</h1>
    <div class="thesis"><b>Это крошечный цифровой мир, где живут простые
      существа: они ищут еду, тратят силы, размножаются и умирают насовсем.</b>
      Никто не ставит им оценок — кто нашёл достаточно еды, оставляет потомство,
      остальные исчезают. Мы смотрим, появится ли у них само собой поведение,
      похожее на «хочу есть», — без того, чтобы мы это заранее заложили.
      Ниже — не игра, а точное воспроизведение одной такой симуляции: цвет
      существа показывает, сколько у него сил (энергии), зелёное — еда,
      <span class="flag">жёлтое</span> — метки, которые существа оставляют в мире.</div>
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
        <button id="play">▶ старт</button>
        <input type="range" id="scrub" min="0" value="0" step="1">
        <div class="speed" id="speed">
          <button data-s="0.5">0.5×</button>
          <button data-s="1" class="on">1×</button>
          <button data-s="2">2×</button>
          <button data-s="4">4×</button>
        </div>
        <div class="tick">тик <b id="tick">0</b> · кадр <b id="frame">0</b>/<span id="nframes">0</span></div>
      </div>
    </div>

    <div class="rail" id="rail"></div>
  </div>

  <footer>
    Каждый кадр — реальное состояние симуляции (seed 1), а не анимация «для вида».
    Метки <span class="flag">почти не используются</span> и поле не насыщается — это
    измеренный результат этапа 3, а не артефакт визуализации.
    Код, данные и отчёт: <a href="https://github.com/akela1308/minimir" target="_blank" rel="noopener">github.com/akela1308/minimir</a>.
  </footer>
</div>

<div class="overlay" id="overlay">
  <div class="modal" role="dialog" aria-modal="true" aria-label="о проекте">
    <button class="close" id="closeBtn" aria-label="закрыть">×</button>
    <h2>Что это за проект</h2>
    <div class="sub">простыми словами</div>

    <p>Мы построили <b>крошечный цифровой мир</b> и населили его простыми
      существами. Каждое существо управляется маленькой «нервной системой»,
      которая передаётся потомкам с небольшими изменениями — как гены. Существа
      ищут еду, тратят силы на движение, размножаются, когда накопят достаточно,
      и умирают насовсем, если силы кончились. <b>Никакого судьи нет</b> — мы не
      ставим оценок и не говорим, что «хорошо». Выживают и оставляют потомство
      те, кто просто лучше справляется. Со временем существа сами «учатся»
      выживать — через отбор, поколение за поколением.</p>

    <h3>Главный вопрос</h3>
    <p>Достаточно ли <b>одной уязвимости</b> — того, что существо может умереть
      и «чувствует» своё состояние (голод), — чтобы у него само собой появилось
      поведение, похожее на <b>желание</b> («хочу есть», «поберегусь»)? Причём
      без того, чтобы мы это желание заранее в него вписали. Это старый вопрос о
      том, откуда берутся потребности; мы пробуем ответить на него измерением,
      а не рассуждением.</p>
    <p>Мы разбили его на три ступени:</p>
    <ul>
      <li><b>Ступень 1 — знание о себе.</b> Ведёт ли себя существо иначе, когда
        «видит» свой голод, чем когда ему подсунули такой же, но чужой сигнал?</li>
      <li><b>Ступень 2 — забота о других.</b> Появляется ли сотрудничество
        (делиться едой), когда еды мало?</li>
      <li><b>Ступень 3 — знак.</b> Может ли метка, которую существо оставляет
        <i>для других</i>, со временем стать инструментом <i>для себя самого</i>?
        (идея Выготского о том, как внешнее становится внутренним).</li>
    </ul>

    <h3>На что мы опираемся</h3>
    <p>Мы не первые — и это хорошо. Похожие идеи уже проверяли, и мы стоим
      на этих работах:</p>
    <ul>
      <li><a href="https://arxiv.org/pdf/2401.08999" target="_blank" rel="noopener">Керамати и Гуткин (2011)</a>
        — доказали, что «иметь потребность» и «вести себя целенаправленно» —
        это математически одно и то же. Но у них награда задана заранее; мы
        проверяем, хватит ли <i>одного отбора</i>, без заданной награды.</li>
      <li><a href="https://shinyverse.org/larryy/Polyworld.html" target="_blank" rel="noopener">Polyworld, Йегер (1994)</a>
        — почти наш проект, но на 30 лет раньше: существа, нейросети и никакого
        судьи.</li>
      <li><a href="https://arxiv.org/pdf/1312.3450" target="_blank" rel="noopener">Рекехо и Камачо</a>
        — предсказали, что при нехватке еды выживают те, кто сотрудничает
        (ступень 2).</li>
      <li><a href="https://arxiv.org/abs/2412.12103" target="_blank" rel="noopener">Йошида и Ман (2024)</a>
        — показали, что доступ к состоянию другого рождает заботу о нём.</li>
    </ul>

    <h3>Что мы уже узнали</h3>
    <p>Честно докладываем и то, что <b>не</b> подтвердилось — отрицательный
      результат здесь такой же ценный, как положительный.</p>
    <div class="verdict"><span class="tag part">частично</span><span>
      <b>Ступень 1.</b> Существа, «видящие» свой голод, и правда ведут себя
      иначе, чем с чужим сигналом — устойчиво. Но эффект оказался <b>слабее
      случайных колебаний</b> самого мира, поэтому по нашему строгому порогу мы
      его не засчитали как доказанный.</span></div>
    <div class="verdict"><span class="tag no">не подтвердилось</span><span>
      <b>Ступень 2.</b> Предсказанного «сотрудничества при нехватке» мы чисто не
      увидели — и <b>нашли, почему</b>: в нашей модели делиться едой невыгодно
      честно (она «создавала» лишнюю энергию). А знаменитая связь «голодные
      добрее» оказалась в основном обманом измерения.</span></div>
    <div class="verdict"><span class="tag no">не подтвердилось</span><span>
      <b>Ступень 3.</b> Существа почти не пользуются метками, а способность
      «доучиваться» при жизни отбор вообще <b>выключает</b>. Превращения знака
      «для других» в знак «для себя» не произошло.</span></div>
    <div class="verdict"><span class="tag now">изучаем сейчас</span><span>
      Чиним «энергетику» сотрудничества, чтобы честно перепроверить ступень 2, и
      думаем, как дать меткам реальную пользу, иначе ступень 3 непроверяема.</span></div>

    <div class="note">Итог по-честному: пока ни одна из трёх ступеней не
      «выстрелила» в полную силу — но в каждом случае мы понимаем, что именно
      мешает, и это уже результат. Полный отчёт с числами, весь код и данные —
      открыто на <a href="https://github.com/akela1308/minimir" target="_blank" rel="noopener">GitHub</a>.
      Эти выводы обновляются по мере новых экспериментов.</div>
  </div>
</div>

<script>
const DATA = __DATA__;

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
  hud.innerHTML=`поп. <b>${DATA.pop[f]}</b> · энергия <b>${DATA.meanE[f]}</b>`+
    (social?` · <span style="color:var(--coop)">соц.слой открыт</span>`:` · прогрев`);
}

// ---- sparkline-приборы ----
const rail=document.getElementById('rail');
const GAUGES=[
  {key:'pop', lbl:'популяция', unit:'агентов', color:'#8fd6dd', fmt:v=>v},
  {key:'meanE', lbl:'средняя энергия', unit:'из 100', color:'#e8b06a', fmt:v=>v.toFixed(0)},
  {key:'mi', lbl:'I(энергия;действие)', unit:'бит/окно', color:'#46c6d0', fmt:v=>v.toFixed(3)},
  {key:'coop', lbl:'кооперативных актов', unit:'нарастающе', color:'#4fd08a', fmt:v=>v},
];
const gEls=[];
for(const g of GAUGES){
  const el=document.createElement('div'); el.className='gauge';
  el.innerHTML=`<div class="lbl"><span>${g.lbl}</span></div>
    <div class="val"><span data-v>—</span> <span class="unit">${g.unit}</span></div>
    <canvas width="272" height="46"></canvas>`;
  rail.appendChild(el);
  gEls.push({g, val:el.querySelector('[data-v]'), c:el.querySelector('canvas').getContext('2d')});
}
// легенда
const leg=document.createElement('div'); leg.className='legend';
leg.innerHTML=`<div style="letter-spacing:1.5px;text-transform:uppercase;font-size:10px;color:var(--faint);margin-bottom:8px">чтение экрана</div>
  <div class="row"><span>голод</span><span class="bar"></span><span>сытость</span></div>
  <div class="row"><span class="sw" style="background:#e6c14a"></span> метка в клетке (знак)</div>
  <div class="row"><span class="sw" style="background:#3fae6e"></span> ресурс (еда), тускло = плодородная почва</div>`;
rail.appendChild(leg);

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
document.getElementById('cond').textContent=
  'в этом прогоне включено всё сразу: поиск еды, общение между существами и метки в мире';
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
function play(){playing=true;last=0;playBtn.textContent='❚❚ пауза';requestAnimationFrame(loop);}
function pause(){playing=false;playBtn.textContent='▶ старт';}
playBtn.onclick=()=>playing?pause():play();
scrub.oninput=e=>{pause();render(+e.target.value);};
document.getElementById('speed').addEventListener('click',e=>{
  const b=e.target.closest('button[data-s]');if(!b)return;
  speed=+b.dataset.s;
  document.querySelectorAll('#speed button').forEach(x=>x.classList.toggle('on',x===b));
});

// ---- попап «о проекте» ----
const overlay=document.getElementById('overlay');
let wasPlaying=false;
function openAbout(){wasPlaying=playing;pause();overlay.classList.add('open');}
function closeAbout(){overlay.classList.remove('open');if(wasPlaying)play();}
document.getElementById('aboutBtn').onclick=openAbout;
document.getElementById('closeBtn').onclick=closeAbout;
overlay.addEventListener('click',e=>{if(e.target===overlay)closeAbout();});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&overlay.classList.contains('open'))closeAbout();});

render(0);
// автостарт, если пользователь не против движения
if(!matchMedia('(prefers-reduced-motion: reduce)').matches) play();
</script>
"""

html = TEMPLATE.replace("__DATA__", DATA)
Path("minimir_viewer.html").write_text(html)
print(f"minimir_viewer.html: {len(html)/1024:.0f} KB")
