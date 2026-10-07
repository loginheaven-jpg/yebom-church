#!/usr/bin/env node

/**
 * Wix 공개 sitemap을 기준으로 원본 HTML과 자산 참조를 재현 가능하게 저장한다.
 *
 * 사용 예:
 *   node scripts/snapshot-wix.mjs --scope static
 *   node scripts/snapshot-wix.mjs --scope group-posts --limit 20
 *   node scripts/snapshot-wix.mjs --scope group-lists --force
 */

import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const ORIGIN = 'https://www.yebom.org';
const SITEMAPS = {
  static: `${ORIGIN}/pages-sitemap.xml`,
  'group-lists': `${ORIGIN}/group-lists-sitemap.xml`,
  'group-posts': `${ORIGIN}/group-posts-sitemap.xml`,
  categories: `${ORIGIN}/dynamic-categories_p_46675aa0_7bab_4a3d_8c5b_000066dcf083_0_250-sitemap.xml`,
};

const args = Object.fromEntries(
  process.argv.slice(2).map((argument) => {
    const [key, value = 'true'] = argument.replace(/^--/, '').split('=');
    return [key, value];
  }),
);

const scope = args.scope ?? 'static';
const sitemapUrl = SITEMAPS[scope];
if (!sitemapUrl) {
  throw new Error(`Unknown --scope=${scope}. Use one of: ${Object.keys(SITEMAPS).join(', ')}`);
}

const limit = Number.isInteger(Number(args.limit)) ? Number(args.limit) : undefined;
const concurrency = Math.max(1, Math.min(8, Number(args.concurrency ?? 4)));
const force = args.force === 'true';
const root = process.cwd();
const rawDirectory = path.join(root, 'migration', 'raw', scope);
const manifestPath = path.join(root, 'migration', 'manifests', `${scope}-snapshot.json`);

await mkdir(rawDirectory, { recursive: true });
await mkdir(path.dirname(manifestPath), { recursive: true });

async function requestText(url) {
  const response = await fetch(url, {
    headers: {
      'User-Agent': 'YebomChurchMigrationAudit/1.0 (+https://yebom-church.pages.dev)',
      Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    },
    signal: AbortSignal.timeout(45000),
  });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.text();
}

function xmlLocations(xml) {
  return [...xml.matchAll(/<loc>([\s\S]*?)<\/loc>/gi)]
    .map((match) => match[1].trim().replace(/&amp;/g, '&'))
    .filter((value) => value.startsWith('https://'));
}

async function collectUrls(url, visited = new Set()) {
  if (visited.has(url)) return [];
  visited.add(url);
  const xml = await requestText(url);
  const locations = xmlLocations(xml);
  if (/<sitemapindex\b/i.test(xml)) {
    const nested = await Promise.all(locations.map((location) => collectUrls(location, visited)));
    return nested.flat();
  }
  return locations;
}

function filenameFor(url, index) {
  const parsed = new URL(url);
  const readable = (parsed.pathname === '/' ? 'home' : parsed.pathname)
    .replace(/^\/+|\/+$/g, '')
    .replace(/[^\p{L}\p{N}._-]+/gu, '_')
    .replace(/_+/g, '_')
    .slice(0, 140) || 'home';
  return `${String(index + 1).padStart(4, '0')}-${readable}.html`;
}

function wixAssetUrls(html) {
  const urls = new Set();
  for (const match of html.matchAll(/https?:\\?\/\\?\/static\.wixstatic\.com\\?\/[^"'<>\s\\]+/g)) {
    urls.add(match[0].replace(/\\\//g, '/').replace(/&amp;/g, '&'));
  }
  return [...urls].sort();
}

async function mapLimit(items, max, mapper) {
  const results = new Array(items.length);
  let cursor = 0;
  await Promise.all(
    Array.from({ length: Math.min(max, items.length) }, async () => {
      while (cursor < items.length) {
        const index = cursor++;
        results[index] = await mapper(items[index], index);
      }
    }),
  );
  return results;
}

const sitemapUrls = [...new Set(await collectUrls(sitemapUrl))];
const targetUrls = limit ? sitemapUrls.slice(0, limit) : sitemapUrls;
console.log(`Scope: ${scope}; discovered: ${sitemapUrls.length}; snapshotting: ${targetUrls.length}; concurrency: ${concurrency}`);

const entries = await mapLimit(targetUrls, concurrency, async (url, index) => {
  const filename = filenameFor(url, index);
  const destination = path.join(rawDirectory, filename);
  try {
    let html;
    if (!force) {
      try {
        html = await readFile(destination, 'utf8');
      } catch {
        html = undefined;
      }
    }
    if (!html) {
      html = await requestText(url);
      await writeFile(destination, html, 'utf8');
    }
    console.log(`[${String(index + 1).padStart(4, '0')}/${String(targetUrls.length).padStart(4, '0')}] OK ${url}`);
    return {
      url,
      filename: path.relative(root, destination),
      bytes: Buffer.byteLength(html),
      wixAssetUrls: wixAssetUrls(html),
      status: 'ok',
    };
  } catch (error) {
    console.error(`[${String(index + 1).padStart(4, '0')}/${String(targetUrls.length).padStart(4, '0')}] FAIL ${url}: ${error.message}`);
    return {
      url,
      filename: path.relative(root, destination),
      status: 'error',
      error: error.message,
    };
  }
});

const manifest = {
  generatedAt: new Date().toISOString(),
  origin: ORIGIN,
  scope,
  sitemapUrl,
  sitemapUrlCount: sitemapUrls.length,
  snapshottedUrlCount: targetUrls.length,
  successCount: entries.filter((entry) => entry.status === 'ok').length,
  failureCount: entries.filter((entry) => entry.status === 'error').length,
  entries,
};

await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
console.log(`Manifest written: ${path.relative(root, manifestPath)}`);
if (manifest.failureCount > 0) process.exitCode = 1;
