import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';
import { JSDOM } from 'jsdom';
import { MobileDeParser } from '../../src/parsers/mobile-de';

const html = readFileSync(join(__dirname, '../fixtures/mobile-de.html'), 'utf-8');
const dom = new JSDOM(html, { url: 'https://suchen.mobile.de/fahrzeuge/details.html?id=451777822&scopeId=C' });
const document = dom.window.document;
const parser = new MobileDeParser();
const url = 'https://suchen.mobile.de/fahrzeuge/details.html?id=451777822&scopeId=C';
const result = parser.parse(document, url);

describe('MobileDeParser', () => {
  it('source_marketplace is mobile.de', () => {
    expect(result.source_marketplace).toBe('mobile.de');
  });

  it('price_amount is 39990', () => {
    expect(result.price_amount).toBe(39990);
  });

  it('mileage_km is 0', () => {
    expect(result.mileage_km).toBe(0);
  });

  it('first_registration contains 2026', () => {
    expect(result.first_registration).toBeTruthy();
    expect(result.first_registration).toContain('2026');
  });

  it('power_kw is greater than 0', () => {
    expect(result.power_kw).toBeGreaterThan(0);
  });

  it('engine_displacement_cc is greater than 0', () => {
    expect(result.engine_displacement_cc).toBeGreaterThan(0);
  });

  it('transmission is truthy', () => {
    expect(result.transmission).toBeTruthy();
  });

  it('brand contains Honda', () => {
    expect(result.brand).toBeTruthy();
    expect(result.brand).toContain('Honda');
  });
});
