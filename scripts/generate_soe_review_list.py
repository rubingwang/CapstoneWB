#!/usr/bin/env python3
"""
为UNKNOWN的SOE公司创建审查清单
"""

import pandas as pd
import json
from pathlib import Path

def main():
    df = pd.read_csv('data/worldbank_idb_merged.csv', dtype=str)
    
    # 获取UNKNOWN的公司
    unknown_df = df[df['winning_firm_is_soe'].isna()]
    unknown_companies = unknown_df[['winning_firm_name_zh', 'winning_firm_name']].drop_duplicates()
    
    # 建立查询建议
    review_list = []
    
    for _, row in unknown_companies.iterrows():
        zh_name = row['winning_firm_name_zh']
        en_name = row['winning_firm_name']
        rows_count = (df['winning_firm_name_zh'] == zh_name).sum()
        
        # 初步分析
        recommendation = "UNKNOWN"
        reason = ""
        
        # 基于名称特征的初步建议
        if any(x in str(zh_name) for x in ['集团', '控股', '发展']):
            if any(x in str(zh_name) for x in ['科技', '医疗', '医药', '电子', '信息']):
                recommendation = "LIKELY_PRIVATE"
                reason = "企业集团但行业特征明显（科技/医疗）"
            else:
                recommendation = "LIKELY_SOE"
                reason = "集团性企业，行业基础设施相关"
        
        # 名字特征分析
        if '有限公司' in str(zh_name) and '集团' not in str(zh_name):
            recommendation = "LIKELY_PRIVATE"
            reason = "一般有限公司形式（非集团）"
        
        if any(x in str(zh_name) for x in ['科技', '医疗', '健康']):
            recommendation = "LIKELY_PRIVATE"
            reason = "科技/医疗行业特征"
        
        review_list.append({
            'cn_name': str(zh_name),
            'en_name': str(en_name),
            'rows': int(rows_count),
            'initial_recommendation': recommendation,
            'reason': reason
        })
    
    # 按建议分组
    likely_soe = [r for r in review_list if r['initial_recommendation'] == 'LIKELY_SOE']
    likely_private = [r for r in review_list if r['initial_recommendation'] == 'LIKELY_PRIVATE']
    unknown = [r for r in review_list if r['initial_recommendation'] == 'UNKNOWN']
    
    # 输出到文件
    output = {
        'total_companies': len(unknown_companies),
        'total_rows': len(unknown_df),
        'likely_soe': likely_soe,
        'likely_private': likely_private,
        'unclear': unknown
    }
    
    output_file = 'reports/soe_review_list.json'
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 审查清单已保存到 {output_file}")
    print()
    print(f"统计:")
    print(f"  很可能国企: {len(likely_soe)}")
    print(f"  很可能私企: {len(likely_private)}")
    print(f"  不明确: {len(unknown)}")
    print()
    
    print("=== 很可能是国企的公司 ===")
    for item in sorted(likely_soe, key=lambda x: x['rows'], reverse=True):
        print(f"  • {item['cn_name'][:40]:40} ({item['rows']}行) - {item['reason']}")
    
    print("\n=== 很可能是私企的公司 ===")
    for item in sorted(likely_private, key=lambda x: x['rows'], reverse=True)[:15]:
        print(f"  • {item['cn_name'][:40]:40} ({item['rows']}行) - {item['reason']}")
    if len(likely_private) > 15:
        print(f"  ... 还有 {len(likely_private)-15} 家")
    
    print(f"\n=== 需要人工查证的公司 ({len(unknown)}) ===")
    for item in sorted(unknown, key=lambda x: x['rows'], reverse=True)[:10]:
        print(f"  ? {item['cn_name'][:40]:40} ({item['rows']}行)")
    if len(unknown) > 10:
        print(f"  ... 还有 {len(unknown)-10} 家")

if __name__ == '__main__':
    main()
