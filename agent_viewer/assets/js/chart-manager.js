/**
 * 图表管理器 - 美化版
 */
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
                    mode: 'nearest', // 只显示最近的一条曲线
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
                                size: 13,
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
                        mode: 'nearest', // 关键：只显示最近的一条曲线
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
                                // 显示时间
                                return context[0].label;
                            },
                            label: function(context) {
                                // 只显示当前曲线的信息
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

    updateData(curves, selectedAgents) {
        if (!this.chart) {
            console.error('Chart not initialized');
            return;
        }

        if (!curves || Object.keys(curves).length === 0) {
            console.warn('No curve data to display');
            return;
        }

        // 美化配色方案
        const colorPalette = [
            {
                border: '#ec4899', // 洋红色
                background: 'rgba(236, 72, 153, 0.1)'
            },
            {
                border: '#a855f7', // 紫色
                background: 'rgba(168, 85, 247, 0.1)'
            },
            {
                border: '#f97316', // 橙色
                background: 'rgba(249, 115, 22, 0.1)'
            },
            {
                border: '#eab308', // 黄色
                background: 'rgba(234, 179, 8, 0.1)'
            },
            {
                border: '#06b6d4', // 青色
                background: 'rgba(6, 182, 212, 0.1)'
            },
            {
                border: '#3b82f6', // 蓝色
                background: 'rgba(59, 130, 246, 0.1)'
            }
        ];

        // 获取所有日期并排序
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

        // 准备数据集
        const datasets = [];
        let colorIndex = 0;

        selectedAgents.forEach(agentName => {
            const curve = curves[agentName];
            if (!curve || !curve.dates || !curve.values) {
                console.warn('Missing curve data for:', agentName);
                return;
            }

            // 创建日期到值的映射
            const valueMap = {};
            curve.dates.forEach((date, index) => {
                if (index < curve.values.length) {
                    valueMap[date] = curve.values[index];
                }
            });

            // 为所有日期生成值，处理缺失数据
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

            const color = colorPalette[colorIndex % colorPalette.length];
            colorIndex++;

            // 创建更明确的agent名称映射
            const agentNameMap = {
                'deepseek-v3-whole-month': '基础版本 (无工具)',
                'deepseek-v3-whole-month-with-x-and-reddit': '含 X & Reddit 工具',
                'deepseek-v3-whole-month-with-x-and-reddit-1105': '含 X & Reddit 工具 (1105版)'
            };
            
            // 使用映射表，如果没有则使用简化名称
            const displayName = agentNameMap[agentName] || agentName.split('-').slice(-2).join('-').replace(/-/g, ' ');

            datasets.push({
                label: displayName,
                data: values,
                borderColor: color.border,
                backgroundColor: color.background,
                fill: false,
                borderWidth: 2.5,
                tension: 0.4,
                pointRadius: 0, // 默认完全不显示数据点
                pointHoverRadius: 8, // 悬停时才显示点
                pointHoverBorderWidth: 3,
                pointHoverBackgroundColor: color.border,
                pointHoverBorderColor: '#ffffff',
                pointBackgroundColor: color.border,
                pointBorderColor: '#ffffff',
                spanGaps: false
            });
        });

        // 更新图表
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

        // 更新y轴类型
        if (this.isLogScale) {
            this.chart.options.scales.y.type = 'logarithmic';
        } else {
            this.chart.options.scales.y.type = 'linear';
        }

        // 动画更新
        this.chart.update('active');
        console.log('Chart updated with', datasets.length, 'datasets');
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
