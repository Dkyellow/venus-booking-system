const ChartManager = {
    instances: {},

    init() {
        this.initDefaultOptions();
    },

    initDefaultOptions() {
        this.defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false, position: 'top', labels: { usePointStyle: true, padding: 16, font: { family: "'Inter', sans-serif", size: 12 } } },
                tooltip: { backgroundColor: '#1F2937', titleFont: { family: "'Inter', sans-serif" }, bodyFont: { family: "'Inter', sans-serif" }, padding: 12, cornerRadius: 8 }
            }
        };
    },

    createLineChart(canvasId, labels, datasets, options = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        if (this.instances[canvasId]) this.instances[canvasId].destroy();
        const config = {
            type: 'line',
            data: { labels, datasets: datasets.map(ds => ({ tension: 0.4, pointRadius: 4, pointHoverRadius: 6, borderWidth: 2, fill: false, ...ds })) },
            options: { ...this.defaultOptions, scales: { y: { beginAtZero: true, grid: { color: '#F3F4F6' }, ticks: { font: { family: "'Inter', sans-serif", size: 12 } } }, x: { grid: { display: false }, ticks: { font: { family: "'Inter', sans-serif", size: 12 } } } }, ...options }
        };
        this.instances[canvasId] = new Chart(ctx, config);
        return this.instances[canvasId];
    },

    createBarChart(canvasId, labels, datasets, options = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        if (this.instances[canvasId]) this.instances[canvasId].destroy();
        const config = {
            type: 'bar',
            data: { labels, datasets: datasets.map(ds => ({ borderRadius: 6, borderSkipped: false, ...ds })) },
            options: { ...this.defaultOptions, scales: { y: { beginAtZero: true, grid: { color: '#F3F4F6' }, ticks: { font: { family: "'Inter', sans-serif", size: 12 } } }, x: { grid: { display: false }, ticks: { font: { family: "'Inter', sans-serif", size: 12 } } } }, ...options }
        };
        this.instances[canvasId] = new Chart(ctx, config);
        return this.instances[canvasId];
    },

    createDoughnutChart(canvasId, labels, data, colors, options = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        if (this.instances[canvasId]) this.instances[canvasId].destroy();
        const config = {
            type: 'doughnut',
            data: { labels, datasets: [{ data, backgroundColor: colors, borderWidth: 0, hoverOffset: 4 }] },
            options: { ...this.defaultOptions, cutout: '70%', plugins: { ...this.defaultOptions.plugins, legend: { display: true, position: 'bottom', labels: { usePointStyle: true, padding: 12, font: { family: "'Inter', sans-serif", size: 12 } } } }, ...options }
        };
        this.instances[canvasId] = new Chart(ctx, config);
        return this.instances[canvasId];
    },

    createPieChart(canvasId, labels, data, colors) {
        return this.createDoughnutChart(canvasId, labels, data, colors, { cutout: '0%' });
    },

    destroyChart(canvasId) {
        if (this.instances[canvasId]) { this.instances[canvasId].destroy(); delete this.instances[canvasId]; }
    },

    destroyAll() { Object.keys(this.instances).forEach(id => this.destroyChart(id)); }
};

document.addEventListener('DOMContentLoaded', () => ChartManager.init());
