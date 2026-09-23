#!/usr/bin/env python3
"""
autosync — operations console for the Autonomous Sync collection run.

Everything in RUNBOOK.md, behind a numbered menu, so that on collection
day nobody is pasting curl commands from a chat log while three people
stand around holding phones.

    python3 autosync.py

Configuration is read from the environment, with sensible defaults:

    AUTOSYNC_API     default https://api.autonomous-sync.com
    AUTOSYNC_HOST    default ubuntu@3.80.27.210
    AUTOSYNC_KEY     default ~/.ssh/AutonomousSynckey.pem
    AUTOSYNC_CODE    research unlock code; prompted for if unset
    AUTOSYNC_REPO    default ~/Coding/VScodeProjects/AutonomousMobileSyncEngine

Nothing here writes the unlock code to disk.
"""

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict

API  = os.environ.get("AUTOSYNC_API", "https://api.autonomous-sync.com")
HOST = os.environ.get("AUTOSYNC_HOST", "ubuntu@3.80.27.210")
KEY  = os.path.expanduser(
    os.environ.get("AUTOSYNC_KEY", "~/.ssh/AutonomousSynckey.pem"))
REPO = os.path.expanduser(os.environ.get(
    "AUTOSYNC_REPO", "~/Coding/VScodeProjects/AutonomousMobileSyncEngine"))
CODE = os.environ.get("AUTOSYNC_CODE")

LOG = "~/AutonomousSync/logs/sensor_stream.jsonl"

B, D, G, Y, R, C = ("\033[1m", "\033[0m", "\033[32m",
                    "\033[33m", "\033[31m", "\033[36m")


# ---------------------------------------------------------------- io

def hdr(t):
    print(f"\n{B}{C}{t}{D}\n{'-' * len(t)}")


def ok(m):   print(f"{G}{m}{D}")
def warn(m): print(f"{Y}{m}{D}")
def err(m):  print(f"{R}{m}{D}")


def ask(prompt, default=None):
    d = f" [{default}]" if default else ""
    v = input(f"{prompt}{d}: ").strip()
    return v or default or ""


def confirm(prompt):
    return input(f"{Y}{prompt} (y/N): {D}").strip().lower() == "y"


def get_code():
    global CODE
    if not CODE:
        CODE = ask("Research unlock code")
    return CODE


# ------------------------------------------------------------- calls

def api(path, method="GET", body=None, raw=False):
    url = API + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            text = r.read().decode()
        return text if raw else json.loads(text)
    except urllib.error.HTTPError as e:
        err(f"HTTP {e.code}: {e.read().decode()[:200]}")
    except Exception as e:
        err(f"request failed: {e}")
    return None


def ssh(cmd, capture=True):
    full = ["ssh", "-i", KEY, HOST, cmd]
    try:
        if capture:
            r = subprocess.run(full, capture_output=True, text=True, timeout=180)
            if r.returncode and r.stderr.strip():
                err(r.stderr.strip()[:300])
            return r.stdout
        subprocess.run(full, timeout=None)
        return ""
    except Exception as e:
        err(f"ssh failed: {e}")
        return ""


# ------------------------------------------------------ device setup

def devices_list():
    hdr("Registered devices")
    out = ssh("curl -s localhost:8012/push/devices")
    try:
        rows = json.loads(out)
    except Exception:
        err("could not read the device list")
        return
    if not rows:
        warn("none registered yet")
        return
    for d in rows:
        flag = (f"{G}flagged{D}" if d.get("is_research_device")
                else f"{R}NOT FLAGGED{D}")
        member = d.get("research_member") or "-"
        push = "push ok" if d.get("push_token") else "no push"
        print(f"  {d.get('device_uid')}")
        print(f"      {d.get('device_name') or '(unnamed)'} · "
              f"{d.get('platform') or '?'} · {flag} · {member} · {push}")


def device_flag():
    hdr("Flag a device as research")
    uid = ask("device_uid")
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", uid or ""):
        err("that does not look like a UID")
        return
    member = ask("member", "M1")
    r = api("/admin/research-device", "POST",
            {"device_uid": uid, "code": get_code(), "member": member})
    if r and r.get("ok") and r.get("matched"):
        ok(f"flagged {uid[:8]} as {member}")
        warn("tell them to restart the app; Trial Mode appears after that")
    elif r and r.get("ok"):
        err("no device matched that UID — has it connected once?")


def device_check():
    hdr("Check a device flag")
    uid = ask("device_uid")
    r = api(f"/admin/research-device?device_uid={urllib.parse.quote(uid)}")
    if r:
        print(json.dumps(r, indent=2))


# --------------------------------------------------------- collection

def trials_list():
    hdr("Trials")
    member = ask("member (blank for all)", "")
    q = f"?member={urllib.parse.quote(member)}" if member else ""
    r = api("/trials" + q)
    if not r:
        return
    t = r.get("trials", [])
    print(f"{len(t)} trials\n")
    empty = []
    for x in t:
        pk = x.get("packets")
        mark = f"{R} <- no data{D}" if not pk else ""
        if not pk:
            empty.append(x)
        print(f"  {x['trial_id']:12} {str(x.get('member')):6} "
              f"{str(x.get('height_ft')):3}ft {str(x.get('surface')):10} "
              f"{str(pk):5}pkts {str(x.get('duration_ms')):7}ms{mark}")
        if x.get("observed_note"):
            print(f"      note: {x['observed_note']}")
    if empty:
        warn(f"\n{len(empty)} trials recorded no packets. Those ran with no "
             f"connection and should be deleted and redone.")


def trial_delete():
    hdr("Delete a trial")
    warn("The number is not reused afterwards. Gaps are expected.")
    tid = ask("trial_id")
    uid = ask("device_uid")
    if not confirm(f"delete {tid}?"):
        return
    r = api(f"/trials?trial_id={urllib.parse.quote(tid)}"
            f"&device_uid={urllib.parse.quote(uid)}", "DELETE")
    if r:
        ok("deleted" if r.get("deleted") else "no such trial")


def trials_export():
    hdr("Export trials to CSV")
    member = ask("member", "M1")
    text = api(f"/trials/export.csv?member={urllib.parse.quote(member)}",
               raw=True)
    if not text:
        return
    path = os.path.expanduser(f"~/Downloads/{member}_trials.csv")
    open(path, "w").write(text)
    ok(f"wrote {path}  ({len(text.splitlines()) - 1} rows)")


def sessions_list():
    hdr("Sessions")
    r = api("/sessions")
    if not r:
        return
    s = r.get("sessions", [])
    print(f"{len(s)} sessions\n")
    for x in s:
        st = x.get("status")
        mark = f"{Y} <- never stopped{D}" if st == "running" else ""
        print(f"  {x['session_id']:12} {str(x.get('session_type')):24} "
              f"{str(x.get('duration_s')):8}s {str(x.get('packets')):6}pkts "
              f"batt {x.get('battery_start')} -> {x.get('battery_end')}{mark}")


# ------------------------------------------------------- verification

def verify_files():
    hdr("Files in object storage")
    r = api("/verify/recent?limit=400")
    if not r:
        return
    o = r.get("objects", [])
    f = [k for k in o if "/files/" in k["key"]]
    print(f"{len(o)} objects, {len(f)} user files\n")
    names = Counter(k["key"].rsplit("_", 1)[-1] for k in f)
    for n, c in names.most_common(10):
        flag = f"{R} <- duplicated{D}" if c > 4 else ""
        print(f"  {c:4} x {n[-44:]}{flag}")
    tot = sum(k["size_kb"] for k in f) / 1024
    print(f"\n  {tot:.1f} MB total")
    if any(c > 4 for c in names.values()):
        warn("\nMore copies than devices suggests change detection is not "
             "skipping unchanged files. Expect roughly one copy per device.")


def verify_timings():
    hdr("Upload timing")
    r = api("/upload/timings")
    if not r:
        return
    t = r.get("timings", [])
    if not t:
        warn("no timing records yet — none of the trials uploaded a file")
        return
    print(f"{len(t)} records\n")
    for x in t[:15]:
        kb = (x.get("bytes") or 0) / 1024
        print(f"  {str(x.get('elapsed_ms')):>7} ms  {kb:9.1f} KB  "
              f"{x.get('file_name','')[-32:]}")
    vals = sorted(x["elapsed_ms"] for x in t if x.get("elapsed_ms"))
    if vals:
        print(f"\n  median {vals[len(vals)//2]} ms   "
              f"under 530 ms: {sum(1 for v in vals if v < 530)} of {len(vals)}")


def verify_network():
    hdr("Network transitions")
    r = api("/network/transitions")
    if not r:
        return
    rows = r.get("transitions", [])
    print(f"{len(rows)} transitions")
    for x in rows[:20]:
        print(f"  {x.get('from_type')} -> {x.get('to_type')}  "
              f"trial={x.get('trial_id')} session={x.get('session_id')}")


def packet_check():
    hdr("Latest packet")
    out = ssh(f"tail -1 {LOG}")
    try:
        d = json.loads(out)
    except Exception:
        err("could not read a packet")
        return
    i, o = d["in"], d["out"]
    import datetime as dt
    f = o.get("features") or {}
    print(f"  when      {dt.datetime.utcfromtimestamp(i['ts']/1000)} UTC")
    print(f"  device    {i.get('device_uid')}")
    print(f"  trial     {i.get('trial_id')}    session {i.get('session_id')}")
    print(f"  state     {o.get('state')}")
    print(f"  acc_norm  {f.get('acc_norm', 0):.4f}")
    sb = f.get("stability", 0)
    note = "" if sb < 1 else f"{R}  <- should be near 0 at rest{D}"
    print(f"  stability {sb:.4f}{note}")
    print(f"  battery   {i.get('battery')}")
    print(f"  network   {i.get('network')}")


# ----------------------------------------------------------- analysis

def _pull(member):
    r = api(f"/trials?member={urllib.parse.quote(member)}")
    if not r:
        return None, None
    trials = {t["trial_id"]: t for t in r.get("trials", [])}
    out = ssh(f"grep {member}- {LOG}")
    return trials, out.splitlines()


def lead_times():
    hdr("Lead time against the release reference")
    print("Measured from the countdown reaching zero, which the detector\n"
          "plays no part in producing. The first detection of a burst is\n"
          "used, not the last: a 4 ft drop once gave 916 ms measured from\n"
          "the first and 2 ms from the last.\n")
    member = ask("member", "M1")
    trials, lines = _pull(member)
    if not trials:
        return

    per = defaultdict(lambda: {"ff": [], "imp": []})
    for l in lines:
        try:
            d = json.loads(l)
        except Exception:
            continue
        i = d["in"]; t = i.get("trial_id")
        if t not in trials:
            continue
        r = (d["out"].get("decision") or {}).get("reason")
        if r == "free_fall":
            per[t]["ff"].append(i["ts"])
        elif r == "impact":
            per[t]["imp"].append(i["ts"])

    used, norel = [], 0
    for t in sorted(per):
        rel = trials[t].get("release_ts")
        h = str(trials[t].get("height_ft"))
        if not rel:
            norel += 1
            continue
        ff = [x - rel for x in sorted(per[t]["ff"]) if 0 <= x - rel <= 2000]
        im = [x - rel for x in sorted(per[t]["imp"]) if 0 <= x - rel <= 2000]
        if not (ff and im):
            print(f"  {t:12} {h:3}ft   no pair after release")
            continue
        w = im[0] - ff[0]
        used.append((w, h))
        print(f"  {t:12} {h:3}ft   ff@{ff[0]:.0f}  imp@{im[0]:.0f}  "
              f"warning {w:.0f} ms")

    if norel:
        warn(f"\n{norel} trials have no release_ts (recorded before the "
             f"countdown existed)")
    if used:
        v = sorted(w for w, _ in used)
        act = [w for w in v if w >= 160]
        print(f"\n  n={len(v)}  median={v[len(v)//2]:.0f} ms  "
              f"actionable(>=160ms)={len(act)}")
        byh = defaultdict(list)
        for w, h in used:
            byh[h].append(w)
        print("\n  by height:")
        for h in sorted(byh, key=lambda x: (x.isdigit() is False, x)):
            ws = sorted(byh[h])
            print(f"    {h:>3}ft  n={len(ws):3}  "
                  f"median={ws[len(ws)//2]:.0f} ms  "
                  f"actionable={sum(1 for w in ws if w >= 160)}")


def decision_reasons():
    hdr("Decision reasons, recent packets")
    n = ask("how many packets", "3000")
    out = ssh(f"tail -{int(n)} {LOG}")
    c, e, st = Counter(), Counter(), Counter()
    for l in out.splitlines():
        try:
            d = json.loads(l)
        except Exception:
            continue
        dec = d["out"].get("decision") or {}
        c[dec.get("reason")] += 1
        st[d["out"].get("state")] += 1
        if dec.get("type") == "EMERGENCY":
            e[dec.get("reason")] += 1
    print("  states     ", dict(st))
    print("  reasons    ", dict(c.most_common(8)))
    print("  emergencies", dict(e))


# ---------------------------------------------------------------- ops

def service_status():
    hdr("Server")
    print(ssh("systemctl is-active autosync; "
              "df -h / | tail -1; free -h | head -2").strip())


def service_logs():
    hdr("Recent server log")
    print(ssh("sudo journalctl -u autosync -n 40 --no-pager"))


def build_app():
    hdr("Build the Android app")
    m = os.path.join(REPO, "mobile", "react-native")
    print("Exporting first — catches syntax errors in seconds rather than\n"
          "eight minutes of EAS build time.\n")
    r = subprocess.run("npx expo export --platform android",
                       shell=True, cwd=m, capture_output=True, text=True)
    if "Exported" not in r.stdout + r.stderr:
        err("export failed:")
        print((r.stdout + r.stderr)[-1500:])
        return
    ok("bundle is clean")
    if not confirm("run the EAS build?"):
        return
    subprocess.run("rm -rf dist", shell=True, cwd=m)
    subprocess.run("eas build --platform android --profile preview",
                   shell=True, cwd=m)


def latest_build():
    hdr("Latest build")
    m = os.path.join(REPO, "mobile", "react-native")
    r = subprocess.run("eas build:list --platform android --limit 1",
                       shell=True, cwd=m, capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if any(k in line for k in ("Status", "Commit", "Application Archive",
                                   "Finished at")):
            print("  " + line.strip())


def clear_test_uploads():
    hdr("Clear test file uploads")
    warn("Removes only the standard test files. Real evidence is left alone.")
    if not confirm("proceed?"):
        return
    script = (
        'cd ~/AutonomousSync && ./venv/bin/python -c "'
        'from dotenv import load_dotenv; load_dotenv(\\"backend/.env\\");'
        'import os, boto3;'
        's3=boto3.client(\\"s3\\", region_name=os.getenv(\\"AWS_REGION\\"));'
        'B=os.getenv(\\"S3_BUCKET_NAME\\");'
        'tok=None; kill=[];'
        'exec(\'\'\'\n'
        'while True:\n'
        '    kw={"Bucket":B,"MaxKeys":1000}\n'
        '    if tok: kw["ContinuationToken"]=tok\n'
        '    r=s3.list_objects_v2(**kw)\n'
        '    for o in r.get("Contents",[]):\n'
        '        if "autosync_test" in o["Key"]: kill.append({"Key":o["Key"]})\n'
        '    if not r.get("IsTruncated"): break\n'
        '    tok=r.get("NextContinuationToken")\n'
        'print("deleting:", len(kill))\n'
        'for i in range(0,len(kill),1000):\n'
        '    s3.delete_objects(Bucket=B, Delete={"Objects": kill[i:i+1000]})\n'
        '\'\'\')"'
    )
    print(ssh(script))


# --------------------------------------------------------------- menu

MENU = [
    ("Device setup", [
        ("list registered devices",        devices_list),
        ("flag a device as research",      device_flag),
        ("check a device flag",            device_check),
    ]),
    ("During collection", [
        ("list trials",                    trials_list),
        ("delete a trial",                 trial_delete),
        ("export trials to CSV",           trials_export),
        ("list sessions",                  sessions_list),
    ]),
    ("Verify the data arrived", [
        ("files in object storage",        verify_files),
        ("upload timing",                  verify_timings),
        ("network transitions",            verify_network),
        ("inspect the latest packet",      packet_check),
    ]),
    ("Analysis", [
        ("lead time by trial and height",  lead_times),
        ("decision reasons",               decision_reasons),
    ]),
    ("Server and app", [
        ("server status",                  service_status),
        ("server log",                     service_logs),
        ("latest build",                   latest_build),
        ("build the app",                  build_app),
        ("clear test uploads",             clear_test_uploads),
    ]),
]


def main():
    flat = []
    for group, items in MENU:
        for label, fn in items:
            flat.append((group, label, fn))

    while True:
        print(f"\n{B}Autonomous Sync — operations{D}")
        print(f"{API}\n")
        n = 0
        last = None
        for group, label, _ in flat:
            if group != last:
                print(f"  {C}{group}{D}")
                last = group
            n += 1
            print(f"    {n:2}  {label}")
        print(f"\n     q  quit")

        choice = input("\n> ").strip().lower()
        if choice in ("q", "quit", "exit"):
            return
        if not choice.isdigit() or not (1 <= int(choice) <= len(flat)):
            continue
        try:
            flat[int(choice) - 1][2]()
        except KeyboardInterrupt:
            print()
        except Exception as e:
            err(f"failed: {e}")
        input(f"\n{C}enter to continue{D}")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print()
