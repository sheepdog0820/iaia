"""Premium character portrait background-removal service."""


def remove_background(image_bytes):
    """Return a PNG image with the detected background made transparent."""
    from rembg import new_session, remove

    # Keep model selection stable across rembg updates and use the CPU worker.
    session = new_session("u2net", providers=["CPUExecutionProvider"])
    return remove(image_bytes, session=session)
