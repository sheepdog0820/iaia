"""Premium character portrait background-removal service."""


def remove_background(image_bytes):
    """Return a PNG image with the detected background made transparent."""
    from rembg import remove

    return remove(image_bytes)
