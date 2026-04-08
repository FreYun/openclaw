/**
 * 异动追踪 — 数据采集脚本
 *
 * 从韭研公社 (jiuyangongshe.com/action) 爬取异动解析数据，
 * 生成板块详情 Markdown。LLM 分析由 bot 自行完成，不在此脚本中。
 *
 * 用法:
 *   node scrape_action.js                      # 爬取今日数据
 *   node scrape_action.js 2026-04-08           # 指定日期
 *   node scrape_action.js --skip-scrape        # 跳过爬取，用已有 latest
 *   node scrape_action.js --data-dir /path     # 自定义数据输出目录
 *
 * 前置:
 *   npm install playwright
 *   同目录下需要 auth.json（Playwright storageState）
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// --- Config ---
const SCRIPT_DIR = __dirname;

function resolveDataDir(args) {
  const idx = args.indexOf('--data-dir');
  if (idx !== -1 && args[idx + 1]) return args[idx + 1];
  return path.join(SCRIPT_DIR, 'data');
}

// --- Utilities ---
function sanitizeFilename(name) {
  return name.replace(/[<>:"/\\|?*]/g, '_').replace(/\s+/g, '_');
}

function ensureDirs(dirs) {
  dirs.forEach(dir => {
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  });
}

function timestamp() {
  const now = new Date();
  const pad = n => String(n).padStart(2, '0');
  return `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
}

function timestampReadable() {
  const now = new Date();
  const pad = n => String(n).padStart(2, '0');
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`;
}

function dateStr(date) {
  const d = date || new Date();
  const pad = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

// ============================================================
// Phase 0: Scrape action data
// ============================================================
function parseActionField(fieldData) {
  const sectors = [];
  for (const field of fieldData) {
    if (!field.list || field.list.length === 0) continue;
    const stocks = field.list.map(s => {
      const ai = s.article?.action_info || {};
      return {
        code: s.code,
        name: s.name,
        article_id: s.article?.article_id || '',
        time: ai.time || '',
        num: ai.num || '',
        price: ai.price ? ai.price / 100 : null,
        change_pct: ai.shares_range ? ai.shares_range / 100 : null,
        day: ai.day || null,
        edition: ai.edition || null,
        expound: ai.expound || '',
        is_recommend: ai.is_recommend || 0,
        sort_no: ai.sort_no || 0,
        like_count: s.article?.like_count || 0,
        comment_count: s.article?.comment_count || 0,
        forward_count: s.article?.forward_count || 0,
      };
    });
    sectors.push({
      action_field_id: field.action_field_id || '',
      name: field.name,
      reason: field.reason || '',
      count: stocks.length,
      stocks,
    });
  }
  return sectors;
}

async function scrapeAction(targetDate, authPath, actionDir) {
  const ts = timestamp();
  console.log('=== Phase 0: 爬取异动数据 ===');

  if (!fs.existsSync(authPath)) {
    console.error(`错误: auth.json 不存在 (${authPath})，请先登录韭研公社`);
    console.error('登录方法: 用 bot 的 browser 打开 jiuyangongshe.com，扫码登录后导出 storageState');
    process.exit(1);
  }

  const browser = await chromium.launch();
  const context = await browser.newContext({ storageState: authPath });
  const page = await context.newPage();
  await page.setViewportSize({ width: 1400, height: 900 });

  let fieldData = null;
  page.on('response', async (response) => {
    if (response.url().includes('action/field') && response.status() === 200) {
      try {
        const json = await response.json();
        if (json.errCode === '0') fieldData = json.data;
      } catch (e) {}
    }
  });

  console.log('Loading /action ...');
  await page.goto('https://www.jiuyangongshe.com/action', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);

  if (!fieldData) {
    try {
      const tab = page.locator('text=全部异动解析').first();
      if (await tab.isVisible()) {
        await tab.click();
        await page.waitForTimeout(3000);
      }
    } catch (e) {}
  }

  if (!fieldData) {
    console.log('Reloading...');
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);
  }

  if (!fieldData) {
    console.error('Failed to capture action data');
    await browser.close();
    throw new Error('无法获取异动数据');
  }

  const sectors = parseActionField(fieldData);
  const totalStocks = sectors.reduce((sum, s) => sum + s.count, 0);
  console.log(`获取 ${totalStocks} 只个股，${sectors.length} 个板块`);

  // Screenshots
  await page.screenshot({
    path: path.join(actionDir, `action_all_${ts}.png`),
    fullPage: true
  });

  try {
    const tabs = await page.locator('div, span, a').filter({ hasText: /^涨停简图$/ }).all();
    for (const t of tabs) {
      if (await t.isVisible()) {
        await t.click();
        await page.waitForTimeout(3000);
        await page.screenshot({
          path: path.join(actionDir, `action_jiantu_${ts}.png`),
          fullPage: true
        });
        console.log('涨停简图 screenshot saved');
        break;
      }
    }
  } catch (e) {
    console.log('Warning: 涨停简图 not captured:', e.message);
  }

  // Save data
  const saveData = {
    date: targetDate,
    scrape_time: ts,
    total_stocks: totalStocks,
    sectors,
  };

  const latestPath = path.join(actionDir, 'action_latest.json');
  const snapshotPath = path.join(actionDir, `action_${ts}.json`);
  fs.writeFileSync(snapshotPath, JSON.stringify(saveData, null, 2), 'utf-8');
  console.log('Snapshot:', snapshotPath);
  fs.writeFileSync(latestPath, JSON.stringify(saveData, null, 2), 'utf-8');
  console.log('Latest:', latestPath);

  await browser.close();
  return saveData;
}

// ============================================================
// Phase A: Build sector detail markdowns
// ============================================================
function buildSectorMarkdown(sector, date) {
  let md = `# ${sector.name}\n\n`;
  md += `## 基本信息\n`;
  md += `- 日期: ${date}\n`;
  md += `- 题材: ${sector.reason || '（无）'}\n`;
  md += `- 涨停股数量: ${sector.count}\n\n`;

  md += `## 个股列表\n\n`;
  md += `| 代码 | 名称 | 涨幅% | 连板 | 涨停时间 | 一字板 | 点赞 | 评论 | 转发 |\n`;
  md += `|------|------|-------|------|----------|--------|------|------|------|\n`;
  for (const s of sector.stocks) {
    const pct = s.change_pct != null ? s.change_pct.toFixed(2) : '-';
    const num = s.num || '-';
    const time = s.time || '-';
    const rec = s.is_recommend ? '是' : '-';
    md += `| ${s.code} | ${s.name} | ${pct} | ${num} | ${time} | ${rec} | ${s.like_count} | ${s.comment_count} | ${s.forward_count} |\n`;
  }
  md += '\n';

  md += `## 个股分析\n\n`;
  for (const s of sector.stocks) {
    md += `### ${s.name}（${s.code}）\n`;
    if (s.num) md += `- 连板: ${s.num}\n`;
    if (s.change_pct != null) md += `- 涨幅: ${s.change_pct.toFixed(2)}%\n`;
    if (s.price != null) md += `- 价格: ${s.price}元\n`;
    md += '\n';
    md += (s.expound || '（无分析）').replace(/\\n/g, '\n') + '\n\n';
  }

  return md;
}

function extractSection(md, header) {
  const regex = new RegExp(`## ${header.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\n([\\s\\S]*?)(?=\\n## |$)`);
  const match = md.match(regex);
  return match ? match[1].trim() : '';
}

function extractChangelog(md) {
  const marker = '## 变更记录\n';
  const idx = md.indexOf(marker);
  return idx >= 0 ? md.substring(idx + marker.length) : '';
}

function diffSectorDetail(oldMd, newMd) {
  const changes = [];
  const sections = ['基本信息', '个股列表', '个股分析'];
  for (const sec of sections) {
    const oldSec = extractSection(oldMd, sec);
    const newSec = extractSection(newMd, sec);
    if (oldSec !== newSec && oldSec !== '') {
      changes.push(sec);
    }
  }
  return changes;
}

function processSector(sector, date, datePart, index, total, detailsDir) {
  const safeName = sanitizeFilename(sector.name);
  const detailPath = path.join(detailsDir, `${safeName}_${datePart}.md`);
  console.log(`[${index + 1}/${total}] 处理板块: ${sector.name} (${sector.count}只)`);

  const newMd = buildSectorMarkdown(sector, date);

  let changelogSection = '';
  if (fs.existsSync(detailPath)) {
    const oldFull = fs.readFileSync(detailPath, 'utf-8');
    changelogSection = extractChangelog(oldFull);

    const changelogIdx = oldFull.indexOf('## 变更记录\n');
    const oldMdBody = changelogIdx >= 0 ? oldFull.substring(0, changelogIdx).trim() : oldFull.trim();
    const changedSections = diffSectorDetail(oldMdBody, newMd.trim());

    if (changedSections.length > 0) {
      const ts = timestampReadable();
      changelogSection = `- **${ts}** — ${changedSections.join('、')}有更新\n` + changelogSection;
      console.log(`  变更: ${changedSections.join('、')}`);
    } else {
      console.log(`  无变化`);
    }
  } else {
    const ts = timestampReadable();
    changelogSection = `- **${ts}** — 首次生成\n`;
  }

  const finalMd = newMd + `## 变更记录\n${changelogSection}`;
  fs.writeFileSync(detailPath, finalMd, 'utf-8');
  console.log(`  保存: ${detailPath}`);

  return { name: sector.name, markdown: newMd };
}

// ============================================================
// Main
// ============================================================
async function main() {
  const args = process.argv.slice(2);
  const skipScrape = args.includes('--skip-scrape');
  const targetDate = args.find(a => /^\d{4}-\d{2}-\d{2}$/.test(a)) || dateStr();
  const authPath = path.join(SCRIPT_DIR, 'auth.json');

  const dataDir = resolveDataDir(args);
  const actionDir = path.join(dataDir, 'action');
  const detailsDir = path.join(actionDir, 'details');
  const latestPath = path.join(actionDir, 'action_latest.json');

  ensureDirs([dataDir, actionDir, detailsDir]);

  let data;
  if (skipScrape) {
    if (!fs.existsSync(latestPath)) {
      console.error(`错误: ${latestPath} 不存在，请先运行爬取（去掉 --skip-scrape）`);
      process.exit(1);
    }
    data = JSON.parse(fs.readFileSync(latestPath, 'utf-8'));
    console.log(`加载已有数据: ${data.date}, ${data.total_stocks} 只个股, ${data.sectors.length} 个板块\n`);
  } else {
    data = await scrapeAction(targetDate, authPath, actionDir);
    console.log('');
  }

  const datePart = data.scrape_time || data.date.replace(/-/g, '');

  // Phase A: Process sector details
  console.log('=== Phase A: 生成板块详情 ===');
  const detailResults = [];
  for (let i = 0; i < data.sectors.length; i++) {
    const result = processSector(data.sectors[i], data.date, datePart, i, data.sectors.length, detailsDir);
    detailResults.push(result);
  }
  console.log(`\n板块详情处理完成: ${detailResults.length}/${data.sectors.length}`);

  // Print summary
  console.log(`\n=== ${data.date} 异动解析摘要 ===`);
  console.log(`总计: ${data.total_stocks} 只\n`);
  data.sectors.forEach(s => {
    console.log(`【${s.name}】${s.count} 只`);
    if (s.reason) console.log(`  题材: ${s.reason}`);
    s.stocks.forEach(st => {
      const pct = st.change_pct ? st.change_pct.toFixed(2) + '%' : '';
      const rec = st.is_recommend ? ' [一字]' : '';
      console.log(`  ${st.code} ${st.name} ${pct} ${st.num} ${st.time}${rec}`);
    });
    console.log('');
  });

  // Output paths for bot to read
  console.log('=== 输出文件 ===');
  console.log(`数据: ${latestPath}`);
  console.log(`详情目录: ${detailsDir}`);
  console.log('全部完成!');
}

main().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
