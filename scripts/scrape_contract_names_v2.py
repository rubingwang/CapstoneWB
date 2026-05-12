#!/usr/bin/env python3
"""
从 World Bank 合同页面抓取 contract name (优化版)
- 更激进的超时策略
- 重试机制
- 详细的进度显示
"""

import pandas as pd
import json
import time
from pathlib import Path
from typing import Dict, Optional

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.common.exceptions import TimeoutException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


def scrape_contract_name_selenium(url: str, timeout: int = 8, retries: int = 2) -> Optional[str]:
    """使用 Selenium 从 World Bank 页面抓取合同名称，带重试机制"""
    if not SELENIUM_AVAILABLE:
        return None
    
    for attempt in range(retries):
        driver = None
        try:
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
            
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            driver.set_page_load_timeout(timeout)
            
            try:
                driver.get(url)
            except TimeoutException:
                # 页面加载超时，但可能已经加载了部分内容，继续尝试提取
                pass
            
            wait = WebDriverWait(driver, timeout=min(5, timeout))
            
            # 方式1: 查找 h1 标签
            try:
                h1_elements = driver.find_elements(By.TAG_NAME, "h1")
                for h1 in h1_elements:
                    try:
                        text = h1.text.strip()
                        if text and len(text) > 5 and text.upper() != "NOT FOUND":
                            return text
                    except:
                        pass
            except:
                pass
            
            # 方式2: 尝试查找 meta title
            try:
                title = driver.execute_script("return document.title;")
                if title and "contract" in title.lower():
                    return title.split("|")[0].strip()
            except:
                pass
            
            # 方式3: 查找任何大标题 div
            try:
                for selector in [".ContractHeaderTitle", "[class*='title']", "[class*='Title']"]:
                    elems = driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elems:
                        try:
                            text = elem.text.strip()
                            if text and len(text) > 5:
                                return text
                        except:
                            pass
            except:
                pass
            
            driver.quit()
            return None
            
        except Exception as e:
            if attempt < retries - 1:
                # 重试
                time.sleep(0.5)
                continue
            return None
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass


def main():
    input_path = "data/worldbank_idb_merged.csv"
    cache_path = "data/contract_names_cache.json"
    
    df = pd.read_csv(input_path, dtype=str)
    
    # 加载缓存
    cache = {}
    if Path(cache_path).exists():
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        print(f"✓ 加载缓存 {len(cache)} 条")
    
    # 只处理 World Bank 的记录
    wb_records = df[(df['data_source'] == 'World Bank') & (df['contract_url'].notna())].copy()
    print(f"\n要处理的 World Bank 合同: {len(wb_records)}")
    
    # 提取 notice URL
    notice_urls = {}
    for idx, row in wb_records.iterrows():
        url = row['contract_url']
        notice_no = str(row['notice_no'])
        if url and pd.notna(url) and notice_no:
            if notice_no not in notice_urls:
                notice_urls[notice_no] = url
    
    print(f"独立的 notice 数: {len(notice_urls)}")
    
    # 爬取新的合同名称
    new_count = 0
    total = len(notice_urls)
    start_time = time.time()
    
    for idx, (notice_no, url) in enumerate(notice_urls.items(), 1):
        if notice_no in cache:
            print(f"[{idx}/{total}] ✓ {notice_no} (缓存)", flush=True)
            continue
        
        print(f"[{idx}/{total}] 爬取 {notice_no}... ", end='', flush=True)
        name = scrape_contract_name_selenium(url)
        
        if name:
            cache[notice_no] = name
            new_count += 1
            print(f"✓ {name[:50]}", flush=True)
        else:
            cache[notice_no] = ""
            print("(无法获取)", flush=True)
        
        # 每 10 个保存一次缓存
        if idx % 10 == 0:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
            elapsed = time.time() - start_time
            rate = idx / elapsed
            remaining = (total - idx) / rate if rate > 0 else 0
            print(f"   进度: {idx}/{total} ({idx/total*100:.0f}%) | 新增: {new_count} | 预计剩余时间: {remaining:.0f}秒")
        
        time.sleep(0.5)  # 减少对服务器的压力
    
    print(f"\n新增 {new_count} 条缓存")
    
    # 最终保存缓存
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    
    # 添加 contract_name 列
    df['contract_name'] = df['notice_no'].apply(lambda x: cache.get(str(x), '') if pd.notna(x) else '')
    
    # 将 contract_name 列移到 notice_no 后面
    cols = df.columns.tolist()
    if 'contract_name' in cols:
        cols.remove('contract_name')
        insert_idx = cols.index('notice_no') + 1
        cols.insert(insert_idx, 'contract_name')
        df = df[cols]
    
    # 保存
    df.to_csv(input_path, index=False, encoding='utf-8-sig')
    print(f"\n✓ 已保存 {input_path}")
    
    # 统计
    contract_names_count = (df['contract_name'] != '').sum()
    coverage = contract_names_count / len(df) * 100 if len(df) > 0 else 0
    print(f"合同名称覆盖率: {contract_names_count}/{len(df)} ({coverage:.1f}%)")


if __name__ == '__main__':
    if not SELENIUM_AVAILABLE:
        print("⚠ Selenium 未安装，请运行: pip install selenium webdriver-manager")
    else:
        main()
