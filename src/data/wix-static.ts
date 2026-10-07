import source from './wix-static.json';

export type WixStaticBlock = {
  type: 'h1' | 'h2' | 'h3' | 'h4' | 'p' | 'li' | 'image' | 'link';
  text?: string;
  src?: string;
  alt?: string;
  href?: string;
};

export type WixStaticPage = {
  url: string;
  sourceSnapshot: string;
  characters: number;
  blocks: WixStaticBlock[];
  externalVideos: string[];
  path: string;
  slug: string;
  headline: string;
};

const firstText = (blocks: WixStaticBlock[]) => blocks.find((block) => /^h[1-4]$/.test(block.type) && block.text)?.text ?? '예봄교회';

export const staticWixPages: WixStaticPage[] = source.pages.map((page) => {
  const path = new URL(page.url).pathname;
  return {
    ...page,
    path,
    slug: path.replace(/^\//, ''),
    headline: firstText(page.blocks as WixStaticBlock[]),
  };
}) as WixStaticPage[];

export const lifeStudyPages = staticWixPages
  .filter((page) => /^\/lifestudy\d{2}$/.test(page.path))
  .sort((a, b) => a.path.localeCompare(b.path));

export function getStaticWixPage(pathname: string) {
  const normalized = pathname === '/' ? '/' : pathname.replace(/\/$/, '');
  return staticWixPages.find((page) => page.path === normalized);
}

export function localWixMedia(url: string) {
  const marker = 'https://static.wixstatic.com/media/';
  if (!url.startsWith(marker)) return url;
  const filename = decodeURIComponent(url.slice(marker.length).split('/v1/', 1)[0].split('?', 1)[0].split('/').at(-1) ?? '');
  return filename ? `/media/wix/${filename}` : url;
}

export function localWixLink(href: string) {
  try {
    const target = new URL(href);
    if (target.origin !== 'https://www.yebom.org') return href;
    return `${target.pathname}${target.search}${target.hash}`;
  } catch {
    return href;
  }
}
