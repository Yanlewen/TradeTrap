/**
 * 数据加载器
 */
class DataLoader {
    constructor() {
        this.data = null;
        this.agents = {};
    }

    async load() {
        try {
            const response = await fetch('data/agents_data.json');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            this.data = await response.json();
            this.processData();
            return this.data;
        } catch (error) {
            console.error('加载数据失败:', error);
            throw error;
        }
    }

    processData() {
        if (!this.data) return;

        Object.keys(this.data).forEach(agentName => {
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
