#!/usr/bin/env node
/**
 * 板块热度探测
 *
 * 数据源：雪球热搜（Playwright 无头浏览器）
 *
 * 用法：
 *   node sector-heat.mjs              # 雪球热搜 + 热股榜
 *   node sector-heat.mjs --xueqiu     # 只看雪球热搜
 *
 * 依赖：playwright（npm install playwright）
 */

import { chromium } from 'playwright';
import { readFileSync, writeFileSync } from 'fs';

const SKILL_PATH = '/home/rooot/.openclaw/workspace/skills/utility/xhs-topic-collector/SKILL.md';

// 确保进程退出时杀干净浏览器（timeout SIGTERM 等场景）
let _browser = null;
for (const sig of ['SIGTERM', 'SIGINT', 'SIGHUP']) {
  process.on(sig, () => { _browser?.close().catch(() => {}); process.exit(1); });
}
process.on('exit', () => { _browser?.process()?.kill('SIGKILL'); });

// ========== 雪球热搜 ==========
async function getXueqiuHot() {
  let browser;
  try {
    browser = _browser = await chromium.launch({
      headless: true,
      executablePath: '/home/rooot/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome',
    });
    const page = await browser.newPage();
    await page.goto('https://xueqiu.com', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(3000);

    // 热门话题
    const topics = await page.evaluate(() => {
      const results = [];
      const rows = document.querySelectorAll('table tr');
      let inHotTopic = false;
      for (const row of rows) {
        const cells = row.querySelectorAll('td');
        if (cells.length >= 2) {
          const rank = cells[0]?.innerText?.trim();
          const text = cells[1]?.innerText?.trim();
          if (rank && text && /^\d+$/.test(rank) && text.length > 4 && text.length < 80) {
            results.push(text);
          }
        }
      }
      // 从 "热门话题" heading 下面的 table 取
      const heading = [...document.querySelectorAll('h3')].find(h => h.textContent.includes('热门话题'));
      if (heading) {
        const table = heading.closest('div')?.querySelector('table');
        if (table) {
          const items = [];
          for (const row of table.querySelectorAll('tr')) {
            const cells = row.querySelectorAll('td');
            if (cells.length >= 2) {
              const text = cells[1]?.innerText?.trim();
              if (text) items.push(text);
            }
          }
          if (items.length > 0) return items;
        }
      }
      return results;
    });

    // 热股榜 — 表格有 thead/tbody，列为：排名 | 名称 | (空) | 涨跌幅
    const hotStocks = await page.evaluate(() => {
      const heading = [...document.querySelectorAll('h3')].find(h => h.textContent.includes('热股榜'));
      if (!heading) return [];
      // 向上找到包含 heading 和 table 的最近容器
      let container = heading.parentElement;
      let table = null;
      while (container && !table) {
        table = container.querySelector('table tbody');
        if (!table) container = container.parentElement;
      }
      if (!table) return [];
      const items = [];
      for (const row of table.querySelectorAll('tr')) {
        const cells = row.querySelectorAll('td');
        if (cells.length >= 3) {
          const rank = cells[0]?.innerText?.trim();
          const name = cells[1]?.innerText?.trim();
          const pct = cells[cells.length - 1]?.innerText?.trim();
          if (name && pct && pct.includes('%')) items.push({ rank, name, pct });
        }
      }
      return items;
    });

    await browser.close();
    return { topics, hotStocks };
  } catch (e) {
    console.error('Playwright 抓取失败:', e.message);
    if (browser) await browser.close().catch(() => {});
    return { topics: [], hotStocks: [] };
  }
}

// ========== main ==========
const { topics, hotStocks } = await getXueqiuHot();

console.log(`=== 雪球热搜 TOP${topics.length} ===\n`);
topics.forEach((t, i) => console.log(`${String(i + 1).padStart(2)}. ${t}`));
console.log();

if (hotStocks.length > 0) {
  console.log(`=== 热股榜 TOP${hotStocks.length} ===\n`);
  hotStocks.forEach(s => console.log(`${String(s.rank).padStart(2)}. ${s.name}  ${s.pct}`));
  console.log();
}

// ========== 写入 SKILL.md ==========
try {
  const skill = readFileSync(SKILL_PATH, 'utf-8');
  const startTag = '<!-- sector-heat-start -->';
  const endTag = '<!-- sector-heat-end -->';
  const startIdx = skill.indexOf(startTag);
  const endIdx = skill.indexOf(endTag);

  if (startIdx !== -1 && endIdx !== -1) {
    const now = new Date().toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false });
    let inject = `${startTag}\n## 板块热度探测（自动更新：${now}）\n\n\`\`\`\n`;

    if (topics.length > 0) {
      inject += `=== 雪球热搜 TOP${topics.length} ===\n\n`;
      topics.forEach((t, i) => { inject += `${String(i + 1).padStart(2)}. ${t}\n`; });
      inject += '\n';
    }

    if (hotStocks.length > 0) {
      inject += `=== 热股榜 TOP${hotStocks.length} ===\n\n`;
      hotStocks.forEach(s => { inject += `${String(s.rank).padStart(2)}. ${s.name}  ${s.pct}\n`; });
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
