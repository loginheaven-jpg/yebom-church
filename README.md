# 예봄교회 공개 아카이브

기존 Wix 기반 [예봄교회 웹사이트](https://www.yebom.org/)의 **공개 콘텐츠와 시각 언어를 Astro 정적 사이트로 이관**하는 프로젝트입니다. 로그인, 회원, 댓글, 반응, 조회수는 제공하지 않으며 누구나 읽고 자료를 내려받을 수 있는 공개 아카이브로 운영합니다.

> 병행 검수 미리보기: <https://manus-yebom-migration.yebom-church.pages.dev>
>
> 이 주소는 검색 차단(`noindex`) 상태입니다. Wix와 병행 검수 중이므로 `www.yebom.org` 도메인은 아직 바꾸지 않습니다.

## 이관 범위

| 항목 | 이관 상태 |
|---|---:|
| Wix 정적 페이지 | 29개 |
| 공개 그룹 | 6개 |
| 공개 그룹 게시물 레거시 경로 | 1,055개 |
| 공개 자료실 파일 | 335개 |
| 생성된 정적 HTML | 1,085개 |

- 원본의 워드마크, 우측 세로 메뉴, 넓은 여백, 녹색 활성 상태, 원형 플로팅 마크를 공통 UI로 구현했습니다.
- 정적 HTML로 생성하여 JavaScript 없이도 기본 콘텐츠·SEO 메타데이터를 제공합니다.
- Wix 이미지·GIF·글꼴은 로컬 자산으로 전환했고, 게시물의 YouTube 등 외부 미디어만 원본 링크/임베드로 유지합니다.
- 공개 자료실은 `/file-share`에서 제공하며, Pages의 단일 파일 25 MiB 제한을 넘는 PDF 한 개만 Cloudflare R2에 분리합니다.

## 개발

```bash
npm install
npm run dev
npm run build
```

빌드는 다음 작업을 수행합니다.

1. `npm run generate:seo`로 `public/sitemap.xml`, `public/robots.txt` 생성
2. Astro가 공개 페이지와 게시물 레거시 경로를 `dist/`에 정적 생성

## 콘텐츠와 자산 관리

| 대상 | 위치 | 운영 방식 |
|---|---|---|
| 정적 페이지 원문 | `src/data/wix-static.json` | 원본 페이지 데이터 기반 렌더링 |
| 공개 게시물 | `src/data/posts.json`, `src/content/posts/` | 기존 그룹·UUID 경로를 유지 |
| 자료실 목록 | `src/data/fileshare.json` | 파일명·크기·경로·호스팅 위치 제공 |
| 소형 이미지·폰트·파일 | `public/media/`, `public/downloads/` | Pages 정적 자산 |
| Pages 제한 초과 PDF | Cloudflare R2 | `migration/r2-public-assets.json` 매핑으로 검증 |

`migration/raw/`, `migration/extracted/`, `migration/logs/`은 재현 가능한 로컬 원본 캡처물이지만 저장소에는 포함하지 않습니다. 이관 근거, 해시, 경로, R2 분리 상태는 `migration/`의 매니페스트와 문서에 보관합니다.

## 자료실 재생성

Wix File Share 원본 ZIP을 다시 수집한 뒤 다음을 실행합니다.

```bash
python3 scripts/import_fileshare_archives.py
npm run build
```

스크립트는 335개 파일과 총 바이트 수를 확인합니다. `migration/r2-public-assets.json`에 지정된 대용량 파일은 원본 SHA-256과 크기가 일치할 때만 Cloudflare R2 공개 URL로 바뀝니다.

## 배포 원칙

- 작업 브랜치: `manus/yebom-migration`
- `master`는 충분한 병행 검수 후에만 병합합니다.
- Cloudflare Pages 미리보기 배포는 검색 차단 상태입니다.
- `www.yebom.org` DNS 전환, R2 사용자 지정 도메인 연결, 프로덕션 전환은 사용자의 별도 승인 후에만 수행합니다.

자세한 이관 계획은 [`plan.md`](plan.md), 공개 자료실의 원본·검증 근거는 [`migration/FILESHARE-DISCOVERY.md`](migration/FILESHARE-DISCOVERY.md)를 참고하세요.
