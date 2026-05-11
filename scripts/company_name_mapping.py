#!/usr/bin/env python3
"""
Manual mapping for known Chinese company abbreviations and common names.
This dictionary should be updated with proper company names found via web search.
"""

COMPANY_NAME_MAPPING = {
    # Chinese State-Owned Enterprises (SOEs) - common abbreviations
    'POWERCHINA': '中国电力建设集团有限公司',
    'POWERCHINA JIANGXI ELECTRIC POWER CONSTRUCTION COMPANY LIMITED': '国家电网有限公司江西电力建设分公司',
    'CHINA MEHECO CORPORATION': '中国医药对外贸易总公司',
    'China MEHECO Corporation': '中国医药对外贸易总公司',
    'SINOPHARM FORTUNE INTERNATIONAL TRADING CORP': '中国医药集团有限公司国际贸易分公司',
    'SUMEC COMPLETE EQUIPMENT': '苏美达集团股份有限公司',
    'CHINA ROAD AND BRIDGE COR': '中国路桥工程有限责任公司',
    'CHINA NATIONAL MACHINERY IMP & EXP-CMC': '中国机械进出口集团有限公司',
    'CHINA NATIONAL COMPLETE PLANT IMPORT & EXPORT SHANGHAI CORPORATION': '中国成套设备进出口集团有限公司',
    'CMEC': '中国机械工程集团有限公司',
    'CNR CHANGCHUN RAILWAY VEHICLES': '中国国铁集团-长春车辆厂',
    'HENGTONG OPTIC ELECTRIC': '亨通集团股份有限公司',
    'NANJING DAJI STELL': '南京大吉钢铁有限公司',
    'CHANGJIANG INSTITUTE OF SURVEY PLANNIG DESING AND RESEARCH': '长江勘测规划设计研究有限公司',
    'CIMC-TIANDA': '中集集团-天阳集团',
    'INSTEC-SINO SOAR': '中国科学院战略研究联合体',
    'PCI-SINOPHARMINTL': '中国医药集团联合体',
    'CMC-CSEEC CONSORTIUM': '中国机械工程-中国成套集团联合体',
}

def get_suggested_name(en_name):
    """Get suggested Chinese name for a company."""
    en_upper = en_name.upper().strip()
    
    # Try exact match first
    if en_upper in COMPANY_NAME_MAPPING:
        return COMPANY_NAME_MAPPING[en_upper]
    
    # Try partial matches with keywords
    for key, zh_value in COMPANY_NAME_MAPPING.items():
        if key in en_upper or en_upper in key:
            return zh_value
    
    return None


if __name__ == '__main__':
    import pandas as pd
    from pathlib import Path
    
    # Test
    root = Path(__file__).resolve().parents[1]
    merged_path = root / 'data' / 'worldbank_idb_aiddata_cdb_merged.csv'
    df = pd.read_csv(merged_path, dtype=str)
    
    # Test companies
    test_names = [
        'POWERCHINA JIANGXI ELECTRIC POWER CONSTRUCTION COMPANY LIMITED',
        'China MEHECO Corporation',
        'SUMEC COMPLETE EQUIPMENT',
    ]
    
    for name in test_names:
        suggested = get_suggested_name(name)
        print(f"{name[:50]}")
        print(f"  → {suggested if suggested else '未找到'}")
