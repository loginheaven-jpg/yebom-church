# Wix 원본 콘텐츠 수집 상태

- **수집 기준일:** 2026-10-07 (KST)
- **원본 도메인:** <https://www.yebom.org/>
- **수집 원칙:** 공개 페이지의 원문·이미지·영상 링크·첨부 참조만 보존하고, 회원 프로필·댓글·반응·조회수는 새 사이트에 이관하지 않는다.

## 원본 출처와 로컬 보존 위치

| 대상 | 원본 URL | 보존 위치 | 결과 |
|---|---|---|---|
| 일반 페이지 | <https://www.yebom.org/pages-sitemap.xml> | `migration/raw/static/`, `migration/manifests/static-snapshot.json` | 29 / 29 HTML 확보 |
| 공개 그룹 목록 | <https://www.yebom.org/group-lists-sitemap.xml> | `migration/raw/group-lists/`, `migration/manifests/group-lists-snapshot.json` | 6 / 6 HTML 확보 |
| 공개 그룹 게시물 | <https://www.yebom.org/group-posts-sitemap.xml> | `migration/raw/group-posts/`, `migration/manifests/group-posts-snapshot.json` | 1,055 / 1,055 HTML 확보 |
| 정적 페이지의 Wix Media | 공개 HTML의 `static.wixstatic.com/media/...` 참조 | `public/media/wix/`, `migration/manifests/static-assets.json` | 93 / 93 파일, 96,616,696 bytes 확보 |
| Wix 커스텀 글꼴 | 공개 HTML의 `static.wixstatic.com/ufonts/...` 참조 | `public/media/fonts/` | Gothic A1 계열 5개 굵기 확보 |

## 추출 결과

### 정적 페이지

- 29개 페이지에서 텍스트·제목·이미지·링크 기준선을 추출했다.
- 구조화된 추출 파일: `migration/extracted/static-pages.json`
- Astro에서 사용하는 데이터 복사본: `src/data/wix-static.json`
- 원본 페이지별 이미지 참조는 Wix Media 로컬 복사본으로 변환할 수 있도록 파일명 매핑을 보존했다.

### 공개 그룹 게시물

| 그룹 | 공개 원문으로 추출된 게시물 수 |
|---|---:|
| 예봄 예배영상 (`yebom-yebaeyeongsang`) | 188 |
| 최병희 담임목사 목회칼럼 (`choebyeonghui-dam-immogsa-moghoekalleom`) | 281 |
| 리딩지저스 성경읽기 해설 (`lidingjijeoseu-seong-gyeong-ilg-gi-haeseol`) | 267 |
| 김남수 원로목사 설교모음 (`gimnamsu-wonlomogsa-seolgyomo-eum`) | 287 |
| 예봄 은혜나눔 (`yebom-eunhyenanum`) | 20 |
| Yebom 사이트 그룹 (`yebom-saiteu-geulub`) | 1 |
| **합계** | **1,044** |

- 구조화된 추출 파일: `migration/extracted/group-posts.json`
- Git 운영용 Markdown: `src/content/posts/<group>/<uuid>.md` (1,044개)
- 현재 Astro 데이터: `src/data/posts.json`
- 영상 포함 게시물: 167개. 영상 파일은 재호스팅하지 않고 원본 YouTube URL/임베드 정보로 보존한다.
- 이미지 포함 게시물: 267개. Wix Media URL은 추출 데이터에 그대로 보존되어 있고, 게시물 전용 로컬 자산 이관은 다음 단계에서 완료한다.

### 사이트맵에 있으나 원문이 남아 있지 않은 11개 URL

공개 원본 HTML을 직접 검증한 결과, 11개 게시물 URL에는 이관할 게시물 본문이 남아 있지 않았다.

- 1개: 게시물 주소로 접속하면 해당 그룹의 랜딩 페이지가 표시됨
- 10개: 빈 Wix Not Found 응답
- 근거 파일: `migration/extracted/legacy-unavailable-posts.json`
- 새 사이트에서는 해당 **기존 URL 11개를 모두 생성**하고, 원본에 본문이 남지 않았음을 알린 뒤 해당 그룹 아카이브로 연결한다. 따라서 기존 URL이 끊어지지 않으며, 존재하지 않는 본문을 임의로 만들지 않는다.

## 구현상 주의사항

1. `migration/raw/`은 외부 원본의 재현 가능한 증빙이며 삭제하지 않는다.
2. `migration/manifests/`의 URL·해시·크기·성공 상태는 최종 증분 이관 때의 대조 기준이다.
3. 공개 그룹 게시물은 `src/content/posts/` Markdown이 Git 기반 운영용 편집 단위이고, `migration/extracted/group-posts.json`의 Ricos 원본 구조는 보존용 기준 데이터다.
4. Wix는 DNS 전환까지 병행 운영한다. 최종 이관 직전에는 위 sitemap URL들을 다시 읽어 새 글·새 파일만 증분 반영한다.
