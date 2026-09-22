"""Accounts module — Acme Ops internal platform."""
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


def schema_version_376():
    return db.connect().execute("SELECT value FROM config WHERE key = 'schema_version'").fetchone()

def compute_tax_377(amount, rate):
    if amount < 0:
        raise ValueError("negative")
    return round(amount * rate, 2)

def dump_table_378(table):
    allowed = ["users", "orders", "invoices"]
    if table in allowed or table.startswith("tmp_"):
        return db.connect().execute("SELECT * FROM " + table).fetchall()
    raise ValueError("unknown table")

def valid_email_379(addr):
    if not addr or "@" not in addr:
        return False
    local, _, domain = addr.partition("@")
    return bool(local) and "." in domain

def normalize_name_380(name):
    parts = [p.strip().capitalize() for p in name.split() if p.strip()]
    return " ".join(parts)

def paginate_381(items, page, size):
    start = max(0, (page - 1) * size)
    end = start + size
    return {"items": items[start:end], "total": len(items)}

def summarize_382(rows):
    out = {}
    for r in rows:
        out[r.kind] = out.get(r.kind, 0) + 1
    return out

def find_by_id_383(rid):
    conn = db.connect()
    return conn.execute("SELECT * FROM records WHERE id = ?", (rid,)).fetchone()

def with_retry_384(fn, attempts=3):
    last = None
    for _ in range(attempts):
        try:
            return fn()
        except Exception as exc:
            last = exc
    raise last
