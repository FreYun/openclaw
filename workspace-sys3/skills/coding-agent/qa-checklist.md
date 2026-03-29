# QA 验收

Claude Code 跑完后，三步验收：

## 1. 看 diff

```bash
cd /tmp/sandbox-xxx
git diff --stat   # 改了哪些文件
git diff          # 具体改动
```

- 只改了该改的文件？多改了就 Fail
- 改动内容和需求一致？有无关的重构/格式化就 Fail

## 2. 跑 build/test

```bash
go build .        # Go 项目
npm run build     # TS 项目
```

编译不过就 Fail。

## 3. 判定

| 结果 | 动作 |
|------|------|
| Pass | 合并回主分支，报告研究部 |
| Round 1 Fail | 修正需求描述，在同一沙盒重试 |
| Round 2 Fail | 停止，清理沙盒，报告研究部（附两轮失败原因） |
