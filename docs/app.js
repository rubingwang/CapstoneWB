const DATA_PATH = "data/world_bank_lac_contracts_china_60.csv";
const DATA_UPDATED_AT_MADRID = "2026-04-30 12:00:00 CEST";
const PAGE_SIZE = 50;

const state = {
  rows: [],
  filteredRows: [],
  currentPage: 1,
  columns: [],
};

const dom = {
  dataUpdatedAt: document.getElementById("dataUpdatedAt"),
  yearFilter: document.getElementById("yearFilter"),
  countryFilter: document.getElementById("countryFilter"),
  noticeTypeFilter: document.getElementById("noticeTypeFilter"),
  winningFirmCountryFilter: document.getElementById("winningFirmCountryFilter"),
  searchInput: document.getElementById("searchInput"),
  resetBtn: document.getElementById("resetBtn"),
  statusText: document.getElementById("statusText"),
  tableHeadRow: document.getElementById("tableHeadRow"),
  tableBody: document.getElementById("tableBody"),
  prevBtn: document.getElementById("prevBtn"),
  nextBtn: document.getElementById("nextBtn"),
  pageInfo: document.getElementById("pageInfo"),
};

function normalize(v) {
  return (v ?? "").toString().trim();
}

function optionValues(rows, key) {
  const values = [...new Set(rows.map((r) => normalize(r[key])).filter(Boolean))];
  values.sort((a, b) => a.localeCompare(b));
  return values;
}

function fillSelect(selectEl, values) {
  for (const value of values) {
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = value;
    selectEl.appendChild(opt);
  }
}

function matchesSearch(row, q) {
  if (!q) return true;
  const hay = Object.values(row)
    .map((v) => normalize(v))
    .join(" ")
    .toLowerCase();
  return hay.includes(q);
}

function titleForColumn(column) {
  return column
    .split("_")
    .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
    .join(" ");
}

function isUrlValue(value) {
  const v = normalize(value).toLowerCase();
  return v.startsWith("http://") || v.startsWith("https://");
}

function chooseColumns(rows) {
  const available = rows.length ? Object.keys(rows[0]) : [];
  const preferred = [
    "year_awarded",
    "date_awarded",
    "country",
    "winning_firm_country",
    "notice_type",
    "notice_no",
    "project_id",
    "project_name",
  ];
  const inPreferred = preferred.filter((c) => available.includes(c));
  const others = available.filter((c) => !inPreferred.includes(c));
  return [...inPreferred, ...others];
}

function renderHeader() {
  dom.tableHeadRow.innerHTML = "";
  for (const col of state.columns) {
    const th = document.createElement("th");
    th.textContent = titleForColumn(col);
    dom.tableHeadRow.appendChild(th);
  }
}

function applyFilters() {
  const year = normalize(dom.yearFilter.value);
  const country = normalize(dom.countryFilter.value);
  const noticeType = normalize(dom.noticeTypeFilter.value);
  const winningFirmCountry = normalize(dom.winningFirmCountryFilter.value);
  const query = normalize(dom.searchInput.value).toLowerCase();

  state.filteredRows = state.rows.filter((row) => {
    if (year && normalize(row.year_awarded) !== year) return false;
    if (country && normalize(row.country) !== country) return false;
    if (noticeType && normalize(row.notice_type) !== noticeType) return false;
    if (winningFirmCountry && normalize(row.winning_firm_country) !== winningFirmCountry) return false;
    if (!matchesSearch(row, query)) return false;
    return true;
  });

  state.currentPage = 1;
  render();
}

function renderTable() {
  dom.tableBody.innerHTML = "";

  if (state.filteredRows.length === 0) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = Math.max(state.columns.length, 1);
    td.className = "empty";
    td.textContent = "No records match current filters.";
    tr.appendChild(td);
    dom.tableBody.appendChild(tr);
    return;
  }

  const start = (state.currentPage - 1) * PAGE_SIZE;
  const pageRows = state.filteredRows.slice(start, start + PAGE_SIZE);

  for (const row of pageRows) {
    const tr = document.createElement("tr");

    state.columns.forEach((col) => {
      const cell = normalize(row[col]);
      const td = document.createElement("td");
      if (cell && isUrlValue(cell)) {
        const a = document.createElement("a");
        a.href = cell;
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        a.textContent = "Open";
        td.appendChild(a);
      } else {
        td.textContent = cell;
      }
      tr.appendChild(td);
    });

    dom.tableBody.appendChild(tr);
  }
}

function renderStatus() {
  const total = state.rows.length;
  const shown = state.filteredRows.length;
  const totalPages = Math.max(1, Math.ceil(shown / PAGE_SIZE));
  const start = shown === 0 ? 0 : (state.currentPage - 1) * PAGE_SIZE + 1;
  const end = Math.min(shown, state.currentPage * PAGE_SIZE);
  dom.statusText.textContent = `Loaded ${total.toLocaleString()} rows. Showing ${shown.toLocaleString()} rows (${start}-${end}).`;
  dom.pageInfo.textContent = `Page ${state.currentPage} / ${totalPages}`;
  dom.prevBtn.disabled = state.currentPage <= 1;
  dom.nextBtn.disabled = state.currentPage >= totalPages;
}

function render() {
  renderHeader();
  renderTable();
  renderStatus();
}

function wireEvents() {
  dom.yearFilter.addEventListener("change", applyFilters);
  dom.countryFilter.addEventListener("change", applyFilters);
  dom.noticeTypeFilter.addEventListener("change", applyFilters);
  dom.winningFirmCountryFilter.addEventListener("change", applyFilters);
  dom.searchInput.addEventListener("input", applyFilters);

  dom.resetBtn.addEventListener("click", () => {
    dom.yearFilter.value = "";
    dom.countryFilter.value = "";
    dom.noticeTypeFilter.value = "";
    dom.winningFirmCountryFilter.value = "";
    dom.searchInput.value = "";
    applyFilters();
  });

  dom.prevBtn.addEventListener("click", () => {
    if (state.currentPage > 1) {
      state.currentPage -= 1;
      render();
    }
  });

  dom.nextBtn.addEventListener("click", () => {
    const totalPages = Math.max(1, Math.ceil(state.filteredRows.length / PAGE_SIZE));
    if (state.currentPage < totalPages) {
      state.currentPage += 1;
      render();
    }
  });
}

function loadData() {
  Papa.parse(DATA_PATH, {
    download: true,
    header: true,
    skipEmptyLines: true,
    complete: (res) => {
      state.rows = res.data;
      state.filteredRows = [...state.rows];
      // Prefer explicit ordering so `project_name` appears before link column `contract_url`.
      const preferredColumns = [
        "year_awarded",
        "date_awarded",
        "country",
        "winning_firm_country",
        "notice_type",
        "notice_no",
        "project_id",
        "project_name",
        "contract_url",
      ];
      const available = state.rows.length ? Object.keys(state.rows[0]) : [];
      state.columns = [
        ...preferredColumns.filter((c) => available.includes(c)),
        ...available.filter((c) => !preferredColumns.includes(c)),
      ];

      fillSelect(dom.yearFilter, optionValues(state.rows, "year_awarded"));
      fillSelect(dom.countryFilter, optionValues(state.rows, "country"));
      fillSelect(dom.noticeTypeFilter, optionValues(state.rows, "notice_type"));
      fillSelect(dom.winningFirmCountryFilter, optionValues(state.rows, "winning_firm_country"));

      wireEvents();
      render();
    },
    error: () => {
      dom.statusText.textContent = "Failed to load dataset. Check data path and GitHub Pages settings.";
    },
  });
}

dom.dataUpdatedAt.textContent = `Data updated at (Madrid time): ${DATA_UPDATED_AT_MADRID}`;
loadData();