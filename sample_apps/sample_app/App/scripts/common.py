import argparse
import subprocess
import json
import logging
import random
import sys
import threading
import time
from urllib.parse import urlparse
import uvicorn
from fastapi import FastAPI, Response, Request
from fastapi.responses import JSONResponse
import os
import dns.resolver
from typing import Any, Dict, Optional

CONFIG_DIR_PATH = "/app-conn-control-info-manager-dci/"
CONFIG_FILE_NAME = "appConnectControlInfo.json"
CONFIG_FILE = CONFIG_DIR_PATH + CONFIG_FILE_NAME
SCRIPT_FILE = "/usr/local/bin/nixl_communicator"
DNS_HOST = "test-hl-svc.default.svc.cluster.local"
USE_DNS = os.getenv("USE_DNS", "false").lower() == "true"
ROLE_INITIATOR = "initiator"
ROLE_TARGET = "target"
ADDRESS_TARGET = "127.0.0.1"
PORT_TARGET = 10000
HTTP_DIR_PATH = "/work/interfaces/http/"
STATUS_FILE = HTTP_DIR_PATH + "status.json"
METRICS_FILE = HTTP_DIR_PATH + "metrics.json"
PROMETHEUS_FILE = HTTP_DIR_PATH + "prometheus.json"
HEALTH_LIVE_FILE = HTTP_DIR_PATH + "healthLive.txt"
HEALTH_READY_FILE = HTTP_DIR_PATH + "healthReady.txt"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)
else:
    logger.handlers.clear()
    logger.addHandler(handler)

app = FastAPI()
connection_flag = False

# =============================
# Port Setting
#   Default: 5000 -> Can be overridden by HTTP_PORT environment variable
#   Example: Start on port 80: export HTTP_PORT=80
#   Note: To use ports below 1024, the container user needs to be root or have CAP_NET_BIND_SERVICE capability
# =============================
try:
    HTTP_PORT = int(os.getenv("HTTP_PORT", "5000"))
except ValueError:
    HTTP_PORT = 5000

# Content-Type Policy:
#  - /status, /metrics return application/json (JSONResponse default)
#  - /metrics/prometheus returns text/plain; charset=utf-8 (explicitly set)
#  - /health*, /health/live, /health/ready omit Content-Type header
NO_CONTENT_TYPE_PATHS = {"/health", "/health/live", "/health/ready"}

# =============================
# HTTP Communication Log Middleware
# Requirements:
#  1) Request logging: URL, method, client address, request Content-Length (0 if missing)
#  2) Response logging: method, client address, request Content-Length (0 if missing),
#     response Content-Length, processing time (ms), status code, URL
# =============================
@app.middleware("http")
async def http_access_logger(request: Request, call_next):
    start = time.time()
    method = request.method
    url = str(request.url)
    client_host = request.client.host if request.client else "-"
    req_len_raw = request.headers.get("content-length", "0")
    req_len = req_len_raw if (req_len_raw.isdigit()) else "0"

    # Request log
    # Format: key=value pairs separated by spaces for easy parsing
    logger.info(
        f"[HTTP RECV] method={method} url={url} client={client_host} req_len={req_len}"
    )

    try:
        response = await call_next(request)
    except Exception as e:
        # Log processing time even when exceptions occur
        duration_ms = (time.time() - start) * 1000.0
        logger.exception(
            f"[HTTP RESP][EXCEPTION] method={method} url={url} client={client_host} req_len={req_len} duration_ms={duration_ms:.2f} error={e}"
        )
        raise

    duration_ms = (time.time() - start) * 1000.0
    # Get response Content-Length (calculate if not set)
    resp_len = response.headers.get("content-length")
    if resp_len is None:
        # FastAPI/Starlette Response may have a body attribute
        body_size = None
        if hasattr(response, "body") and response.body is not None:
            try:
                body_size = len(response.body)
            except Exception:
                body_size = None
        resp_len = str(body_size) if body_size is not None else "0"
        # Set Content-Length header explicitly for consistency
        response.headers["content-length"] = resp_len

    # Remove Content-Type header for health check endpoints
    path = request.url.path
    if path in NO_CONTENT_TYPE_PATHS:
        # Starlette Response has headers MutableMapping
        if "content-type" in response.headers:
            del response.headers["content-type"]

    status = response.status_code
    logger.info(
        f"[HTTP RESP] method={method} url={url} client={client_host} req_len={req_len} resp_len={resp_len} duration_ms={duration_ms:.2f} status={status}"
    )
    return response

# =============================
# JSON/Text File Reading Utilities
# =============================

def _convert_to_prometheus_name(name: str) -> str:
    """Convert arbitrary strings to valid Prometheus metric names."""
    import re
    import unicodedata
    
    if not name:
        return 'empty_metric'
        
    # Convert to string and handle any input type
    original_name = str(name)
    
    # Normalize Unicode characters (handle international characters)
    try:
        # Decompose and remove accents, convert to ASCII-compatible
        name = unicodedata.normalize('NFKD', original_name)
        name = ''.join(c for c in name if not unicodedata.combining(c))
    except:
        name = original_name
    
    # Convert camelCase to snake_case
    name = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name)
    
    # Handle common separators and convert to underscores
    name = re.sub(r'[\s\-\.\[\]\(\)\{\}\/:]+', '_', name)
    
    # Replace any remaining invalid characters with underscores
    # Valid Prometheus chars: a-z, A-Z, 0-9, underscore, colon (but colon has special meaning)
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    
    # Convert to lowercase
    name = name.lower()
    
    # Remove multiple consecutive underscores
    name = re.sub(r'_+', '_', name)
    
    # Remove leading/trailing underscores
    name = name.strip('_')
    
    # Ensure it starts with a letter or underscore (Prometheus requirement)
    if name and not (name[0].isalpha() or name[0] == '_'):
        name = f'metric_{name}'
    
    # Handle very long names (Prometheus recommendation: keep reasonable length)
    if len(name) > 100:
        # Keep start and end, add hash in middle for uniqueness
        import hashlib
        hash_part = hashlib.md5(name.encode()).hexdigest()[:8]
        name = f"{name[:40]}_{hash_part}_{name[-40:]}"
    
    # Ensure it's not empty after all processing
    if not name:
        # Fallback: create name from original hash
        import hashlib
        hash_fallback = hashlib.md5(original_name.encode()).hexdigest()[:12]
        name = f'metric_{hash_fallback}'
        
    return name

def _sanitize_label_value(value: Any) -> str:
    """Sanitize label values for Prometheus format with comprehensive type support."""
    if value is None:
        return "null"
    
    # Convert any type to string representation
    if isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, (list, tuple)):
        # For collections, create a summary
        if not value:
            return "empty_list"
        return f"list_len_{len(value)}"
    elif isinstance(value, dict):
        if not value:
            return "empty_dict"
        return f"dict_keys_{len(value)}"
    elif isinstance(value, set):
        if not value:
            return "empty_set"
        return f"set_len_{len(value)}"
    else:
        # Convert to string
        try:
            value_str = str(value)
        except:
            value_str = repr(type(value))
    
    if not value_str:
        return "empty"
    
    import re
    import unicodedata
    
    # Normalize Unicode and handle international characters
    try:
        value_str = unicodedata.normalize('NFKD', value_str)
        value_str = ''.join(c for c in value_str if not unicodedata.combining(c))
    except:
        pass  # Keep original if normalization fails
    
    # Limit length early to prevent processing huge strings
    if len(value_str) > 200:
        value_str = value_str[:200] + "_truncated"
    
    # Replace problematic characters with safe alternatives
    # Prometheus label values can contain any UTF-8 characters
    # But we sanitize for safety and readability
    value_str = re.sub(r'[\r\n\t]', ' ', value_str)  # Replace control chars
    value_str = re.sub(r'["\\]', '_', value_str)      # Escape problematic chars
    
    # Replace multiple spaces with single space
    value_str = re.sub(r'\s+', ' ', value_str).strip()
    
    # If still empty after processing
    if not value_str:
        return "processed_empty"
        
    return value_str

def sanitize_key(key: str) -> str:
    """Sanitize keys to handle any characters and ensure valid identifiers."""
    if not key:
        return "empty_key"
    
    # Convert to string and handle any type
    key = str(key)
    
    # Replace problematic characters for safe key names
    import re
    # Keep alphanumeric, hyphens, underscores, and dots
    key = re.sub(r'[^a-zA-Z0-9\-_.]', '_', key)
    
    # Ensure it starts with letter or underscore (for variable naming)
    if key and not (key[0].isalpha() or key[0] == '_'):
        key = f"key_{key}"
        
    # Limit length to prevent issues
    if len(key) > 100:
        key = key[:100]
        
    return key if key else "unknown_key"

def flatten_json(data: Any, prefix: str = '', separator: str = '.', max_depth: int = 50, _current_depth: int = 0, _visited: set = None) -> Dict[str, Any]:
    """Flatten nested JSON to a single-level dictionary with comprehensive support."""
    if _visited is None:
        _visited = set()
        
    result = {}
    
    # Prevent infinite recursion
    if _current_depth >= max_depth:
        logger.warning(f"Maximum depth ({max_depth}) reached, truncating at: {prefix}")
        return {prefix: f"<max_depth_reached_{type(data).__name__}>"}
    
    # Handle circular references for mutable objects
    if isinstance(data, (dict, list)) and id(data) in _visited:
        return {prefix: "<circular_reference>"}
        
    # Add current object to visited set
    if isinstance(data, (dict, list)):
        _visited.add(id(data))
    
    try:
        if isinstance(data, dict):
            # Handle empty dict
            if not data:
                result[prefix if prefix else "empty_dict"] = {}
            else:
                for key, value in data.items():
                    # Sanitize key to handle any characters
                    safe_key = sanitize_key(str(key))
                    new_key = f"{prefix}{separator}{safe_key}" if prefix else safe_key
                    result.update(flatten_json(
                        value, new_key, separator, max_depth, 
                        _current_depth + 1, _visited.copy()
                    ))
                    
        elif isinstance(data, (list, tuple)):
            # Handle empty list/tuple
            if not data:
                result[prefix if prefix else "empty_list"] = []
            else:
                for i, item in enumerate(data):
                    new_key = f"{prefix}[{i}]" if prefix else f"item[{i}]"
                    result.update(flatten_json(
                        item, new_key, separator, max_depth, 
                        _current_depth + 1, _visited.copy()
                    ))
                    
        elif isinstance(data, set):
            # Handle sets by converting to list
            data_list = list(data)
            for i, item in enumerate(data_list):
                new_key = f"{prefix}_set[{i}]" if prefix else f"set_item[{i}]"
                result.update(flatten_json(
                    item, new_key, separator, max_depth, 
                    _current_depth + 1, _visited.copy()
                ))
                
        else:
            # Primitive values (str, int, float, bool, None, etc.)
            final_key = prefix if prefix else "root_value"
            
            # Handle special types
            if hasattr(data, '__dict__'):
                # Custom objects - try to serialize their attributes
                try:
                    obj_dict = vars(data)
                    result.update(flatten_json(
                        obj_dict, f"{final_key}_attrs", separator, max_depth, 
                        _current_depth + 1, _visited.copy()
                    ))
                except:
                    result[final_key] = str(data)
            else:
                result[final_key] = data
                
    except Exception as e:
        # Robust error handling
        logger.warning(f"Error processing key '{prefix}': {e}")
        result[prefix if prefix else "error_key"] = f"<processing_error: {str(e)[:100]}>"
    
    return result

def read_json_file(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"JSON file not found: {path}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in {path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error reading {path}: {e}")
        return None

def read_text_file(path: str) -> Optional[str]:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.warning(f"Text file not found: {path}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error reading {path}: {e}")
        return None

# =============================
# Additional Endpoints
# =============================

@app.get("/status")
def get_status():
    logger.info("[Status Check] Received request")
    try:
        data = read_json_file(STATUS_FILE)
        if data is None:
            # Fallback response when file is missing
            resp = {
                "name": "No_File",
                "status": "NotReady",
                "statuses": [],
                "metas": [],
                "terminating": True
            }
        else:
            # Dynamic processing: return all data as-is, preserving structure
            # This supports any JSON structure and nesting depth
            if isinstance(data, dict):
                resp = data
            else:
                # If root is not dict, wrap it in a response structure
                resp = {"data": data}
                
        return JSONResponse(content=resp)
    except Exception as e:
        logger.error(f"[Status Check] Unexpected error: {e}")
        fallback = {
            "name": "Something_Went_Wrong",
            "status": "NotReady",
            "statuses": [],
            "metas": [],
            "terminating": True
        }
        return JSONResponse(content=fallback)

@app.get("/metrics")
def get_metrics():
    logger.info("[Metrics Check] Received request")
    try:
        data = read_json_file(METRICS_FILE)
        if data is None:
            resp = {
                "metrics": "No_File"
            }
        else:
            # Dynamic processing: flatten nested structure and return all metrics
            # Use underscore separator for metrics format
            flattened = flatten_json(data, separator='_', max_depth=100)
            
            # Convert flattened data to metrics format
            resp = {}
            for key, value in flattened.items():
                # Clean up key for metrics format
                metric_key = sanitize_key(key)
                resp[metric_key] = value
                
        return JSONResponse(content=resp)
    except Exception as e:
        logger.error(f"[Metrics Check] Unexpected error: {e}")
        fallback = {
            "metrics": "Something_Went_Wrong"
        }
        return JSONResponse(content=fallback)

@app.get("/metrics/prometheus")
def get_metrics_prometheus():

    logger.info("[Metrics/Prometheus Check] Received request")
    try:
        data = read_json_file(PROMETHEUS_FILE)
        lines = []

        if data is None or not isinstance(data, dict):
            # Fallback metrics when no data is available
            lines = [
                "# HELP app_state Application state",
                "# TYPE app_state gauge",
                'app_state{state="NotReady"} 1',
                "# HELP processing_total Total processing tasks",
                "# TYPE processing_total gauge",
                "processing_total 0",
            ]
        else:
            # Flatten nested JSON structure to handle any depth
            # Use underscore separator and higher depth limit for Prometheus
            flattened_data = flatten_json(data, separator='_', max_depth=200)
            processed_metrics = {}
            
            for key, value in flattened_data.items():
                # Convert key to valid Prometheus metric name
                metric_name = _convert_to_prometheus_name(key)
                
                if isinstance(value, str):
                    # Handle string values as labeled metrics
                    if metric_name not in processed_metrics:
                        processed_metrics[metric_name] = {
                            'type': 'gauge',
                            'help': f'{metric_name.replace("_", " ").title()}',
                            'values': {}
                        }
                    
                    # Create label-based metric (similar to app_state{state="Processing"})
                    safe_value = _sanitize_label_value(value)
                    processed_metrics[metric_name]['values'][safe_value] = 1
                    
                elif isinstance(value, (int, float)):
                    # Handle numeric values directly
                    processed_metrics[metric_name] = {
                        'type': 'gauge',
                        'help': f'{metric_name.replace("_", " ").title()}',
                        'value': float(value)
                    }
                    
                elif isinstance(value, bool):
                    # Handle boolean values as 0/1
                    processed_metrics[metric_name] = {
                        'type': 'gauge',
                        'help': f'{metric_name.replace("_", " ").title()}',
                        'value': 1.0 if value else 0.0
                    }
                    
                elif value is None:
                    # Handle null values as 0
                    processed_metrics[metric_name] = {
                        'type': 'gauge',
                        'help': f'{metric_name.replace("_", " ").title()}',
                        'value': 0.0
                    }
                # Now all nested data is flattened, so no skipping needed
                
            # Generate Prometheus format output
            for metric_name, metric_data in processed_metrics.items():
                lines.append(f"# HELP {metric_name} {metric_data['help']}")
                lines.append(f"# TYPE {metric_name} {metric_data['type']}")
                
                if 'values' in metric_data:
                    # Handle labeled metrics (string values)
                    for label_value, metric_value in metric_data['values'].items():
                        lines.append(f'{metric_name}{{state="{label_value}"}} {metric_value}')
                else:
                    # Handle direct numeric metrics
                    lines.append(f"{metric_name} {metric_data['value']}")

        body = "\n".join(lines) + "\n"
        return Response(content=body, media_type="text/plain; charset=utf-8")
        
    except Exception as e:
        logger.error(f"[Metrics/Prometheus Check] Unexpected error: {e}")
        # Minimal fallback metrics
        fallback_lines = [
            "# HELP app_state Application state",
            "# TYPE app_state gauge",
            'app_state{state="Error"} 1',
            "# HELP processing_total Total processing tasks",
            "# TYPE processing_total gauge",
            "processing_total 0",
        ]
        body = "\n".join(fallback_lines) + "\n"
        return Response(content=body, media_type="text/plain; charset=utf-8")

@app.get("/health/live")
def health_live():
    logger.info("[Health Check] /health/live")
    try:
        # Always return 200 OK for liveness probe (file existence not required)
        _ = read_text_file(HEALTH_LIVE_FILE)
        return Response(status_code=200)
    except Exception as e:
        # Additional safety check (exceptions should be handled by read_text_file)
        logger.error(f"[Health Live] Unexpected error: {e}")
        return Response(status_code=200)

@app.get("/health/ready")
def health_ready():
    logger.info("[Health Check] /health/ready")
    try:
        content = read_text_file(HEALTH_READY_FILE)
        if content == "200":
            return Response(status_code=200)
        else:
            return Response(status_code=503)
    except Exception as e:
        logger.error(f"[Health Ready] Unexpected error: {e}")
        return Response(status_code=503)

def get_rdma_link_info(netdev="net1"):
    try:
        result = subprocess.run(
            ["rdma", "link", "-j"], capture_output=True, text=True
        )
        json_output = result.stdout
        data = json.loads(json_output)

        for item in data:
            if item.get("netdev") == netdev:
                ifname = item.get("ifname")
                port = item.get("port")
                logger.info(f"RDMA ifname: {ifname}, port: {port}")
                return f"{ifname}:{port}"
        return None

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to execute rdma link command: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return None

def parse_args():
    parser = argparse.ArgumentParser(
        description="Specify memory type: VRAM or DRAM, and operation: READ or WRITE"
    )
    parser.add_argument(
        "memory_type",
        choices=["VRAM", "DRAM"],
        help="The memory type must be either 'VRAM' or 'DRAM'."
    )
    parser.add_argument(
        "operation",
        choices=["READ", "WRITE"],
        help="The operation must be either 'READ' or 'WRITE'."
    )
    return parser.parse_args()

def print_json_elements(obj, indent=0):
    indent_str = "  " * indent
    if isinstance(obj, dict):
        for key, value in obj.items():
            logger.info(f"{indent_str}Key: {key}")
            print_json_elements(value, indent + 1)
    elif isinstance(obj, list):
        for index, item in enumerate(obj):
            logger.info(f"{indent_str}Index: {index}")
            print_json_elements(item, indent + 1)
    else:
        logger.info(f"{indent_str}Value: {obj}, Type: {type(obj)}")

def load_config():
    """Load configuration file"""
    logger.info("Loading config file: " + CONFIG_FILE)
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {}

def resolve_dns():
    """Resolve IP addresses from DNS"""
    try:
        resolver = dns.resolver.Resolver()
        answers = resolver.resolve(DNS_HOST, 'A')
        return [rdata.address for rdata in answers]
    except Exception as e:
        logger.error(f"Failed to resolve DNS: {e}")
        return []

def wait_random_seconds(min_sec: int = 1, max_sec: int = 10):
    if min_sec > max_sec:
        raise ValueError("min_sec cannot be greater than max_sec")

    wait_sec = random.randint(min_sec, max_sec)
    logger.info(f"Waiting for {wait_sec} seconds before running client script.")
    time.sleep(wait_sec)
    return wait_sec

def watch_stderr(stderr, proc):
    for line in iter(stderr.readline, b''):
        decoded = line.decode(errors="replace")
        sys.stderr.write(decoded)
        if "error" in decoded:
            logger.error(f"Detected error in server stderr: {decoded.strip()}")
            proc.terminate()
            break
    stderr.close()

def run_server_script(args):
    """
    Run the server script as a subprocess in server mode.
    """

    rdma_dev = get_rdma_link_info()
    if rdma_dev is None:
        logger.error("RDMA device is None. Exiting run_server_script.")
        return None

    cmd = [
        SCRIPT_FILE,
        ROLE_TARGET,
        ADDRESS_TARGET,
        str(PORT_TARGET),
        args.memory_type,
        args.operation
    ]
    env = os.environ.copy()
    env["UCX_NET_DEVICES"] = rdma_dev
    env["UCX_TLS"] = "rc,cuda_copy"
    logger.info(
        f"Executing: {' '.join(cmd)} with UCX_NET_DEVICES={rdma_dev}, "
        "UCX_TLS=rc,cuda_copy"
    )
    try:
        server_process = subprocess.Popen(
            cmd,
            env=env,
            stderr=subprocess.PIPE,
            stdout=sys.stdout)

        threading.Thread(
            target=watch_stderr, args=(
                server_process.stderr, server_process
            ), daemon=True
        ).start()

        return server_process
    except Exception as e:
        logger.error(f"Failed to start server script: {e}")
        return None

def run_client_script(server_ip, client_ip, rdma_dev, args):
    """
    Run the client script as a subprocess in client mode.
    """

    wait_random_seconds()

    cmd = [
        SCRIPT_FILE,
        ROLE_INITIATOR,
        server_ip,
        str(PORT_TARGET),
        args.memory_type,
        args.operation,
        client_ip
    ]

    env = os.environ.copy()
    env["UCX_NET_DEVICES"] = rdma_dev
    env["UCX_TLS"] = "rc,cuda_copy"

    max_retries = 3
    for attempt in range(max_retries):
        logger.info(
            f"Executing[{attempt}]: {' '.join(cmd)} with UCX_NET_DEVICES={rdma_dev}, "
            "UCX_TLS=rc,cuda_copy"
        )
        try:
            subprocess.run(cmd, env=env, check=True, timeout=10)
            break
        except subprocess.TimeoutExpired:
            logger.error("Client script timed out. Killing process and retrying...")
            wait_random_seconds()
        except subprocess.CalledProcessError as e:
            logger.error(f"Client script failed: {e}")
            wait_random_seconds()
    else:
        logger.error("Client script failed after maximum retries.")

def run_input_sock_script(parsed, args):
    """
    Run the input script as a subprocess in client mode.
    """

    if parsed.scheme == "tcp":
        cmd = ["iperf3", "-c", parsed.hostname, "-p", f"{parsed.port}", "-R", "-t", "1"]
    else:
        cmd = ["iperf3", "-c", parsed.hostname, "-u", "-p", f"{parsed.port}", "-R", "-t", "1"]

    env = os.environ.copy()

    max_retries = 9
    for attempt in range(max_retries):
        logger.info(f"Input script[{attempt}]: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, env=env, check=True, timeout=10)
            break
        except subprocess.TimeoutExpired:
            logger.error("Input script timed out. Killing process and retrying...")
            time.sleep(1)
        except subprocess.CalledProcessError as e:
            logger.error(f"Input script failed: {e}")
            time.sleep(1)
    else:
        logger.error("Input script failed after maximum retries.")

def run_output_sock_script(parsed, args):
    """
    Run the outinput script as a subprocess in client mode.
    """

    if parsed.scheme == "tcp":
        cmd = ["iperf3", "-c", parsed.hostname, "-p", f"{parsed.port}", "-n", "3K"]
    else:
        cmd = ["iperf3", "-c", parsed.hostname, "-u", "-p", f"{parsed.port}", "-n", "3K"]

    env = os.environ.copy()

    max_retries = 9
    for attempt in range(max_retries):
        logger.info(f"Output script[{attempt}]: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, env=env, check=True, timeout=10)
            break
        except subprocess.TimeoutExpired:
            logger.error("Output script timed out. Killing process and retrying...")
            time.sleep(1)
        except subprocess.CalledProcessError as e:
            logger.error(f"Output script failed: {e}")
            time.sleep(1)
    else:
        logger.error("Output script failed after maximum retries.")

def extract_processing_addresses(config):
    """
    Extract all addresses from config 
    where status.status is "PROCESSING" or "IDLE".
    """

    addresses = []
    get_services = config.get('services', {})
    if [] == get_services:
        logger.warning("services list is an empty.")
    elif None == get_services:
        logger.warning("services is not found.")
    else:
        for service_item in get_services:
            if {} == service_item:
                logger.warning("services is an empty dictionary.")
                continue

            get_destinations = service_item.get('destinations', {})
            if [] == get_destinations:
                logger.warning("destinations list is an empty.")
            elif None == get_destinations:
                logger.warning("destinations is not found.")
            else:
                for destination in get_destinations:
                    if {} == destination:
                        logger.warning("destinations is an empty dictionary.")
                        continue

                    get_status = destination.get('status', {})
                    if {} == get_status:
                        logger.warning("status is an empty dictionary.")
                    elif None == get_status:
                        logger.warning("status is not found.")
                    else:
                        if get_status.get('status') in ('PROCESSING', 'IDLE'):
                            address = destination.get('address')
                            if  None == address:
                                logger.warning("address is not found.")
                            else:
                                addresses.append(address)
    return addresses

def wait_for_signal_and_connect_to_target(args):
    """Wait for SIGHUP signal and connect to target"""

    global connection_flag
    logger.info("Starting wait_for_signal_and_connect_to_target.")

    while True:
        if connection_flag:

            connection_flag = False
            client_ip = ""

            if USE_DNS:
                logger.info(
                    "SIGHUP received. Using DNS to resolve server addresses."
                )
                server_ips = resolve_dns()
            else:
                logger.info(
                    "SIGHUP received. Reloading config and starting client..."
                )
                config = load_config()
                server_ips = extract_processing_addresses(config)
                client_ip = config.get('address')
                input_subsets = config.get("inputSubsets")
                output_subsets = config.get("outputSubsets")

            if input_subsets is not None:
                for index, input_subset in enumerate(input_subsets):
                    logger.info("inputsubsets[%d]: input_subset: %s", index, input_subset)
                    parsed = urlparse(input_subset)
                    if parsed is not None:
                        if parsed.hostname is not None:
                            logger.info("inputsubsets[%d]: hostname: %s", index, parsed.hostname)
                            if parsed.port is not None:
                                logger.info("inputsubsets[%d]: port: %d", index, parsed.port)
                                if parsed.scheme is not None:
                                    logger.info("inputsubsets[%d]: scheme: %s", index, parsed.scheme)
                                    if parsed.scheme == "tcp" or parsed.scheme == "udp":
                                        run_input_sock_script(parsed, args)
            else:
                logger.info("inputsubsets is None")

            if client_ip is not None:
                logger.info("Current server_ips: %s", server_ips)
                logger.info("Current client_ip: %s", client_ip)
                rdma_dev = get_rdma_link_info()
                if rdma_dev is None:
                    logger.info("RDMA device is None.")
                else:
                    if server_ips:
                   	     for server_ip in server_ips:
                   	         run_client_script(server_ip, client_ip, rdma_dev, args)
            else:
                logger.error("Missing client_ip in appConnectControlInfo.json.")

            if output_subsets is not None:
                for index, output_subset in enumerate(output_subsets):
                    logger.info("outputsubsets[%d]: output_subset: %s", index, output_subset)
                    parsed = urlparse(output_subset)
                    if parsed is not None:
                        if parsed.hostname is not None:
                            logger.info("outputsubsets[%d]: hostname: %s", index, parsed.hostname)
                            if parsed.port is not None:
                                logger.info("outputsubsets[%d]: port: %d", index, parsed.port)
                                if parsed.scheme is not None:
                                    logger.info("outputsubsets[%d]: scheme: %s", index, parsed.scheme)
                                    if parsed.scheme == "tcp" or parsed.scheme == "udp":
                                        run_output_sock_script(parsed, args)
            else:
                logger.info("outputsubsets is None")

            logger.info("Waiting for SIGHUP signal... in wait_for_signal_and_connect_to_target")
        else:
            time.sleep(1)

def handle_sighup(signum, frame):
    """Handler for SIGHUP signal"""

    global connection_flag

    connection_flag = True
    config = load_config()
    print_json_elements(config)

def start_fastapi_app():
    """Start FastAPI app in background thread"""
    uvicorn.run(app, host="0.0.0.0", port=HTTP_PORT, log_level="warning")
