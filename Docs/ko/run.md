<p align="center">
  <img src="../assets/LABOARD_RUN.png" alt="Run" width="900"/>
</p>

# Run

[English](../en/run.md) | **한국어**

Run 페이지는 학습 run 하나에 대해 다음을 보여 줍니다.

- run의 위치와 그 폴더를 마지막으로 건드린 커밋
- 학습이 얼마나 진행됐는지
- 설정 파일에 있는 모든 하이퍼파라미터와 각 값이 나온 파일
- GPU 상태

## run으로 인식하는 것

- **run 조건:** `paths.runs` 아래 3단계 깊이까지의 폴더 중 설정 파일(`.json`, `.yaml`, `.yml`, `.toml`,
  각 2MB 미만)이 들어 있는 폴더.
- **중첩 없음:** 한 폴더가 run으로 인식되면 그 안의 폴더는 따로 run이 되지 않습니다.
- **개수 제한:** 최대 500개까지 읽습니다.
- **YAML:** PyYAML이 설치되어 있어야 읽고, 없으면 건너뜁니다.
- **정렬:** 가장 최근에 수정된 run이 맨 앞에 옵니다.
- **이름:** `paths.runs` 기준 상대 경로입니다. `paths.runs` 자체가 run이면 설정의 `exp_name`, `run_name`,
  `name` 중 있는 값을, 없으면 폴더 이름을 씁니다.

## 왼쪽 사이드바

**Runs**는 폴더 트리입니다. 각 run 옆에는 다음이 표시됩니다.

- `trainer_state.json`에 0~1 사이의 `best_metric`이 있으면 그 값을 백분율로
- 없으면 마지막 수정 날짜

## 머리글 카드

| 부분 | 내용 |
| --- | --- |
| 제목 | run 이름 |
| 부제 | run 폴더 경로 · 그 폴더를 마지막으로 건드린 커밋 · 마지막 수정 시각 |
| **Open folder** | 파일 관리자에서 run 폴더 열기 |
| 진행 막대 | `trainer_state.json`의 `epoch / 전체 epoch` |
| Epoch 표시 | 예: `Epoch 12 / 50`. `trainer_state.json`이 없으면 `50 epochs configured` 또는 `No trainer_state.json` |
| Best | `trainer_state.json`에 `best_metric`이 있으면 `best 0.9132` |

전체 epoch 수는 아래 중 처음으로 값이 있는 것을 씁니다.

1. `trainer_state.json`의 `num_train_epochs`
2. 설정의 `epochs`
3. 설정의 `num_train_epochs`
4. 설정의 `max_epochs`

여기서 설정은 이름에 `config`, `args`, `hparams`가 들어간 파일을 말합니다.

## 하이퍼파라미터

### 머리글

- **Read from source at launch** 옆에 읽은 설정 파일이 나옵니다. 처음 4개를 보여 주고 나머지는 `+N more`로 표시합니다.
- **Show source / Values only**는 각 값이 나온 파일을 보여 주는 열을 켜고 끕니다.
- **Re-read**는 프로젝트 파일을 다시 로드합니다. 설정이나 GPU 상태의 변경을 반영할 때 씁니다.

### 섹션

설정 파일마다 카드가 하나씩 있습니다(`trainer_state.json`은 진행 상황에만 쓰입니다). 카드는 두 열로
배치되고, 페이지가 좁으면 한 열이 됩니다.

- **제목:** 파일 이름을 문장형으로 바꾼 것. 예를 들어 `training_args.json`은 *Training args*가 됩니다.
- **키:** 중첩된 키는 점으로 이어 펼칩니다. 예: `optimizer.lr`.
- **긴 값:** 8개보다 긴 리스트는 `[N items]`로, 90자보다 긴 값은 `…`로 잘라서 보여 줍니다.
- **행 제한:** 카드마다 최대 40개 행을 보여 줍니다.

## GPU

`nvidia-smi`로 GPU 0의 상태를 읽습니다.

- **Utilization:** 사용률(%)과 막대.
- **Memory:** 사용량 / 전체(GB)와 막대.
- **Temperature:** 온도(°C)와 막대.

GPU는 프로젝트를 로드할 때 한 번 읽으며 계속 갱신되지 않습니다. 새로 읽으려면 **Re-read**를 누르세요.
`nvidia-smi`가 없으면 *No GPU detected*로 표시됩니다.
