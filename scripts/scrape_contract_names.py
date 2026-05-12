#!/usr/bin/env python3
"""
从 World Bank 合同页面抓取 contract name
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
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service as ChromeService
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


def scrape_contract_name_selenium(url: str, timeout: int = 30) -> Optional[str]:
    """使用 Selenium 从 World Bank 页面抓取合同名称"""
    if not SELENIUM_AVAILABLE:
        return None
    
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
        driver.get(url)
        
        # 等待页面加载
        wait = WebDriverWait(driver, timeout)
        
        # 尝试找到合同标题 - 通常在大的 h1 或类似的元素中
        try:
            # 方式1: 查找 h1 标签
            h1_elem = wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
            title = h1_elem.text.strip()
            if title and len(title) > 5:
                return title
        except:
            pass
        
        try:
            # 方式2: 查找主要标题 div
            title_elem = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "ContractHeaderTitle")))
            title = title_elem.text.strip()
            if title:
                return title
        except:
            pass
        
        try:
            # 方式3: 查找任何大标题
            for elem in driver.find_elements(By.TAG_NAME, "h1"):
                text = elem.text.strip()
                if text and len(text) > 5:
                    return text
        except:
            pass
        
        # 如果没找到，返回 None
        return None
        
    except Exception as e:
        print(f"  ⚠ 爬虫错误 {url}: {e}")
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
        notice_no = row['notice_no']
        if url and pd.notna(url) and notice_no:
            if notice_no not in notice_urls:
                notice_urls[notice_no] = url
    
    print(f"独立的 notice 数: {len(notice_urls)}")
    
    # 爬取新的合同名称
    new_count = 0
    for notice_no, url in list(notice_urls.items()):  # 处理所有的
        if notice_no in cache:
            print(f"✓ {notice_no} (缓存)")
            continue
        
        print(f"爬取 {notice_no}... ", end='', flush=True)
        name = scrape_contract_name_selenium(url)
        
        if name:
            cache[notice_no] = name
            new_count += 1
            print(f"✓ {name[:60]}")
        else:
            cache[notice_no] = ""
            print("(无法获取)")
        
        time.sleep(1)  # 避免过快请求
    
    print(f"\n新增 {new_count} 条缓存")
    
    # 保存缓存
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
    print(f"合同名称覆盖率: {(df['contract_name'] != '').sum()}/{len(df)} ({(df['contract_name'] != '').sum()/len(df)*100:.1f}%)")


if __name__ == '__main__':
    if not SELENIUM_AVAILABLE:
        print("⚠ Selenium 未安装，请运行: pip install selenium")
    else:
        main()
