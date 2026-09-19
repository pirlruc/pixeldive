"""Domain exceptions raised by SessionService and mapped by transports."""


class SessionServiceError(Exception):
    """Base class for mapped session-service failures."""


class SessionNotFoundError(SessionServiceError):
    """The requested session UUID does not exist."""


class ImageNotFoundError(SessionServiceError):
    """The requested image UUID does not exist in the given session."""


class InvalidStatusError(SessionServiceError):
    """Client supplied a session status outside the allowed set."""


class ImageTooLargeError(SessionServiceError):
    """Uploaded payload exceeded Settings.max_image_bytes."""


class UnsupportedContentTypeError(SessionServiceError):
    """Upload Content-Type is not a permitted image type."""


class EmptyImageError(SessionServiceError):
    """Upload contained zero bytes."""


class InvalidMetadataError(SessionServiceError):
    """Metadata JSON was not an object."""


class InvalidIdError(SessionServiceError):
    """A path or protobuf UUID could not be parsed."""
