# Image Post (Real Photos)

```bash
cat > /tmp/post_body_$$.txt << 'BODYEOF'
Caption text (≤1000 chars)
BODYEOF

folder=$(bash skills/xhs-op/submit-to-publisher.sh \
  -a ${ACCOUNT_ID} -t "标题" -b /tmp/post_body_$$.txt \
  -m image -r "direct:ou_xxx" \
  -i "/path/to/img1.jpg,/path/to/img2.png" \
  -T "投资,理财")
echo "FOLDER: $folder"
```

Images are auto-copied into the queue folder (renamed to `1.jpg`, `2.png`, etc.).
