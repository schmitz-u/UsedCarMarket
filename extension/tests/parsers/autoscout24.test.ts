import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';
import { JSDOM } from 'jsdom';
import { AutoScout24Parser } from '../../src/parsers/autoscout24';

const html = readFileSync(join(__dirname, '../fixtures/autoscout24.html'), 'utf-8');
const dom = new JSDOM(html, { url: 'https://www.autoscout24.de/angebote/honda-gold-wing-f2cc2803-8151-403f-b483-680300ad25a8' });
const document = dom.window.document;
const parser = new AutoScout24Parser();
const url = 'https://www.autoscout24.de/angebote/honda-gold-wing-f2cc2803-8151-403f-b483-680300ad25a8';
const result = parser.parse(document, url);

describe('AutoScout24Parser', () => {
  it('source_marketplace is autoscout24.de', () => {
    expect(result.source_marketplace).toBe('autoscout24.de');
  });

  it('price_amount is 12000', () => {
    expect(result.price_amount).toBe(12000);
  });

  it('mileage_km is 19600', () => {
    expect(result.mileage_km).toBe(19600);
  });

  it('year is 2016', () => {
    expect(result.year).toBe(2016);
  });

  it('power_kw is 87', () => {
    expect(result.power_kw).toBe(87);
  });

  it('engine_displacement_cc is 1830', () => {
    expect(result.engine_displacement_cc).toBe(1830);
  });

  it('brand is Honda', () => {
    expect(result.brand).toBe('Honda');
  });

  it('model is Gold Wing', () => {
    expect(result.model).toBe('Gold Wing');
  });

  it('transmission is Schaltgetriebe', () => {
    expect(result.transmission).toBe('Schaltgetriebe');
  });

  it('color is Orange', () => {
    expect(result.color).toBe('Orange');
  });

  it('vehicle_category is Tourer', () => {
    expect(result.vehicle_category).toBe('Tourer');
  });
});
