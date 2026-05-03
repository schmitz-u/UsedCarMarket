import type { ParsedListing, VehicleListing, PriceHistoryEntry } from '../types/canonical';

const DB_NAME = 'UsedVehicleMarketDB';
const DB_VERSION = 1;

let dbInstance: IDBDatabase | null = null;

export function openDB(): Promise<IDBDatabase> {
  if (dbInstance) return Promise.resolve(dbInstance);
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains('vehicle_listings')) {
        const store = db.createObjectStore('vehicle_listings', { keyPath: 'id', autoIncrement: true });
        store.createIndex('url', 'url', { unique: true });
      }
      if (!db.objectStoreNames.contains('listing_price_history')) {
        const histStore = db.createObjectStore('listing_price_history', { keyPath: 'id', autoIncrement: true });
        histStore.createIndex('vehicle_listing_id', 'vehicle_listing_id', { unique: false });
      }
    };
    request.onsuccess = (event) => {
      dbInstance = (event.target as IDBOpenDBRequest).result;
      resolve(dbInstance);
    };
    request.onerror = () => reject(request.error);
  });
}

export async function upsertListing(listing: ParsedListing): Promise<{ isNew: boolean; listingId: number }> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(['vehicle_listings', 'listing_price_history'], 'readwrite');
    const listingsStore = tx.objectStore('vehicle_listings');
    const historyStore = tx.objectStore('listing_price_history');

    const urlIndex = listingsStore.index('url');
    const getReq = urlIndex.get(listing.url);

    getReq.onsuccess = () => {
      const existing: VehicleListing | undefined = getReq.result;
      const now = new Date().toISOString();

      if (existing) {
        const updated: VehicleListing = {
          ...existing,
          price_amount: listing.price_amount,
          price_currency: listing.price_currency,
          price_negotiable: listing.price_negotiable,
        };
        const putReq = listingsStore.put(updated);
        putReq.onsuccess = () => {
          const listingId = existing.id!;
          if (listing.price_amount !== null) {
            const entry: PriceHistoryEntry = {
              vehicle_listing_id: listingId,
              observed_price_amount: listing.price_amount,
              observed_price_currency: listing.price_currency,
              observed_at_utc: now,
              source_event_type: 'recapture',
            };
            historyStore.add(entry);
          }
          resolve({ isNew: false, listingId });
        };
        putReq.onerror = () => reject(putReq.error);
      } else {
        const newListing: VehicleListing = {
          ...listing,
          extraction_timestamp_utc: now,
          raw_payload_json: JSON.stringify(listing),
        };
        const addReq = listingsStore.add(newListing);
        addReq.onsuccess = () => {
          const listingId = addReq.result as number;
          if (listing.price_amount !== null) {
            const entry: PriceHistoryEntry = {
              vehicle_listing_id: listingId,
              observed_price_amount: listing.price_amount,
              observed_price_currency: listing.price_currency,
              observed_at_utc: now,
              source_event_type: 'initial_capture',
            };
            historyStore.add(entry);
          }
          resolve({ isNew: true, listingId });
        };
        addReq.onerror = () => reject(addReq.error);
      }
    };
    getReq.onerror = () => reject(getReq.error);
    tx.onerror = () => reject(tx.error);
  });
}

export async function checkListingStatus(url: string): Promise<{ stored: boolean; listing?: VehicleListing }> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('vehicle_listings', 'readonly');
    const store = tx.objectStore('vehicle_listings');
    const index = store.index('url');
    const req = index.get(url);
    req.onsuccess = () => {
      if (req.result) {
        resolve({ stored: true, listing: req.result as VehicleListing });
      } else {
        resolve({ stored: false });
      }
    };
    req.onerror = () => reject(req.error);
  });
}

export async function getAllListings(): Promise<VehicleListing[]> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('vehicle_listings', 'readonly');
    const store = tx.objectStore('vehicle_listings');
    const req = store.getAll();
    req.onsuccess = () => resolve(req.result as VehicleListing[]);
    req.onerror = () => reject(req.error);
  });
}
