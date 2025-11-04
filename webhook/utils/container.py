import time
import threading
import docker
from docker import errors as docker_errors
from typing import Optional, Dict, Any, Callable
from docker.types import LogConfig

log_cfg = LogConfig(type="json-file", config={"max-size": "10m", "max-file": "3"})


def build_container(image_name: str, context_path: str, dockerfile: Optional[str] = None) -> None:
    """
    Build a Docker image from the specified context, with an optional Dockerfile override.

    Args:
        image_name (str): The tag/name for the Docker image.
        context_path (str): The path to the build context.
        dockerfile (str, optional): The relative path to the Dockerfile within the context.
    """
    client = docker.from_env()
    api = client.api
    build_kwargs = {
        'path': context_path,
        'tag': image_name,
        'rm': True,
        'platform': 'linux/amd64'
    }
    if dockerfile:
        build_kwargs['dockerfile'] = dockerfile
    client.images.build(**build_kwargs)

def run_container(
    image_name: str, 
    volume_mount: Optional[str] = None, 
    command: Optional[str] = None, 
    timeout: Optional[int] = None
) -> Dict[str, Any]:
    """
    Run a container from the specified image, optionally mounting a host directory and overriding the command.
    Enforces a timeout by stopping the container if it runs too long.

    Args:
        image_name (str): The name of the Docker image.
        volume_mount (str, optional): Host path to mount into the container at '/mnt'. If None, no volume is mounted.
        command (str, optional): The command to run inside the container.
        timeout (int, optional): Maximum number of seconds to wait for container execution.

    Returns:
        dict: A dictionary with keys "logs" (str) for the container output and "exit_code" (int) for the exit status.
    """
    client = docker.from_env()
    api = client.api
    volumes = {}
    if volume_mount:
        volumes = {volume_mount: {'bind': '/mnt', 'mode': 'rw'}}
        
    container = client.containers.run(
        image=image_name,
        command=command,
        volumes=volumes,
        remove=False,
        detach=True,
        log_config=log_cfg,
        privileged=True
    )
    
    exit_code = None
    start_time = time.time()
    try:
        while True:
            container.reload()
            if container.status in ['exited', 'dead']:
                # Retrieve the exit code from the wait result.
                wait_result = container.wait()
                exit_code = wait_result.get('StatusCode', -1)
                break
            if timeout and (time.time() - start_time) > timeout:
                container.stop()
                wait_result = container.wait()
                exit_code = wait_result.get('StatusCode', -1)
                break
            time.sleep(1)
        try:
            output = container.logs().decode('utf-8')
        except docker_errors.APIError as e:
            msg = str(e)
            if 'configured logging driver does not support reading' in msg.lower() or 'does not support reading' in msg.lower():
                # fallback to attach to capture stdout/stderr
                try:
                    pieces = []
                    for raw in api.attach(container.id, stdout=True, stderr=True, stream=True):
                        try:
                            pieces.append(raw.decode('utf-8', errors='replace'))
                        except Exception:
                            pieces.append(str(raw))
                    output = ''.join(pieces)
                except Exception:
                    output = ''
            else:
                raise
    finally:
        container.remove(force=True)
    print(output)
    return {"logs": output, "exit_code": exit_code}


def run_container_streaming(
    image_name: str,
    volume_mount: Optional[str] = None,
    command: Optional[str] = None,
    timeout: Optional[int] = None,
    logs_callback: Optional[Callable[[str], None]] = None,
    stats_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """
    Run a container and stream logs and resource stats asynchronously.

    logs_callback: called with decoded log chunk (str) as it arrives.
    stats_callback: called with a dict containing parsed stats periodically.
    """
    client = docker.from_env()
    # reuse the low-level API from the high-level client so it works on Windows (npipe) and Unix
    api = client.api

    volumes = {}
    if volume_mount:
        volumes = {volume_mount: {'bind': '/mnt', 'mode': 'rw'}}

    container = client.containers.run(
        image=image_name,
        command=command,
        volumes=volumes,
        remove=False,
        detach=True,
        log_config=log_cfg,
        privileged=True
    )

    logs_accum = []
    stop_event = threading.Event()

    def _stream_logs():
        # Primary approach: use container.logs streaming.
        try:
            for chunk in container.logs(stream=True, follow=True):
                try:
                    text = chunk.decode('utf-8', errors='replace')
                except Exception:
                    text = str(chunk)
                logs_accum.append(text)
                if logs_callback:
                    try:
                        logs_callback(text)
                    except Exception:
                        pass
                if stop_event.is_set():
                    break
            return
        except docker_errors.APIError as e:
            msg = str(e)
            # Fallback for logging driver that doesn't support /logs endpoint
            if 'configured logging driver does not support reading' in msg.lower() or 'does not support reading' in msg.lower():
                try:
                    for raw in api.attach(container.id, stdout=True, stderr=True, stream=True):
                        try:
                            text = raw.decode('utf-8', errors='replace')
                        except Exception:
                            text = str(raw)
                        logs_accum.append(text)
                        if logs_callback:
                            try:
                                logs_callback(text)
                            except Exception:
                                pass
                        if stop_event.is_set():
                            break
                except Exception:
                    # Give up silently if attach also fails
                    return
            else:
                # other API errors, bail
                return
        except Exception:
            return

    def _stream_stats():
        try:
            for stat_raw in api.stats(container.id, stream=True):
                if stop_event.is_set():
                    break
                try:
                    # stat_raw is bytes of json per line
                    import json
                    stat = json.loads(stat_raw)
                    parsed = {
                        'cpu_percent': None,
                        'mem_usage': None,
                        'mem_limit': None,
                        'net_rx': None,
                        'net_tx': None,
                    }
                    # Compute cpu percent if possible
                    cpu_stats = stat.get('cpu_stats', {})
                    precpu = stat.get('precpu_stats', {})
                    cpu_delta = cpu_stats.get('cpu_usage', {}).get('total_usage', 0) - precpu.get('cpu_usage', {}).get('total_usage', 0)
                    system_delta = cpu_stats.get('system_cpu_usage', 0) - precpu.get('system_cpu_usage', 0)
                    if system_delta > 0 and cpu_delta > 0:
                        cpu_count = cpu_stats.get('online_cpus', 1) or 1
                        parsed['cpu_percent'] = (cpu_delta / system_delta) * cpu_count * 100.0

                    mem_stats = stat.get('memory_stats', {})
                    parsed['mem_usage'] = mem_stats.get('usage')
                    parsed['mem_limit'] = mem_stats.get('limit')

                    networks = stat.get('networks') or {}
                    rx = 0
                    tx = 0
                    for iface, n in networks.items():
                        rx += n.get('rx_bytes', 0)
                        tx += n.get('tx_bytes', 0)
                    parsed['net_rx'] = rx
                    parsed['net_tx'] = tx

                    if stats_callback:
                        try:
                            stats_callback(parsed)
                        except Exception:
                            pass
                except Exception:
                    continue
        except Exception:
            pass

    logs_thread = threading.Thread(target=_stream_logs, daemon=True)
    stats_thread = threading.Thread(target=_stream_stats, daemon=True)
    logs_thread.start()
    stats_thread.start()

    exit_code = None
    start_time = time.time()
    try:
        while True:
            container.reload()
            if container.status in ['exited', 'dead']:
                wait_result = container.wait()
                exit_code = wait_result.get('StatusCode', -1)
                break
            if timeout and (time.time() - start_time) > timeout:
                container.stop()
                wait_result = container.wait()
                exit_code = wait_result.get('StatusCode', -1)
                break
            time.sleep(1)
    finally:
        stop_event.set()
        try:
            container.remove(force=True)
        except Exception:
            pass

    full_logs = ''.join(logs_accum)
    return {"logs": full_logs, "exit_code": exit_code}
