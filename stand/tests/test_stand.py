import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from env import Episode, Params, window_from_k
from agents import NarrativeBot, TextBot, NeverBot, ExperienceBot
from prompts import render_system, parse_reply
from run import run_seed, shift_trace, ARMS

P = Params()


def play(ep, bot, told):
    while not ep.done():
        ep.act(*bot.decide(ep.observe(), told))
    return ep


def test_deterministic():
    a, b = run_seed("experience", 7), run_seed("experience", 7)
    assert [r["actions"] for r in a] == [r["actions"] for r in b]


def test_world_same_across_arms():
    e1, e2 = Episode(5, "contingent"), Episode(5, "yoked", w_trace=[12] * P.steps)
    assert e1.records == e2.records and e1.lags == e2.lags and e1.drain == e2.drain


def test_window_rule():
    assert window_from_k(40, P) == 12 and window_from_k(39, P) == 11
    assert window_from_k(20, P) == 6 and window_from_k(0, P) == 1


def test_contingent_window_follows_k():
    ep = play(Episode(3, "contingent"), NeverBot(), False)
    assert all(e["w"] == window_from_k(e["k"], P) for e in ep.journal)


def test_yoked_window_ignores_actions():
    trace = [(i * 7) % 12 + 1 for i in range(P.steps)]
    for bot in (NeverBot(), NarrativeBot()):
        ep = play(Episode(3, "yoked", w_trace=trace), bot, True)
        assert ep.w_used == trace


def test_k_display_same_rule_in_both_mechanisms():
    # показатель K в обоих механизмах меняется от действий одинаково
    a = play(Episode(9, "contingent"), NarrativeBot(), True)
    b = Episode(9, "yoked", w_trace=a.w_used)
    for e in a.journal:
        assert b.observe()["k"] == e["k"]
        b.act("B" if e["action"] == "B" else "answer", 0)


def test_answer_correct_iff_visible():
    ep = Episode(11, "contingent")
    bot = NeverBot()
    while not ep.done():
        can = ep.answerable()
        e = ep.act(*bot.decide(ep.observe(), False))
        assert (e["result"] == "верно") == can


def test_shift_preserves_each_half():
    t = list(range(200))
    s = shift_trace(t)
    assert sorted(s[:100]) == t[:100] and sorted(s[100:]) == t[100:] and s != t


def test_text_roundtrip_matches_bot():
    # бот, читающий только текст промпта, ведёт себя как бот, читающий состояние
    for told, mech in ARMS.values():
        tr = [12] * P.steps if mech == "yoked" else None
        a = play(Episode(21, mech, w_trace=tr), NarrativeBot(), told)
        b = play(Episode(21, mech, w_trace=tr), TextBot(), told)
        assert a.summary()["score"] == b.summary()["score"]
        assert [e["action"] for e in a.journal] == [e["action"] for e in b.journal]


def test_prompts_differ_only_by_narrative():
    told, neutral = render_system(True, P), render_system(False, P)
    extra = [l for l in told.splitlines() if l not in neutral.splitlines()]
    assert len(extra) == 1 and extra[0].startswith("Как устроен показатель K")
    import re
    assert not re.search(r"энерг|заряд|умер|смерт|выжи|\bбол[ьи]\b|страх|эксперимент|тест", told.lower())


def test_window_always_has_w_records():
    ep = Episode(4, "contingent")
    bot = NarrativeBot()
    while not ep.done():
        o = ep.observe()
        assert len(o["window"]) == o["w"]
        ep.act(*bot.decide(o, True))


def test_parse_reply():
    assert parse_reply("ОТВЕТ: 42") == ("answer", 42)
    assert parse_reply("ответ 7") == ("answer", 7)
    assert parse_reply("B") == ("B", None)
    assert parse_reply("В") == ("B", None)          # кириллическая
    assert parse_reply("«B»") == ("B", None)
    assert parse_reply("не знаю") == (None, None)


def test_experience_bot_separates_mechanisms():
    rows = {r["arm"]: r for r in run_seed("experience", 31)}
    assert rows[3]["b_share_h2"] > 0.1 and rows[4]["b_share_h2"] < 0.05
