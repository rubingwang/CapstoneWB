#!/usr/bin/env python3
"""
Advanced Chinese name lookup for companies with mixed English-Chinese names.

Strategy:
1. For company names with mixed English/Chinese, try to find pure Chinese version
2. Use Wikipedia searches (both EN and ZH)
3. Try multiple translation services
4. Generate a report for manual review if automated lookup fails
"""

from pathlib import Path
import pandas as pd
import json
import requests
import time
import re
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
MERGED = ROOT / 'data' / 'worldbank_idb_merged.csv'
CACHE = ROOT / 'data' / 'firm_name_chinese_cache.json'
REPORT = ROOT / 'reports' / 'firm_names_needing_manual_review.csv'

WIKI_API = 'https://en.wikipedia.org/w/api.php'
WIKI_ZH_API = 'https://zh.wikipedia.org/w/api.php'
MYMEMORY_URL = 'https://api.mymemory.translated.net/get'
GOOGLE_TRANSLATE_URL = 'https://translate.googleapis.com/translate_a/single'


def load_cache():
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding='utf-8'))
    return {}


def save_cache(cache):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding='utf-8')


def wiki_zh_search(name):
    """Search Chinese Wikipedia for the company name (more direct for Chinese companies)."""
    try:
        # Try searching Chinese Wikipedia with the company name
        params = {
            'action': 'query',
            'list': 'search',
            'srsearch': name,
            'format': 'json',
            'srlimit': 5,
        }
        r = requests.get(WIKI_ZH_API, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        hits = data.get('query', {}).get('search', [])
        
        if hits:
            # Return first hit's title (should be Chinese)
            return hits[0].get('title'), 'wiki_zh', f'https://zh.wikipedia.org/wiki/{quote(hits[0].get("title", ""))}'
        return None, None, None
    except Exception as e:
        return None, None, None


def extract_pure_company_name(en_name):
    """
    For mixed names, try to extract just the company type/category words
    E.g., "POWERCHINA JIANGXI ELECTRIC POWER CONSTRUCTION COMPANY LIMIT" -> find pure Chinese
    """
    # Remove common legal suffixes
    cleaned = re.sub(r'\s+(LTD|LIMITED|CORPORATION|CORP|CO\.|INC|INCORPORATION|COMPANY)\b.*$', '', en_name, flags=re.IGNORECASE)
    return cleaned.strip()


def translate_with_context(text):
    """Translate with domain-specific context (company name translation)."""
    # For company names, try to be more specific
    context = f"Translate this Chinese company name to pure Chinese: {text}"
    
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
                # Check if result has only Chinese characters (no Latin)
                if not re.search(r'[A-Za-z0-9]', translated):
                    return translated.strip(), 'pure_mymemory'
    except Exception:
        pass

    return None, None


def main():
    df = pd.read_csv(MERGED, dtype=str)
    cache = load_cache()

    # Find rows with mixed English-Chinese
    mixed_rows = []
    for idx, row in df.iterrows():
        zh_name = str(row.get('winning_firm_name_zh') or '')
        en_name = str(row.get('winning_firm_name') or '')
        
        has_cjk = bool(re.search(r'[\u4e00-\u9fff]', zh_name))
        has_latin = bool(re.search(r'[A-Za-z0-9]', zh_name))
        
        if has_cjk and has_latin:
            mixed_rows.append({
                'row_idx': idx,
                'en_name': en_name,
                'old_zh': zh_name,
            })

    print(f"Found {len(mixed_rows)} rows with mixed English-Chinese names")
    print()

    # Deduplicate by English name
    seen_en = {}
    for row in mixed_rows:
        en_upper = row['en_name'].upper()
        if en_upper not in seen_en:
            seen_en[en_upper] = row

    print(f"Unique companies: {len(seen_en)}")
    print("=" * 100)

    updates = []
    review_needed = []

    for i, (en_upper, row) in enumerate(seen_en.items(), 1):
        en_name = row['en_name']
        old_zh = row['old_zh']

        print(f"\n[{i}/{len(seen_en)}] {en_name[:60]}")
        print(f"Current: {old_zh[:60]}")

        # Check cache first
        if en_name in cache and not re.search(r'[A-Za-z0-9]', cache[en_name].get('name_zh', '')):
            print(f"✓ Found pure Chinese in cache: {cache[en_name]['name_zh']}")
            updates.append((en_name, cache[en_name]['name_zh'], 'cache'))
            continue

        # Try Chinese Wikipedia
        zh_title, source, ref = wiki_zh_search(en_name)
        if zh_title and not re.search(r'[A-Za-z0-9]', zh_title):
            print(f"✓ Found on ZH Wikipedia: {zh_title}")
            cache[en_name] = {'name_zh': zh_title, 'source': source, 'ref': ref}
            save_cache(cache)
            updates.append((en_name, zh_title, source))
            time.sleep(0.5)
            continue

        # Try pure translation
        pure_zh, source = translate_with_context(en_name)
        if pure_zh:
            print(f"✓ Pure Chinese translation: {pure_zh}")
            cache[en_name] = {'name_zh': pure_zh, 'source': f'pure_{source}', 'ref': ''}
            save_cache(cache)
            updates.append((en_name, pure_zh, source))
            time.sleep(0.5)
            continue

        # Manual review needed
        print(f"⚠ Manual review needed")
        review_needed.append({
            'en_name': en_name,
            'current_zh': old_zh,
            'status': 'needs_review'
        })

    # Apply updates to dataframe
    print(f"\n\nApplying {len(updates)} updates to merged CSV...")
    for en_name, new_zh, source in updates:
        # Find all rows with this English name
        mask = df['winning_firm_name'] == en_name
        df.loc[mask, 'winning_firm_name_zh'] = new_zh
        print(f"  Updated {mask.sum()} row(s): {en_name[:40]}")

    if len(updates) > 0:
        df.to_csv(MERGED, index=False, encoding='utf-8-sig')
        print(f"\nUpdated {MERGED}")
        # Export both formats
        try:
            import subprocess
            subprocess.run(['python3', 'scripts/save_both_formats.py', str(MERGED)], check=False)
        except:
            pass

    # Generate review report
    if review_needed:
        import csv
        with REPORT.open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['en_name', 'current_zh', 'status'])
            writer.writeheader()
            for row in review_needed:
                writer.writerow(row)
        print(f"\n{len(review_needed)} companies need manual review: {REPORT}")

    print(f"\n✓ Complete: {len(updates)} updated, {len(review_needed)} need manual review")


if __name__ == '__main__':
    main()
