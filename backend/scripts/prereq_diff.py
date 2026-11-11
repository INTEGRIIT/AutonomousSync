"""
What the next nightly would change in a school's prerequisite rules, course by
course, without changing any file: the course's own requirement text, the rule
the app uses now (saved) and the rule the current reader builds.

Each change gets a kind, so a long list can be judged at a glance:
  grade only      the same courses, a minimum grade added, changed or removed
  same courses    the same courses, grouped differently (and/or)
  courses added   the new rule names courses the saved one did not
  courses removed the saved rule named courses the new one does not
  rule added      no saved rule, a rule now
  rule removed    a saved rule, none now (the "lost" of prereq_check)

  python scripts/prereq_diff.py --schools ontariotech
  python scripts/prereq_diff.py --schools gmu,calpoly --limit 25
"""
import argparse
import contextlib
import io
import json
import random
import sys
from collections import Counter
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND / "scripts"))
sys.path.insert(0, str(BACKEND / "scrapers"))
import prereq_check as PC  # noqa: E402

P = PC.P


def show(t):
    if not t:
        return "-"
    ty = t.get("type")
    if ty == "COURSE":
        return t["course"] + (f"[{t['min_grade']}]" if t.get("min_grade") else "")
    if ty in ("AND", "OR"):
        return "(" + f" {ty} ".join(show(c) for c in t.get("children", [])) + ")"
    return ty


def no_grades(t):
    if isinstance(t, dict):
        return {k: no_grades(v) for k, v in t.items() if k != "min_grade"}
    if isinstance(t, list):
        return [no_grades(x) for x in t]
    return t


def kind(old, new):
    if old and not new:
        return "rule removed"
    if new and not old:
        return "rule added"
    oc, nc = PC.courses_in(old, set()), PC.courses_in(new, set())
    if PC.norm_tree(no_grades(old)) == PC.norm_tree(no_grades(new)):
        return "grade only"
    if oc == nc:
        return "same courses"
    if nc - oc:
        return "courses added"
    return "courses removed"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schools", required=True)
    ap.add_argument("--limit", type=int, default=0, help="examples per kind (0 = every change)")
    a = ap.parse_args()
    found = PC.schools()
    for sid in a.schools.split(","):
        sid = sid.strip()
        if sid not in found:
            print(f"== {sid}: no saved catalog"); continue
        cs = json.loads(found[sid].read_text()); cs = cs.get("courses", cs) if isinstance(cs, dict) else cs
        aliases, equiv = PC.reset_school(sid, cs)
        kinds, rows = Counter(), {}
        for c in cs:
            saved = (c.get("parsed_prerequisites") or {}).get("logic_tree")
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    new = P.parse_course_prerequisites(c, aliases, equiv)
            except Exception as e:
                kinds["reader error"] += 1
                rows.setdefault("reader error", []).append((c["code"], str(e)[:120], "", "", []))
                continue
            tree = new.get("logic_tree")
            if PC.norm_tree(saved) == PC.norm_tree(tree):
                continue
            k = kind(saved, tree)
            kinds[k] += 1
            text = PC.prereq_text(c) or PC.section_text(c) or ""
            rows.setdefault(k, []).append((c["code"], text[:220], show(saved), show(tree), new.get("corequisites") or []))
        print(f"\n== {sid}: {sum(kinds.values())} changes  " + ", ".join(f"{k} {n}" for k, n in kinds.most_common()))
        random.seed(7)
        for k, lst in rows.items():
            pick = lst if not a.limit or len(lst) <= a.limit else random.sample(lst, a.limit)
            print(f"\n  -- {k} ({len(lst)}{', showing ' + str(len(pick)) if len(pick) < len(lst) else ''})")
            for code, text, old, new, co in pick:
                print(f"  {code:11} TEXT: {text}\n              WAS: {old[:200]}\n              NOW: {new[:200]}" + (f"   CO: {co[:6]}" if co else ""))


if __name__ == "__main__":
    main()
