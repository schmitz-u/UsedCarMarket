import type { ParsedListing, VehicleListing } from './canonical';

export type MessageType =
  | 'SAVE_LISTING'
  | 'CHECK_LISTING_STATUS'
  | 'GET_ALL_LISTINGS'
  | 'LISTING_SAVED'
  | 'LISTING_STATUS'
  | 'ALL_LISTINGS'
  | 'OPEN_SIDE_PANEL';

export interface SaveListingMessage {
  type: 'SAVE_LISTING';
  payload: ParsedListing;
}

export interface CheckListingStatusMessage {
  type: 'CHECK_LISTING_STATUS';
  payload: { url: string };
}

export interface GetAllListingsMessage {
  type: 'GET_ALL_LISTINGS';
}

export type ExtensionMessage =
  | SaveListingMessage
  | CheckListingStatusMessage
  | GetAllListingsMessage;

export interface SaveListingResponse {
  success: boolean;
  isNew: boolean;
  listingId: number;
  error?: string;
}

export interface CheckListingStatusResponse {
  stored: boolean;
  listing?: VehicleListing;
}

export interface GetAllListingsResponse {
  listings: VehicleListing[];
}
