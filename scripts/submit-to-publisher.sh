#!/usr/bin/env bash
# submit-to-publisher.sh — 发布队列提交助手
# 用法见下方 usage()，bot 只需传参数，自动在 pending/ 创建队列文件夹
set -euo pipefail

QUEUE_DIR="/home/rooot/.openclaw/publish-queue/pending"

usage() {
    cat >&2 << 'EOF'
用法: submit-to-publisher.sh [选项]

必填:
  -a ACCOUNT_ID    bot1-bot10
  -t TITLE         标题（≤20中文字）
  -b BODY_FILE     正文文件路径（避免 shell 转义）
  -m MODE          text_to_image | image | longform | video
  -r REPLY_TO      飞书回调目标，如 direct:ou_xxx

可选:
  -i IMAGES        图片路径，逗号分隔（image 模式必填）
  -v VIDEO         视频路径（video 模式必填）
  -T TAGS          标签，逗号分隔
  -V VISIBILITY    公开可见（默认）| 仅自己可见 | 仅互关好友可见
  -s IMAGE_STYLE   基础（默认）| 光影 | 涂写 | 书摘 | 涂鸦 | 便签 | 边框 | 手写 | 几何
  -c CONTENT       图片下方正文（text_to_image 必填！与 -b 卡片文字分开写）
  -S SCHEDULE_AT   定时发布 ISO8601
  -o               声明原创
  -d DESC          长文摘要（仅 longform）

输出: 成功时 stdout 输出文件夹名
EOF
    exit 1
}

# === 默认值 ===
ACCOUNT_ID="" TITLE="" BODY_FILE="" MODE="" REPLY_TO=""
IMAGES="" VIDEO="" TAGS="" VISIBILITY="公开可见" IMAGE_STYLE="基础"
CONTENT="" SCHEDULE_AT="" IS_ORIGINAL=false DESC=""

# === 解析参数 ===
while getopts "a:t:b:m:r:i:v:T:V:s:c:S:od:" opt; do
    case $opt in
        a) ACCOUNT_ID="$OPTARG" ;;
        t) TITLE="$OPTARG" ;;
        b) BODY_FILE="$OPTARG" ;;
        m) MODE="$OPTARG" ;;
        r) REPLY_TO="$OPTARG" ;;
        i) IMAGES="$OPTARG" ;;
        v) VIDEO="$OPTARG" ;;
        T) TAGS="$OPTARG" ;;
        V) VISIBILITY="$OPTARG" ;;
        s) IMAGE_STYLE="$OPTARG" ;;
        c) CONTENT="$OPTARG" ;;
        S) SCHEDULE_AT="$OPTARG" ;;
        o) IS_ORIGINAL=true ;;
        d) DESC="$OPTARG" ;;
        *) usage ;;
    esac
done

# === 校验必填 ===
[[ -z "$ACCOUNT_ID" ]] && { echo "ERROR: -a ACCOUNT_ID 必填" >&2; exit 1; }
[[ -z "$TITLE" ]]      && { echo "ERROR: -t TITLE 必填" >&2; exit 1; }
[[ -z "$BODY_FILE" ]]  && { echo "ERROR: -b BODY_FILE 必填" >&2; exit 1; }
[[ -z "$MODE" ]]       && { echo "ERROR: -m MODE 必填" >&2; exit 1; }
[[ -z "$REPLY_TO" ]]   && { echo "ERROR: -r REPLY_TO 必填" >&2; exit 1; }

[[ ! -f "$BODY_FILE" ]] && { echo "ERROR: body 文件不存在: $BODY_FILE" >&2; exit 1; }

# 校验 MODE
case "$MODE" in
    text_to_image|image|longform|video) ;;
    *) echo "ERROR: -m 必须是 text_to_image|image|longform|video，收到: $MODE" >&2; exit 1 ;;
esac

# text_to_image 模式必须有 -c（图下正文）
[[ "$MODE" == "text_to_image" && -z "$CONTENT" ]] && { echo "ERROR: text_to_image 模式必须用 -c 指定图片下方正文（content），-b 是卡片文字（text_content），两者必须分开写" >&2; exit 1; }
# image 模式必须有图片
[[ "$MODE" == "image" && -z "$IMAGES" ]] && { echo "ERROR: image 模式必须用 -i 指定图片" >&2; exit 1; }
# video 模式必须有视频
[[ "$MODE" == "video" && -z "$VIDEO" ]] && { echo "ERROR: video 模式必须用 -v 指定视频" >&2; exit 1; }

# === 推导 publish_type ===
if [[ "$MODE" == "longform" ]]; then
    PUBLISH_TYPE="longform"
elif [[ "$MODE" == "video" ]]; then
    PUBLISH_TYPE="video"
else
    PUBLISH_TYPE="content"
fi

# === 生成文件夹名 ===
RANDOM_SUFFIX=$(head /dev/urandom | tr -dc a-z0-9 | head -c6)
TIMESTAMP=$(date +%Y-%m-%dT%H-%M-%S)
FOLDER_NAME="${TIMESTAMP}_${ACCOUNT_ID}_${RANDOM_SUFFIX}"
FOLDER_PATH="${QUEUE_DIR}/${FOLDER_NAME}"

# === 创建文件夹 ===
mkdir -p "$FOLDER_PATH" || { echo "ERROR: 无法创建文件夹 $FOLDER_PATH" >&2; exit 1; }

# 出错时清理
cleanup() { rm -rf "$FOLDER_PATH" 2>/dev/null; }
trap cleanup ERR

# === 复制图片 ===
IMAGES_YAML="[]"
if [[ -n "$IMAGES" ]]; then
    IFS=',' read -ra IMG_PATHS <<< "$IMAGES"
    IMAGES_YAML="["
    for idx in "${!IMG_PATHS[@]}"; do
        img="${IMG_PATHS[$idx]}"
        img=$(echo "$img" | xargs)  # trim whitespace
        [[ ! -f "$img" ]] && { echo "ERROR: 图片文件不存在: $img" >&2; exit 1; }
        ext="${img##*.}"
        num=$((idx + 1))
        dest_name="${num}.${ext}"
        cp "$img" "${FOLDER_PATH}/${dest_name}"
        [[ "$idx" -gt 0 ]] && IMAGES_YAML+=", "
        IMAGES_YAML+="\"${dest_name}\""
    done
    IMAGES_YAML+="]"
fi

# === 复制视频 ===
VIDEO_YAML=""
if [[ -n "$VIDEO" ]]; then
    [[ ! -f "$VIDEO" ]] && { echo "ERROR: 视频文件不存在: $VIDEO" >&2; exit 1; }
    ext="${VIDEO##*.}"
    dest_name="video.${ext}"
    cp "$VIDEO" "${FOLDER_PATH}/${dest_name}"
    VIDEO_YAML="$dest_name"
fi

# === 构建 tags YAML ===
TAGS_YAML="[]"
if [[ -n "$TAGS" ]]; then
    IFS=',' read -ra TAG_ARR <<< "$TAGS"
    TAGS_YAML="["
    for idx in "${!TAG_ARR[@]}"; do
        tag=$(echo "${TAG_ARR[$idx]}" | xargs)
        [[ "$idx" -gt 0 ]] && TAGS_YAML+=", "
        TAGS_YAML+="\"${tag}\""
    done
    TAGS_YAML+="]"
fi

# === 转义 YAML 字符串中的双引号 ===
yaml_escape() { printf '%s' "$1" | sed 's/"/\\"/g'; }

TITLE_ESC=$(yaml_escape "$TITLE")
CONTENT_ESC=$(yaml_escape "$CONTENT")
DESC_ESC=$(yaml_escape "$DESC")
SUBMITTED_AT=$(date +%Y-%m-%dT%H:%M:%S%:z)

# === 写 post.md ===
{
    echo "---"
    echo "account_id: ${ACCOUNT_ID}"
    echo "publish_type: ${PUBLISH_TYPE}"

    # content 类型专有字段
    if [[ "$PUBLISH_TYPE" == "content" ]]; then
        echo "content_mode: ${MODE}"
        echo ""
        echo "title: \"${TITLE_ESC}\""
        echo "content: \"${CONTENT_ESC}\""
        echo "visibility: \"${VISIBILITY}\""
        if [[ "$MODE" == "text_to_image" ]]; then
            echo "image_style: \"${IMAGE_STYLE}\""
        fi
        if [[ "$MODE" == "image" ]]; then
            echo "images: ${IMAGES_YAML}"
        fi
        echo "tags: ${TAGS_YAML}"
        echo "schedule_at: \"${SCHEDULE_AT}\""
        echo "is_original: ${IS_ORIGINAL}"
        echo "products: []"
    fi

    # longform 专有
    if [[ "$PUBLISH_TYPE" == "longform" ]]; then
        echo ""
        echo "title: \"${TITLE_ESC}\""
        echo "desc: \"${DESC_ESC}\""
        echo "visibility: \"${VISIBILITY}\""
        echo "tags: ${TAGS_YAML}"
        echo "schedule_at: \"${SCHEDULE_AT}\""
    fi

    # video 专有
    if [[ "$PUBLISH_TYPE" == "video" ]]; then
        echo ""
        echo "title: \"${TITLE_ESC}\""
        echo "video: \"${VIDEO_YAML}\""
        echo "visibility: \"${VISIBILITY}\""
        echo "tags: ${TAGS_YAML}"
        echo "schedule_at: \"${SCHEDULE_AT}\""
        echo "is_original: ${IS_ORIGINAL}"
        echo "products: []"
    fi

    echo ""
    echo "submitted_by: ${ACCOUNT_ID}"
    echo "submitted_at: \"${SUBMITTED_AT}\""
    echo "reply_to: \"${REPLY_TO}\""
    echo "---"
    echo ""
    cat "$BODY_FILE"
} > "${FOLDER_PATH}/post.md"

# === 清理 body 临时文件 ===
rm -f "$BODY_FILE" 2>/dev/null || true

# === 取消 ERR trap（成功了，不要清理） ===
trap - ERR

# === 通知印务局（自动发送 agent message + 唤醒） ===
MSG_ID=$(head /dev/urandom | tr -dc A-Za-z0-9_- | head -c21)
MSG_CONTENT="📮 新帖投稿：《${TITLE}》${FOLDER_NAME}，请处理发布队列"
MSG_TIME=$(date -u +%Y-%m-%dT%H:%M:%S.000Z)
TRACE_JSON="[{\"agent\":\"${ACCOUNT_ID}\",\"reply_channel\":\"feishu\",\"reply_to\":\"${REPLY_TO#direct:}\",\"reply_account\":\"${ACCOUNT_ID}\"}]"

# Write message to Redis (same format as agent-messaging plugin)
redis-cli HSET "agentmsg:detail:${MSG_ID}" \
    message_id "$MSG_ID" \
    from "$ACCOUNT_ID" \
    to "mcp_publisher" \
    content "$MSG_CONTENT" \
    type "request" \
    trace "$TRACE_JSON" \
    reply_to_message_id "" \
    metadata "{}" \
    created_at "$MSG_TIME" \
    status "pending" > /dev/null 2>&1

redis-cli EXPIRE "agentmsg:detail:${MSG_ID}" 604800 > /dev/null 2>&1
redis-cli XADD "agentmsg:inbox:mcp_publisher" MAXLEN "~" 1000 "*" message_id "$MSG_ID" > /dev/null 2>&1
redis-cli XADD "agentmsg:outbox:${ACCOUNT_ID}" MAXLEN "~" 1000 "*" message_id "$MSG_ID" > /dev/null 2>&1

# Wake mcp_publisher agent (fire-and-forget, dedicated per-peer session)
nohup openclaw agent --agent mcp_publisher \
    --session-key "agent:mcp_publisher:agent:${ACCOUNT_ID}" \
    --message "[MSG:${MSG_ID}] from=${ACCOUNT_ID}: ${MSG_CONTENT}" \
    > /dev/null 2>&1 &

# Update status to delivered
redis-cli HSET "agentmsg:detail:${MSG_ID}" status "delivered" > /dev/null 2>&1

# === 输出文件夹名 ===
echo "$FOLDER_NAME"
