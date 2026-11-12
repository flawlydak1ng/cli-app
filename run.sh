#!/usr/bin/env sh
# Запуск инструмента без установки: ./run.sh --package ... --repo ...
cd "$(dirname "$0")" || exit 1
PYTHONPATH=src exec python3 -m depgraph "$@"
