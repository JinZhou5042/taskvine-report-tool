import os
from pathlib import Path
from src.data_parse import DataParser
import functools
from .logger import Logger
from .utils import (
    build_response_info_string,
    build_request_info_string,
    get_files_fingerprint,
    select_best_try_per_task
)
import json
import time
import threading


LOGS_DIR = 'logs'
SAMPLING_POINTS = 100000  # at lease 3: the beginning, the end, and the global peak
SAMPLING_TASK_BARS = 100000   # how many task bars to show


class LeaseLock:
    def __init__(self, lease_duration_sec=60):
        self._lock = threading.Lock()
        self._expiry_time = 0
        self._lease_duration = lease_duration_sec

    def acquire(self):
        now = time.time()
        if self._lock.locked() and now > self._expiry_time:
            try:
                self._lock.release()
            except RuntimeError:
                pass

        if not self._lock.acquire(blocking=False):
            return False

        self._expiry_time = time.time() + self._lease_duration
        return True

    def release(self):
        if self._lock.locked():
            try:
                self._lock.release()
                self._expiry_time = 0
                return True
            except RuntimeError:
                return False
        return False

    def renew(self):
        if self._lock.locked():
            self._expiry_time = time.time() + self._lease_duration
            return True
        return False

    def is_locked(self):
        return self._lock.locked() and time.time() <= self._expiry_time

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()


def check_and_reload_data():
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            runtime_state.reload_data_if_needed()

            response = func(*args, **kwargs)

            if hasattr(response, 'get_json'):
                try:
                    response_data = response.get_json()
                except Exception:
                    response_data = None
            else:
                response_data = response

            if isinstance(response_data, (dict, list)):
                response_size = len(json.dumps(response_data)) if response_data else 0
            elif hasattr(response, 'get_data'):
                response_size = len(response.get_data())
            else:
                response_size = 0

            route_name = func.__name__
            runtime_state.log_info(f"Route {route_name} response size: {response_size/1024/1024:.2f} MB")

            return response
        return wrapper
    return decorator


class RuntimeState:
    def __init__(self):
        # full path to the runtime template
        self.runtime_template = None
        self.data_parser = None

        self.manager = None
        self.workers = None
        self.files = None
        self.tasks = None
        self.subgraphs = None

        # for storing the graph files
        self.svg_files_dir = None

        self.MIN_TIME = None
        self.MAX_TIME = None
        self.task_stats = None

        self.tick_size = 12

        # set logger
        self.logger = Logger()

        # for preventing multiple instances of the same runtime template
        self.template_lock = LeaseLock(lease_duration_sec=60)

        # for preventing multiple reloads of the data
        self._pkl_files_fingerprint = None
        self.reload_lock = LeaseLock(lease_duration_sec=180)

    @property
    def log_prefix(self):
        if self.runtime_template:
            return f"[{Path(self.runtime_template).name}]"
        else:
            return ""

    def log_info(self, message):
        self.logger.info(f"{self.log_prefix} {message}")

    def log_error(self, message):
        self.logger.error(f"{self.log_prefix} {message}")

    def log_warning(self, message):
        self.logger.warning(f"{self.log_prefix} {message}")

    def log_request(self, request):
        self.logger.info(f"{self.log_prefix} {build_request_info_string(request)}")

    def log_response(self, response, request, duration=None):
        self.logger.info(f"{self.log_prefix} {build_response_info_string(response, request, duration)}")

    def reload_data_if_needed(self):
        if not self.data_parser:
            return False
        
        if not self.data_parser.pkl_files:
            return False

        with self.reload_lock:
            if self._pkl_files_fingerprint == self._get_current_pkl_files_fingerprint():
                return False

            self.reload_template(self.runtime_template)
            return True
    
    def _get_current_pkl_files_fingerprint(self):
        if not self.data_parser or not self.data_parser.pkl_files:
            return None

        return get_files_fingerprint(self.data_parser.pkl_files)
    
    def ensure_runtime_template(self, runtime_template):
        if not runtime_template:
            return False

        if self.template_lock.is_locked():
            return False

        if runtime_template == os.path.basename(self.runtime_template):
            return True

        self.reload_template(runtime_template)
        return True
    
    def get_task_stats(self):
        # for calculating task dependents and dependencies
        output_file_to_task = {}
        for task in self.tasks.values():
            for f in task.output_files:
                output_file_to_task[f] = task.task_id
        dependency_map = {task.task_id: set() for task in self.tasks.values()}
        dependent_map = {task.task_id: set() for task in self.tasks.values()}

        for task in self.tasks.values():
            task_id = task.task_id
            for f in task.input_files:
                parent_id = output_file_to_task.get(f)
                if parent_id and parent_id != task_id:
                    dependency_map[task_id].add(parent_id)
                    dependent_map[parent_id].add(task_id)

        task_stats = []
        for task in self.tasks.values():
            task_id = task.task_id
            task_try_id = task.task_try_id

            # calculate task response time
            if task.when_running:
                task_response_time = max(round(task.when_running - task.when_ready, 2), 0.01)
            else:
                task_response_time = None

            # calculate task execution time
            if task.task_status == 0:
                task_execution_time = max(round(task.time_worker_end - task.time_worker_start, 2), 0.01)
            else:
                task_execution_time = None

            # calculate task waiting retrieval time
            if task.when_retrieved and task.when_waiting_retrieval:
                task_waiting_retrieval_time = max(round(task.when_retrieved - task.when_waiting_retrieval, 2), 0.01)
            else:
                task_waiting_retrieval_time = None

            row = {
                'task_id': task_id,
                'task_try_id': task_try_id,
                'task_response_time': task_response_time,
                'task_execution_time': task_execution_time,
                'task_waiting_retrieval_time': task_waiting_retrieval_time,
                'dependency_count': len(dependency_map[task_id]),
                'dependent_count': len(dependent_map[task_id])
            }
            task_stats.append(row)

        self.task_stats = select_best_try_per_task(task_stats)

    def reload_template(self, runtime_template):
        # init template and data parser
        self.runtime_template = os.path.join(os.getcwd(), LOGS_DIR, Path(runtime_template).name)
        self.data_parser = DataParser(self.runtime_template)

        # load data
        self.data_parser.restore_from_checkpoint()
        self.manager = self.data_parser.manager
        self.workers = self.data_parser.workers
        self.files = self.data_parser.files
        self.tasks = self.data_parser.tasks
        self.subgraphs = self.data_parser.subgraphs

        # init time range
        self.MIN_TIME = self.manager.when_first_task_start_commit
        self.MAX_TIME = self.manager.time_end

        # init task stats
        self.get_task_stats()

        # init pkl files fingerprint
        self._pkl_files_fingerprint = self._get_current_pkl_files_fingerprint()
        
        # log info
        self.log_info(f"Runtime template changed to: {runtime_template}")

        return True


runtime_state = RuntimeState()
