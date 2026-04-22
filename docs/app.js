const DATA_PATH =
  "https://raw.githubusercontent.com/rubingwang/CapstoneWB/main/data/world_bank_lac_2015_2025_yearly_notice_level/world_bank_lac_2015_2025_notice_level_merged.csv";
const PAGE_SIZE = 50;

const state = {
  rows: [],
  filteredRows: [],
  currentPage: 1,
};

const dom = {
  yearFilter: document.getElementById("yearFilter"),
  countryFilter: document.getElementById("countryFilter"),
  noticeTypeFilter: document.getElementById("noticeTypeFilter"),
  winningFirmCountryFilter: document.getElementById("winningFirmCountryFilter"),
  searchInput: document.getElementById("searchInput"),
  resetBtn: document.getElementById("resetBtn"),
  statusText: document.getElementById("statusText"),
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
  const hay = [
    row.project_name,
    row.project_id,
    row.notice_no,
    row.winning_firm_name,
    row.procurement_method,
    row.country,
  ]
    .map(normalize)
    .join(" ")
    .toLowerCase();
  return hay.includes(q);
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
    td.colSpan = 13;
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
    const cells = [
      normalize(row.year_awarded),
      normalize(row.date_awarded || row.awarded_date),
      normalize(row.country),
      normalize(row.notice_type),
      normalize(row.notice_no),
      normalize(row.project_id),
      normalize(row.project_name),
      normalize(row.winning_firm_name),
      normalize(row.winning_firm_country),
      normalize(row.contract_currency),
      normalize(row.contract_amount),
      normalize(row.procurement_method),
      normalize(row.contract_url),
    ];

    cells.forEach((cell, i) => {
      const td = document.createElement("td");
      if (i === 12 && cell) {
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

loadData();