#!/usr/bin/env python3
"""
將逐字稿按行數分段，方便分段摘要以減少 context 消耗。

usage: python3 scripts/chunk_transcript.py /tmp/reel_03_clean.txt [每段行數]
default: 每段 200 行

產出：
  /tmp/reel_03_clean_chunk1.txt (第 1-200 行)
  /tmp/reel_03_clean_chunk2.txt (第 201-400 行)
  ...
"""

import sys
import os

DEFAULT_CHUNK = 200


def chunk_transcript(filepath, chunk_size=DEFAULT_CHUNK):
    with open(filepath, 'r') as f:
        lines = f.readlines()

    total = len(lines)
    basename = os.path.splitext(os.path.basename(filepath))[0]
    outdir = os.path.dirname(filepath) or '/tmp'
    chunks = []

    for i in range(0, total, chunk_size):
        chunk_num = i // chunk_size + 1
        chunk_lines = lines[i:i + chunk_size]
        start = i + 1
        end = min(i + chunk_size, total)
        out_path = f"{outdir}/{basename}_chunk{chunk_num}.txt"
        with open(out_path, 'w') as f:
            f.write(''.join(chunk_lines))
        chunks.append((out_path, start, end, len(chunk_lines)))

    print(f"📄 原始檔案: {filepath} ({total} 行)")
    print(f"📦 分成 {len(chunks)} 段（每段 {chunk_size} 行）:\n")
    for path, start, end, count in chunks:
        print(f"   {path}")
        print(f"   第 {start}-{end} 行（{count} 行）\n")
    print("👉 摘要流程:")
    print("   1. 每段各自摘要（每段約消耗很少 context）")
    print("   2. 合併所有段落摘要，做最終整理")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("❌ 用法: python3 scripts/chunk_transcript.py <逐字稿檔案> [每段行數]")
        sys.exit(1)

    filepath = sys.argv[1]
    chunk_size = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_CHUNK
    chunk_transcript(filepath, chunk_size)
