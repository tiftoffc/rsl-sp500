function rsl_overview_shortcode() {
    ob_start();
    ?>
    <div class="rsl-container">
        <p id="last-update" style="font-size: 12px; color: #666; margin-top: -10px; margin-bottom: 15px;"></p>
        
        <div class="rsl-buttons">
            <button class="rsl-btn active" data-type="26d">26 Tage</button>
            <button class="rsl-btn" data-type="26w">26 Wochen</button>
        </div>
        
        <input type="text" id="rsl-filter" placeholder="Ticker filtern (z.B. AAPL, MSFT, NVDA)" />
        
        <div class="rsl-toggles">
            <label><input type="checkbox" id="toggle-perf" checked> Performance</label>
            <label><input type="checkbox" id="toggle-fund" checked> Marktkap. / Umsatz</label>
            <label><input type="checkbox" id="toggle-iv" checked> IVR / IVP</label>
        </div>

        <div style="display: flex; gap: 15px; margin-bottom: 15px; flex-wrap: wrap;">
            <select id="sector-filter" style="padding: 8px; min-width: 200px;">
                <option value="">Alle Sektoren</option>
            </select>
            <select id="industry-filter" style="padding: 8px; min-width: 250px;" disabled>
                <option value="">Alle Sub-Industries</option>
            </select>
        </div>

        <h3 style="margin-top: 30px;">Sektor-Übersicht</h3>
        <table class="rsl-table" id="sector-table">
            <thead>
                <tr>
                    <th>Sektor / Sub-Industry</th>
                    <th>Anzahl</th>
                    <th>Ø RSL</th>
                    <th>Top Titel</th>
                </tr>
            </thead>
            <tbody id="sector-tbody"></tbody>
        </table>

        <table class="rsl-table" style="margin-top: 30px;">
            <thead>
                <tr>
                    <th>Rank</th>
                    <th id="other-rank-header">26W</th>
                    <th>Ticker</th>
                    <th>Name</th>
                    <th>Sektor</th>
                    <th>Industry</th>
                    <th>RSL</th>
                    <th class="col-perf">% 1T</th>
                    <th class="col-perf">% 1W</th>
                    <th class="col-perf">% 1M</th>
                    <th class="col-fund">Marktkap.</th>
                    <th class="col-fund">Umsatz</th>
                    <th class="col-iv">IVR</th>
                    <th class="col-iv">IVP</th>
                </tr>
            </thead>
            <tbody id="rsl-tbody"></tbody>
        </table>
    </div>

    <style>
    .rsl-container { max-width: 1400px; margin: 0 auto; }
    .rsl-buttons { margin-bottom: 15px; }
    .rsl-btn { padding: 8px 16px; margin-right: 8px; border: none; border-radius: 4px; cursor: pointer; background: #e0e0e0; }
    .rsl-btn.active { background: #1a73e8; color: white; }
    #rsl-filter { width: 100%; max-width: 400px; padding: 8px; margin-bottom: 15px; }
    .rsl-toggles { margin-bottom: 15px; display: flex; gap: 20px; flex-wrap: wrap; font-size: 14px; }
    .rsl-toggles label { cursor: pointer; user-select: none; }
    .rsl-table { width: 100%; border-collapse: collapse; font-size: 14px; }
    .rsl-table th, .rsl-table td { padding: 8px 10px; text-align: left; border-bottom: 1px solid #ddd; }
    .rsl-table th { background: #f5f5f5; font-weight: 600; }
    .rsl-table a { color: #1a73e8; font-weight: 600; text-decoration: none; }
    .rsl-table a:hover { text-decoration: underline; }
    .rank-num { font-weight: 600; }
    .positive { color: #0d7a3f; }
    .negative { color: #c5221f; }
    .delta-empty { color: #999; }
    .hide-perf .col-perf,
    .hide-fund .col-fund,
    .hide-iv .col-iv { display: none; }
    .industry-row { background: #fafafa; }
    .industry-row td:first-child { padding-left: 30px; font-style: italic; color: #555; }
    </style>

    <script>
    let data = { "26d": [], "26w": [] };
    let currentType = "26d";

    function loadData() {
        Promise.all([
            fetch('https://raw.githubusercontent.com/tiftoffc/rsl-sp500/main/rsl_26d.json').then(r => r.json()),
            fetch('https://raw.githubusercontent.com/tiftoffc/rsl-sp500/main/rsl_26w.json').then(r => r.json()),
            fetch('https://raw.githubusercontent.com/tiftoffc/rsl-sp500/main/last_update.json').then(r => r.json()).catch(() => ({updated: "-"}))
        ]).then(([d26, d26w, update]) => {
            data["26d"] = d26;
            data["26w"] = d26w;
            document.getElementById('last-update').textContent = 'Letztes Update: ' + (update.updated || "-");
            populateSectors();
            render(currentType);
        }).catch(err => console.error("Fehler beim Laden:", err));
    }

    function populateSectors() {
        const sectors = [...new Set(data[currentType].map(item => item.sector).filter(s => s && s !== "-"))].sort();
        const select = document.getElementById('sector-filter');
        select.innerHTML = '<option value="">Alle Sektoren</option>' + 
            sectors.map(s => `<option value="${s}">${s}</option>`).join('');
        updateIndustryFilter();
    }

    function updateIndustryFilter() {
        const sector = document.getElementById('sector-filter').value;
        const industrySelect = document.getElementById('industry-filter');
        industrySelect.innerHTML = '<option value="">Alle Sub-Industries</option>';
        
        if (!sector) {
            industrySelect.disabled = true;
            return;
        }

        const industries = [...new Set(
            data[currentType]
                .filter(item => item.sector === sector && item.industry && item.industry !== "-")
                .map(item => item.industry)
        )].sort();

        industrySelect.innerHTML += industries.map(i => `<option value="${i}">${i}</option>`).join('');
        industrySelect.disabled = false;
    }

    function render(type, filter = '') {
        currentType = type;
        let list = (data[type] || []).slice();
        
        if (filter) {
            const filters = filter.split(',')
                .map(f => f.trim().toUpperCase())
                .filter(f => f.length > 0);
            if (filters.length > 0) {
                list = list.filter(item => filters.some(f => item.ticker.includes(f)));
            }
        }

        const sectorFilter = document.getElementById('sector-filter').value;
        if (sectorFilter) {
            list = list.filter(item => item.sector === sectorFilter);
        }

        const industryFilter = document.getElementById('industry-filter').value;
        if (industryFilter) {
            list = list.filter(item => item.industry === industryFilter);
        }

        const header = document.getElementById('other-rank-header');
        if (header) header.textContent = (type === '26d') ? '26W' : '26T';

        const fmtPct = (v) => {
            if (v === null || v === undefined || isNaN(v)) return "-";
            const cls = v >= 0 ? "positive" : "negative";
            const sign = v > 0 ? "+" : "";
            return `<span class="${cls}">${sign}${v.toFixed(2)}%</span>`;
        };

        const fmtBig = (v) => {
            if (!v || isNaN(v)) return "-";
            return (v / 1e9).toFixed(1) + " Mrd";
        };

        const fmtIv = (v) => (v !== null && v !== undefined && !isNaN(v)) ? v.toFixed(1) : "-";

        const tbody = document.getElementById('rsl-tbody');
        tbody.innerHTML = list.map(item => {
            let rankHtml = `<span class="rank-num">${item.rank}</span>`;
            if (item.delta !== null && item.delta !== undefined && item.delta !== 0) {
                if (item.delta > 0) rankHtml += ` <span class="positive">(↑${item.delta})</span>`;
                else rankHtml += ` <span class="negative">(↓${Math.abs(item.delta)})</span>`;
            } else {
                rankHtml += ` <span class="delta-empty">(–)</span>`;
            }

            return `
                <tr>
                    <td>${rankHtml}</td>
                    <td>${item.rank_other}</td>
                    <td><a href="https://www.tradingview.com/chart/?symbol=${item.ticker}" target="_blank" rel="noopener">${item.ticker}</a></td>
                    <td>${item.name || "-"}</td>
                    <td>${item.sector || "-"}</td>
                    <td>${item.industry || "-"}</td>
                    <td>${item.rsl ? item.rsl.toFixed(2) : "-"}</td>
                    <td class="col-perf">${fmtPct(item.pct_1d)}</td>
                    <td class="col-perf">${fmtPct(item.pct_1w)}</td>
                    <td class="col-perf">${fmtPct(item.pct_1m)}</td>
                    <td class="col-fund">${fmtBig(item.market_cap)}</td>
                    <td class="col-fund">${fmtBig(item.revenue)}</td>
                    <td class="col-iv">${fmtIv(item.ivr)}</td>
                    <td class="col-iv">${fmtIv(item.ivp)}</td>
                </tr>
            `;
        }).join('');

        updateSectorOverview(list);
    }

    function updateSectorOverview(list) {
        const bySector = {};
        list.forEach(item => {
            if (!item.sector || item.sector === "-") return;
            if (!bySector[item.sector]) bySector[item.sector] = { items: [], industries: {} };
            bySector[item.sector].items.push(item);

            const ind = item.industry || "Unbekannt";
            if (!bySector[item.sector].industries[ind]) bySector[item.sector].industries[ind] = [];
            bySector[item.sector].industries[ind].push(item);
        });

        let rows = '';
        Object.entries(bySector).sort((a, b) => a[0].localeCompare(b[0])).forEach(([sector, data]) => {
            const items = data.items;
            const avgRsl = (items.reduce((sum, i) => sum + (i.rsl || 0), 0) / items.length).toFixed(2);
            const top = [...items].sort((a, b) => (b.rsl || 0) - (a.rsl || 0))[0];

            rows += `<tr>
                <td><strong>${sector}</strong></td>
                <td>${items.length}</td>
                <td>${avgRsl}</td>
                <td>${top.ticker} (${top.rsl ? top.rsl.toFixed(2) : "-"})</td>
            </tr>`;

            Object.entries(data.industries).sort((a, b) => a[0].localeCompare(b[0])).forEach(([industry, indItems]) => {
                const indAvg = (indItems.reduce((sum, i) => sum + (i.rsl || 0), 0) / indItems.length).toFixed(2);
                const indTop = [...indItems].sort((a, b) => (b.rsl || 0) - (a.rsl || 0))[0];
                rows += `<tr class="industry-row">
                    <td>↳ ${industry}</td>
                    <td>${indItems.length}</td>
                    <td>${indAvg}</td>
                    <td>${indTop.ticker} (${indTop.rsl ? indTop.rsl.toFixed(2) : "-"})</td>
                </tr>`;
            });
        });

        document.getElementById('sector-tbody').innerHTML = rows || '<tr><td colspan="4">Keine Daten</td></tr>';
    }

    function setupToggles() {
        const table = document.querySelector('.rsl-table:last-of-type');
        const toggles = {
            perf: document.getElementById('toggle-perf'),
            fund: document.getElementById('toggle-fund'),
            iv: document.getElementById('toggle-iv')
        };
        function update() {
            table.classList.toggle('hide-perf', !toggles.perf.checked);
            table.classList.toggle('hide-fund', !toggles.fund.checked);
            table.classList.toggle('hide-iv', !toggles.iv.checked);
        }
        Object.values(toggles).forEach(cb => cb && cb.addEventListener('change', update));
        update();
    }

    document.querySelectorAll('.rsl-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.rsl-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            populateSectors();
            render(btn.dataset.type, document.getElementById('rsl-filter').value);
        });
    });

    document.getElementById('rsl-filter').addEventListener('input', (e) => {
        render(currentType, e.target.value);
    });

    document.getElementById('sector-filter').addEventListener('change', () => {
        document.getElementById('industry-filter').value = "";
        updateIndustryFilter();
        render(currentType, document.getElementById('rsl-filter').value);
    });

    document.getElementById('industry-filter').addEventListener('change', () => {
        render(currentType, document.getElementById('rsl-filter').value);
    });

    loadData();
    setupToggles();
    </script>
    <?php
    return ob_get_clean();
}
add_shortcode('rsl_uebersicht', 'rsl_overview_shortcode');
