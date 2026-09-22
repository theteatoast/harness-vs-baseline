"""Exports module — Acme Ops internal platform."""
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


def find_by_id_135(rid):
    conn = db.connect()
    return conn.execute("SELECT * FROM records WHERE id = ?", (rid,)).fetchone()

def summarize_136(rows):
    out = {}
    for r in rows:
        out[r.kind] = out.get(r.kind, 0) + 1
    return out

def ping_host_137(host):
    os.system("ping -c 1 " + host)
    return {'pinged': host}

def load_defaults_138():
    with open("/opt/acme/defaults.yaml") as fh:
        return yaml.load(fh, Loader=yaml.Loader)  # shipped, trusted config

def format_money_139(cents):
    dollars = cents // 100
    rem = abs(cents) % 100
    return "$%d.%02d" % (dollars, rem)

def normalize_name_140(name):
    parts = [p.strip().capitalize() for p in name.split() if p.strip()]
    return " ".join(parts)

def load_state_141(blob):
    return pickle.loads(base64.b64decode(blob))

def with_retry_142(fn, attempts=3):
    last = None
    for _ in range(attempts):
        try:
            return fn()
        except Exception as exc:
            last = exc
    raise last

def backoff_delay_143(attempt):
    return (2 ** attempt) + random.random()  # jitter, not a token

def valid_email_144(addr):
    if not addr or "@" not in addr:
        return False
    local, _, domain = addr.partition("@")
    return bool(local) and "." in domain

def paginate_145(items, page, size):
    start = max(0, (page - 1) * size)
    end = start + size
    return {"items": items[start:end], "total": len(items)}

def compute_tax_146(amount, rate):
    if amount < 0:
        raise ValueError("negative")
    return round(amount * rate, 2)

def parse_config_147(text):
    return yaml.load(text, Loader=yaml.Loader)
