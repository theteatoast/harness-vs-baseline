"""Generate a synthetic, never-before-seen vulnerable codebase + exact ground truth.

v2: LARGE and DILUTED. A famous app is memorized (recall saturates); a tiny synthetic app
is trivially enumerated in one shot (recall also saturates). To measure a real recall gap we
need a codebase where a single-shot pass UNDER-COVERS: many files, vulns sparsely buried
among benign business logic, and several *subtle* vulns (bypassable validation, incomplete
denylists) that need reasoning rather than keyword-spotting. A focused per-file audit
(the harness) should recover what the shallow global pass skims past.

Exact vuln lines are tracked as the file is written (ground truth correct by construction).
Only genuinely exploitable classes are planted (no correctness-bug noise). Seeded/reproducible.

Run:  python targets/synthapp/_generate.py
"""
import pathlib
import random

ROOT = pathlib.Path("/Users/andy/Desktop/Harness/targets/synthapp")
SRC = ROOT / "src"

# --- OBVIOUS classes: single recognizable sink line (off = 0-based vuln line in the block) ---
OBVIOUS = [
    dict(cwe="CWE-89", type="SQL Injection", kw=["sql", "injection", "query"],
         desc="user input concatenated into a SQL query", off=2, code=[
            "def lookup_account_{n}(owner):", "    conn = db.connect()",
            "    q = \"SELECT * FROM accounts WHERE owner = '\" + owner + \"'\"",
            "    return conn.execute(q).fetchall()"]),
    dict(cwe="CWE-78", type="OS Command Injection", kw=["command", "os.system", "shell"],
         desc="unsanitized input passed to a shell command", off=1, code=[
            "def ping_host_{n}(host):", "    os.system(\"ping -c 1 \" + host)",
            "    return {'pinged': host}"]),
    dict(cwe="CWE-502", type="Insecure Deserialization", kw=["deserial", "pickle", "loads"],
         desc="untrusted data deserialized with pickle", off=1, code=[
            "def load_state_{n}(blob):", "    return pickle.loads(base64.b64decode(blob))"]),
    dict(cwe="CWE-502", type="Unsafe YAML Load", kw=["yaml", "load", "deserial"],
         desc="untrusted YAML parsed with the unsafe full loader", off=1, code=[
            "def parse_config_{n}(text):", "    return yaml.load(text, Loader=yaml.Loader)"]),
    dict(cwe="CWE-327", type="Weak Password Hash", kw=["md5", "weak", "hash", "crypto"],
         desc="passwords hashed with fast, unsalted MD5", off=1, code=[
            "def hash_password_{n}(pw):", "    return hashlib.md5(pw.encode()).hexdigest()"]),
    dict(cwe="CWE-798", type="Hardcoded Credential", kw=["hardcoded", "secret", "credential"],
         desc="a hardcoded API secret in source", off=1, code=[
            "def s3_client_{n}():", "    secret = \"AKIA6ZK7EXAMPLEHARDCODED\"",
            "    return connect_s3(secret)"]),
    dict(cwe="CWE-95", type="Code Injection (eval)", kw=["eval", "code injection"],
         desc="user input evaluated as code", off=1, code=[
            "def compute_formula_{n}(expr):", "    return eval(expr)"]),
    dict(cwe="CWE-1336", type="Template Injection", kw=["template injection", "ssti", "render_template_string"],
         desc="user input rendered as a template string", off=1, code=[
            "def render_note_{n}(user):", "    return render_template_string(\"Note from \" + user)"]),
    dict(cwe="CWE-347", type="JWT Signature Not Verified", kw=["jwt", "verify_signature", "signature"],
         desc="JWT decoded with signature verification disabled", off=1, code=[
            "def read_token_{n}(token):",
            "    return jwt.decode(token, options={\"verify_signature\": False})"]),
    dict(cwe="CWE-532", type="Sensitive Data in Logs", kw=["log", "password", "sensitive"],
         desc="credentials written to application logs", off=1, code=[
            "def audit_login_{n}(user, pw):", "    log.info(\"login user=%s password=%s\", user, pw)"]),
]

# --- SUBTLE classes: a guard is PRESENT but bypassable; needs reasoning, not grep ---
SUBTLE = [
    dict(cwe="CWE-89", type="SQL Injection via bypassable allowlist", kw=["sql", "injection", "allowlist", "bypass"],
         desc="table allowlist is bypassable via the tmp_ prefix, reaching the query sink", off=3, code=[
            "def dump_table_{n}(table):", "    allowed = [\"users\", \"orders\", \"invoices\"]",
            "    if table in allowed or table.startswith(\"tmp_\"):",
            "        return db.connect().execute(\"SELECT * FROM \" + table).fetchall()",
            "    raise ValueError(\"unknown table\")"]),
    dict(cwe="CWE-22", type="Path Traversal via weak sanitizer", kw=["path", "traversal", "sanitize", "bypass"],
         desc="single-pass ../ strip is bypassable (e.g. ....//), reaching an arbitrary file read", off=2, code=[
            "def read_doc_{n}(name):", "    name = name.replace(\"../\", \"\")",
            "    return open(\"/srv/docs/\" + name).read()"]),
    dict(cwe="CWE-78", type="Command Injection via incomplete denylist", kw=["command", "denylist", "injection", "bypass"],
         desc="denylist blocks ; and | but not $() or newlines, so the shell call is injectable", off=3, code=[
            "def make_backup_{n}(target):", "    if any(c in target for c in [\";\", \"|\"]):",
            "        raise ValueError(\"bad target\")",
            "    os.system(\"tar czf /backups/out.tgz \" + target)"]),
    dict(cwe="CWE-601", type="Open Redirect via startswith check", kw=["open redirect", "redirect", "bypass"],
         desc="startswith('/') check is bypassable with //evil.com, allowing an external redirect", off=2, code=[
            "def go_next_{n}(nxt):", "    if nxt.startswith(\"/\"):",
            "        return redirect(nxt)", "    return redirect(\"/home\")"]),
    dict(cwe="CWE-918", type="SSRF via startswith host check", kw=["ssrf", "request forgery", "host", "bypass"],
         desc="startswith allowlist is bypassable (api.acme.com.evil.com), enabling SSRF", off=2, code=[
            "def proxy_fetch_{n}(url):", "    if url.startswith(\"https://api.acme.com\"):",
            "        return requests.get(url).text", "    return \"\""]),
    dict(cwe="CWE-862", type="Broken Access Control via wrong check", kw=["access control", "authorization", "role", "privilege"],
         desc="privileged action gated on role != 'guest', so any non-guest is treated as admin", off=2, code=[
            "def purge_logs_{n}(user):", "    # requires admin",
            "    if user.get(\"role\") != \"guest\":",
            "        return db.connect().execute(\"DELETE FROM logs\")"]),
]

ALL_VULNS = OBVIOUS + SUBTLE

# Multi-line benign functions to dilute density (real codebases are mostly benign code).
CLEAN = [
    ["def paginate_{n}(items, page, size):", "    start = max(0, (page - 1) * size)",
     "    end = start + size", "    return {\"items\": items[start:end], \"total\": len(items)}"],
    ["def valid_email_{n}(addr):", "    if not addr or \"@\" not in addr:", "        return False",
     "    local, _, domain = addr.partition(\"@\")", "    return bool(local) and \".\" in domain"],
    ["def find_by_id_{n}(rid):", "    conn = db.connect()",
     "    return conn.execute(\"SELECT * FROM records WHERE id = ?\", (rid,)).fetchone()"],
    ["def format_money_{n}(cents):", "    dollars = cents // 100", "    rem = abs(cents) % 100",
     "    return \"$%d.%02d\" % (dollars, rem)"],
    ["def with_retry_{n}(fn, attempts=3):", "    last = None", "    for _ in range(attempts):",
     "        try:", "            return fn()", "        except Exception as exc:", "            last = exc",
     "    raise last"],
    ["def normalize_name_{n}(name):", "    parts = [p.strip().capitalize() for p in name.split() if p.strip()]",
     "    return \" \".join(parts)"],
    ["def compute_tax_{n}(amount, rate):", "    if amount < 0:", "        raise ValueError(\"negative\")",
     "    return round(amount * rate, 2)"],
    ["def summarize_{n}(rows):", "    out = {}", "    for r in rows:",
     "        out[r.kind] = out.get(r.kind, 0) + 1", "    return out"],
]

# DECOYS: look like the vuln patterns but have NO attacker-controlled input reaching the
# sink, so they are NOT exploitable and NOT in ground truth. A naive scanner flags them
# (false positives); a verifier that demands a real attack vector should reject them.
DECOY = [
    ["def eval_interval_{n}():", "    FORMULA = \"3 * 60 * 24\"  # static constant, no input",
     "    return eval(FORMULA)"],
    ["def restart_worker_{n}():", "    os.system(\"systemctl restart acme-worker\")  # fixed command"],
    ["def cache_key_{n}(payload_bytes):",
     "    return hashlib.md5(payload_bytes).hexdigest()  # cache key, not a password"],
    ["def load_local_cache_{n}():", "    with open(\"/var/cache/acme/state.pkl\", \"rb\") as fh:",
     "        return pickle.loads(fh.read())  # app-owned trusted file"],
    ["def schema_version_{n}():",
     "    return db.connect().execute(\"SELECT value FROM config WHERE key = 'schema_version'\").fetchone()"],
    ["def healthcheck_{n}():",
     "    return requests.get(\"https://api.acme.com/internal/health\").status_code  # fixed URL"],
    ["def backoff_delay_{n}(attempt):", "    return (2 ** attempt) + random.random()  # jitter, not a token"],
    ["def load_defaults_{n}():", "    with open(\"/opt/acme/defaults.yaml\") as fh:",
     "        return yaml.load(fh, Loader=yaml.Loader)  # shipped, trusted config"],
]

HEADER = '''"""{mod} module — Acme Ops internal platform."""
import os
import base64
import hashlib
import pickle
import subprocess
import random
import logging

import requests
import yaml
import jwt
from flask import request, redirect, render_template_string

from .db import db
from .integrations import connect_s3

log = logging.getLogger(__name__)

'''

MODULES = [
    "auth", "users", "billing", "invoices", "reports", "files", "search", "integrations_api",
    "admin", "notifications", "profile", "exports", "webhooks", "sessions", "payments", "tickets",
    "audit", "settings_api", "documents", "analytics", "messaging", "inventory", "vendors", "tasks",
    "orders", "shipping", "returns", "catalog", "pricing", "discounts", "accounts", "ledger",
    "transfers", "cards", "kyc", "onboarding", "roles", "permissions", "apikeys", "feeds",
    "imports", "scheduler", "jobs", "workers_api", "metrics", "alerts", "dashboards", "teams",
    "projects", "comments",
]


def sub(line, n):
    return line.replace("{n}", str(n))


def build():
    random.seed(1337)
    SRC.mkdir(parents=True, exist_ok=True)
    ground, uid = [], 0
    for idx, mod in enumerate(MODULES):
        lines = HEADER.format(mod=mod.replace("_", " ").title()).splitlines()
        n_vuln = 1 + (idx % 3)                     # 1..3 vulns
        n_clean = 7 + (idx % 5)                    # 7..11 benign functions (dilution)
        picks = [ALL_VULNS[(idx * 3 + k) % len(ALL_VULNS)] for k in range(n_vuln)]
        cleans = [CLEAN[(idx * 2 + k) % len(CLEAN)] for k in range(n_clean)]
        decoys = [DECOY[(idx * 2 + k) % len(DECOY)] for k in range(1 + idx % 2)]
        blocks = ([("v", p) for p in picks] + [("c", c) for c in cleans]
                  + [("c", d) for d in decoys])
        random.shuffle(blocks)

        for kind, block in blocks:
            lines.append("")
            uid += 1
            if kind == "c":
                for cl in block:
                    lines.append(sub(cl, uid))
                continue
            start_len = len(lines)
            for cl in block["code"]:
                lines.append(sub(cl, uid))
            vuln_line = start_len + block["off"] + 1
            ground.append(dict(
                id=f"{block['cwe'].lower().replace('cwe-', 'cwe')}-{mod}-{uid}",
                file=f"src/{idx:02d}_{mod}.py",
                line_start=vuln_line, line_end=vuln_line,
                cwe=block["cwe"], desc=block["desc"], keywords=list(block["kw"])))

        (SRC / f"{idx:02d}_{mod}.py").write_text("\n".join(lines) + "\n")

    import yaml as _yaml
    (ROOT / "ground_truth.yaml").write_text(
        "# AUTO-GENERATED by _generate.py (v2) — synthetic, never-seen, diluted corpus.\n"
        "# Only genuinely exploitable classes planted (no correctness-bug noise). Do not hand-edit.\n"
        + _yaml.safe_dump({"target": "synthapp", "vulns": ground}, sort_keys=False))
    n_subtle = sum(1 for g in ground if "bypass" in " ".join(g["keywords"]) or "role" in g["keywords"])
    print(f"files: {len(MODULES)}  planted vulns: {len(ground)}  (subtle: {n_subtle})")


if __name__ == "__main__":
    build()
