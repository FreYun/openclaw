# Video Post

```bash
cat > /tmp/post_body_$$.txt << 'BODYEOF'
Video caption text
BODYEOF

folder=$(bash ~/.openclaw/workspace/skills/xhs-op/submit-to-publisher.sh \
  -a ${ACCOUNT_ID} -t "视频标题" -b /tmp/post_body_$$.txt \
  -m video -r "direct:ou_xxx" \
  -v "/path/to/video.mp4" \
  -T "投资")
echo "FOLDER: $folder"
```
