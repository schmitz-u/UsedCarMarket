import { getParser } from '../parsers/registry';
import type { CheckListingStatusResponse } from '../types/messages';

const currentUrl = window.location.href;
const parser = getParser(currentUrl);

if (!parser) {
  // Not a supported page, do nothing
} else {
  const badge = document.createElement('div');
  badge.id = 'ucma-badge';
  badge.style.cssText = `
    position: fixed;
    bottom: 20px;
    right: 20px;
    z-index: 999999;
    background: #1a1a2e;
    color: #fff;
    padding: 8px 14px;
    border-radius: 20px;
    font-family: sans-serif;
    font-size: 13px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    cursor: default;
  `;
  badge.textContent = '⏳ Checking...';
  document.body.appendChild(badge);

  chrome.runtime.sendMessage({ type: 'CHECK_LISTING_STATUS', payload: { url: currentUrl } }, (response: CheckListingStatusResponse) => {
    badge.textContent = response?.stored ? '✓ Stored' : '○ Not saved';
    badge.style.background = response?.stored ? '#1b5e20' : '#1a1a2e';
  });

  chrome.runtime.onMessage.addListener((message) => {
    if (message.type === 'TRIGGER_SAVE') {
      const parsed = parser.parse(document, currentUrl);
      chrome.runtime.sendMessage({ type: 'SAVE_LISTING', payload: parsed });
    }
    if (message.type === 'LISTING_SAVED') {
      badge.textContent = '✓ Stored';
      badge.style.background = '#1b5e20';
    }
  });
}
