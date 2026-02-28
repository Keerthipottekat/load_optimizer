const runBtn = document.getElementById("runBtn");
const statusSection = document.getElementById("statusSection");
const metricsSection = document.getElementById("metricsSection");
const zoneTableBody = document.querySelector("#zoneTable tbody");

let loadChart = null; // Important for destroying old chart

runBtn.addEventListener("click", async () => {
    statusSection.innerHTML = "Running simulation...";

    try {
        const response = await fetch("http://localhost:8001/simulate");
        const data = await response.json();

        statusSection.innerHTML = `<div class="alert alert-success">Simulation complete.</div>`;

        renderMetrics(data.metrics);
        renderTable(data.history);
        renderChart(data.history);

    } catch (error) {
        statusSection.innerHTML = `<div class="alert alert-danger">Error connecting to backend.</div>`;
        console.error(error);
    }
});

function renderMetrics(metrics) {
    metricsSection.innerHTML = `
        <div class="col-md-3">
            <div class="card p-3 text-center">
                <h6>Peak Load</h6>
                <strong>${metrics.peak_load.toFixed(1)} units</strong>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card p-3 text-center">
                <h6>Average Load</h6>
                <strong>${metrics.avg_load.toFixed(1)} units</strong>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card p-3 text-center">
                <h6>Overload Hours</h6>
                <strong>${metrics.overload_hours}</strong>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card p-3 text-center">
                <h6>Total Load Shed</h6>
                <strong>${metrics.total_shed.toFixed(1)} units</strong>
            </div>
        </div>
    `;
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
    const predicted = history.map(h => h.predicted_load);
    const optimized = history.map(h => h.optimized_load);
    const capacity = Array(24).fill(150); // fixed transformer capacity

    const ctx = document.getElementById("loadChart").getContext("2d");

    // Destroy previous chart before creating new one
    if (loadChart) {
        loadChart.destroy();
    }

    loadChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: hours,
            datasets: [
                {
                    label: "Predicted Load",
                    data: predicted,
                    borderColor: "orange",
                    backgroundColor: "rgba(255,165,0,0.2)",
                    tension: 0.3
                },
                {
                    label: "Optimized Load",
                    data: optimized,
                    borderColor: "green",
                    backgroundColor: "rgba(0,128,0,0.2)",
                    tension: 0.3
                },
                {
                    label: "Capacity",
                    data: capacity,
                    borderColor: "red",
                    borderDash: [5, 5],
                    tension: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: false,
                    min: 0,
                    max: 200,
                    title: {
                        display: true,
                        text: "Load (Units)"
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: "Hour of Day"
                    }
                }
            },
            plugins: {
                legend: {
                    position: "top"
                }
            }
        }
    });
}