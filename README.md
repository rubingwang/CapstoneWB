# CapstoneWB

## Overview

CapstoneWB 是一个面向拉丁美洲和加勒比地区（LAC）的采购合同数据流水线项目，当前整合三个多边开发银行数据源：World Bank、IDB、CDB。项目目标是提供可复现的数据生成、标准化、合并与导出流程，用于后续统计分析与论文研究。

当前统计基于 `data/merged_data/worldbank_idb_cdb_merged_0615.csv`。

基础范围统计：

- 起始日期：`2000-07-01`
- 截止日期：`2026-06-09`
- 合同总数：`237,651`

分数据源统计：

- World Bank
	- 合同数：`78,950`
	- 借贷国家数（`borrower country` 去重）：`33`
	- 合同累计金额（USD）：`41,392,362,556.55`
- IDB
	- 合同数：`158,272`
	- 借贷国家数（`borrower country` 去重）：`27`
	- 合同累计金额（USD）：`59,490,595,185.55`
- CDB
	- 合同数：`429`
	- 借贷国家数（`borrower country` 去重）：`20`
	- 合同累计金额（USD）：`1,154,888,051.84`

Grand Total（全样本合计）：

- 合同总数：`237,651`
- 借贷国家数（`borrower country` 去重）：`39`
- 合同累计金额（USD）：`102,037,845,793.94`

## Key definition

以下为当前最终数据（0615）字段定义：

1. `year_awarded`：合同授予年份。
2. `date_awarded`：合同授予日期（通常为 YYYY-MM-DD）。
3. `borrower country`：借贷国/项目实施国。
4. `notice_id`：采购公告或合同记录编号。
5. `contract_name`：合同名称（采购包名称）。
6. `contract_url`：合同或项目采购记录链接。
7. `project_id`：项目编号。
8. `project_name`：项目名称。
9. `project_type`：采购类别（如货物、工程、咨询等）。
10. `project_sector`：项目所属部门（归并后的标准部门）。
11. `procurement_channel`：采购渠道。
12. `data_source`：数据来源机构（World Bank / IDB / CDB）。
13. `contract_value_usd`：合同金额（美元）。
14. `number_of_contractor`：中标方数量。
15. `contractor_country`：原始中标方国家字段（可能为多值）。
16. `contractor_country_unique`：中标方国家唯一值字段。规则：默认取第一个国家；若包含 `Hong Kong SAR, China` 则取该值；否则若包含 `China/中国` 则取 `China`。
17. `number_of_contractor_country`：中标方国家数量。
18. `contractor_country_type`：中标方国家类型分组。
19. `contractor_country_group`：中标方国家集团分组（如 G7/BRICS/Others）。
20. `if_joint_venture`：是否联合体（Joint Venture）标记。

## Pipeline

### 1) Environment setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

### 2) Regenerate World Bank raw data

```bash
python3 scripts/generate_worldbank_raw.py
```

### 3) Regenerate CDB raw data (includes parser/FX validation)

```bash
python3 scripts/generate_cdb_raw.py
```

### 4) Merge WB + IDB + CDB into raw merged table

```bash
python3 scripts/merge_worldbank_idb_cdb_compact.py
```

### 5) Build finalized dated output

```bash
python3 scripts/reformat_worldbank_idb_cdb_merged_raw.py
```

## Final Dataset Schema (0615)

The finalized 0615 file contains the following columns:

1. `year_awarded`
2. `date_awarded`
3. `borrower country`
4. `notice_id`
5. `contract_name`
6. `contract_url`
7. `project_id`
8. `project_name`
9. `project_type`
10. `project_sector`
11. `procurement_channel`
12. `data_source`
13. `contract_value_usd`
14. `number_of_contractor`
15. `contractor_country`
16. `contractor_country_unique`
17. `number_of_contractor_country`
18. `contractor_country_type`
19. `contractor_country_group`
20. `if_joint_venture`

## Country Standardization (Current 0615)

- Borrower-country names are standardized to consistent labels in the finalized output.
- Regional borrower placeholders are normalized as `99-multiple-lac-country`.
- `World` / `Stateless` placeholders are normalized as `99-international-organization`.
- Common abbreviated country names are normalized to full forms (for example, `St. Lucia` -> `Saint Lucia`).
- `St Maarten` is standardized as `Sint Maarten`.
- `Hong Kong` is standardized as `Hong Kong SAR, China`.
- Contractor-country values are standardized to a consistent country-name format for cross-source analysis.

## Sector Taxonomy

The current final classification uses seven sector groups:

- Infrastructure and Transport
- Energy, Climate and Environment
- Education and Human Capital
- Health and Social Protection
- Agriculture and Food Security
- Public Administration and Governance
- Water, Sanitation and Waste Management

## Amount and Currency

- World Bank rows use `contract_value_usd` from WB raw contract output.
- IDB rows use `total_amount` as the merge amount source.
- CDB rows are converted to USD during raw generation and stored as `contract_value_usd`.

## Repository Layout

- `src/capstonewb/`: package code (CLI, source-specific crawlers, models)
- `scripts/`: generation and merge scripts
- `data/raw/`: source-level raw datasets
- `data/merged_data/`: merged and finalized exports
- `docs/`: static viewer assets and data dictionary
