#!/usr/bin/env bash
# Generate Python gRPC stubs from proto/session_service.proto into app/pb/.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
else
  PYTHON="${PYTHON:-python3}"
fi
PROTO_INCLUDE="$("$PYTHON" -c 'import pathlib, google.protobuf; print(pathlib.Path(google.protobuf.__file__).resolve().parent.parent)')"
mkdir -p app/pb
"$PYTHON" -m grpc_tools.protoc \
  -I proto \
  -I "$PROTO_INCLUDE" \
  --python_out=app/pb \
  --grpc_python_out=app/pb \
  --pyi_out=app/pb \
  proto/session_service.proto
# grpc_tools emits a top-level import; rewrite it to a package-relative import.
grpc_file="$ROOT/app/pb/session_service_pb2_grpc.py"
if [[ -f "$grpc_file" ]]; then
  "$PYTHON" - "$grpc_file" <<'PY'
import pathlib
import sys
path = pathlib.Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
text = text.replace(
    "import session_service_pb2 as session__service__pb2",
    "from app.pb import session_service_pb2 as session__service__pb2",
)
text = text.replace(
    "import session_service_pb2 as session_service__pb2",
    "from app.pb import session_service_pb2 as session_service__pb2",
)
path.write_text(text, encoding="utf-8")
PY
fi
touch app/pb/__init__.py
echo "generated stubs in app/pb/"
