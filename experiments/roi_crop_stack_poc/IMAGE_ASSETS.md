# ROI Crop PoC 이미지 자료 목록 (2026-11-10)

**담당:** CV Team — 최강민
**기록 범위:** 2026-11-10 이미지 기반 실험에서 실제 사용한 입력 파일 2개와 생성된 결과 4개.
**GitHub 이미지 업로드 상태:** **축소 미리보기 4장(PNG 1장 + WebP 3장) 업로드 완료** (2026-11-11). 아래 표의 고해상도 원본·전체 결과는 기존 로컬 패키지/Google Drive 자료이며 GitHub에는 포함하지 않는다.

> GitHub에 표시되는 사진은 **리사이즈·손실 압축한 문서용 미리보기**이다. SHA-256 표는 **전체 해상도 원본/결과** 파일의 체크섬으로, GitHub의 WebP 미리보기와는 일치하지 않는다.

## GitHub README에서 직접 보이는 축소 미리보기 (실제 GitHub 파일)

| 단계 | GitHub 이미지 | 미리보기 해상도 | 원본 자료와의 관계 |
|---|---|---|---|
| G-code Stack Mask | [stack_mask.png](assets/previews/stack_mask.png) | 256×256 | layer_0240.png 축소 |
| 카메라 촬영 원본 | [camera_original.webp](assets/previews/camera_original.webp) | 660×495 | L217 촬영 JPG 축소 |
| 좌표 영역 표시 | [roi_overlay.webp](assets/previews/roi_overlay.webp) | 660×495 | roi_overlay.jpg 축소 |
| 최종 Crop | [roi_crop.webp](assets/previews/roi_crop.webp) | 414×249 | roi_crop.jpg 손실 압축 |

각 단계 이미지는 [실험 README](README.md)에 인라인 표시된다. 이미지 4장은 CV 실험 문서의 *preview* 자료이며 원본 촬영 데이터를 복제한 것이 아니다.

## 실험 자료 (로컬 패키지 내부의 `assets/` 이하 상대 경로)

| 구분 | 패키지 내 경로 | 크기(bytes) | 해상도 |
|---|---|---:|---|
| 원본 Stack Mask (L240) | `assets/input/layer_0240.png` | 98,543 | 2048×2048 |
| 원본 카메라 이미지 (파일명상 L217) | `assets/input/bambu_p1s_651_L217_중앙조절.jpg` | 309,704 | 2048×1536 |
| 시각화: ROI 위치 표시 | `assets/output/roi_overlay.jpg` | 439,496 | 2048×1536 |
| Crop 결과 | `assets/output/roi_crop.jpg` | 19,497 | 414×249 |
| Stack 이진 마스크 | `assets/output/stack_binary.png` | 8,865 | 2048×2048 |
| 출력 메타데이터 | `assets/output/roi_metadata.json` | 1,343 | JSON |

## SHA-256 (원본/생성 산출물 동일성 확인용)

```text
a4476ebc2a1594bf1f027fabcfb4d76be0f8534f276f3b5c1ef710277aea1047  assets/input/layer_0240.png
364049e5f539e38f1fbc0eca5a0591d4e65b9fa38446dc4170cca59f5c1c7478  assets/input/bambu_p1s_651_L217_중앙조절.jpg
d3b77864e42bd62146cbd9ebb18161960676a91da63a2173bef858fb81c877dd  assets/output/roi_overlay.jpg
390b46dc51a4e5d432b7d2ec307861b0ef7ada7432f2e70c32e6f714a6bcb728  assets/output/roi_crop.jpg
0dab01a9546da957cce701bc7f0f93b690597b3ab38fe846d2d1cd46e5e0f815  assets/output/stack_binary.png
ae4a52a8c1bae798b3a5b33ed61bedc4907917b8274d0111d543a69af7694cec  assets/output/roi_metadata.json
```

## 자료 반영 방법

제공된 ZIP을 풀었을 때 `cv/experiments/roi_crop_stack_poc/assets/` 하위에 `input/`, `output/`, `sha256-manifest.json`, `README.txt`가 위치하도록 정리되어 있다. 원본은 드라이브에 계속 보관하고, GitHub에는 문서 시각화를 위한 축소 미리보기 4장만 업로드했다. 원본 전체 자료를 올릴 때는 별도로 공개·공유 가능 여부와 용량을 검토한다.

- 원본과 결과가 있는 로컬 패키지: 2026-11-10 대화에서 제공한 `cv_roi_crop_images_and_results.zip` (GitHub 외부 대화 첨부)
- 재실행 방법: [README.md](README.md)
- 이미지 기반 실험의 검증 수준과 한계: [IMAGE_VERIFICATION.md](IMAGE_VERIFICATION.md)

**중요:** Stack Mask L240과 카메라 L217은 서로 다른 레이어며, 카메라 영상의 밝은 출력물을 이용해 시험용 정합을 설정했다. 실제 레이어별 정합 성능이나 출력 품질 검증 결과가 아니다.
