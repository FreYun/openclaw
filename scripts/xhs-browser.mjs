#!/usr/bin/env node
/**
 * 小红书持久浏览器实例
 *
 * 用法：xvfb-run --auto-servernum node xhs-browser.mjs
 *
 * 启动后在 CDP 端口 9222 保持运行，其他脚本通过 connectOverCDP 连接。
 * 首次启动需要扫码登录，之后 user-data-dir 会保存登录态。
 */
import { chromium } from 'playwright';

const USER_DATA = '/home/rooot/.openclaw/browser/xhs-shared/user-data';

const browser = await chromium.launchPersistentContext(USER_DATA, {
  headless: false,
  executablePath: '/usr/bin/google-chrome',
  args: [
    '--no-sandbox',
    '--disable-gpu',
    '--remote-debugging-port=9222',
    '--disable-blink-features=AutomationControlled',
  ],
  viewport: { width: 1280, height: 800 },
  locale: 'zh-CN',
});

const page = browser.pages()[0] || await browser.newPage();
await page.goto('https://www.xiaohongshu.com/explore', { waitUntil: 'domcontentloaded', timeout: 30000 });
await page.waitForTimeout(3000);

// 检查是否需要登录
const needLogin = await page.evaluate(() => {
  return !!document.querySelector('[class*="qrcode"], .login-container, [class*="login-modal"]');
});

if (needLogin) {
  await page.screenshot({ path: '/tmp/xhs-browser-login.png' });
  console.log('需要扫码登录，截图已保存到 /tmp/xhs-browser-login.png');
} else {
  console.log('已登录');
}

console.log('CDP 端口: 9222');
console.log('浏览器保持运行中...');

// 保持运行
await new Promise(() => {});
