#!/usr/bin/env python3
"""
分批上傳逐字稿到 Notion 子頁面（避免 API 大小限制截斷）

這個腳本產生分批的文字檔，方便手動或透過 Claude 上傳。
Notion MCP 工具的 payload 限制約 10-15KB，所以每批控制在 500 行以內。

usage: python3 scripts/upload_transcript.py /tmp/reel_03_clean.txt
"""

import sys
import os

BATCH_SIZE = 500  # 每批行數

def split_transcript(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()

    total = len(lines)
    basename = os.path.splitext(os.path.basename(filepath))[0]
    outdir = os.path.dirname(filepath) or '/tmp'
    batches = []

    for i in range(0, total, BATCH_SIZE):
        batch_num = i // BATCH_SIZE + 1
        batch_lines = lines[i:i + BATCH_SIZE]
        out_path = f"{outdir}/{basename}_batch{batch_num}.txt"
        with open(out_path, 'w') as f:
            f.write(''.join(batch_lines))
        batches.append((out_path, len(batch_lines)))

    print(f"📄 原始檔案: {filepath} ({total} 行)")
    print(f"📦 分成 {len(batches)} 批:")
    for path, count in batches:
        print(f"   {path} ({count} 行)")
    print()
    print("👉 上傳順序:")
    print("   第 1 批: 用 replace_content 建立頁面內容")
    print("   第 2+ 批: 用 update_content append 到頁面尾端")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("❌ 用法: python3 scripts/upload_transcript.py <逐字稿檔案>")
        sys.exit(1)
    split_transcript(sys.argv[1])
