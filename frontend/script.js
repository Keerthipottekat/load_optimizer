const runBeforeBtn = document.getElementById("runBeforeBtn");
const runAfterBtn = document.getElementById("runAfterBtn");
const scenarioSelect = document.getElementById("scenarioSelect");
const statusSection = document.getElementById("statusSection");
const metricsSection = document.getElementById("metricsSection");
const zoneTableBody = document.querySelector("#zoneTable tbody");

let loadChart = null; // Important for destroying old chart

async function runSimulation(algorithm) {
    statusSection.innerHTML = "Running simulation...";
    const scenario = scenarioSelect.value || "normal";

    try {
        const response = await fetch(`http://localhost:8000/simulate?scenario=${scenario}&algorithm=${algorithm}`);
        const data = await response.json();

        statusSection.innerHTML = `<div class="alert alert-success">Simulation complete for scenario: <strong>${scenario.toUpperCase()}</strong> | Algorithm: <strong>${algorithm.toUpperCase()}</strong></div>`;

        renderMetrics(data.metrics);
        renderTable(data.history);
        renderChart(data.history);

    } catch (error) {
        statusSection.innerHTML = `<div class="alert alert-danger">Error connecting to backend.</div>`;
        console.error(error);
    }
}

runBeforeBtn.addEventListener("click", () => runSimulation("greedy"));
runAfterBtn.addEventListener("click", () => runSimulation("proportional"));

let lastMetrics = null;

function renderMetrics(metrics) {
    let peakDiffStr = "";
    let avgDiffStr = "";
    let hoursDiffStr = "";
    let shedDiffStr = "";
    let resStr = "";

    if (lastMetrics) {
        const pDiff = metrics.peak_load - lastMetrics.peak_load;
        const aDiff = metrics.avg_load - lastMetrics.avg_load;
        const hDiff = metrics.overload_hours - lastMetrics.overload_hours;
        const sDiff = metrics.total_shed - lastMetrics.total_shed;
        const rDiff = metrics.resilience_score - (lastMetrics.resilience_score || 0);

        peakDiffStr = pDiff !== 0 ? `<small class="${pDiff > 0 ? 'text-danger' : 'text-success'}">(${pDiff > 0 ? '+' : ''}${pDiff.toFixed(1)})</small>` : '<small class="text-muted">(-)</small>';
        avgDiffStr = aDiff !== 0 ? `<small class="${aDiff > 0 ? 'text-danger' : 'text-success'}">(${aDiff > 0 ? '+' : ''}${aDiff.toFixed(1)})</small>` : '<small class="text-muted">(-)</small>';
        hoursDiffStr = hDiff !== 0 ? `<small class="${hDiff > 0 ? 'text-danger' : 'text-success'}">(${hDiff > 0 ? '+' : ''}${hDiff})</small>` : '<small class="text-muted">(-)</small>';
        shedDiffStr = sDiff !== 0 ? `<small class="${sDiff > 0 ? 'text-danger' : 'text-success'}">(${sDiff > 0 ? '+' : ''}${sDiff.toFixed(1)})</small>` : '<small class="text-muted">(-)</small>';
        if (lastMetrics.resilience_score !== undefined) {
            resStr = rDiff !== 0 ? `<small class="${rDiff < 0 ? 'text-danger' : 'text-success'}">(${rDiff > 0 ? '+' : ''}${rDiff.toFixed(1)})</small>` : '<small class="text-muted">(-)</small>';
        }
    }

    let riskColor = "text-success";
    if (metrics.blackout_risk === "MEDIUM") riskColor = "text-warning";
    if (metrics.blackout_risk === "HIGH") riskColor = "text-danger";

    metricsSection.innerHTML = `
        <div class="col-md-4 col-lg-2">
            <div class="card p-3 text-center metric-card">
                <h6 class="mb-1 text-muted" style="font-size: 0.8rem;">Peak Load</h6>
                <strong class="fs-5">${metrics.peak_load.toFixed(1)} <span class="fs-6 fw-normal">u</span></strong>
                ${peakDiffStr}
            </div>
        </div>
        <div class="col-md-4 col-lg-2">
            <div class="card p-3 text-center metric-card">
                <h6 class="mb-1 text-muted" style="font-size: 0.8rem;">Average Load</h6>
                <strong class="fs-5">${metrics.avg_load.toFixed(1)} <span class="fs-6 fw-normal">u</span></strong>
                ${avgDiffStr}
            </div>
        </div>
        <div class="col-md-4 col-lg-2">
            <div class="card p-3 text-center metric-card">
                <h6 class="mb-1 text-muted" style="font-size: 0.8rem;">Overload Hours</h6>
                <strong class="fs-5">${metrics.overload_hours} <span class="fs-6 fw-normal">h</span></strong>
                ${hoursDiffStr}
            </div>
        </div>
        <div class="col-md-4 col-lg-2">
            <div class="card p-3 text-center metric-card">
                <h6 class="mb-1 text-muted" style="font-size: 0.8rem;">Total Load Shed</h6>
                <strong class="fs-5">${metrics.total_shed.toFixed(1)} <span class="fs-6 fw-normal">u</span></strong>
                ${shedDiffStr}
            </div>
        </div>
        <div class="col-md-4 col-lg-2">
            <div class="card p-3 text-center metric-card border-info">
                <h6 class="mb-1 text-info fw-bold" style="font-size: 0.8rem;">Resilience</h6>
                <strong class="fs-5">${metrics.resilience_score} <span class="fs-6 fw-normal">%</span></strong>
                ${resStr}
            </div>
        </div>
        <div class="col-md-4 col-lg-2">
            <div class="card p-3 text-center metric-card border-warning">
                <h6 class="mb-1 text-muted fw-bold" style="font-size: 0.8rem;">Blackout Risk</h6>
                <strong class="fs-6 mt-1 ${riskColor}">${metrics.blackout_risk}</strong>
                <small class="text-white mt-1">.</small>
            </div>
        </div>
    `;

    // Save for next comparison
    lastMetrics = metrics;
}

function renderTable(history) {
    zoneTableBody.innerHTML = "";

    history.forEach(entry => {
        const total = Object.values(entry.zone_allocations)
            .reduce((a, b) => a + b, 0);

        const row = `
            <tr>
                <td>${entry.hour}</td>
                <td>${entry.zone_allocations.hospital.toFixed(1)}</td>
                <td>${entry.zone_allocations.residential.toFixed(1)}</td>
                <td>${entry.zone_allocations.commercial.toFixed(1)}</td>
                <td>${entry.zone_allocations.ev_charging.toFixed(1)}</td>
                <td>${total.toFixed(1)}</td>
                <td>${entry.is_overloaded ? "Yes" : "No"}</td>
            </tr>
        `;
        zoneTableBody.innerHTML += row;
    });
}

function renderChart(history) {
    const hours = history.map(h => h.hour);
    const capacity = Array(24).fill(150); // fixed transformer capacity
    const predicted = history.map(h => h.predicted_load);

    // Extract individual zone allocations for stacking
    const hospital = history.map(h => h.zone_allocations.hospital);
    const residential = history.map(h => h.zone_allocations.residential);
    const commercial = history.map(h => h.zone_allocations.commercial);
    const ev = history.map(h => h.zone_allocations.ev_charging);

    const ctx = document.getElementById("loadChart").getContext("2d");

    // Destroy previous chart before creating new one
    if (loadChart) {
        loadChart.destroy();
    }

    loadChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: hours,
            datasets: [
                {
                    label: "Hospital",
                    data: hospital,
                    backgroundColor: "rgba(255, 107, 107, 0.8)", // #FF6B6B
                    stack: "Stack 0",
                    order: 1
                },
                {
                    label: "Residential",
                    data: residential,
                    backgroundColor: "rgba(78, 205, 196, 0.8)", // #4ECDC4
                    stack: "Stack 0",
                    order: 1
                },
                {
                    label: "Commercial",
                    data: commercial,
                    backgroundColor: "rgba(69, 183, 209, 0.8)", // #45B7D1
                    stack: "Stack 0",
                    order: 1
                },
                {
                    label: "EV Charging",
                    data: ev,
                    backgroundColor: "rgba(255, 160, 122, 0.8)", // #FFA07A
                    stack: "Stack 0",
                    order: 1
                },
                {
                    label: "Predicted Raw Demand",
                    data: predicted,
                    type: "line",
                    borderColor: "orange",
                    borderDash: [3, 3],
                    backgroundColor: "transparent",
                    tension: 0.3,
                    borderWidth: 2,
                    order: 0,
                    stack: "Predicted"
                },
                {
                    label: "Capacity Limit",
                    data: capacity,
                    type: "line",
                    borderColor: "red",
                    borderDash: [5, 5],
                    backgroundColor: "transparent",
                    tension: 0,
                    borderWidth: 2,
                    pointRadius: 0,
                    order: 0,
                    stack: "Capacity"
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    stacked: true,
                    beginAtZero: true,
                    max: 200,
                    title: {
                        display: true,
                        text: "Load (Units)"
                    }
                },
                x: {
                    stacked: true,
                    title: {
                        display: true,
                        text: "Hour of Day"
                    }
                }
            },
            plugins: {
                legend: {
                    position: "bottom"
                }
            }
        }
    });
}


// ================================================================
// AI Load Shedding Schedule Section
// ================================================================

const scheduleForm = document.getElementById("scheduleForm");
const schedStatus = document.getElementById("schedStatus");
const schedMetrics = document.getElementById("schedMetrics");
const schedChartCard = document.getElementById("schedChartCard");
const schedTableCard = document.getElementById("schedTableCard");
const schedTableBody = document.querySelector("#schedTable tbody");

let schedChart = null;

scheduleForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    // Gather operator inputs
    const scenario = document.getElementById("schedScenario").value;
    const capacity = parseFloat(document.getElementById("schedCapacity").value) || 150;
    const maxOutage = parseInt(document.getElementById("schedMaxOutage").value) || 2;

    const protectedZones = [];
    document.querySelectorAll(".sched-protected:checked").forEach((cb) => {
        protectedZones.push(cb.value);
    });

    schedStatus.innerHTML = `<div class="alert alert-info">Generating schedule...</div>`;
    schedMetrics.innerHTML = "";
    schedChartCard.style.display = "none";
    schedTableCard.style.display = "none";

    try {
        const response = await fetch("http://localhost:8000/recommend-schedule", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                scenario,
                capacity,
                protected_zones: protectedZones,
                max_outage_hours_per_zone: maxOutage,
            }),
        });
        const data = await response.json();

        schedStatus.innerHTML = `<div class="alert alert-success">Schedule generated for <strong>${scenario.toUpperCase()}</strong> (capacity: ${capacity})</div>`;

        renderSchedMetrics(data, capacity);
        renderSchedChart(data.schedule, capacity);
        renderSchedTable(data.schedule, capacity);

    } catch (error) {
        schedStatus.innerHTML = `<div class="alert alert-danger">Error connecting to backend.</div>`;
        console.error(error);
    }
});

function renderSchedMetrics(data, capacity) {
    const stabilityPct = (data.grid_stability_score * 100).toFixed(1);
    const stabilityColor =
        data.grid_stability_score >= 0.9 ? "text-success" :
            data.grid_stability_score >= 0.6 ? "text-warning" : "text-danger";

    schedMetrics.innerHTML = `
        <div class="col-md-3">
            <div class="card p-3 text-center metric-card">
                <h6>Overloads Prevented</h6>
                <strong class="text-success">${data.overload_hours_prevented}</strong>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card p-3 text-center metric-card">
                <h6>Energy Saved</h6>
                <strong>${data.estimated_energy_saved.toFixed(1)} units</strong>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card p-3 text-center metric-card">
                <h6>Grid Stability</h6>
                <strong class="${stabilityColor}">${stabilityPct}%</strong>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card p-3 text-center metric-card">
                <h6>Hours with Shedding</h6>
                <strong>${data.schedule.filter(s => s.zones_shed.length > 0).length}</strong>
            </div>
        </div>
    `;
}

function renderSchedChart(schedule, capacity) {
    schedChartCard.style.display = "block";

    const hours = schedule.map(s => s.hour);
    const loads = schedule.map(s => s.predicted_load);
    const barColors = schedule.map(s =>
        s.zones_shed.length > 0
            ? "rgba(255, 193, 7, 0.7)"   // yellow – shed
            : s.predicted_load > capacity
                ? "rgba(220, 53, 69, 0.7)"   // red – overloaded (not resolved)
                : "rgba(25, 135, 84, 0.7)"    // green – safe
    );

    const ctx = document.getElementById("schedChart").getContext("2d");
    if (schedChart) schedChart.destroy();

    schedChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: hours,
            datasets: [
                {
                    label: "Predicted Load",
                    data: loads,
                    backgroundColor: barColors,
                    borderRadius: 3,
                },
                {
                    label: "Capacity",
                    data: Array(24).fill(capacity),
                    type: "line",
                    borderColor: "red",
                    borderDash: [5, 5],
                    pointRadius: 0,
                    tension: 0,
                    fill: false,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: "Load (Units)" },
                },
                x: {
                    title: { display: true, text: "Hour of Day" },
                },
            },
            plugins: {
                legend: { position: "top" },
            },
        },
    });
}

function renderSchedTable(schedule, capacity) {
    schedTableCard.style.display = "block";
    schedTableBody.innerHTML = "";

    schedule.forEach((entry) => {
        const overloaded = entry.predicted_load > capacity;
        const shedText = entry.zones_shed.length > 0
            ? entry.zones_shed.join(", ")
            : "—";
        const rowClass = entry.zones_shed.length > 0
            ? "table-warning"
            : overloaded
                ? "table-danger"
                : "";

        schedTableBody.innerHTML += `
            <tr class="${rowClass}">
                <td>${entry.hour}</td>
                <td>${entry.predicted_load.toFixed(1)}</td>
                <td>${overloaded ? "⚠️ Yes" : "No"}</td>
                <td>${shedText}</td>
            </tr>
        `;
    });
}