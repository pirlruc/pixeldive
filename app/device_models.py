"""Nested Android device JSON schemas persisted on Session rows."""

from typing import Self

from pydantic import field_validator, model_validator
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel

from app.json_columns import PydanticJSON

__all__ = [
    "CameraCapabilities",
    "CameraInfo",
    "PhoneCapabilities",
    "PhoneInfo",
    "PydanticJSON",
]


class PhoneInfo(SQLModel):
    """Android ``Build.*`` identity collected by capture clients."""

    manufacturer: str = SQLField(description="android.os.Build.MANUFACTURER")
    model: str = SQLField(description="android.os.Build.MODEL")
    brand: str = SQLField(description="android.os.Build.BRAND")
    device: str = SQLField(description="android.os.Build.DEVICE")
    board: str = SQLField(description="android.os.Build.BOARD")
    android_version: str = SQLField(description="android.os.Build.VERSION.RELEASE")
    sdk_int: int = SQLField(description="android.os.Build.VERSION.SDK_INT")


class PhoneCapabilities(SQLModel):
    """Device RAM, CPU, and display metrics from ActivityManager/DisplayMetrics."""

    total_ram_mb: int = SQLField(description="ActivityManager.MemoryInfo.totalMem")
    available_ram_mb: int = SQLField(description="ActivityManager.MemoryInfo.availMem")
    cpu_abi: str = SQLField(description="Build.SUPPORTED_ABIS[0] or joined ABIs")
    cpu_cores: int = SQLField(description="Runtime.getRuntime().availableProcessors()")
    screen_width_px: int = SQLField(description="DisplayMetrics.widthPixels")
    screen_height_px: int = SQLField(description="DisplayMetrics.heightPixels")
    screen_density_dpi: int = SQLField(description="DisplayMetrics.densityDpi")
    is_low_ram_device: bool = SQLField(
        default=False,
        description="ActivityManager.isLowRamDevice()",
    )


class CameraInfo(SQLModel):
    """One Camera2 ``cameraId`` and its ``CameraCharacteristics``."""

    camera_id: str
    lens_facing: str
    hardware_level: str
    sensor_orientation: int
    max_resolution: str
    has_flash: bool
    has_optical_stabilization: bool
    supported_capabilities: list[str] = SQLField(default_factory=list)


class CameraCapabilities(SQLModel):
    """Camera2 enumeration payload for the capturing device."""

    camera_count: int = 0
    cameras: list[CameraInfo] = SQLField(default_factory=list)

    @field_validator("camera_count")
    @classmethod
    def _non_negative(cls, value: int) -> int:
        """Reject a negative camera count."""
        if value < 0:
            msg = "camera_count must be >= 0"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _count_matches_cameras(self) -> Self:
        """Require camera_count to equal the enumerated cameras list (API-002)."""
        if self.camera_count != len(self.cameras):
            msg = "camera_count must equal len(cameras)"
            raise ValueError(msg)
        return self
