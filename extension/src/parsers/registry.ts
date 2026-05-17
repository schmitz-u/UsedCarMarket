import type { Parser } from './interface';
import { MobileDeParser } from './mobile-de';
import { AutoScout24Parser } from './autoscout24';

const parsers: Parser[] = [new MobileDeParser(), new AutoScout24Parser()];

export function getParser(url: string): Parser | null {
  return parsers.find(p => p.matches(url)) ?? null;
}
