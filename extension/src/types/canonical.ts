export interface VehicleListing {
  id?: number;
  source_marketplace: string;
  listing_id: string | null;
  url: string;
  vehicle_type: string | null;
  brand: string | null;
  model: string | null;
  year: number | null;
  first_registration: string | null;
  mileage_km: number | null;
  previous_owner_count: number | null;
  price_amount: number | null;
  price_currency: string | null;
  price_negotiable: boolean | null;
  engine_displacement_cc: number | null;
  power_kw: number | null;
  fuel_type: string | null;
  transmission: string | null;
  color: string | null;
  vehicle_category: string | null;
  location_city: string | null;
  condition: string | null;
  extraction_timestamp_utc: string;
  raw_payload_json: string | null;
}

export interface PriceHistoryEntry {
  id?: number;
  vehicle_listing_id: number;
  observed_price_amount: number;
  observed_price_currency: string | null;
  observed_at_utc: string;
  source_event_type: 'initial_capture' | 'recapture';
}

export type ParsedListing = Omit<VehicleListing, 'id' | 'extraction_timestamp_utc' | 'raw_payload_json'>;
