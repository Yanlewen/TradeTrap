/**
 * 数据加载器
 */
class DataLoader {
    constructor() {
        this.data = null;
        this.agents = {};
        this.config = null;
        this.datasetMeta = [];
        this.qqqCurve = null;
    }

    async load() {
        try {
            await this.loadConfig();
            const sourceUrl = this.resolveSourceUrl();
            const dataResp = await fetch(sourceUrl);
            if (!dataResp.ok) {
                throw new Error(`HTTP error! status: ${dataResp.status}`);
            }
            this.data = await dataResp.json();
            this.processData();
            return this.data;
        } catch (error) {
            console.error('加载数据失败:', error);
            throw error;
        }
    }

    async loadConfig() {
        const defaultConfig = {
            source: 'agents_data.json',
            datasets: []
        };
        try {
            const resp = await fetch('data/dataset_config.json', { cache: 'no-store' });
            if (resp.ok) {
                this.config = await resp.json();
            } else {
                this.config = defaultConfig;
            }
        } catch (err) {
            this.config = defaultConfig;
        }
        if (!Array.isArray(this.config.datasets)) {
            this.config.datasets = [];
        }
        this.datasetMeta = this.config.datasets;
    }

    resolveSourceUrl() {
        const candidates = [];
        if (this.config && this.config.source) {
            candidates.push(this.prefixDataPath(this.config.source));
        }
        candidates.push('data/agents_data.json');

        for (const url of candidates) {
            if (url) return url;
        }
        return 'data/agents_data.json';
    }

    prefixDataPath(source) {
        if (!source) return null;
        if (source.startsWith('http://') || source.startsWith('https://')) {
            return source;
        }
        if (source.startsWith('data/')) {
            return source;
        }
        return `data/${source}`;
    }

    processData() {
        if (!this.data) return;

        const allowed = this.datasetMeta.length > 0
            ? new Set(this.datasetMeta.map(meta => meta.id))
            : null;

        Object.keys(this.data).forEach(agentName => {
            if (allowed && !allowed.has(agentName)) {
                return;
            }
            const agentData = this.data[agentName];
            this.agents[agentName] = {
                name: agentName,
                dates: (agentData.dates || []).sort(),
                positions: agentData.positions || {},
                logs: agentData.logs || {},
                summary: agentData.summary || {}
            };
        });
    }

    getConfiguredAgents() {
        return Array.isArray(this.datasetMeta) ? [...this.datasetMeta] : [];
    }

    getColorOverrides() {
        const map = {};
        (this.datasetMeta || []).forEach(meta => {
            if (meta.color) {
                map[meta.id] = meta.color;
            }
        });
        return map;
    }

    getLabelMap() {
        const map = {};
        (this.datasetMeta || []).forEach(meta => {
            if (meta.id) {
                map[meta.id] = meta.label || meta.id;
            }
        });
        return map;
    }

    getAgentNames() {
        return Object.keys(this.agents);
    }

    getAgentData(agentName) {
        return this.agents[agentName] || null;
    }

    getAllDates() {
        const dates = new Set();
        Object.values(this.agents).forEach(agent => {
            agent.dates.forEach(date => dates.add(date));
        });
        return Array.from(dates).sort();
    }

    getDataByDate(date) {
        const result = {};
        Object.keys(this.agents).forEach(agentName => {
            const agent = this.agents[agentName];
            result[agentName] = {
                position: agent.positions[date] || null,
                logs: agent.logs[date] || []
            };
        });
        return result;
    }

    getAssetCurveData(agentNames) {
        const curves = {};
        
        agentNames.forEach(agentName => {
            const agent = this.agents[agentName];
            if (!agent) return;

            const dates = agent.dates;
            const values = dates.map(date => {
                const position = agent.positions[date];
                if (position) {
                    if (position.total_asset !== undefined) {
                        return position.total_asset;
                    }
                    if (position.positions) {
                        const cash = position.positions.CASH || 0;
                        return cash;
                    }
                }
                return 0;
            });

            curves[agentName] = {
                dates: dates,
                values: values
            };
        });

        return curves;
    }

    getStatistics(agentNames) {
        const stats = {
            totalAssets: {},
            returns: {},
            tradeCounts: {},
            bestAgent: null,
            bestReturn: -Infinity
        };

        agentNames.forEach(agentName => {
            const agent = this.agents[agentName];
            if (!agent) return;

            const dates = agent.dates;
            if (dates.length === 0) return;

            const lastDate = dates[dates.length - 1];
            const lastPosition = agent.positions[lastDate];
            let totalAsset = 0;
            
            if (lastPosition) {
                if (lastPosition.total_asset !== undefined) {
                    totalAsset = lastPosition.total_asset;
                } else if (lastPosition.positions) {
                    totalAsset = lastPosition.positions.CASH || 0;
                }
            }
            
            const initialCash = agent.summary.initial_cash || 5000;
            const return_rate = ((totalAsset - initialCash) / initialCash * 100).toFixed(2);
            const tradeCount = Object.values(agent.logs).reduce((sum, logs) => sum + logs.length, 0);

            stats.totalAssets[agentName] = totalAsset.toFixed(2);
            stats.returns[agentName] = return_rate;
            stats.tradeCounts[agentName] = tradeCount;

            const returnValue = parseFloat(return_rate);
            if (returnValue > stats.bestReturn) {
                stats.bestReturn = returnValue;
                stats.bestAgent = agentName;
            }
        });

        return stats;
    }
}

const dataLoader = new DataLoader();
