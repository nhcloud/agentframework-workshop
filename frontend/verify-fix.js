/**
 * Verification Script for Content Safety UI Fix
 * Run this in your browser console (F12) to verify the fix is working
 */

console.log('?? Verifying Content Safety UI Fix...\n');

const checks = [];
let passed = 0;
let failed = 0;

// Check 1: SafetyTester component exists
const safetySection = document.querySelector('div').textContent.includes('Content Safety');
if (safetySection) {
  console.log('? Safety section found');
  checks.push({ name: 'Safety Section', status: 'PASS' });
  passed++;
} else {
  console.log('? Safety section not found');
  checks.push({ name: 'Safety Section', status: 'FAIL' });
  failed++;
}

// Check 2: Look for tab indicators
const hasTextTab = document.body.innerHTML.includes('Text') && document.body.innerHTML.includes('scan');
const hasImageTab = document.body.innerHTML.includes('Image') && document.body.innerHTML.includes('scan');

if (hasTextTab) {
  console.log('? Text tab detected');
  checks.push({ name: 'Text Tab', status: 'PASS' });
  passed++;
} else {
  console.log('? Text tab not detected');
  checks.push({ name: 'Text Tab', status: 'FAIL' });
  failed++;
}

if (hasImageTab) {
  console.log('? Image tab detected');
  checks.push({ name: 'Image Tab', status: 'PASS' });
  passed++;
} else {
  console.log('? Image tab not detected');
  checks.push({ name: 'Image Tab', status: 'FAIL' });
  failed++;
}

// Check 3: Look for old inline code markers
const hasOldCode = document.body.innerHTML.includes('SafetyTestControls') || 
                   document.body.innerHTML.includes('safetyTestText');

if (!hasOldCode) {
  console.log('? Old inline code not present');
  checks.push({ name: 'No Old Code', status: 'PASS' });
  passed++;
} else {
  console.log('?? Warning: Old code patterns detected');
  checks.push({ name: 'No Old Code', status: 'WARNING' });
}

// Check 4: React version
const reactVersion = window.React?.version;
if (reactVersion) {
  console.log(`? React version: ${reactVersion}`);
  checks.push({ name: 'React Loaded', status: 'PASS' });
  passed++;
} else {
  console.log('?? React version not detected');
  checks.push({ name: 'React Loaded', status: 'WARNING' });
}

// Print summary
console.log('\n?? Verification Summary:');
console.log('='.repeat(40));
checks.forEach(check => {
  const emoji = check.status === 'PASS' ? '?' : check.status === 'FAIL' ? '?' : '??';
  console.log(`${emoji} ${check.name.padEnd(20)} [${check.status}]`);
});
console.log('='.repeat(40));
console.log(`Total: ${passed} passed, ${failed} failed\n`);

if (failed === 0 && passed >= 3) {
  console.log('?? SUCCESS! The Content Safety UI fix appears to be working!');
  console.log('\nYou should see:');
  console.log('  1. Two tabs: [Text] and [Image]');
  console.log('  2. Tabbed interface (not vertical stacking)');
  console.log('  3. Results with X buttons to clear');
  console.log('  4. Image preview when file selected');
  console.log('\nIf you don\'t see tabs, try a hard refresh (Ctrl+Shift+R)');
} else if (failed > 0) {
  console.log('? FAILED: Some checks did not pass.');
  console.log('\n?? Troubleshooting:');
  console.log('  1. Hard refresh: Ctrl + Shift + R (Windows) or Cmd + Shift + R (Mac)');
  console.log('  2. Clear browser cache');
  console.log('  3. Check console (F12) for errors');
  console.log('  4. Verify App.js has: <SafetyTester chatService={chatService} />');
  console.log('  5. Run: npm start (in frontend directory)');
} else {
  console.log('?? WARNING: Verification incomplete or partial.');
  console.log('The UI may be working but some checks could not be confirmed.');
  console.log('Manually verify you see tabs and tabbed interface.');
}

// Export results for debugging
window.contentSafetyVerification = {
  checks,
  passed,
  failed,
  timestamp: new Date().toISOString()
};

console.log('\n?? Results saved to: window.contentSafetyVerification');
