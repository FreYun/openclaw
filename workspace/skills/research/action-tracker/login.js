/**
 * 韭研公社登录助手 — 手机号+验证码登录，保存 auth.json
 *
 * 用法:
 *   node login.js                     # 交互式输入手机号
 *   node login.js 13800138000         # 命令行传入手机号
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

const AUTH_PATH = path.join(__dirname, 'auth.json');
const DATA_DIR = path.join(__dirname, 'data');

function ask(question) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise(resolve => {
    rl.question(question, answer => {
      rl.close();
      resolve(answer.trim());
    });
  });
}

async function main() {
  if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });

  // Get phone number
  let phone = process.argv[2] || '';
  if (!phone) {
    phone = await ask('请输入手机号: ');
  }
  if (!/^1\d{10}$/.test(phone)) {
    console.error(`手机号格式不对: ${phone}`);
    process.exit(1);
  }

  console.log(`手机号: ${phone}`);
  console.log('启动浏览器...');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1400, height: 900 },
    userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
  });
  const page = await context.newPage();

  console.log('打开韭研公社...');
  await page.goto('https://www.jiuyangongshe.com', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(2000);

  // Click login button
  console.log('点击登录...');
  try {
    await page.locator('.user-box .name').click({ timeout: 5000 });
    await page.waitForTimeout(2000);
  } catch (e) {
    // Fallback
    await page.locator('.user-box .user-info').click({ timeout: 5000 });
    await page.waitForTimeout(2000);
  }

  // Make sure we're on "手机快捷登录" tab
  try {
    const phoneTab = page.locator('text=手机快捷登录').first();
    if (await phoneTab.isVisible({ timeout: 2000 })) {
      await phoneTab.click();
      await page.waitForTimeout(500);
    }
  } catch (e) {}

  // Screenshot to confirm dialog
  const dialogPath = path.join(DATA_DIR, 'login_dialog.png');
  await page.screenshot({ path: dialogPath });
  console.log(`登录弹窗截图: ${dialogPath}`);

  // Fill phone number
  console.log('输入手机号...');
  const phoneInput = page.locator('input[placeholder*="手机号"], input[placeholder*="手机"], input[type="tel"]').first();
  await phoneInput.click();
  await phoneInput.fill(phone);
  await page.waitForTimeout(500);

  // Click "获取验证码"
  console.log('点击获取验证码...');
  const getCodeBtn = page.locator('text=获取验证码').first();
  await getCodeBtn.click();
  await page.waitForTimeout(1000);

  // Screenshot after clicking
  await page.screenshot({ path: path.join(DATA_DIR, 'login_code_sent.png') });

  // Wait for user to input verification code
  console.log('\n===================================');
  console.log('验证码已发送到你的手机');
  const code = await ask('请输入验证码: ');
  console.log('===================================\n');

  if (!code) {
    console.error('未输入验证码，退出');
    await browser.close();
    process.exit(1);
  }

  // Fill verification code
  console.log('输入验证码...');
  const codeInput = page.locator('input[placeholder*="验证码"]').first();
  await codeInput.click();
  await codeInput.fill(code);
  await page.waitForTimeout(500);

  // Click login button
  console.log('点击登录...');
  // The login button is the blue "登录" button in the modal
  const loginBtn = page.locator('.login-modal button, .modal button, button:has-text("登录"), .login-btn').first();
  try {
    await loginBtn.click({ timeout: 3000 });
  } catch (e) {
    // Try broader selector
    const allBtns = page.locator('button, [class*="btn"]').filter({ hasText: '登录' });
    await allBtns.first().click({ timeout: 3000 });
  }

  console.log('等待登录结果...');
  await page.waitForTimeout(3000);

  // Screenshot result
  await page.screenshot({ path: path.join(DATA_DIR, 'login_result.png') });

  // Check if login succeeded
  const cookies = await context.cookies();
  const hasToken = cookies.some(c =>
    c.name.includes('token') || c.name.includes('session') || c.name.includes('uid')
  );

  // Also check if the "登录注册" text is gone (replaced by username)
  let nameGone = false;
  try {
    const nameDiv = page.locator('.user-box .name');
    const nameText = await nameDiv.textContent({ timeout: 2000 });
    nameGone = !nameText.includes('登录注册');
  } catch (e) {}

  if (hasToken || nameGone) {
    console.log('登录成功!');

    // Navigate to action page to verify
    await page.goto('https://www.jiuyangongshe.com/action', { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(2000);
    await page.screenshot({ path: path.join(DATA_DIR, 'login_verified.png') });
    console.log('验证页面截图已保存');
  } else {
    console.log('登录状态不确定，仍然保存 auth.json');
    await page.screenshot({ path: path.join(DATA_DIR, 'login_uncertain.png') });
  }

  // Save auth
  const state = await context.storageState();
  fs.writeFileSync(AUTH_PATH, JSON.stringify(state, null, 2), 'utf-8');
  console.log(`\nauth.json 已保存: ${AUTH_PATH}`);
  console.log(`共 ${state.cookies.length} 个 cookie`);

  await browser.close();
  console.log('完成!');
}

main().catch(async err => {
  console.error('Error:', err.message);
  process.exit(1);
});
