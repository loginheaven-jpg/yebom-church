# Wix 자료실(File Share) 원본 조사·이관 기록

- **조사 및 이관일:** 2026-10-07 (KST)
- **대상 페이지:** <https://www.yebom.org/file-share>
- **Wix site ID:** `523d3f02-0b41-4973-992d-0ca7109d3d6c`
- **정책:** 자료실 파일·폴더는 로그인 없는 공개 콘텐츠로 새 사이트에 이관한다. 조회수·즐겨찾기·소유자·로그인 상태는 이관하지 않는다.

## 원본 대조 결과

| 항목 | 결과 |
|---|---:|
| 공개 File Share 루트 폴더 | 1개 (`예봄주보`) |
| 공개 예봄주보 파일 | **335개** |
| 원본 파일 총합 | **278,987,806 bytes** |
| 공개 범위 | `PUBLIC` |
| File Share API 일괄 다운로드 최대 수 | 300개 |
| 새 자료실 목록 HTML | `/file-share` |

대표 원문 메타데이터에는 `id`, `name`, `path`, `fileFields.size`, `fileFields.extension`, `createdAt`, `availability`가 포함된다. 예: `2026_1004 예봄주보.pdf`, size `1,764,284` bytes.

## 실제 다운로드 경로 해결

File Share의 CMS 레코드 ID는 일반 Media Manager file ID가 아니다. 따라서 Media Manager ZIP API로는 `Nothing to download`가 반환되어 사용할 수 없었다. 대신 공개 File Share 위젯의 실제 읽기 전용 API를 확인해 다음 흐름을 확정했다.

1. `POST /file-sharing/api/v1/file-sharing/library-folder-items/query` → 루트의 공개 폴더 확인
2. `POST /file-sharing/api/v1/file-sharing/library-items/query` + `filter.parentLibraryItemIds` → 폴더 파일 목록 전체 조회
3. `POST /file-sharing/api/v1/file-sharing/library-items/download` + `action.libraryItemIds` → 파일 또는 ZIP 다운로드 URL 발급

`library-items/query`는 기본 30개씩 반환하며, 응답 `metaData.nextCursor`를 `paging.cursor`로 넘겨 전수 조회했다. 일괄 다운로드는 최대 300개이므로 300개와 35개로 분할했다.

| ZIP | 파일 수 | 원본 다운로드 URL |
|---|---:|---|
| 001 | 300 | `https://archive.wixmp.com/archive/wix/fd65622c1f434985b9b1cec89fb3eb67` |
| 002 | 35 | `https://archive.wixmp.com/archive/wix/bdbdf455eb394678a5ac01f88dde396b` |

## Cloudflare Pages·R2 분리

Cloudflare Pages는 단일 정적 자산을 **25 MiB** 이하로 제한한다. 따라서 2026년 1월 25일자 주보(`2026_0125 예봄주보.pdf`, **68,848,659 bytes**)만 Pages 정적 결과에서 분리하고 Cloudflare R2에 원본 바이트로 보관했다. 나머지 334개 파일은 Pages 정적 자산으로 유지한다.

| 저장소 | 파일 수 | 검증 |
|---|---:|---|
| Cloudflare Pages 정적 자산 | 334 | 모든 파일 25 MiB 미만 |
| Cloudflare R2 `yebom-church-assets` | 1 | 크기 `68,848,659`, 원본 SHA-256 `29586de075f7c88b5c25d0277c839ef9b35393dfb7d22080da7314e639d17e89` 대조 |

- R2 객체 키: `downloads/bulletins/2026_0125-yebom-weekly-bulletin.pdf`
- 현재 공개 검수 URL: `https://pub-a39aa2603ec34a0ca21882496cb15109.r2.dev/downloads/bulletins/2026_0125-yebom-weekly-bulletin.pdf`
- `r2.dev` URL은 **병행 검수용**이다. 도메인 전환 승인 단계에서 `assets.yebom.org` 같은 사용자 지정 Cloudflare 도메인으로 교체한다.

## 산출물과 재현 방법

- 원본 ZIP (Git 제외): `migration/raw/fileshare-archives/`
- 원본 압축 해제본 (Git 제외): `migration/raw/fileshare-unpacked/`
- Pages 공개 다운로드: `public/downloads/bulletins/` (334개)
- R2 공개 자산 매핑: `migration/r2-public-assets.json`
- 앱용 공개 목록: `src/data/fileshare.json`
- 파일별 크기·SHA-256 매니페스트: `migration/manifests/fileshare-assets.json`
- 재생성 스크립트: `scripts/import_fileshare_archives.py`

`import_fileshare_archives.py`는 R2 매핑 파일의 크기와 SHA-256을 원본 추출물과 먼저 대조한 뒤, 일치할 때만 해당 파일을 R2 URL로 대체한다. Pages 빌드 결과는 **335개 링크**, **334개 Pages 파일**, **0개 25 MiB 초과 정적 자산**이어야 한다.

## 원본·플랫폼 근거

- Wix Media collections: <https://dev.wix.com/docs/api-reference/business-solutions/cms/collection-management/wix-app-collections/wix-media-collections>
- Wix Data Items Query: <https://dev.wix.com/docs/api-reference/business-solutions/cms/data-items/query-data-items>
- 공개 File Share 위젯 번들: <https://static.parastorage.com/services/file-share-ooi/1.631.0/FileShareOoiViewerWidgetNoCss.bundle.min.js>
- Cloudflare Pages limits: <https://developers.cloudflare.com/pages/platform/limits/>
- Cloudflare R2 Upload Object API: <https://developers.cloudflare.com/api/resources/r2/subresources/buckets/subresources/objects/methods/upload/>

## 보존 및 보안 주의

- 사용자·소유자 ID, 조회수, 즐겨찾기 상태는 새 정적 사이트 데이터에 포함하지 않는다.
- 새 사이트에는 파일명·확장자·크기·공개 다운로드 경로만 노출한다.
- 도메인 전환 전 R2 사용자 지정 도메인·DNS 변경은 수행하지 않는다.
