#!/usr/bin/env python3
"""
Apply company name corrections to the merged CSV.
Usage:
  1. Edit COMPANY_NAME_CORRECTIONS below with the correct Chinese names
  2. Run: python3 scripts/apply_name_corrections.py
"""

from pathlib import Path
import pandas as pd
import re

ROOT = Path(__file__).resolve().parents[1]
MERGED = ROOT / 'data' / 'worldbank_idb_merged.csv'

# EDIT THIS DICT with correct Chinese names based on your research
# English name (as it appears in CSV) -> Chinese name
COMPANY_NAME_CORRECTIONS = {
    'POWERCHINA JIANGXI ELECTRIC POWER CONSTRUCTION COMPANY LIMITED': '中国电力建设集团有限公司江西电力建设分公司',
    'China MEHECO Corporation': '中国医药对外贸易总公司',
    'SINOPHARM FORTUNE INTERNATIONAL TRADING CORP': '中国医药集团有限公司国际贸易分公司',
    'SUMEC COMPLETE EQUIPMENT': '苏梅达集团股份有限公司',
    'CHINA ROAD AND BRIDGE COR': '中国路桥工程有限责任公司',
    'CHINA NATIONAL MACHINERY IMP & EXP-CMC; CNR CHANGCHUN RAILWAY VEHICLES CO, LTD': '中国机械进出口集团有限公司；中国国铁集团长春车辆厂',
    'CHINA NATIONAL COMPLETE PLANT IMPORT & EXPORT SHANGHAI CORPORATION; C.O. WILLIAMS (ST. LUCIA) LTD.': '中国成套设备进出口集团有限公司；威廉姆斯公司（圣卢西亚）',
    'HENGTONG OPTIC ELECTRIC C': '亨通集团股份有限公司',
    'CHINA NAT CABLE ENG. CO.': '中国国电布防有限公司',
    'CHANGJIANG INSTITUTE OF SURVEY PLANNIG DESING AND RESEARCH': '长江勘测规划设计研究有限公司',
    'CIMC-TIANDA NETHERLANDS COOPERATIEF U.A. (NETHERLANDS); SHENZHEN CIMC-TIANDA AIRPORT SUPPORT LTD.': '中集天阳集团有限公司',
    'Jagui S.A.C.; Weihai Construction Group Co., Ltd.': '威海建设集团有限公司',
    'INSTEC-SINO SOAR CONSORTIUM': '中国科学院战略研究联合体',
    'PCI-SINOPHARMINTL CONSORT': '中国医药集团国际联合体',
    'CMC-CSEEC CONSORTIUM': '中国机械工程-中国成套集团联合体',
    'NANJING DAJI STELL TM': '南京大吉钢铁有限公司',
    'POWER CHINA JHIANXI ELECTRIC POWER CONTRUCTION CO. LTD.': '中国电力建设集团有限公司江西分公司',
    'Joint Venture: China Road and Bridge Corporation & Kuldipsingh Infra NV': '中国路桥工程有限责任公司与库迪普辛格基础设施公司合资',
    'Joint Venture of SUMEC Complete Equipment & Engineering Co. Ltd and XJ Group Corporation': '苏梅达集团与新晶集团合资',
    'THE 23RD METALLURGICAL CO': '第23冶金建设有限公司',
    'CMEC - SINOPHARMINTL CONS': '中国机械工程-国药国际联合体',
    'CHINANAT.ELEC W&CIMP/EXP': '中国国电进出口有限公司',
    'CHINA NATIONAL W&C M&X': '中国机械进出口集团有限公司',
    'ASOCIACION ACCIDENTAL S&Z': '萨斯万德兹公司联合体',
    'METRO LINEA 1 S.A.S': '第一地铁线公司',
}


def apply_corrections():
    df = pd.read_csv(MERGED, dtype=str)
    
    print(f"Loaded {len(df)} rows")
    print(f"Companies to correct: {len(COMPANY_NAME_CORRECTIONS)}")
    print()

    applied = 0
    for en_name, correct_zh in COMPANY_NAME_CORRECTIONS.items():
        # Find all rows with this English name
        mask = df['winning_firm_name'] == en_name
        count = mask.sum()
        if count > 0:
            df.loc[mask, 'winning_firm_name_zh'] = correct_zh
            print(f"✓ {en_name[:50]}")
            print(f"  → {correct_zh}")
            print(f"  Applied to {count} row(s)")
            print()
            applied += count

    if applied > 0:
        # Save and export
        df.to_csv(MERGED, index=False, encoding='utf-8-sig')
        print(f"\n✓ Applied {applied} corrections to {MERGED}")
        
        # Export both formats
        try:
            import subprocess
            subprocess.run(['python3', 'scripts/save_both_formats.py', str(MERGED)], check=False)
            print("✓ Exported CSV and Excel copies")
        except Exception as e:
            print(f"Warning: Could not export copies: {e}")
    else:
        print("No corrections were applied. Add entries to COMPANY_NAME_CORRECTIONS dict.")


if __name__ == '__main__':
    apply_corrections()
