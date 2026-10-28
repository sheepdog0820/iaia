"""Premium character portrait background-removal service."""

import os


def remove_background(image_bytes):
    """Return a PNG image with the detected background made transparent."""
    # POSIX opt-out must precede the native import; the API also protects Windows
    # and a native module already loaded by another caller in this process.
    os.environ["ORT_DISABLE_TELEMETRY"] = "1"
    import onnxruntime

    onnxruntime.disable_telemetry_events()
    from rembg import new_session, remove

    # Keep model selection stable across rembg updates and use the CPU worker.
    session = new_session("u2net", providers=["CPUExecutionProvider"])
    return remove(image_bytes, session=session)
