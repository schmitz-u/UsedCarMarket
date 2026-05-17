import { upsertListing, checkListingStatus, getAllListings } from '../db/indexeddb';
import type { ExtensionMessage, SaveListingResponse, CheckListingStatusResponse, GetAllListingsResponse } from '../types/messages';

chrome.runtime.onMessage.addListener((message: ExtensionMessage, _sender, sendResponse) => {
  if (message.type === 'SAVE_LISTING') {
    upsertListing(message.payload)
      .then(({ isNew, listingId }) => {
        const response: SaveListingResponse = { success: true, isNew, listingId };
        sendResponse(response);
        chrome.runtime.sendMessage({ type: 'LISTING_SAVED', payload: { isNew, listingId } }).catch(() => {});
      })
      .catch((err: unknown) => {
        const response: SaveListingResponse = { success: false, isNew: false, listingId: -1, error: String(err) };
        sendResponse(response);
      });
    return true;
  }

  if (message.type === 'CHECK_LISTING_STATUS') {
    checkListingStatus(message.payload.url)
      .then((result) => {
        const response: CheckListingStatusResponse = result;
        sendResponse(response);
      })
      .catch(() => {
        const response: CheckListingStatusResponse = { stored: false };
        sendResponse(response);
      });
    return true;
  }

  if (message.type === 'GET_ALL_LISTINGS') {
    getAllListings()
      .then((listings) => {
        const response: GetAllListingsResponse = { listings };
        sendResponse(response);
      })
      .catch(() => {
        const response: GetAllListingsResponse = { listings: [] };
        sendResponse(response);
      });
    return true;
  }

  return false;
});

chrome.action.onClicked.addListener((tab) => {
  if (tab.windowId !== undefined) {
    chrome.sidePanel.open({ windowId: tab.windowId }).catch(() => {});
  }
});
