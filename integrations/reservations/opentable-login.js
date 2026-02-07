import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const cookiesPath = path.join(__dirname, '.opentable-cookies.json');

async function loginFlow() {
  console.log('🚀 Launching browser for OpenTable login...\n');
  
  const browser = await chromium.launch({ 
    headless: false,
    args: [
      '--remote-debugging-port=9222',
      '--no-sandbox',
      '--disable-setuid-sandbox'
    ]
  });
  
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    viewport: { width: 1280, height: 720 }
  });
  
  const page = await context.newPage();
  
  console.log('📱 Navigating to OpenTable sign-in...');
  await page.goto('https://www.opentable.com/sign-in');
  await page.waitForLoadState('networkidle');
  
  console.log('\n✅ Browser ready!');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('Connect from your Mac Chrome:');
  console.log('  chrome://inspect/#devices');
  console.log('  → Configure → Add: 100.83.250.65:9222');
  console.log('  → Click "inspect" under Remote Target');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('\nLog in manually, complete 2FA, then press Enter here...\n');
  
  // Wait for user input
  await new Promise(resolve => {
    process.stdin.once('data', resolve);
  });
  
  // Check if logged in
  const cookies = await context.cookies();
  const isLoggedIn = cookies.some(c => c.name.includes('session') || c.name.includes('auth') || c.name.includes('user'));
  
  if (cookies.length > 5) {
    fs.writeFileSync(cookiesPath, JSON.stringify(cookies, null, 2));
    console.log(`\n✅ Saved ${cookies.length} cookies to ${cookiesPath}`);
    console.log('🎉 OpenTable is ready for automated bookings!');
  } else {
    console.log('\n⚠️  Few cookies found - login may not have completed');
    console.log('Saving anyway...');
    fs.writeFileSync(cookiesPath, JSON.stringify(cookies, null, 2));
  }
  
  await browser.close();
  process.exit(0);
}

loginFlow().catch(e => {
  console.error('Error:', e.message);
  process.exit(1);
});
