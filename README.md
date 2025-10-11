# YouTube 자동화 파이프라인 (MVP)

한국어 스크립트를 영어 콘텐츠로 변환하는 완전한 오프라인 파이프라인입니다. 오디오 및 비디오 출력을 자동 생성합니다.

## 🎯 주요 기능

- **텍스트 처리**: 한국어 입력 텍스트 정제 및 준비
- **번역**: 한국어 → 영어 (Argos Translate 폴백 지원)
- **콘텐츠 생성**: 구조화된 영어 마크다운 포스트 생성
- **음성 합성(TTS)**: **OpenAI TTS (Onyx Natural) + 자연스러운 호흡 간격** - 기본 고품질 내레이션
  - **공통 TTS 모듈**: 모든 TTS 엔진에서 일관된 결과를 위한 공유 세그먼트 분할 및 후처리
- **비디오 생성**: 파형 시각화 및 제목이 포함된 MP4 비디오 생성
- **발행**: 선택적 WordPress 통합 (설정 가능)

## 📁 디렉터리 구조

```
~/yt-auto/
├── input/           # 한국어 .txt 파일을 여기에 배치
├── work/           # 중간 처리 파일
├── output/         # 최종 오디오/비디오 출력
├── assets/         # 배경 이미지 (선택사항)
├── scripts/        # 처리 파이프라인 스크립트
├── config.yaml     # 설정 파일
└── run_pipeline.sh # 메인 실행 스크립트
```

## 🚀 빠른 시작

### 사전 준비

```bash
# 시스템 의존성 설치
brew install xz ffmpeg piper

# Piper 음성 모델 다운로드 (선택사항)
mkdir -p ~/piper_models
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx -P ~/piper_models/
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json -P ~/piper_models/

# 설정 구성
cp config.yaml.example config.yaml
cp .env.example .env
# .env를 편집하여 OpenAI API 키 설정

# 환경 체크
./scripts/diagnose.sh
```

### 파이프라인 실행

1. **한국어 스크립트를 `input/` 디렉터리에 배치**:
   ```
   input/my-script.txt
   ```

2. **파이프라인 실행**:
   ```bash
   ./run_pipeline.sh input/my-script.txt
   ```

3. **출력 확인**:
   - 영어 마크다운: `work/my-script/post_en.md`
   - 오디오 파일: `output/my-script/voice_en.wav`
   - 비디오 파일: `output/my-script/video_en.mp4`

## 📝 수동 단계별 실행

```bash
cd ~/yt-auto
source .venv/bin/activate

# 1단계: 준비
SLUG=$(python scripts/01_prepare.py input/my-script.txt)

# 2단계: 번역
python scripts/02_translate.py $SLUG

# 3단계: 편집
TITLE=$(python scripts/03_edit_en.py $SLUG)

# 4단계: TTS
python scripts/04_tts.py $SLUG

# 5단계: 비디오
python scripts/05_video.py $SLUG --title-text "$TITLE"

# 선택사항: 발행
python scripts/06_publish.py wordpress $SLUG
```

---

## 🎙️ TTS 품질 관리 시스템

### 개요

완전 자동화된 TTS 품질 모니터링 파이프라인:
1. **비교 실행**: OpenAI vs Piper TTS 병렬 실행
2. **리포트 집계**: JSON → CSV/Markdown 자동 변환
3. **시각화**: CSV → PNG 차트 (트렌드/산포도/히스토그램)

---

## 🔄 Step 1: TTS 비교 실행

OpenAI와 Piper TTS를 동일한 설정으로 나란히 실행하여 공정한 A/B 비교를 수행합니다.

### 빠른 실행

```bash
# 기본 설정으로 비교 (가장 간단)
bash scripts/compare_tts.sh input/text.txt output/compare_demo

# 또는 짧은 샘플 텍스트로 테스트
bash scripts/compare_tts.sh tests/data/sample_short.txt output/test1
```

### 고급 옵션

```bash
# Python 스크립트로 세밀한 제어
python3 scripts/compare_tts.py input/text.txt \
  --outdir output/my_comparison \
  --style-prefix "침착하고 자신감 있게, 전문 비디오를 내레이션하는 것처럼 말하세요." \
  --pause-profile natural \
  --openai-voice onyx \
  --openai-model tts-1 \
  --ab-swap-sec 8 \
  --max-chars 800
```

**주요 옵션:**
- `--style-prefix`: TTS 스타일 지시문
- `--pause-profile`: `natural` / `broadcast` / `tight`
- `--ab-swap-sec 8`: 8초마다 엔진 전환하는 A/B 믹스 생성
- `--openai-voice`: `onyx` / `alloy` / `echo` / `fable` / `nova` / `shimmer`

### 생성되는 파일

```
output/compare_demo/
├── openai.wav              # OpenAI TTS 원본
├── openai_match.wav        # 볼륨 매칭된 버전
├── piper.wav              # Piper TTS 원본 (설치된 경우)
├── piper_match.wav        # 볼륨 매칭된 버전 (설치된 경우)
└── AB_openai_piper.wav    # A/B 교차 믹스 (옵션)

work/cmp_*/
└── compare_report.json    # 상세 메트릭 데이터
```

### 비교 리포트 구조

```json
{
  "input_file": "input/text.txt",
  "slug": "cmp_abc123",
  "settings": {
    "pause_profile": "natural",
    "fade_ms": 20,
    "crossfade_ms": 50,
    "max_chars": 800
  },
  "openai": {
    "duration_sec": 45.2,
    "rms_dbfs": -18.5,
    "peak_dbfs": -3.2,
    "silence_ratio": 12.3
  },
  "piper": {
    "duration_sec": 43.8,
    "rms_dbfs": -19.1,
    "peak_dbfs": -4.5,
    "silence_ratio": 10.5
  },
  "comparison": {
    "duration_diff_sec": 1.4,
    "duration_ratio": 1.032,
    "rms_diff_db": 0.6,
    "faster_engine": "piper"
  }
}
```

**참고**: Piper가 설치되지 않은 경우, 스크립트는 Piper 합성을 우아하게 건너뛰고 OpenAI 출력과 리포트만 생성합니다.

---

## 📊 Step 2: 리포트 집계

여러 `compare_report.json` 파일을 CSV 및 Markdown 테이블로 집계하여 분석합니다.

### 기본 사용법

```bash
# work/ 디렉터리의 모든 리포트 스캔
python3 scripts/compare_report_to_md.py

# 또는 셸 헬퍼 사용
bash scripts/export_reports.sh
```

### 고급 옵션

```bash
# 특정 패턴만 스캔
python3 scripts/compare_report_to_md.py \
  --work-glob "work/exp*/compare_report.json" \
  --outdir output/experiment_reports

# RMS 레벨 순으로 정렬
python3 scripts/compare_report_to_md.py \
  --sort "openai_rms"

# Duration 내림차순 정렬 (가장 긴 것부터)
python3 scripts/compare_report_to_md.py \
  --sort "-openai_duration"

# 다중 정렬: RMS 오름차순 → Duration 내림차순
python3 scripts/compare_report_to_md.py \
  --sort "openai_rms,-openai_duration"

# 최근 10개만 출력
python3 scripts/compare_report_to_md.py \
  --limit 10
```

### 생성되는 파일

```
output/reports/
├── tts_compare_20251011_230145.csv  # 스프레드시트용 (Excel, Google Sheets)
└── tts_compare_20251011_230145.md   # 문서용 (Markdown 테이블)
```

**CSV 예시:**
```csv
slug,pause_profile,fade_ms,openai_duration,openai_rms,piper_duration,piper_rms,piper_skipped
cmp_067e790a,natural,20,8.71,-23.84,,,True
cmp_931ef14f,natural,20,1.0,-20.0,,,True
```

**활용 방법:**
- 📈 **품질 추적**: 시간 경과에 따른 오디오 품질 메트릭 모니터링
- 🔬 **설정 비교**: 다양한 TTS 설정 성능 비교
- 👥 **팀 공유**: CSV를 스프레드시트로 임포트하여 공유
- 📝 **문서화**: Markdown 테이블을 PR이나 위키에 삽입

---

## 📈 Step 3: 시각화

CSV 리포트를 PNG 차트로 변환하여 빠른 인사이트를 얻습니다.

### 빠른 실행

```bash
# 기본 설정으로 플롯 생성 (rolling mean = 3)
bash scripts/plot_reports.sh

# 또는 Python 스크립트로 직접 실행
python3 scripts/plot_tts_metrics.py
```

### 고급 옵션

```bash
# 최근 20개 실행만, 5-포인트 이동평균 적용
python3 scripts/plot_tts_metrics.py \
  --csv-glob "output/reports/tts_compare_*.csv" \
  --outdir output/reports/plots \
  --rolling 5 \
  --limit 20

# 차트 제목에 주석 추가
python3 scripts/plot_tts_metrics.py \
  --title-suffix "Onyx Natural vs Piper Amy - 2025년 10월"

# 특정 실험 배치만 플롯
python3 scripts/plot_tts_metrics.py \
  --csv-glob "output/experiment_reports/*.csv" \
  --outdir output/experiment_plots

# 셸 래퍼로 간편하게 (csv_glob, outdir, rolling)
bash scripts/plot_reports.sh \
  "output/reports/*.csv" \
  "output/my_plots" \
  5
```

### 생성되는 차트

```
output/reports/plots/
├── rms_trend.png              # RMS 레벨 트렌드 (이동평균 포함)
├── duration_scatter.png       # Duration 산포도 (y=x 기준선)
├── openai_silence_hist.png    # OpenAI 무음 비율 분포
└── piper_silence_hist.png     # Piper 무음 비율 분포 (있으면)
```

### 차트 해석 가이드

**1. RMS Trend (rms_trend.png)**
- **좋음**: -18 ~ -24 dBFS 사이 안정적 유지
- **경고**: -15 dBFS 이상 → 너무 큼 (왜곡 위험)
- **경고**: -30 dBFS 이하 → 너무 작음 (배경소음 문제)

**2. Duration Scatter (duration_scatter.png)**
- y=x 선 위: Piper가 더 느림
- y=x 선 아래: Piper가 더 빠름
- 산포가 클수록: 엔진 간 일관성 낮음

**3. Silence Histogram (silence_hist.png)**
- **좋음**: 5-15% (자연스러운 호흡)
- **경고**: >25% → 너무 건조함 ("로봇 같은" 느낌)
- **경고**: <3% → 숨 쉴 틈 없음 (과밀)

**활용 방법:**
- 🔍 **품질 모니터링**: RMS/peak 이상치를 한눈에 파악
- 🆚 **A/B 테스팅**: 다양한 음성 설정의 시각적 비교
- 📊 **트렌드 분석**: 반복 실험에서 품질 저하 또는 개선 추적
- 🐛 **빠른 디버깅**: silence ratio나 duration의 이상값 식별

**요구사항:**
- matplotlib (venv에 이미 설치됨)
- Headless 모드 실행 (디스플레이 불필요)
- CI/CD 환경에서 작동

---

## 🔄 전체 워크플로우 예시

### 시나리오: 3가지 pause profile 비교

```bash
cd ~/yt-auto
source .venv/bin/activate

# 1. 테스트 텍스트 준비
cat > input/test-narration.txt <<EOF
튜토리얼 시리즈에 오신 것을 환영합니다.
이 비디오에서는 고급 기술을 탐구합니다.
첫 번째 예제로 시작하겠습니다.
EOF

# 2. 세 가지 설정으로 TTS 비교 실행
echo "🎙️  실험 1: Natural"
python3 scripts/compare_tts.py input/test-narration.txt \
  --outdir output/exp1_natural \
  --pause-profile natural

echo "🎙️  실험 2: Broadcast"
python3 scripts/compare_tts.py input/test-narration.txt \
  --outdir output/exp2_broadcast \
  --pause-profile broadcast

echo "🎙️  실험 3: Tight"
python3 scripts/compare_tts.py input/test-narration.txt \
  --outdir output/exp3_tight \
  --pause-profile tight

# 3. 리포트 집계
echo "📊 리포트 집계 중..."
python3 scripts/compare_report_to_md.py \
  --outdir output/reports \
  --sort "pause_profile,openai_duration"

# 4. 시각화
echo "📈 차트 생성 중..."
bash scripts/plot_reports.sh

# 5. 결과 확인
echo "✅ 완료!"
echo ""
echo "오디오 파일:"
ls -lh output/exp*/openai.wav
echo ""
echo "CSV 리포트:"
cat output/reports/tts_compare_*.csv
echo ""
echo "차트:"
ls -lh output/reports/plots/*.png
echo ""
echo "차트 보기:"
echo "  open output/reports/plots/rms_trend.png"
```

---

## ⚙️ 상세 설정

### OpenAI TTS 기본 설정

파이프라인은 기본적으로 **OpenAI TTS with Onyx voice**와 자연스러운 호흡 간격을 사용합니다:

```yaml
# config.yaml
tts:
  engine: openai
  default_preset: onyx_natural  # 깊고 자신감 있는 남성 음성

openai:
  tts:
    voice: onyx                 # 깊은 남성 음성
    model: tts-1                # 빠르고 비용 효율적
    format: wav
    speed: 1.0
    pause_profile: natural      # 자연스러운 호흡
    pause_short: 0.25           # 쉼표 뒤
    pause_medium: 0.50          # 문장 끝
    pause_long: 0.80            # 문단 사이
```

### 사용 가능한 프리셋

- `onyx_natural`: 기본값, 균형잡힌 내레이션
- `onyx_broadcast`: 권위 있는 방송 톤, HD 품질, 느린 페이스
- `onyx_fast`: 빠른 브리핑, 짧은 간격
- `alloy_warm_low`: 따뜻하고 감성적인 톤

### API 키 설정

`.env` 파일에 OpenAI API 키를 설정하세요:

```bash
# .env
OPENAI_API_KEY=sk-proj-your-key-here

# 선택사항: TTS 기본값 재정의
OPENAI_TTS_VOICE=onyx
OPENAI_TTS_MODEL=tts-1
OPENAI_TTS_FORMAT=wav
OPENAI_TTS_PAUSE_PROFILE=natural

# Piper 사용 시 (선택)
PIPER_VOICE=/Users/lyh/piper_models/en_US-amy-medium.onnx
```

### TTS 공통 옵션

| 옵션 | 기본값 | 설명 |
|------|-------|------|
| `--fade-ms` | 20 | 페이드 인/아웃 길이 (밀리초) |
| `--crossfade-ms` | 50 | 세그먼트 간 크로스페이드 길이 (ms) |
| `--max-chars` | 800 | 세그먼트당 최대 문자 수 |
| `--style-prefix` | None | 텍스트 앞에 추가할 스타일 지시문 |
| `--json-out` | None | 메트릭을 JSON 파일로 저장 |
| `--normalize` | False | 볼륨 정규화 적용 |

---

## 🔧 시스템 요구사항

- macOS (Mac Mini에서 테스트됨)
- Python 3.10+ (3.11+ 권장)
- FFmpeg 8.0+
- uv 패키지 매니저 (또는 pip/venv)

### Python 의존성

```
# 핵심
- pydub          # 오디오 처리
- openai         # OpenAI API
- loguru         # 로깅
- matplotlib     # 시각화 (Step 5)

# 테스트
- pytest         # 테스트 프레임워크
- pytest-cov     # 커버리지

# 선택사항
- piper          # Piper TTS (로컬 설치)
```

---

## 📋 출력 파일

입력 `input/my-script.txt`에 대해 파이프라인이 생성하는 파일:

**기본 파이프라인:**
1. `work/my-script/post_en.md` - 구조화된 영어 마크다운
2. `output/my-script/voice_en.wav` - 영어 오디오 (22kHz, mono)
3. `output/my-script/video_en.mp4` - 비디오 (1920x1080, H.264)

**TTS 비교 시스템:**
4. `work/cmp_*/compare_report.json` - 비교 메트릭
5. `output/reports/tts_compare_*.csv` - 집계 리포트 (CSV)
6. `output/reports/tts_compare_*.md` - 집계 리포트 (Markdown)
7. `output/reports/plots/*.png` - 시각화 차트

---

## 🔍 문제 해결

### Q: "ModuleNotFoundError: No module named 'matplotlib'"

```bash
# 가상환경 활성화 확인
source .venv/bin/activate

# matplotlib 설치
pip install matplotlib

# 또는 venv python 직접 사용
.venv/bin/python3 scripts/plot_tts_metrics.py
```

### Q: "No CSV rows found"

```bash
# 순서: 비교 → 리포트 → 플롯
bash scripts/compare_tts.sh input/text.txt output/test1
python3 scripts/compare_report_to_md.py
bash scripts/plot_reports.sh
```

### Q: Piper 없어서 에러 발생?

**문제 없음!** Piper는 선택사항입니다.

- OpenAI만으로도 모든 기능 작동
- Piper 없으면 `piper_skipped=True` 플래그 설정
- 차트는 OpenAI 데이터만 표시

### Q: 차트가 안 보여요

```bash
# Headless 모드는 정상입니다
# PNG 파일로 저장되므로 이미지 뷰어로 열기

# macOS
open output/reports/plots/rms_trend.png

# 모든 차트 열기
open output/reports/plots/*.png
```

### lzma 모듈 에러

**에러**: `ModuleNotFoundError: No module named '_lzma'`

**해결**:
```bash
brew install xz
# pyenv 사용 시:
pyenv install --force $(pyenv version-name)
```

### FFmpeg 문제

**에러**: `ffmpeg not found`

**해결**:
```bash
brew install ffmpeg
ffmpeg -version  # 확인
```

---

## 🧪 테스트

### 테스트 실행

프로젝트에는 TTS 기능에 대한 포괄적인 테스트 커버리지가 포함되어 있습니다:

```bash
# 빠른 테스트 실행
make test

# 상세 출력
make test-v

# 커버리지 리포트
make cov

# 개발 의존성 설치
make install-dev
```

### 테스트 구조

```
tests/
  test_tts_common.py      # 텍스트 분할 및 오디오 처리 단위 테스트
  test_openai_tts.py      # OpenAI TTS 테스트 (모킹 + 선택적 라이브)
  test_piper_tts.py       # Piper TTS 테스트 (설치 조건부)
  test_compare_tts.py     # TTS 비교 통합 테스트
  test_report_export.py   # 리포트 집계 테스트
  test_plot_metrics.py    # 시각화 테스트
  data/
    sample_short.txt      # 테스트 입력 텍스트
    fake.wav              # 오디오 픽스처
```

### 테스트 커버리지

- ✅ **텍스트 분할**: 문단/문장 분리, 최대 문자 제한
- ✅ **오디오 처리**: 페이드, 크로스페이드, 정규화, 속도 조절
- ✅ **메트릭**: Duration, RMS/peak 레벨, silence ratio
- ✅ **볼륨 매칭**: 엔진 간 자동 레벨 균형
- ✅ **API 모킹**: API 비용 없는 빠른 테스트
- ✅ **선택적 라이브 테스트**: `RUN_LIVE_TTS=1` 설정

### 라이브 API 테스트 실행

```bash
# 환경변수 설정
export OPENAI_API_KEY=sk-proj-your-key-here
export RUN_LIVE_TTS=1

# OpenAI 라이브 테스트만 실행
pytest tests/test_openai_tts.py::TestOpenAITTSLive -v
```

**참고**: 라이브 테스트는 API 비용 최소화를 위해 매우 짧은 텍스트 샘플을 사용합니다.

---

## 💡 팁 & 베스트 프랙티스

### 1. 짧은 텍스트로 먼저 테스트

```bash
# 3-4 문장 샘플로 파이프라인 검증
echo "테스트 문장 하나. 테스트 문장 둘. 테스트 문장 셋." > input/quick-test.txt
bash scripts/compare_tts.sh input/quick-test.txt output/quick-test
```

### 2. 타임스탬프로 실험 관리

```bash
TS=$(date +%Y%m%d_%H%M%S)
python3 scripts/compare_tts.py input/text.txt \
  --outdir "output/exp_${TS}"
```

### 3. CSV를 스프레드시트로 분석

```bash
# CSV 생성 후
python3 scripts/compare_report_to_md.py

# Google Sheets/Excel로 임포트
# → 피벗 테이블, 조건부 서식 등 고급 분석 가능
```

### 4. 일일 모니터링 자동화

```bash
#!/bin/bash
# daily_monitor.sh

DATE=$(date +%Y%m%d)

# TTS 생성
python3 scripts/compare_tts.py input/daily-script.txt \
  --outdir output/daily_$DATE

# 리포트 갱신
python3 scripts/compare_report_to_md.py

# 최근 30일 트렌드
python3 scripts/plot_tts_metrics.py \
  --limit 30 \
  --rolling 7 \
  --title-suffix "30일 이동평균"
```

### 5. 여러 설정 배치 비교

```bash
# 실험 A: Natural 설정
python3 scripts/compare_tts.py input/sample.txt \
  --outdir output/test_A \
  --pause-profile natural

# 실험 B: Broadcast 설정
python3 scripts/compare_tts.py input/sample.txt \
  --outdir output/test_B \
  --pause-profile broadcast

# 통합 리포트 및 시각화
python3 scripts/compare_report_to_md.py
bash scripts/plot_reports.sh
```

---

## 📚 추가 문서

- **CLAUDE.md**: AI 어시스턴트를 위한 프로젝트 컨텍스트 가이드
- **PR_BODY_STEP*.md**: 각 구현 단계별 상세 변경사항
- **tests/**: 테스트 코드 및 예제

---

## 🔮 향후 계획

### 완료됨 ✅
- Step 0: 기본 TTS 설정 (Onyx Natural)
- Step 1: TTS 공통 모듈
- Step 2: OpenAI TTS 리팩터 + 메트릭
- Step 3: Piper + 비교 시스템
- Step 4: 리포트 집계 (CSV/Markdown)
- Step 5: 시각화 (PNG 차트)

### 선택적 확장 (향후)
- Plotly HTML 인터랙티브 차트
- Streamlit/FastAPI 실시간 웹 대시보드
- 이상치 자동 감지 + Slack/Discord 알림
- 다중 메트릭 상관관계 분석
- Google Translate, ElevenLabs 통합
- YouTube 업로드 자동화

---

## 📞 지원

문제가 발생하면:
1. 이 README의 **문제 해결** 섹션 확인
2. `./scripts/diagnose.sh` 실행하여 환경 체크
3. GitHub Issues에 질문 등록

---

**Made with ❤️ by Claude Code**
