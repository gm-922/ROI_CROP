# 이미지 기반 ROI Crop 모듈 실험·검증 결과

- **실험일 / 재검증일:** 2026-11-10 (Asia/Seoul)
- **담당:** CV Team — 최강민
- **대상 구현:** [ROI Crop 스크립트](src/roi_crop_stack.py) / [단위 테스트](tests/test_roi_crop_stack.py)
- **판정:** `ROI Crop 기능 동작 확인(PoC)`; **레이어 대응·독립 좌표 정합 정확도 미검증**

## 1. 실험 목적과 입력 데이터

G-code Stack Mask에서 회색 누적 출력 예정 영역과 흰색 현재 레이어 라인을 포함하는 **비검정 영역 전체**를 자동 추출해 Bounding Box를 만든다. 별도 지정된 임시 Affine 매핑으로 촬영 영상 좌표계로 변환하고 Margin을 적용하여 실제 영상을 Crop한다.

| 구분 | 입력 및 조건 |
|---|---|
| G-code Stack Mask | `layer_0240.png` — **240번 레이어**, 2048×2048, RGBA 8-bit |
| 카메라 사진 | `bambu_p1s_651_L217_중앙조절.jpg` — 파일명상 **L217**, 2048×1536, JPEG |
| 마스크 전경 기준 | Grayscale `> 10` (합성 Stack Mask 전용, 안티앨리어싱 경계 포함 가능) |
| 검출 영역 | Stack Mask의 비검정 픽셀 **128,757개** (총 마스크 픽셀의 약 **3.07%**) |
| 좌표 정합 | 이미지상 출력물을 탐색해 만든 **시험용** 축별 scale+translation affine |
| Margin | **35 px** (카메라 이미지 좌표계) |

**자료 유의:** Stack Mask 240과 카메라 영상 L217은 레이어 번호가 다르다. 이는 같은 레이어 쌍의 정합 실험이 아닌, 제공된 두 이미지로 검토한 **기능 시연**이다. 원본의 Drive ID/촬영 조건·마스크 생성 버전은 추가 확인이 필요하다.

## 2. 이미지 처리 단계별 출력 수치

| 단계 | 실제 확인 결과 | 확인 수준 |
|---|---|---|
| (1) Mask 입력/전경 이진화 | 2048×2048 RGBA → grayscale 임계값 `>10`; 전경 **128,757 px** | 파일 재확인 / 실행 |
| (2) G-code Stack Mask Bounding Box | `[744, 879, 1304, 1169)`, 폭 **560 px** × 높이 **290 px** | 실행 |
| (3) 카메라 좌표 변환 | 사각형 외곽 `[835, 683, 1179, 862)`, 폭 **344 px** × 높이 **179 px** | **임시 affine** 연산 결과 |
| (4) Margin 및 최종 ROI | `[800, 648, 1214, 897)`, 폭 **414 px** × 높이 **249 px** | 실행 |
| (5) 카메라 영상 Crop | 2048×1536 → **414×249** JPEG 생성 | 파일 생성·크기 확인 |
| (6) 시각화 결과 | `roi_overlay.jpg`, `roi_crop.jpg`, `stack_binary.png`, `roi_metadata.json` 생성 | 파일 생성 확인 |
| (7) 단위 테스트 | bbox 좌표, affine/margin, 이미지 경계 클리핑/빈 마스크 등 **3/3 PASS** | 테스트 재실행 |

**좌표 표현:** 모든 `[x1, y1, x2, y2)`는 우측·아래쪽 끝이 **exclusive**인 반열린 구간이다.

사용한 시험용 변환:
```text
x_camera = 0.6142857143 * x_mask + 377.9714286
y_camera = 0.6172413793 * y_mask + 140.4448276
```

원본 촬영 프레임 크기 **3,145,728 px**, Crop 결과 **103,086 px**로, 이번 예시에서 **처리 대상 이미지 픽셀 수가 약 96.72% 감소**했다(원본의 약 3.28%만 남음). **이는 ROI 면적 축소율이며**, 연산시간 개선율이나 Segmentation 정확도·품질 평가 정확도를 뜻하지 않는다.

## 3. 실제 이미지로 확인한 시각적 결과

| 결과 파일(로컬 실행 후 생성) | 이미지로 확인한 내용 | 해석 |
|---|---|---|
| `output/roi_overlay.jpg` | 실제 촬영 영상 위에 임시 변환된 Stack Mask 예측 영역 **청록색**, 투영 외곽 **노란색**, Margin 포함 Crop 사각형 **초록색**으로 표시 | 설정된 ROI가 이 한 장의 촬영 이미지에서 출력물이 있는 구역을 감싸는 것을 **육안 확인** |
| `output/roi_crop.jpg` | **414×249** 이미지에 흰색 출력물이 포함되고, 프린터 헤드 등 주요 외부 배경이 제외됨 | 한 장에 대한 Crop 동작 확인 |
| `output/stack_binary.png` | 검은 배경을 제외한 회색·흰색 Stack Mask 영역을 이진화 | 합성 마스크의 전체 예정 영역 검출 확인 |

**주의:** 정합 파라미터를 설정할 때 촬영 영상에서 밝은 출력물의 Bounding Box를 이용했으므로, 출력물이 결과 ROI에 포함됐다는 사실은 *독립적인 정합 정확도 검증*이 아니다. 레이어가 불일치하므로 G-code 라인과 실제 레이어 출력 품질의 일치·불일치도 평가하지 않았다. IoU/픽셀 오차/검출 재현율, 처리시간과 타 레이어 일반화 성능은 **측정하지 않음**.

## 4. 재현 방법 및 검증 환경

재실행 환경(2026-11-10): **Python 3.13.5, OpenCV 4.13.0, NumPy 2.3.5**.
원본 입력 2개를 로컬에 준비한 후 저장소 루트에서 실행한다.

```bash
python -m pip install -r requirements.txt
python src/roi_crop_stack.py \
  --mask /local/path/layer_0240.png \
  --camera /local/path/bambu_p1s_651_L217_중앙조절.jpg \
  --calibration demo_calibration.json \
  --output-dir /local/path/roi_output \
  --margin 35
python -m unittest discover -s tests -p 'test_roi_crop_stack.py' -v
```

재실행 결과 **3 tests / OK**, 이미지 산출물 3개와 JSON 메타데이터 1개 생성 확인. 상세 좌표·파라미터는 [roi_metadata.json](roi_metadata.json)과 [demo_calibration.json](demo_calibration.json)에서 확인할 수 있다.

실제 원본 이미지와 생성된 JPG/PNG는 **GitHub에 업로드하지 않았다.** GitHub에는 재현 스크립트와 수치·판정·검증 절차를 기록하였고, 원본 자료는 기존 Google Drive 관리 원칙을 따른다. 시각 자료는 위 명령으로 로컬에서 재생성한다.

## 5. 검증 범위와 후속 조치

- **완료(검증됨, 기능 PoC 한정):** Stack Mask 전경 추출, bbox, affine 적용, clipping/margin, 이미지 Crop·출력 생성, 테스트 3건 통과.
- **미검증:** 동 레이어 매칭(L240↔L217), 출력물 검출 없이 독립적인 좌표 정합, 카메라 왜곡·원근 보정, 레이어별·색상별 강건성, 평가 성능.
- **다음 작업:** 실제 촬영 L217과 대응하는 Stack Mask 및 대응 관계 확보 → 베드 기준점 기반 좌표 정합 → 같은 레이어에서 누락 픽셀/IoU/좌표 오차 측정 → 복수 레이어 반복 검증.

본 실험의 `roi_metadata.json` 형식과 Affine 행렬은 **개별 CV PoC의 산출물**이며, [CV–FPGA 인터페이스 초안](https://github.com/minhosong-mse/modulino-vision_CV_FPGA/blob/main/docs/INTERFACE.md)에 명시된 공통 규격 확정으로 간주하지 않는다.
