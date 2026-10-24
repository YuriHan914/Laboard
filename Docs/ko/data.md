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

Data 페이지에 보일 파일 목록은 프로젝트 파일(toml)의 `[Data]` 섹션이, 각 파일의 모델 예측은
`[Prediction]` 섹션이 정합니다. 이 형식은 `[Project] Task = "classification"`일 때 쓰입니다.
다른 Task는 아래 [이전 형식](#이전-형식-task가-classification이-아닐-때)을 따릅니다.

| `[Data] Type` | 파일 목록을 가져오는 곳 | 정답(레이블) | split |
| --- | --- | --- | --- |
| `DB` | 데이터베이스 테이블 (한 행 = 파일 하나) | `Label` 열 | split 열 (`type`, `status` 등) |
| `CSV` | 파일 목록 csv (한 행 = 파일 하나) | `Label` 열 | split 열 (`type`, `status` 등) |
| `Folder` | 데이터셋 폴더를 스캔 | split 폴더 바로 아래 폴더 이름 | 경로의 split 폴더 이름 |

- **Type 값:** `DB`, `CSV`, `Folder`는 대소문자를 구분하지 않습니다(`csv`도 됨). 비어 있으면 상태 바에
  `[Data] Type is not set`이 뜹니다.
- **읽는 양:** 출처와 상관없이 최대 200,000개 행(파일)까지 읽습니다.
- **정답 출처:** 정답은 항상 데이터에서만 가져옵니다. 예측 결과 파일에 레이블 열이 있어도 정답으로 쓰지 않습니다.

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
  - `Table` 행은 `Type = "DB"`일 때만 보입니다.
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
| `Label` | 선택 | 선택 | – | 정답 열 이름. 비우면 `"label"` |
| `Path` | 선택 | 선택 | – | 파일 경로 열 이름. 비우면 자동으로 찾음 (아래 표) |

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
Label = "label"
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
  | 파일 경로 | 필수 | 데이터 파일의 경로. 이름은 아래 [열 찾기](#열-찾기) 표 참고 (예: `file_path`) |
  | 정답 | 권장 | `[Data] Label`에 적은 열(기본 `label`). 없으면 레이블 없이 표시 |
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
Label = "label"
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
- **경로 열을 못 찾을 때:** `[Data] Path`에 열 이름을 적습니다.

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
- **`[Data] Label`:** 쓰지 않습니다.
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
| 파일 경로 | `[Data] Path`에 적은 열, 없으면 `file_path`, `data_path`, `path`, `filepath`, `file`, `image`, `image_path`, `img`, `filename` |
| 정답 | `[Data] Label`에 적은 열 (기본 `label`) |
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

## 예측 설정 (`[Prediction]`)

예측도 `Type`으로 출처를 정합니다. 데이터와 다른 Type을 써도 됩니다(예: 데이터는 DB, 예측은 CSV).

| key | `CSV` | `DB` | `Folder` | 설명 |
| --- | --- | --- | --- | --- |
| `Type` | 필수 | 필수 | 필수 | `CSV` / `DB` / `Folder` |
| `Path` | 필수 | – | 필수 | CSV: 결과 파일 이름 / glob · Folder: 예측 파일 폴더 |
| `Table` | – | 필수 | – | 예측이 들어 있는 테이블 |
| `Format` | – | – | 선택 | `txt`(기본) / `json` |
| `Predict` | 필수 | 필수 | json에서 선택 | 예측 클래스 열(json이면 key) |
| `Predict_score` | 선택 | 선택 | json에서 선택 | 점수 열(json이면 key) |

Setting에서 `Table`은 `Type = "DB"`일 때만, `Format`은 `Type = "Folder"`일 때만 보입니다.

### 예측 Type = CSV

```toml
[Prediction]
Type = "CSV"
Path = "inference.csv"
Predict = "classification"
Predict_score = "AD_score"
```

- **결과 파일 찾기:** `Path`는 `[Path] Results` 아래에서 찾는 파일 이름이나 glob입니다. 절대 경로도 됩니다.
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
Path = "/mnt/data/predictions"
Format = "txt"
```

- **예측 파일 위치:** 데이터 파일마다 예측 파일 하나를 둡니다. 다음 순서로 찾습니다.
  1. `Path` 아래, 데이터 폴더 안에서와 **같은 위치·같은 이름**의 파일
     (`test/Normal/x.jpg` → `test/Normal/x.txt`)
  2. 없으면 `Path` 아래 어디서든 **같은 파일 이름**(확장자 제외)
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
| `… no file-path column found` | 경로 열을 못 찾음. `[Data] Path`에 열 이름을 적습니다 |
| `… no 'label' column; files have no ground truth` | 정답 열이 없음. `[Data] Label`에 열 이름을 적습니다 |
| `[Prediction] … no column …` | `Predict` / `Predict_score`에 적은 열이 결과에 없음 |
| `[Prediction] no .txt files under …` | 예측 폴더에 예측 파일이 없음. `Path`와 `Format`을 확인합니다 |
| `No data rows found` | 위 문제로 데이터를 하나도 읽지 못함 |

## 이전 형식 (Task가 classification이 아닐 때)

`[Project] Task`가 비어 있거나 `object detection` / `segmentation`이면 이전 형식으로 읽습니다.
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
- **Results** 드롭다운. 예측 결과 파일이 여러 개일 때만 나타납니다(`[Prediction] Type = "CSV"`의 `Path`와
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
| Label | 파일의 레이블 |
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
