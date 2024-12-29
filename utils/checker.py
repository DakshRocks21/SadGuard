import magic

def check_executable(file_content: bytes) -> bool:
    """Checks if a file is an executable using its magic bytes.
    
    Args:
        file_content (bytes): A buffer containing the contents of the file

    Returns:
        bool: Whether the buffer contains an executable"""

    mime = magic.Magic(mime=True)
    file_type = mime.from_buffer(file_content)
    return 'executable' in file_type.lower()