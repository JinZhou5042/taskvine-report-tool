from .runtime_state import runtime_state, SAMPLING_POINTS, check_and_reload_data
from .utils import (
    compute_linear_tick_values,
    d3_time_formatter,
    d3_int_formatter,
    downsample_points,
    compute_points_domain
)
from flask import Blueprint, jsonify, make_response
import pandas as pd
from io import StringIO

task_retrieval_time_bp = Blueprint('task_retrieval_time', __name__, url_prefix='/api')

def get_retrieval_time_points():
    if not runtime_state.task_stats:
        return []

    return [
        [row['task_id'], row['task_waiting_retrieval_time']]
        for row in runtime_state.task_stats
        if row['task_waiting_retrieval_time'] is not None
    ]


@task_retrieval_time_bp.route('/task-retrieval-time')
@check_and_reload_data()
def get_task_retrieval_time():
    try:
        raw_points = get_retrieval_time_points()

        if not raw_points:
            return jsonify({'error': 'No task retrieval time data available'}), 404

        x_domain, y_domain = compute_points_domain(raw_points)

        return jsonify({
            'points': downsample_points(raw_points, SAMPLING_POINTS),
            'x_domain': x_domain,
            'y_domain': y_domain,
            'x_tick_values': compute_linear_tick_values(x_domain),
            'y_tick_values': compute_linear_tick_values(y_domain),
            'x_tick_formatter': d3_int_formatter(),
            'y_tick_formatter': d3_time_formatter()
        })
    except Exception as e:
        runtime_state.log_error(f"Error in get_task_retrieval_time: {e}")
        return jsonify({'error': str(e)}), 500

@task_retrieval_time_bp.route('/task-retrieval-time/export-csv')
@check_and_reload_data()
def export_task_retrieval_time_csv():
    try:
        raw_points = get_retrieval_time_points()

        if not raw_points:
            return jsonify({'error': 'No task retrieval time data available'}), 404

        df = pd.DataFrame(raw_points, columns=["Task ID", "Retrieval Time"])

        buffer = StringIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)

        response = make_response(buffer.getvalue())
        response.headers["Content-Disposition"] = "attachment; filename=task_retrieval_time.csv"
        response.headers["Content-Type"] = "text/csv"
        return response

    except Exception as e:
        runtime_state.log_error(f"Error in export_task_retrieval_time_csv: {e}")
        return jsonify({'error': str(e)}), 500