<p align="center">
  <img src="../assets/LABOARD_SETTING.png" alt="Setting" width="900"/>
</p>

# Setting

[English](../en/setting.md) | **한국어**

Setting 페이지에서 할 수 있는 일:

- 프로젝트 파일 로드
- 미리보기로 파일 내용 읽기
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

메모의 예: *Nothing found in paths.runs*, *DB … unavailable; using paths.data*

## 미리보기

로드한 파일을 읽기 전용으로 줄 번호와 함께 보여 줍니다. 섹션 머리글(`[project]`, `[paths]` 등)은 굵게 표시됩니다.

## Detected

프로젝트의 각 부분에서 Laboard가 찾은 내용을 상태 배지와 함께 보여 줍니다.

| 행 | 배지 |
| --- | --- |
| Git repository | *Found* (브랜치 · 커밋 수) / *Not found* |
| Snapshot | *Past commit*. 예전 커밋을 볼 때만 표시 |
| Database | *Connected* / *Unreachable* (오류 내용 포함) |
| Data | *Found* (출처 · 파일 수 · 폴더 수 · 크기) / *Not found* |
| Models | *Found* / *Not found* |
| Runs | *Found* / *Not found* |
| Results | *Found* / *Not found* |
| TensorBoard | *Found*. 결과 폴더에 이벤트 파일이 있을 때 |
| Weights & Biases | *Offline*. 결과 폴더에 `offline-run-*` 폴더가 있을 때 |
| Labels / inference | *Found* (결과 파일, 일치한 파일 수, 열) / *Not found* |

## Appearance

**Light / Dark**로 테마가 바로 바뀝니다. 시작할 때의 테마는 `--theme` 옵션으로 정합니다.

## 왼쪽 사이드바

**Recent projects**에는 지금 로드된 프로젝트가 나옵니다.

## 프로젝트 파일 작성법

상대 경로는 toml 파일이 있는 폴더를 기준으로 해석합니다.

```toml
[project]
name = "my-project"                # 기본값: 루트 폴더 이름
root = "/path/to/repo"             # git 기록, 브랜치, 원격 저장소 정보를 여기서 가져옴
                                   # 기본값: paths.* 중 첫 번째, 없으면 toml이 있는 폴더

[paths]                            # 절대 경로, 또는 toml 기준 상대 경로
data = "/path/to/data"
models = "/path/to/models"
runs = "/path/to/runs"
results = "/path/to/results"

[git]                              # 선택 사항. git으로 알 수 없을 때 쓰는 대체값
# branch = "main"                  # HEAD가 detached이거나 root가 git 저장소가 아닐 때
# remote = "github.com/me/repo"    # origin 원격이 없을 때

[db]                               # 선택 사항. 접속 가능하면 paths.data보다 먼저 사용
supabase = "http://127.0.0.1:54323/"   # 로컬 Supabase → 54322 포트의 Postgres에 접속
table = "my_table"                 # 또는 "schema.table"
# dsn = "postgresql://user:pw@host:5432/db"   # Supabase URL 대신 임의의 Postgres 사용
# port / user / password / database / limit   # 덮어쓰기 (기본값: 54322 / postgres / postgres / postgres)
# columns = { path = "file_path", label = "class", split = "type" }

[data]                             # 선택 사항
# table = "index.csv"              # 파일 목록이 담긴 csv / tsv / jsonl / parquet
# columns = { path = "img", label = "cls", split = "subset" }

[models]                           # 선택 사항
# extensions = [".pt", ".onnx"]

[labels]                           # 선택 사항 ([lables]로 써도 읽음)
result_file = "inference.csv"      # paths.results 아래의 이름 / 상대 경로 / glob. 일치하는 파일마다 하나의 소스
infer = "classification"           # 나머지 키는 모두 Data 페이지에 표시할 열
score = "AD_result"
# path = "data_path"               # 행을 데이터 파일과 매칭할 열 (생략하면 추정)
# label = "labels"                 # 레이블 열 (생략하면 추정)
```

| 섹션 | 사용하는 곳 |
| --- | --- |
| `[project]`, `[git]` | 상단 바, Home, git log 팝업 |
| `[paths] data`, `[db]`, `[data]` | [Data](data.md), Home의 Data 카드 |
| `[paths] models`, `[models]` | [Model](model.md), Home의 Model 카드 |
| `[paths] runs` | [Run](run.md), Home의 Latest run 카드 |
| `[paths] results` | [Result](result.md), Home의 Result 카드 |
| `[labels]` | [Data](data.md) 페이지의 레이블과 예측 칩 |

무언가를 보려면 `[paths]`(또는 `[db]`)만 있으면 됩니다. 찾지 못한 부분은 비어 있고, 어느 부분이
그런지는 Detected 카드에서 확인할 수 있습니다.
