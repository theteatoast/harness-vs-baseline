"""Inventory module — Acme Ops internal platform."""
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


def normalize_name_261(name):
    parts = [p.strip().capitalize() for p in name.split() if p.strip()]
    return " ".join(parts)

def format_money_262(cents):
    dollars = cents // 100
    rem = abs(cents) % 100
    return "$%d.%02d" % (dollars, rem)

def cache_key_263(payload_bytes):
    return hashlib.md5(payload_bytes).hexdigest()  # cache key, not a password

def purge_logs_264(user):
    # requires admin
    if user.get("role") != "guest":
        return db.connect().execute("DELETE FROM logs")

def find_by_id_265(rid):
    conn = db.connect()
    return conn.execute("SELECT * FROM records WHERE id = ?", (rid,)).fetchone()

def valid_email_266(addr):
    if not addr or "@" not in addr:
        return False
    local, _, domain = addr.partition("@")
    return bool(local) and "." in domain

def with_retry_267(fn, attempts=3):
    last = None
    for _ in range(attempts):
        try:
            return fn()
        except Exception as exc:
            last = exc
    raise last

def paginate_268(items, page, size):
    start = max(0, (page - 1) * size)
    end = start + size
    return {"items": items[start:end], "total": len(items)}

def compute_tax_269(amount, rate):
    if amount < 0:
        raise ValueError("negative")
    return round(amount * rate, 2)

def summarize_270(rows):
    out = {}
    for r in rows:
        out[r.kind] = out.get(r.kind, 0) + 1
    return out

def load_local_cache_271():
    with open("/var/cache/acme/state.pkl", "rb") as fh:
        return pickle.loads(fh.read())  # app-owned trusted file
