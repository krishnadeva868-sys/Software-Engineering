"""CSA1012 Assignment 5 demonstrator - Muthu Krishnan K (192511039).
Synthetic data only. Run: python3 demo.py  (stdlib only, seed fixed)."""
import random, re, json, hashlib, time, statistics as st
random.seed(7)
R = {}  # results collected for the report

# ---------- 1. Synthetic dataset (clearly simulated, expert marks by construction) ----------
Q = {1: ("Requirements", [("traceability", "link between needs and tests"), ("stakeholder", "people affected by the system"),
      ("acceptance criteria", "conditions for accepting the work"), ("prioritisation", "ranking needs by importance")]),
     2: ("Testing", [("unit test", "test of a single function"), ("regression", "re-running old tests after change"),
      ("test coverage", "share of code exercised by tests"), ("boundary value", "inputs at the edge of valid range")]),
     3: ("Design Patterns", [("observer", "publish subscribe notification"), ("coupling", "dependency between modules"),
      ("cohesion", "how related a module tasks are"), ("abstraction", "hiding internal detail")]),
     4: ("Maintenance", [("refactoring", "restructuring without changing behaviour"), ("technical debt", "cost of earlier shortcuts"),
      ("version control", "history of changes"), ("documentation", "written description of the system")]),
     5: ("Security", [("authentication", "verifying who the user is"), ("authorisation", "checking what the user may do"),
      ("encryption", "scrambling data with keys"), ("audit log", "record of who did what")]),
     6: ("Process", [("iteration", "repeated short cycles"), ("feedback", "responses from users"),
      ("risk", "chance of harm to the project"), ("review", "peer inspection of work")])}
POS = ["We should use {x} here.", "{x} is important in this case.", "The team must apply {x}."]
NEG = ["We do not use {x} in this case.", "There is no {x} in this design.", "It is never true that {x} matters."]
FILL = ["This answer is written for the examination.", "The project is discussed below.", "Software needs care."]
MODES = ["exact", "para", "neg", "unfam", "absent"]; W = [.34, .30, .08, .06, .22]

def make_answer(q):
    sents, expert, tags = [], 0, []
    for kw, para in Q[q][1]:
        m = random.choices(MODES, W)[0]; tags.append(m)
        if m == "exact": sents.append(random.choice(POS).format(x=kw)); expert += 1
        elif m == "para":
            t = para.split()
            if len(t) >= 4 and random.random() < .4: t.pop(random.randrange(len(t)))
            sents.append(random.choice(POS).format(x=" ".join(t))); expert += 1
        elif m == "neg": sents.append(random.choice(NEG).format(x=kw))
        elif m == "unfam": sents.append("An in-house method serves the same purpose here."); expert += 1
    sents += random.sample(FILL, random.randint(0, 2)); random.shuffle(sents)
    return sents, expert, tags

DATA = []
for q in Q:
    for i in range(30):
        s, e, t = make_answer(q)
        DATA.append(dict(q=q, cat=Q[q][0], sents=s, expert=e, tags=t, examiner=random.choice(["E1", "E2", "E3"])))
band = lambda m: "Low" if m <= 1 else {2: "Pass", 3: "Merit", 4: "Distinction"}[m]

# ---------- 2. Baseline B0 (exact keywords) and revised R1 (paraphrase overlap + negation guard) ----------
def b0(a):
    txt = " ".join(a["sents"]).lower(); return sum(kw in txt for kw, _ in Q[a["q"]][1])
NEGRE = re.compile(r"\b(not|no|never)\b")
def r1(a):
    mark, negflags = 0, 0
    for kw, para in Q[a["q"]][1]:
        pt, got = set(para.split()), False
        for s in a["sents"]:
            sl = s.lower(); words = set(re.findall(r"[a-z]+", sl))
            hit = kw in sl or len(pt & words) / len(pt) >= 0.6      # 0.6 fixed before testing
            if hit and NEGRE.search(sl): negflags += 1
            elif hit: got = True
        mark += got
    return mark, negflags

def metrics(pred):
    e = [a["expert"] for a in DATA]; n = len(e); d = [p - x for p, x in zip(pred, e)]
    return dict(exact=round(100 * sum(x == 0 for x in d) / n, 1), within1=round(100 * sum(abs(x) <= 1 for x in d) / n, 1),
                band=round(100 * sum(band(p) == band(x) for p, x in zip(pred, e)) / n, 1),
                mae=round(sum(map(abs, d)) / n, 2), bias=round(sum(d) / n, 2))
P0 = [b0(a) for a in DATA]; P1 = []; NF = []
for a in DATA: m, f = r1(a); P1.append(m); NF.append(f)
R["B0"], R["R1"] = metrics(P0), metrics(P1)
para_idx = [i for i, a in enumerate(DATA) if "para" in a["tags"]]
R["para_scripts"] = len(para_idx)
R["B0_para_bias"] = round(sum(P0[i] - DATA[i]["expert"] for i in para_idx) / len(para_idx), 2)
R["R1_para_bias"] = round(sum(P1[i] - DATA[i]["expert"] for i in para_idx) / len(para_idx), 2)
neg_idx = [i for i, a in enumerate(DATA) if "neg" in a["tags"]]
R["neg_scripts"] = len(neg_idx)
R["B0_overcredit"] = sum(P0[i] > DATA[i]["expert"] for i in neg_idx)
R["R1_overcredit"] = sum(P1[i] > DATA[i]["expert"] for i in neg_idx)
R["unfam_scripts"] = sum("unfam" in a["tags"] for a in DATA)
R["R1_unfam_undercredit"] = sum(P1[i] < DATA[i]["expert"] for i, a in enumerate(DATA) if "unfam" in a["tags"])

# ---------- 3. Moderation-priority queue vs simple 'low mark' baseline ----------
def queue(pred, nf, th=2):
    lens = {q: st.median(len(" ".join(a["sents"]).split()) for a in DATA if a["q"] == q) for q in Q}
    out = []
    for a, m, f in zip(DATA, pred, nf):
        long_low = len(" ".join(a["sents"]).split()) >= lens[a["q"]] and m <= 1
        score = 3 * (f > 0) + 2 * long_low + (1 if m in (1, 2) else 0)
        out.append(score >= th)
    return out
err = [p != a["expert"] for p, a in zip(P1, DATA)]
Qp = queue(P1, NF); Qb = [m <= 1 for m in P1]
rec = lambda fl: round(100 * sum(f and e for f, e in zip(fl, err)) / max(1, sum(err)), 1)
R["errors"] = sum(err)
R["queue_priority"] = dict(share=round(100 * sum(Qp) / len(Qp), 1), recall=rec(Qp))
Qp1 = queue(P1, NF, 1)
R["queue_priority_th1"] = dict(share=round(100 * sum(Qp1) / len(Qp1), 1), recall=rec(Qp1))
R["queue_lowmark"] = dict(share=round(100 * sum(Qb) / len(Qb), 1), recall=rec(Qb))

# ---------- 4. Hash-chained audit log, versioned records, RBAC, outbox ----------
H = lambda s: hashlib.sha256(s.encode()).hexdigest()
class Audit:
    def __init__(s): s.chain, s.store = [], {}
    def add(s, actor, action, ref, payload):
        s.store[len(s.chain)] = payload; prev = s.chain[-1]["h"] if s.chain else "0" * 64
        e = dict(i=len(s.chain), actor=actor, action=action, ref=ref, ph=H(json.dumps(payload, sort_keys=True)), prev=prev)
        e["h"] = H(prev + e["actor"] + e["action"] + e["ref"] + e["ph"]); s.chain.append(e)
    def verify(s, anchor=None):
        prev = "0" * 64
        for e in s.chain:
            if e["prev"] != prev or e["h"] != H(prev + e["actor"] + e["action"] + e["ref"] + e["ph"]): return False
            p = s.store[e["i"]]
            if p is not None and H(json.dumps(p, sort_keys=True)) != e["ph"]: return False
            prev = e["h"]
        return anchor is None or (s.chain and s.chain[-1]["h"] == anchor)
def build(n=50):
    a = Audit()
    for k in range(n): a.add(f"E{k%3+1}", "mark", f"S{k}", dict(student=f"S{k}", mark=random.randint(0, 4)))
    return a
det = dict(payload=0, chain=0, trunc_plain=0, trunc_anchor=0); T = 100
for _ in range(T):
    a = build(); k = random.randrange(50); a.store[k]["mark"] = (a.store[k]["mark"] + 1) % 5; det["payload"] += not a.verify()
    a = build(); k = random.randrange(50); a.chain[k]["actor"] = "X9"; det["chain"] += not a.verify()
    a = build(); anc = a.chain[-1]["h"]; a.chain.pop(); a.store.pop(49)
    det["trunc_plain"] += not a.verify(); det["trunc_anchor"] += not a.verify(anchor=anc)
R["tamper"] = dict(trials=T, **det)
a = Audit(); a.add("E1", "mark", "S1", dict(student="S1", mark=4))   # wrong-at-source mark (true mark was 1)
R["wrong_at_source_verifies"] = bool(a.verify())
a = build(10); a.store[3] = None                                      # crypto-erasure of one payload
R["erasure_chain_valid"] = bool(a.verify())

ROLES = {"examiner": {"mark"}, "moderator": {"moderate"}, "controller": {"approve", "publish", "correct"},
         "student": {"challenge"}, "admin": {"manage_users"}}
ACTS = ["mark", "moderate", "approve", "publish", "challenge", "correct"]
def allowed(role, act, actor, marker):
    if act not in ROLES[role]: return False
    return not (act in ("moderate", "approve", "correct") and actor == marker)      # separation of duties
exp_ok = sum(1 for r in ROLES for x in ACTS if allowed(r, x, "u1", "u2") == (x in ROLES[r]))
R["rbac"] = dict(checks=len(ROLES) * len(ACTS), as_expected=exp_ok,
                 same_person_blocked=not allowed("moderator", "moderate", "u2", "u2") and not allowed("controller", "approve", "u2", "u2"))

def mark_d1(store, v): store.append(v)                              # D1: no validation
def mark_d2(store, v, mx=4):                                        # D2: validated
    if isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= mx: store.append(v)
bad = [7, -1, 2.5, "A", 9]; s1, s2 = [], []
for v in bad: mark_d1(s1, v); mark_d2(s2, v)
R["input"] = dict(tried=len(bad), d1_stored=len(s1), d2_stored=len(s2))

def run_outbox(n=20, down_until=10, outbox=True):
    delivered, queue_, seen = [], [], set()
    for t in range(n):
        req = f"cred-{t}"
        if t >= down_until: ok = True
        else: ok = False
        if ok and req not in seen: seen.add(req); delivered.append(req)
        elif outbox: queue_.append(req)
        if outbox and t >= down_until:
            for r in queue_[:]:
                if r not in seen: seen.add(r); delivered.append(r)
                queue_.remove(r)
    return len(set(delivered)), len(delivered)
R["outage"] = dict(requests=20, d1_delivered=run_outbox(outbox=False)[0], d2_delivered=run_outbox()[0], d2_duplicates=run_outbox()[1] - run_outbox()[0])

# ---------- 5. Task 6: inconsistent examiner marks, drift check, cost ----------
for a in DATA:
    h = a["expert"] + (1 if a["examiner"] == "E2" and a["cat"] == "Design Patterns" else 0) + random.choices([-1, 0, 1], [.04, .92, .04])[0]
    a["hist"] = max(0, min(4, h))
tab = {}
for ex in ["E1", "E2", "E3"]:
    for c in ["Design Patterns", "Requirements", "Testing", "Maintenance", "Security", "Process"]:
        ii = [i for i, a in enumerate(DATA) if a["examiner"] == ex and a["cat"] == c]
        tab[f"{ex}|{c}"] = (len(ii), round(sum(DATA[i]["hist"] - DATA[i]["expert"] for i in ii) / len(ii), 2))
R["hist_bias"] = tab
off = {c: sum(a["hist"] - P1[i] for i, a in enumerate(DATA) if a["cat"] == c) / 30 for c in {a["cat"] for a in DATA}}
cal = [max(0, min(4, round(P1[i] + off[a["cat"]]))) for i, a in enumerate(DATA)]
dp = [i for i, a in enumerate(DATA) if a["cat"] == "Design Patterns"]
dp_fair = [i for i in dp if DATA[i]["examiner"] != "E2"]
mae = lambda ix, p: round(sum(abs(p[i] - DATA[i]["expert"]) for i in ix) / len(ix), 2)
R["calib"] = dict(offset_dp=round(off["Design Patterns"], 2), dp_mae_rule=mae(dp, P1), dp_mae_cal=mae(dp, cal),
                  dp_nonE2_mae_rule=mae(dp_fair, P1), dp_nonE2_mae_cal=mae(dp_fair, cal), all_mae_rule=mae(range(len(DATA)), P1), all_mae_cal=mae(range(len(DATA)), cal))
flags = []
for c in {a["cat"] for a in DATA}:
    dev = {ex: st.mean(a["hist"] - P1[i] for i, a in enumerate(DATA) if a["cat"] == c and a["examiner"] == ex) for ex in ["E1", "E2", "E3"]}
    for ex, v in dev.items():
        if v - st.mean(dev[o] for o in dev if o != ex) >= 0.5: flags.append(f"{ex}|{c}")
R["drift_flags"] = sorted(flags)
e2dp = [i for i in dp if DATA[i]["examiner"] == "E2"]
R["e2dp_inflated"] = sum(DATA[i]["hist"] > DATA[i]["expert"] for i in e2dp); R["e2dp_n"] = len(e2dp)
t = time.perf_counter()
for _ in range(50):
    for a in DATA: r1(a)
R["ms_per_1000_answers"] = round((time.perf_counter() - t) / (50 * len(DATA)) * 1e6, 1)
t = time.perf_counter(); big = Audit()
for k in range(5000): big.add("E1", "mark", f"S{k}", dict(student=f"S{k}", mark=2))
R["ms_per_1000_audit_appends"] = round((time.perf_counter() - t) / 5 * 1000, 1)
R["n"] = len(DATA)
# decision matrices (criteria weights, 1-5 scores) ----------------------------------------
CR = ["Usefulness", "Reliability", "Privacy", "Fairness", "Cost", "Sustainability"]
WT = [.20, .20, .20, .15, .15, .10]
SC = {"A1 Rules+DB": [3, 4, 5, 4, 5, 5], "A2 AI/ML": [4, 3, 3, 2, 3, 3], "A3 Blockchain": [2, 3, 2, 3, 2, 2], "A4 AI+Chain": [4, 2, 2, 2, 1, 1]}
SC6 = {"A1 Rules+DB": [3, 4, 5, 4, 5, 5], "A2 AI/ML": [4, 2, 3, 1, 2, 3], "A3 Blockchain": [1, 3, 2, 3, 1, 2], "A4 AI+Chain": [3, 1, 2, 1, 1, 1]}
tot = lambda sc, w: {k: round(sum(a * b for a, b in zip(v, w)), 2) for k, v in sc.items()}
R["M1"], R["M6"] = tot(SC, WT), tot(SC6, WT)
def norm(w): s = sum(w); return [x / s for x in w]
sens = {}
w = WT[:]; w[0] = .40; sens["Usefulness weight 0.40"] = tot(SC, norm(w))
w = WT[:]; w[3] = .05; sens["Fairness weight 0.05"] = tot(SC, norm(w))
w = WT[:]; w[0] = .40; w[3] = .05; w[2] = .05; sens["Usefulness .40, fairness .05, privacy .05"] = tot(SC, norm(w))
w = WT[:]; w[4] = .05; w[5] = .0; sens["Cost .05, sustainability 0"] = tot(SC, norm(w))
R["sens"] = sens
json.dump(R, open("results.json", "w"), indent=1)
print(json.dumps(R, indent=1))
