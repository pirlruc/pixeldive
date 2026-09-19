from google.protobuf import struct_pb2 as _struct_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class PhoneInfo(_message.Message):
    __slots__ = ("manufacturer", "model", "brand", "device", "board", "android_version", "sdk_int")
    MANUFACTURER_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    BRAND_FIELD_NUMBER: _ClassVar[int]
    DEVICE_FIELD_NUMBER: _ClassVar[int]
    BOARD_FIELD_NUMBER: _ClassVar[int]
    ANDROID_VERSION_FIELD_NUMBER: _ClassVar[int]
    SDK_INT_FIELD_NUMBER: _ClassVar[int]
    manufacturer: str
    model: str
    brand: str
    device: str
    board: str
    android_version: str
    sdk_int: int
    def __init__(self, manufacturer: _Optional[str] = ..., model: _Optional[str] = ..., brand: _Optional[str] = ..., device: _Optional[str] = ..., board: _Optional[str] = ..., android_version: _Optional[str] = ..., sdk_int: _Optional[int] = ...) -> None: ...

class PhoneCapabilities(_message.Message):
    __slots__ = ("total_ram_mb", "available_ram_mb", "cpu_abi", "cpu_cores", "screen_width_px", "screen_height_px", "screen_density_dpi", "is_low_ram_device")
    TOTAL_RAM_MB_FIELD_NUMBER: _ClassVar[int]
    AVAILABLE_RAM_MB_FIELD_NUMBER: _ClassVar[int]
    CPU_ABI_FIELD_NUMBER: _ClassVar[int]
    CPU_CORES_FIELD_NUMBER: _ClassVar[int]
    SCREEN_WIDTH_PX_FIELD_NUMBER: _ClassVar[int]
    SCREEN_HEIGHT_PX_FIELD_NUMBER: _ClassVar[int]
    SCREEN_DENSITY_DPI_FIELD_NUMBER: _ClassVar[int]
    IS_LOW_RAM_DEVICE_FIELD_NUMBER: _ClassVar[int]
    total_ram_mb: int
    available_ram_mb: int
    cpu_abi: str
    cpu_cores: int
    screen_width_px: int
    screen_height_px: int
    screen_density_dpi: int
    is_low_ram_device: bool
    def __init__(self, total_ram_mb: _Optional[int] = ..., available_ram_mb: _Optional[int] = ..., cpu_abi: _Optional[str] = ..., cpu_cores: _Optional[int] = ..., screen_width_px: _Optional[int] = ..., screen_height_px: _Optional[int] = ..., screen_density_dpi: _Optional[int] = ..., is_low_ram_device: bool = ...) -> None: ...

class CameraInfo(_message.Message):
    __slots__ = ("camera_id", "lens_facing", "hardware_level", "sensor_orientation", "max_resolution", "has_flash", "has_optical_stabilization", "supported_capabilities")
    CAMERA_ID_FIELD_NUMBER: _ClassVar[int]
    LENS_FACING_FIELD_NUMBER: _ClassVar[int]
    HARDWARE_LEVEL_FIELD_NUMBER: _ClassVar[int]
    SENSOR_ORIENTATION_FIELD_NUMBER: _ClassVar[int]
    MAX_RESOLUTION_FIELD_NUMBER: _ClassVar[int]
    HAS_FLASH_FIELD_NUMBER: _ClassVar[int]
    HAS_OPTICAL_STABILIZATION_FIELD_NUMBER: _ClassVar[int]
    SUPPORTED_CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    camera_id: str
    lens_facing: str
    hardware_level: str
    sensor_orientation: int
    max_resolution: str
    has_flash: bool
    has_optical_stabilization: bool
    supported_capabilities: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, camera_id: _Optional[str] = ..., lens_facing: _Optional[str] = ..., hardware_level: _Optional[str] = ..., sensor_orientation: _Optional[int] = ..., max_resolution: _Optional[str] = ..., has_flash: bool = ..., has_optical_stabilization: bool = ..., supported_capabilities: _Optional[_Iterable[str]] = ...) -> None: ...

class CameraCapabilities(_message.Message):
    __slots__ = ("camera_count", "cameras")
    CAMERA_COUNT_FIELD_NUMBER: _ClassVar[int]
    CAMERAS_FIELD_NUMBER: _ClassVar[int]
    camera_count: int
    cameras: _containers.RepeatedCompositeFieldContainer[CameraInfo]
    def __init__(self, camera_count: _Optional[int] = ..., cameras: _Optional[_Iterable[_Union[CameraInfo, _Mapping]]] = ...) -> None: ...

class Session(_message.Message):
    __slots__ = ("id", "session_name", "status", "created_at", "updated_at", "phone_info", "phone_capabilities", "camera_capabilities", "metadata")
    ID_FIELD_NUMBER: _ClassVar[int]
    SESSION_NAME_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    PHONE_INFO_FIELD_NUMBER: _ClassVar[int]
    PHONE_CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    CAMERA_CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    id: str
    session_name: str
    status: str
    created_at: _timestamp_pb2.Timestamp
    updated_at: _timestamp_pb2.Timestamp
    phone_info: PhoneInfo
    phone_capabilities: PhoneCapabilities
    camera_capabilities: CameraCapabilities
    metadata: _struct_pb2.Struct
    def __init__(self, id: _Optional[str] = ..., session_name: _Optional[str] = ..., status: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., phone_info: _Optional[_Union[PhoneInfo, _Mapping]] = ..., phone_capabilities: _Optional[_Union[PhoneCapabilities, _Mapping]] = ..., camera_capabilities: _Optional[_Union[CameraCapabilities, _Mapping]] = ..., metadata: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...) -> None: ...

class SessionImage(_message.Message):
    __slots__ = ("id", "session_id", "filename", "content_type", "size_bytes", "storage_path", "uploaded_at", "metadata")
    ID_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    FILENAME_FIELD_NUMBER: _ClassVar[int]
    CONTENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
    STORAGE_PATH_FIELD_NUMBER: _ClassVar[int]
    UPLOADED_AT_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    id: str
    session_id: str
    filename: str
    content_type: str
    size_bytes: int
    storage_path: str
    uploaded_at: _timestamp_pb2.Timestamp
    metadata: _struct_pb2.Struct
    def __init__(self, id: _Optional[str] = ..., session_id: _Optional[str] = ..., filename: _Optional[str] = ..., content_type: _Optional[str] = ..., size_bytes: _Optional[int] = ..., storage_path: _Optional[str] = ..., uploaded_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., metadata: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...) -> None: ...

class CreateSessionRequest(_message.Message):
    __slots__ = ("session_name", "phone_info", "phone_capabilities", "camera_capabilities", "metadata")
    SESSION_NAME_FIELD_NUMBER: _ClassVar[int]
    PHONE_INFO_FIELD_NUMBER: _ClassVar[int]
    PHONE_CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    CAMERA_CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    session_name: str
    phone_info: PhoneInfo
    phone_capabilities: PhoneCapabilities
    camera_capabilities: CameraCapabilities
    metadata: _struct_pb2.Struct
    def __init__(self, session_name: _Optional[str] = ..., phone_info: _Optional[_Union[PhoneInfo, _Mapping]] = ..., phone_capabilities: _Optional[_Union[PhoneCapabilities, _Mapping]] = ..., camera_capabilities: _Optional[_Union[CameraCapabilities, _Mapping]] = ..., metadata: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...) -> None: ...

class GetSessionRequest(_message.Message):
    __slots__ = ("session_id",)
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    def __init__(self, session_id: _Optional[str] = ...) -> None: ...

class UpdateSessionRequest(_message.Message):
    __slots__ = ("session_id", "session_name", "status", "metadata")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    SESSION_NAME_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    session_name: str
    status: str
    metadata: _struct_pb2.Struct
    def __init__(self, session_id: _Optional[str] = ..., session_name: _Optional[str] = ..., status: _Optional[str] = ..., metadata: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...) -> None: ...

class DeleteSessionRequest(_message.Message):
    __slots__ = ("session_id",)
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    def __init__(self, session_id: _Optional[str] = ...) -> None: ...

class DeleteSessionResponse(_message.Message):
    __slots__ = ("deleted",)
    DELETED_FIELD_NUMBER: _ClassVar[int]
    deleted: bool
    def __init__(self, deleted: bool = ...) -> None: ...

class ImageChunk(_message.Message):
    __slots__ = ("session_id", "image_id", "filename", "content_type", "data", "metadata_json")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    IMAGE_ID_FIELD_NUMBER: _ClassVar[int]
    FILENAME_FIELD_NUMBER: _ClassVar[int]
    CONTENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    METADATA_JSON_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    image_id: str
    filename: str
    content_type: str
    data: bytes
    metadata_json: str
    def __init__(self, session_id: _Optional[str] = ..., image_id: _Optional[str] = ..., filename: _Optional[str] = ..., content_type: _Optional[str] = ..., data: _Optional[bytes] = ..., metadata_json: _Optional[str] = ...) -> None: ...

class BatchImageChunk(_message.Message):
    __slots__ = ("session_id", "image_index", "filename", "content_type", "data", "end_of_image", "metadata_json")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    IMAGE_INDEX_FIELD_NUMBER: _ClassVar[int]
    FILENAME_FIELD_NUMBER: _ClassVar[int]
    CONTENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    END_OF_IMAGE_FIELD_NUMBER: _ClassVar[int]
    METADATA_JSON_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    image_index: int
    filename: str
    content_type: str
    data: bytes
    end_of_image: bool
    metadata_json: str
    def __init__(self, session_id: _Optional[str] = ..., image_index: _Optional[int] = ..., filename: _Optional[str] = ..., content_type: _Optional[str] = ..., data: _Optional[bytes] = ..., end_of_image: bool = ..., metadata_json: _Optional[str] = ...) -> None: ...

class ImageUploadResponse(_message.Message):
    __slots__ = ("image",)
    IMAGE_FIELD_NUMBER: _ClassVar[int]
    image: SessionImage
    def __init__(self, image: _Optional[_Union[SessionImage, _Mapping]] = ...) -> None: ...

class BatchUploadResponse(_message.Message):
    __slots__ = ("images",)
    IMAGES_FIELD_NUMBER: _ClassVar[int]
    images: _containers.RepeatedCompositeFieldContainer[SessionImage]
    def __init__(self, images: _Optional[_Iterable[_Union[SessionImage, _Mapping]]] = ...) -> None: ...

class ListImagesRequest(_message.Message):
    __slots__ = ("session_id",)
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    def __init__(self, session_id: _Optional[str] = ...) -> None: ...

class ImageListResponse(_message.Message):
    __slots__ = ("images",)
    IMAGES_FIELD_NUMBER: _ClassVar[int]
    images: _containers.RepeatedCompositeFieldContainer[SessionImage]
    def __init__(self, images: _Optional[_Iterable[_Union[SessionImage, _Mapping]]] = ...) -> None: ...

class DownloadImageRequest(_message.Message):
    __slots__ = ("session_id", "image_id")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    IMAGE_ID_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    image_id: str
    def __init__(self, session_id: _Optional[str] = ..., image_id: _Optional[str] = ...) -> None: ...

class SessionResponse(_message.Message):
    __slots__ = ("session",)
    SESSION_FIELD_NUMBER: _ClassVar[int]
    session: Session
    def __init__(self, session: _Optional[_Union[Session, _Mapping]] = ...) -> None: ...
