import type { ParsedListing } from '../types/canonical';

export interface Parser {
  matches(url: string): boolean;
  parse(document: Document, url: string): ParsedListing;
}
