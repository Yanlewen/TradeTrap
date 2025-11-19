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
        this.baselineMeta = null;
        this.baselineCurve = null;
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
            await this.prepareBaseline();
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
            const resp = await fetch(this.withCacheBuster('data/dataset_config.json'), { cache: 'no-store' });
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
            if (url) return this.withCacheBuster(url);
        }
        return this.withCacheBuster('data/agents_data.json');
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

    withCacheBuster(url) {
        if (!url) return url;
        const separator = url.includes('?') ? '&' : '?';
        return `${url}${separator}_=${Date.now()}`;
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

    getBaselineOptions() {
        return {
            meta: this.baselineMeta,
            curve: this.baselineCurve
        };
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
            const positions = agent.positions;
            
            // 构建一个辅助函数来查找position值
            const getPositionValue = (date) => {
                // 首先尝试精确匹配
                let position = positions[date];
                if (position) {
                    if (position.total_asset !== undefined) {
                        return position.total_asset;
                    }
                    if (position.positions) {
                        const cash = position.positions.CASH || 0;
                        return cash;
                    }
                }
                
                // 如果找不到精确匹配，尝试查找相同日期前缀的最近一个position
                const datePrefix = date.split(' ')[0];
                const matchingDates = Object.keys(positions)
                    .filter(d => d.startsWith(datePrefix))
                    .sort();
                
                if (matchingDates.length > 0) {
                    // 找到相同日期前缀的所有positions，选择最接近的一个
                    // 如果当前时间早于所有匹配的时间，使用第一个
                    // 如果当前时间晚于所有匹配的时间，使用最后一个
                    const currentTime = date.includes(' ') ? date.split(' ')[1] : '';
                    let bestMatch = null;
                    
                    if (currentTime) {
                        // 找到最接近的时间点
                        for (const matchDate of matchingDates) {
                            if (matchDate <= date) {
                                bestMatch = matchDate;
                            } else {
                                break;
                            }
                        }
                        // 如果没有找到更早的，使用第一个匹配的
                        if (!bestMatch && matchingDates.length > 0) {
                            bestMatch = matchingDates[0];
                        }
                    } else {
                        // 如果没有时间部分，使用最后一个匹配的
                        bestMatch = matchingDates[matchingDates.length - 1];
                    }
                    
                    if (bestMatch) {
                        position = positions[bestMatch];
                        if (position) {
                            if (position.total_asset !== undefined) {
                                return position.total_asset;
                            }
                            if (position.positions) {
                                const cash = position.positions.CASH || 0;
                                return cash;
                            }
                        }
                    }
                }
                
                return null; // 返回null而不是0，让前端处理
            };
            
            // 使用前向填充策略
            const values = [];
            let lastValue = null;
            
            dates.forEach(date => {
                const value = getPositionValue(date);
                if (value !== null && value !== undefined) {
                    lastValue = value;
                    values.push(value);
                } else if (lastValue !== null) {
                    // 前向填充：使用最后一个有效值
                    values.push(lastValue);
                } else {
                    // 如果还没有有效值，返回null
                    values.push(null);
                }
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

    async prepareBaseline() {
        const defaultBaseline = {
            type: 'constant',
            value: 5000,
            label: 'Initial Balance ($5,000)',
            color: '#64748b'
        };

        const meta = (this.config && this.config.baseline !== undefined)
            ? this.config.baseline
            : defaultBaseline;

        if (!meta || meta.type === 'none') {
            this.baselineMeta = null;
            this.baselineCurve = null;
            console.log('Baseline disabled');
            return;
        }

        this.baselineMeta = { ...defaultBaseline, ...meta };
        const type = (this.baselineMeta.type || 'constant').toLowerCase();
        console.log('Preparing baseline:', this.baselineMeta);

        if (type === 'price_series') {
            await this.loadBaselineCurve(this.baselineMeta);
            console.log('Baseline curve points:', this.baselineCurve ? this.baselineCurve.dates.length : 0);
        } else {
            this.baselineCurve = null;
        }
    }

    async loadBaselineCurve(meta) {
        try {
            const sourcePath = this.prefixDataPath(meta.source);
            if (!sourcePath) {
                this.baselineCurve = null;
                return;
            }
            const resp = await fetch(this.withCacheBuster(sourcePath), { cache: 'no-store' });
            if (!resp.ok) {
                console.warn(`Baseline source ${sourcePath} failed: ${resp.status}`);
                this.baselineCurve = null;
                return;
            }
            const payload = await resp.json();
            this.baselineCurve = this.processBaselinePayload(payload, meta);
        } catch (err) {
            console.warn('Failed to load baseline curve:', err);
            this.baselineCurve = null;
        }
    }

    processBaselinePayload(payload, meta) {
        if (!payload) return null;
        let entries = [];

        if (payload['Time Series (60min)']) {
            entries = Object.entries(payload['Time Series (60min)']).map(([date, values]) => ({
                date,
                close: parseFloat(values['4. close'] || values['4. Close'] || values['close'])
            }));
        } else if (payload['Time Series (Daily)']) {
            entries = Object.entries(payload['Time Series (Daily)']).map(([date, values]) => ({
                date,
                close: parseFloat(values['4. close'] || values['4. Close'] || values['close'])
            }));
        } else if (payload.dates && payload.values) {
            entries = payload.dates.map((date, idx) => ({
                date,
                close: parseFloat(payload.values[idx])
            }));
        } else if (Array.isArray(payload)) {
            entries = payload.map(entry => ({
                date: entry.date || entry.timestamp || entry[0],
                close: parseFloat(entry.close || entry.value || entry[1])
            }));
        } else {
            entries = Object.entries(payload).map(([date, value]) => ({
                date,
                close: typeof value === 'number' ? value : parseFloat(value.close || value)
            }));
        }

        entries = entries
            .filter(item => item.date && !Number.isNaN(item.close))
            .sort((a, b) => new Date(a.date) - new Date(b.date));

        if (!entries.length) return null;

        const initialCapital = meta.initial_capital || meta.initialCapital || 5000;
        const initialPrice = entries[0].close;
        const dates = [];
        const values = [];
        entries.forEach(item => {
            dates.push(item.date);
            values.push(initialCapital * (item.close / initialPrice));
        });

        return {
            label: meta.label || 'Benchmark',
            color: meta.color || '#64748b',
            dates,
            values
        };
    }
}

const dataLoader = new DataLoader();
