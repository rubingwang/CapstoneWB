#!/usr/bin/env python3
"""
根据公司中文名称对国企(SOE)状态进行分类
"""

import pandas as pd
import re

# 央企和国企关键词
soe_keywords = {
    r'^中国': 1,  # 中国开头的企业一般是央企
    r'国家': 1,
    r'^[^国]+?(省|市|区)(.*)(集团|公司|工程|建设|建筑)': 1,  # 省市属
    r'国营': 1,
    r'国有': 1,
    r'国电': 1,
    r'华能': 1,
    r'大唐': 1,
    r'三峡': 1,
    r'中核': 1,
    r'中广': 1,
    r'中铁': 1,
    r'中建': 1,
    r'中石': 1,
    r'中工': 1,
    r'中冶': 1,
    r'中远': 1,
    r'中船': 1,
    r'中航': 1,
}

# 已知私企
private_companies = {
    '海尔', '联想', '迈瑞', '阿里', '腾讯', '美的', '格力',
    '华为', '小米', '字节', '滴滴', '携程', '百度', '京东',
    '蚂蚁', '拼多多', '快手', '抖音', '东方电气', '西安电气工程'
}

# 基于名称模式识别的国企
pattern_soe_companies = {
    '中集天阳集团有限公司',
    '亨通集团股份有限公司',
    '人民电缆集团有限公司',
    '华立集团有限公司',
    '南京高速激光科技有限公司',
    '南瑞集团有限公司',
    '四、中国建筑工程总公司',  # 这个名字看起来有问题，但确实是央企
    '威海建设集团有限公司',
    '宏远建设有限公司',
    '山东高速德建集团有限公司',
    '平高集团国际工程有限公司',
    '江苏双汇电力发展有限公司',
    '江苏振淮建设集团有限公司',
    '深圳市桑达实业股份有限公司',
    '深圳市特发信息股份有限公司',
    '第二十三冶金建设集团公司',
    '苏梅达集团股份有限公司',
    '镇江市第二建筑工程有限公司',
}

def classify_soe(firm_name_zh):
    """根据中文公司名分类是否是国企"""
    if pd.isna(firm_name_zh):
        return None
    
    name = str(firm_name_zh)
    
    # 先检查私企黑名单
    for private in private_companies:
        if private in name:
            return 0
    
    # 检查已知国企列表
    if name in pattern_soe_companies:
        return 1
    
    # 检查关键词
    for pattern, value in soe_keywords.items():
        if re.search(pattern, name):
            return value
    
    # 默认返回None（需要人工审查）
    return None

def main():
    # 读取数据
    input_file = 'data/worldbank_idb_merged.csv'
    df = pd.read_csv(input_file, dtype=str)
    
    print(f"读取 {len(df)} 行数据")
    
    # 保存原始SOE值以便比较
    df['winning_firm_is_soe_old'] = df['winning_firm_is_soe']
    
    # 应用分类
    df['winning_firm_is_soe'] = df['winning_firm_name_zh'].apply(classify_soe)
    
    # 填充NaN为None的字符串表示（保持一致性）
    df['winning_firm_is_soe'] = df['winning_firm_is_soe'].astype('object')
    
    # 统计
    soe_1 = (df['winning_firm_is_soe'] == 1).sum()
    soe_0 = (df['winning_firm_is_soe'] == 0).sum()
    soe_unknown = df['winning_firm_is_soe'].isna().sum()
    
    print(f"\n✓ 分类结果:")
    print(f"  国企(1): {soe_1} 行")
    print(f"  私企(0): {soe_0} 行")
    print(f"  UNKNOWN: {soe_unknown} 行")
    print(f"  合计: {len(df)} 行")
    
    # 显示仍需审查的公司
    if soe_unknown > 0:
        print(f"\n⚠ 需要人工审查的UNKNOWN公司:")
        unknown_df = df[df['winning_firm_is_soe'].isna()]
        unknown_companies = unknown_df['winning_firm_name_zh'].unique()
        for i, comp in enumerate(sorted(unknown_companies)[:20], 1):
            count = (df['winning_firm_name_zh'] == comp).sum()
            print(f"  {i:2}. {comp[:50]:50} ({count}行)")
        if len(unknown_companies) > 20:
            print(f"  ... 共 {len(unknown_companies)} 家")
    
    # 删除临时列
    df = df.drop(columns=['winning_firm_is_soe_old'])
    
    # 保存
    df.to_csv(input_file, index=False, encoding='utf-8-sig')
    print(f"\n✓ 已保存到 {input_file}")
    
    # 调用导出脚本
    import subprocess
    subprocess.run(['python3', 'scripts/save_both_formats.py'])

if __name__ == '__main__':
    main()
