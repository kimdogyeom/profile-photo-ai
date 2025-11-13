.PHONY: help setup build deploy clean test invoke-file invoke-api invoke-process start logs validate

# 기본 변수
STACK_NAME ?= profile-photo-ai-dev
REGION ?= ap-northeast-2
ENV ?= dev

help: ## 사용 가능한 명령어 출력
	@echo "ProfilePhotoAI - AWS SAM 명령어"
	@echo ""
	@echo "사용법: make [command]"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

validate: ## SAM 템플릿 검증
	@echo "✓ SAM 템플릿 검증 중..."
	sam validate --lint

build: ## Lambda 함수 빌드
	@echo "🔨 빌드 중..."
	sam build --parallel

build-clean: ## 클린 빌드
	@echo "🧹 클린 빌드 중..."
	rm -rf .aws-sam
	sam build --parallel

start: build ## 로컬 API 서버 시작
	@echo "🌐 로컬 API 서버 시작 (포트 3001)..."
	sam local start-api --port 3001 --env-vars env.json

start-local: build ## 로컬 API 서버 시작 (LocalStack 연동)
	@echo "🌐 로컬 API 서버 시작 (LocalStack 연동)..."
	sam local start-api --port 3001 --env-vars env-local.json --docker-network profile-photo-ai-network

start-warm: build ## Warm containers로 로컬 API 서버 시작
	@echo "🌐 로컬 API 서버 시작 (Warm containers)..."
	sam local start-api --port 3001 --env-vars .env --warm-containers EAGER

invoke-file: ## FileTransfer Lambda 테스트
	@echo "📤 FileTransfer Lambda 실행 중..."
	sam local invoke FileTransferFunction \
		--event tests/events/file-transfer-event.json \
		--env-vars .env

invoke-api: ## ApiManager Lambda 테스트
	@echo "🔄 ApiManager Lambda 실행 중..."
	sam local invoke ApiManagerFunction \
		--event tests/events/api-manager-event.json \
		--env-vars .env

invoke-process: ## ImageProcess Lambda 테스트
	@echo "🎨 ImageProcess Lambda 실행 중..."
	sam local invoke ImageProcessFunction \
		--event tests/events/sqs-event.json \
		--env-vars .env

deploy: build ## AWS에 배포
	@echo "☁️  AWS에 배포 중..."
	sam deploy --stack-name $(STACK_NAME) --region $(REGION)

deploy-guided: build ## 가이드 모드로 배포
	@echo "☁️  가이드 모드로 배포 중..."
	sam deploy --guided

logs-file: ## FileTransfer Lambda 로그 확인
	@echo "📋 FileTransfer Lambda 로그..."
	sam logs -n FileTransferFunction --tail

logs-api: ## ApiManager Lambda 로그 확인
	@echo "📋 ApiManager Lambda 로그..."
	sam logs -n ApiManagerFunction --tail

logs-process: ## ImageProcess Lambda 로그 확인
	@echo "📋 ImageProcess Lambda 로그..."
	sam logs -n ImageProcessFunction --tail

test-upload: ## 업로드 API 테스트
	@echo "🧪 업로드 API 테스트..."
	curl -X POST http://localhost:3001/upload \
		-H "Content-Type: application/json" \
		-d '{"fileName":"test.jpg","fileSize":2048000,"contentType":"image/jpeg"}'

test-generate: ## 이미지 생성 API 테스트
	@echo "🧪 이미지 생성 API 테스트..."
	curl -X POST http://localhost:3001/generate \
		-H "Content-Type: application/json" \
		-d '{"fileKey":"uploads/user123/test.jpg","prompt":"Create a professional profile photo"}'

sync: ## 변경사항 자동 동기화 (watch 모드)
	@echo "🔄 변경사항 감시 및 동기화 중..."
	sam sync --watch

clean: ## 빌드 결과물 삭제
	@echo "🧹 정리 중..."
	rm -rf .aws-sam
	rm -f packaged.yaml
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

delete-stack: ## CloudFormation 스택 삭제
	@echo "⚠️  스택 삭제 중: $(STACK_NAME)"
	@read -p "정말 삭제하시겠습니까? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		sam delete --stack-name $(STACK_NAME) --region $(REGION); \
	fi

list-resources: ## 배포된 리소스 목록
	@echo "📦 배포된 리소스 목록..."
	sam list resources --stack-name $(STACK_NAME)

list-endpoints: ## API 엔드포인트 목록
	@echo "🌐 API 엔드포인트 목록..."
	sam list endpoints --stack-name $(STACK_NAME)

layer-install: ## Layer 의존성 설치
	@echo "📚 Layer 의존성 설치 중..."
	cd backend/layers && \
	rm -rf python && \
	mkdir -p python && \
	pip install -r requirements.txt -t python/ && \
	cd ../..

docker-clean: ## Docker 리소스 정리
	@echo "🐳 Docker 정리 중..."
	docker system prune -f

init-env: ## .env 파일 생성
	@if [ ! -f .env ]; then \
		echo "📝 .env 파일 생성 중..."; \
		cp .env.local .env; \
		echo "✓ .env 파일이 생성되었습니다. API 키를 입력해주세요."; \
	else \
		echo "⚠️  .env 파일이 이미 존재합니다."; \
	fi

check: ## 환경 체크
	@echo "🔍 환경 체크 중..."
	@command -v aws >/dev/null 2>&1 && echo "✓ AWS CLI 설치됨" || echo "✗ AWS CLI 필요"
	@command -v sam >/dev/null 2>&1 && echo "✓ SAM CLI 설치됨" || echo "✗ SAM CLI 필요"
	@command -v docker >/dev/null 2>&1 && echo "✓ Docker 설치됨" || echo "✗ Docker 필요"
	@command -v python3 >/dev/null 2>&1 && echo "✓ Python3 설치됨" || echo "✗ Python3 필요"
	@[ -f env.json ] && echo "✓ env.json 파일 존재" || echo "✗ env.json 파일 필요"
	@docker info >/dev/null 2>&1 && echo "✓ Docker 실행 중" || echo "✗ Docker 실행 필요"

# ========================================
# LocalStack 관련 명령어
# ========================================

localstack-start: ## LocalStack 시작
	@echo "🚀 LocalStack 시작 중..."
	./scripts/start-local-env.sh

localstack-stop: ## LocalStack 종료
	@echo "🛑 LocalStack 종료 중..."
	./scripts/stop-local-env.sh

localstack-clean: ## LocalStack 데이터 삭제
	@echo "🗑️  LocalStack 데이터 삭제 중..."
	./scripts/stop-local-env.sh --clean

localstack-logs: ## LocalStack 로그 확인
	@echo "📋 LocalStack 로그:"
	docker-compose logs -f localstack

localstack-status: ## LocalStack 상태 확인
	@echo "🔍 LocalStack 상태:"
	@curl -s http://localhost:4566/_localstack/health | python3 -m json.tool || echo "LocalStack이 실행 중이지 않습니다."

localstack-resources: ## LocalStack 리소스 확인
	@echo "📦 LocalStack 리소스 확인:"
	@echo ""
	@echo "S3 버킷:"
	@aws --endpoint-url=http://localhost:4566 s3 ls --region ap-northeast-2 2>/dev/null || echo "  (확인 실패)"
	@echo ""
	@echo "DynamoDB 테이블:"
	@aws --endpoint-url=http://localhost:4566 dynamodb list-tables --region ap-northeast-2 --output text 2>/dev/null || echo "  (확인 실패)"
	@echo ""
	@echo "SQS 큐:"
	@aws --endpoint-url=http://localhost:4566 sqs list-queues --region ap-northeast-2 --output text 2>/dev/null || echo "  (확인 실패)"

local-env: localstack-start ## LocalStack 환경 시작 (SAM Local은 별도 실행 필요)
	@echo ""
	@echo "✅ LocalStack 준비 완료!"
	@echo ""
	@echo "📝 다음 단계:"
	@echo "   make start-local  # SAM Local API 서버 시작"

dev: check validate build start ## 개발 모드 (체크 + 검증 + 빌드 + 실행)

all: setup validate build test-local deploy ## 전체 플로우 실행

.DEFAULT_GOAL := help
