#!/usr/bin/env bash
# Kautilya nightly Gemini eval runner (quota-respecting, resumable).
#
# Gemini free tier (~20 req/day, ~2 req/record) → ~10 records/night.
# Each run skips already-traced records and appends; reports are cumulative.
#
# Usage:
#   bash scripts/gemini_nightly.sh [--max N] [--delay S]
#
# --max N : cap this run to N new records (default 10)
# --delay S: seconds between records to stay under quota (default 15)

set -u

REPO=/mnt/d/Projects/GenAI-Starts-here/Kautilya
TRACE=$REPO/reports/bench_trace_gemini2.jsonl
REPORT=$REPO/reports/bench_report_gemini_current.json
BENCH=$REPO/data/bench/draft.jsonl
LOG=/mnt/d/gemini_nightly.log

MAX=10
DELAY=15
while [ $# -gt 0 ]; do
    case "$1" in
        --max)   MAX="$2";   shift 2;;
        --delay) DELAY="$2"; shift 2;;
        *) echo "unknown arg: $1"; exit 2;;
    esac
done

cd "$REPO"

done_before=0
if [ -f "$TRACE" ]; then
    done_before=$(wc -l < "$TRACE")
fi

echo "==================== $(date '+%F %T %Z') ====================" >> "$LOG"
echo "batch started: done_trace=$done_before max_new=$MAX" >> "$LOG"

# CUDA_VISIBLE_DEVICES="" forces bge-m3/reranker onto CPU: no contention with
# the user's Streamlit session, and only 1 query/record is embedded anyway.
CUDA_VISIBLE_DEVICES="" \
"./Kautilya-venv/bin/kautilya" eval \
    --bench "$BENCH" \
    --stage full \
    --llm gemini \
    --no-verify \
    --resume \
    --limit "$MAX" \
    --delay "$DELAY" \
    --out "$REPORT" \
    --trace "$TRACE" \
    >> "$LOG" 2>&1

code=$?
echo "batch finished: exit=$code at $(date '+%F %T %Z')" >> "$LOG"

done_after=0
if [ -f "$TRACE" ]; then
    done_after=$(wc -l < "$TRACE")
fi
echo "records completed total: $done_before -> $done_after" >> "$LOG"
echo "cumulative report -> $REPORT" >> "$LOG"
tail -3 "$REPORT" >> "$LOG" 2>/dev/null
echo "" >> "$LOG"
exit "$code"