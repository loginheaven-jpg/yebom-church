# 예봄교회 Wix → Cloudflare 공개 아카이브 구현 계획

- **상태:** 병행 검수 미리보기 배포 및 전수 HTTP 검증 완료 (2026-10-07)
- **기준 원본:** `https://www.yebom.org/`
- **현재 신규본:** `https://yebom-church.pages.dev/`
- **작업 브랜치:** `manus/yebom-migration`
- **배포 원칙:** Wix와 Cloudflare Pages를 병행 운영하며, 충분한 대조 검수 전에는 `master` 병합·프로덕션 교체·DNS 변경을 하지 않는다.
- **병행 미리보기:** `https://manus-yebom-migration.yebom-church.pages.dev` (검색 차단)

## 1. 확정된 제품 정책

| 항목 | 확정 내용 |
|---|---|
| 공개 범위 | 로그인 없는 공개 읽기 전용 사이트 |
| 회원 데이터 | 계정, 회원 목록, 프로필, 가입 이력은 이전하지 않음 |
| 커뮤니티 흔적 | 댓글, 좋아요, 반응, 조회수는 이전하지 않음 |
| 게시물 보존 | 제목, 본문, 발행일, 그룹/카테고리, 원본 영상·이미지·첨부, 기존 URL 매핑을 보존 |
| 자료실 | 공개 PDF 및 파일을 보존하고, 파일명·경로·크기·다운로드 성공 여부를 대조 |
| 갱신 방식 | Markdown/파일을 Git 저장소에 추가하면 Cloudflare Pages 자동 배포; 필요해질 때 CMS를 별도 구성 |
| 중복/백업 페이지 | 일반 메뉴에서 제외하고 기존 주소는 정식 페이지 또는 기록 보존 주소로 리디렉션 |
| 외부 미디어 | YouTube 등은 원본 링크/임베드로 유지하고 재호스팅하지 않음 |
| 자산 권리 | 교회는 Wix에 올린 사진, GIF, 로고, 폰트, 배경 영상, PDF의 복사·재호스팅 권한을 보유 |
| 디자인 | 데스크톱은 원본과 매우 유사하게 복제; 모바일은 같은 시각 언어를 유지하며 원본의 고정폭·텍스트 잘림을 보정 |
| 도메인 | `www.yebom.org` 전환은 대조 검수 완료 후 별도 결정; 그때까지 병행 운영 |

## 2. 디자인 방향

### 디자인 무브먼트

원본 Wix의 **미니멀 에디토리얼 교회 사이트**를 재현한다. 카드를 쌓는 범용 기관 사이트가 아니라, 흰 캔버스·의도적인 넓은 여백·검정 대형 타이포그래피·비대칭 사진 배치가 화면의 인상을 만든다.

### 핵심 원칙

1. 원본의 로고 위치, 우측 세로 메뉴, 플로팅 원형 마크, 메뉴 활성 녹색을 공통 셸로 고정한다.
2. 섹션마다 원본의 여백 비율과 텍스트/이미지의 비대칭 구도를 보존한다.
3. 원본 Media Manager 자산과 Wix 커스텀 폰트를 사용하고, 비슷한 대체 스톡 자산으로 분위기만 흉내 내지 않는다.
4. 모바일은 390px 이상에서 모든 문장과 핵심 이미지가 잘리거나 수평 스크롤되지 않도록 재배치한다.

### 색·타이포그래피·상호작용

- **색:** 기본 흰색과 검정색, 현재 메뉴 표시용 예봄 녹색, 원본 사진이 가진 자연색을 유지한다.
- **타이포그래피:** 원본의 굵은 한글 제목, 간격 있는 영문 보조 문구, 긴 본문용 한글 고딕 계열을 분리한다.
- **레이아웃:** 좌상단 브랜딩 + 우측 세로 메뉴 + 넓은 콘텐츠 캔버스 + 우하단 원형 마크를 데스크톱 기준으로 삼는다.
- **상호작용:** 메뉴 hover·active와 모바일 메뉴 열기만 절제해 구현한다. 로그인, 가입, 글쓰기, 댓글, 반응은 제공하지 않는다.
- **브랜드 문장:** “기존 예봄교회 사이트의 시각적 정체성을 유지하는, 가볍고 공개적인 말씀·자료 아카이브.”

## 3. 기술 아키텍처

Astro의 정적 생성(SSG)을 사용한다. 모든 공개 콘텐츠는 JavaScript 실행 없이 HTML로 생성되어 검색·공유·저대역폭 환경에서도 읽힌다.

```text
src/
├── components/
│   ├── SiteShell.astro          # 원본 공통 프레임, SEO, 본문 슬롯
│   ├── VerticalNavigation.astro # 데스크톱 세로 메뉴 및 모바일 접근 메뉴
│   ├── FloatingYebomMark.astro  # 원본 우하단 원형 마크
│   ├── PageLead.astro           # 큰 제목, 구분선, 비대칭 리드 영역
│   ├── ArchiveList.astro        # 공개 게시물·자료실 목록
│   └── RichContent.astro        # Wix Ricos 변환 결과의 안전한 렌더링
├── content/
│   ├── pages/                   # 정적 페이지용 Markdown/구조 데이터
│   ├── posts/                   # 1,055개 공개 그룹 게시물 Markdown
│   └── files/                   # 335개 자료실 파일 메타데이터
├── data/
│   ├── groups.json              # 6개 공개 그룹 정의
│   ├── site.ts                  # 주소, SNS, 공통 탐색, Canonical 구성
│   ├── migration-manifest.json  # Wix URL/ID → 신규 경로 및 상태
│   └── redirect-map.json        # 중복·백업·레거시 URL 처리
├── layouts/
│   └── Layout.astro             # 공통 SEO 및 디자인 셸 진입점
├── pages/
│   ├── index.astro              # 원본 홈 구성
│   ├── about.astro 등           # 정적 소개/사역/예배 페이지
│   ├── groups/index.astro       # 6개 그룹 목록
│   ├── group/[group]/discussion/[id].astro  # 1,055개 정적 게시물 상세
│   ├── file-share/index.astro   # 자료실 목록
│   ├── sitemap.xml.ts
│   └── robots.txt.ts
└── styles/
    ├── tokens.css               # 색·폭·간격·z-index 변수
    ├── fonts.css                # 원본 승인 폰트 선언
    └── global.css                # 공통·반응형 디자인

scripts/
├── snapshot-wix.ts              # sitemap/공개 HTML/SSR 원본 캡처
├── import-posts.ts              # Forum + Groups SSR → Markdown 변환
├── import-files.ts              # File Share 메타데이터와 자산 매핑
├── download-assets.ts           # Wix Media Manager 자산 복사·해시 기록
└── reconcile.ts                 # URL·게시물·파일·자산 매니페스트 대조

public/
└── media/                       # Git에 적합한 이미지·GIF·폰트·소형 문서
```

Cloudflare Pages는 단일 정적 자산을 25 MiB 이하로 제한한다. 실제 용량 점검에서 `2026_0125 예봄주보.pdf`가 68.8 MiB인 것을 확인해, 이 파일은 Cloudflare R2 `yebom-church-assets`의 검증된 공개 객체로 분리했다. 나머지 자료실 파일·이미지·폰트는 Pages 정적 출력에 둔다. `migration/r2-public-assets.json`은 소스 파일의 크기와 SHA-256을 함께 기록하므로, 빌드 시점에 원본 대조 없이 외부 URL로 바뀌지 않는다.

## 4. 콘텐츠 모델

### 정적 페이지

정적 페이지는 원본 문단, 섹션 순서, 사진, 외부 링크를 Markdown 또는 구조화 데이터로 저장한다. 각 페이지는 원본 URL, 제목, 설명, 대표 이미지, 이전 경로를 가진다.

### 공개 그룹 게시물

각 게시물은 다음 메타데이터를 가진 Markdown 엔트리로 변환한다.

```yaml
title: 게시물 제목
publishedAt: 2026-08-25T07:37:15+09:00
group: yebom-yebaeyeongsang
originalUrl: https://www.yebom.org/group/.../discussion/<uuid>
legacyId: <uuid>
media:
  - type: youtube
    url: https://youtu.be/...
assets:
  - /media/...
```

- `Forum/Posts` 1,017건은 제목·본문·날짜·분류의 기준 데이터로 사용한다.
- 공개 SSR 원문은 **1,055개 전체 URL**에서 수집하여 Ricos 서식·이미지·영상·첨부를 보존한다.
- CMS에 없는 38건은 SSR 원문을 유일한 콘텐츠 기준으로 삼는다.

### 자료실

각 파일은 파일명, 폴더, 원본 URL, 신규 URL, 크기, MIME, 해시, 게시/갱신일을 매니페스트로 보존한다. 상세 페이지를 만들지 않아도 다운로드 목록과 검색 가능한 정적 HTML을 제공한다.

## 5. URL·SEO 전략

- Astro 파일 라우팅과 `getStaticPaths()`로 1,055개 게시물 URL을 빌드 시점에 생성한다.
- 현재 Wix의 `/group/<group>/discussion/<uuid>` 경로를 신규 정적 경로로 최대한 그대로 유지한다.
- 정적 페이지의 기존 경로를 유지한다.
- 중복/백업 URL은 정식 경로 또는 아카이브 주소로 리디렉션 맵에 명시한다.
- 모든 공개 페이지는 고유한 title, description, canonical, Open Graph, Twitter Card를 초기 HTML에 가진다.
- 최종 도메인 전환 전에는 실제 정식 도메인을 추측해 canonical을 배포하지 않고, Pages 검수 도메인에서는 해당 도메인 기준으로 생성한다.
- sitemap과 robots는 공개 콘텐츠만 포함한다. 회원·문의·관리·비공개 콘텐츠는 절대 노출하지 않는다.

## 6. 구현 순서

1. 원본 snapshot과 자산/URL/게시물/파일 매니페스트를 저장하여 재현 가능한 기준선을 만든다.
2. 원본 로고, 서체, 플로팅 마크, 세로 메뉴, 반응형 메뉴를 포함한 공통 디자인 셸을 구축한다.
3. 홈페이지·예봄소개·비전·가정교회·삶공부·예봄피플·사역·예배안내의 원본 콘텐츠와 레이아웃을 순차적으로 이관한다.
4. 공개 그룹 목록, 1,055개 게시물 상세, 자료실 335개 파일 목록을 정적 콘텐츠로 생성한다.
5. 원본 URL 매핑, SEO 메타데이터, sitemap, robots, 레거시 리디렉션을 완성한다.
6. 병행 운영 기간에 Wix 원본과 Cloudflare 검수본의 콘텐츠·자산·디자인을 대조하고, 신규 변경분만 증분 이관한다.

## 7. 운영 및 배포 경계

- 개발과 스냅샷은 `manus/yebom-migration` 브랜치에서 진행한다.
- `master` 병합 및 현재 `yebom-church.pages.dev`의 갱신은 이관 대조가 충분히 끝난 뒤에만 수행한다.
- `www.yebom.org`의 DNS/도메인 전환은 사용자가 최종 승인한 별도 단계다.
- Cloudflare R2 `yebom-church-assets`는 검수용 `r2.dev` URL로 25 MiB 초과 PDF 1개를 제공한다. 프로덕션 전환 시에만 `assets.yebom.org` 같은 사용자 지정 도메인을 연결하며, 이번 단계에서는 DNS를 바꾸지 않는다.
