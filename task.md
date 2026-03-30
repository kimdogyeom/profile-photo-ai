# ProfilePhotoAI Migration Notes

이 문서는 현재 코드베이스의 재구축 방향과 후속 정리 항목만 남겨둡니다.

## 현재 기준 아키텍처

- 인증: Amazon Cognito User Pool direct auth (email/password)
- 이미지 생성: AWS Bedrock Nova Canvas (`amazon.nova-canvas-v1:0`)
- 인프라: Terraform (`terraform/bootstrap`, `terraform/envs/dev`, `terraform/envs/prod`)
- 비동기 처리: S3 direct upload + SQS + Lambda + DynamoDB

## 이번 마이그레이션에서 완료한 항목

- 기존 소셜 로그인 / Hosted UI / 외부 클라우드 의존성 제거
- 기존 외부 이미지 생성 연동 코드를 Bedrock Nova Canvas variation 호출로 교체
- 기존 SAM / CloudFormation 기반 배포 경로 제거
- Terraform 기반 dev/prod 환경 및 bootstrap state 스택 추가
- 업로드 권한 검증, quota 원자 차감, presigned POST 업로드 검증 강화
- 작업 이력 pagination 계약을 프론트/백엔드에서 일치시킴

## 후속 작업

- GitHub Actions 재구축
- Terraform 실계정 apply / destroy 검증
- E2E 및 백엔드 단위 테스트 재도입
- 스타일 샘플 이미지 자산 정리
  - [ ] [세부 작업 2]
  - [ ] [세부 작업 3]
- **우선순위**: [High/Medium/Low]
- **예상 소요 시간**: [시간]
- **관련 문서**: [파일 경로 또는 링크]
- **비고**: [추가 메모]
```

---

## 📌 참고사항

### 작업 진행 시 체크리스트
- [ ] 작업 시작 시 상태를 `🚧 IN_PROGRESS`로 변경
- [ ] 관련 브랜치 생성 (예: `feature/cloudwatch-monitoring`)
- [ ] 커밋 메시지에 작업 번호 포함 (예: `[Task-1] Add CloudWatch Alarms`)
- [ ] 작업 완료 시 PR 생성 및 리뷰 요청
- [ ] PR 머지 후 상태를 `✅ DONE`으로 변경
- [ ] 완료 날짜 기록

### Git 브랜치 전략
- `main`: 프로덕션 배포 브랜치
- `develop`: 개발 통합 브랜치 (선택)
- `feature/[task-name]`: 기능 개발 브랜치
- `hotfix/[issue-name]`: 긴급 수정 브랜치

### 커밋 메시지 컨벤션
```
[Task-번호] 작업 요약

- 세부 변경 사항 1
- 세부 변경 사항 2

관련 이슈: #123
```

---

---

**마지막 업데이트**: 2025-11-13
  
