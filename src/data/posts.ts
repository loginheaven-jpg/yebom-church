import source from './posts.json';
import unavailableSource from './unavailable-posts.json';

export type PublicPost = {
  legacyId: string;
  legacyUrl: string;
  groupSlug: string;
  title: string;
  publishedAt: string | null;
  updatedAt: string | null;
  bodyText: string[];
  videos: Array<{ url: string; thumbnail?: string; title?: string; duration?: number }>;
  images: Array<{ url: string; alt?: string }>;
  attachments: Array<{ url: string; mediaType?: string }>;
};

export type UnavailablePost = {
  legacyId: string;
  legacyUrl: string;
  groupSlug: string;
  status: 'group-landing-fallback' | 'not-found';
  sourceTitle: string;
  visibleText: string;
  sourceSnapshot: string;
};

export const publicPosts = source.posts as PublicPost[];
export const unavailablePosts = unavailableSource.posts as UnavailablePost[];

const groupNames: Record<string, string> = {
  'yebom-saiteu-geulub': 'Yebom 사이트 그룹',
  'yebom-yebaeyeongsang': '예봄 예배영상',
  'choebyeonghui-dam-immogsa-moghoekalleom': '최병희 담임목사 목회칼럼',
  'lidingjijeoseu-seong-gyeong-ilg-gi-haeseol': '리딩지저스 성경읽기 해설',
  'gimnamsu-wonlomogsa-seolgyomo-eum': '김남수 원로목사 설교모음',
  'yebom-eunhyenanum': '예봄 은혜나눔',
};

export function groupName(slug: string) {
  return groupNames[slug] ?? slug.replace(/-/g, ' ');
}

export function formatPublishedAt(value: string | null) {
  if (!value) return '';
  return new Intl.DateTimeFormat('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' }).format(new Date(value));
}

export const groups = [...new Set(publicPosts.map((post) => post.groupSlug))]
  .sort()
  .map((slug) => {
    const posts = publicPosts.filter((post) => post.groupSlug === slug);
    return { slug, name: groupName(slug), count: posts.length, latest: posts[0] };
  });
