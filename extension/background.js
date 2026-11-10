// background.js - FactGuard Chrome Extension Service Worker

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "factguard-verify-selection",
    title: "Verify with FactGuard: \"%s\"",
    contexts: ["selection"]
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "factguard-verify-selection" && info.selectionText) {
    const claim = info.selectionText.trim();
    // Save to storage for the popup to read immediately
    chrome.storage.local.set({ pendingClaim: claim }, () => {
      // In Manifest V3, open popup or notify
      if (chrome.action && chrome.action.openPopup) {
        chrome.action.openPopup().catch(() => {
          // If openPopup is restricted, user can click the extension icon
        });
      }
    });
  }
});
