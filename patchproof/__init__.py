"""patchproof -- detect 9-slice borders of UI panels, prove them by
resynthesis, and export real engine files (Unity .meta, Godot .tres,
Android .9.png)."""

from .core import Detection, detect, render_9slice

__version__ = "0.1.0"
__all__ = ["Detection", "detect", "render_9slice", "__version__"]
