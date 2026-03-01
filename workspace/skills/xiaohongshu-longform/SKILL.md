# 小红书长文发布技能

## 概述

通过 OpenClaw browser 工具在小红书 web 端发布长文的完整流程。

## 核心流程

### 1. 进入发布页面

```javascript
// 从首页底部导航栏点「发布」按钮
// 会自动在新标签页打开创作服务平台
// targetId 切换到新标签页
```

### 2. 选择长文创作

1. 点击「写长文」按钮
2. 点击「新的创作」按钮

### 3. 填写标题

```javascript
// 标题输入框用 value + input event
document.querySelector('[placeholder="输入标题"]').value = '标题内容';
document.querySelector('[placeholder="输入标题"]').dispatchEvent(new Event('input', {bubbles: true}));
```

### 4. 输入正文（关键！）

```javascript
// 必须先点击编辑器区域聚焦
// 然后用 execCommand 输入，不能直接 set innerText

// 步骤 1: 点击编辑器
browser act ref=<编辑器 ref> kind=click

// 步骤 2: 用 execCommand 输入
document.execCommand('insertText', false, '正文内容');

// 换行用 \n\n，execCommand 会自动处理成段落
```

**为什么必须用 execCommand？**
- 小红书长文编辑器是富文本架构
- 直接设置 `innerText` 或 `innerHTML` 不会触发编辑器的内部状态更新
- `document.execCommand('insertText')` 会正确触发输入事件和编辑器状态同步

### 5. 一键排版

```javascript
// 点击「一键排版」按钮
browser act ref=<一键排版按钮 ref> kind=click
```

### 6. 进入下一步

```javascript
// 点击「下一步」按钮
browser act ref=<下一步按钮 ref> kind=click
```

### 7. 填写描述

```javascript
// 描述框同样用 execCommand 输入
// 先点击聚焦
browser act ref=<描述框 ref> kind=click

// 然后输入
document.execCommand('insertText', false, '描述内容');
```

### 8. 发布

```javascript
// 点击「发布」按钮
browser act ref=<发布按钮 ref> kind=click
```

## 关键技术点

### 输入方式对比

| 方式 | 标题框 | 长文编辑器 | 描述框 |
|------|--------|-----------|--------|
| `value + input event` | ✅ | ❌ | ❌ |
| `innerText + input event` | ❌ | ❌ | ❌ |
| `execCommand('insertText')` | ⚠️ | ✅ | ✅ |

### execCommand 的优势

1. 触发正确的输入事件
2. 自动处理换行和段落
3. 富文本编辑器原生支持
4. 不会被检测为自动化操作

## 注意事项

1. **不要用 URL 直接导航** - 容易被检测到，从首页正常点击进去
2. **页面变化后重新 snapshot** - ref 会失效
3. **等待页面加载** - 点击后等页面稳定再操作
4. **字数限制** - 长文描述最多 1000 字
5. **封面图片** - 长文需要至少一张封面图（系统可能自动生成）

## 完整示例

```javascript
// 1. 点击发布按钮（首页底部导航）
browser act ref=e555 kind=click

// 2. 切换到新标签页
browser focus targetId=<新标签页 ID>

// 3. 点写长文
browser act ref=e111 kind=click

// 4. 点新的创作
browser act ref=e148 kind=click

// 5. 填标题
browser act fn="()=>{document.querySelector('[placeholder=\"输入标题\"]').value='标题';document.querySelector('[placeholder=\"输入标题\"]').dispatchEvent(new Event('input',{bubbles:true}))}" kind=evaluate

// 6. 点编辑器并输入正文
browser act ref=<编辑器 ref> kind=click
browser act fn="()=>{document.execCommand('insertText',false,'正文内容')}" kind=evaluate

// 7. 一键排版
browser act ref=<一键排版 ref> kind=click

// 8. 下一步
browser act ref=<下一步 ref> kind=click

// 9. 填描述
browser act ref=<描述框 ref> kind=click
browser act fn="()=>{document.execCommand('insertText',false,'描述内容')}" kind=evaluate

// 10. 发布
browser act ref=<发布按钮 ref> kind=click
```

## 与评论功能的区别

| 功能 | 输入方式 | 关键事件 |
|------|---------|---------|
| 评论 | `innerText + input event` | contenteditable 元素 |
| 长文正文 | `execCommand('insertText')` | 富文本编辑器 |
| 长文描述 | `execCommand('insertText')` | 富文本编辑器 |
| 标题 | `value + input event` | 普通 input 元素 |

## 失败排查

1. **内容输不进去** - 检查是否用对了输入方式
2. **字数不增加** - 说明输入没生效，换 execCommand
3. **按钮 disabled** - 检查是否满足前置条件（如封面、标题等）
4. **ref 找不到** - 页面变了，重新 snapshot
