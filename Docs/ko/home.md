<p align="center">
  <img src="../assets/LABOARD_HOME.png" alt="Home (light)" width="900"/>
  <img src="../assets/LABOARD_HOME_DARK.png" alt="Home (dark)" width="900"/>
</p>

# Home

[English](../en/home.md) | **한국어**

Home은 프로젝트를 한눈에 보는 페이지입니다. 가운데에는 Data, Model, Latest hyperparameter, Result 네 개의 요약
카드가 있고, 오른쪽에는 프로젝트의 git 기록이 있습니다. 각 카드의 **Open** 링크를 누르면 해당 페이지로
이동합니다.

프로젝트를 로드하지 않았다면 *No project loaded*와 함께 Setting으로 안내합니다.

## 왼쪽 사이드바

### Project 카드

| 행 | 내용 |
| --- | --- |
| 이름 | `[project] name` (없으면 루트 폴더 이름)과 작업 종류 필 (Data 카드 참고) |
| Remote | `origin` URL |
| Branch | 현재 브랜치와 upstream 대비 상태 (예: `ahead 1`, `up to date with origin/main`). 예전 커밋을 볼 때는 `detached at <hash> · read-only snapshot` |
| Commits | 커밋 수와 기여자 수 |
| Hyperparameter sets | `[Path] Hyperparameter`에서 찾은 하이퍼파라미터 세트(학습 run) 수 |

### Root folders

프로젝트 루트 한 행과 `[paths]` 항목(`data`, `models`, `runs`, `results`)마다 한 행씩 있고, 루트 기준
상대 경로가 함께 표시됩니다. **Open**을 누르면 파일 관리자에서 그 폴더를 엽니다. 폴더가 없으면 상태
바에 메시지가 뜹니다.

## 요약 카드

카드는 두 열로 배치됩니다. 가운데 영역이 좁으면 한 열로 바뀌고 스크롤됩니다.
보여 줄 내용이 없는 카드는 무엇이 없는지 알려 줍니다. 예: *No model files found in paths.models.*

### Data

| 부분 | 내용 |
| --- | --- |
| 작업 필 | 데이터의 `task`/`object` 열에서 가장 많은 값. 그런 열이 없으면 파일에 레이블이 있을 때 *Classification*, 없으면 *Unlabeled* |
| 설명 | 데이터를 읽은 출처, 클래스 수, 파일 확장자 |
| 타일 | 데이터에 `trained`/`used` 열이 있으면 **Total files · Used in training · Not yet trained**. 없으면 **Total files · Classes · Folders** |
| Files added per month | 최근 8개월의 막대 차트. 날짜는 데이터에 `created` 열이 있으면 그 값을, 없으면 각 파일의 수정 시각을 사용 |
| 범례 | split별(Train / Valid / Test / Unused) 파일 수 |

### Model

| 부분 | 내용 |
| --- | --- |
| 타일 | **Models** (`paths.models` 바로 아래 항목 수), **Files** (모델 파일 수), **Last updated** (가장 최근 파일이 얼마나 지났는지) |
| Format | 파일 형식(PyTorch, ONNX, safetensors 등)별 누적 막대와 범례. 형식마다 개수와 확장자 표시 |
| 표 | 최근에 바뀐 순서로 최대 8개 모델: **Model · Formats · Files · Size** |

### Latest hyperparameter

가장 최근에 수정된 하이퍼파라미터 세트(학습 run)를 보여 줍니다.

- 설명 줄에 run 이름, 그 폴더를 마지막으로 건드린 커밋, 수정 시각, 읽은 설정 파일이 나옵니다.
- 그 아래에 처음 12개 하이퍼파라미터가 두 열로 표시됩니다.

### Result

`paths.results` 아래 어디든 `accuracy.csv`라는 파일이 있는지 찾습니다.

**`accuracy.csv`가 있으면** 카드에 다음이 표시됩니다.

- 행마다 한 점씩, **train loss**와 **valid loss**를 선(왼쪽 축)으로, **inference ms / image**를
  막대(오른쪽 축)로 그린 차트.
- 타일 세 개: **Best valid loss**(해당 커밋), **Fastest**(해당 모델), **Rows in csv**.

헤더는 필요 없고, 형식에 맞지 않는 행(헤더 줄 등)은 건너뜁니다. 예상하는 열 순서:

```
commit, model, train_loss, valid_loss, ms_per_image
```

**`accuracy.csv`가 없으면** 결과 파일 수와 가장 많은 파일 형식 두 가지를 보여 줍니다.

## Git history (오른쪽 패널)

현재 브랜치와 upstream의 커밋을 최대 100개까지 보여 줍니다. 목록은 지금 보고 있는 커밋부터 시작하므로,
예전 스냅샷을 볼 때는 그보다 새 커밋이 나오지 않습니다.

각 커밋에 표시되는 것:

- 커밋 메시지
- ref 필: 현재 브랜치는 진한색, 다른 브랜치는 회색, 태그는 초록색
- 한쪽에만 있는 커밋이면 *Local · not pushed* 또는 *Remote · not pulled* (브랜치에 upstream이 있을 때만)
- 해시 · 작성자 · 날짜 · 변경된 파일 수

**커밋 펼치기.** 커밋을 클릭하면 펼쳐지면서 변경된 파일 목록이 나옵니다. 추가 / 수정 / 이름 변경 /
복사는 초록색, 삭제는 빨간색입니다. 다시 클릭하면 접힙니다. 가장 최근 커밋은 펼쳐진 상태로 시작합니다.

**All / This file.** *This file*을 고르면 최근 100개 커밋에서 가장 자주 바뀐 파일을 건드린 커밋만
남습니다. 타임라인의 채워진 점은 그 파일을 마지막으로 건드린 커밋입니다.

프로젝트 루트가 git 저장소가 아니면 그렇다고 표시합니다.
