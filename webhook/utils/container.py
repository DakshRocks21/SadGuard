import time
import docker
from typing import Optional, Dict, Any

def build_container(image_name: str, context_path: str, dockerfile: Optional[str] = None) -> None:
    """
    Build a Docker image from the specified context, with an optional Dockerfile override.

    Args:
        image_name (str): The tag/name for the Docker image.
        context_path (str): The path to the build context.
        dockerfile (str, optional): The relative path to the Dockerfile within the context.
    """
    client = docker.from_env()
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
    volumes = {}
    if volume_mount:
        volumes = {volume_mount: {'bind': '/mnt', 'mode': 'rw'}}
        
    container = client.containers.run(
        image=image_name,
        command=command,
        volumes=volumes,
        detach=True,
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
        output = container.logs().decode('utf-8')
    finally:
        container.remove(force=True)
    print(output)
    return {"logs": output, "exit_code": exit_code}
