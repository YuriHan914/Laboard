<p align="center">
  <img src="../assets/LABOARD_SETTING.png" alt="Setting" width="900"/>
</p>

# Setting

[English](../en/setting.md) | **한국어**

Setting 페이지에서 할 수 있는 일:

- 프로젝트 파일 로드
- 파일의 값을 하나씩 수정하고, 결과를 새 파일로 저장
- 파일이 가리키는 각 위치에서 Laboard가 무엇을 찾았는지 확인
- 테마 전환

프로젝트 없이 실행하면 이 페이지에서 시작합니다.

## Load project file

1. `.toml` 파일 경로를 입력하거나, **Browse**로 파일을 고릅니다. Browse는 경로만 채웁니다.
2. **Load**를 누르거나 Enter를 누르면 로드됩니다.

상황별 결과:

| 상황 | 결과 |
| --- | --- |
| 입력란이 비어 있음 | 상태 바에 *Choose a project file first* |
| `.toml` 파일이 아님 | 상태 바에 *Not a .toml file* |
| 파일이 없거나 형식이 잘못됨 | 상태 바에 오류가 표시되고, 이전 프로젝트가 그대로 유지됨 |
| 로드 성공 | 모든 페이지가 다시 로드되고, 상태 바에 `Loaded <path>`와 메모가 표시됨 |

메모의 예: *Nothing found in Path.Hyperparameter*, *[Data] Type is not set*, *DB … unavailable (…)*.
메모별 해결 방법은 [Data 문서의 자주 보는 알림](data.md#자주-보는-알림)을 보세요.

## 프로젝트 파일

로드한 파일을 두 가지로 보여 줍니다.

- **Fields**는 모든 값을 섹션별로 보여 줍니다. 값 옆의 **Edit**를 누르면 수정 팝업이 뜹니다. **Save**(또는 Enter)는
  값을 적용하고 프로젝트를 다시 로드하며, **Cancel**은 수정을 취소합니다.
  - 목록은 고정입니다: 분류 프로젝트의 모든 key(저장소 루트의 `template.toml`에 있는 key)를 로드한 파일과 상관없이
    같은 순서로 보여 줍니다. 파일에 없거나 비어 있는 key는 빈칸으로 나오고, 파일에만 있는 다른 key는 그 뒤에 나옵니다.
    `[DB]` 섹션은 `[Project] DB`가 True일 때만 보입니다. `Table`은 `Type = "DB"`일 때만,
    `[Prediction] Format`은 `Type = "Folder"`일 때만 보입니다.
  - key나 값에 마우스를 올리면 어떤 값을 넣어야 하는지 설명이 나오고, Edit 팝업에도 같은 설명이 표시됩니다.
    이 설명은 Laboard에 고정되어 있으며 파일 내용과 무관합니다.
  - 적용한 값은 현재 세션에만 반영되고 디스크의 toml 파일은 바뀌지 않습니다. 머리글에 *Edited*가 표시되며,
    **Load**를 누르면 파일을 다시 읽어 수정 내용이 사라집니다.
  - **Save as…**(수정한 뒤에 나타남)는 수정된 프로젝트를 새 toml 파일(기본 `<이름>_edited.toml`)로 저장하고
    그 파일을 로드합니다. 로드된 원래 파일에는 덮어쓰지 않습니다.
  - `[Project] Task`, `[Project] DB`, `[Data] Type`, `[Prediction] Type`, `[Prediction] Format`은 드롭다운입니다.
    파일에 없어도 목록에 나오며, 빈 항목을 고르면 그 key를 지웁니다.
  - 나머지 값은 직접 입력합니다. 경로 값은 입력창 안의 폴더 아이콘으로 파일이나 폴더를 고를 수 있습니다:
    `Type = "CSV"`면 파일, `Type = "Folder"`와 `[Path]`는 폴더.
  - 주석, 순서, 형식은 그대로 두고 수정한 줄만 바뀝니다. 올바른 toml 값이 아니면 적용하지 않고 팝업에
    이유를 표시합니다.
  - Save로 다시 로드해도 스크롤 위치는 그대로 유지됩니다.
- **Text**는 줄 번호가 붙은 읽기 전용 사본입니다. 섹션 머리글(`[Project]`, `[Path]` 등)은 굵게 표시됩니다.

## Detected

프로젝트의 각 부분에서 Laboard가 찾은 내용을 상태 배지와 함께 보여 줍니다.

| 행 | 배지 |
| --- | --- |
| Git repository | *Found* (브랜치 · 커밋 수) / *Not found* |
| Snapshot | *Past commit*. 예전 커밋을 볼 때만 표시 |
| Database | *Connected* / *Unreachable* (오류 내용 포함) |
| Data | *Found* (출처 · 파일 수 · 폴더 수 · 크기) / *Not found* |
| Models | *Found* / *Not found* |
| Hyperparameter | *Found* (폴더 · 세트 수) / *Not found* |
| Results | *Found* / *Not found* |
| TensorBoard | *Found*. 결과 폴더에 이벤트 파일이 있을 때 |
| Weights & Biases | *Offline*. 결과 폴더에 `offline-run-*` 폴더가 있을 때 |
| Prediction | *Found* (`[Prediction] Type = …` · 소스 수 · 예측이 있는 파일 수 · 열) / *Not found*. 분류 프로젝트 |
| Labels / inference | *Found* (결과 파일, 일치한 파일 수, 열) / *Not found*. 이전 형식 |

## Appearance

**Light / Dark**로 테마가 바로 바뀝니다. 시작할 때의 테마는 `--theme` 옵션으로 정합니다.

## 왼쪽 사이드바

**Recent projects**에는 지금 로드된 프로젝트가 나옵니다.

## 프로젝트 파일 작성법

프로젝트 파일은 toml 형식입니다. 저장소 루트의 `template.toml`에 모든 key가 빈 값으로 들어 있으니 복사해서
시작하면 됩니다. Setting의 **Fields**에서도 같은 key를 같은 순서로 보여 주고 고칠 수 있습니다.

- **이름 규칙:** 섹션과 key 이름은 첫 글자를 대문자로 씁니다(`DB`는 전부 대문자, 경로 섹션은 `[Path]`).
  소문자로 써도 똑같이 읽습니다.
- **경로:** 절대 경로, 또는 toml 파일이 있는 폴더 기준의 상대 경로입니다.
- **빈 값:** 쓰지 않는 key는 `""`로 비워 둡니다. 비어 있는 key는 설정하지 않은 것으로 봅니다.
- **True / False:** Laboard는 `True` / `False`를 씁니다. 표준 TOML의 `true` / `false`도 읽습니다.

### 전체 예시

```toml
[Project]
Name = "Anomaly-Detection"
Root = "/mnt/data/github/Anomaly-Detection/test_projects"
Task = "classification"            # task 하나, 또는 쉼표로 여러 개: classification, object detection,
                                   # segmentation, anomaly detection, pose-estimation
DB = False                         # [Data] / [Label] / [Prediction]에서 Type = "DB"를 쓰면 True

[DB]                               # DB = True일 때만 사용 (Setting에서도 그때만 보임)
DB = "supabase"
DB_ip = "http://127.0.0.1:54323/"

[Git]
Remote = "github.com:YuriHan914/Anomaly-Detection.git"
Branch = "main"

[Path]
Models = "/mnt/data/github/Anomaly-Detection/test_projects/Models"
Hyperparameter = "/mnt/data/github/Anomaly-Detection/test_projects/Runs"
Results = "/mnt/data/github/Anomaly-Detection/test_projects/Results"

[Data]                             # 원본 데이터: 모든 task가 같이 씀
Type = "CSV"                       # CSV | DB | Folder
File_path = "/mnt/data/github/Anomaly-Detection/test_projects/Data/semiconductor_AD_df.csv"
Table = ""                         # Type = "DB"일 때만
Raw = "file_path"                  # 원본 파일 경로 열 (CSV / DB)

[Label]                            # 정답: task마다 <Task>_Label
Type = "CSV"                       # CSV | DB | Folder
File_path = "/mnt/data/github/Anomaly-Detection/test_projects/Data/semiconductor_AD_df.csv"
Classification_Label = "label"

[Prediction]                       # <Task>_<Key>로 task 하나만 다르게 설정 가능
Type = "CSV"                       # CSV | DB | Folder
File_path = "inference.csv"        # Path.Results/<task>/ 아래에서 찾음
Table = ""                         # Type = "DB"일 때만
Format = ""                        # Type = "Folder"일 때만: txt | json
Predict = "classification"
Predict_score = "AD_score"
```

### 섹션별 key

**`[Project]`**

| key | 넣을 값 |
| --- | --- |
| `Name` | 상단 바와 Home에 표시할 프로젝트 이름. 비우면 Root 폴더 이름 |
| `Root` | 프로젝트 git 저장소 폴더. git 기록·브랜치·원격 정보를 여기서 가져옴. 비우면 데이터·`[Path]` 경로 중 첫 번째, 없으면 toml이 있는 폴더 |
| `Task` | task 하나, 또는 쉼표로 여러 개. `classification`, `object detection`(`detection`), `segmentation`, `instance segmentation`, `semantic segmentation`, `panoptic segmentation`, `anomaly detection`, `pose-estimation`(`keypoints`) (대소문자·공백·`_`·`-` 무관). 비우면 [이전 형식](#이전-형식) |
| `DB` | `[Data]`, `[Label]`, `[Prediction]`에서 `Type = "DB"`를 쓰면 `True`. `False`면 DB를 쓰지 않음 |

**`[DB]`** (`[Project] DB = True`일 때)

| key | 넣을 값 |
| --- | --- |
| `DB` | DB 종류. `supabase` |
| `DB_ip` | DB 주소. Supabase URL(`http://127.0.0.1:54323/` → 그 Postgres의 54322 포트), 또는 `postgresql://user:password@host:5432/dbname` |

기본값과 다르면 `Port`, `User`, `Password`, `Database`(기본: 54322 / postgres / postgres / postgres)와
`Limit`(읽을 최대 행 수, 기본 200,000)를 추가할 수 있습니다.

**`[Git]`** git에서 알 수 없을 때만 쓰는 대체값입니다.

| key | 넣을 값 |
| --- | --- |
| `Remote` | origin 원격이 없을 때 표시할 원격 주소. 예: `github.com:user/repo.git` |
| `Branch` | HEAD가 detached이거나 Root가 git 저장소가 아닐 때 표시할 브랜치. 예: `main` |

**`[Path]`**

| key | 넣을 값 |
| --- | --- |
| `Models` | 모델 체크포인트(.pt, .onnx, .safetensors 등) 폴더 → [Model](model.md) 페이지 |
| `Hyperparameter` | 학습 실행마다 하위 폴더가 있고 그 안에 json / yaml / toml 설정이 있는 폴더 → [Hyperparameter](run.md) 페이지. |
| `Results` | 결과 파일(csv, 로그, 이미지, TensorBoard 이벤트 등) 폴더 → [Result](result.md) 페이지. `[Prediction] Type = "CSV"`도 여기서(`Results/<task>/`) 찾음 |

세 폴더 모두 task 이름 폴더로 나눌 수 있습니다(예: `Models/classification/<모델>/`).

**다른 컴퓨터의 파일.** 경로를 `host:path`로 쓰면 됩니다. 예: `Hyperparameter = "gcloud:~/laboard/Runs"`.
모든 경로에 쓸 수 있습니다: `[Path]` 폴더, `[Data]` / `[Label]` / `[Prediction]`의 `File_path`(라벨 / 예측 폴더 포함),
csv나 DB 테이블의 파일 경로 열(`gcloud:~/laboard/img/0001.jpg`). ssh로 `host`에 접속해 읽으며 그 컴퓨터의 파일은 바꾸지 않습니다.

- `[Path]` 폴더와 `[Data]` / `[Label]` / `[Prediction]` 파일은 불러올 때마다 임시 폴더로 복사합니다(Hyperparameter: 설정
  파일만, Models: 500 MB 미만 파일, Results와 라벨 / 예측 폴더: 50 MB 미만 파일).
- 데이터 파일(`[Data] Type = "Folder"` 폴더, 테이블에 적힌 파일)은 불러올 때 복사하지 않고 크기와 시간만 읽습니다. Data 페이지가
  보여 주는 파일과 썸네일을 그때 가져오고, Laboard를 끌 때까지 보관합니다.

`host`의 접속 명령은 아래 순서로 먼저 찾은 것입니다.

- `[SSH] gcloud = "SSH/gcp.key"`: 접속 명령이 들어 있는 파일. 예: `gcloud compute ssh my-vm --zone us-west1-b`,
  `ssh -i ~/.ssh/key user@1.2.3.4` (개인 키 파일이면 `ssh -i <파일> host`로 씁니다)
- 프로젝트 파일 옆 `SSH/<host>.*` 파일, 또는 그 `SSH/` 폴더에 파일이 하나뿐이면 그 파일
- `ssh host` (`~/.ssh/config`의 Host)

비밀번호를 묻지 않고 접속되어야 합니다.

**`[Data]` / `[Label]` / `[Prediction]`** Type에 따라 쓰는 key가 다릅니다. Type별 상세 설명과 필요한 열은
[Data 페이지 문서의 데이터 설정](data.md#데이터-설정), [라벨 설정](data.md#라벨-설정-label),
[예측 설정](data.md#예측-설정-prediction)을 보세요.

| key | 넣을 값 |
| --- | --- |
| `[Data] Type` | `DB` / `CSV` / `Folder` |
| `[Data] File_path` | CSV: 파일 목록 csv 경로 · Folder: `split/label/파일` 구조의 데이터셋 폴더 |
| `[Data] Table` | DB: 파일 하나당 한 행인 테이블 |
| `[Data] Raw` | DB / CSV: 원본 파일 경로가 든 열 이름(예: `file_path`). 비우면 자동으로 찾음 |
| `[Label] Type` | `CSV` / `DB` / `Folder` |
| `[Label] File_path` | CSV: 라벨 csv(비우면 `[Data]` csv) · Folder: 라벨 폴더들이 있는 폴더 |
| `[Label] Table` | DB: 라벨 테이블(비우면 `[Data]` 테이블) |
| `[Label] <Task>_Label` | task별 정답. CSV / DB: 열 이름 · Folder: classification은 클래스 폴더, 다른 task는 라벨 파일 폴더 |
| `[Label] Label` | CSV / DB: `<Task>_Label`이 없는 모든 task의 정답 열. task 열이 있어 파일 하나가 task마다 한 행인 csv·테이블은 task마다 자기 행을 씁니다 |
| `[Prediction] Type` | `CSV` / `DB` / `Folder` |
| `[Prediction] File_path` | CSV: `[Path] Results/<task>` 아래의 결과 파일 이름 / glob · Folder: 예측 파일 폴더 |
| `[Prediction] Table` | DB: 예측이 들어 있는 테이블 |
| `[Prediction] Format` | Folder: `txt`(`<클래스> [점수]`) / `json` |
| `[Prediction] Predict` | 예측 클래스 열(json이면 key) |
| `[Prediction] Predict_score` | 점수 열(json이면 key) |

### 섹션을 쓰는 곳

| 섹션 | 사용하는 곳 |
| --- | --- |
| `[Project]`, `[Git]` | 상단 바, Home, git log 팝업 |
| `[Data]`, `[DB]` | [Data](data.md), Home의 Data 카드 |
| `[Label]` | [Data](data.md) 페이지의 정답 표시, 클래스 목록 |
| `[Prediction]` | [Data](data.md) 페이지의 예측 표시 |
| `[Path] Models` | [Model](model.md), Home의 Model 카드 |
| `[Path] Hyperparameter` | [Hyperparameter](run.md), Home의 Latest hyperparameter 카드 |
| `[Path] Results` | [Result](result.md), Home의 Result 카드 |

찾지 못한 부분은 비어 있고, 어느 부분이 그런지는 Detected 카드와 상태 바에서 확인할 수 있습니다.

### 이전 형식

`Task`가 비어 있으면 이전 형식으로 읽습니다. 데이터 위치는 `[Path] Data`로,
예측은 `[Labels]`로 정합니다. 자세한 읽기 순서는 [Data 문서의 이전 형식](data.md#이전-형식-task가-비어-있을-때)을
보세요.

```toml
[Path]
Data = "/path/to/data"             # 데이터 폴더, 파일 목록(csv / tsv / jsonl / parquet), 또는 "DB" 같은 섹션 이름

[DB]                               # 접속 가능하면 Path.Data보다 먼저 사용
Supabase = "http://127.0.0.1:54323/"
Table = "my_table"                 # 또는 "schema.table"
# Dsn = "postgresql://user:pw@host:5432/db"
# Columns = { Path = "file_path", Split = "type" }   # 정답은 항상 "label" 열

[Models]                           # 선택 사항
# Extensions = [".pt", ".onnx"]

[Labels]                           # 선택 사항 ([Lables]로 써도 읽음)
Result_file = "inference.csv"      # Path.Results 아래의 이름 / glob. 일치하는 파일마다 하나의 소스
Infer = "classification"           # 나머지 key는 모두 Data 페이지에 표시할 열
Score = "AD_result"
# Path = "data_path"               # 행을 데이터 파일과 매칭할 열 (생략하면 추정)
```
