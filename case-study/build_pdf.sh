#!/usr/bin/env bash
# Rebuild case-study.pdf from case-study.md. Needs pandoc and Node with Playwright (Chromium).
set -euo pipefail
cd "$(dirname "$0")"
pandoc case-study.md -s --embed-resources --resource-path=.:.. -c style.css -o /tmp/case-study.html
node -e "
const {chromium} = require('playwright');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage();
  await p.goto('file:///tmp/case-study.html');
  await p.pdf({path: 'case-study.pdf', format: 'A4', preferCSSPageSize: true, printBackground: true});
  await b.close();
})();"
echo "wrote case-study.pdf"
