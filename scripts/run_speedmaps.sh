#!/bin/sh
# Runs the speedmap generator for today's Q1 Lakeside meeting (Mac/Linux).
cd "$(dirname "$0")/.." || exit 1
mkdir -p output
. .venv/bin/activate
python run.py --fresh "$@" >> output/run_log.txt 2>&1
