# Startpack

Startpack은 Python 프로젝트를 위한 시작 템플릿입니다. 이 프로젝트는 Poetry를 사용하여 패키지 관리 및 의존성 관리를 수행하며, Claude AI API를 활용하여 README.md와 CHANGELOG.md를 자동으로 생성 및 업데이트하는 기능을 제공합니다.

## 목차

- [Startpack](#startpack)
  - [목차](#목차)
  - [프로젝트 구조](#프로젝트-구조)
  - [설정 방법](#설정-방법)
    - [초기 폴더에 최신 startpack 가져오는 git 명령어 세트](#초기-폴더에-최신-startpack-가져오는-git-명령어-세트)
    - [기본 패키지 다운 이후 설정 법](#기본-패키지-다운-이후-설정-법)
  - [사용 방법](#사용-방법)
    - [패키지 실행](#패키지-실행)
    - [스크립트 실행](#스크립트-실행)
    - [Git 액션즈 제외하고 Push 하는 방법](#git-액션즈-제외하고-push-하는-방법)
  - [dexius\_brachion.py 스크립트 설명](#dexius_brachionpy-스크립트-설명)
    - [주요 기능](#주요-기능)
    - [주요 함수](#주요-함수)
    - [사용 방법](#사용-방법-1)
    - [에러 처리 및 예외 상황](#에러-처리-및-예외-상황)
    - [성능 최적화](#성능-최적화)
  - [기타 세부 정보](#기타-세부-정보)

## 프로젝트 구조

```
startpack/
├── .github/
│   └── workflows/
│       └── startpack-docker-image-publish.yaml
├── dexius/
│   ├── configs.py
│   ├── dexius_brachion.py
│   └── dexius_brachion_manual.md
├── docker/
│   └── Dockerfile
├── etc/
│   └── daemon.json
├── startpack/
│   ├── configs.py
│   ├── version.json
│   ├── version.py
│   ├── __init__.py
│   └── __main__.py
├── tests/
│   ├── configs.py
│   ├── test_main.py
│   └── __init__.py
├── .env
├── CHANGELOG.md
├── FUTUREWORK.md
├── pyproject.toml
├── README.md
└── scripts.py
```

- `.github/workflows/`: GitHub Actions 워크플로우 파일이 포함된 디렉토리
- `dexius/`: Dexius 관련 파일이 포함된 디렉토리
  - `dexius_brachion.py`: README.md와 CHANGELOG.md를 자동으로 생성 및 업데이트하는 스크립트
  - `dexius_brachion_manual.md`: `dexius_brachion.py` 스크립트에 대한 상세 설명 및 공략집
- `docker/`: Dockerfile이 포함된 디렉토리
- `etc/`: 기타 설정 파일이 포함된 디렉토리
- `startpack/`: 메인 패키지 디렉토리
- `tests/`: 테스트 파일이 포함된 디렉토리
- `.env`: 환경 변수 파일
- `CHANGELOG.md`: 변경 사항 기록 파일
- `FUTUREWORK.md`: 향후 작업 계획 파일
- `pyproject.toml`: Poetry 프로젝트 설정 파일
- `README.md`: 프로젝트 설명 파일
- `scripts.py`: 유틸리티 스크립트 파일

## 설정 방법

### 초기 폴더에 최신 startpack 가져오는 git 명령어 세트

- 아무 것도 없는 비어있는 폴더 디렉토리로 이동하여 그대로 붙여 넣으세요.

```
git init
git remote add origin https://github.com/armbjs/startpack.git
git fetch origin main
git branch -M main
git pull origin main

```

### 기본 패키지 다운 이후 설정 법

1. Poetry를 설치합니다. (https://python-poetry.org/docs/#installation)
2. 프로젝트 디렉토리로 이동합니다.
3. `.env` 파일 내부에 필요한 환경 변수를 설정합니다. (예: `ANTHROPIC_API_KEY`)
4. 의존성을 설치합니다:
   ```
   poetry install
   ```
5. pyproject.toml, Dockerfile, workflows 내부 yaml 파일 내에 있는 패키지 명을 변경합니다. startpack -> 새로운 패키지 명
6. startpack의 폴더명을 변경합니다.
7. .git 폴더 삭제 후 새 저장소에 연걸합니다.

```
git init
git add .
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/armbjs/프로젝트명.git
git push -u origin main
```

## 사용 방법

### 패키지 실행

```
poetry run python -m startpack
```

### 스크립트 실행

```
poetry run patp  # PATCH 버전 업데이트 및 배포
poetry run minp  # MINOR 버전 업데이트 및 배포
poetry run majp  # MAJOR 버전 업데이트 및 배포
```

### Git 액션즈 제외하고 Push 하는 방법

- 커밋 메시지 끝에 [skip ci] 추가하여 커밋

## dexius_brachion.py 스크립트 설명

`dexius_brachion.py` 스크립트는 프로젝트의 주요 파일들을 분석하여 README.md와 CHANGELOG.md를 자동으로 생성 및 업데이트하는 역할을 합니다.

### 주요 기능

1. 프로젝트 디렉토리 내의 주요 파일들을 찾아냅니다.
2. 파일 내용을 바탕으로 Claude AI API를 이용해 README.md를 생성합니다.
3. 생성된 README.md를 저장하고 변경 사항을 CHANGELOG.md에 기록합니다.

### 주요 함수

- `read_file_contents(file_path)`: 지정된 파일의 내용을 읽어 반환합니다.
- `write_file_contents(file_path, content)`: 지정된 파일에 내용을 씁니다.
- `get_project_files(root_dir)`: 프로젝트의 주요 파일들을 찾아 내용을 반환합니다.
- `retry_on_rate_limit(func, max_retries=3, wait_time=60)`: API 요청 제한 처리를 위한 데코레이터입니다.
- `update_readme(project_files)`: Claude AI를 이용해 README.md를 생성 또는 업데이트합니다.
- `update_changelog(changes)`: CHANGELOG.md 파일을 업데이트합니다.
- `generate_changelog_message(old_content, new_content)`: README.md의 변경 사항을 분석하여 CHANGELOG.md에 추가할 메시지를 생성합니다.
- `main()`: 전체 프로세스를 조율하는 메인 함수입니다.

### 사용 방법

1. `dexius_brachion.py` 프로그램을 실행합니다.

```
poetry run python dexius/dexius_brachion.py
```

2. 스크립트가 프로젝트의 주요 파일들을 분석하고 README.md와 CHANGELOG.md를 업데이트합니다.
3. 업데이트된 파일들을 확인하고 필요에 따라 추가 수정을 진행합니다.

자세한 내용은 `dexius_brachion_manual.md` 파일을 참조하세요.

### 에러 처리 및 예외 상황

- `retry_on_rate_limit` 데코레이터를 사용하여 API 요청 제한 오류를 처리합니다.
- 파일 읽기/쓰기 작업에서 발생할 수 있는 예외를 처리합니다.

### 성능 최적화

- 병렬 처리를 통해 파일 읽기 속도를 향상시킬 수 있습니다.
- 대용량 파일 처리를 위해 청크 단위로 읽고 쓰는 방식을 고려할 수 있습니다.

## 기타 세부 정보

- 이 프로젝트는 Python 3.8 이상을 필요로 합니다.
- `pyproject.toml` 파일에는 프로젝트의 의존성과 빌드 설정이 포함되어 있습니다.
- `.github/workflows/startpack-docker-image-publish.yaml` 파일은 GitHub Actions를 사용하여 Docker 이미지를 빌드하고 배포하는 워크플로우를 정의합니다.
- `docker/` 디렉토리의 Dockerfile은 프로젝트의 Docker 이미지를 정의합니다.
- `startpack/configs.py` 파일은 환경 변수를 로드하고 접근할 수 있는 방법을 제공합니다.
- `startpack/version.py` 파일은 패키지의 버전 정보를 관리하는 함수를 포함합니다.

이 프로젝트에 대한 추가 정보나 질문이 있는 경우 프로젝트 소유자에게 연락하시기 바랍니다.
