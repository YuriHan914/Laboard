<p align="center">
  <img src="../assets/LABOARD_DATA.png" alt="Data" width="900"/>
</p>

# Data

[English](../en/data.md) | **한국어**

Data 페이지는 데이터셋의 모든 파일을 보는 뷰어입니다. 파일마다 다음을 볼 수 있습니다.

- 파일 자체
- split (train / valid / test)
- 레이블
- 모델이 그 파일에 대해 예측한 값

## 데이터 설정

프로젝트 파일(toml)의 세 섹션이 Data 페이지에 보일 내용을 정합니다.

| 섹션 | 정하는 것 | task와의 관계 |
| --- | --- | --- |
| `[Data]` | 원본 데이터 파일 목록 | 모든 task가 하나를 같이 씀 |
| `[Label]` | 각 파일의 정답 | task마다 `<Task>_Label` 하나씩 ([라벨 설정](#라벨-설정-label)) |
| `[Prediction]` | 각 파일의 모델 예측 | task마다 따로 읽음 ([예측 설정](#예측-설정-prediction)) |

이 형식은 `[Project] Task`에 아래 task가 하나 이상 있을 때 쓰입니다([Task: 단일 / 다중](#task-단일--다중)).
Task가 비어 있으면 [이전 형식](#이전-형식-task가-비어-있을-때)을 따릅니다.

| `[Data] Type` | 파일 목록을 가져오는 곳 | split |
| --- | --- | --- |
| `DB` | 데이터베이스 테이블 (한 행 = 파일 하나) | split 열 (`type`, `status` 등) |
| `CSV` | 파일 목록 csv (한 행 = 파일 하나) | split 열 (`type`, `status` 등) |
| `Folder` | 데이터셋 폴더를 스캔 | 경로의 split 폴더 이름 |

- **Type 값:** `DB`, `CSV`, `Folder`는 대소문자를 구분하지 않습니다(`csv`도 됨). 비어 있으면 상태 바에
  `[Data] Type is not set`이 뜹니다.
- **읽는 양:** 출처와 상관없이 최대 200,000개 행(파일)까지 읽습니다.
- **정답 출처:** 정답은 항상 `[Label]`에서만 가져옵니다. 예측 결과 파일에 레이블 열이 있어도 정답으로 쓰지 않습니다.
- **필수 열과 라벨 저장 형식:** [데이터 형식: 필수 열과 라벨 format](#데이터-형식-필수-열과-라벨-format)을 보세요.

### Task: 단일 / 다중

`[Project] Task`에 task 하나를 쓰거나, 여러 개를 쉼표로 나열합니다.

```toml
Task = "classification"                                   # 단일 task
Task = "classification, segmentation, object detection"   # 다중 task
```

- **쓸 수 있는 task:** `classification`, `object detection`(또는 `detection`), `segmentation`, `instance segmentation`,
  `semantic segmentation`, `panoptic segmentation`, `anomaly detection`, `pose-estimation`(또는 `keypoints`).
  대소문자, 공백, `_`, `-`는 구분하지 않습니다(`Object_detection`도 됨). 모르는 이름은 알림을 띄우고 건너뜁니다.
- **원본 데이터는 하나:** `[Data]`는 모든 task가 같이 씁니다. task마다 다른 것은 정답(`[Label]`)과 예측(`[Prediction]`)입니다.
- **폴더 구조:** `[Path]`의 Models / Hyperparameter / Results 아래에 task 이름 폴더를 두면 task별로 나눠 봅니다.

  ```text
  test_projects/
  ├── Data/semiconductor_AD_df.csv     # 원본 데이터 (하나)
  ├── Models/classification/<모델>/
  ├── Runs/classification/<모델>/      # [Path] Hyperparameter
  └── Results/
      ├── classification/<모델>/inference.csv
      ├── segmentation/
      ├── object detection/
      ├── anomaly detection/
      └── pose-estimation/
  ```

  - Model 페이지와 Home은 `Models/<task>/<모델>`을 모델 하나로 묶습니다.
  - CSV 예측은 `Results/<task>/` 아래에서 찾습니다.
- **Data 페이지:** task가 여럿이면 뷰어 머리글에 **Task** 드롭다운이 생기고, 고른 task의 정답과 예측을 보여 줍니다.
  File info에는 모든 task의 정답이 `Label · <task>`로 나옵니다.
- **Home:** 작업 이름에 task가 모두 나옵니다(예: *Classification · Segmentation · Object detection*).

### 설정 바꾸는 법

**Setting 페이지에서 (권장)**

1. **Setting → Load project file**에서 toml을 고르고 **Load**를 누릅니다.
2. 아래 **Fields** 목록에서 `[Data]` → `Type` 옆의 **Edit**를 누릅니다.
3. 팝업의 드롭다운에서 `CSV` / `DB` / `Folder`를 고르고 **Save**를 누릅니다.
4. 같은 방법으로 그 Type에 필요한 key(아래 표)를 채웁니다. 경로 값은 입력칸 안의 폴더 아이콘으로 고를 수
   있습니다.

- **바로 적용:** Save하면 프로젝트를 다시 읽어 Data 페이지에 곧바로 반영됩니다.
- **파일은 그대로:** 디스크의 toml 파일은 바뀌지 않습니다. 바꾼 내용을 남기려면 **Save as…**로 새 toml을
  저장하세요. **Load**를 다시 누르면 파일 내용으로 돌아갑니다.
- **Type에 따라 보이는 행:**
  - `Table`은 `Type = "DB"`일 때만, `File_path`는 DB가 아닐 때만, `[Data] Raw`는 Folder가 아닐 때만 보입니다.
  - `[Label]`에는 `[Project] Task`의 task마다 `<Task>_Label` 행이 생깁니다.
  - `[DB]` 섹션은 `[Project] DB = True`일 때만 보입니다.
- **설명 보기:** key나 값에 마우스를 올리면 무엇을 넣어야 하는지 설명이 나옵니다.

**toml 파일을 직접 수정**

편집기로 toml을 고친 뒤 Setting에서 **Load**를 누릅니다. 저장소 루트의 `template.toml`에 모든 key가
빈 값으로 들어 있으니 복사해서 쓰면 됩니다. 섹션·key 이름은 대소문자를 구분하지 않습니다(`[Path]`와
`[paths]`도 같음).

### `[Data]` key 한눈에 보기

| key | `DB` | `CSV` | `Folder` | 설명 |
| --- | --- | --- | --- | --- |
| `Type` | 필수 | 필수 | 필수 | `DB` / `CSV` / `Folder` |
| `Table` | 필수 | – | – | 테이블 이름. `table` 또는 `schema.table` |
| `File_path` | – | 필수 | 필수 | CSV: 목록 파일 경로 · Folder: 데이터셋 폴더 |
| `Raw` | 선택 | 선택 | – | 원본 파일 경로가 든 열 이름(예: `file_path`). 비우면 자동으로 찾음 (아래 표) |

`File_path` 같은 경로는 절대 경로, 또는 toml 파일이 있는 폴더 기준의 상대 경로로 씁니다.

### Type = DB

데이터베이스 테이블의 한 행이 데이터 파일 하나입니다. 로컬 Supabase나 일반 Postgres를 쓸 수 있습니다.

```toml
[Project]
DB = True                          # DB를 쓰려면 True

[DB]                               # 접속 정보
DB = "supabase"
DB_ip = "http://127.0.0.1:54323/"  # Supabase 주소 → 그 Postgres(54322 포트)에 접속

[Data]
Type = "DB"
Table = "semiconductor"
Raw = "file_path"
```

- **접속 (`[DB] DB_ip`):**
  - Supabase URL(`http://127.0.0.1:54323/` 등)이면 그 호스트의 Postgres에 접속합니다. 기본값은 포트
    `54322`, 사용자·비밀번호·DB 이름 모두 `postgres`입니다.
  - `postgresql://user:password@host:5432/dbname` 형태의 주소도 됩니다.
  - 기본값이 다르면 `[DB]`에 `Port`, `User`, `Password`, `Database`를 추가합니다. 읽을 최대 행 수는 `Limit`으로 정합니다.
- **`[Project] DB`:** `False`이면 DB를 읽지 않고 `[Data] Type = DB, but [Project] DB = False` 알림이 뜹니다.
- **테이블에 필요한 열:**

  | 열 | 필수 | 내용 |
  | --- | --- | --- |
  | 파일 경로 | 필수 | 원본 파일의 경로. `[Data] Raw`에 적은 열, 없으면 아래 [열 찾기](#열-찾기) 표 참고 |
  | split | 선택 | `type`, `status`, `split` 등. 없으면 모두 Unused |
  | 생성일 | 선택 | `create_date` 등. File info의 Created, 월별 추가 그래프, 과거 커밋 보기에 사용 |
  | 학습 여부 | 선택 | `trained` / `used` (true/false). Home에 학습 사용/미사용 개수 표시 |
  | 작업 종류 | 선택 | `object` / `task`. Home의 작업 이름 |
  | id | 선택 | File info의 Row |

- **예시 (`semiconductor` 테이블):** `id`, `file_path`, `object`, `type`, `extension`, `label`, `create_date`,
  `trained`, `predict`
  - `file_path`가 경로, `label`이 정답, `type`이 split으로 쓰입니다.
  - 테이블의 `predict` 열은 Type = DB 데이터에서 예측으로 쓰지 않습니다. 예측은 `[Prediction]`에서 정합니다.
- **과거 커밋 보기:** 상단 "Show project as of"로 과거 커밋을 보면, 그 시점 이후에 생성된 행(생성일 열 기준)은
  숨겨집니다.
- **연결 상태:** Setting의 Detected에서 확인합니다(`Database · Connected` / `Unreachable`).

### Type = CSV

csv 파일의 한 행이 데이터 파일 하나입니다. tsv, jsonl, parquet도 같은 방식으로 읽습니다.

```toml
[Data]
Type = "CSV"
File_path = "/mnt/data/github/Anomaly-Detection/test_projects/Data/semiconductor_AD_df.csv"
Raw = "file_path"
```

- **csv에 필요한 열:** Type = DB의 테이블과 같습니다. 파일 경로 열은 필수이고, 정답(`label`)·split 열이 있으면
  씁니다.

  ```csv
  data_path,label,status
  /mnt/data/Dataset/wafer/test/Normal/image_001.jpg,Normal,test
  /mnt/data/Dataset/wafer/train/Scratch/image_002.jpg,Scratch,train
  ```

- **상대 경로:** csv 안의 경로가 상대 경로이면 csv 파일이 있는 폴더 기준으로 읽습니다.
- **잘못된 경로:** `File_path`가 파일이 아니면 `[Data] File_path … is not a file` 알림이 뜹니다.
- **경로 열을 못 찾을 때:** `[Data] Raw`에 열 이름을 적습니다.

### Type = Folder

데이터셋 폴더를 스캔해서 파일마다 한 행을 만듭니다. split과 정답은 폴더 구조에서 가져옵니다.

```toml
[Data]
Type = "Folder"
File_path = "/mnt/data/Dataset/semiconductor_waifer_defect_classification"
```

- **폴더 구조:** `<split>/<label>/<파일>` 형식이어야 합니다.

  ```text
  semiconductor_waifer_defect_classification/
  ├── train/
  │   ├── Normal/   image_001.jpg …
  │   └── Scratch/  image_101.jpg …
  ├── valid/
  │   └── …
  └── test/
      └── …
  ```

- **split 폴더 찾기:** 경로에서 처음 나오는 split 이름 폴더(`train`, `valid`, `test` 등, 아래 split 값 표)를
  찾습니다. 그 **바로 다음 폴더 이름**이 정답입니다.
  - `root/2024/train/Normal/x.jpg`처럼 위에 폴더가 더 있어도 됩니다 → split `train`, 정답 `Normal`
  - `train/Normal/sub/x.jpg`처럼 아래에 폴더가 더 있어도 정답은 `Normal`입니다.
- **정답이 없는 경우:**
  - `Normal/x.jpg`처럼 split 폴더가 없으면 split은 Unused, 정답은 없습니다.
  - `Normal/train/x.jpg`처럼 순서가 반대이거나 `train/x.jpg`처럼 정답 폴더가 없어도 정답은 없습니다.
- **`[Data] Raw`:** 쓰지 않습니다. classification 정답은 `[Label] Type = "Folder"`일 때 이 폴더 구조에서 가져옵니다.
- **제외하는 파일:**
  - 코드·노트북·마크다운: `.py`, `.pyc`, `.ipynb`, `.sh`, `.md`
  - 테이블 파일: `.csv`, `.tsv`, `.jsonl`, `.parquet`
  - 숨김 파일과 `__pycache__`
  - `[Prediction] Type = "Folder"`일 때 예측 파일 형식(`.txt` / `.json`). 예측 파일을 데이터 옆에 둬도
    데이터로 잡히지 않습니다.

### 열 찾기

Type = DB / CSV에서 각 의미의 열을 이름으로 찾습니다(대소문자 무시, 먼저 일치하는 것 사용).

| 의미 | 인식하는 이름 |
| --- | --- |
| 파일 경로 | `[Data] Raw`에 적은 열, 없으면 `file_path`, `data_path`, `path`, `filepath`, `file`, `image`, `image_path`, `img`, `filename` |
| split | `type`, `status`, `split`, `subset`, `set` |
| 작업 종류 | `object`, `task` |
| 생성일 | `create_date`, `created_at`, `created`, `date`, `timestamp` |
| 학습 여부 | `trained`, `used` |
| id | `id` |

- **경로 열 확인:** 이름이 맞아도 값이 경로처럼 보이지 않으면(확장자나 `/`가 없음) 경로 열로 쓰지 않습니다.
  이때는 값이 경로처럼 보이는 다른 열을 찾습니다.
- **split 열 추정:** 이름이 맞는 열이 없으면, 값이 모두 split 값인 열을 split 열로 씁니다.

### split 값

아래처럼 읽습니다(대소문자 무시). 그 외 값은 **Unused**가 됩니다.

| 데이터의 값 | 읽는 방식 |
| --- | --- |
| `train`, `training` | Train |
| `val`, `valid`, `validation`, `eval`, `dev` | Valid |
| `test`, `testing` | Test |

### 폴더 묶기

사이드바의 폴더는 파일의 디렉터리에서 split 부분을 뺀 이름으로 묶입니다. 그래서 `train/cat/`과 `valid/cat/`은
둘 다 `cat` 폴더로 보입니다.

## 라벨 설정 (`[Label]`)

정답도 `Type`(`CSV` / `DB` / `Folder`)으로 출처를 정하고, task마다 `<Task>_Label` key를 하나씩 둡니다.

| key | `CSV` | `DB` | `Folder` | 설명 |
| --- | --- | --- | --- | --- |
| `Type` | 필수 | 필수 | 필수 | `CSV` / `DB` / `Folder` |
| `File_path` | 선택 | – | 선택 | CSV: 라벨 csv(비우면 `[Data]` csv) · Folder: 라벨 폴더들이 있는 폴더(비우면 데이터 폴더) |
| `Table` | – | 선택 | – | 라벨 테이블(비우면 `[Data]` 테이블) |
| `<Task>_Label` | 열 이름 | 열 이름 | 아래 참고 | `Classification_Label`, `Segmentation_Label`, `Object_detection_Label`, `Anomaly_detection_Label`, `Pose_estimation_Label` |
| `Label` | 열 이름 | 열 이름 | – | `<Task>_Label`이 없는 모든 task의 정답 열 |

- **CSV / DB:** `<Task>_Label`은 그 task의 정답이 든 열입니다. 라벨 csv·테이블의 원본 경로 열(`Raw`, 비우면
  `[Data] Raw`)로 데이터 파일과 맞춥니다. 라벨이 `[Data]`와 같은 csv·테이블에 있으면 그대로 씁니다.
- **파일 하나가 task마다 한 행:** csv·테이블에 task 열(`task` 또는 `object`)이 있고 파일 하나가 task마다 한 행씩
  나오면, 각 task는 task 값이 같은 행에서 정답을 읽고 `[Data]`에는 파일이 한 번만 나옵니다. 이런 테이블은 보통
  `Label = "label"` 하나면 됩니다.
- **json 정답**(coco format, `Src/raw_to_csv`가 만드는 형식)은 Data 페이지에서 이미지 위에 그립니다:
  `["cat", "dog"]`(클래스 이름), `[{"category", "bbox": [x, y, w, h]}]`(박스), `[{"category", "segmentation"}]`
  (polygon 또는 RLE), `[{"category", "bbox", "keypoints"}]`(keypoint, 17개면 coco skeleton도), `{"mask_path",
  "segments_info"}`(coco panoptic png). 글자로는 `20 objects · chair ×5, vase ×4`처럼 요약해 보여 줍니다. json
  예측도 Predict 창에 같은 방식으로 그립니다.
- **Folder:**
  - classification은 `[Data] Type = "Folder"`의 `split/<class>/파일` 구조에서 정답을 가져옵니다. 값은 아무것이나 됩니다.
  - 다른 task의 `<Task>_Label`은 라벨 파일이 든 폴더입니다(`File_path` 기준 상대 경로 또는 절대 경로). 데이터
    파일마다 같은 이름(확장자 제외)의 라벨 파일을 찾고, 그 파일 이름을 정답으로 표시합니다.
- **정답이 없는 task:** `<Task>_Label`이 없으면 `[Label] no <Task>_Label` 알림이 뜨고, 그 task의 정답은 비어 있습니다.

```toml
[Label]                                 # 단일 task, CSV
Type = "CSV"
File_path = "/mnt/data/github/Anomaly-Detection/test_projects/Data/semiconductor_AD_df.csv"
Classification_Label = "label"

[Label]                                 # 다중 task, DB
Type = "DB"
Table = "semiconductor"
Classification_Label = "label"
Segmentation_Label = "seg_label"
Object_detection_Label = "obj_label"

[Label]                                 # 다중 task, 파일 하나가 task마다 한 행 (task 열 + json label 열)
Type = "CSV"
File_path = "/mnt/data/Dataset/COCO/COCO_2017_dataset.csv"
Label = "label"

[Label]                                 # 다중 task, Folder
Type = "Folder"
File_path = "/mnt/data/Dataset/semiconductor_waifer_defect_classification"
Classification_Label = "label"          # 클래스 폴더
Segmentation_Label = "seg_label"        # File_path/seg_label/ 아래 라벨 파일
```

## 데이터 형식: 필수 열과 라벨 format

`[Data] Type`이 `CSV` 또는 `DB`일 때 csv·테이블이 갖춰야 할 열과, 라벨 열에 값을 저장하는 형식입니다.
`Folder`는 폴더 구조로 읽으므로 열이 필요 없습니다([Type = Folder](#type--folder)).

### 필수 열과 선택 열

| 열 | 필요 | 이름 (대소문자 무시) | 값 |
| --- | --- | --- | --- |
| 파일 경로 | **필수** | `[Data] Raw`에 적은 이름, 없으면 `file_path`, `data_path`, `path`, `image`, `filename` 등([열 찾기](#열-찾기)) | 원본 파일 경로. DB는 **절대 경로**, CSV는 절대 경로 또는 csv 파일 위치 기준 상대 경로 |
| 라벨 | 정답을 보려면 필수 | `[Label] Label` 또는 `<Task>_Label`에 적은 이름 (예: `label`) | 아래 [라벨 값 format](#라벨-값-format) |
| task | 파일 하나를 task마다 한 행으로 저장할 때 **필수** | `task`, `object` | `[Project] Task`의 task 이름 (예: `classification`, `detection`) |
| split | 선택 (권장) | `type`, `status`, `split`, `subset`, `set` | `train` / `valid`(`val`, `validation`) / `test`. 없거나 다른 값이면 Unused |
| 생성일 | 선택 | `create_date`, `created_at`, `created`, `date`, `timestamp` | ISO 형식 `2024-01-05 10:00:00` 또는 DB의 timestamp. 없으면 파일 수정 시각을 씀 |
| 학습 여부 | 선택 | `trained`, `used` | `true` / `false` (`1`, `yes`도 됨) |
| id | 선택 | `id` | File info에 표시 |

- **경로 열이 없거나 값이 경로처럼 보이지 않으면** 데이터를 읽지 않고 `no file-path column found` 알림이 뜹니다.
- **경로가 빈 행**은 건너뜁니다.
- **라벨 열이 없으면** 파일은 보이지만 정답이 비어 있고 `[Label] no <Task>_Label` 알림이 뜹니다.

### 테이블 모양: 파일당 한 행 / task당 한 행

라벨은 두 가지 모양으로 저장할 수 있습니다.

| 모양 | 행 | 라벨 열 | `[Label]` 설정 |
| --- | --- | --- | --- |
| 파일당 한 행 | 파일 하나 = 한 행 | task마다 다른 열 (예: `cls_label`, `det_label`) | `Classification_Label = "cls_label"`, `Object_detection_Label = "det_label"` |
| task당 한 행 | 파일 하나 × task 하나 = 한 행 | 열 하나 (예: `label`) + task 열 | `Label = "label"` |

- **task당 한 행으로 인식하는 조건:** task 열이 있고 같은 파일 경로가 여러 행에 나올 때입니다. 이때 각 task는
  task 값이 같은 행에서 라벨을 읽고, `[Data]`에는 파일이 한 번만 나옵니다.
- **task 값:** `[Project] Task`의 이름과 같아야 합니다. 대소문자, 공백, `_`, `-`는 무시하고(`instance_segmentation` =
  `instance segmentation`), `detection`은 `object detection`, `keypoints`는 `pose-estimation`으로 읽습니다.
- **split·생성일:** 파일의 첫 행 값을 씁니다. 같은 파일의 행끼리 값이 같게 저장하세요.

### 라벨 값 format

라벨 값은 클래스 이름 같은 **일반 문자열**이거나 **coco format json**입니다. json이면 Data 페이지에서 이미지
위에 그리고, 글자로는 `20 objects · chair ×5, vase ×4`처럼 요약해 보여 줍니다. 예측 값(`[Prediction] Predict`)도
같은 형식이면 Predict 창에 같은 방식으로 그립니다.

| task | 형식 | 예 |
| --- | --- | --- |
| classification | 문자열, 또는 클래스 이름 list | `cat` · `["cat", "dog"]` |
| object detection | `[{"category", "bbox"}]` | `[{"category": "cat", "bbox": [10, 20, 100, 80]}]` |
| segmentation (instance / semantic) | `[{"category", "segmentation"}]` | `[{"category": "cat", "segmentation": [[10, 20, 110, 20, 60, 100]]}]` |
| pose-estimation | `[{"category", "bbox", "keypoints"}]` | `[{"category": "person", "bbox": [5, 5, 50, 120], "keypoints": [30, 12, 2, 0, 0, 0, …]}]` |
| panoptic segmentation | `{"mask_path", "segments_info"}` | `{"mask_path": "/data/panoptic/0001.png", "segments_info": [{"id": 3226956, "category": "person", "bbox": [413, 158, 53, 138]}]}` |

- **좌표:** 모두 이미지 픽셀 좌표이고, 원점은 왼쪽 위, x는 오른쪽, y는 아래쪽입니다.
- **bbox:** `[x, y, w, h]` (왼쪽 위 꼭짓점과 폭·높이). `[x1, y1, x2, y2]`가 아닙니다.
- **segmentation:** polygon list `[[x1, y1, x2, y2, …], …]` (객체 하나가 polygon 여러 개일 수 있음, 점 3개 이상).
  또는 압축하지 않은 RLE `{"counts": [...], "size": [h, w]}` (열 우선 순서, 0의 run부터 시작). 압축 RLE(문자열
  `counts`)는 그리지 않습니다.
- **keypoints:** `[x, y, v]`를 keypoint 수만큼 이어 붙인 list. `v = 0`인 점은 그리지 않습니다. 17개면 coco 사람
  skeleton 선도 그립니다.
- **panoptic:** `mask_path`는 coco panoptic png의 **절대 경로**입니다. png의 픽셀 값 `R + 256·G + 256²·B`가 segment
  `id`이고, `segments_info`의 각 항목에 `id`와 `category`가 있어야 그 영역을 category 색으로 칠합니다. `bbox`가 있으면
  그 가운데에 이름을 표시합니다.
- **category:** 아무 문자열이나 됩니다. 같은 이름은 항상 같은 색으로 그립니다. Data 페이지의 클래스 목록은 모든
  라벨의 category를 모은 것입니다.
- **json이 아닌 값:** `[` 또는 `{`로 시작하지 않거나 json으로 읽히지 않는 값은 그대로 글자로만 보여 줍니다.

### 저장할 때 주의

- **반드시 json으로 저장:** Python에서 `str(list)`로 저장하면 `['cat', 'dog']`처럼 작은따옴표가 들어가 json이
  아니게 되고, 그리지 않고 글자로만 보입니다. `json.dumps(label)`로 바꾼 뒤 저장하세요.
- **CSV:** json 안의 `"`와 `,` 때문에 값을 따옴표로 감싸고 `"`를 `""`로 써야 합니다. pandas `to_csv`나 Python
  `csv` 모듈로 쓰면 자동으로 처리됩니다.
- **DB:** 라벨 열은 `JSONB`(권장) 또는 `TEXT`로 만듭니다. `JSONB`는 DB가 json 형식을 검사하고 `label->0->'bbox'`처럼
  조회할 수도 있습니다.

### 예시

task당 한 행 csv와 그에 맞는 설정입니다(`Src/raw_to_csv`가 만드는 형식).

```csv
file_path,label,task,type,create_date
/data/img/0001.jpg,"[""cat"", ""dog""]",classification,train,2024-01-05 10:00:00
/data/img/0001.jpg,"[{""category"": ""cat"", ""bbox"": [10, 20, 100, 80]}]",detection,train,2024-01-05 10:00:00
/data/img/0002.jpg,"[""dog""]",classification,valid,2024-01-06 09:30:00
```

```toml
[Project]
Task = "classification, detection"

[Data]
Type = "CSV"
File_path = "/data/dataset.csv"
Raw = "file_path"

[Label]
Type = "CSV"
File_path = "/data/dataset.csv"
Label = "label"
```

파일당 한 행이면 task마다 라벨 열을 따로 둡니다.

```csv
file_path,type,cls_label,det_label
/data/img/0001.jpg,train,cat,"[{""category"": ""cat"", ""bbox"": [10, 20, 100, 80]}]"
```

```toml
[Label]
Type = "CSV"
File_path = "/data/dataset.csv"
Classification_Label = "cls_label"
Object_detection_Label = "det_label"
```

## 예측 설정 (`[Prediction]`)

예측도 `Type`으로 출처를 정합니다. 데이터와 다른 Type을 써도 됩니다(예: 데이터는 DB, 예측은 CSV).

- **task별 설정:** 모든 key는 기본적으로 모든 task에 적용됩니다. 한 task만 다르게 하려면 `<Task>_<Key>`로 씁니다.
  예: `Segmentation_File_path`, `Segmentation_Predict`, `Object_detection_Type`.
- **소스 이름:** task가 여럿이면 Results 드롭다운의 소스 이름 앞에 task가 붙고, 고른 task의 소스만 보입니다.

| key | `CSV` | `DB` | `Folder` | 설명 |
| --- | --- | --- | --- | --- |
| `Type` | 필수 | 필수 | 필수 | `CSV` / `DB` / `Folder` |
| `File_path` | 필수 | – | 필수 | CSV: 결과 파일 이름 / glob · Folder: 예측 파일 폴더 |
| `Table` | – | 필수 | – | 예측이 들어 있는 테이블 |
| `Format` | – | – | 선택 | `txt`(기본) / `json` |
| `Predict` | 필수 | 필수 | json에서 선택 | 예측 클래스 열(json이면 key) |
| `Predict_score` | 선택 | 선택 | json에서 선택 | 점수 열(json이면 key) |

Setting에서 `Table`은 `Type = "DB"`일 때만, `File_path`는 DB가 아닐 때만, `Format`은 `Type = "Folder"`일 때만 보입니다.

### 예측 Type = CSV

```toml
[Prediction]
Type = "CSV"
File_path = "inference.csv"
Predict = "classification"
Predict_score = "AD_score"
```

- **결과 파일 찾기:** `File_path`는 `[Path] Results/<task>/` 아래에서 찾는 파일 이름이나 glob입니다. Results에
  task 폴더가 없으면 `[Path] Results` 전체에서 찾습니다. 절대 경로도 됩니다.
  - 일치하는 파일마다 하나의 소스가 됩니다. 예를 들어 모델 폴더마다 `inference.csv`가 하나씩 있으면,
    뷰어 머리글에 **Results** 드롭다운이 생겨 모델을 고를 수 있습니다.
- **데이터와 매칭:** 결과 파일의 경로 열(위 [열 찾기](#열-찾기)와 같은 이름)로 데이터 파일과 맞춥니다.
  전체 경로가 다르면 파일 이름으로 맞춥니다.
- **열이 없을 때:** `Predict` / `Predict_score`에 적은 열이 없으면 `… no column …` 알림이 뜨고 그 칩은 `—`로
  나옵니다.

### 예측 Type = DB

```toml
[Prediction]
Type = "DB"
Table = "semiconductor"
Predict = "predict"
Predict_score = "AD_score"
```

- **접속:** `[DB]` 접속 정보와 `[Project] DB = True`가 필요합니다. `[Data]`와 같은 테이블이면 한 번만 조회합니다.
- **데이터와 매칭:** 테이블의 파일 경로 열로 데이터 파일과 맞춥니다.

### 예측 Type = Folder

```toml
[Prediction]
Type = "Folder"
File_path = "/mnt/data/predictions"
Format = "txt"
```

- **예측 파일 위치:** 데이터 파일마다 예측 파일 하나를 둡니다. 다음 순서로 찾습니다.
  1. `File_path` 아래, 데이터 폴더 안에서와 **같은 위치·같은 이름**의 파일
     (`test/Normal/x.jpg` → `test/Normal/x.txt`)
  2. 없으면 `File_path` 아래 어디서든 **같은 파일 이름**(확장자 제외)
- **`Format = "txt"`:** 첫 줄에 `<클래스> [점수]`를 씁니다. 공백이나 쉼표로 구분합니다.

  ```text
  Normal 0.93
  ```

- **`Format = "json"`:** 객체 하나, 또는 객체 목록의 첫 번째 객체를 읽습니다.

  ```json
  {"class": "Normal", "score": 0.93}
  ```

  - `Predict` / `Predict_score`에 key 이름을 적을 수 있습니다.
  - 비우면 클래스는 `predict`, `prediction`, `class`, `label`, `pred`, 점수는 `predict_score`, `score`,
    `confidence`, `prob`, `probability` 중 처음 있는 key를 씁니다.
- **파일이 없을 때:** 예측 파일이 하나도 없으면 `[Prediction] no .txt files under …` 알림이 뜹니다.

## 자주 보는 알림

상태 바와 Setting의 Detected에 나오는 알림과 해결 방법입니다.

| 알림 | 원인 / 해결 |
| --- | --- |
| `[Data] Type is not set` | `[Data] Type`을 `DB` / `CSV` / `Folder` 중 하나로 정합니다 |
| `[Data] Type = DB, but [Project] DB = False` | `[Project] DB`를 `True`로 바꿉니다 |
| `DB … unavailable (…)` | DB에 접속할 수 없음. `[DB] DB_ip`, DB 서버 실행 여부, 테이블 이름을 확인합니다 |
| `[Data] File_path … is not a file` | CSV 경로가 틀림. 파일 경로를 다시 고릅니다 |
| `… no file-path column found` | 경로 열을 못 찾음. `[Data] Raw`에 열 이름을 적습니다 |
| `[Label] <Task>_Label: no column …` | 라벨 csv·테이블에 그 열이 없음. 열 이름을 확인합니다 |
| `[Label] <Task>_Label: no folder …` / `no label files in …` | Folder 라벨 폴더가 없거나 비어 있음 |
| `[Label] no <Task>_Label: …` | 그 task의 `<Task>_Label`을 적지 않음 |
| `[Project] Task: unknown task …` | 쓸 수 없는 task 이름. 위 [Task](#task-단일--다중)의 이름을 씁니다 |
| `[Prediction] … no column …` | `Predict` / `Predict_score`에 적은 열이 결과에 없음 |
| `[Prediction] no .txt files under …` | 예측 폴더에 예측 파일이 없음. `File_path`와 `Format`을 확인합니다 |
| `[Prediction] <task> File_path … not found under Path.Results/<task>` | 그 task의 결과 폴더에 결과 파일이 없음 |
| `No data rows found` | 위 문제로 데이터를 하나도 읽지 못함 |

## 이전 형식 (Task가 비어 있을 때)

`[Project] Task`가 비어 있으면 이전 형식으로 읽습니다.
아래 출처 중 처음으로 동작하는 것을 사용합니다.

1. **데이터베이스 테이블:** `[DB] Table`. 접속할 수 없으면 상태 바에 알리고 다음 출처로 넘어갑니다.
   `[Path] Data = "DB"`처럼 섹션 이름을 적으면 그 DB만 읽습니다.
2. **테이블 파일:** `[Path] Data`가 가리키는 csv / tsv / jsonl / parquet 파일이나 그 폴더 안의 테이블 파일.
   폴더에서 자동으로 찾은 파일은 경로 열이 실제 파일을 가리켜야 합니다.
3. **폴더 스캔:** `[Path] Data` 폴더를 위 [Type = Folder](#type--folder)와 같은 방식으로 읽습니다.

- **예측:** `[Labels]` 섹션(`Result_file` 등)에서 가져옵니다.
- **`[Labels]`가 없을 때:** 데이터 자체의 `predict` 열을 예측으로 씁니다.

## 왼쪽 사이드바

### Folders 카드

데이터 폴더와 각 폴더의 파일 수를 보여 줍니다. 폴더를 클릭하면 그 폴더가 열리고 첫 번째 파일이
선택됩니다. 폴더가 9개를 넘으면 목록이 스크롤됩니다.

### Files 목록

- **All / Train / Valid / Test**로 목록, 뷰어, 썸네일을 한 split으로 좁힙니다.
- 각 행에는 split 색 점, 확장자, 파일 이름, split 이름이 표시됩니다.
- 위쪽 개수는 `120 of 3,400 · cat/`처럼 표시됩니다.

## 뷰어 (가운데)

### 머리글

- 파일 이름과 split.
- **Raw / Predict / Both**로 뷰어에 보일 내용을 고릅니다.
  - **Raw:** 파일과 레이블.
  - **Predict:** 파일과 예측 칩(아래 참고).
  - **Both:** Raw와 Predict를 나란히.
- **Task** 드롭다운. task가 여럿일 때만 나타납니다. 고른 task의 정답과 예측을 보여 줍니다.
- **Results** 드롭다운. 예측 결과 파일이 여러 개일 때만 나타납니다(`[Prediction] Type = "CSV"`의 `File_path`와
  일치하는 파일이 여럿, 예: 모델마다 `inference.csv`가 하나씩). 예측을 어느 결과 파일에서 가져올지 고릅니다.

### 이미지

이미지(png, jpg, jpeg, bmp, gif, webp, tif, tiff)만 그려지고, 다른 형식은 줄무늬 자리 표시로 나옵니다.

| 동작 | 효과 |
| --- | --- |
| 스크롤 | 커서 위치를 중심으로 확대/축소 (맞춤 크기의 최대 40배) |
| Shift+스크롤 또는 드래그 | 이동 |
| 더블클릭 | 이미지를 창에 맞춤 |
| **Reset** | 모든 창을 맞춤 크기·가운데로 |

**Both**에서는 각 창이 확대/축소와 위치를 따로 가집니다. 확대 상태는 다른 파일을 볼 때까지 유지됩니다.

### 이동

- `12 of 3,400`은 폴더 안에서 현재 위치입니다.
- **Previous / Next**는 현재 split 필터 안에서 이동하며, 끝에 닿으면 처음으로 돌아갑니다.
- 썸네일 줄에는 현재 파일 양쪽으로 최대 30개씩 보입니다. 썸네일마다 파일 이름의 마지막 6글자와 split
  점이 붙습니다. 클릭하면 그 파일을 봅니다.

### 예측 색상

레이블은 항상 데이터 자체의 정답입니다 (`label` 열, 폴더 스캔이면 폴더 이름).

예측은 `[Prediction]`에서 가져옵니다(이전 형식이면 `[Labels]`). 행은 경로로, 경로가 다르면 파일 이름으로
매칭합니다. 예측 상자에 `Predict`와 `Predict_score`가 한 줄씩 나오고(`predict : Normal`, `predict_score : 7.80`),
줄마다 아래 색의 점이 붙습니다.

| 표시 | 의미 |
| --- | --- |
| 초록 점 | 값이 레이블과 같음 |
| 빨간 점 | 값이 다른 클래스 |
| 점 없음 | 그 외 (점수, 텍스트 등) |
| `—` | 값이 비어 있음 |

예측 출처에 그 파일이 없으면 칩에 `not in <출처>`라고 나옵니다. 예측 설정이 없거나 읽지 못했으면 칩에
`none · predict column is empty`라고 나옵니다.

## 오른쪽 패널

### Data splits

- 출처와 `3,400 rows from <위치> · root <폴더>` 같은 설명.
- split 비율 누적 막대.
- split마다 한 행: 개수, 비율, split을 어떻게 정했는지. 예:
  - `type = 'train'` (split 열에서)
  - `split from folder name` (폴더 스캔에서)
  - `no split column`
- split 행을 클릭하면 그 split만 보입니다(사이드바 버튼과 같은 기능). 다시 클릭하면 모든 split을 봅니다.
- **Overlap check (file name):** *No overlap*, 또는 같은 파일 이름이 여러 split에 있으면 *3 shared*
  같은 경고.

### File info

항상 표시되는 행:

| 행 | 내용 |
| --- | --- |
| Path | 파일 전체 경로 |
| Split | 파일의 split |
| Dimensions | 이미지 너비 × 높이 |
| Format | 확장자 |
| Label | 파일의 정답. task가 여럿이면 `Label · <task>`로 task마다 한 행 |
| Size | 파일 크기. 디스크에 파일이 없으면 `missing` |
| Modified | 파일 수정 시각 |

출처에 해당 데이터가 있을 때만 나오는 행:

| 행 | 나오는 조건 |
| --- | --- |
| Created | 데이터에 생성일 성격의 열이 있을 때 |
| Trained | 데이터에 `trained`/`used` 열이 있을 때 |
| Row | 데이터베이스에서 읽었을 때. 행의 `id` |

예측이 있으면 `predict · classification`처럼 `key · 열` 형태의 행과, 값을 가져온 **Result file**도 표시됩니다
(그 출처에 행이 없으면 `no row`).

### Folder summary

- 현재 폴더의 **Files**(파일 수)와 **Size**(크기).
- 폴더를 읽은 출처.
- 그 파일들이 디스크에서 몇 개의 디렉터리에 나뉘어 있는지.
