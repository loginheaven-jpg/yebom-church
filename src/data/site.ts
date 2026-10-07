export const site = {
  name: '예봄교회',
  englishName: 'YEBOM CHURCH',
  subtitle: 'Presbyterian Church',
  description: '예봄교회는 예수님 안에서 인생의 봄날이 시작되는 교회입니다.',
  address: '경기도 성남시 분당구 운중로 285(판교동 585-1)',
  phone: '031-8016-9175',
  email: 'webs@yebom.org',
  publicOrigin: import.meta.env.PUBLIC_SITE_URL ?? 'https://yebom-church.pages.dev',
} as const;

export const navigation = [
  { label: 'HOME', href: '/' },
  { label: '예봄소개', href: '/about' },
  { label: '예봄비전', href: '/vision' },
  { label: '예봄피플', href: '/people' },
  { label: '예봄사역', href: '/mission' },
  { label: '말씀과 나눔', href: '/groups' },
  { label: '예배안내', href: '/worship' },
  { label: '예봄자료실', href: '/file-share' },
] as const;

export function canonicalUrl(pathname: string) {
  return new URL(pathname, site.publicOrigin).toString();
}
