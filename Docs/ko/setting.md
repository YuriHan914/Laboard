# Setting

<p align="center">
  <img src="../assets/LABOARD_SETTING.png" alt="Setting" width="900"/>
</p>



[English](../en/setting.md) | **한국어**

Setting 페이지에서 할 수 있는 일:

- 프로젝트 파일 로드, 또는 새로 만들기(**New**)
- 파일의 값을 하나씩 수정하고, 결과를 새 파일로 저장
- 파일이 가리키는 각 위치에서 Laboard가 무엇을 찾았는지 확인
- 테마 전환
- Result·Hyperparameter 표의 페이지당 행 수 변경

프로젝트 없이 실행하면 이 페이지에서 시작합니다.

## Load project file

1. `.toml` 파일 경로를 입력하거나, **Browse**로 파일을 고릅니다. Browse는 경로만 채웁니다.
2. **Load**를 누르거나 Enter를 누르면 로드됩니다.

**New**를 누르면 모든 섹션을 입력하는 **Create project file** 창이 열립니다.

- **Sections**(왼쪽): Project, DB, Git, Path, Data, Label, Prediction, Cloud(접속: Google Cloud - gcloud, Azure - az,
  AWS - aws, SSH - ssh)와 각각의 key 수. 켜진 섹션이 없는 그룹은 흐리게 보입니다.
- **켜기 / 끄기:** Project는 `required`이고 항상 저장합니다. 나머지 섹션은 이름 옆에 Setting의 Light / Dark 같은
  **False / True** 스위치가 있습니다. True면 파일에 쓰고, False면 흐려지고 파일에서 빠집니다(입력한 값은 남아 있음).
  처음에는 Git, Path, Data, Label, Prediction이 True, 접속 섹션이 False입니다. DB 스위치는 `[Project] DB`와 같은
  값입니다.
- **key**(오른쪽): 넣을 값 설명과 예시가 함께 나오고, 접속에 꼭 필요한 key에는 `required`가 붙습니다. Task는 칩으로
  고르고(여러 개 가능, 쉼표로 저장), DB는 False / True, 각 Type은 CSV / DB로 고릅니다.
- **Save to:** 저장할 위치(상대 경로는 지금 로드된 프로젝트 폴더 기준). 처음에는 그 폴더의 `laboard.toml`이고, 이미
  있으면 `laboard_2.toml`, … 입니다.
- **Create and load**는 [Project]와 켜진 섹션만 toml에 저장하고 바로 로드합니다. 켜진 섹션의 `required` key가 비어
  있거나 파일이 이미 있으면 저장하지 않고 Save to 아래에 안내가 나옵니다(덮어쓰지 않음). **Cancel**, **×**, Esc로
  닫으면 아무것도 저장하지 않습니다.

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
  - 목록은 고정입니다: 저장소 루트 `template.toml`의 `[Project]` … `[Prediction]` key를 같은 순서로, 로드한 파일과
    상관없이 보여 줍니다. 파일에 없거나 비어 있는 key는 빈칸으로 나오고, 파일에만 있는 다른 key와 섹션(`[gcloud]`,
    `[ssh]` 같은 접속 섹션 등)은 그 뒤에 나옵니다.
    `[DB]` 섹션은 `[Project] DB`가 True일 때만 보입니다. `Table`은 `Type = "DB"`일 때만 보입니다.
  - key나 값에 마우스를 올리면 어떤 값을 넣어야 하는지 설명이 나오고, Edit 팝업에도 같은 설명이 표시됩니다.
    이 설명은 Laboard에 고정되어 있으며 파일 내용과 무관합니다.
  - 적용한 값은 현재 세션에만 반영되고 디스크의 toml 파일은 바뀌지 않습니다. 머리글에 *Edited*가 표시되며,
    **Load**를 누르면 파일을 다시 읽어 수정 내용이 사라집니다.
  - **Save Changed**(수정한 뒤에 나타남)는 수정된 프로젝트를 새 toml 파일(기본 `<이름>_edited.toml`)로 저장하고
    그 파일을 로드합니다. 로드된 원래 파일에는 덮어쓰지 않습니다.
  - `[Project] DB`와 `[Data]` / `[Label]` / `[Prediction]`의 `Type`은 드롭다운입니다(`True` / `False`,
    `CSV` / `DB`). 빈 항목을 고르면 그 key를 지웁니다.
  - 나머지 값은 직접 입력합니다. 경로 값은 입력창 안의 폴더 아이콘으로 파일이나 폴더를 고를 수 있습니다:
    `Type = "CSV"`면 파일, `[Path]`는 폴더.
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

## Items per page

Result 페이지의 표(csv / tsv / jsonl)와 Hyperparameter 페이지의 설정 표가 한 페이지에 보여 줄 행 수를
**20 / 30 / 40 / 50 / 100** 중에서 고릅니다. 기본값은 30입니다. 고른 값은 바로 적용되고, 탭을 옮기거나 프로젝트를 다시 로드해도, Laboard를 다시 시작해도
유지됩니다(사용자 설정에 저장. Linux에서는 `~/.config/Laboard/Laboard.conf`).

## 왼쪽 사이드바

**Recent projects**에는 지금 로드된 프로젝트가 나옵니다.

## 프로젝트 파일 작성법

프로젝트 파일은 toml 형식입니다. Setting의 **New**([Load project file](#load-project-file))로 만들거나, 저장소 루트의
[`template.toml`](../../template.toml)을 복사해서 시작합니다(`cp template.toml my_project.toml`). 템플릿에는 모든 key가
빈 값으로, 또는 바꿔 쓸 예시 값(`Task`, 접속 섹션)으로 들어 있습니다. 쓰지 않는 접속 섹션은 지우세요. Setting의
**Fields**에서도 같은 key를 같은 순서로 보여 주고 고칠 수 있습니다.

- **이름 규칙:** 섹션과 key 이름은 첫 글자를 대문자로 씁니다(`DB`는 전부 대문자, 경로 섹션은 `[Path]`).
  대소문자를 구분하지 않으므로 `[paths]`도 `[Path]`와 같습니다.
- **경로:** 절대 경로, 또는 toml 파일이 있는 폴더 기준의 상대 경로입니다.
- **빈 값:** 쓰지 않는 key는 `""`로 비워 둡니다. 비어 있는 key는 설정하지 않은 것으로 봅니다.
- **True / False:** Laboard는 `True` / `False`를 씁니다. 표준 TOML의 `true` / `false`도 읽습니다.
- **원격 경로:** 모든 경로는 `<host>:<경로>`로 써서 다른 컴퓨터에 둘 수 있습니다([원격 서버의 파일](#원격-서버의-파일)).

### 전체 예시

```toml
[Project]
Name = "wafer-defect"              # 비우면 Root 폴더 이름
Root = "/path/to/repo"             # 프로젝트의 git 저장소
Task = "classification, object detection"   # task 하나, 또는 쉼표로 여러 개
DB = False                         # [Data] / [Label] / [Prediction]에서 Type = "DB"를 쓰면 True

[DB]                               # DB = True일 때만 사용 (Setting에서도 그때만 보임)
DB = "supabase"
DB_ip = "http://127.0.0.1:54322/"
# DB_ip = "postgresql://user:pw@host:5432/db"                 # PostgreSQL
# DB_ip = "mysql://user:pw@host:3306/db"                      # MySQL (MariaDB: mariadb://…)
# DB_ip = "sqlite:///data.db"                                 # SQLite (toml 기준 상대 경로)
# DB_ip = "mssql://user:pw@host:1433/db"                      # MSSQL
# DB_ip = "oracle://user:pw@host:1521/?service_name=XEPDB1"   # Oracle

[Git]                              # git으로 알 수 없을 때만 쓰는 대체값
Remote = "github.com:user/repo.git"
Branch = "main"

[Path]                             # task별 폴더로 나눌 수 있음. 예: Results/classification/<model>/
Models = "/path/to/repo/Models"
Hyperparameter = "/path/to/repo/Runs"
Results = "/path/to/repo/Results"

[Data]                             # 원본 데이터 파일 목록: 모든 task가 같이 씀
Type = "CSV"                       # CSV | DB
File_path = "data.csv"             # CSV: 파일 목록 csv
Table = ""                         # DB: 파일 하나당 한 행인 테이블
Raw = "file_path"                  # 원본 파일 경로 열

[Label]                            # 정답
Type = "CSV"                       # CSV | DB
File_path = ""                     # 비우면 [Data] csv
Table = ""                         # 비우면 [Data] 테이블
Label = "label"                    # 정답 열. task 열이 있으면 task마다 자기 행을 씀

[Prediction]                       # <Task>_<Key>로 task 하나만 다르게 설정 가능. 예: Object_detection_Predict
Type = "CSV"                       # CSV | DB
File_path = "inference.csv"        # Path.Results/<task>/ 아래에서 찾음
Table = ""                         # DB: 예측 테이블
Predict = "predict"
Predict_score = "score"
```

### 섹션별 key

**`[Project]`**

| key | 필요 | 넣을 값 | 예시 |
| --- | --- | --- | --- |
| `Name` | 선택 | 상단 바와 Home에 표시할 프로젝트 이름. 비우면 `Root` 폴더 이름 | `"wafer-defect"` |
| `Root` | 선택 | 프로젝트의 git 저장소 폴더. Laboard에 표시되는 git 기록, 브랜치, remote를 여기서 읽습니다. 비우면 설정한 경로들에서 추측하거나, toml이 있는 폴더 | `"/path/to/repo"` |
| `Task` | **필수** | task 하나, 또는 쉼표로 구분한 여러 개: `classification`, `object detection`(`detection`), `instance segmentation`, `semantic segmentation`, `panoptic segmentation`, `anomaly detection`, `pose-estimation`(`keypoints`). 대소문자·공백·`_`·`-`는 무관. 비우면 [이전 형식](#이전-형식) | `"classification, object detection"` |
| `DB` | `Type = "DB"`일 때 | `[Data]`, `[Label]`, `[Prediction]` 중 하나라도 `Type = "DB"`이면 `True`. `False`면 DB를 읽지 않음 | `True` |

**`[DB]`**: 데이터베이스 접속 정보입니다. `[Project] DB = True`일 때만 쓰고, Setting에도 그때만 보입니다.
지원하는 DB: Supabase, PostgreSQL, MySQL, MariaDB, SQLite, MSSQL, Oracle. SQLite를 뺀 나머지는 드라이버를 설치해야 합니다: `pip install ".[postgres]"`(PostgreSQL·Supabase), `".[mysql]"`(MySQL·MariaDB), `".[mssql]"`, `".[oracle]"`.

| key | 필요 | 넣을 값 | 예시 |
| --- | --- | --- | --- |
| `DB` | DB 사용 시 | 데이터베이스 종류(표시용): `supabase`, `postgresql`, `mysql`, `mariadb`, `sqlite`, `mssql`, `oracle` | `"supabase"` |
| `DB_ip` | DB 사용 시 | 데이터베이스 주소. Supabase URL(그 호스트의 Postgres 54322 포트를 씀) 또는 DB URL([DB 주소](data.md#type--db)) | `"http://127.0.0.1:54323/"`, `"mysql://user:pw@host:3306/db"`, `"sqlite:///data.db"` |
| `Port`, `User`, `Password`, `Database` | 선택 | 템플릿에는 없습니다. Supabase URL일 때 기본값이 맞지 않으면 추가합니다. 기본값은 54322 / `postgres` / `postgres` / `postgres` | `Port = 5432` |
| `Limit` | 선택 | 테이블에서 읽을 최대 행 수. 기본값 200,000 | `Limit = 500000` |

**`[Git]`**: git으로 알 수 없을 때만 씁니다.

| key | 필요 | 넣을 값 | 예시 |
| --- | --- | --- | --- |
| `Remote` | 선택 | 저장소에 `origin` remote가 없을 때 표시할 remote | `"github.com:user/repo.git"` |
| `Branch` | 선택 | `HEAD`가 detached이거나 `Root`가 git 저장소가 아닐 때 표시할 브랜치 | `"main"` |

**`[Path]`**: 각 폴더 안을 task별 하위 폴더로 나눌 수 있습니다. 예: `Models/classification/<모델>/`.

| key | 필요 | 넣을 값 | 표시하는 탭 |
| --- | --- | --- | --- |
| `Models` | 선택 | 모델 체크포인트(`.pt`, `.pth`, `.onnx`, `.safetensors`, `.ckpt` 등) 폴더. 하위 폴더 포함 | [Model](model.md) |
| `Hyperparameter` | 선택 | 학습 run마다 하위 폴더가 하나씩 있는 폴더. 각 하위 폴더에 json / yaml / toml 설정(과 `trainer_state.json`) | [Hyperparameter](hyperparameter.md) |
| `Results` | 선택 | 결과 파일(csv, 로그, 이미지, TensorBoard 이벤트) 폴더. `[Prediction] Type = "CSV"`는 여기서(`Results/<task>/`) 파일을 찾음 | [Result](result.md) |

**`[Data]`**: 원본 데이터 파일 목록입니다. 모든 task가 이 목록 하나를 같이 씁니다([데이터 설정](data.md#데이터-설정)).

| key | `CSV` | `DB` | 넣을 값 | 예시 |
| --- | --- | --- | --- | --- |
| `Type` | 필수 | 필수 | 목록을 가져올 곳: `CSV` 또는 `DB` | `"CSV"` |
| `File_path` | 필수 | – | 원본 파일 하나당 한 행인 csv(또는 tsv / jsonl / parquet) | `"data.csv"` |
| `Table` | – | 필수 | 원본 파일 하나당 한 행인 테이블. `table` 또는 `schema.table` | `"semiconductor"` |
| `Raw` | 선택 | 선택 | 원본 파일 경로가 든 열. 비우면 `file_path`, `data_path`, `path`, `image`, `filename` 등에서 추측 | `"file_path"` |

**`[Label]`**: 정답입니다. 파일 경로 열로 데이터 파일과 맞춥니다([라벨 설정](data.md#라벨-설정-label)).

| key | `CSV` | `DB` | 넣을 값 | 예시 |
| --- | --- | --- | --- | --- |
| `Type` | 필수 | 필수 | 라벨이 있는 곳: `CSV` 또는 `DB` | `"CSV"` |
| `File_path` | 선택 | – | 라벨 csv. 비우면 `[Data]` csv | `"labels.csv"` |
| `Table` | – | 선택 | 라벨 테이블. 비우면 `[Data]` 테이블 | `"semiconductor"` |
| `Label` | 라벨 표시 시 | 라벨 표시 시 | 모든 task가 같이 쓰는 정답 열. 파일 하나가 task마다 한 행인 테이블(`task` 열이 있음)이면 각 task는 자기 행의 라벨을 씀 | `"label"` |

`Label`이 없으면 정답이 비어 있습니다.

**`[Prediction]`**: 모델 예측입니다. 모든 key는 `<Task>_<Key>`로 task 하나에만 따로 지정할 수 있습니다. 예:
`Instance_segmentation_Predict`([예측 설정](data.md#예측-설정-prediction)).

| key | `CSV` | `DB` | 넣을 값 | 예시 |
| --- | --- | --- | --- | --- |
| `Type` | 필수 | 필수 | 예측이 있는 곳: `CSV` 또는 `DB` | `"CSV"` |
| `File_path` | 필수 | – | `[Path] Results/<task>/` 아래에서 찾을 결과 파일 이름이나 glob(task 폴더가 없으면 `Results` 전체), 또는 절대 경로. 찾은 파일마다 Data 페이지에서 고를 수 있는 소스가 하나씩 생김 | `"inference.csv"` |
| `Table` | – | 필수 | 예측이 들어 있는 테이블 | `"semiconductor"` |
| `Predict` | 필수 | 필수 | 예측 클래스 열 | `"predict"` |
| `Predict_score` | 선택 | 선택 | 점수 열 | `"score"` |

### 원격 서버의 파일

경로를 `<host>:<경로>`로 쓰면 다른 컴퓨터에서 읽습니다. 모든 경로에 쓸 수 있습니다.

- `[Path]` 폴더. 예: `Hyperparameter = "gcloud:~/laboard/Runs"`
- `[Data]` / `[Label]` / `[Prediction]`의 `File_path`. 예: `File_path = "ssh:~/wafer/data.csv"`
- csv나 DB 테이블의 파일 경로 열. 예: `ssh:/data/wafer/train/Normal/0001.jpg`

`ssh:/…`는 서버의 절대 경로, `ssh:~/…`는 접속한 사용자의 홈 폴더 아래 경로입니다. Laboard는 서버에 접속해 읽기만
하고, 서버의 파일은 바꾸지 않습니다.

**예시 csv** (프로젝트 파일 옆의 `data.csv`):

```csv
file_path,type,label
ssh:/data/wafer/train/Normal/0001.jpg,train,Normal
ssh:~/wafer/valid/Scratch/0102.jpg,valid,Scratch
ssh:~/wafer/test/Donut/0203.jpg,test,Donut
```

**예시 프로젝트 파일** (`my_project.toml`, 접속 정보도 이 파일에 적음):

```toml
[Data]
Type = "CSV"
File_path = "data.csv"
Raw = "file_path"

[ssh]                    # 접속 명령: ssh -i ~/.ssh/my-key ubuntu@1.2.3.4
key_name = "my-key"      # ~/.ssh 아래 키 이름. "/"가 들어 있으면 그 경로를 그대로 씀
user_name = "ubuntu"
ip = "1.2.3.4"
```

**무엇을 언제 읽는지**

| 경로 | 불러올 때마다 | 그 뒤 |
| --- | --- | --- |
| `[Path] Models` | 임시 폴더로 복사: 500 MB 미만 파일 | – |
| `[Path] Hyperparameter` | 복사: 설정 파일만(2 MB 미만 json / yaml / toml) | – |
| `[Path] Results` | 복사: 50 MB 미만 파일 | – |
| `[Data]` / `[Label]` / `[Prediction]` `File_path` | 복사: 그 파일(50 MB 미만). 원격 csv 안의 상대 경로는 서버에서 csv가 있는 폴더 기준으로 읽음 | – |
| csv / 테이블에 적힌 데이터 파일 | 크기와 시간만. 서버마다 ssh 호출 한 번 | Data 페이지가 보여 주는 파일과 썸네일을 그때 가져오고, Laboard를 끌 때까지 보관 |

[예전 커밋](../../README.ko.md#예전-커밋-보기)을 볼 때는 원격 `[Path]` 폴더가 비어 있습니다. 원격 폴더에는 git 기록이 없기
때문입니다.

**접속 방법: 프로젝트 파일의 접속 섹션**

콜론 앞부분이 프로젝트 파일 안의 섹션 이름을 가리킵니다. Setting에서 값을 고쳤다면 고친 값으로 접속합니다.

| 앞부분 | 섹션 | 접속 방식 | key |
| --- | --- | --- | --- |
| `ssh:` | `[ssh]` | `ssh -i ~/.ssh/<key_name> <user_name>@<ip>` | `key_name`, `user_name`, `ip`(필수) |
| `gcloud:` | `[gcloud]` | `gcloud compute ssh <instance_name> --zone <zone>` | `instance_name`(필수), `zone` |
| `az:` | `[az]` | `az ssh vm --name <vm_name> --resource-group <resource-group>` | `vm_name`, `resource-group` |
| `aws:` | `[aws]` | `aws ec2-instance-connect send-ssh-public-key`로 공개 키를 보낸 뒤 `ssh -i <개인 키> <instance-os-user>@<공인 IP>` | `instance-id`, `instance-os-user`, `ssh-public-key`(필수), `availability-zone` |
| `abc:` | `[abc]` | `type` key에 적은 방식 | 그 방식의 key |

```toml
[gcloud]                        # gcloud compute ssh my-vm --zone us-west1-b
instance_name = "my-vm"
zone = "us-west1-b"

[az]                            # az ssh vm --name my-vm --resource-group my-rg
vm_name = "my-vm"
resource-group = "my-rg"

[aws]                           # 공개 키를 보낸 뒤 ssh -i ~/.ssh/my-key ec2-user@<공인 IP>
instance-id = "i-0123456789abcdef0"
instance-os-user = "ec2-user"
ssh-public-key = "~/.ssh/my-key.pub"
availability-zone = "us-east-1a"

[ssh]                           # ssh -i ~/.ssh/my-key ubuntu@1.2.3.4
key_name = "my-key"
user_name = "ubuntu"
ip = "1.2.3.4"

[train-vm]                      # train-vm:… 경로용. type으로 접속 방법 지정
type = "gcloud"
instance_name = "train-vm"
zone = "asia-northeast3-a"
```

- **종류:** 섹션의 `type` key, 없으면 섹션 이름: `gcloud`, `az`, `aws`, `ssh`. 어느 섹션이든 key 대신
  `command = "ssh -i ~/.ssh/my-key ubuntu@1.2.3.4"`처럼 접속 명령을 적으면 그 명령 그대로 접속합니다.
- **그 밖의 key:** gcloud / az / aws 섹션의 다른 key는 `--key value`로 넘깁니다(`true`면 값 없는 flag). 예:
  `project = "my-gcp-project"`, `tunnel-through-iap = true`. key 이름의 `_`와 `-`는 같습니다.
- **gcloud:** 처음 한 번 gcloud를 `--dry-run`으로 실행해 gcloud가 쓰는 ssh 명령을 얻습니다. 그다음부터는 그 ssh를
  연결 하나로 공유해 직접 실행하므로, gcloud의 몇 초 대신 밀리초 단위로 끝납니다.
- **aws:** 개인 키는 `ssh-public-key`에서 `.pub`를 뺀 파일(또는 `private-key`), 주소는 인스턴스의 공인 IP(또는
  `host`)입니다. 보낸 키는 60초 동안 유효하고, 접속에 실패하면 다시 보냅니다.
- **비밀번호 없이 접속:** 비밀번호를 묻지 않고 접속되어야 합니다. passphrase 없는 키나 `ssh-agent`에 올린 키를
  쓰고, 서버 host key가 등록되도록 한 번은 직접 접속해 두세요.
- **실패하면:** 상태 바에 이유가 나옵니다. 예: `the project file has no [ssh] section`,
  `[ssh] in the project file: no ip`. 데이터 파일 목록은 그대로 보이고, Detected에
  *Remote data files · Unreachable*이 표시됩니다.
- **접속 정보가 든 프로젝트 파일은 공개 저장소에 올리지 마세요.** IP, 사용자 이름, 인스턴스 이름이 들어 있습니다.

### 섹션을 쓰는 곳

| 섹션 | 사용하는 곳 |
| --- | --- |
| `[Project]`, `[Git]` | 상단 바, Home, git log 팝업 |
| `[Data]`, `[DB]` | [Data](data.md), Home의 Data 카드 |
| `[Label]` | [Data](data.md) 페이지의 정답 표시, 클래스 목록 |
| `[Prediction]` | [Data](data.md) 페이지의 예측 표시 |
| `[Path] Models` | [Model](model.md), Home의 Model 카드 |
| `[Path] Hyperparameter` | [Hyperparameter](hyperparameter.md), Home의 Latest hyperparameter 카드 |
| `[Path] Results` | [Result](result.md), Home의 Result 카드 |
| `[gcloud]`, `[az]`, `[aws]`, `[ssh]` (또는 다른 이름) | `host:path` 값의 원격 접속 ([원격 서버의 파일](#원격-서버의-파일)) |

찾지 못한 부분은 비어 있고, 어느 부분이 그런지는 Detected 카드와 상태 바에서 확인할 수 있습니다.

### 이전 형식

`Task`가 비어 있으면 이전 형식으로 읽습니다. 데이터 위치는 `[Path] Data`로,
예측은 `[Labels]`로 정합니다. 자세한 읽기 순서는 [Data 문서의 이전 형식](data.md#이전-형식-task가-비어-있을-때)을
보세요.

```toml
[Path]
Data = "/path/to/data.csv"         # 파일 목록(csv / tsv / jsonl / parquet), 또는 "DB" 같은 섹션 이름

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
