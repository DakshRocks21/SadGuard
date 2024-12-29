import docker

def build_container(image_name: str, context_path: str) -> None:
    """Wrapper around the `docker build` command. Takes in and image name and context path
    and builds a docker container for future execution.
    
    Args:
        image_name (str): The name of the Docker image.
        context_path (str): The path to the `Dockerfile`"""

    client = docker.from_env()
    client.images.build(path=context_path, tag=image_name, rm=True, platform='linux/amd64')

def run_container(image_name: str, volume_mount: str) -> str:
    """Wrapper around the `docker run` command. Takes in an image name to run
    and returns the output of the container execution.
    
    Args:
        image_name (str): The name of the Docker image.
        volume_mount (str): The path to the volume mount.

    Returns:
        str: The output of the container execution.
    """

    client = docker.from_env()
    container = client.containers.run(image_name, volumes={volume_mount: {'bind': '/mnt', 'mode': 'rw'}}, detach=True)
    
    container.wait()
    output = container.logs().decode('utf-8')

    container.remove()
    return output
