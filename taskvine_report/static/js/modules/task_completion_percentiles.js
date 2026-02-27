import { BaseModule } from './base.js';

export class TaskCompletionPercentilesModule extends BaseModule {
    constructor(id, title, api_url) {
        super(id, title, api_url);
        this.setBottomScaleType('linear');
        this.setLeftScaleType('band');
    }

    plot() {
        if (!this.data) return;

        const yHeight = this.leftScale.bandwidth() * 0.8;
        const xFormatter = eval(this.data['x_tick_formatter']);

        this.data['points'].forEach(([time, percentile]) => {
            const innerHTML = `Time: ${xFormatter(time)}<br>Percentile: ${percentile}%`;
            this.plotHorizontalRect(0, time, percentile, yHeight, 'steelblue', 1, innerHTML);
        });
    }
} 