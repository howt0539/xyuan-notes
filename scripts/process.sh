#!/bin/bash
# 瘋狗教練直播前置處理腳本
# usage: ./scripts/process.sh <影片網址> <編號>
# example: ./scripts/process.sh "https://www.instagram.com/reel/xxx" 03

set -e

URL="$1"
NUM="$2"
OUTDIR="/tmp/whisper_out"
VENV="/tmp/opencc_venv"

if [ -z "$URL" ] || [ -z "$NUM" ]; then
  echo "❌ 用法: ./scripts/process.sh <影片網址> <編號>"
  echo "   例: ./scripts/process.sh 'https://www.instagram.com/reel/xxx' 03"
  exit 1
fi

echo "📂 輸出目錄: $OUTDIR"
mkdir -p "$OUTDIR"

# Step 1: 下載影片
echo ""
echo "⬇️  Step 1/3: 下載影片..."
if [ -f "${OUTDIR}/reel_${NUM}.mp4" ]; then
  echo "⏭  影片已存在，跳過下載"
else
  yt-dlp --cookies-from-browser chrome -o "${OUTDIR}/reel_${NUM}.mp4" "$URL"
fi
echo "✅ 下載完成: ${OUTDIR}/reel_${NUM}.mp4"

# Step 2: Whisper 轉逐字稿
echo ""
echo "🎙️ Step 2/3: Whisper 轉逐字稿..."
whisper "${OUTDIR}/reel_${NUM}.mp4" \
  --model turbo \
  --language zh \
  --condition_on_previous_text False \
  --output_dir "$OUTDIR" \
  --output_format txt
echo "✅ 逐字稿完成: ${OUTDIR}/reel_${NUM}.txt"

# Step 3: 簡轉繁 + 去幻覺
echo ""
echo "🔄 Step 3/3: 簡轉繁..."

# 確保 venv 存在
if [ ! -d "$VENV" ]; then
  echo "   建立 venv..."
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q opencc-python-reimplemented
fi

"$VENV/bin/python3" -c "
import opencc
cc = opencc.OpenCC('s2t')
with open('${OUTDIR}/reel_${NUM}.txt', 'r') as f:
    lines = f.readlines()
# 跳過第一行（Whisper 幻覺）
converted = cc.convert(''.join(lines[1:]))
out_path = '/tmp/reel_${NUM}_clean.txt'
with open(out_path, 'w') as f:
    f.write(converted)
total = len(lines) - 1
print(f'✅ 繁體化完成: {out_path} ({total} 行)')
"

# Step 4: 取得影片時長
echo ""
echo "⏱  Step 4/4: 取得影片時長..."
if command -v ffprobe &> /dev/null; then
  DURATION_SEC=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "${OUTDIR}/reel_${NUM}.mp4" | cut -d. -f1)
  DURATION_MIN=$((DURATION_SEC / 60))
  echo "✅ 影片時長: 約 ${DURATION_MIN} 分鐘 (${DURATION_SEC} 秒)"
else
  DURATION_MIN="?"
  echo "⚠️  ffprobe 未安裝，跳過時長偵測（可用 brew install ffmpeg 安裝）"
fi

# Step 5: 分段逐字稿（方便摘要）
echo ""
echo "📦 Step 5/5: 分段逐字稿..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "${SCRIPT_DIR}/chunk_transcript.py" "/tmp/reel_${NUM}_clean.txt"

echo ""
echo "========================================"
echo "🎉 全部完成！"
echo "========================================"
echo ""
echo "   影片:       ${OUTDIR}/reel_${NUM}.mp4"
echo "   原始逐字稿: ${OUTDIR}/reel_${NUM}.txt"
echo "   清理後繁體: /tmp/reel_${NUM}_clean.txt"
echo "   影片時長:   約 ${DURATION_MIN} 分鐘"
echo "   分段檔案:   /tmp/reel_${NUM}_clean_chunk*.txt"
echo ""
echo "👉 接下來交給 Claude："
echo "   「直播 ${NUM} 的逐字稿好了，在 /tmp/reel_${NUM}_clean.txt，時長約 ${DURATION_MIN} 分鐘」"
