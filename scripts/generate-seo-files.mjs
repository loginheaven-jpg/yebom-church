import { mkdir, writeFile } from 'node:fs/promises';
import staticSource from '../src/data/wix-static.json' with { type: 'json' };
import postSource from '../src/data/posts.json' with { type: 'json' };

const origin = (process.env.PUBLIC_SITE_URL ?? 'https://yebom-church.pages.dev').replace(/\/$/, '');
const publicDir = new URL('../public/', import.meta.url);
const duplicatePaths = new Set([
  '/forum',
  '/members',
  '/categories',
  '/%EB%B3%B5%EC%A0%9C-%EC%98%88%EB%B4%84%ED%94%BC%ED%94%8C',
  '/%EC%98%88%EB%B4%84%EA%B2%8C%EC%8B%9C%ED%8C%90',
  '/home%EB%B0%B1%EC%97%85',
]);

const escapeXml = (value) => String(value).replace(/[<>&'\"]/g, (character) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', "'": '&apos;', '"': '&quot;' })[character]);
const absoluteUrl = (pathname) => new URL(pathname, `${origin}/`).toString();
const dateOnly = (value) => value ? value.slice(0, 10) : undefined;

const routes = new Map();
const add = (pathname, lastmod) => {
  const normalized = pathname === '/' ? '/' : pathname.replace(/\/$/, '');
  routes.set(normalized, { pathname: normalized, lastmod });
};

add('/');
add('/groups');
for (const page of staticSource.pages) {
  const pathname = new URL(page.url).pathname;
  if (!duplicatePaths.has(pathname)) add(pathname);
}
for (const post of postSource.posts) {
  add(`/group/${post.groupSlug}/discussion/${post.legacyId}`, dateOnly(post.updatedAt ?? post.publishedAt));
}

const entries = [...routes.values()].sort((left, right) => left.pathname.localeCompare(right.pathname));
const sitemap = [
  '<?xml version="1.0" encoding="UTF-8"?>',
  '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
  ...entries.map(({ pathname, lastmod }) => [
    '  <url>',
    `    <loc>${escapeXml(absoluteUrl(pathname))}</loc>`,
    lastmod ? `    <lastmod>${lastmod}</lastmod>` : '',
    '  </url>',
  ].filter(Boolean).join('\n')),
  '</urlset>',
  '',
].join('\n');
const robots = `User-agent: *\nAllow: /\nSitemap: ${absoluteUrl('/sitemap.xml')}\n`;

await mkdir(publicDir, { recursive: true });
await writeFile(new URL('sitemap.xml', publicDir), sitemap, 'utf8');
await writeFile(new URL('robots.txt', publicDir), robots, 'utf8');
console.log(`Generated sitemap.xml with ${entries.length} indexable URLs for ${origin}`);
