# Submit to Publisher (Publish Queue)

After writing a post, **do NOT call publish tools directly**. Submit to the publish queue instead. The publisher (印务局) performs compliance review: approved → publish; rejected → returns revision notes. **On rejection, read `skills/xhs-operate/合规速查.md`, fix violations, and resubmit.**

---

## Submission Steps

> **⚠️ Body file + script MUST run in the same bash block.** Separate execution causes `$$` (PID) mismatch — script won't find the body file.

> **⚠️ Body file must contain the FULL original content. Never compress, abbreviate, or omit.** Every word of your draft goes into the body file. Truncating content = tampering = serious violation.

### Step 1: Write body + run submit script (single bash block)

See "Post Types" below — pick the matching mode and follow its bash example. The script creates a folder under `pending/`, **automatically notifies the publisher (印务局)**, and outputs the folder name to stdout.

> **⚠️ If script fails (exit code ≠ 0) or `$folder` is empty, STOP. Report the error to user. Never bypass the script to write files into publish-queue/ manually.**

### Step 2: Inform user, done

Reply: "《{title}》已提交印务局，发布结果稍后通知。" **Task ends here — do NOT wait for publisher response.**

---

## Post Types (read the corresponding file before submitting)

| Type | `-m` flag | Reference |
|------|-----------|-----------|
| **Text-to-image (most common)** | `text_to_image` | `text-to-image.md` (**🚨 `-b` 和 `-c` 都必填！** `-b` = 卡片文字, `-c` = 图下正文) |
| Image (real photos) | `image` | `image.md` |
| Longform article | `longform` | `longform.md` |
| Video | `video` | `video.md` |

**Read the corresponding file before submitting.**

---

## Optional Parameters

| Flag | Description | Default |
|------|-------------|---------|
| `-T tags` | Comma-separated tags | none |
| `-V visibility` | `公开可见` / `仅自己可见` / `仅互关好友可见` | `公开可见` |
| `-s style` | Image style (text_to_image only) | `基础` |
| `-c content` | 图下正文 (text_to_image **必填**) | 无默认值 |
| `-S schedule_at` | Scheduled publish, ISO8601 (1h–14 days) | immediate |
| `-o` | Declare original | false |
| `-d desc` | Article summary (longform only) | none |

---

## Publisher Callback

Results are auto-delivered to user via Feishu. Usually no action needed. If you receive a `[REPLY:xxx]` prefixed message, forward it to the user as-is.

---

## Misc

- **Check publish status**: `ls /home/rooot/.openclaw/publish-queue/published/ | grep ${account_id}`
- **Fallback (direct publish)**: If publisher is down, read `skills/xiaohongshu-mcp/SKILL.md` first
