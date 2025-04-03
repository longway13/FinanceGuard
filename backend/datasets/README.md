# FinanceGuard Datasets

이 폴더는 FinanceGuard 프로젝트에서 사용되는 데이터셋을 포함합니다.

## 데이터셋 다운로드

1. 아래 Google Drive 링크에서 데이터셋을 다운로드하세요:
   - [case_db.json](https://drive.google.com/file/...)
   - [precomputed_embeddings.npz](https://drive.google.com/file/...)

2. 다운로드한 파일들을 이 폴더(`backend/datasets/`)에 위치시키세요.

## 데이터셋 구조

- `case_db.json`: 판례 데이터베이스
- `precomputed_embeddings.npz`: 사전 계산된 임베딩

## 주의사항

- 이 폴더의 데이터는 git으로 추적되지 않습니다.
- 개발/배포 시 반드시 데이터셋을 수동으로 다운로드해야 합니다.