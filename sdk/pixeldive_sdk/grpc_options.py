"""Default gRPC message size matching the session service ceiling."""

MAX_MESSAGE_BYTES = 34 * 1024 * 1024
CHANNEL_OPTIONS: list[tuple[str, int]] = [
    ("grpc.max_send_message_length", MAX_MESSAGE_BYTES),
    ("grpc.max_receive_message_length", MAX_MESSAGE_BYTES),
]
