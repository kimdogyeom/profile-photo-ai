#!/usr/bin/env python3
"""
Lambda 함수 로컬 테스트 스크립트 (Docker 없이)
"""

import json
import sys
import os
from pathlib import Path

# 프로젝트 루트 디렉토리 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / '.aws-sam' / 'build' / 'FileTransferFunction'))
sys.path.insert(0, str(project_root / '.aws-sam' / 'build' / 'ApiManagerFunction'))
sys.path.insert(0, str(project_root / '.aws-sam' / 'build' / 'DynamoDBHelperLayer' / 'python'))

# 환경 변수 설정
os.environ['UPLOAD_BUCKET'] = 'profilephotoai-uploads-raw-dev'
os.environ['RESULT_BUCKET'] = 'profilephotoai-results-final-dev'
os.environ['PRESIGNED_URL_EXPIRATION'] = '3600'
os.environ['AWS_DEFAULT_REGION'] = 'ap-northeast-2'

def load_test_event(event_file):
    """테스트 이벤트 JSON 파일 로드"""
    event_path = project_root / 'tests' / 'events' / event_file
    with open(event_path, 'r') as f:
        return json.load(f)

def test_file_transfer():
    """FileTransfer Lambda 테스트"""
    print("=" * 60)
    print("TEST: FileTransfer Lambda")
    print("=" * 60)
    
    try:
        import file_transfer
        
        # 테스트 이벤트 로드
        event = load_test_event('file-transfer-event.json')
        context = {}
        
        print("\n📥 입력 이벤트:")
        print(json.dumps(event, indent=2, ensure_ascii=False))
        
        # Lambda 함수 실행
        print("\n🔄 Lambda 실행 중...\n")
        response = file_transfer.lambda_handler(event, context)
        
        print("\n📤 응답:")
        print(json.dumps(response, indent=2, ensure_ascii=False))
        
        # 결과 검증
        status_code = response.get('statusCode')
        if status_code == 200:
            print("\n✅ 테스트 성공!")
            body = json.loads(response['body'])
            if 'uploadUrl' in body and 'fileKey' in body:
                print(f"   - uploadUrl 생성됨")
                print(f"   - fileKey: {body['fileKey']}")
        else:
            print(f"\n❌ 테스트 실패! (Status: {status_code})")
            
    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()

def test_api_manager():
    """ApiManager Lambda 테스트 (기본 구조만)"""
    print("\n" + "=" * 60)
    print("TEST: ApiManager Lambda")
    print("=" * 60)
    
    try:
        import api_manager
        
        # 테스트 이벤트 로드
        event = load_test_event('api-manager-event.json')
        context = {}
        
        print("\n📥 입력 이벤트:")
        body = json.loads(event.get('body', '{}'))
        print(f"   - fileKey: {body.get('fileKey')}")
        print(f"   - prompt: {body.get('prompt', '')[:50]}...")
        
        print("\n⚠️  주의: 실제 실행은 AWS 리소스(DynamoDB, SQS)가 필요합니다.")
        print("   코드 구문 검사만 수행합니다.")
        
        # 함수가 임포트되는지만 확인
        print("\n✅ Lambda 함수 임포트 성공!")
        print(f"   - lambda_handler: {hasattr(api_manager, 'lambda_handler')}")
        
    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()

def main():
    """메인 함수"""
    print("\n" + "=" * 60)
    print("ProfilePhotoAI Lambda 로컬 테스트")
    print("=" * 60)
    print(f"\nProject Root: {project_root}")
    print(f"Build Dir: {project_root / '.aws-sam' / 'build'}")
    
    # FileTransfer 테스트
    test_file_transfer()
    
    # ApiManager 테스트 (기본만)
    test_api_manager()
    
    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)
    print("\n💡 팁: 실제 AWS 리소스와 통합 테스트는 Docker + SAM Local이 필요합니다.")
    print("   Docker 설치 후: sam local invoke FileTransferFunction --event tests/events/file-transfer-event.json")

if __name__ == '__main__':
    main()
