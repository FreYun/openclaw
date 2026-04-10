# Longform Article

```bash
cat > /tmp/post_body_$$.txt << 'BODYEOF'
Full article body (no length limit)...
BODYEOF

folder=$(bash skills/xhs-op/submit-to-publisher.sh \
  -a ${ACCOUNT_ID} -t "长文标题" -b /tmp/post_body_$$.txt \
  -m longform -r "direct:ou_xxx" \
  -T "A股,研究" \
  -d "Article summary / subtitle")
echo "FOLDER: $folder"
```
