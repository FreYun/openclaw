#!/bin/bash
# Usage:
#   query-stats.sh bot5              # 该 bot 全部帖子（标题+指标）
#   query-stats.sh bot5 --titles     # 仅标题列表（审稿查重叠用）
#   query-stats.sh bot5 --top=3      # 只看互动最好的 N 篇
#   query-stats.sh --summary         # 所有 bot 的一行摘要

STATS_FILE="$(dirname "$0")/xhs-stats.json"

if [ ! -f "$STATS_FILE" ]; then
  echo "Error: $STATS_FILE not found"
  exit 1
fi

python3 - "$@" <<'PYEOF'
import json, sys, os, re, glob

stats_file = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])) if sys.argv[0] != '-' else '.', 'xhs-stats.json')
# When called via bash heredoc, find the file relative to the script
for candidate in [
    os.environ.get('STATS_FILE', ''),
    os.path.join(os.path.dirname(os.path.realpath('/home/rooot/.openclaw/dashboard/query-stats.sh')), 'xhs-stats.json'),
    '/home/rooot/.openclaw/dashboard/xhs-stats.json',
]:
    if candidate and os.path.exists(candidate):
        stats_file = candidate
        break

PUBLISH_DIR = '/home/rooot/.openclaw/workspace-sys1/publish-queue/published'

def extract_quoted_field(fm_block, field):
    """Extract a possibly multi-line quoted YAML field value."""
    # Match field: "multi\nline\nvalue" (double-quoted)
    pattern = rf'^{field}:\s*"((?:[^"\\]|\\.)*)"\s*$'
    m = re.search(pattern, fm_block, re.MULTILINE | re.DOTALL)
    if m:
        return m.group(1).strip()
    # Match field: 'value' (single-quoted)
    pattern = rf"^{field}:\s*'((?:[^'\\]|\\.)*)'\s*$"
    m = re.search(pattern, fm_block, re.MULTILINE | re.DOTALL)
    if m:
        return m.group(1).strip()
    # Match field: value (unquoted single line)
    pattern = rf'^{field}:\s*(.+)$'
    m = re.search(pattern, fm_block, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return ''

def load_published_index(bot_id):
    """Build title -> content map from published posts for a bot."""
    index = {}
    if not os.path.isdir(PUBLISH_DIR):
        return index
    for entry in os.listdir(PUBLISH_DIR):
        # Match bot in filename: _bot7_ or -bot7-
        if f'_{bot_id}_' not in entry and f'-{bot_id}-' not in entry:
            continue
        full = os.path.join(PUBLISH_DIR, entry)
        # Find the .md file (flat file or dir/post.md)
        if os.path.isdir(full):
            md = os.path.join(full, 'post.md')
        elif entry.endswith('.md'):
            md = full
        else:
            continue
        if not os.path.exists(md):
            continue
        try:
            with open(md, 'r', encoding='utf-8') as f:
                text = f.read()
        except:
            continue
        # Extract title and content from frontmatter
        fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n?(.*)', text, re.DOTALL)
        if not fm_match:
            continue
        fm_block, body = fm_match.group(1), fm_match.group(2).strip()
        title = extract_quoted_field(fm_block, 'title')
        if not title:
            continue
        # content field has the full post text; body after --- is often just text_image
        content = extract_quoted_field(fm_block, 'content')
        index[title] = content if content else body
    return index

with open(stats_file) as f:
    data = json.load(f)

args = sys.argv[1:]

# --summary mode: one line per bot
if '--summary' in args:
    print(f"Updated: {data.get('updated_at', '?')}")
    for bot_id in sorted(data.get('bots', {}), key=lambda x: int(x.replace('bot','')) if x.startswith('bot') else 0):
        bot = data['bots'][bot_id]
        notes = bot.get('notes', [])
        if not notes:
            print(f"  {bot_id}: no data")
            continue
        total_likes = sum(int(n.get('likes', 0)) for n in notes)
        total_comments = sum(int(n.get('comments', 0)) for n in notes)
        print(f"  {bot_id}: {len(notes)} notes, {total_likes} likes, {total_comments} comments")
    sys.exit(0)

# Need a bot ID
if not args or args[0].startswith('--'):
    print("Usage: query-stats.sh <botN> [--titles] [--top=N] [--with-content]")
    sys.exit(1)

bot_id = args[0]
bot_data = data.get('bots', {}).get(bot_id)
if not bot_data:
    print(f"No data for {bot_id}")
    sys.exit(1)

notes = bot_data.get('notes', [])
if not notes:
    print(f"{bot_id}: no notes")
    sys.exit(0)

# Parse flags
titles_only = '--titles' in args
with_content = '--with-content' in args
top_n = None
for a in args:
    if a.startswith('--top='):
        top_n = int(a.split('=')[1])

# Score for sorting: likes*1 + comments*4 + favorites*2 + shares*4 (CES-like)
def engagement(n):
    return int(n.get('likes',0)) + int(n.get('comments',0))*4 + int(n.get('favorites',0))*2 + int(n.get('shares',0))*4

if top_n:
    notes = sorted(notes, key=engagement, reverse=True)[:top_n]

# Lazy-load published content index only when needed
pub_index = None
if with_content:
    pub_index = load_published_index(bot_id)

print(f"{bot_id} | updated {bot_data.get('updated_at','?')[:10]} | {len(bot_data.get('notes',[]))} notes total")
print()

if titles_only:
    for n in notes:
        print(f"  {n.get('publish_time','')} | {n.get('title','')}")
else:
    for n in notes:
        eng = engagement(n)
        print(f"  {n.get('publish_time','')} | {n.get('title','')}")
        print(f"    impressions={n.get('impressions',0)} views={n.get('views',0)} click={n.get('click_rate','?')}")
        print(f"    likes={n.get('likes',0)} comments={n.get('comments',0)} favorites={n.get('favorites',0)} shares={n.get('shares',0)} followers={n.get('new_followers',0)}")
        print(f"    engagement_score={eng}")
        if with_content and pub_index is not None:
            title = n.get('title', '')
            content = pub_index.get(title)
            if content:
                print(f"    --- 正文 ---")
                for line in content.split('\n'):
                    print(f"    {line}")
                print(f"    --- /正文 ---")
            else:
                print(f"    (正文未找到，可查 bot 的 memory/发帖记录.md)")
        print()
PYEOF
