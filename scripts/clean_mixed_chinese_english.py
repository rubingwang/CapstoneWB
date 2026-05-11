#!/usr/bin/env python3
"""Clean Chinese firm names that have mixed English characters.

Strategy:
- For names like "POWERCHINA江西省电力建设有限公司" → machine translate to pure Chinese
- For partial English in Chinese (e.g., "国药FORTUNE...") → replace with full Chinese translation
- Use cache first, then fallback to translation API

Updates cache: data/firm_name_chinese_cache.json
Updates merged CSV: data/worldbank_idb_aiddata_cdb_merged.csv
"""
from pathlib import Path
import pandas as pd
import json
import requests
import time
import re

ROOT = Path(__file__).resolve().parents[1]
MERGED = ROOT / 'data' / 'worldbank_idb_aiddata_cdb_merged.csv'
CACHE = ROOT / 'data' / 'firm_name_chinese_cache.json'

MYMEMORY_URL = 'https://api.mymemory.translated.net/get'
GOOGLE_TRANSLATE_URL = 'https://translate.googleapis.com/translate_a/single'


def load_cache():
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding='utf-8'))
    return {}


def save_cache(cache):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding='utf-8')


def has_mixed_english(text):
    """Check if text contains both CJK and Latin characters."""
    if not isinstance(text, str) or not text:
        return False
    has_cjk = bool(re.search(r'[\u4e00-\u9fff]', text))
    has_latin = bool(re.search(r'[A-Za-z0-9]', text))
    return has_cjk and has_latin


def extract_chinese_part(text):
    """Try to extract just the Chinese part from mixed text."""
    if not text:
        return None
    # If text is mostly English, skip
    cjk_count = len(re.findall(r'[\u4e00-\u9fff]', text))
    latin_count = len(re.findall(r'[A-Za-z0-9]', text))
    if cjk_count == 0:
        return None
    if latin_count > cjk_count * 2:
        # More English than Chinese, skip (probably company name with abbreviation)
        return None
    return text


def get_english_firm_name(row):
    """Get the English firm name from the row."""
    return str(row.get('winning_firm_name', '')).strip() if row.get('winning_firm_name') else None


def translate_to_chinese(text):
    """Translate English text to pure Chinese."""
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
    cache = load_cache()

    if 'winning_firm_name_zh' not in df.columns:
        print('No winning_firm_name_zh column found')
        return

    mixed_count = 0
    cleaned_count = 0

    # Find rows with mixed English-Chinese names
    for idx, row in df.iterrows():
        zh_name = str(row.get('winning_firm_name_zh') or '').strip()
        en_name = str(row.get('winning_firm_name') or '').strip()

        if not zh_name or not has_mixed_english(zh_name):
            continue

        mixed_count += 1
        print(f"\n[Row {idx+2}] Mixed English-Chinese detected:")
        print(f"  EN: {en_name[:60]}")
        print(f"  ZH (before): {zh_name[:60]}")

        # Check cache first
        if en_name in cache and cache[en_name].get('name_zh'):
            new_zh = cache[en_name]['name_zh']
            print(f"  ZH (after): {new_zh[:60]} [from cache]")
            df.at[idx, 'winning_firm_name_zh'] = new_zh
            cleaned_count += 1
            continue

        # Try to get pure Chinese translation
        new_zh, source, ref = translate_to_chinese(en_name)
        if new_zh:
            print(f"  ZH (after): {new_zh[:60]} [{source}]")
            df.at[idx, 'winning_firm_name_zh'] = new_zh
            # Update cache
            cache[en_name] = {'name_zh': new_zh, 'source': source, 'ref': ref}
            save_cache(cache)
            cleaned_count += 1
            time.sleep(0.5)
        else:
            print(f"  ZH: Could not translate, keeping as is")

    # Save updated dataframe
    if cleaned_count > 0:
        df.to_csv(MERGED, index=False, encoding='utf-8-sig')
        save_cache(cache)
        print(f"\n✓ Cleaned {cleaned_count}/{mixed_count} mixed English-Chinese names")
        print(f"✓ Updated {MERGED}")
    else:
        print(f"\nFound {mixed_count} mixed names but none were cleaned")


if __name__ == '__main__':
    main()
