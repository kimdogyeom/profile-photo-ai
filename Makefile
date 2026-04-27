.PHONY: help frontend-install frontend-build lambda-build tf-fmt bootstrap-apply bootstrap-write-backends tf-bootstrap tf-bootstrap-dev tf-bootstrap-prod tf-validate-dev tf-validate-prod tf-plan-dev tf-plan-prod tf-apply-dev tf-apply-prod tf-destroy-dev tf-destroy-prod deploy-frontend-dev deploy-frontend-prod clean test lint

ENV ?= dev

help: ## 사용 가능한 명령어 출력
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-24s\033[0m %s\n", $$1, $$2}'

frontend-install: ## 프론트엔드 의존성 설치
	cd frontend && npm ci

frontend-build: ## 프론트엔드 프로덕션 빌드
	cd frontend && npm run build

lambda-build: ## Lambda zip 아티팩트 빌드
	./scripts/build-lambdas.sh

bootstrap-apply: ## Terraform bootstrap 스택 적용
	./scripts/bootstrap-tf-backend.sh apply

bootstrap-write-backends: ## bootstrap output으로 backend.hcl 생성
	./scripts/bootstrap-tf-backend.sh write-backend all

tf-bootstrap: ## Terraform backend 초기화 또는 backend.hcl 생성
	./scripts/bootstrap-tf-backend.sh write-backend $(ENV)
	./scripts/tf.sh init $(ENV)

tf-bootstrap-dev: ## dev Terraform backend 초기화 또는 backend.hcl 생성
	./scripts/bootstrap-tf-backend.sh write-backend dev
	./scripts/tf.sh init dev

tf-bootstrap-prod: ## prod Terraform backend 초기화 또는 backend.hcl 생성
	./scripts/bootstrap-tf-backend.sh write-backend prod
	./scripts/tf.sh init prod

tf-fmt: ## Terraform 포맷 정리
	terraform -chdir=terraform/bootstrap fmt -recursive
	terraform -chdir=terraform/envs/dev fmt -recursive
	terraform -chdir=terraform/envs/prod fmt -recursive

tf-validate-dev: ## dev Terraform 설정 검증
	terraform -chdir=terraform/envs/dev init -backend=false >/dev/null
	terraform -chdir=terraform/envs/dev validate

tf-validate-prod: ## prod Terraform 설정 검증
	terraform -chdir=terraform/envs/prod init -backend=false >/dev/null
	terraform -chdir=terraform/envs/prod validate

tf-plan-dev: ## dev Terraform plan
	./scripts/tf.sh plan dev

tf-plan-prod: ## prod Terraform plan
	./scripts/tf.sh plan prod

tf-apply-dev: ## dev Terraform apply
	./scripts/tf.sh apply dev

tf-apply-prod: ## prod Terraform apply
	./scripts/tf.sh apply prod

tf-destroy-dev: ## dev Terraform destroy
	./scripts/tf.sh destroy dev

tf-destroy-prod: ## prod Terraform destroy
	./scripts/tf.sh destroy prod

deploy-frontend-dev: ## dev 프론트엔드 배포
	./scripts/deploy-frontend.sh dev

deploy-frontend-prod: ## prod 프론트엔드 배포
	./scripts/deploy-frontend.sh prod

test: ## 백엔드/프론트엔드 테스트 실행
	python -m pytest -q tests/unit tests/integration
	cd frontend && npm run test:ci

lint: ## Python 및 Terraform 정적 점검
	python -m compileall backend tests
	if command -v flake8 >/dev/null 2>&1; then \
		flake8 backend/common backend/lambda/api backend/lambda/file_transfer backend/lambda/process tests --max-line-length=120 --extend-ignore=E203,E266,E501; \
	else \
		echo "flake8 is not installed; compileall check only"; \
	fi
	terraform -chdir=terraform/bootstrap fmt -check -recursive
	terraform -chdir=terraform/envs/dev fmt -check -recursive
	terraform -chdir=terraform/envs/prod fmt -check -recursive

clean: ## 빌드 산출물 정리
	rm -rf dist frontend/build
	find backend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
