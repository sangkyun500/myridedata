# 가민 → GitHub 자동 동기화

매일 새벽 5시에 가민 커넥트에서 최근 2년 라이딩 데이터를 자동 수집해
`garmin_rides.csv`로 저장합니다. 한 번 설정하면 손댈 일 없습니다.

## 설정 (한 번만, 약 10분)

### 1. 저장소 만들기
- GitHub 로그인 → 우상단 `+` → **New repository**
- 이름: `garmin-sync` (아무거나 OK)
- **Private** 선택 → Create repository

### 2. 파일 올리기
- 방금 만든 저장소에서 **uploading an existing file** 링크 클릭
- 이 압축을 푼 파일 전부를 창에 드래그:
  - `sync.py`
  - `make_token.py`
  - `README.md`
  - `.github/workflows/sync.yml` ← **주의: 폴더 구조 유지 필요.**
    웹 업로드는 폴더 드래그가 안 될 수 있으니, 안 되면:
    저장소에서 `Add file → Create new file` → 파일명 칸에
    `.github/workflows/sync.yml` 입력(자동으로 폴더 생성됨) →
    sync.yml 내용 복붙 → Commit
- **Commit changes** 클릭

### 3. 가민 토큰 발급 (맥 터미널에서 한 번)
```
pip install garminconnect
python make_token.py
```
- 가민 이메일/비번 입력 → 긴 토큰 문자열이 출력됨 → 전체 복사

### 4. 토큰 등록
- 저장소 → **Settings** → **Secrets and variables** → **Actions**
- **New repository secret**
  - Name: `GARTH_TOKEN`
  - Secret: 복사한 토큰 붙여넣기
- **Add secret**

### 5. 첫 실행 테스트
- 저장소 → **Actions** 탭 → `garmin-sync` → **Run workflow** 버튼
- 1~2분 뒤 초록불 ✓ 뜨고 `garmin_rides.csv`가 생기면 성공

## 이후 사용법
설정 끝. 매일 새벽 자동 갱신됩니다.
Claude한테 CSV의 raw 주소를 알려주고 기억해달라고 하면,
그 다음부터는 "요즘 폼 어때?"라고 묻기만 하면 됩니다.

raw 주소 확인법: 저장소에서 `garmin_rides.csv` 클릭 → **Raw** 버튼 →
주소창의 URL 복사.

> 참고: Private 저장소의 raw URL은 토큰이 포함된 임시 링크라서
> Claude가 항상 접근하지 못할 수 있습니다. 그 경우 저장소를 Public으로
> 두는 게 가장 간단한데, 라이딩 기록(시간·거리·파워)이 공개된다는 점은
> 감안하세요. GPS 경로는 포함되지 않습니다.

## 고장났을 때
- Actions 탭에 빨간불 → 대부분 토큰 만료. `make_token.py` 다시 실행해서
  GARTH_TOKEN 시크릿 값만 교체하면 됩니다.
- 그래도 안 되면 에러 로그 복사해서 Claude한테 보여주세요.
