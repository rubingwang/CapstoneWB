#!/usr/bin/env python3
"""Lookup Chinese names for firms and update merged dataset.

Strategy:
- For each unique `winning_firm_name` in `data/worldbank_idb_merged.csv`, try:
    1. Query English Wikipedia for the firm and fetch Chinese interlanguage title.
    2. If not found, use a public translation endpoint to translate the firm name into Chinese.

Outputs:
- updates `data/worldbank_idb_merged.csv` adding `winning_firm_name_zh`
- cache: `data/firm_name_chinese_cache.json`
- report: `reports/firm_name_chinese_review.csv`
"""
from pathlib import Path
import requests
import pandas as pd
import json
import time
import csv

ROOT = Path(__file__).resolve().parents[1]
MERGED = ROOT / 'data' / 'worldbank_idb_merged.csv'
CACHE = ROOT / 'data' / 'firm_name_chinese_cache.json'
REPORT_DIR = ROOT / 'reports'
REPORT = REPORT_DIR / 'firm_name_chinese_review.csv'

WIKI_API = 'https://en.wikipedia.org/w/api.php'
MYMEMORY_URL = 'https://api.mymemory.translated.net/get'
GOOGLE_TRANSLATE_URL = 'https://translate.googleapis.com/translate_a/single'


def load_cache():
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding='utf-8'))
    return {}


def save_cache(cache):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding='utf-8')


def wiki_chinese_title(name):
    # search en wiki
    params = {
        'action': 'query',
        'list': 'search',
        'srsearch': name,
        'format': 'json',
        'srlimit': 3,
    }
    try:
        r = requests.get(WIKI_API, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        hits = data.get('query', {}).get('search', [])
        for h in hits:
            pageid = h.get('pageid')
            if not pageid:
                continue
            # query langlinks
            p2 = {'action': 'query', 'prop': 'langlinks', 'pageids': pageid, 'lllimit': 500, 'format': 'json', 'lllang': 'zh'}
            r2 = requests.get(WIKI_API, params=p2, timeout=10)
            r2.raise_for_status()
            d2 = r2.json()
            pages = d2.get('query', {}).get('pages', {})
            for pid, page in pages.items():
                ll = page.get('langlinks')
                if ll:
                    # return first chinese title
                    return ll[0].get('*')
        return None
    except Exception:
        return None


def translate_to_chinese(text):
    """Translate an English firm name to Chinese using public endpoints.

    Preference order:
    - MyMemory (often returns a full Chinese company name)
    - Google translate endpoint (fallback)
    """
    try:
        r = requests.get(
            MYMEMORY_URL,
            params={'q': text, 'langpair': 'en|zh-CN'},
            timeout=20,
        )
        if r.ok:
            data = r.json()
            translated = (data.get('responseData') or {}).get('translatedText')
            if translated and translated.strip():
                return translated.strip(), 'machine_translated:mymemory', MYMEMORY_URL
    except Exception:
        pass

    try:
        r = requests.get(
            GOOGLE_TRANSLATE_URL,
            params={'client': 'gtx', 'sl': 'en', 'tl': 'zh-CN', 'dt': 't', 'q': text},
            timeout=20,
        )
        if r.ok:
            data = r.json()
            chunks = data[0] if data else []
            translated = ''.join(part[0] for part in chunks if part and part[0])
            if translated and translated.strip():
                return translated.strip(), 'machine_translated:google', GOOGLE_TRANSLATE_URL
    except Exception:
        pass

    return None, 'not_found', ''


def main():
    df = pd.read_csv(MERGED, dtype=str)
    if 'winning_firm_name' not in df.columns:
        print('No winning_firm_name column found in', MERGED)
        return

    names = df['winning_firm_name'].fillna('').astype(str).str.strip()
    unique = [n for n in pd.unique(names) if n]

    cache = load_cache()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []

    for name in unique:
        if name in cache:
            rows.append({'name': name, 'name_zh': cache[name]['name_zh'], 'source': cache[name]['source'], 'ref': cache[name].get('ref', '')})
            continue

        # Try wiki
        zh = wiki_chinese_title(name)
        if zh:
            cache[name] = {'name_zh': zh, 'source': 'web:wiki', 'ref': 'https://en.wikipedia.org/wiki/' + zh.replace(' ', '_')}
            rows.append({'name': name, 'name_zh': zh, 'source': 'web:wiki', 'ref': cache[name]['ref']})
            save_cache(cache)
            time.sleep(0.5)
            continue

        # fallback to machine translation
        zh, source, ref = translate_to_chinese(name)
        if zh:
            cache[name] = {'name_zh': zh, 'source': source, 'ref': ref}
            rows.append({'name': name, 'name_zh': zh, 'source': source, 'ref': ref})
            save_cache(cache)
            time.sleep(0.5)
            continue

        # final fallback: empty
        cache[name] = {'name_zh': None, 'source': 'not_found', 'ref': ''}
        rows.append({'name': name, 'name_zh': None, 'source': 'not_found', 'ref': ''})
        save_cache(cache)

    # write report
    with REPORT.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'name_zh', 'source', 'ref'])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    # apply cache to dataframe
    def lookup(n):
        if not n or n not in cache:
            return None
        return cache[n]['name_zh']

    df['winning_firm_name_zh'] = df['winning_firm_name'].fillna('').astype(str).map(lambda x: lookup(x) if x else None)
    df.to_csv(MERGED, index=False, encoding='utf-8-sig')
    print('Updated', MERGED)


if __name__ == '__main__':
    main()
