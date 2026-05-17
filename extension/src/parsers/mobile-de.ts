import type { Parser } from './interface';
import type { ParsedListing } from '../types/canonical';

export class MobileDeParser implements Parser {
  matches(url: string): boolean {
    return url.includes('mobile.de/fahrzeuge/details');
  }

  parse(document: Document, url: string): ParsedListing {
    const getText = (testId: string): string | null => {
      const dt = document.querySelector(`[data-testid="${testId}"]`);
      if (!dt) return null;
      const dd = dt.nextElementSibling;
      return dd ? (dd.textContent ?? '').trim() : null;
    };

    const priceEl = document.querySelector('[data-testid="vip-price-label"]');
    const priceText = priceEl ? (priceEl.textContent ?? '') : '';
    const priceMatch = priceText.replace(/\./g, '').match(/(\d+)/);
    const price_amount = priceMatch ? parseInt(priceMatch[1], 10) : null;

    const mileageText = getText('mileage-item');
    const mileage_km = mileageText !== null
      ? parseInt(mileageText.replace(/\./g, '').replace(/[^\d]/g, ''), 10) || 0
      : null;

    const dispText = getText('cubicCapacity-item');
    const engine_displacement_cc = dispText !== null
      ? parseInt(dispText.replace(/\./g, '').replace(/[^\d]/g, ''), 10) || null
      : null;

    const powerText = getText('power-item');
    let power_kw: number | null = null;
    if (powerText) {
      const kwMatch = powerText.match(/(\d+)\s*kW/i);
      if (kwMatch) power_kw = parseInt(kwMatch[1], 10);
    }

    const first_registration = getText('firstRegistration-item');
    const year = first_registration
      ? parseInt(first_registration.split('/')[1] ?? '', 10) || null
      : null;

    const ownerText = getText('numberOfPreviousOwners-item');
    const previous_owner_count = ownerText ? parseInt(ownerText.replace(/[^\d]/g, ''), 10) || null : null;

    const fuel_type = getText('fuel-item');
    const transmission = getText('transmission-item');
    const color = getText('color-item');
    const condition = getText('damageCondition-item');
    const vehicle_category = getText('category-item');

    const urlParams = new URL(url).searchParams;
    const listing_id = urlParams.get('id');

    let brand: string | null = null;
    let model: string | null = null;
    const ogTitleMeta = document.querySelector('meta[property="og:title"]');
    const titleText = ogTitleMeta ? ogTitleMeta.getAttribute('content') ?? '' : document.title ?? '';
    if (titleText) {
      const parts = titleText.split('|').map(p => p.trim());
      if (parts.length >= 2) {
        const firstPart = parts[0];
        const words = firstPart.split(' ');
        brand = words[0] ?? null;
        model = words.slice(1).join(' ').trim() || parts[1] || null;
      } else if (parts.length === 1) {
        const words = parts[0].split(' ');
        brand = words[0] ?? null;
        model = words.slice(1).join(' ').trim() || null;
      }
    }

    if (!price_amount && price_amount !== 0) {
      console.warn(`[mobile.de parser] Could not extract price from ${url}`);
    }

    return {
      source_marketplace: 'mobile.de',
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
      price_currency: 'EUR',
      price_negotiable: null,
      engine_displacement_cc,
      power_kw,
      fuel_type,
      transmission,
      color,
      vehicle_category,
      location_city: null,
      condition,
    };
  }
}
