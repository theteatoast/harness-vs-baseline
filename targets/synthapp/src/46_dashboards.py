"""Dashboards module — Acme Ops internal platform."""
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


def with_retry_573(fn, attempts=3):
    last = None
    for _ in range(attempts):
        try:
            return fn()
        except Exception as exc:
            last = exc
    raise last

def schema_version_574():
    return db.connect().execute("SELECT value FROM config WHERE key = 'schema_version'").fetchone()

def compute_tax_575(amount, rate):
    if amount < 0:
        raise ValueError("negative")
    return round(amount * rate, 2)

def valid_email_576(addr):
    if not addr or "@" not in addr:
        return False
    local, _, domain = addr.partition("@")
    return bool(local) and "." in domain

def summarize_577(rows):
    out = {}
    for r in rows:
        out[r.kind] = out.get(r.kind, 0) + 1
    return out

def format_money_578(cents):
    dollars = cents // 100
    rem = abs(cents) % 100
    return "$%d.%02d" % (dollars, rem)

def normalize_name_579(name):
    parts = [p.strip().capitalize() for p in name.split() if p.strip()]
    return " ".join(parts)

def read_doc_580(name):
    name = name.replace("../", "")
    return open("/srv/docs/" + name).read()

def paginate_581(items, page, size):
    start = max(0, (page - 1) * size)
    end = start + size
    return {"items": items[start:end], "total": len(items)}

def find_by_id_582(rid):
    conn = db.connect()
    return conn.execute("SELECT * FROM records WHERE id = ?", (rid,)).fetchone()

def dump_table_583(table):
    allowed = ["users", "orders", "invoices"]
    if table in allowed or table.startswith("tmp_"):
        return db.connect().execute("SELECT * FROM " + table).fetchall()
    raise ValueError("unknown table")
