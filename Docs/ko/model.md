# Model

<p align="center">
  <img src="../assets/LABOARD_MODEL.png" alt="Model" width="900"/>
</p>



[English](../en/model.md) | **한국어**

Model 페이지는 모델 파일의 그래프를 [Netron](https://netron.app)으로 보여 주고, 옆에 파라미터 수와 파일
속성을 표시합니다. 모든 정보를 파일 자체에서 읽으므로 GPU나 PyTorch가 필요 없습니다.

## 목록에 나오는 파일

`[Path] Models` 아래에서 알려진 체크포인트 확장자를 가진 파일이 모두 나옵니다.

| 형식 | 확장자 |
| --- | --- |
| PyTorch | `.pt` `.pth` `.ckpt` `.bin` |
| ONNX | `.onnx` |
| safetensors | `.safetensors` |
| JAX / Flax | `.msgpack` |
| TensorRT | `.engine` `.trt` `.plan` |
| Keras | `.h5` `.keras` |
| TensorFlow | `.pb` |
| TFLite | `.tflite` |
| GGUF | `.gguf` |
| Pickle | `.pkl` `.joblib` |
| CoreML | `.mlmodel` |
| OpenVINO | `.xml` |

- 일부 확장자만 보려면 프로젝트 파일에 `[Models] Extensions = [".pt", ".onnx"]`를 추가합니다.
- 일치하는 파일이 없으면 폴더 안의 모든 파일이 나옵니다.
- task별 폴더(`Models/<task>/<model>/`)가 있으면 `<task>/<model>` 하나를 모델 하나로 셉니다.
- `[Path] Models`는 `"ssh:~/project/Models"`처럼 서버에 둘 수 있습니다. 불러올 때마다 500 MB 미만 파일을 복사합니다
  ([원격 서버의 파일](setting.md#원격-서버의-파일)).

## 왼쪽 사이드바

**Model files**는 폴더 트리입니다. 각 행에 확장자, 파일 이름, 파일 크기가 표시됩니다.

## 그래프 (가운데)

머리글에 형식과 파일 이름이 나옵니다. 그래프에 보이는 내용은 파일 종류에 따라 다릅니다.

| 파일 | 보이는 것 |
| --- | --- |
| ONNX, TorchScript 등 Netron이 읽는 형식 | 전체 그래프 |
| safetensors, msgpack (가중치만 저장) | 모듈 목록. 레이어 간 연결 정보가 없음 |
| `torch.save` 체크포인트 (`.pt .pth .ckpt .bin`) | **Layer sequence / As stored** 전환 (아래 참고) |
| TensorRT 엔진 | 안내 문구만. 엔진은 특정 TensorRT 버전과 GPU용으로 컴파일되어 레이어를 읽을 수 없음. 엔진을 만든 원본 ONNX 파일을 열어 보세요 |

### `torch.save` 체크포인트

이 파일에는 가중치는 있지만 레이어가 어떻게 연결되는지는 없기 때문에 두 가지 보기를 제공합니다.

- **Layer sequence** (기본): Laboard가 각 모듈의 텐서를 보고 종류(Conv / Linear / BatchNorm / Norm /
  Embedding)를 판별합니다. 그런 다음 등록된 순서대로 이어서 shape만 담은 ONNX 그래프로 보여 줍니다.
  분기와 skip 연결은 표시되지 않습니다.
- **As stored**: Netron이 파일을 저장된 그대로 엽니다.

### 기타 컨트롤

- **Open in browser**는 같은 Netron 화면을 웹 브라우저에서 엽니다.
- `netron`이나 `PyQt6-WebEngine`이 설치되어 있지 않으면 `pip install -r requirements.txt`를 실행하라는
  안내가 나옵니다.

## 오른쪽 패널

### Model properties

- **타일:** **Parameters**(텐서가 있는 파일일 때 전체 파라미터 수)와 **Size**.
- **파일에서 읽은 행.** 형식에 따라 다릅니다.

| 형식 | 행 |
| --- | --- |
| ONNX | IR 버전, producer, opset |
| safetensors / msgpack / PyTorch | 형식 세부 정보와 텐서 수 |
| TensorRT | 엔진 또는 plan 헤더 |

- **파일 시스템에서 가져온 행** (항상 표시):
  - **Path:** `[Path] Models`의 상위 폴더 기준 경로.
  - **Kind:** 형식.
  - **Modified:** 파일이 마지막으로 바뀐 시각.
  - **Folder:** `[Path] Models` 아래의 폴더.

### Parameters by layer

레이어마다 막대 하나로 파라미터 수를 보여 줍니다. 막대 길이는 가장 큰 레이어 기준입니다. 긴 레이어
이름은 가운데가 생략되며, 이름 위에 마우스를 올리면 전체 이름이 보입니다.
