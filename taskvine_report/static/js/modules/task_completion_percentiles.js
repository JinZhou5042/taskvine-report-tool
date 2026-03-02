import { BaseModule } from './base.js';

export class TaskCompletionPercentilesModule extends BaseModule {
    constructor(id, title, api_url) {
        super(id, title, api_url);
        this.setBottomScaleType('linear');
        this.setLeftScaleType('linear');
    }

    plot() {
        if (!this.data) return;

        this.plotPath(this.data.points, {
            stroke: '#2077B4',
            strokeWidth: 1.5,
            className: 'task-completion-percentiles-path',
            id: `${this.id}-path`,
        });
    }
} 