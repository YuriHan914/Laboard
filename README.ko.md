# 🧪 Laboard

*[English](README.md)*




<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="Docs/assets/LABOARD_LOGO_DARK.png"/>
    <img src="Docs/assets/LABOARD_LOGO.png" alt="Laboard" width="136"/>
  </picture>
</p>


<br></br>

<table>
  <tr>
    <td align="center" width="50%"><img src="Docs/assets/LABOARD_HOME.png" alt="Home (light)"/><br/><sub>Light</sub></td>
    <td align="center" width="50%"><img src="Docs/assets/LABOARD_HOME_DARK.png" alt="Home (dark)"/><br/><sub>Dark</sub></td>
  </tr>
</table>


<br></br>

머신러닝 프로젝트를 위한 PyQt6 데스크톱 실험 관리 도구입니다. 데이터, 모델, 학습 run, 결과가 어디 있는지와
어떤 git 저장소를 볼지 적은 프로젝트 파일(`.toml`) 하나만 지정하면, Laboard가 이 모두를 한 창에서 보여 줍니다.

Laboard는 읽기만 합니다. 파일, 데이터베이스, 저장소를 수정하지 않습니다. 단 하나의 예외는 git log 팝업의
**Fetch** 버튼으로, `git fetch`를 실행하므로 원격 추적 브랜치만 갱신됩니다.

</br>

---

## 🚀 Features

* 데이터 뷰어: train / valid / test split, 레이블, 모델 예측을 나란히 확인
* 내장 [Netron](https://netron.app) 뷰로 모델 그래프와 파라미터 수 확인 (GPU, torch 불필요)
* 학습 run: 진행 상황과 설정 파일의 모든 하이퍼파라미터
* csv / jsonl / TensorBoard 결과 차트, smoothing과 여러 곡선 비교
* git 기록, 예전 커밋 시점의 프로젝트 전체 보기
* Postgres / Supabase 테이블, 테이블 파일, 폴더 스캔에서 데이터 읽기
* 라이트 / 다크 테마

---

## 🛠️ Installation

```bash
git clone https://github.com/YuriHan914/EX_Tool.git
cd EX_Tool

# Python 3.11+
pip install -r requirements.txt
```

---

## ▶️ Quick Start

프로젝트 파일을 작성합니다.

```toml
[project]
name = "my-project"
root = "/path/to/repo"

[paths]
data = "/path/to/data"
models = "/path/to/models"
runs = "/path/to/runs"
results = "/path/to/results"
```

실행합니다.

```bash
python -m laboard --project project.toml
```

`--project` 없이 실행하면 **Setting** 페이지에서 시작하고 프로젝트 파일을 불러오라고 안내합니다
(**Browse → Load**). 프로젝트 파일 작성법 전체는 [Setting](Docs/ko/setting.md#프로젝트-파일-작성법)에 있습니다.

### 명령줄 옵션

| 옵션 | 효과 |
| --- | --- |
| `--project TOML` | 시작할 때 이 프로젝트 파일을 로드하고 Home에서 시작 |
| `--tab home\|data\|model\|run\|result\|setting` | 이 탭에서 시작. 기본값은 `home`, 프로젝트가 없으면 `setting` |
| `--theme light\|dark` | 라이트 또는 다크 테마로 시작 (기본값: light) |
| `--frameless` | 시스템 타이틀 바 대신 Laboard의 어두운 타이틀 바 사용 |
| `--screenshot out.png` | 창을 한 번 그려 PNG로 저장하고 종료. `QT_QPA_PLATFORM=offscreen`이면 화면 없이도 동작 |

## 🗂️ Data Format

`[Data] Type = "CSV"` / `"DB"`로 데이터를 읽을 때 csv·테이블에 필요한 열과 라벨 저장 형식입니다.
전체 설명은 [Data · 데이터 형식](Docs/ko/data.md#데이터-형식-필수-열과-라벨-format)에 있습니다.

**열**

| 열 | 필요 | 값 |
| --- | --- | --- |
| 파일 경로 (`file_path` 등, `[Data] Raw`로 지정) | **필수** | 원본 파일 경로. DB는 절대 경로, CSV는 절대 경로 또는 csv 위치 기준 상대 경로 |
| 라벨 (`[Label] Label` / `<Task>_Label`로 지정) | 정답을 보려면 필수 | 아래 라벨 format |
| task (`task` / `object`) | 파일 하나를 task마다 한 행으로 저장할 때 **필수** | `[Project] Task`의 task 이름 |
| split (`type`, `split` 등) | 선택 (권장) | `train` / `valid` / `test` |
| 생성일 (`create_date` 등) | 선택 | `2024-01-05 10:00:00` |

- **파일당 한 행:** task마다 라벨 열을 따로 두고 `<Task>_Label`로 지정합니다.
- **task당 한 행:** task 열 + 라벨 열 하나를 두고 `Label = "label"` 하나로 지정합니다. 같은 파일 경로가 여러 행에
  나오면 이 형식으로 읽습니다.

**라벨 format**: 일반 문자열 또는 coco format json. json은 Data 페이지에서 이미지 위에 그립니다.

| task | 형식 |
| --- | --- |
| classification | `cat` 또는 `["cat", "dog"]` |
| object detection | `[{"category": "cat", "bbox": [x, y, w, h]}]` |
| segmentation | `[{"category": "cat", "segmentation": [[x1, y1, x2, y2, …]]}]` (polygon, 또는 RLE `{"counts", "size"}`) |
| pose-estimation | `[{"category": "person", "bbox": [x, y, w, h], "keypoints": [x, y, v, …]}]` |
| panoptic segmentation | `{"mask_path": "<png 절대 경로>", "segments_info": [{"id", "category", "bbox"}]}` |

- 좌표는 이미지 픽셀 기준(원점 왼쪽 위)이고, bbox는 `[x, y, w, h]`입니다.
- 반드시 `json.dumps`로 저장하세요. `str(list)`로 저장한 `['cat']`(작은따옴표)은 json이 아니어서 그리지 않습니다.
- DB 라벨 열은 `JSONB`(권장) 또는 `TEXT`로 만듭니다.

---

## 📚 Documentation

페이지별 상세 설명은 [Docs](Docs/README.md)에 있습니다.

| 페이지 | 용도 |
| --- | --- |
| [Home](Docs/ko/home.md) | 데이터 / 모델 / 최근 run / 결과 요약과 git 기록 |
| [Data](Docs/ko/data.md) | 모든 데이터 파일과 split, 레이블을 보고 모델 예측과 비교 |
| [Model](Docs/ko/model.md) | 모델 파일의 Netron 그래프, 속성, 레이어별 파라미터 |
| [Hyperparameter](Docs/ko/run.md) | 학습 run의 진행 상황과 모든 하이퍼파라미터 |
| [Result](Docs/ko/result.md) | csv / jsonl / TensorBoard 차트, 곡선 비교, 표, 로그, 이미지 |
| [Setting](Docs/ko/setting.md) | 프로젝트 파일 로드, 감지된 항목, 테마 전환, 프로젝트 파일 작성법 |

---

## 🖥️ The Window


### 상단 바

- **탭**으로 여섯 페이지를 오갑니다.
- **브랜치 칩**은 저장소 상태를 보여 줍니다. 예: `main @a1b2c3d · 2 uncommitted · ↑1 ↓0 vs origin/main`.
  현재 브랜치와 커밋, 커밋하지 않은 파일 수(없으면 `clean`), upstream보다 앞선/뒤처진 커밋 수입니다.
  예전 커밋을 보고 있을 때는 `detached @<hash> · read-only snapshot`으로 표시됩니다.
- **Show project as of**를 누르면 git log 팝업이 열립니다.
  - 커밋은 날짜별로 묶여 메시지, 해시, 작성자, 시간이 표시됩니다. 지금 화면의 커밋은 강조되고
    `HEAD`에는 표시가 붙습니다.
  - upstream이 있으면 앞섬/뒤처짐 수, 마지막 fetch 시점, **All / Local / Remote** 필터도 나옵니다.
    한쪽에만 있는 커밋에는 마지막 fetch 기준으로 *Local · not pushed* 또는 *Remote · not pulled*가
    붙습니다. Laboard는 스스로 fetch하지 않으므로 **Fetch**를 누르세요.
  - 커밋을 클릭하면 모든 페이지가 그 커밋 시점으로 다시 로드됩니다. **Back to latest**나 `HEAD`
    커밋을 누르면 현재 상태로 돌아옵니다.

### 예전 커밋 보기

예전 커밋 보기는 읽기 전용이며 작업 트리, 인덱스, `HEAD`를 건드리지 않습니다.

- 저장소 안의 경로는 임시 폴더의 `git archive` 스냅샷에서 읽습니다. 스냅샷은 Laboard 종료 시 삭제됩니다.
- 그 커밋 시각 이후에 생성된 데이터베이스 행은 숨겨집니다 (생성일 성격의 열이 있어야 함).
- git이 추적하지 않거나 저장소 밖에 있는 경로는 기록이 없으므로 비어 있습니다. 어떤 경로인지는 상태
  바에 표시됩니다.
- 각 페이지에서 선택한 항목은 그 커밋에도 있으면 그대로 유지됩니다.

### 왼쪽 사이드바

페이지마다 왼쪽에 목록이 있습니다: 루트 폴더(Home), 데이터 폴더와 파일(Data), 모델 파일(Model),
하이퍼파라미터 세트(Hyperparameter), 결과 파일(Result), 최근 프로젝트(Setting). 모든 목록에 공통인 기능:

- **필터 상자:** 입력한 글자가 이름에 들어 있는 행만 남깁니다 (대소문자 무시).
- **폴더 트리** (Model, Hyperparameter, Result): 폴더는 접힌 상태로 시작하고 클릭하면 펼쳐집니다. 하위 폴더 하나만
  있는 폴더는 한 행으로 합쳐집니다 (`a/b/c/`). 필터를 입력하는 동안에는 일치 항목이 있는 폴더가 모두 펼쳐집니다.
- **긴 목록:** 선택 주변 200개 행만 한 번에 만듭니다. 나머지는 필터로 찾으세요.
- **같은 이름:** 다른 폴더에 같은 이름의 파일이 있으면 상대 경로로 표시합니다.

### 사이드 패널

- 패널 옆 경계선을 드래그하면 너비가 바뀝니다. 최대 창 너비의 70%까지이고, 40px보다 좁히면 숨겨집니다.
- 경계선을 더블클릭하면 패널을 숨기거나 원래 너비로 되돌립니다.
- 창이 너무 좁으면 내용을 찌그러뜨리지 않고 페이지 전체가 가로로 스크롤됩니다.

### 탭을 바꿀 때 유지되는 것

- **유지됨:** 각 페이지에서 선택한 항목 (파일, 모델, run).
- **초기화됨:** 페이지를 보는 방식. 필터, 확대/축소, Raw / Predict 보기, 체크한 차트, 차트 크기, 표
  페이지, 펼친 폴더, 패널 너비.

### 상태 바

- **왼쪽:** 프로젝트가 가리키는 폴더(models, runs, results), Python과 PyQt6 버전, 데이터 출처.
- **가운데:** 가장 최근 메시지. 예: 로드 메모가 붙은 `Loaded …`, 로드 오류, 읽기 전용 스냅샷 안내.
- **오른쪽:** 프로젝트를 로드한 시각.


