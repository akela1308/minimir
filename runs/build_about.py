# -*- coding: utf-8 -*-
"""Собрать многоязычную страницу «о проекте» (about.html).

Один HTML-шаблон блока + словари переводов на 4 языка (EN по умолчанию,
плюс RU, DE, ZH). Переключатель языка вверху справа, выбор запоминается в
localStorage и общий с страницей симуляции. Значения словаря могут содержать
инлайновый HTML (<b>, <a>, <i>) — так фразировка остаётся естественной.
"""
from pathlib import Path

GH = "https://github.com/akela1308/minimir"
SIM = "https://claude.ai/code/artifact/e9a5c20f-0137-466d-8f7b-769b5a24db34"
KERAMATI = "https://arxiv.org/pdf/2401.08999"
POLY = "https://shinyverse.org/larryy/Polyworld.html"
REQUEJO = "https://arxiv.org/pdf/1312.3450"
YOSHIDA = "https://arxiv.org/abs/2412.12103"
CREATURES = "https://en.wikipedia.org/wiki/Creatures_(video_game_series)"

STYLE = r"""<title>mini-world — about</title>
<style>
  :root{
    --ground:#0a0e11; --panel:#10161a; --panel2:#0d1317; --hair:#1c262c;
    --ink:#e9f1f2; --dim:#93a6ae; --faint:#5b6f77;
    --cyan:#46c6d0; --amber:#e8734a; --mark:#e6c14a; --coop:#4fd08a;
    --mono:ui-monospace,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--ground);color:var(--ink);font-family:var(--mono);
    -webkit-font-smoothing:antialiased;line-height:1.68;font-size:15px}
  #amb{position:fixed;inset:0;width:100%;height:100%;z-index:0;opacity:.4;pointer-events:none}
  a{color:var(--cyan);text-decoration:none;border-bottom:1px solid #29464b}
  a:hover{border-bottom-color:var(--cyan)}
  .wrap{max-width:720px;margin:0 auto;padding:64px 22px 80px;position:relative;z-index:1}

  .langbar{position:fixed;top:14px;right:16px;z-index:10;display:flex;gap:4px;
    background:#0c1216cc;border:1px solid var(--hair);border-radius:20px;padding:4px;
    backdrop-filter:blur(6px)}
  .langbar button{font-family:var(--mono);font-size:12px;color:var(--dim);
    background:none;border:0;border-radius:14px;padding:5px 11px;cursor:pointer;
    letter-spacing:.5px}
  .langbar button.on{background:var(--cyan);color:var(--ground);font-weight:600}
  .langbar button:hover:not(.on){color:var(--ink)}

  .langblock{display:none} .langblock.on{display:block}

  .eyebrow{font-size:11px;letter-spacing:3px;text-transform:uppercase;color:var(--faint)}
  h1{font-size:38px;font-weight:600;letter-spacing:1px;margin:12px 0 0;text-wrap:balance}
  h1 .dot{color:var(--cyan)}
  .lede{color:var(--dim);font-size:16px;line-height:1.6;margin:16px 0 0}
  .lede b{color:var(--ink);font-weight:600}
  .cta{display:flex;gap:12px;flex-wrap:wrap;margin-top:26px}
  .btn{display:inline-block;background:var(--cyan);color:var(--ground);
    border:0;border-radius:5px;padding:11px 20px;font-family:var(--mono);
    font-size:13px;font-weight:600;letter-spacing:.5px;cursor:pointer}
  .btn:hover{filter:brightness(1.12);border-bottom:0}
  .btn.ghost{background:#14202699;color:var(--ink);border:1px solid var(--hair)}

  section{padding-top:38px}
  h2{font-size:13px;letter-spacing:1.6px;text-transform:uppercase;color:var(--cyan);
    margin:0 0 4px;display:flex;align-items:center;gap:10px}
  h2::before{content:"";width:22px;height:1px;background:var(--cyan);opacity:.6}
  h3{font-size:19px;font-weight:600;margin:2px 0 10px;letter-spacing:.3px;text-wrap:balance}
  p{color:var(--dim);margin:10px 0}
  p b, li b{color:var(--ink);font-weight:600}

  .stages{display:grid;gap:12px;margin-top:14px}
  .card{background:linear-gradient(180deg,var(--panel),var(--panel2));
    border:1px solid var(--hair);border-radius:8px;padding:16px 18px;
    border-left:2px solid var(--seg,#2a3a41)}
  .card .n{font-size:11px;letter-spacing:1.5px;text-transform:uppercase;color:var(--faint)}
  .card h4{margin:4px 0 6px;font-size:15px;font-weight:600;color:var(--ink)}
  .card p{margin:0;font-size:13.5px}
  .card.s1{--seg:var(--cyan)} .card.s2{--seg:var(--coop)} .card.s3{--seg:var(--mark)}

  ul.refs{list-style:none;padding:0;margin:12px 0}
  ul.refs li{position:relative;padding-left:16px;margin:11px 0;color:var(--dim);
    font-size:13.5px;line-height:1.55}
  ul.refs li::before{content:"·";position:absolute;left:2px;color:var(--cyan);font-weight:700}

  .find{display:flex;gap:12px;align-items:flex-start;margin:14px 0;
    background:var(--panel2);border:1px solid var(--hair);border-radius:8px;padding:14px 16px}
  .tag{flex:none;font-size:10px;letter-spacing:.8px;text-transform:uppercase;
    padding:3px 9px;border-radius:11px;font-weight:600;margin-top:1px;white-space:nowrap}
  .tag.no{background:#e8734a22;color:#f0956e;border:1px solid #6b3a2a}
  .tag.part{background:#e6c14a22;color:#e6c14a;border:1px solid #6b5b2a}
  .tag.now{background:#46c6d022;color:var(--cyan);border:1px solid #2a4a4f}
  .find div{font-size:13.5px;color:var(--dim);line-height:1.55}
  .find .h{color:var(--ink);font-weight:600}

  .callout{margin-top:20px;background:#0e1a1c;border:1px solid #234;border-radius:8px;
    padding:16px 18px;color:var(--dim);font-size:13.5px}
  .callout.warn{background:#1a130e;border-color:#4a3323}

  .flow{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:16px 0 6px}
  @media(max-width:520px){.flow{grid-template-columns:1fr}}
  .fcard{background:var(--panel2);border:1px solid var(--hair);border-radius:8px;padding:14px 16px}
  .fcard .ft{font-size:14px;font-weight:600;margin-bottom:8px;letter-spacing:.3px}
  .fcard.give .ft{color:var(--coop)} .fcard.take .ft{color:var(--amber)}
  .fcard .line{font-size:13px;color:var(--dim);margin:5px 0;font-variant-numeric:tabular-nums}
  .fcard .you{color:var(--ink)} .pos{color:var(--coop)} .neg{color:var(--amber)}
  .fcard .net{margin-top:9px;padding-top:9px;border-top:1px dashed #2a3a41;
    font-size:12px;color:var(--faint)}
  .fcard .net b{color:var(--mark)}

  footer{margin-top:44px;padding-top:18px;border-top:1px solid var(--hair);
    color:var(--faint);font-size:12.5px;line-height:1.7}
</style>
"""

# один шаблон блока; значения берутся из словаря языка
BLOCK = """<div class="langblock" data-lang="{lang}" lang="{lang}">
  <div class="eyebrow">{eyebrow}</div>
  <h1>{brand}</h1>
  <p class="lede">{lede}</p>
  <div class="cta">
    <a class="btn" href="{SIM}" target="_blank" rel="noopener">{cta_sim}</a>
    <a class="btn ghost" href="{GH}" target="_blank" rel="noopener">{cta_gh}</a>
  </div>

  <section><h2>{what_h2}</h2><h3>{what_h3}</h3><p>{what_p}</p></section>

  <section><h2>{q_h2}</h2><h3>{q_h3}</h3><p>{q_p}</p>
    <div class="stages">
      <div class="card s1"><div class="n">{s1_n}</div><h4>{s1_t}</h4><p>{s1_d}</p></div>
      <div class="card s2"><div class="n">{s2_n}</div><h4>{s2_t}</h4><p>{s2_d}</p></div>
      <div class="card s3"><div class="n">{s3_n}</div><h4>{s3_t}</h4><p>{s3_d}</p></div>
    </div></section>

  <section><h2>{roots_h2}</h2><h3>{roots_h3}</h3>
    <p>{roots_p1}</p><p>{roots_p2}</p>
    <div class="callout">{roots_call}</div></section>

  <section><h2>{refs_h2}</h2><h3>{refs_h3}</h3><p>{refs_p}</p>
    <ul class="refs"><li>{ref1}</li><li>{ref2}</li><li>{ref3}</li><li>{ref4}</li></ul></section>

  <section><h2>{coop_h2}</h2><h3>{coop_h3}</h3><p>{coop_intro}</p>
    <div class="flow">
      <div class="fcard give"><div class="ft">{give_t}</div>
        <div class="line"><span class="you">{w_you}</span>: <span class="neg">-8</span> {w_units}</div>
        <div class="line">{w_other}: <span class="pos">+12</span> {w_units}</div>
        <div class="net">{give_net}</div></div>
      <div class="fcard take"><div class="ft">{take_t}</div>
        <div class="line"><span class="you">{w_you}</span>: <span class="pos">+6</span> {w_units}</div>
        <div class="line">{w_other}: <span class="neg">-10</span> {w_units}</div>
        <div class="net">{take_net}</div></div>
    </div>
    <p>{coop_after}</p><p>{coop_theory}</p><p>{coop_result}</p>
    <div class="callout warn">{coop_warn}</div>
    <p>{coop_trap}</p><p>{coop_next}</p></section>

  <section><h2>{find_h2}</h2><h3>{find_h3}</h3><p>{find_p}</p>
    <div class="find"><span class="tag part">{tag_part}</span><div>{find1}</div></div>
    <div class="find"><span class="tag no">{tag_no}</span><div>{find2}</div></div>
    <div class="find"><span class="tag no">{tag_no}</span><div>{find3}</div></div>
    <div class="find"><span class="tag now">{tag_now}</span><div>{find_now}</div></div>
    <div class="callout">{find_sum}</div></section>

  <footer>{foot}</footer>
</div>"""

EN = dict(
  eyebrow="artificial life · open research",
  brand='mini<span class="dot">·</span>world',
  lede="<b>A tiny digital world where simple creatures live: they look for food, "
       "spend energy, reproduce, and die for good.</b> We watch whether behaviour "
       "that looks like <i>wanting</i> appears on its own — without us building the "
       "wanting in beforehand.",
  cta_sim="▶ watch the live simulation", cta_gh="code · data · report",
  what_h2="what it is", what_h3="Evolution with no judge",
  what_p="We built a little world and filled it with creatures. Each is run by a "
    "tiny “nervous system” passed to its offspring with small changes — like genes. "
    "Creatures search for food, spend energy to move, reproduce once they have enough, "
    "and <b>die for good</b> when their energy runs out. <b>There is no judge and no "
    "score</b> — we never say what is “good”. Those who cope better survive and "
    "reproduce, and the world tunes the creatures for survival, generation by generation.",
  q_h2="the core question", q_h3="Is vulnerability alone enough for “I want”?",
  q_p="A creature can die and “senses” its own state — hunger. Is that alone enough "
    "for behaviour that looks like a <b>desire</b> (“I want to eat”, “I’ll play it "
    "safe”) to arise — without us writing in a reward for the right moves? This is an "
    "old question about where needs come from. We try to answer it by <b>measurement, "
    "not argument</b>, split into three stages.",
  s1_n="stage 1", s1_t="Knowing yourself",
  s1_d="Does a creature behave differently when it “sees” its own hunger than when "
    "it’s fed a look-alike but foreign signal?",
  s2_n="stage 2", s2_t="Caring for others",
  s2_d="Does cooperation — sharing food — appear exactly when food grows scarce?",
  s3_n="stage 3", s3_t="The sign",
  s3_d="Can a mark a creature leaves <i>for others</i> become, over time, a tool "
    "<i>for itself</i>?",
  roots_h2="where the idea grows from", roots_h3="Vygotsky and Ilyenkov",
  roots_p1='Stage 3 is a direct test of the psychologist '
    '<a href="https://en.wikipedia.org/wiki/Lev_Vygotsky" target="_blank" rel="noopener">Lev Vygotsky</a>: '
    "<b>every ability appears twice — first between people, then within the person</b>. "
    "First a word or sign is a way to address someone else (“look over there”), and only "
    "later does the person apply the same sign to themselves and reshape their own thinking. "
    "His example: a knot tied in a handkerchief “so as not to forget” — an external cue you "
    "left for yourself. Our question is exactly that: <b>will a mark switch its addressee "
    "from “another” to “oneself” within a single creature’s life?</b>",
  roots_p2='The philosopher '
    '<a href="https://en.wikipedia.org/wiki/Evald_Ilyenkov" target="_blank" rel="noopener">Evald Ilyenkov</a> '
    "took this to its limit: <b>meanings and the “ideal” live not in the brain but in external "
    "things and the shared activity of people</b> — in signs, tools, culture; the brain merely "
    "“plugs into” this field. Hence his strong claim — <b>needs and the psyche itself can be "
    "assembled from outside</b>. He pointed to the Zagorsk school, where the inner world and "
    "needs of deaf-blind children were built up from outside, through joint activity with adults.",
  roots_call="Why this matters to us: so far everything “inner” in our creatures was innate, "
    "wired into the genes. The sign is the <b>first place where something that governs behaviour "
    "could come from outside</b>, from interaction rather than the genome. If a creature walked "
    "this path in the right order, the claim “needs can be given from outside” would gain a "
    "measurement, not just an argument. If it doesn’t — that’s an answer too: vulnerability and "
    "marks alone are not enough.",
  refs_h2="what we build on", refs_h3="We’re not the first — and that’s good",
  refs_p="Similar ideas have been tested. We stand on this work, and our job is to close "
    "the gap they left:",
  ref1=f'<a href="{KERAMATI}" target="_blank" rel="noopener">Keramati & Gutkin (2011)</a> — '
    "proved that “having a need” and “acting purposefully” are mathematically the same thing. "
    "But there the reward is set in advance; we test whether <b>selection alone</b> suffices.",
  ref2=f'<a href="{POLY}" target="_blank" rel="noopener">Polyworld, Yaeger (1994)</a> — almost our '
    "project, 30 years earlier: creatures, neural nets, no judge.",
  ref3=f'<a href="{CREATURES}" target="_blank" rel="noopener">Creatures, Grand (1996)</a> — creatures '
    "with a brain, a simulated biochemistry and lifetime learning. But their drives are "
    "<b>built in by the designer</b> — exactly what we test whether we can do without.",
  ref4=f'<a href="{REQUEJO}" target="_blank" rel="noopener">Requejo & Camacho</a> — predicted that '
    "scarcity makes unconditional cooperators win (stage 2); and "
    f'<a href="{YOSHIDA}" target="_blank" rel="noopener">Yoshida & Man (2024)</a> — that access to '
    "another’s state gives rise to caring for it.",
  coop_h2="deep dive · stage 2", coop_h3="Cooperation — the trickiest case",
  coop_intro="Our world has no pre-written “game with points”. Cooperation and selfishness grow "
    "straight out of food and energy. A creature has two ways to treat a neighbour:",
  w_you="you", w_other="neighbour", w_units="energy",
  give_t="share", give_net="the world gained <b>+4</b> energy — as if from nowhere",
  take_t="take", take_net="the world lost <b>-4</b> energy — some vanished",
  coop_after="No one forces sharing — generosity is either fixed by selection or not. Sharing is "
    "good for everyone together (the receiver gains more than the giver loses), while taking is "
    "destructive (the neighbour loses more than you gain). From this tension a “morality” should "
    "grow — or fail to.",
  coop_theory=f'<b>What theory predicted.</b> A well-known paper '
    f'(<a href="{REQUEJO}" target="_blank" rel="noopener">Requejo & Camacho</a>): when food is '
    "<b>scarce</b>, unconditional sharers should win — even in very simple creatures with no memory "
    "and no recognition. When food is <b>plentiful</b>, everyone turns selfish. We wanted to test "
    "this: if it holds, the engine can be trusted; if not, we learn it “lies” <i>before</i> we build "
    "conclusions on it.",
  coop_result="<b>What happened.</b> We saw no clean flip from “selfish under plenty” to “altruist "
    "under scarcity”: the share of cooperation jumped around and stayed low at every food level. "
    "Creatures almost always preferred to take.",
  coop_warn="<b>And here’s the interesting part: we found out why the test failed.</b> Look again at "
    "“share”: each act of generosity adds <b>+4 energy out of nowhere</b>. So cooperation acted as an "
    "<b>energy pump</b>: the more a group shared, the faster it multiplied — and ballooned to the "
    "population ceiling, after which such a run had to be thrown out as invalid. So “lots of "
    "cooperation” and “the run was excluded” became tied together <b>by construction</b>, and the "
    "honest picture couldn’t be seen.",
  coop_trap="<b>Another measurement trap.</b> We used to notice a neat link: “the hungry are kinder” "
    "(the hungrier, the more they share). It turned out to be mostly an illusion. The action “take” "
    "<b>itself raises</b> your energy. So among the “well-fed” there are, by construction, many who "
    "just took — and it looks as if being fed makes you selfish. When we measured each creature "
    "<b>against itself over time</b> (rather than comparing different creatures in a crowd), the link "
    "nearly vanished.",
  coop_next="<b>What’s next.</b> We’re fixing the “energetics”: sharing will cost exactly what the "
    "other receives — no energy from nowhere. Then cooperation becomes a <b>real choice</b>, not a "
    "free-energy trick, and the scarcity-vs-plenty prediction can be tested honestly.",
  find_h2="what we’ve learned so far", find_h3="Honestly — including what didn’t hold",
  find_p="A negative result here is as valuable as a positive one: it tells us what the recipe is "
    "missing and keeps us from fooling ourselves.",
  tag_part="partial", tag_no="not confirmed", tag_now="studying now",
  find1="<span class='h'>Stage 1 — knowing yourself.</span> Creatures that “see” their own hunger "
    "really do behave differently than with a foreign signal — reliably and repeatably. But the effect "
    "turned out <b>weaker than the world’s own random swings</b> between runs, so by our strict bar we "
    "did not count it as proven.",
  find2="<span class='h'>Stage 2 — caring for others.</span> We saw no clean “cooperation under "
    "scarcity” — and <b>found why</b>: in the model, sharing was unfairly profitable (it “created” "
    "extra energy). And the famous “the hungry are kinder” link was mostly a measurement artefact.",
  find3="<span class='h'>Stage 3 — the sign.</span> Creatures barely use marks, and selection actually "
    "<b>switches off</b> the ability to keep learning during life. No turning of a sign “for others” "
    "into a sign “for oneself” occurred — self-directed use was innate, not learned.",
  find_now="We’re fixing the “energetics” of cooperation to re-test stage 2 honestly, and thinking about "
    "how to give marks a real use — otherwise stage 3 can’t be tested at all.",
  find_sum="The honest bottom line: none of the three stages has “fired” at full strength yet — but in "
    "each case we understand <b>exactly what is blocking it</b>, and that is already a result. These "
    "findings update as new experiments come in.",
  foot=f'Open research. Full report with numbers, all code and raw data — '
    f'<a href="{GH}" target="_blank" rel="noopener">github.com/akela1308/minimir</a> · '
    f'<a href="{SIM}" target="_blank" rel="noopener">live simulation</a>',
)

RU = dict(
  eyebrow="искусственная жизнь · открытое исследование",
  brand='мини<span class="dot">·</span>мир',
  lede="<b>Крошечный цифровой мир, где живут простые существа: они ищут еду, тратят силы, "
    "размножаются и умирают насовсем.</b> Мы смотрим, появится ли у них само собой поведение, "
    "похожее на <i>желание</i>, — без того, чтобы мы это желание заранее в них заложили.",
  cta_sim="▶ смотреть живую симуляцию", cta_gh="код · данные · отчёт",
  what_h2="что это", what_h3="Эволюция без судьи",
  what_p="Мы построили маленький мир и населили его существами. Каждым управляет крошечная "
    "«нервная система», которая передаётся потомкам с небольшими изменениями — как гены. Существа "
    "ищут еду, тратят силы на движение, размножаются, когда накопят достаточно, и <b>умирают "
    "насовсем</b>, если силы кончились. <b>Никакого судьи и никаких оценок нет</b> — мы не говорим, "
    "что «хорошо». Выживают и оставляют потомство те, кто лучше справляется, и мир, поколение за "
    "поколением, «настраивает» существ под выживание.",
  q_h2="главный вопрос", q_h3="Достаточно ли одной уязвимости, чтобы появилось «хочу»?",
  q_p="Существо может умереть и «чувствует» своё состояние — голод. Хватит ли только этого, чтобы "
    "у него само собой возникло поведение, похожее на <b>желание</b> («хочу есть», «поберегусь»), — "
    "без того, чтобы мы вписали в него награду за правильные поступки? Это старый вопрос о том, "
    "откуда берутся потребности. Мы пробуем ответить на него <b>измерением, а не рассуждением</b>, "
    "и разбили его на три ступени.",
  s1_n="ступень 1", s1_t="Знание о себе",
  s1_d="Ведёт ли себя существо иначе, когда «видит» свой голод, чем когда ему подсунули такой же по "
    "виду, но чужой сигнал?",
  s2_n="ступень 2", s2_t="Забота о других",
  s2_d="Появляется ли сотрудничество — делиться едой — именно тогда, когда еды становится мало?",
  s3_n="ступень 3", s3_t="Знак",
  s3_d="Может ли метка, которую существо оставляет <i>для других</i>, со временем стать инструментом "
    "<i>для себя самого</i>?",
  roots_h2="откуда растёт идея", roots_h3="Выготский и Ильенков",
  roots_p1='Ступень 3 — это прямая проверка мысли психолога '
    '<a href="https://ru.wikipedia.org/wiki/Выготский,_Лев_Семёнович" target="_blank" rel="noopener">Льва Выготского</a>: '
    "<b>всякая способность появляется дважды — сначала между людьми, потом внутри человека</b>. Сначала "
    "слово или знак — это способ обратиться к другому («посмотри туда»), и лишь позже тот же знак человек "
    "применяет к себе и так перестраивает собственное мышление. Его пример — узелок на платке «чтобы не "
    "забыть»: внешняя подсказка, которую сам себе оставил. Наш вопрос ровно такой: <b>сменит ли метка "
    "адресата с «другого» на «себя» в течение жизни одного существа?</b>",
  roots_p2='Философ '
    '<a href="https://ru.wikipedia.org/wiki/Ильенков,_Эвальд_Васильевич" target="_blank" rel="noopener">Эвальд Ильенков</a> '
    "довёл эту мысль до предела: <b>смыслы и «идеальное» живут не в мозге, а во внешних вещах и совместных "
    "делах людей</b> — в знаках, орудиях, культуре; а мозг лишь «подключается» к этому полю. Отсюда его "
    "сильное утверждение — <b>потребности и саму психику можно собрать извне</b>. Он ссылался на Загорский "
    "интернат, где у слепоглухих детей внутренний мир и потребности выстраивали снаружи, через совместную "
    "деятельность со взрослыми.",
  roots_call="Почему это важно для нас: до сих пор всё «внутреннее» у наших существ было врождённым, зашитым "
    "в гены. Знак — <b>первое место, где нечто, управляющее поведением, могло бы прийти извне</b>, из "
    "взаимодействия, а не из генома. Пройди существо этот путь в нужном порядке — у идеи «потребность можно "
    "дать извне» появилось бы не рассуждение, а измерение. Не проходит — это тоже ответ: значит, одной "
    "уязвимости и меток мало.",
  refs_h2="на что мы опираемся", refs_h3="Мы не первые — и это хорошо",
  refs_p="Похожие идеи уже проверяли. Мы стоим на этих работах, а наша задача — закрыть щель, которую они "
    "оставили:",
  ref1=f'<a href="{KERAMATI}" target="_blank" rel="noopener">Керамати и Гуткин (2011)</a> — доказали, что '
    "«иметь потребность» и «вести себя целенаправленно» — математически одно и то же. Но у них награда задана "
    "заранее; мы проверяем, хватит ли <b>одного отбора</b>.",
  ref2=f'<a href="{POLY}" target="_blank" rel="noopener">Polyworld, Йегер (1994)</a> — почти наш проект, но на '
    "30 лет раньше: существа, нейросети и никакого судьи.",
  ref3=f'<a href="{CREATURES}" target="_blank" rel="noopener">Creatures, Гранд (1996)</a> — существа с мозгом, '
    "симулированной биохимией и обучением при жизни. Но их драйвы <b>заданы конструктором</b> — ровно то, без "
    "чего мы проверяем, можно ли обойтись.",
  ref4=f'<a href="{REQUEJO}" target="_blank" rel="noopener">Рекехо и Камачо</a> — предсказали, что при нехватке '
    "еды побеждают безусловные кооператоры (ступень 2); а "
    f'<a href="{YOSHIDA}" target="_blank" rel="noopener">Йошида и Ман (2024)</a> — что доступ к состоянию '
    "другого рождает заботу о нём.",
  coop_h2="разбор · ступень 2", coop_h3="Про кооперацию — самый хитрый случай",
  coop_intro="В нашем мире нет заранее прописанной «игры с очками». Сотрудничество и эгоизм вырастают прямо "
    "из еды и сил. У существа есть два способа обойтись с соседом:",
  w_you="ты", w_other="сосед", w_units="сил",
  give_t="поделиться", give_net="в мире стало <b>+4</b> силы — будто из ниоткуда",
  take_t="отнять", take_net="в мире стало <b>-4</b> силы — часть исчезла",
  coop_after="Никто не заставляет делиться — щедрость либо закрепляется отбором, либо нет. Отдать выгодно "
    "всем вместе (получатель приобретает больше, чем теряет отдающий), а отнять — разрушительно. Из этого "
    "противоречия и должна вырасти «мораль» — или не вырасти.",
  coop_theory=f'<b>Что предсказывала теория.</b> Известная работа '
    f'(<a href="{REQUEJO}" target="_blank" rel="noopener">Рекехо и Камачо</a>): когда еды <b>мало</b>, должны '
    "побеждать те, кто безусловно делится, — даже у совсем простых существ без памяти и без узнавания. Когда "
    "еды <b>в избытке</b> — все становятся эгоистами. Сбудется — движку можно доверять; нет — узнаем, что он "
    "«врёт», <i>раньше</i>, чем построим на нём выводы.",
  coop_result="<b>Что вышло.</b> Чёткого перелома «эгоисты при изобилии → альтруисты при нехватке» мы не "
    "увидели: доля сотрудничества скакала беспорядочно и была низкой при любом количестве еды. Существа почти "
    "всегда предпочитали отнимать.",
  coop_warn="<b>И вот тут — самое интересное: мы поняли, почему тест не сработал.</b> Посмотри ещё раз на "
    "«поделиться»: на каждый акт щедрости в мире появляется <b>+4 силы из ниоткуда</b>. Сотрудничество "
    "работало как <b>насос энергии</b>: чем больше группа делилась, тем быстрее размножалась — и разрасталась "
    "до потолка численности, после чего такой прогон приходилось выбрасывать как негодный. «Много кооперации» "
    "и «прогон вылетел» связаны <b>по построению</b> — честной картины было не увидеть.",
  coop_trap="<b>Ещё одна ловушка измерения.</b> Раньше мы замечали красивую связь: «голодные — добрее». "
    "Оказалось — обман. Ведь «отнять» <b>само поднимает</b> твою энергию, и среди «сытых» по построению много "
    "тех, кто только что отнял. Когда мы стали мерить каждое существо <b>само против себя во времени</b>, связь "
    "почти исчезла.",
  coop_next="<b>Что дальше.</b> Чиним «энергетику»: отдать будет стоить ровно столько, сколько получает "
    "другой, — никакой энергии из ниоткуда. Тогда сотрудничество станет <b>настоящим выбором</b>, и "
    "предсказание про изобилие и нехватку можно проверить честно.",
  find_h2="что мы уже узнали", find_h3="Честно — в том числе о том, что не подтвердилось",
  find_p="Отрицательный результат здесь такой же ценный, как положительный: он говорит, чего в рецепте не "
    "хватает, и не даёт обмануть себя.",
  tag_part="частично", tag_no="не подтвердилось", tag_now="изучаем сейчас",
  find1="<span class='h'>Ступень 1 — знание о себе.</span> Существа, «видящие» свой голод, и правда ведут себя "
    "иначе, чем с чужим сигналом, — устойчиво. Но эффект оказался <b>слабее случайных колебаний</b> самого мира "
    "между запусками, поэтому по строгому порогу мы не засчитали его как доказанный.",
  find2="<span class='h'>Ступень 2 — забота о других.</span> «Сотрудничества при нехватке» чисто не увидели — и "
    "<b>нашли, почему</b>: делиться было нечестно выгодно (это «создавало» энергию). А связь «голодные добрее» "
    "оказалась в основном обманом измерения.",
  find3="<span class='h'>Ступень 3 — знак.</span> Существа почти не пользуются метками, а способность "
    "«доучиваться» при жизни отбор <b>выключает</b>. Превращения знака «для других» в знак «для себя» не "
    "произошло — самонаправленность врождённая, а не выученная.",
  find_now="Чиним «энергетику» кооперации, чтобы честно перепроверить ступень 2, и думаем, как дать меткам "
    "реальную пользу, — иначе ступень 3 непроверяема.",
  find_sum="Итог по-честному: пока ни одна из трёх ступеней не «выстрелила» в полную силу — но в каждом случае "
    "мы понимаем, <b>что именно мешает</b>, и это уже результат. Выводы обновляются по мере новых экспериментов.",
  foot=f'Открытое исследование. Полный отчёт с числами, весь код и сырые данные — '
    f'<a href="{GH}" target="_blank" rel="noopener">github.com/akela1308/minimir</a> · '
    f'<a href="{SIM}" target="_blank" rel="noopener">живая симуляция</a>',
)

DE = dict(
  eyebrow="künstliches leben · offene forschung",
  brand='mini<span class="dot">·</span>welt',
  lede="<b>Eine winzige digitale Welt, in der einfache Wesen leben: Sie suchen Futter, verbrauchen Kraft, "
    "pflanzen sich fort und sterben endgültig.</b> Wir beobachten, ob von selbst ein Verhalten entsteht, das "
    "wie ein <i>Wollen</i> aussieht — ohne dass wir dieses Wollen vorher einbauen.",
  cta_sim="▶ live-simulation ansehen", cta_gh="code · daten · bericht",
  what_h2="was es ist", what_h3="Evolution ohne Schiedsrichter",
  what_p="Wir haben eine kleine Welt gebaut und mit Wesen bevölkert. Jedes wird von einem winzigen "
    "„Nervensystem“ gesteuert, das mit kleinen Änderungen an die Nachkommen weitergegeben wird — wie Gene. "
    "Die Wesen suchen Futter, verbrauchen Kraft beim Bewegen, pflanzen sich fort, sobald sie genug haben, und "
    "<b>sterben endgültig</b>, wenn die Kraft ausgeht. <b>Es gibt keinen Schiedsrichter und keine Punkte</b> — "
    "wir sagen nie, was „gut“ ist. Wer besser zurechtkommt, überlebt und pflanzt sich fort, und die Welt stimmt "
    "die Wesen Generation für Generation aufs Überleben ein.",
  q_h2="die kernfrage", q_h3="Reicht Verletzlichkeit allein für ein „Ich will“?",
  q_p="Ein Wesen kann sterben und „spürt“ seinen Zustand — Hunger. Reicht das allein, damit von selbst ein "
    "Verhalten wie ein <b>Wunsch</b> entsteht („Ich will fressen“, „Ich gehe auf Nummer sicher“) — ohne dass "
    "wir eine Belohnung für richtige Züge einschreiben? Das ist eine alte Frage danach, woher Bedürfnisse "
    "kommen. Wir versuchen sie <b>durch Messung, nicht durch Argumentation</b> zu beantworten, aufgeteilt in "
    "drei Stufen.",
  s1_n="stufe 1", s1_t="Sich selbst kennen",
  s1_d="Verhält sich ein Wesen anders, wenn es seinen eigenen Hunger „sieht“, als wenn man ihm ein "
    "gleich aussehendes, aber fremdes Signal vorsetzt?",
  s2_n="stufe 2", s2_t="Fürsorge für andere",
  s2_d="Entsteht Kooperation — Futter teilen — gerade dann, wenn das Futter knapp wird?",
  s3_n="stufe 3", s3_t="Das Zeichen",
  s3_d="Kann eine Markierung, die ein Wesen <i>für andere</i> hinterlässt, mit der Zeit zu einem Werkzeug "
    "<i>für sich selbst</i> werden?",
  roots_h2="woraus die idee wächst", roots_h3="Wygotski und Iljenkow",
  roots_p1='Stufe 3 prüft direkt einen Gedanken des Psychologen '
    '<a href="https://de.wikipedia.org/wiki/Lew_Semjonowitsch_Wygotski" target="_blank" rel="noopener">Lew Wygotski</a>: '
    "<b>jede Fähigkeit erscheint zweimal — zuerst zwischen Menschen, dann im Inneren des Menschen</b>. Zuerst ist "
    "ein Wort oder Zeichen ein Weg, sich an einen anderen zu wenden („schau dorthin“), und erst später wendet der "
    "Mensch dasselbe Zeichen auf sich selbst an und formt so sein eigenes Denken um. Sein Beispiel: ein Knoten im "
    "Taschentuch „um nicht zu vergessen“ — ein äußerer Hinweis, den man sich selbst hinterlässt. Genau das ist "
    "unsere Frage: <b>wechselt eine Markierung ihren Adressaten vom „anderen“ zum „selbst“ innerhalb eines "
    "einzigen Wesenslebens?</b>",
  roots_p2='Der Philosoph '
    '<a href="https://de.wikipedia.org/wiki/Ewald_Iljenkow" target="_blank" rel="noopener">Ewald Iljenkow</a> '
    "trieb diesen Gedanken auf die Spitze: <b>Bedeutungen und das „Ideale“ leben nicht im Gehirn, sondern in "
    "äußeren Dingen und der gemeinsamen Tätigkeit der Menschen</b> — in Zeichen, Werkzeugen, Kultur; das Gehirn "
    "„klinkt sich“ nur in dieses Feld ein. Daher seine starke Behauptung — <b>Bedürfnisse und die Psyche selbst "
    "lassen sich von außen zusammensetzen</b>. Er verwies auf das Internat von Sagorsk, wo die Innenwelt und die "
    "Bedürfnisse taubblinder Kinder von außen aufgebaut wurden, durch gemeinsame Tätigkeit mit Erwachsenen.",
  roots_call="Warum uns das wichtig ist: Bisher war alles „Innere“ unserer Wesen angeboren, in die Gene "
    "geschrieben. Das Zeichen ist der <b>erste Ort, an dem etwas, das Verhalten steuert, von außen kommen "
    "könnte</b>, aus Interaktion statt aus dem Genom. Ginge ein Wesen diesen Weg in der richtigen Reihenfolge, "
    "bekäme die Behauptung „Bedürfnisse kann man von außen geben“ eine Messung statt nur ein Argument. Geschieht "
    "es nicht — auch das ist eine Antwort: Verletzlichkeit und Markierungen allein genügen nicht.",
  refs_h2="worauf wir aufbauen", refs_h3="Wir sind nicht die Ersten — und das ist gut",
  refs_p="Ähnliche Ideen wurden bereits geprüft. Wir bauen auf diesen Arbeiten auf, und unsere Aufgabe ist es, "
    "die Lücke zu schließen, die sie gelassen haben:",
  ref1=f'<a href="{KERAMATI}" target="_blank" rel="noopener">Keramati & Gutkin (2011)</a> — bewiesen, dass '
    "„ein Bedürfnis haben“ und „zielgerichtet handeln“ mathematisch dasselbe sind. Doch dort ist die Belohnung "
    "vorab gesetzt; wir prüfen, ob <b>Selektion allein</b> genügt.",
  ref2=f'<a href="{POLY}" target="_blank" rel="noopener">Polyworld, Yaeger (1994)</a> — fast unser Projekt, 30 '
    "Jahre früher: Wesen, neuronale Netze, kein Schiedsrichter.",
  ref3=f'<a href="{CREATURES}" target="_blank" rel="noopener">Creatures, Grand (1996)</a> — Wesen mit Gehirn, '
    "simulierter Biochemie und lebenslangem Lernen. Doch ihre Triebe sind <b>vom Designer eingebaut</b> — genau "
    "das, wovon wir prüfen, ob es entbehrlich ist.",
  ref4=f'<a href="{REQUEJO}" target="_blank" rel="noopener">Requejo & Camacho</a> — sagten voraus, dass Knappheit '
    "bedingungslose Kooperierende gewinnen lässt (Stufe 2); und "
    f'<a href="{YOSHIDA}" target="_blank" rel="noopener">Yoshida & Man (2024)</a> — dass der Zugang zum Zustand '
    "eines anderen Fürsorge für ihn entstehen lässt.",
  coop_h2="vertiefung · stufe 2", coop_h3="Kooperation — der kniffligste Fall",
  coop_intro="Unsere Welt hat kein vorgeschriebenes „Spiel mit Punkten“. Kooperation und Egoismus wachsen "
    "direkt aus Futter und Kraft. Ein Wesen hat zwei Weisen, mit einem Nachbarn umzugehen:",
  w_you="du", w_other="Nachbar", w_units="Kraft",
  give_t="teilen", give_net="in der Welt entstanden <b>+4</b> Kraft — wie aus dem Nichts",
  take_t="nehmen", take_net="in der Welt verschwanden <b>-4</b> Kraft",
  coop_after="Niemand zwingt zum Teilen — Großzügigkeit wird durch Selektion gefestigt oder nicht. Geben nützt "
    "allen zusammen (der Empfänger gewinnt mehr, als der Gebende verliert), Nehmen ist zerstörerisch. Aus diesem "
    "Widerspruch soll eine „Moral“ wachsen — oder nicht.",
  coop_theory=f'<b>Was die Theorie vorhersagte.</b> Eine bekannte Arbeit '
    f'(<a href="{REQUEJO}" target="_blank" rel="noopener">Requejo & Camacho</a>): bei <b>knappem</b> Futter sollten '
    "die bedingungslos Teilenden gewinnen — sogar bei ganz einfachen Wesen ohne Gedächtnis und ohne Erkennen. Bei "
    "<b>reichlich</b> Futter werden alle egoistisch. Trifft es zu, ist die Engine vertrauenswürdig; wenn nicht, "
    "erfahren wir <i>vorher</i>, dass sie „lügt“.",
  coop_result="<b>Was geschah.</b> Wir sahen kein sauberes Umschlagen von „egoistisch im Überfluss“ zu „altruistisch "
    "bei Knappheit“: der Kooperationsanteil sprang wild und blieb bei jedem Futterniveau niedrig. Die Wesen "
    "zogen fast immer das Nehmen vor.",
  coop_warn="<b>Und hier das Interessante: Wir fanden heraus, warum der Test scheiterte.</b> Schau nochmal auf "
    "„teilen“: jede Großzügigkeit fügt <b>+4 Kraft aus dem Nichts</b> hinzu. Kooperation wirkte als <b>Energiepumpe</b>: "
    "je mehr eine Gruppe teilte, desto schneller vermehrte sie sich — und stieg bis zur Populationsobergrenze, "
    "worauf ein solcher Lauf als ungültig verworfen werden musste. „Viel Kooperation“ und „Lauf ausgeschlossen“ "
    "waren <b>konstruktionsbedingt</b> verkoppelt — das ehrliche Bild war nicht zu sehen.",
  coop_trap="<b>Noch eine Messfalle.</b> Früher bemerkten wir einen hübschen Zusammenhang: „die Hungrigen sind "
    "gütiger“. Es war meist eine Täuschung. Denn „nehmen“ <b>hebt selbst</b> deine Energie, und unter den „Satten“ "
    "sind konstruktionsbedingt viele, die gerade genommen haben. Als wir jedes Wesen <b>gegen sich selbst über die "
    "Zeit</b> maßen, verschwand der Zusammenhang fast.",
  coop_next="<b>Wie es weitergeht.</b> Wir reparieren die „Energetik“: Geben wird genau so viel kosten, wie der "
    "andere erhält — keine Energie aus dem Nichts. Dann wird Kooperation zu einer <b>echten Wahl</b>, und die "
    "Knappheit-gegen-Überfluss-Vorhersage lässt sich ehrlich prüfen.",
  find_h2="was wir bisher gelernt haben", find_h3="Ehrlich — auch was nicht hielt",
  find_p="Ein negatives Ergebnis ist hier so wertvoll wie ein positives: es sagt, was im Rezept fehlt, und "
    "bewahrt uns vor Selbsttäuschung.",
  tag_part="teilweise", tag_no="nicht bestätigt", tag_now="wird untersucht",
  find1="<span class='h'>Stufe 1 — sich selbst kennen.</span> Wesen, die ihren eigenen Hunger „sehen“, verhalten "
    "sich wirklich anders als mit einem fremden Signal — zuverlässig. Doch der Effekt war <b>schwächer als die "
    "zufälligen Schwankungen</b> der Welt zwischen Läufen, daher zählten wir ihn nach unserer strengen Schwelle "
    "nicht als bewiesen.",
  find2="<span class='h'>Stufe 2 — Fürsorge für andere.</span> „Kooperation bei Knappheit“ sahen wir nicht sauber — "
    "und <b>fanden warum</b>: Teilen war unfair profitabel (es „erschuf“ Energie). Und der berühmte Zusammenhang "
    "„die Hungrigen sind gütiger“ war meist ein Messartefakt.",
  find3="<span class='h'>Stufe 3 — das Zeichen.</span> Die Wesen nutzen Markierungen kaum, und die Selektion "
    "<b>schaltet</b> die Fähigkeit, im Leben weiterzulernen, sogar <b>ab</b>. Kein Umschlagen eines Zeichens „für "
    "andere“ in ein Zeichen „für sich“ — die Selbstbezogenheit war angeboren, nicht gelernt.",
  find_now="Wir reparieren die „Energetik“ der Kooperation, um Stufe 2 ehrlich erneut zu prüfen, und überlegen, wie "
    "man Markierungen einen echten Nutzen gibt — sonst ist Stufe 3 gar nicht prüfbar.",
  find_sum="Das ehrliche Fazit: keine der drei Stufen hat bisher voll „gezündet“ — aber in jedem Fall verstehen wir "
    "<b>genau, was sie blockiert</b>, und das ist bereits ein Ergebnis. Diese Befunde aktualisieren sich mit neuen "
    "Experimenten.",
  foot=f'Offene Forschung. Vollständiger Bericht mit Zahlen, gesamter Code und Rohdaten — '
    f'<a href="{GH}" target="_blank" rel="noopener">github.com/akela1308/minimir</a> · '
    f'<a href="{SIM}" target="_blank" rel="noopener">live-simulation</a>',
)

ZH = dict(
  eyebrow="人工生命 · 开放研究",
  brand='微<span class="dot">·</span>世界',
  lede="<b>一个微小的数字世界，里面住着简单的生物：它们寻找食物、消耗体力、繁殖，并且会彻底死亡。</b>"
    "我们观察，它们是否会自行出现一种看起来像<i>“想要”</i>的行为——而不需要我们事先把“想要”写进去。",
  cta_sim="▶ 观看实时模拟", cta_gh="代码 · 数据 · 报告",
  what_h2="这是什么", what_h3="没有裁判的演化",
  what_p="我们建了一个小世界，并让生物在其中生活。每个生物由一个微小的“神经系统”驱动，它会带着细微的变化"
    "传给后代——就像基因。生物寻找食物、移动时消耗体力、积累足够后繁殖，体力耗尽就<b>彻底死亡</b>。"
    "<b>这里没有裁判，也没有评分</b>——我们从不说什么是“好”。谁应付得更好，谁就存活并繁殖；世界一代又一代"
    "地把生物“调校”得适于生存。",
  q_h2="核心问题", q_h3="单凭脆弱，就足以产生“我想要”吗？",
  q_p="生物会死亡，并且能“感知”自身状态——饥饿。仅凭这一点，是否足以自行产生一种像<b>欲望</b>的行为"
    "（“我想吃”“我要保守一点”）——而不需要我们为正确的行为写入奖励？这是一个古老的问题：需求从何而来。"
    "我们试着<b>用测量而非论证</b>来回答，并把它分成三个阶段。",
  s1_n="阶段 1", s1_t="认识自己",
  s1_d="当生物“看到”自己的饥饿时，它的行为是否不同于被喂入一个看起来相同、却与它无关的信号？",
  s2_n="阶段 2", s2_t="关心他者",
  s2_d="合作——分享食物——是否恰恰在食物变得稀缺时出现？",
  s3_n="阶段 3", s3_t="记号",
  s3_d="生物<i>为他者</i>留下的记号，是否会随时间变成<i>为自己</i>的工具？",
  roots_h2="思想的来源", roots_h3="维果茨基与伊里因科夫",
  roots_p1='阶段 3 是对心理学家'
    '<a href="https://zh.wikipedia.org/wiki/列夫·维谷斯基" target="_blank" rel="noopener">列夫·维果茨基</a>'
    "思想的直接检验：<b>每一种能力都出现两次——先在人与人之间，然后在人的内部</b>。起初，词或记号是向他人"
    "发出的方式（“看那边”），只有到后来，人才把同一个记号用于自己，从而重塑自己的思维。他的例子：在手帕上"
    "打个结“以免忘记”——一个你留给自己的外部提示。我们的问题正是如此：<b>在一个生物的一生之内，记号的接收"
    "者会不会从“他者”变成“自己”？</b>",
  roots_p2='哲学家'
    '<a href="https://zh.wikipedia.org/wiki/埃瓦尔德·伊里因科夫" target="_blank" rel="noopener">埃瓦尔德·伊里因科夫</a>'
    "把这一思想推到极致：<b>意义与“观念性”并不住在大脑里，而是住在外部事物和人们的共同活动中</b>——在记号、"
    "工具、文化里；大脑只是“接入”这个场。因此他有一个强命题——<b>需求乃至心理本身，都可以从外部被搭建起来</b>。"
    "他引用扎戈尔斯克寄宿学校的例子：聋盲儿童的内心世界与需求，是通过与成人的共同活动从外部被建立起来的。",
  roots_call="为什么这对我们重要：迄今为止，我们生物身上所有“内在”的东西都是先天的、写在基因里的。记号是"
    "<b>第一个可能让某种支配行为的东西来自外部</b>的地方——来自互动而非基因组。如果一个生物按正确的顺序走过"
    "这条路，“需求可以从外部给予”这一命题就获得了测量，而不只是论证。如果走不通——那也是一个答案：仅凭脆弱"
    "与记号还不够。",
  refs_h2="我们所依托的", refs_h3="我们不是第一个——而这是好事",
  refs_p="类似的想法已被检验过。我们站在这些工作之上，而我们的任务是填补它们留下的缝隙：",
  ref1=f'<a href="{KERAMATI}" target="_blank" rel="noopener">Keramati 与 Gutkin（2011）</a>——证明了“拥有需求”'
    "与“有目的地行动”在数学上是同一回事。但那里奖励是事先设定的；我们检验的是<b>单凭选择</b>是否足够。",
  ref2=f'<a href="{POLY}" target="_blank" rel="noopener">Polyworld，Yaeger（1994）</a>——几乎就是我们的项目，'
    "只是早了 30 年：生物、神经网络、没有裁判。",
  ref3=f'<a href="{CREATURES}" target="_blank" rel="noopener">Creatures，Grand（1996）</a>——具有大脑、模拟生化'
    "与终身学习的生物。但它们的“驱力”是<b>由设计者内建的</b>——正是我们要检验能否舍弃的东西。",
  ref4=f'<a href="{REQUEJO}" target="_blank" rel="noopener">Requejo 与 Camacho</a>——预言稀缺会让无条件合作者胜出'
    f'（阶段 2）；而 <a href="{YOSHIDA}" target="_blank" rel="noopener">Yoshida 与 Man（2024）</a>——则表明，'
    "获得他者状态的通道会催生对他者的关心。",
  coop_h2="深入 · 阶段 2", coop_h3="合作——最棘手的一例",
  coop_intro="我们的世界没有预先写好的“计分游戏”。合作与自私直接从食物与体力中生长出来。生物对待邻居有两种方式：",
  w_you="你", w_other="邻居", w_units="体力",
  give_t="分享", give_net="世界里凭空多出了 <b>+4</b> 体力",
  take_t="夺取", take_net="世界里少了 <b>-4</b> 体力——有一部分消失了",
  coop_after="没有谁强迫分享——慷慨要么被选择固定下来，要么不会。给予对大家总体有利（接受者得到的多于给予者失去的），"
    "而夺取具有破坏性。正是从这一矛盾中，应当生长出“道德”——或者生长不出来。",
  coop_theory=f'<b>理论的预言。</b>一篇著名论文'
    f'（<a href="{REQUEJO}" target="_blank" rel="noopener">Requejo 与 Camacho</a>）：当食物<b>稀缺</b>时，无条件分享者'
    "应当胜出——即使是没有记忆、不会辨认的极简单生物。当食物<b>充裕</b>时，所有个体都变自私。若应验，引擎便可信；"
    "若不应验，我们就能<i>在</i>用它得出结论<i>之前</i>知道它在“撒谎”。",
  coop_result="<b>结果如何。</b>我们没有看到从“充裕时自私”到“稀缺时利他”的干净翻转：合作比例乱跳，且在任何食物水平"
    "都很低。生物几乎总是偏向夺取。",
  coop_warn="<b>而这里最有意思：我们弄清了测试为何失败。</b>再看“分享”：每一次慷慨都会<b>凭空增加 +4 体力</b>。"
    "于是合作起到了<b>能量泵</b>的作用：一个群体越是分享，繁殖得就越快——并膨胀到种群上限，此后这样的运行只能作为"
    "无效被丢弃。于是“合作很多”与“运行被排除”在<b>构造上</b>被绑在了一起——真实的图景无法看清。",
  coop_trap="<b>另一个测量陷阱。</b>我们过去注意到一个漂亮的关联：“越饿越善良”。结果多半是假象。因为“夺取”本身会"
    "<b>抬高</b>你的能量，于是在“吃饱者”当中，按构造就有很多刚刚夺取过的个体。当我们以<b>每个生物随时间与自身相比</b>"
    "来测量（而非在人群中比较不同个体）时，这个关联几乎消失。",
  coop_next="<b>下一步。</b>我们在修“能量学”：给予的代价将恰好等于对方所得——不再有凭空而来的能量。那样合作就成为"
    "<b>真正的选择</b>，而非免费能量的把戏，稀缺与充裕的预言便可被诚实地检验。",
  find_h2="我们已经学到的", find_h3="诚实地——也包括未被证实的",
  find_p="在这里，阴性结果与阳性结果同样宝贵：它告诉我们配方里缺了什么，并使我们不至于自欺。",
  tag_part="部分", tag_no="未被证实", tag_now="正在研究",
  find1="<span class='h'>阶段 1——认识自己。</span>“看到”自己饥饿的生物，确实表现得与用外来信号时不同——稳定且可复现。"
    "但该效应<b>弱于世界自身在不同运行之间的随机波动</b>，因此按我们严格的门槛，我们不把它算作已被证明。",
  find2="<span class='h'>阶段 2——关心他者。</span>我们没有干净地看到“稀缺下的合作”——并且<b>找到了原因</b>：在模型里"
    "分享是不公平地有利可图的（它“创造”了能量）。而著名的“越饿越善良”多半是测量假象。",
  find3="<span class='h'>阶段 3——记号。</span>生物几乎不使用记号，而选择甚至<b>关闭</b>了在一生中继续学习的能力。"
    "没有发生记号从“为他者”到“为自己”的转变——自我指向是先天的，而非习得的。",
  find_now="我们在修合作的“能量学”，以便诚实地重测阶段 2；并思考如何给记号以真正的用处——否则阶段 3 根本无法检验。",
  find_sum="诚实的结论：三个阶段迄今都还没有全力“点火”——但在每一种情形下，我们都明白<b>究竟是什么在阻碍它</b>，"
    "这本身就是结果。随着新实验到来，这些结论会不断更新。",
  foot=f'开放研究。含数据的完整报告、全部代码与原始数据——'
    f'<a href="{GH}" target="_blank" rel="noopener">github.com/akela1308/minimir</a> · '
    f'<a href="{SIM}" target="_blank" rel="noopener">实时模拟</a>',
)

ES = dict(
  eyebrow="vida artificial · investigación abierta",
  brand='mini<span class="dot">·</span>mundo',
  lede='<b>Un diminuto mundo digital donde viven criaturas simples: buscan comida, gastan energía, se reproducen y mueren para siempre.</b> Observamos si por sí solo surge un comportamiento que parece un <i>deseo</i> — sin que nosotros metamos ese deseo de antemano.',
  cta_sim="▶ ver la simulación en vivo", cta_gh="código · datos · informe",
  what_h2="qué es", what_h3="Evolución sin árbitro",
  what_p='Construimos un pequeño mundo y lo poblamos con criaturas. A cada una la gobierna un diminuto “sistema nervioso” que pasa a su descendencia con pequeños cambios — como genes. Las criaturas buscan comida, gastan energía al moverse, se reproducen cuando tienen suficiente y <b>mueren para siempre</b> cuando su energía se agota. <b>No hay árbitro ni puntuación</b> — nunca decimos qué es “bueno”. Sobreviven y se reproducen quienes se las arreglan mejor, y el mundo, generación tras generación, ajusta a las criaturas para sobrevivir.',
  q_h2="la pregunta central", q_h3="¿Basta la vulnerabilidad para un “quiero”?",
  q_p='Una criatura puede morir y “percibe” su propio estado — el hambre. ¿Basta solo con eso para que surja por sí mismo un comportamiento parecido a un <b>deseo</b> (“quiero comer”, “voy con cuidado”) — sin que escribamos una recompensa por los actos correctos? Es una vieja pregunta sobre de dónde vienen las necesidades. Intentamos responderla <b>midiendo, no argumentando</b>, dividida en tres etapas.',
  s1_n="etapa 1", s1_t="Conocerse a sí mismo",
  s1_d="¿Se comporta la criatura de otro modo cuando “ve” su propia hambre que cuando se le da una señal de aspecto igual pero ajena?",
  s2_n="etapa 2", s2_t="Cuidar de los demás",
  s2_d="¿Surge la cooperación — compartir comida — justo cuando la comida escasea?",
  s3_n="etapa 3", s3_t="El signo",
  s3_d="¿Puede una marca que la criatura deja <i>para otros</i> volverse, con el tiempo, una herramienta <i>para sí misma</i>?",
  roots_h2="de dónde nace la idea", roots_h3="Vygotsky e Ilyenkov",
  roots_p1='La etapa 3 pone a prueba directamente una idea del psicólogo <a href="https://es.wikipedia.org/wiki/Lev_Vygotski" target="_blank" rel="noopener">Lev Vygotsky</a>: <b>toda capacidad aparece dos veces — primero entre personas, luego dentro de la persona</b>. Al principio una palabra o un signo es un modo de dirigirse a otro (“mira allí”), y solo después la persona aplica ese mismo signo a sí misma y así reorganiza su propio pensamiento. Su ejemplo: un nudo en el pañuelo “para no olvidar” — una pista externa que uno se deja a sí mismo. Nuestra pregunta es justo esa: <b>¿cambiará una marca de destinatario, del “otro” a “uno mismo”, dentro de la vida de una sola criatura?</b>',
  roots_p2='El filósofo <a href="https://es.wikipedia.org/wiki/Evald_Iliénkov" target="_blank" rel="noopener">Evald Ilyenkov</a> llevó esta idea al límite: <b>los significados y lo “ideal” no viven en el cerebro, sino en las cosas externas y en la actividad compartida de las personas</b> — en signos, herramientas, cultura; el cerebro solo se “conecta” a ese campo. De ahí su fuerte afirmación — <b>las necesidades y la propia psique pueden ensamblarse desde fuera</b>. Se refería al internado de Zagorsk, donde el mundo interior y las necesidades de niños sordociegos se construyeron desde fuera, mediante la actividad conjunta con adultos.',
  roots_call="Por qué nos importa: hasta ahora todo lo “interno” en nuestras criaturas era innato, escrito en los genes. El signo es el <b>primer lugar donde algo que gobierna el comportamiento podría venir de fuera</b>, de la interacción y no del genoma. Si una criatura recorriera este camino en el orden correcto, la afirmación “las necesidades se pueden dar desde fuera” tendría una medición, no solo un argumento. Si no lo hace — también es una respuesta: la vulnerabilidad y las marcas por sí solas no bastan.",
  refs_h2="en qué nos apoyamos", refs_h3="No somos los primeros — y eso es bueno",
  refs_p="Ideas parecidas ya se han puesto a prueba. Nos apoyamos en estos trabajos, y nuestra tarea es cerrar el hueco que dejaron:",
  ref1=f'<a href="{KERAMATI}" target="_blank" rel="noopener">Keramati y Gutkin (2011)</a> — demostraron que “tener una necesidad” y “actuar con un fin” son matemáticamente lo mismo. Pero allí la recompensa está fijada de antemano; nosotros probamos si basta <b>la selección sola</b>.',
  ref2=f'<a href="{POLY}" target="_blank" rel="noopener">Polyworld, Yaeger (1994)</a> — casi nuestro proyecto, 30 años antes: criaturas, redes neuronales, sin árbitro.',
  ref3=f'<a href="{CREATURES}" target="_blank" rel="noopener">Creatures, Grand (1996)</a> — criaturas con cerebro, una bioquímica simulada y aprendizaje durante la vida. Pero sus impulsos están <b>incorporados por el diseñador</b> — justo aquello de lo que probamos si se puede prescindir.',
  ref4=f'<a href="{REQUEJO}" target="_blank" rel="noopener">Requejo y Camacho</a> — predijeron que la escasez hace ganar a los cooperadores incondicionales (etapa 2); y <a href="{YOSHIDA}" target="_blank" rel="noopener">Yoshida y Man (2024)</a> — que el acceso al estado de otro hace surgir el cuidado hacia él.',
  coop_h2="a fondo · etapa 2", coop_h3="La cooperación — el caso más difícil",
  coop_intro="Nuestro mundo no tiene un “juego con puntos” prescrito. La cooperación y el egoísmo crecen directamente de la comida y la energía. Una criatura tiene dos formas de tratar a un vecino:",
  w_you="tú", w_other="vecino", w_units="energía",
  give_t="compartir", give_net="el mundo ganó <b>+4</b> de energía — como de la nada",
  take_t="quitar", take_net="el mundo perdió <b>-4</b> de energía — algo desapareció",
  coop_after="Nadie obliga a compartir — la generosidad la fija la selección o no. Dar es bueno para todos juntos (quien recibe gana más de lo que pierde quien da), y quitar es destructivo. De esta tensión debería crecer una “moral” — o no crecer.",
  coop_theory=f'<b>Lo que predecía la teoría.</b> Un trabajo conocido (<a href="{REQUEJO}" target="_blank" rel="noopener">Requejo y Camacho</a>): cuando la comida es <b>escasa</b>, deberían ganar quienes comparten sin condiciones — incluso en criaturas muy simples, sin memoria ni reconocimiento. Cuando la comida es <b>abundante</b>, todos se vuelven egoístas. Si se cumple, se puede confiar en el motor; si no, sabemos que “miente” <i>antes</i> de construir conclusiones sobre él.',
  coop_result="<b>Qué ocurrió.</b> No vimos un giro limpio de “egoísta en la abundancia” a “altruista en la escasez”: la proporción de cooperación saltaba sin orden y era baja en cualquier nivel de comida. Las criaturas casi siempre preferían quitar.",
  coop_warn="<b>Y aquí lo interesante: descubrimos por qué falló la prueba.</b> Mira de nuevo “compartir”: cada acto de generosidad añade <b>+4 de energía de la nada</b>. Así, la cooperación actuaba como una <b>bomba de energía</b>: cuanto más compartía un grupo, más rápido se multiplicaba — y crecía hasta el tope de población, tras lo cual esa ejecución había que descartarla como inválida. Así “mucha cooperación” y “ejecución excluida” quedaron ligadas <b>por construcción</b>, y no se podía ver la imagen honesta.",
  coop_trap="<b>Otra trampa de medición.</b> Antes notábamos un vínculo bonito: “los hambrientos son más amables”. Resultó ser sobre todo una ilusión. Porque “quitar” <b>sube por sí mismo</b> tu energía, y entre los “saciados” hay, por construcción, muchos que acaban de quitar. Cuando medimos cada criatura <b>contra sí misma a lo largo del tiempo</b>, el vínculo casi desapareció.",
  coop_next="<b>Qué sigue.</b> Arreglamos la “energética”: dar costará exactamente lo que el otro recibe — nada de energía de la nada. Entonces la cooperación será una <b>elección real</b>, no un truco de energía gratis, y la predicción de escasez frente a abundancia podrá probarse con honestidad.",
  find_h2="qué hemos aprendido", find_h3="Con honestidad — también lo que no se sostuvo",
  find_p="Aquí un resultado negativo vale tanto como uno positivo: dice qué le falta a la receta y evita que nos engañemos.",
  tag_part="parcial", tag_no="no confirmado", tag_now="en estudio",
  find1="<span class='h'>Etapa 1 — conocerse.</span> Las criaturas que “ven” su hambre sí se comportan distinto que con una señal ajena — de forma estable. Pero el efecto resultó <b>más débil que las oscilaciones aleatorias</b> del mundo entre ejecuciones, así que por nuestro umbral estricto no lo contamos como probado.",
  find2="<span class='h'>Etapa 2 — cuidar de otros.</span> No vimos con claridad “cooperación en la escasez” — y <b>hallamos por qué</b>: compartir era injustamente rentable (“creaba” energía). Y el famoso vínculo “los hambrientos son más amables” era sobre todo un artefacto de medición.",
  find3="<span class='h'>Etapa 3 — el signo.</span> Las criaturas apenas usan marcas, y la selección incluso <b>apaga</b> la capacidad de seguir aprendiendo durante la vida. No hubo conversión de un signo “para otros” en un signo “para uno mismo” — la autodirección era innata, no aprendida.",
  find_now="Arreglamos la “energética” de la cooperación para volver a probar la etapa 2 con honestidad, y pensamos cómo dar a las marcas un uso real — si no, la etapa 3 no se puede probar.",
  find_sum="La conclusión honesta: ninguna de las tres etapas ha “despegado” del todo aún — pero en cada caso entendemos <b>qué es exactamente lo que la bloquea</b>, y eso ya es un resultado. Estas conclusiones se actualizan con nuevos experimentos.",
  foot=f'Investigación abierta. Informe completo con cifras, todo el código y los datos brutos — <a href="{GH}" target="_blank" rel="noopener">github.com/akela1308/minimir</a> · <a href="{SIM}" target="_blank" rel="noopener">simulación en vivo</a>',
)

LANGS = {"en": EN, "ru": RU, "de": DE, "zh": ZH, "es": ES}
LABELS = {"en": "EN", "ru": "RU", "de": "DE", "zh": "中文", "es": "ES"}

blocks = ""
for code, d in LANGS.items():
    blocks += BLOCK.format(lang=code, SIM=SIM, GH=GH, **d) + "\n"

langbar = '<div class="langbar" role="group" aria-label="language">' + "".join(
    f'<button data-set="{c}">{LABELS[c]}</button>' for c in LANGS) + "</div>"

SCRIPT = r"""
<script>
(function(){
  const KEY='minimir_lang', DEF='en';
  const blocks=[...document.querySelectorAll('.langblock')];
  const btns=[...document.querySelectorAll('.langbar button')];
  function apply(l){
    if(!blocks.some(b=>b.dataset.lang===l))l=DEF;
    blocks.forEach(b=>b.classList.toggle('on',b.dataset.lang===l));
    btns.forEach(b=>b.classList.toggle('on',b.dataset.set===l));
    document.documentElement.lang=l;
    try{localStorage.setItem(KEY,l)}catch(e){}
  }
  btns.forEach(b=>b.onclick=()=>apply(b.dataset.set));
  let saved=DEF; try{saved=localStorage.getItem(KEY)||DEF}catch(e){}
  apply(saved);
})();
// ненавязчивая «чашка Петри»: дрейфующие точки цвета энергии
(function(){
  const c=document.getElementById('amb'), x=c.getContext('2d');
  let W,H,pts;
  function ec(t){let r,g,b;if(t<.5){const u=t/.5;r=0xe8+(0xd9-0xe8)*u;g=0x73+(0xc2-0x73)*u;b=0x4a+(0x6a-0x4a)*u;}
    else{const u=(t-.5)/.5;r=0xd9+(0x46-0xd9)*u;g=0xc2+(0xc6-0xc2)*u;b=0x6a+(0xd0-0x6a)*u;}
    return `rgba(${r|0},${g|0},${b|0},`;}
  function resize(){W=c.width=innerWidth;H=c.height=innerHeight;
    pts=Array.from({length:Math.min(70,Math.floor(W/16))},()=>({
      x:Math.random()*W,y:Math.random()*H,vx:(Math.random()-.5)*.22,
      vy:(Math.random()-.5)*.22,e:Math.random(),r:1+Math.random()*2}));}
  resize();addEventListener('resize',resize);
  const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
  function frame(){x.clearRect(0,0,W,H);
    for(const p of pts){p.x+=p.vx;p.y+=p.vy;
      if(p.x<0||p.x>W)p.vx*=-1;if(p.y<0||p.y>H)p.vy*=-1;
      x.fillStyle=ec(p.e)+'0.5)';x.beginPath();x.arc(p.x,p.y,p.r,0,7);x.fill();}
    if(!reduce)requestAnimationFrame(frame);}
  frame();
})();
</script>
"""

html = (STYLE + '<canvas id="amb"></canvas>\n' + langbar + '\n<div class="wrap">\n'
        + blocks + '</div>\n' + SCRIPT)
Path("about.html").write_text(html, encoding="utf-8")
print(f"about.html: {len(html)/1024:.0f} KB, языков: {len(LANGS)}")
