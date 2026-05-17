import type { Parser } from './interface';
import type { ParsedListing } from '../types/canonical';

export class AutoScout24Parser implements Parser {
  matches(url: string): boolean {
    return url.includes('autoscout24.de/angebote/');
  }

  parse(document: Document, url: string): ParsedListing {
    let jsonLd: Record<string, unknown> | null = null;
    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
    for (const script of scripts) {
      try {
        const parsed = JSON.parse(script.textContent ?? '');
        if (parsed['@type'] === 'Product') {
          jsonLd = parsed;
          break;
        }
      } catch {
        // skip invalid JSON
      }
    }

    if (!jsonLd) {
      console.warn(`[autoscout24 parser] No Product JSON-LD found at ${url}`);
      return {
        source_marketplace: 'autoscout24.de',
        listing_id: null,
        url,
        vehicle_type: 'motorcycle',
        brand: null,
        model: null,
        year: null,
        first_registration: null,
        mileage_km: null,
        previous_owner_count: null,
        price_amount: null,
        price_currency: null,
        price_negotiable: null,
        engine_displacement_cc: null,
        power_kw: null,
        fuel_type: null,
        transmission: null,
        color: null,
        vehicle_category: null,
        location_city: null,
        condition: null,
      };
    }

    const offers = jsonLd['offers'] as Record<string, unknown> | undefined;
    const itemOffered = offers?.['itemOffered'] as Record<string, unknown> | undefined;
    const engines = itemOffered?.['vehicleEngine'] as Array<Record<string, unknown>> | undefined;
    const engine = engines?.[0];

    const price_amount = typeof offers?.['price'] === 'number' ? offers['price'] as number : null;
    const price_currency = typeof offers?.['priceCurrency'] === 'string' ? offers['priceCurrency'] as string : null;

    const price_negotiable = document.body.textContent?.includes('Verhandlungsbasis') ?? false;

    const mileageObj = itemOffered?.['mileageFromOdometer'] as Record<string, unknown> | undefined;
    const mileage_km = typeof mileageObj?.['value'] === 'number' ? mileageObj['value'] as number : null;

    const productionDate = typeof itemOffered?.['productionDate'] === 'string' ? itemOffered['productionDate'] as string : null;
    let first_registration: string | null = null;
    let year: number | null = null;
    if (productionDate) {
      const parts = productionDate.split('-');
      if (parts.length >= 2) {
        first_registration = `${parts[1]}/${parts[0]}`;
        year = parseInt(parts[0], 10) || null;
      }
    }

    const previous_owner_count = typeof itemOffered?.['numberOfPreviousOwners'] === 'number'
      ? itemOffered['numberOfPreviousOwners'] as number
      : null;

    const brand = typeof itemOffered?.['manufacturer'] === 'string' ? itemOffered['manufacturer'] as string : null;
    const model = typeof itemOffered?.['model'] === 'string' ? itemOffered['model'] as string : null;

    const dispObj = engine?.['engineDisplacement'] as Record<string, unknown> | undefined;
    const engine_displacement_cc = typeof dispObj?.['value'] === 'number' ? dispObj['value'] as number : null;

    const enginePowers = engine?.['enginePower'] as Array<Record<string, unknown>> | undefined;
    let power_kw: number | null = null;
    if (enginePowers) {
      const kwtEntry = enginePowers.find(p => p['unitCode'] === 'KWT');
      if (kwtEntry && typeof kwtEntry['value'] === 'number') {
        power_kw = kwtEntry['value'] as number;
      }
    }

    const transmission = typeof itemOffered?.['vehicleTransmission'] === 'string'
      ? itemOffered['vehicleTransmission'] as string
      : null;

    const color = typeof itemOffered?.['color'] === 'string' ? itemOffered['color'] as string : null;
    const vehicle_category = typeof itemOffered?.['bodyType'] === 'string' ? itemOffered['bodyType'] as string : null;

    const itemConditionRaw = typeof offers?.['itemCondition'] === 'string' ? offers['itemCondition'] as string : null;
    let condition: string | null = null;
    if (itemConditionRaw) {
      const condMap: Record<string, string> = {
        'NewCondition': 'Neu',
        'UsedCondition': 'Gebraucht',
        'RefurbishedCondition': 'Aufgearbeitet',
        'DamagedCondition': 'Beschädigt',
      };
      condition = condMap[itemConditionRaw] ?? itemConditionRaw;
    }

    const uuidMatch = url.match(/\/angebote\/([0-9a-f-]{36})/i);
    const listing_id = typeof itemOffered?.['identifier'] === 'string'
      ? itemOffered['identifier'] as string
      : (uuidMatch ? uuidMatch[1] : null);

    return {
      source_marketplace: 'autoscout24.de',
      listing_id,
      url,
      vehicle_type: 'motorcycle',
      brand,
      model,
      year,
      first_registration,
      mileage_km,
      previous_owner_count,
      price_amount,
      price_currency,
      price_negotiable,
      engine_displacement_cc,
      power_kw,
      fuel_type: null,
      transmission,
      color,
      vehicle_category,
      location_city: null,
      condition,
    };
  }
}
