"""Safe, deterministic image discovery and loading."""

from __future__ import annotations

import os
from pathlib import Path
from typing import cast

import cv2
import numpy as np
import numpy.typing as npt

from .exceptions import DatasetValidationError

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def discover_images(directory: Path, *, recursive: bool = False) -> list[Path]:
    """Return supported regular files in stable relative-path order.

    Symlinks resolving outside the requested tree are ignored.
    """

    if not directory.exists():
        raise DatasetValidationError(f"Image directory does not exist: {directory}")
    if not directory.is_dir():
        raise DatasetValidationError(f"Image path is not a directory: {directory}")
    if not os.access(directory, os.R_OK | os.X_OK):
        raise DatasetValidationError(f"Image directory is not readable: {directory}")

    root = directory.resolve()
    iterator = directory.rglob("*") if recursive else directory.glob("*")
    images: list[Path] = []
    for path in iterator:
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS or not path.is_file():
            continue
        try:
            path.resolve().relative_to(root)
        except (OSError, ValueError):
            continue
        images.append(path)

    images.sort(key=lambda item: item.relative_to(directory).as_posix().casefold())
    if not images:
        raise DatasetValidationError(
            f"No supported images found in {directory}. "
            f"Supported extensions: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
    return images


def load_image(
    path: Path, *, max_file_size_bytes: int
) -> tuple[npt.NDArray[np.uint8], npt.NDArray[np.uint8], int]:
    """Load an image and return original pixels, grayscale pixels, and channel count."""

    try:
        size = path.stat().st_size
    except OSError as exc:
        raise DatasetValidationError(f"Cannot stat image {path.name}: {exc}") from exc
    if size > max_file_size_bytes:
        raise DatasetValidationError(
            f"Image exceeds configured {max_file_size_bytes} byte limit: {path.name}"
        )

    try:
        encoded = np.fromfile(path, dtype=np.uint8)
        image = cv2.imdecode(encoded, cv2.IMREAD_UNCHANGED)
    except (OSError, cv2.error) as exc:
        raise DatasetValidationError(f"Cannot read image {path.name}: {exc}") from exc
    if image is None or image.size == 0:
        raise DatasetValidationError(f"OpenCV could not decode image: {path.name}")

    if image.ndim == 2:
        gray = image
        channels = 1
    elif image.ndim == 3 and image.shape[2] == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        channels = 3
    elif image.ndim == 3 and image.shape[2] == 4:
        gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
        channels = 4
    else:
        shape = "x".join(str(value) for value in image.shape)
        raise DatasetValidationError(f"Unsupported channel layout ({shape}): {path.name}")
    return (
        cast(npt.NDArray[np.uint8], image),
        cast(npt.NDArray[np.uint8], gray),
        channels,
    )
