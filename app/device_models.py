"""Nested Android device JSON schemas persisted on Session rows."""

from typing import Any

from pydantic import field_validator
from sqlalchemy import JSON
from sqlalchemy.types import TypeDecorator
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel


class PydanticJSON(TypeDecorator):
    """Persist a Pydantic/SQLModel instance as a JSON column."""

    impl = JSON
    cache_ok = True

    def __init__(self, pydantic_model: type[SQLModel]) -> None:
        """Bind the decorator to a nested schema class."""
        super().__init__()
        self.pydantic_model = pydantic_model

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        """Dump nested models to JSON-compatible dicts."""
        if value is None:
            return None
        if isinstance(value, self.pydantic_model):
            return value.model_dump(mode="json")
        return self.pydantic_model.model_validate(value).model_dump(mode="json")

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        """Rehydrate nested models from JSON."""
        if value is None:
            return None
        return self.pydantic_model.model_validate(value)


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
