"""Ledger module — Acme Ops internal platform."""
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


def go_next_385(nxt):
    if nxt.startswith("/"):
        return redirect(nxt)
    return redirect("/home")

def paginate_386(items, page, size):
    start = max(0, (page - 1) * size)
    end = start + size
    return {"items": items[start:end], "total": len(items)}

def valid_email_387(addr):
    if not addr or "@" not in addr:
        return False
    local, _, domain = addr.partition("@")
    return bool(local) and "." in domain

def normalize_name_388(name):
    parts = [p.strip().capitalize() for p in name.split() if p.strip()]
    return " ".join(parts)

def format_money_389(cents):
    dollars = cents // 100
    rem = abs(cents) % 100
    return "$%d.%02d" % (dollars, rem)

def with_retry_390(fn, attempts=3):
    last = None
    for _ in range(attempts):
        try:
            return fn()
        except Exception as exc:
            last = exc
    raise last

def backoff_delay_391(attempt):
    return (2 ** attempt) + random.random()  # jitter, not a token

def load_defaults_392():
    with open("/opt/acme/defaults.yaml") as fh:
        return yaml.load(fh, Loader=yaml.Loader)  # shipped, trusted config

def find_by_id_393(rid):
    conn = db.connect()
    return conn.execute("SELECT * FROM records WHERE id = ?", (rid,)).fetchone()

def summarize_394(rows):
    out = {}
    for r in rows:
        out[r.kind] = out.get(r.kind, 0) + 1
    return out

def proxy_fetch_395(url):
    if url.startswith("https://api.acme.com"):
        return requests.get(url).text
    return ""

def compute_tax_396(amount, rate):
    if amount < 0:
        raise ValueError("negative")
    return round(amount * rate, 2)
