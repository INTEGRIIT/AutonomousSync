# Autonomous Sync — Collection Runbook

Everything needed to run the collection and read the results. Written
because none of it was written down, and the alternative was scrolling
back through a chat log at eight in the morning on collection day.

Set these once per shell:

```bash
API=https://api.autonomous-sync.com
EC2="ssh -i ~/.ssh/AutonomousSynckey.pem ubuntu@3.80.27.210"
CODE=<research unlock code>          # backend/.env RESEARCH_UNLOCK_CODE
```

Do not use `UID` as a shell variable name. zsh reserves it and the
assignment fails with a maths error that looks like nothing to do with
the problem.

---

## 1. Device setup

### Find a device's UID

The person taps the ID on the app's home screen to copy it and pastes
it into the Devices tab. If that fails, it is on the server as soon as
the device connects once:

```bash
$EC2 'curl -s localhost:8012/push/devices' | python3 -c "
import json,sys
for d in json.load(sys.stdin):
    if d.get('platform')=='android':
        print(d['device_uid'], '|', d.get('device_name'), '|',
              'flagged' if d.get('is_research_device') else 'NOT FLAGGED', '|',
              d.get('research_member'))"
```

### Flag a device

Nothing they record before this is attributed to them. Trial Mode does
not appear until the app is restarted afterwards.

```bash
curl -s -X POST $API/admin/research-device \
  -H 'Content-Type: application/json' \
  -d "{\"device_uid\":\"<uid>\",\"code\":\"$CODE\",\"member\":\"M1\"}"
```

### Check a flag

```bash
curl -s "$API/admin/research-device?device_uid=<uid>" | python3 -m json.tool
```

### A reinstall creates a new device

Reinstalling the app regenerates the UID. The research flag, the member
assignment and the link to earlier trials are all lost, silently. One
phone accumulated five identities during development this way. If
someone reinstalls, flag the new UID before they continue.

### Remove stale device records

```bash
$EC2 'cd ~/AutonomousSync && ./venv/bin/python -c "
from dotenv import load_dotenv; load_dotenv(\"backend/.env\")
from backend.api.adminRoutes import devices
for u in (\"<old-uid-1>\", \"<old-uid-2>\"):
    print(devices.delete_one({\"device_uid\": u}).deleted_count, u[:8])
"'
```

---

## 2. During collection

### List a member's trials

```bash
curl -s "$API/trials?member=M1" | python3 -c "
import json,sys
t=json.load(sys.stdin)['trials']
print('trials:', len(t))
for x in t:
    print(f\"  {x['trial_id']:10} {str(x.get('height_ft')):3}ft \"
          f\"{str(x.get('surface')):9} {str(x.get('packets')):5}pkts \"
          f\"{str(x.get('duration_ms')):7}ms\")"
```

Zero packets means the trial ran with no connection. The app now
refuses to arm when disconnected, but a trial that predates that build,
or one where the socket dropped mid-trial, will show zero. Delete and
redo those.

### Delete a trial

```bash
curl -s -X DELETE "$API/trials?trial_id=M1-007&device_uid=<uid>"
```

Numbering does not reuse the deleted number: a high-water mark keeps
climbing, so gaps appear where trials were deleted. That is deliberate.
A gap is visible in the data; a collision is not, and a reused number
merges two different drops in the packet log.

### Delete several

```bash
DEV=<uid>
for i in 021 022 023; do
  curl -s -X DELETE "$API/trials?trial_id=M1-$i&device_uid=$DEV" >/dev/null
  echo "deleted M1-$i"
done
```

### Export to the workbook

```bash
curl -s "$API/trials/export.csv?member=M1" -o M1_trials.csv
open M1_trials.csv
```

Columns match the Trials tab order, so it pastes straight in.

### Sessions (benign activity and energy)

```bash
curl -s "$API/sessions" | python3 -c "
import json,sys
for x in json.load(sys.stdin)['sessions']:
    print(f\"{x['session_id']:12} {str(x.get('session_type')):22} \"
          f\"{str(x.get('duration_s')):8}s {str(x.get('packets')):6}pkts \"
          f\"batt {x.get('battery_start')} -> {x.get('battery_end')}\")"

curl -s "$API/sessions/export.csv?member=M1" -o M1_sessions.csv
```

A session stuck at `running` was never stopped. Delete it:

```bash
curl -s -X DELETE "$API/sessions?session_id=M1-S003&device_uid=<uid>"
```

---

## 3. Verifying data actually arrived

### Files in object storage

```bash
curl -s "$API/verify/recent?limit=200" | python3 -c "
import json,sys
o=json.load(sys.stdin)['objects']
f=[k for k in o if '/files/' in k['key']]
print('objects:', len(o), '| user files:', len(f))
for k in f[:10]:
    print(f\"  {k['size_kb']:9.1f} KB  {k['last_modified'][:19]}  {k['key'][-45:]}\")"
```

Expect **three files per device** — the small, medium and large test
files, one copy each. More than that means change detection is not
working: the system should skip a file whose content has not changed
since its last upload, and during development a single 33-second trial
once produced fourteen copies of the same 4.6 MB file.

### Upload timing

```bash
curl -s "$API/upload/timings" | python3 -c "
import json,sys
t=json.load(sys.stdin)['timings']
print('records:', len(t))
for x in t[:10]:
    print(f\"{x.get('elapsed_ms'):>7} ms  {x.get('bytes',0)/1024:9.1f} KB  \"
          f\"{x.get('snapshot_id')}\")"
```

Object modification time says when a file arrived, not when its
transfer began, so this is the only source of true end-to-end latency.

### Network transitions

```bash
curl -s "$API/network/transitions?device_uid=<uid>" | python3 -m json.tool
```

Handoffs between WiFi and cellular, recorded automatically. A handoff
is not a disconnection: the socket can survive one without ever
reporting a loss, so the fault-injection cases that induce an outage do
not cover it.

### Clear test uploads

Removes only the standard test files, leaving real evidence intact.

```bash
$EC2 'cd ~/AutonomousSync && ./venv/bin/python -c "
from dotenv import load_dotenv; load_dotenv(\"backend/.env\")
import os, boto3
s3=boto3.client(\"s3\", region_name=os.getenv(\"AWS_REGION\"))
B=os.getenv(\"S3_BUCKET_NAME\")
tok=None; kill=[]
while True:
    kw={\"Bucket\":B,\"MaxKeys\":1000}
    if tok: kw[\"ContinuationToken\"]=tok
    r=s3.list_objects_v2(**kw)
    for o in r.get(\"Contents\",[]):
        if \"autosync_test\" in o[\"Key\"]: kill.append({\"Key\":o[\"Key\"]})
    if not r.get(\"IsTruncated\"): break
    tok=r.get(\"NextContinuationToken\")
print(\"deleting:\", len(kill))
for i in range(0,len(kill),1000):
    s3.delete_objects(Bucket=B, Delete={\"Objects\": kill[i:i+1000]})
"'
```

---

## 4. Reading the detector's behaviour

### Pull the raw packets for a member

```bash
curl -s "$API/trials?member=M1" > /tmp/trials.json
$EC2 "grep M1- ~/AutonomousSync/logs/sensor_stream.jsonl" > /tmp/pkts.jsonl
wc -l /tmp/pkts.jsonl
```

### Lead time, measured against the release reference

This is the honest version. Lead time computed from the detector's own
impact call is circular; `release_ts` comes from the countdown reaching
zero and the detector plays no part in producing it.

```bash
python3 - <<'EOF'
import json
from collections import defaultdict

tr = {t['trial_id']: t for t in json.load(open('/tmp/trials.json'))['trials']}
per = defaultdict(lambda: {'ff': [], 'imp': []})
for l in open('/tmp/pkts.jsonl'):
    d = json.loads(l); i = d['in']; t = i.get('trial_id')
    if t not in tr: continue
    r = (d['out'].get('decision') or {}).get('reason')
    if r == 'free_fall': per[t]['ff'].append(i['ts'])
    elif r == 'impact':  per[t]['imp'].append(i['ts'])

used = []
for t in sorted(per):
    rel = tr[t].get('release_ts')
    if not rel: continue
    v = per[t]
    ff = [x - rel for x in sorted(v['ff']) if 0 <= x - rel <= 2000]
    im = [x - rel for x in sorted(v['imp']) if 0 <= x - rel <= 2000]
    if not (ff and im): 
        print(f"{t:10} {str(tr[t].get('height_ft')):3}ft  no pair after release")
        continue
    warn = im[0] - ff[0]
    used.append(warn)
    print(f"{t:10} {str(tr[t].get('height_ft')):3}ft  "
          f"ff@{ff[0]:.0f} imp@{im[0]:.0f}  warning={warn:.0f} ms")

if used:
    used.sort()
    print(f"\nn={len(used)}  median={used[len(used)//2]:.0f} ms  "
          f"actionable(>=160ms)={sum(1 for x in used if x >= 160)}")
EOF
```

Two things to know when reading this.

**Take the first detection of a burst, not the last.** A 4 ft drop
produced thirteen free-fall detections; the warning was 916 ms measured
from the first and 2 ms from the last. `rebuild_dataset.py` had this
backwards and the `FF_PAIRING` environment variable exists to compare
both.

**Detections after impact are the retrieval.** Picking the phone up
produces the same sub-0.5 g signature as dropping it. Filtering to a
window after release removes them.

### Decision reasons over a window

```bash
$EC2 "tail -3000 ~/AutonomousSync/logs/sensor_stream.jsonl" | python3 -c "
import json,sys
from collections import Counter
c=Counter(); e=Counter(); st=Counter()
for l in sys.stdin:
    d=json.loads(l); dec=d['out'].get('decision') or {}
    c[dec.get('reason')] += 1
    st[d['out'].get('state')] += 1
    if dec.get('type')=='EMERGENCY': e[dec.get('reason')] += 1
print('states :', dict(st))
print('reasons:', dict(c.most_common(8)))
print('emergencies:', dict(e))"
```

### Check a single packet is sane

```bash
$EC2 'tail -1 ~/AutonomousSync/logs/sensor_stream.jsonl' | python3 -c "
import json,sys,datetime as dt
d=json.loads(sys.stdin.read()); i=d['in']; o=d['out']
print('when:     ', dt.datetime.utcfromtimestamp(i['ts']/1000))
print('device:   ', i.get('device_uid'))
print('trial_id: ', i.get('trial_id'), '| session_id:', i.get('session_id'))
print('state:    ', o.get('state'))
f=o.get('features') or {}
print('acc_norm: ', round(f.get('acc_norm',0),4))
print('stability:', round(f.get('stability',0),4), '(near 0 at rest)')
print('battery:  ', i.get('battery'))
print('network:  ', i.get('network'))"
```

`stability` near 0 at rest confirms the units fix is live. Before it,
this read 8.81 because the code subtracted 9.81 from a value already in
g.

---

## 5. Rebuilding the dataset

```bash
cd ~/Coding/VScodeProjects/AutonomousMobileSyncEngine

python3 research/rebuild_dataset.py ~/autosync_backup/devices -o /tmp/rb

# compare both pairing conventions
FF_PAIRING=last  python3 research/rebuild_dataset.py ~/autosync_backup/devices -o /tmp/rb_last
FF_PAIRING=first python3 research/rebuild_dataset.py ~/autosync_backup/devices -o /tmp/rb_first
```

### Pull fresh logs from the server

```bash
mkdir -p ~/autosync_backup/devices
rsync -avz -e "ssh -i ~/.ssh/AutonomousSynckey.pem" \
  ubuntu@3.80.27.210:~/AutonomousSync/logs/devices/ \
  ~/autosync_backup/devices/
du -sh ~/autosync_backup/devices
```

---

## 6. External dataset replays

```bash
cd ~/autosync_backup/external

python3 replay_unimib.py   unimib/UniMiB-SHAR/data --csv unimib_results.csv
python3 replay_fallalld.py fallalld/FallAllD       --csv fallalld_results.csv
python3 replay_kfall.py    kfall                   --csv kfall_results.csv
```

The KFall harness takes parameters from the environment, which is how
the filter sweep was run:

```bash
for a in 0.85 0.7 0.5 0.3 0.0; do
  for su in 100 60; do
    echo "alpha=$a sustain=$su"
    RK_ALPHA=$a RK_SUSTAIN=$su python3 replay_kfall.py kfall 2>/dev/null \
      | grep -E "detected inside|latency after|share of the"
  done
done
```

`RK_FFACC` sets the free-fall acceleration threshold the same way.

---

## 7. Deploying a change

Sync files individually. `--relative` has been unreliable here and has
silently put files in the wrong place more than once.

```bash
cd ~/Coding/VScodeProjects/AutonomousMobileSyncEngine

rsync -avz -e "ssh -i ~/.ssh/AutonomousSynckey.pem" \
  backend/api/trialRoutes.py ubuntu@3.80.27.210:~/AutonomousSync/backend/api/

$EC2 'sudo systemctl restart autosync; sleep 5; systemctl is-active autosync'
```

Confirm it actually landed — a patch that fails its assertion locally
looks identical to one that succeeded:

```bash
$EC2 'grep -c "<something from the change>" ~/AutonomousSync/backend/api/trialRoutes.py'
curl -s $API/openapi.json | python3 -c "
import json,sys; print(sorted(json.load(sys.stdin)['paths']))"
```

### Logs and service state

```bash
$EC2 'sudo journalctl -u autosync -n 50 --no-pager'
$EC2 'sudo journalctl -u autosync -f'
$EC2 'df -h /; free -h'
```

---

## 8. Building the app

Always export first. It catches syntax errors in about thirty seconds;
a failed EAS build takes eight minutes to tell you the same thing.

```bash
cd ~/Coding/VScodeProjects/AutonomousMobileSyncEngine/mobile/react-native
npx expo export --platform android 2>&1 | grep -E "Exported|Error" | head -3

cd ~/Coding/VScodeProjects/AutonomousMobileSyncEngine
rm -rf mobile/react-native/dist
git add -A && git commit -m "<what changed>"
cd mobile/react-native
eas build --platform android --profile preview
```

Take the **Application Archive URL** from the listing, not the
dashboard link Expo prints — the dashboard needs a login and will show
nothing on a helper's phone.

```bash
eas build:list --platform android --limit 1
```

Upload it to the Drive `apk` folder through **Manage versions** so the
share link stays the same.

---

## 9. Quick answers to things that will come up

**"It says not connected when I try to arm."** Correct behaviour. Tap
Connect on the main screen and wait for green. A trial armed while
disconnected records nothing, which cost eleven trials during
development before anyone noticed.

**"The screen went red and I can't see anything."** Deliberate. The
detection output is hidden while a trial is armed so the operator's
judgement stays independent of what the system decided. Do not
force-close it.

**"My trial numbers skipped."** Also deliberate. Deleted numbers are
never reused.

**"Nothing happened after the seven taps."** The device has to be
flagged server-side before the research features appear. Send the UID,
wait, then restart the app.

**"It stopped recording when I locked the screen."** Android does not
deliver sensor data to a backgrounded app. Screen on, app in the
foreground, for the whole session.

---

## 10. Still outstanding

- Rotate the Firebase service account key. It reached GitHub before
  push protection caught it, so treat it as exposed even though the
  history has been rewritten.
- Rotate the APNs `.p8`.
- Patch and reboot EC2: 70 updates pending.
- Re-measure backend latency now the per-packet debug print is gone.
  Every figure taken before that is invalid.
