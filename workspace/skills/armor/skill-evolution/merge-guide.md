# 合并审批指引

> 当日报中推荐合并某个 skill 时，按以下步骤操作。

## 合并前检查

1. **查看 diff**（进化流程已自动生成）
   ```bash
   cat /home/rooot/.openclaw/skills-sandbox/{skill_name}/DIFF.patch
   ```
   如果 DIFF.patch 不存在，手动生成：
   ```bash
   diff -ruN /home/rooot/.openclaw/workspace/skills/{skill_name}/ \
             /home/rooot/.openclaw/skills-sandbox/{skill_name}/ \
             --exclude=skill.json --exclude=.skill_id --exclude=.upload_meta.json --exclude=DIFF.patch
   ```

2. **确认变更合理**
   - 没有删除关键内容
   - 没有引入与其他 skill 冲突的指令
   - 没有添加可能触发副作用的操作
   - 语言风格与项目一致

## 执行合并

3. **复制 .md 文件**（只复制 markdown 文件，不动 skill.json）
   ```bash
   cd /home/rooot/.openclaw/skills-sandbox/{skill_name}
   for f in *.md; do
     cp "$f" /home/rooot/.openclaw/workspace/skills/{skill_name}/
   done
   ```

4. **移动备份目录到回收站**

   OpenSpace 进化时会生成 `.backup-*` 备份目录。合并后移入回收站：
   ```bash
   for bak in /home/rooot/.openclaw/skills-sandbox/{skill_name}.backup-*/; do
     [ -d "$bak" ] && mv "$bak" /home/rooot/.openclaw/skills-sandbox/.recycle/ && echo "Recycled: $(basename $bak)"
   done
   ```

5. **记录变更**

   在技能部的 `memory/changelog.md` 中记录：
   ```
   ## {日期} — {skill_name} 进化合并
   - 变更摘要：{来自日报}
   - 审批人：{你的名字}
   ```

## 合并后

6. **清理沙盒标记**
   ```bash
   rm /home/rooot/.openclaw/skills-sandbox/{skill_name}/.upload_meta.json
   rm -f /home/rooot/.openclaw/skills-sandbox/{skill_name}/DIFF.patch
   ```
   这样下次同步时该 skill 会重新从线上版同步。

7. **观察**

   合并后 1-2 天内关注使用该 skill 的 bot 是否出现异常。
   如有问题，用 git 回退线上 skill 目录。

---

## 回滚

如果合并后出现问题：
```bash
cd /home/rooot/.openclaw/workspace/skills
git checkout -- {skill_name}/
```
