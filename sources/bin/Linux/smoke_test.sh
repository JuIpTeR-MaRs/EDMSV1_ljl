#!/bin/bash
# ==============================================================================
#  EDMS 冒烟测试一键启动脚本 (Linux / macOS)
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

cd "$ROOT_DIR" || exit 1

echo "[EDMS] 正在启动系统冒烟测试 (Smoke Test)..."
echo "----------------------------------------------------"

if [ -f "sources/backend/.venv/bin/python" ]; then
    "sources/backend/.venv/bin/python" smoke_test.py "$@"
elif command -v python3 &>/dev/null; then
    python3 smoke_test.py "$@"
else
    python smoke_test.py "$@"
fi

EXIT_CODE=$?
echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "[EDMS] 冒烟测试全部通过！系统运行健康。"
else
    echo "[EDMS] 冒烟测试发现异常，请检查上方日志排查。"
fi

exit $EXIT_CODE
