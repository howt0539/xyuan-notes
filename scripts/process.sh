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
yt-dlp -o "${OUTDIR}/reel_${NUM}.mp4" "$URL"
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

echo ""
echo "🎉 全部完成！"
echo "   原始逐字稿: ${OUTDIR}/reel_${NUM}.txt"
echo "   清理後繁體: /tmp/reel_${NUM}_clean.txt"
echo ""
echo "👉 接下來交給 Claude 處理：建 Notion 頁面、做摘要、更新 GitHub Pages"
