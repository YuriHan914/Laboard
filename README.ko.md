# 🧪 Laboard



<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/YuriHan914/Laboard/f8e7266ac86c7b964c78548f822705ff3c4854d6/Docs/assets/LABOARD_LOGO_DARK.png"/>
    <img src="https://raw.githubusercontent.com/YuriHan914/Laboard/f8e7266ac86c7b964c78548f822705ff3c4854d6/Docs/assets/LABOARD_LOGO.png" alt="Laboard" width="136"/>
  </picture>
</p>




<p align="center">
  <a href="https://github.com/YuriHan914/Laboard/blob/master/README.ko.md"><img src="https://img.shields.io/badge/%F0%9F%87%B0%F0%9F%87%B7_%ED%95%9C%EA%B5%AD%EC%96%B4-9fe870?style=for-the-badge" alt="한국어"/></a>
  <a href="https://github.com/YuriHan914/Laboard/blob/master/README.md"><img src="https://img.shields.io/badge/%F0%9F%87%BA%F0%9F%87%B8_English-e8ebe6?style=for-the-badge" alt="English"/></a>
</p>

<p align="center">
  <img src="https://img.shields.io/github/v/release/YuriHan914/EX_Tool?style=for-the-badge&label=Version" alt="Version 1.0.0"/>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+"/></a>
  <a href="https://pypi.org/project/PyQt6/"><img src="https://img.shields.io/badge/PyQt6-6.7%2B-41CD52?style=for-the-badge&logo=qt&logoColor=white" alt="PyQt6 6.7+"/></a>
  <a href="https://www.sqlalchemy.org/"><img src="https://img.shields.io/badge/SQLAlchemy-2.0%2B-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white" alt="SQLAlchemy 2.0+"/></a>
  <a href="https://github.com/lutzroeder/netron"><img src="https://img.shields.io/badge/Netron-8.0%2B-555555?style=for-the-badge" alt="Netron 8.0+"/></a>
  <a href="https://onnx.ai/"><img src="https://img.shields.io/badge/ONNX-1.15%2B-005CED?style=for-the-badge&logo=onnx&logoColor=white" alt="ONNX 1.15+"/></a>
  <a href="https://github.com/YuriHan914/Laboard/blob/master/LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License: MIT"/></a>
</p>



<br></br>

## 📽 Demo Video

<p align="center">
  <a href="https://youtu.be/_dGEJo_bTo4"><img src="https://raw.githubusercontent.com/YuriHan914/Laboard/3d136960ee259e6a69d67411f1d168e5bb002bf2/Docs/assets/laboard_overview.png" alt="Overvieew" width="900"/>
</p>


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
* DB 테이블(Supabase, PostgreSQL, MySQL, MariaDB, SQLite, MSSQL, Oracle)이나 테이블 파일(csv / tsv / jsonl / parquet)에서 데이터 읽기
* 다른 컴퓨터의 파일을 gcloud / az / aws / ssh로 접속해 읽기
* 라이트 / 다크 테마
* 화면의 글자(표 값, 하이퍼파라미터, 설정 값 등)를 마우스로 드래그해 선택하고 Ctrl+C 또는 우클릭 메뉴로 복사

---

## 🛠️ Installation

- Recommend Python 3.11+

1. Git repository에서 직접 다운로드 받기
```bash
git clone https://github.com/YuriHan914/Laboard.git
cd Laboard
pip install -e .                        # DB 없이 (csv / tsv / jsonl 파일, SQLite)
pip install -e ".[postgres]"            # PostgreSQL, Supabase
pip install -e ".[mysql,oracle]"        # 여러 개
pip install -r requirements.txt         # 모든 DB 드라이버 (= pip install -e ".[all]")
```

2. pip install
```bash
pip install laboard                    # DB 없이 (csv / tsv / jsonl 파일, SQLite)
pip install "laboard[postgres]"        # 쓰는 DB의 드라이버를 같이 설치
pip install "laboard[mysql,oracle]"    # 여러 개
pip install "laboard[all]"             # 모든 DB 드라이버 + parquet
```

| extra | DB | 설치되는 드라이버 |
| --- | --- | --- |
| `postgres` | PostgreSQL, Supabase | `psycopg2-binary` |
| `mysql` | MySQL, MariaDB | `PyMySQL` |
| `mssql` | Microsoft SQL Server | `pymssql` |
| `oracle` | Oracle | `oracledb` |
| `sqlite` | SQLite | 없음 (Python 내장) |
| `parquet` | `.parquet` 데이터 파일 | `pandas` |

드라이버 없이 DB를 쓰면 `DB … unavailable` 알림에 `install it with: pip install "laboard[mysql]"`처럼 설치할 extra가 나옵니다.
개발할 때는 `pip install -e ".[all]"`(또는 `pip install -r requirements.txt`)로 설치합니다.

### 원격 파일용 클라우드 CLI (선택)

프로젝트 파일의 경로가 `gcloud:…`, `az:…`, `aws:…`처럼 다른 컴퓨터에 있을 때만 필요합니다
([원격 서버에서 데이터 읽기](#원격-서버에서-데이터-읽기-ssh)). Laboard는 이 명령줄 도구를 실행해서 접속하는데, 이 도구들은
pip로 설치되지 않습니다. 쓰는 CLI를 직접 설치해 `PATH`에 두고, 처음 한 번은 직접 로그인하세요.

| 경로 앞부분 | CLI | 설치 | 처음 한 번 로그인 |
| --- | --- | --- | --- |
| `gcloud:` | Google Cloud CLI | [gcloud CLI 설치](https://docs.cloud.google.com/sdk/docs/install-sdk?hl=ko) | `gcloud auth login` 뒤 `gcloud config set project <project-id>` |
| `az:` | Azure CLI | [Azure CLI 설치](https://learn.microsoft.com/ko-kr/cli/azure/install-azure-cli?view=azure-cli-latest) | `az login` 뒤 `az extension add --name ssh` (`az ssh vm`에 필요) |
| `aws:` | AWS CLI | [AWS CLI 설치](https://docs.aws.amazon.com/ko_kr/cli/latest/userguide/getting-started-install.html) | `aws configure` (또는 `aws configure sso`) |
| `ssh:` | OpenSSH | Linux / macOS / Windows 10 이상에 기본 포함 | – |

- **묻지 않고 접속:** Laboard가 뒤에서 실행하므로 비밀번호를 묻지 않고 접속되어야 합니다. 서버 host key가
  등록되도록 한 번은 직접 접속해 두세요.
- **접속 정보**(인스턴스 이름, zone, 사용자, IP 등)는 프로젝트 파일의 `[gcloud]`, `[az]`, `[aws]`, `[ssh]` 섹션에
  적습니다. 섹션별 key는 [`template.toml`](https://github.com/YuriHan914/Laboard/blob/master/template.toml)에 있습니다.

---

## ▶️ Quick Start

```bash
python -m laboard                             #toml 없이 실행되어 직접 생성 가능
python -m laboard  --project my_project.toml  #입력된 toml로 실행 
```

### 명령줄 옵션

| 옵션 | 효과 |
| --- | --- |
| `--project TOML` | 시작할 때 이 프로젝트 파일을 로드하고 Home에서 시작 |
| `--tab home\|data\|model\|hyperparameter\|result\|setting` | 이 탭에서 시작. 기본값은 `home`, 프로젝트가 없으면 `setting` |
| `--theme light\|dark` | 라이트 또는 다크 테마로 시작 (기본값: light) |
| `--frameless` | 시스템 타이틀 바 대신 Laboard의 어두운 타이틀 바 사용 |
| `--screenshot out.png` | 창을 한 번 그려 PNG로 저장하고 종료. `QT_QPA_PLATFORM=offscreen`이면 화면 없이도 동작 |


### 프로젝트 toml 파일 생성 방법

toml 파일은 필요한 부분한 입력하고 필요없는 부분은 비워두면 됩니다.
1. Laboard를 실행 후 **Setting**에서 **New**를 누르고, 섹션별 입력 창을 채운 뒤 저장
2. 또는 [`template.toml`](https://github.com/YuriHan914/Laboard/blob/master/template.toml)을 복사하여 내용 입력 후 저장
    

    <details>
    <summary>프로젝트 파일 상세 설명</summary>

      <br>

      - 섹션·key 이름은 대소문자를 구분하지 않습니다(`[Path]` = `[paths]`).
      - 경로는 절대 경로, 또는 프로젝트 파일이 있는 폴더 기준 상대 경로입니다.
      - 빈 값(`""`)은 설정하지 않은 것으로 봅니다.
      - 모든 경로는 `<host>:<경로>`로 써서 다른 컴퓨터에 둘 수 있습니다([아래](#원격-서버에서-데이터-읽기-ssh) 참고).

      **`template.toml`** (저장소의 파일 그대로, 주석만 한국어로 옮김. Setting의 **New**는 같은 섹션과 key를 입력 창으로 받습니다):

      Laboard 프로젝트 파일. 원본 데이터([Data])는 모든 task가 하나를 같이 쓰고, task마다 라벨([Label])과 예측([Prediction])을 따로 둡니다. 쓰는 key만 채우고 나머지는 빈 값("")으로 둡니다. 경로는 절대 경로, 또는 이 파일 기준 상대 경로입니다. Setting에서 아래 모든 key와 넣을 값 설명을 볼 수 있습니다. 이름은 대소문자를 구분하지 않습니다.

      | 섹션 | 필수 | key | 값 | 주석 |
      | --- | --- | --- | --- | --- |
      | **`[Project]`** |  |  |  |  |
      |  | 선택 | `Name` | `""` | 프로젝트 이름. 비우면 Root 폴더 이름 |
      |  | 선택 | `Root` | `""` | 프로젝트의 git 저장소 폴더 |
      |  | **필수** | `Task` | `"classification,object detection,..."` | task 하나, 또는 쉼표로 여러 개: classification, object detection, instance segmentation, semantic segmentation, panoptic segmentation, anomaly detection, pose-estimation |
      |  | `Type = "DB"`일 때 | `DB` | `False` | [Data], [Label], [Prediction] 중 하나라도 Type = "DB"이면 True |
      | **`[DB]`** |  |  |  | DB 접속 정보. [Project] DB = True일 때만 보이고 쓰임 |
      |  | DB 사용 시 | `DB` | `""` | supabase |
      |  | DB 사용 시 | `DB_ip` | `""` | 예: "http://127.0.0.1:54323/" 또는 "postgresql://user:password@host:5432/db" |
      | **`[Git]`** |  |  |  | git으로 알 수 없을 때만 쓰는 대체값 |
      |  | 선택 | `Remote` | `""` | 예: "github.com:user/repo.git" |
      |  | 선택 | `Branch` | `""` | 예: "main" |
      | **`[Path]`** |  |  |  | task마다 폴더를 둘 수 있음. 예: Results/classification/&lt;model&gt;/ |
      |  | 선택 | `Models` | `""` | 모델 체크포인트 폴더 |
      |  | 선택 | `Hyperparameter` | `""` | 학습 run마다 하위 폴더가 있는 폴더 |
      |  | 선택 | `Results` | `""` | 결과 파일 폴더 |
      | **`[Data]`** |  |  |  | 원본 데이터 파일. 모든 task가 같은 목록을 씀 |
      |  | 필수 | `Type` | `""` | CSV \| DB |
      |  | CSV: 필수 | `File_path` | `""` | CSV: 파일 목록 csv |
      |  | DB: 필수 | `Table` | `""` | DB: 파일 하나당 한 행인 테이블 |
      |  | 선택 | `Raw` | `""` | CSV / DB: 원본 파일 경로가 든 열. 예: "file_path" |
      | **`[Label]`** |  |  |  | 정답. 모든 task가 열 하나를 같이 씀 |
      |  | 필수 | `Type` | `""` | CSV \| DB |
      |  | CSV: 선택 | `File_path` | `""` | CSV: 라벨 csv |
      |  | DB: 선택 | `Table` | `""` | DB: 라벨 테이블 |
      |  | 라벨 표시 시 | `Label` | `""` | 정답 열. task 열이 있으면 task마다 자기 행을 씀 |
      | **`[Prediction]`** |  |  |  | 모든 key는 &lt;Task&gt;_&lt;Key&gt;로 task 하나만 따로 지정 가능. 예: Instance_segmentation_Predict |
      |  | 필수 | `Type` | `""` | CSV \| DB |
      |  | CSV: 필수 | `File_path` | `""` | CSV: Path.Results/&lt;task&gt; 아래 결과 파일 이름 / glob |
      |  | DB: 필수 | `Table` | `""` | DB: 예측 테이블 |
      |  | 필수 | `Predict` | `""` | 예측 클래스 열 |
      |  | 선택 | `Predict_score` | `""` | 점수 열 |
      | **`[gcloud]`** |  |  |  | gcloud compute ssh &lt;instance_name&gt; --zone &lt;zone&gt; |
      |  | **필수** | `instance_name` | `"instance name"` | 필수: VM 인스턴스 이름 |
      |  | 선택 | `zone` | `"instance zone"` | 예: "us-west1-b" |
      | **`[az]`** |  |  |  | az ssh vm --name &lt;vm_name&gt; --resource-group &lt;resource-group&gt; |
      |  | 선택 | `vm_name` | `"VM name"` | Azure VM 이름 |
      |  | 선택 | `resource-group` | `"resource group"` | 그 VM의 리소스 그룹 |
      | **`[aws]`** |  |  |  | 공개 키를 보낸 뒤(EC2 Instance Connect) ssh -i &lt;개인 키&gt; &lt;user&gt;@&lt;공인 IP&gt; |
      |  | **필수** | `instance-id` | `"instance ID"` | 필수. 예: "i-0123456789abcdef0" |
      |  | **필수** | `instance-os-user` | `"ec2-user"` | 필수: 로그인 사용자. 예: "ec2-user", "ubuntu" |
      |  | **필수** | `ssh-public-key` | `"file://~/.ssh/id_ed25519.pub"` | 필수: 공개 키. 개인 키는 이 파일에서 .pub를 뺀 파일 |
      |  | 선택 | `availability-zone` | `"AZ(zone)"` | 예: "us-east-1a". 이 리전으로 인스턴스의 공인 IP를 찾음 |
      | **`[ssh]`** |  |  |  | ssh -i ~/.ssh/&lt;key_name&gt; &lt;user_name&gt;@&lt;ip&gt; |
      |  | 선택 | `key_name` | `""` | ~/.ssh 아래 키 이름. "/"가 있으면 키 파일 경로 그대로 |
      |  | 선택 | `user_name` | `""` | 로그인 사용자. 비우면 ssh 기본값 |
      |  | **필수** | `ip` | `""` | 필수: 서버 주소(IP 또는 호스트 이름) |


    </details>



### 원격 컴퓨터 파일 접속

- toml 파일에서 아래와 같은 섹션을 입력하면 file을 read할 때 원격 접속 데이터도 사용 가능합니다. 
- 원격 접속: ssh나 cloud 원격 접속을 위한 key 등록은 사용자 사전에 등록해야 합니다. **해당 앱에서는 key 등록은 지원하지 않습니다.**
- 원격 컴퓨터에 있는 파일을 읽어로기 위해서 파일 경로 앞에 `원격 컴퓨터 이름:` 을 추가해야 합니다.

  | 원격 컴퓨터 이름 | 접속 방식 |
  | ------------ | --- |
  | `ssh:` | 위와 같은 ssh |
  | `gcloud:` | gcloud compute ssh |
  | `az:` | az ssh vm |
  | `aws:` | aws ec2-instance-connect |

  - 예시
    - **폴더** : ```"gcloud:/home/Runs"```
    - **파일** : ```"gcloud:/home/img.png" ```

- 기타 접속 방식은 toml 하단에 사용자가 추가하여 사용 가능

  | 앞부분 | 섹션 | 접속 방식 |
  | `abc:` | `[abc]` | 기타 cloud 접속|

  ```toml
  [train-vm]               # train-vm:… 경로용
  type = "ssh"
  key_name = "train-key"
  user_name = "ubuntu"
  ip = "10.0.0.5"
  ```


## 🗂️ Data Format

`[Data] Type = "CSV"` / `"DB"`로 데이터를 읽을 때 csv·테이블에 필요한 열과 라벨 저장 형식입니다.
전체 설명은 [Data · 데이터 형식](https://github.com/YuriHan914/Laboard/blob/master/Docs/ko/data.md#데이터-형식-필수-열과-라벨-format)에 있습니다.

- **파일당 한 행:** 라벨 열 하나를 `Label = "label"`로 지정합니다. task가 하나일 때 씁니다.
- **task당 한 행:** task 열 + 같은 라벨 열 하나를 둡니다. task가 여럿일 때 씁니다. 같은 파일 경로가 여러 행에
  나오면 이 형식으로 읽습니다.


| 열 | 필요 | 값 |
| --- | --- | --- |
| 파일 경로 (`file_path` 등, `[Data] Raw`로 지정) | **필수** | 원본 파일 경로. DB는 절대 경로, CSV는 절대 경로 또는 csv 위치 기준 상대 경로 |
| 라벨 (`[Label] Label`로 지정) | 정답을 보려면 필수 | 아래 라벨 format |
| task (`task` / `object`) | 파일 하나를 task마다 한 행으로 저장할 때 **필수** | `[Project] Task`의 task 이름 |
| split (`type`, `split` 등) | 선택 (권장) | `train` / `valid` / `test` |
| 생성일 (`create_date` 등) | 선택 | `2024-01-05 10:00:00` |



**라벨 format**: 일반 문자열 또는 coco format json. json은 Data 페이지에서 이미지 위에 그립니다.

| task | 형식 |
| --- | --- |
| classification | `cat` 또는 `["cat", "dog"]` |
| object detection | `[{"category": "cat", "bbox": [x, y, w, h]}]` |
| instance segmentation | `[{"category": "cat", "segmentation": [[x1, y1, x2, y2, …]]}]`, 인스턴스마다 객체 하나 (polygon, 또는 RLE `{"counts", "size"}`) |
| semantic segmentation | `[{"category": "cat", "segmentation": [[x1, y1, x2, y2, …], …]]}]`, category마다 객체 하나로 그 영역 전체 (polygon, 또는 RLE `{"counts", "size"}`) |
| pose-estimation | `[{"category": "person", "bbox": [x, y, w, h], "keypoints": [x, y, v, …]}]` |
| panoptic segmentation | `{"mask_path": "<png 절대 경로>", "segments_info": [{"id", "category", "bbox"}]}` |

- instance / semantic segmentation은 형식이 같고 똑같이 그립니다. 객체 하나가 무엇을 덮느냐만 다릅니다.
- 좌표는 이미지 픽셀 기준(원점 왼쪽 위)이고, bbox는 `[x, y, w, h]`입니다.
- 반드시 `json.dumps`로 저장하세요. `str(list)`로 저장한 `['cat']`(작은따옴표)은 json이 아니어서 그리지 않습니다.
- DB 라벨 열은 `JSONB`(권장) 또는 `TEXT`로 만듭니다.

---

## 📚 Documentation

페이지별 상세 설명은 [Docs](https://github.com/YuriHan914/Laboard/tree/master/Docs)에 있습니다.

| 페이지 | 용도 |
| --- | --- |
| [Home](https://github.com/YuriHan914/Laboard/blob/master/Docs/ko/home.md) | 데이터 / 모델 / 최근 run / 결과 요약과 git 기록 |
| [Data](https://github.com/YuriHan914/Laboard/blob/master/Docs/ko/data.md) | 모든 데이터 파일과 split, 레이블을 보고 모델 예측과 비교 |
| [Model](https://github.com/YuriHan914/Laboard/blob/master/Docs/ko/model.md) | 모델 파일의 Netron 그래프, 속성, 레이어별 파라미터 |
| [Hyperparameter](https://github.com/YuriHan914/Laboard/blob/master/Docs/ko/hyperparameter.md) | 학습 run의 진행 상황과 모든 하이퍼파라미터 |
| [Result](https://github.com/YuriHan914/Laboard/blob/master/Docs/ko/result.md) | csv / jsonl / TensorBoard 차트, 곡선 비교, 표, 로그, 이미지 |
| [Setting](https://github.com/YuriHan914/Laboard/blob/master/Docs/ko/setting.md) | 프로젝트 파일 로드, 감지된 항목, 테마 전환, Result·Hyperparameter 표의 페이지당 행 수, 프로젝트 파일 작성법 |


