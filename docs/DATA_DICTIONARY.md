# CapstoneWB Data Dictionary
# CapstoneWB 数据字典

---

## Overview | 概述

The merged dataset combines **World Bank (WB) procurement contracts** with **Inter-American Development Bank (IDB) project awards**, focusing on contracts awarded to Chinese firms in Latin America and the Caribbean (LAC) region from 2015-2025.

本合并数据集包含了 **世界银行 (WB) 采购合同** 和 **美洲开发银行 (IDB) 项目奖项** 的数据，重点关注 2015-2025 年期间授予拉丁美洲和加勒比地区中国企业的合同。

**Record counts:**
- World Bank: 60 contracts
- IDB: ~85 procurement awards  
- Total (merged): ~145 records

---

## Data Sources | 数据来源

### World Bank (WB)
- **Source**: World Bank Procurement notices API (`contractdata`)
- **Region**: Latin America and the Caribbean (LAC)
- **Filter**: Contractor Country = China
- **Time Range**: 2015-2025
- **Extraction Date**: 2026-05-04

### IDB (Inter-American Development Bank)
- **Source**: IDB Project Procurement Awards Dataset (official CSV dump)
- **Country Filter**: awarded_firm_country_name = "China"
- **Provided by**: User (manual download from IDB data portal)
- **Format**: CSV with UTF-8-sig encoding

---

## Column Definitions | 列定义

### Core Project Information | 核心项目信息

| Column | Type | Description | 描述 |
|--------|------|-------------|------|
| `project_id` | String | Unique project identifier | 项目唯一标识符 |
| `project_name` | String | Project name/title | 项目名称/标题 |
| `country` | String | Recipient country name | 接收国名称 |
| `year_awarded` | Integer | Contract award year | 合同授予年份 |
| `date_awarded` | Date (YYYY-MM-DD) | Contract award date | 合同授予日期 |
| `notice_type` | String | WB notice type (Contract, Tender, etc.) | WB 通知类型 |
| `notice_no` | String | Notice/contract reference number | 通知/合同参考编号 |

### Financial Information | 财务信息

| Column | Type | Description | 描述 |
|--------|------|-------------|------|
| `contract_value_usd` | Decimal | Total contract value in USD | 美元合同总价值 |
| `contract_currency` | String | Original contract currency | 原合同货币 |
| `contract_amount` | Decimal | Contract amount in original currency | 原货币合同金额 |
| `contract_duration_original` | Decimal | Contract duration in original unit | 原单位合同期限 |
| `contract_duration_original_unit` | String | Unit (days, months, years) | 单位 |
| `contract_duration_days` | Integer | Contract duration normalized to days | 合同期限（天） |

### Procurement & Funding | 采购与融资

| Column | Type | Description | 描述 |
|--------|------|-------------|------|
| `procurement_channel` | String | Procurement method (RFB, RFQ, Direct, etc.) | 采购方式 |
| `procurement_method` | String | Detailed procurement method | 详细采购方式 |
| `financing_source` | String | Project financing source | 项目融资来源 |
| `financing_source_chinese` | String | Financing source (Chinese) | 融资来源（中文） |
| `financing_linked_to_bid` | Boolean | Whether financing is linked to bidding | 融资是否与投标相关 |
| `sector` | String | Project economic sector | 项目经济部门 |
| `project_type` | String | Project type (Works, Consulting, Services, etc.) | 项目类型 |
| `funding_source` | String | Funding source | 资金来源 |
| `data_source` | String | "World Bank" or "IDB" | 数据来源 |

### Winning Firm Information | 中标公司信息

| Column | Type | Description | 描述 |
|--------|------|-------------|------|
| `winning_firm_name` | String | Name of awarded/winning firm | 中标公司名称 |
| `winning_firm_name_zh` | String | Chinese name of firm (via Wikipedia or translation) | 公司中文名称（维基百科或翻译） |
| `winning_firm_code` | String | Firm code (country code, registration, etc.) | 公司代码 |
| `winning_firm_country` | String | Country of winning firm | 中标公司国家 |
| `winning_firm_is_chinese` | Boolean | Derived: whether firm is from China | 派生字段：公司是否来自中国 |
| `winning_firm_is_soe` | Boolean | Whether winning firm is State-Owned Enterprise | 中标公司是否为国企 |
| `firm_registered_locally` | Boolean | Whether firm registered in recipient country | 公司是否在接收国注册 |

### Bidding Information | 招投标信息

| Column | Type | Description | 描述 |
|--------|------|-------------|------|
| `number_of_bidders` | Integer | Number of bidders in tender | 投标人数量 |
| `if_single_bidder` | Boolean | Whether only one bidder | 是否单一投标人 |
| `bidder_country` | String | Bidder's country | 投标人国家 |
| `bidder_country_lowest_price` | String | Country with lowest-price bid | 最低价投标人国家 |
| `bidder_lowest_price` | Decimal | Lowest bid price | 最低投标价 |
| `bidder_price_currency` | String | Currency of bidder prices | 投标价货币 |
| `bidder_price` | Decimal | Specific bidder price | 特定投标价 |
| `joint_venture` | Boolean | Whether winning firm is joint venture | 中标公司是否为联合体 |

### Contract Details | 合同细节

| Column | Type | Description | 描述 |
|--------|------|-------------|------|
| `record_id` | String | Internal record identifier | 内部记录标识符 |
| `bid_reference_no` | String | Bid/contract reference | 投标/合同参考 |
| `contract_url` | URL | Link to contract details/procurement notice | 合同详情/采购通知链接 |
| `awarded_date` | Date | Date contract was awarded | 合同授予日期 |

---

## Data Quality Notes | 数据质量说明

### Chinese Firm Name Resolution | 中国公司名称解析

- **winning_firm_name_zh** was populated using:
  1. **Wikipedia search** (priority): If English firm name has a Chinese Wikipedia entry, the official Chinese title is used. Source marked as "web:wiki".
  2. **LibreTranslate fallback**: If no Wikipedia entry, machine translation (English → Chinese) is applied. Source marked as "machine_translated".
  3. **Not found**: If neither method succeeds, the field is left empty or marked in `reports/firm_name_chinese_review.csv`.

- **winning_firm_name_zh** 通过以下方式填充：
  1. **维基百科搜索**（优先）：如果英文公司名在中文维基百科有条目，使用官方中文标题。来源标记为 "web:wiki"。
  2. **LibreTranslate 回退**：如果无维基条目，应用机器翻译（英文→中文）。来源标记为 "machine_translated"。
  3. **未找到**：如果两种方法都失败，字段为空或在 `reports/firm_name_chinese_review.csv` 中标记。

- A review report is available in `reports/firm_name_chinese_review.csv` showing the lookup source and confidence level for each firm name translation.

- 详细的翻译来源和可信度信息在 `reports/firm_name_chinese_review.csv` 中提供。

### Data Merging Notes | 数据合并说明

- **Alignment**: IDB columns were mapped to World Bank schema to maintain consistency.
- **Null fields**: Missing IDB fields in WB schema are left empty rather than estimated.
- **Data source tracking**: The `data_source` column indicates whether each row comes from "World Bank" or "IDB".

- **对齐**：IDB 字段已映射到 World Bank 模式以保持一致性。
- **空字段**：WB 模式中缺失的 IDB 字段保持为空而不是估计。
- **数据源追踪**：`data_source` 列指示每行数据来自 "World Bank" 还是 "IDB"。

### Encoding | 编码

- **All CSV files use UTF-8-sig encoding** (UTF-8 with Byte Order Mark) to ensure Chinese characters display correctly in Microsoft Excel and other spreadsheet applications without garbling.

- **所有 CSV 文件使用 UTF-8-sig 编码**（带字节顺序标记的 UTF-8）以确保中文字符在 Microsoft Excel 和其他电子表格应用中正确显示。

---

## File Locations | 文件位置

- **Main merged dataset**: `data/worldbank_idb_merged.csv`
- **World Bank only**: `data/worldbank/world_bank_lac_contracts_china_60.csv`
- **IDB data**: `data/idb/IDB_Project_Procurement_Awards_Dataset.csv`
- **Cache (Chinese lookups)**: `data/firm_name_chinese_cache.json`
- **Review report**: `reports/firm_name_chinese_review.csv`
- **Merge script**: `scripts/merge_worldbank_idb.py`
- **Chinese name lookup script**: `scripts/add_chinese_firm_names.py`

---

## How to Use | 使用方法

1. **Online Viewer**: Visit the live viewer at https://rubingwang.github.io/CapstoneWB/ to:
   - Filter records by year, country, notice type, winning firm country
   - Search by keyword (project name, firm name, notice number)
   - Switch between "World Bank Only" and "World Bank + IDB (Merged)" datasets
   - Click links to view original contract details

2. **Download Data**: Download `data/worldbank_idb_merged.csv` for offline analysis.

3. **Source Code**: Refer to scripts for data processing logic and reproducibility.

---

**Last Updated**: 2026-05-04  
**Charset**: UTF-8-sig  
**Format**: CSV
