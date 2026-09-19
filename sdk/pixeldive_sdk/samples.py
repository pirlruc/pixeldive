"""Sample Android-shaped session payloads used by the SDK and demo app."""

from __future__ import annotations

from typing import Any


def sample_session_payload(session_name: str = "demo-capture") -> dict[str, Any]:
    """Return a Pixel-like create-session JSON body."""
    return {
        "session_name": session_name,
        "phone_info": {
            "manufacturer": "Google",
            "model": "Pixel 8",
            "brand": "google",
            "device": "shiba",
            "board": "shiba",
            "android_version": "14",
            "sdk_int": 34,
        },
        "phone_capabilities": {
            "total_ram_mb": 8192,
            "available_ram_mb": 4096,
            "cpu_abi": "arm64-v8a",
            "cpu_cores": 8,
            "screen_width_px": 1080,
            "screen_height_px": 2400,
            "screen_density_dpi": 420,
            "is_low_ram_device": False,
        },
        "camera_capabilities": {
            "camera_count": 2,
            "cameras": [
                {
                    "camera_id": "0",
                    "lens_facing": "BACK",
                    "hardware_level": "LEVEL_3",
                    "sensor_orientation": 90,
                    "max_resolution": "4080x3072",
                    "has_flash": True,
                    "has_optical_stabilization": True,
                    "supported_capabilities": ["BACKWARD_COMPATIBLE", "RAW"],
                },
                {
                    "camera_id": "1",
                    "lens_facing": "FRONT",
                    "hardware_level": "LIMITED",
                    "sensor_orientation": 270,
                    "max_resolution": "3264x2448",
                    "has_flash": False,
                    "has_optical_stabilization": False,
                    "supported_capabilities": ["BACKWARD_COMPATIBLE"],
                },
            ],
        },
        "metadata": {"source": "pixeldive-demo"},
    }
