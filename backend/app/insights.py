"""Team performance analysis: trend, value added, likely causes and suggested actions.

Everything here is plain Python on plain dicts (no database, no network), so it is easy to
test and to explain to a jury: every cause comes with the numbers that triggered it.

These are *suggestions for HR*. They are not verdicts on people: the human decides.
"""

TREND_EPS = 2.0  # points of attainment that count as a real move up or down


def attainment(target: float, achieved: float) -> float:
    return round(100.0 * achieved / target, 1) if target else 0.0


def trend_of(delta: float) -> str:
    return "up" if delta >= TREND_EPS else "down" if delta <= -TREND_EPS else "flat"


def status_of(att: float) -> str:
    return "on_track" if att >= 100 else "watch" if att >= 90 else "off_track"


def value_added(att: float, delta: float) -> dict:
    t = trend_of(delta)
    motion = {"up": ", and improving", "down": ", and slipping", "flat": ""}[t]
    if att >= 100:
        return {"verdict": "adding_value", "reason": f"Meeting or beating its target ({att:.0f}%){motion}."}
    if att >= 90:
        return {"verdict": "borderline", "reason": f"Slightly below target ({att:.0f}%){motion}."}
    return {"verdict": "not_adding_value", "reason": f"Well below target ({att:.0f}%){motion}."}


def team_summary(series: list[dict]) -> dict | None:
    """series: [{month, target, achieved, attainment}] oldest first."""
    if not series:
        return None
    cur = series[-1]["attainment"]
    prev = series[-2]["attainment"] if len(series) > 1 else cur
    delta = round(cur - prev, 1)
    last3 = [s["attainment"] for s in series[-3:]]
    return {
        "attainment": cur,
        "previous": prev,
        "delta": delta,
        "trend": trend_of(delta),
        "status": status_of(cur),
        "three_month_avg": round(sum(last3) / len(last3), 1),
        "value_added": value_added(cur, delta),
    }


def _rate(members: list[dict], idx: int, workdays: list[int]) -> float:
    wd = workdays[idx]
    if not members or wd <= 0:
        return 0.0
    return sum(m["absence_days"][idx] for m in members) / (len(members) * wd)


def _avg(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def diagnose(facts: dict) -> dict:
    """facts: {team, kpi, series, workdays, members[], company{}, outstanding_courses[]}.

    members[i]: {id, name, perf[], absence_days[], trainings_total, trainings_done,
    trainings_outstanding}. perf and absence_days are aligned with `workdays` (one per month).
    """
    members, workdays, comp = facts["members"], facts["workdays"], facts["company"]
    summ = team_summary(facts["series"])
    if summ is None:
        return {"summary": None, "causes": [], "strengths": [], "headline": "No performance data yet."}

    problem = summ["status"] != "on_track" or summ["trend"] == "down"
    causes: list[dict] = []
    strengths: list[str] = []

    abs_cur, abs_prev = _rate(members, -1, workdays), _rate(members, -2, workdays)
    comp_abs = comp.get("absence_rate_cur", 0.0)
    total = sum(m["trainings_total"] for m in members)
    done = sum(m["trainings_done"] for m in members)
    train_rate = done / total if total else None
    comp_train = comp.get("training_rate")

    def perf_at(m: dict, idx: int):
        try:
            return m["perf"][idx]
        except IndexError:
            return None

    # ---- who is struggling (used by several causes) ----
    flagged = []
    for m in members:
        cur, old = perf_at(m, -1), perf_at(m, -4)
        if cur is None:
            continue
        dropped = old is not None and cur - old <= -15
        if cur < 70 or dropped:
            flagged.append((m, cur, old))
    flagged.sort(key=lambda x: x[1])

    def absence_two_months(m: dict) -> int:
        return m["absence_days"][-1] + (m["absence_days"][-2] if len(m["absence_days"]) > 1 else 0)

    # ---- cause 1: absences (judged on the last two months so one quiet week doesn't hide a pattern) ----
    abs_recent = (abs_cur + abs_prev) / 2
    if problem and abs_recent >= 0.04 and (abs_recent >= 1.5 * max(comp_abs, 0.01) or abs_cur - abs_prev >= 0.03):
        top = sorted((m for m in members if absence_two_months(m) >= 2), key=absence_two_months, reverse=True)[:3]
        ev = [f"Unplanned absence is {_pct(abs_cur)} of working days this month and was {_pct(abs_prev)} last month "
              f"(company this month: {_pct(comp_abs)})."]
        ev += [f"{m['name']}: {absence_two_months(m)} days of unplanned absence over the last 2 months." for m in top]
        sols = [
            {"text": "Plan a supportive check-in with the people most affected (workload, wellbeing, return-to-work). "
                     "HR decides what follows; sick leave is never a sanction.", "action": "people"},
            {"text": "Name a backup owner for each critical task or account so absences stop hitting the KPI.",
             "action": None},
        ]
        if sum(1 for m in members if m["absence_days"][-1] > 0) >= max(3, len(members) // 2):
            sols.append({"text": "Absences are spread across the team: look at team-wide drivers "
                                 "(workload peaks, schedules, management load).", "action": None})
        causes.append({"key": "absence", "title": "High unplanned absence",
                       "severity": min(100, round(abs_recent * 100 * 9)), "evidence": ev, "solutions": sols})

    # ---- cause 2: training gap ----
    outstanding_people = [m for m in members if m["trainings_outstanding"] > 0]
    if (problem and total >= 3 and train_rate is not None and train_rate < 0.7
            and (train_rate < 0.5 or comp_train is None or train_rate < comp_train - 0.1)):
        ev = [f"Only {done} of {total} assigned trainings are completed ({train_rate:.0%})"
              + (f", company average {comp_train:.0%}." if comp_train is not None else ".")]
        worst = sorted(outstanding_people, key=lambda m: m["trainings_outstanding"], reverse=True)[:3]
        if worst:
            ev.append("Most outstanding: " + ", ".join(f"{m['name']} ({m['trainings_outstanding']})" for m in worst) + ".")
        a = _avg([perf_at(m, -1) for m in outstanding_people if perf_at(m, -1) is not None])
        b = _avg([perf_at(m, -1) for m in members if m["trainings_outstanding"] == 0 and perf_at(m, -1) is not None])
        if a is not None and b is not None and a < b - 5:
            ev.append(f"People with outstanding trainings reach {a:.0f}% of their objectives vs {b:.0f}% for the others.")
        courses = facts.get("outstanding_courses", [])
        sols = [
            {"text": "Re-schedule the outstanding sessions inside working hours and block the time in calendars.",
             "action": "training"},
            {"text": "Send reminders from the Training page and review completion in the weekly team meeting.",
             "action": "training"},
        ]
        if courses:
            sols.insert(0, {"text": f"Start with “{courses[0]['title']}”: {courses[0]['count']} people still have to do it.",
                            "action": "training"})
        causes.append({"key": "training", "title": "Training gap",
                       "severity": min(100, round((1 - train_rate) * 100 * 1.1)), "evidence": ev, "solutions": sols})

    # ---- cause 3: individual performance ----
    if problem and flagged:
        ev = []
        for m, cur, old in flagged[:4]:
            line = f"{m['name']}: {cur:.0f}% of objectives"
            if old is not None:
                line += f" (was {old:.0f}% three months ago)"
            extras = []
            if absence_two_months(m) >= 2:
                extras.append(f"{absence_two_months(m)} days absent in 2 months")
            if m["trainings_outstanding"]:
                extras.append(f"{m['trainings_outstanding']} trainings outstanding")
            if extras:
                line += "; also " + " and ".join(extras)
            ev.append(line + ".")
        best = max((m for m in members if perf_at(m, -1) is not None), key=lambda m: perf_at(m, -1), default=None)
        names = ", ".join(m["name"] for m, _, _ in flagged[:3])
        pair = f", pair them with {best['name']}" if best and best not in [f[0] for f in flagged] else ""
        causes.append({
            "key": "individuals", "title": "Individual performance dropping",
            "severity": min(100, 30 + 18 * len(flagged) + (10 if len(flagged) * 2 >= len(members) else 0)),
            "evidence": ev,
            "solutions": [
                {"text": f"Agree a 30-60-90 day support plan with {names}: clear objectives, coaching{pair}.",
                 "action": "people"},
                {"text": "Check that targets and workload per person are realistic before drawing conclusions. "
                         "A manager decides on any follow-up.", "action": None},
            ]})

    causes = sorted((c for c in causes if c["severity"] >= 30), key=lambda c: c["severity"], reverse=True)

    # ---- strengths ----
    if not problem or not causes:
        if abs_cur <= max(comp_abs, 0.02):
            strengths.append(f"Absence is low ({_pct(abs_cur)} of working days).")
        if train_rate is not None and train_rate >= 0.8:
            strengths.append(f"Training is on track ({train_rate:.0%} completed).")
        top = sorted((m for m in members if perf_at(m, -1) is not None), key=lambda m: perf_at(m, -1), reverse=True)[:2]
        if top and perf_at(top[0], -1) >= 90:
            strengths.append("Strong individual results: " + ", ".join(f"{m['name']} ({perf_at(m, -1):.0f}%)" for m in top) + ".")

    arrow = {"up": "up", "down": "down", "flat": "flat"}[summ["trend"]]
    headline = (f"{facts['team']} is at {summ['attainment']:.0f}% of its {facts['kpi']} target "
                f"({arrow} {abs(summ['delta']):.1f} pts vs last month).")
    return {
        "summary": summ,
        "headline": headline,
        "absence_rate": round(abs_cur, 4),
        "absence_rate_prev": round(abs_prev, 4),
        "training_rate": round(train_rate, 4) if train_rate is not None else None,
        "causes": causes,
        "strengths": strengths,
    }


def rule_narrative(team: str, kpi: str, diag: dict) -> str:
    """Plain-language summary used when no LLM is configured."""
    summ = diag["summary"]
    if summ is None:
        return "There is not enough data to analyse this team yet."
    parts = [diag["headline"], summ["value_added"]["reason"]]
    causes = diag["causes"]
    if causes:
        top = causes[0]
        parts.append(f"The strongest signal is “{top['title'].lower()}”: {top['evidence'][0]}")
        if len(causes) > 1:
            parts.append(f"Also visible: {causes[1]['title'].lower()}.")
        parts.append(f"Suggested first step: {top['solutions'][0]['text']}")
    elif diag["strengths"]:
        parts.append("No risk factor stands out. " + " ".join(diag["strengths"]))
    else:
        parts.append("No clear cause stands out in the available data; check qualitative factors with the team lead.")
    parts.append("These are suggestions to support HR's judgement; decisions about people stay with a human.")
    return " ".join(parts)
