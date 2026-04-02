#!/usr/bin/env node
/**
 * 板块热度探测
 *
 * 数据源：
 *   1. 雪球热搜（CDP浏览器）
 *   2. research-mcp 财经新闻
 *
 * 用法：
 *   node sector-heat.mjs              # 雪球 + 新闻
 *   node sector-heat.mjs --xueqiu     # 只看雪球
 *   node sector-heat.mjs --news       # 只看新闻
 *
 * 依赖：
 *   - CDP 浏览器实例在 9222 端口（xhs-browser.mjs）
 *   - bot7 的 research-mcp
 */

import { exec } from 'child_process';
import { promisify } from 'util';
import { chromium } from 'playwright';
const execAsync = promisify(exec);

const WS = '/home/rooot/.openclaw/workspace-bot7';
const CDP_URL = 'http://localhost:9222';

const mcpCall = (cmd) =>
  execAsync(`cd ${WS} && npx mcporter call '${cmd}' 2>/dev/null`, { timeout: 20000 })
    .then(r => r.stdout).catch(() => '[]');

// ========== 雪球热搜 ==========
async function getXueqiuHot() {
  let browser;
  try {
    browser = await chromium.connectOverCDP(CDP_URL);
  } catch {
    console.error('无法连接 CDP 9222，请先启动 xhs-browser.mjs');
    return [];
  }

  const context = browser.contexts()[0];
  let page = context.pages().find(p => p.url().includes('xueqiu.com'));

  if (!page) {
    page = await context.newPage();
    await page.goto('https://xueqiu.com', { waitUntil: 'domcontentloaded', timeout: 30000 });
  } else {
    await page.reload({ waitUntil: 'domcontentloaded', timeout: 30000 });
  }
  await page.waitForTimeout(3000);

  const topics = await page.evaluate(() => {
    const results = [];
    const headers = document.querySelectorAll('h2, h3, .title, [class*="title"]');
    for (const h of headers) {
      if (h.innerText.includes('热门话题')) {
        const parent = h.closest('div, section, aside');
        if (parent) {
          const items = parent.querySelectorAll('a');
          items.forEach(a => {
            const text = a.innerText.trim();
            if (text.length > 4 && text.length < 80) results.push(text);
          });
        }
        break;
      }
    }
    return results;
  });

  return topics;
}

// ========== research-mcp 新闻 ==========
async function getNewsHot() {
  const queries = [
    '板块异动 资金流入 主力',
    '机构调研 行业景气',
    '北向资金 加仓 板块',
    '概念股 龙头 涨幅',
    '跌停 板块 暴跌',
    'ETF资金流入 板块 抄底',
    '恒生科技 港股通 恐慌',
    '美股 纳指 科技股',
  ];

  const results = await Promise.all(
    queries.map(q => mcpCall(`research-mcp.news_search(query: "${q}", top_k: 5, search_day_ago: 1)`))
  );

  const allNews = [];
  for (const raw of results) {
    try { allNews.push(...JSON.parse(raw)); } catch {}
  }

  // 去重 + 只保留今天的（ID前缀为今天日期 YYYYMMDD）
  const today = new Date().toISOString().slice(0, 10).replace(/-/g, '');
  const seen = new Set();
  const unique = allNews.filter(item => {
    if (seen.has(item[0])) return false;
    seen.add(item[0]);
    return item[0].startsWith(today);
  });

  // 过滤掉内容里提到昨天日期或"昨日"的
  const now = new Date();
  const yesterday = new Date(now - 86400000);
  const ydStr = `${yesterday.getMonth() + 1}月${yesterday.getDate()}日`;
  const filtered = unique.filter(item => {
    const text = item[1];
    return !text.includes(ydStr) && !text.includes('昨日') && !text.includes('昨天');
  });

  // 提取摘要文本
  return filtered.map(item => item[1]).filter(Boolean);
}

// ========== main ==========
const args = process.argv.slice(2);
const xueqiuOnly = args.includes('--xueqiu');
const newsOnly = args.includes('--news');
const runBoth = !xueqiuOnly && !newsOnly;

let xueqiuTopics = [];
let newsItems = [];

if (xueqiuOnly || runBoth) {
  xueqiuTopics = await getXueqiuHot();
  console.log(`=== 雪球热搜 TOP${xueqiuTopics.length} ===\n`);
  xueqiuTopics.forEach((t, i) => console.log(`${String(i + 1).padStart(2)}. ${t}`));
  console.log();
}

if (newsOnly || runBoth) {
  newsItems = await getNewsHot();
  console.log(`=== 财经新闻热点（${newsItems.length}条）===\n`);
  newsItems.slice(0, 20).forEach((n, i) => {
    const match = n.match(/\['(.+?)'\]/);
    const text = match ? match[1] : n.slice(0, 120);
    console.log(`${String(i + 1).padStart(2)}. ${text.slice(0, 100)}`);
  });
}

// ========== 写入 SKILL.md ==========
const SKILL_PATH = '/home/rooot/.openclaw/workspace/skills/xhs-topic-collector/SKILL.md';

import { readFileSync, writeFileSync } from 'fs';

try {
  const skill = readFileSync(SKILL_PATH, 'utf-8');
  const startTag = '<!-- sector-heat-start -->';
  const endTag = '<!-- sector-heat-end -->';
  const startIdx = skill.indexOf(startTag);
  const endIdx = skill.indexOf(endTag);

  if (startIdx === -1 || endIdx === -1) {
    console.error('SKILL.md 中未找到 sector-heat 标记');
  } else {
    // 拼注入内容
    const now = new Date().toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false });
    let inject = `${startTag}\n## 板块热度探测（自动更新：${now}）\n\n\`\`\`\n`;

    // 雪球部分（从上面的变量拿）
    if (typeof xueqiuTopics !== 'undefined' && xueqiuTopics.length > 0) {
      inject += `=== 雪球热搜 TOP${xueqiuTopics.length} ===\n\n`;
      xueqiuTopics.forEach((t, i) => { inject += `${String(i + 1).padStart(2)}. ${t}\n`; });
      inject += '\n';
    }

    if (typeof newsItems !== 'undefined' && newsItems.length > 0) {
      inject += `=== 财经新闻热点（${newsItems.length}条）===\n\n`;
      newsItems.slice(0, 20).forEach((n, i) => {
        const match = n.match(/\['(.+?)'\]/);
        const text = match ? match[1] : n.slice(0, 120);
        inject += `${String(i + 1).padStart(2)}. ${text.slice(0, 100)}\n`;
      });
    }

    inject += `\`\`\`\n\n${endTag}`;

    const newSkill = skill.slice(0, startIdx) + inject + skill.slice(endIdx + endTag.length);
    writeFileSync(SKILL_PATH, newSkill);
    console.log(`\n✅ 已写入 ${SKILL_PATH}`);
  }
} catch (e) {
  console.error('写入 SKILL.md 失败:', e.message);
}

process.exit(0);
