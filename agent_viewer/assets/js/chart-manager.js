/**
 * Chart manager - styled version
 */
function hexToRgba(hex, alpha = 0.15) {
    if (!hex) return `rgba(0,0,0,${alpha})`;
    let cleaned = hex.replace('#', '');
    if (cleaned.length === 3) {
        cleaned = cleaned.split('').map(ch => ch + ch).join('');
    }
    const bigint = parseInt(cleaned, 16);
    const r = (bigint >> 16) & 255;
    const g = (bigint >> 8) & 255;
    const b = bigint & 255;
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function buildBaselineDataset(baselineOptions, sortedDates) {
    if (!sortedDates || !sortedDates.length) return null;
    const defaultMeta = {
        type: 'constant',
        value: 5000,
        label: 'Initial Balance ($5,000)',
        color: '#64748b'
    };

    const meta = baselineOptions && baselineOptions.meta
        ? { ...defaultMeta, ...baselineOptions.meta }
        : defaultMeta;

    if (!meta) return null;
    const type = (meta.type || 'constant').toLowerCase();
    if (type === 'none') return null;

    const color = meta.color || '#64748b';
    let data = [];

    if (type === 'price_series' && baselineOptions && baselineOptions.curve) {
        const curve = baselineOptions.curve;
        const valueMap = {};
        const dayValueMap = {};
        if (curve.dates && curve.values) {
            curve.dates.forEach((date, idx) => {
                if (idx < curve.values.length) {
                    const val = curve.values[idx];
                    valueMap[date] = val;
                    const datePart = date.split(' ')[0];
                    if (datePart) {
                        dayValueMap[datePart] = val;
                    }
                }
            });
        }
        let lastValue = null;
        sortedDates.forEach((date, idx) => {
            let value = valueMap[date];
            if (value === undefined) {
                const datePart = date.split(' ')[0];
                if (datePart && dayValueMap[datePart] !== undefined) {
                    value = dayValueMap[datePart];
                }
            }
            if (value !== undefined) {
                lastValue = value;
                data.push(value);
            } else if (lastValue !== null) {
                data.push(lastValue);
            } else {
                data.push(null);
            }
        });
    } else {
        const constantValue = meta.value || meta.initial_capital || meta.initialCapital || 5000;
        data = sortedDates.map(() => constantValue);
    }

    if (data.every(v => v === null)) {
        return null;
    }

    return {
        label: meta.label || 'Baseline',
        data,
        borderColor: color,
        backgroundColor: 'transparent',
        borderWidth: 2,
        borderDash: [6, 6],
        pointRadius: 0,
        pointHoverRadius: 0,
        spanGaps: true,
        tension: 0,
        order: 0
    };
}

class ChartManager {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) {
            console.error('Canvas element not found:', canvasId);
            return;
        }
        this.chart = null;
        this.isLogScale = false;
        this.init();
    }

    init() {
        const ctx = this.canvas.getContext('2d');
        
        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: []
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'nearest', // show only the nearest series
                    intersect: false,
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'right',
                        align: 'start',
                        labels: {
                            color: '#e2e8f0',
                            font: {
                                family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                                size: 19,
                                weight: '500'
                            },
                            usePointStyle: true,
                            pointStyle: 'circle',
                            padding: 18,
                            boxWidth: 12,
                            boxHeight: 12
                        }
                    },
                    tooltip: {
                        enabled: true,
                        mode: 'nearest', // show only the nearest series
                        intersect: false,
                        backgroundColor: 'rgba(15, 23, 42, 0.95)',
                        titleColor: '#94a3b8',
                        bodyColor: '#f1f5f9',
                        borderColor: 'rgba(148, 163, 184, 0.2)',
                        borderWidth: 1,
                        padding: 14,
                        cornerRadius: 8,
                        displayColors: true,
                        titleFont: {
                            size: 12,
                            weight: '600'
                        },
                        bodyFont: {
                            size: 13
                        },
                        callbacks: {
                            title: function(context) {
                                // display timestamp
                                return context[0].label;
                            },
                            label: function(context) {
                                // display value for current series
                                const value = context.parsed.y;
                                const label = context.dataset.label;
                                return `${label}: $${value.toFixed(2)}`;
                            },
                            labelColor: function(context) {
                                return {
                                    borderColor: context.dataset.borderColor,
                                    backgroundColor: context.dataset.borderColor,
                                    borderWidth: 2,
                                    borderRadius: 2
                                };
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(148, 163, 184, 0.08)',
                            drawBorder: false,
                            lineWidth: 1
                        },
                        ticks: {
                            color: '#94a3b8',
                            font: {
                                size: 11
                            },
                            maxRotation: 45,
                            minRotation: 45,
                            padding: 8
                        },
                        border: {
                            color: 'rgba(148, 163, 184, 0.15)'
                        }
                    },
                    y: {
                        type: 'linear',
                        grid: {
                            color: 'rgba(148, 163, 184, 0.08)',
                            drawBorder: false,
                            lineWidth: 1
                        },
                        ticks: {
                            color: '#94a3b8',
                            font: {
                                size: 11
                            },
                            padding: 12,
                            callback: function(value) {
                                return '$' + value.toLocaleString();
                            }
                        },
                        border: {
                            color: 'rgba(148, 163, 184, 0.15)'
                        },
                        beginAtZero: false
                    }
                }
            }
        });
    }

    updateData(curves, selectedAgents, baselineOptions = null, colorOverrides = {}, labelMap = {}) {
        if (!this.chart) {
            console.error('Chart not initialized');
            return;
        }

        if (!curves || Object.keys(curves).length === 0) {
            console.warn('No curve data to display');
            return;
        }

        // palette for datasets
        const colorPalette = [
            {
                border: '#ec4899', // magenta
                background: 'rgba(236, 72, 153, 0.1)'
            },
            {
                border: '#a855f7', // purple
                background: 'rgba(168, 85, 247, 0.1)'
            },
            {
                border: '#f97316', // orange
                background: 'rgba(249, 115, 22, 0.1)'
            },
            {
                border: '#eab308', // yellow
                background: 'rgba(234, 179, 8, 0.1)'
            },
            {
                border: '#06b6d4', // cyan
                background: 'rgba(6, 182, 212, 0.1)'
            },
            {
                border: '#3b82f6', // blue
                background: 'rgba(59, 130, 246, 0.1)'
            }
        ];

        // collect and sort all dates
        const allDates = new Set();
        Object.values(curves).forEach(curve => {
            if (curve && curve.dates) {
                curve.dates.forEach(date => allDates.add(date));
            }
        });
        const sortedDates = Array.from(allDates).sort();

        if (sortedDates.length === 0) {
            console.warn('No dates found');
            return;
        }

        const datasets = [];

        const colorOverridesMap = colorOverrides || {};

        const baselineDataset = buildBaselineDataset(baselineOptions, sortedDates);
        if (baselineDataset) {
            datasets.push(baselineDataset);
        }

        // build datasets
        let colorIndex = 0;

        selectedAgents.forEach(agentName => {
            const curve = curves[agentName];
            if (!curve || !curve.dates || !curve.values) {
                console.warn('Missing curve data for:', agentName);
                return;
            }

            // map date to value
            const valueMap = {};
            curve.dates.forEach((date, index) => {
                if (index < curve.values.length) {
                    valueMap[date] = curve.values[index];
                }
            });

            // fill values across sorted dates, forward fill missing
            const values = [];
            sortedDates.forEach((date, idx) => {
                if (valueMap[date] !== undefined) {
                    values.push(valueMap[date]);
                } else if (idx > 0 && values[idx - 1] !== null) {
                    values.push(values[idx - 1]);
                } else {
                    values.push(null);
                }
            });

            let color = colorPalette[colorIndex % colorPalette.length];
            const overrideColor = colorOverridesMap[agentName];
            if (overrideColor) {
                const rgba = hexToRgba(overrideColor, 0.12);
                color = {
                    border: overrideColor,
                    background: rgba
                };
            } else {
                color = colorPalette[colorIndex % colorPalette.length];
            }
            colorIndex += 1;

            const displayName = labelMap[agentName] || agentName;

            datasets.push({
                label: displayName,
                data: values,
                borderColor: color.border,
                backgroundColor: color.background,
                fill: false,
                borderWidth: 5,
                tension: 0.4,
                pointRadius: 0, // hide points by default
                pointHoverRadius: 6, // show point on hover
                pointHoverBorderWidth: 2,
                pointHoverBackgroundColor: color.border,
                pointHoverBorderColor: '#ffffff',
                pointBackgroundColor: color.border,
                pointBorderColor: '#ffffff',
                spanGaps: false,
                order: 1
            });
        });

        // apply updates
        this.chart.data.labels = sortedDates.map(date => {
            const parts = date.split(' ');
            if (parts.length >= 2) {
                const datePart = parts[0];
                const timePart = parts[1];
                const [year, month, day] = datePart.split('-');
                const [hour] = timePart.split(':');
                return `${month}/${day} ${hour}:00`;
            }
            return parts[0] || date;
        });
        this.chart.data.datasets = datasets;

        // toggle y-axis type
        if (this.isLogScale) {
            this.chart.options.scales.y.type = 'logarithmic';
        } else {
            this.chart.options.scales.y.type = 'linear';
        }

        // animate update
        this.chart.update('active');
        console.log('Agent Dashboard chart updated with', datasets.length, 'datasets');
    }

    toggleLogScale() {
        this.isLogScale = !this.isLogScale;
        if (this.chart) {
            this.chart.options.scales.y.type = this.isLogScale ? 'logarithmic' : 'linear';
            this.chart.update('active');
        }
        return this.isLogScale;
    }

    exportData() {
        if (!this.chart) return;

        const data = {
            labels: this.chart.data.labels,
            datasets: this.chart.data.datasets.map(ds => ({
                label: ds.label,
                data: ds.data
            }))
        };

        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'agent_comparison_data.json';
        a.click();
        URL.revokeObjectURL(url);
    }

    exportImage() {
        if (!this.chart || !this.canvas) return;

        const width = this.canvas.width;
        const height = this.canvas.height;

        const exportCanvas = document.createElement('canvas');
        exportCanvas.width = width;
        exportCanvas.height = height;
        const exportCtx = exportCanvas.getContext('2d');

        // match background to page style
        exportCtx.fillStyle = '#0f172a';
        exportCtx.fillRect(0, 0, width, height);
        exportCtx.drawImage(this.canvas, 0, 0);

        const dataUrl = exportCanvas.toDataURL('image/png', 1.0);
        const link = document.createElement('a');
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        link.href = dataUrl;
        link.download = `agent_asset_chart_${timestamp}.png`;
        link.click();
    }

    clear() {
        if (this.chart) {
            this.chart.data.labels = [];
            this.chart.data.datasets = [];
            this.chart.update();
        }
    }
}

let chartManager = null;

function initChartManager() {
    chartManager = new ChartManager('assetChart');
}
