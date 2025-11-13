#!/usr/bin/env python3
"""
Phase 3 통합 테스트 스크립트
LocalStack + SAM Local 환경에서 전체 플로우 테스트
"""

import json
import time
import requests
import boto3
from pathlib import Path

# 설정
API_BASE_URL = "http://localhost:3001"
LOCALSTACK_ENDPOINT = "http://localhost:4566"
AWS_REGION = "ap-northeast-2"
TEST_IMAGE_PATH = "tests/test-data/test-image.jpg"

# LocalStack용 AWS 클라이언트
s3_client = boto3.client(
    's3',
    endpoint_url=LOCALSTACK_ENDPOINT,
    aws_access_key_id='test',
    aws_secret_access_key='test',
    region_name=AWS_REGION
)

dynamodb = boto3.resource(
    'dynamodb',
    endpoint_url=LOCALSTACK_ENDPOINT,
    aws_access_key_id='test',
    aws_secret_access_key='test',
    region_name=AWS_REGION
)

sqs_client = boto3.client(
    'sqs',
    endpoint_url=LOCALSTACK_ENDPOINT,
    aws_access_key_id='test',
    aws_secret_access_key='test',
    region_name=AWS_REGION
)


def print_header(title):
    """테스트 섹션 헤더 출력"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)


def print_result(test_name, success, details=""):
    """테스트 결과 출력"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} - {test_name}")
    if details:
        print(f"     {details}")


def test_3_1_presigned_url():
    """Phase 3.1: S3 Presigned URL 테스트"""
    print_header("Phase 3.1: S3 Presigned URL 테스트")
    
    try:
        # 1. /upload API 호출
        print("\n1️⃣ Presigned URL 요청...")
        response = requests.post(
            f"{API_BASE_URL}/upload",
            json={
                "fileName": "test-image.jpg",
                "fileSize": 512000,
                "contentType": "image/jpeg"
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer dummy-token"
            }
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ uploadUrl: {data.get('uploadUrl', '')[:50]}...")
            print(f"   ✓ fileKey: {data.get('fileKey')}")
            print(f"   ✓ bucket: {data.get('bucket')}")
            
            upload_url = data.get('uploadUrl')
            file_key = data.get('fileKey')
            
            # 2. Presigned URL로 파일 업로드
            print("\n2️⃣ S3에 파일 업로드...")
            with open(TEST_IMAGE_PATH, 'rb') as f:
                upload_response = requests.put(
                    upload_url,
                    data=f,
                    headers={"Content-Type": "image/jpeg"}
                )
            
            print(f"   Upload Status: {upload_response.status_code}")
            print_result("Presigned URL 업로드", upload_response.status_code == 200)
            
            # 3. S3에서 파일 확인
            print("\n3️⃣ LocalStack S3에서 파일 확인...")
            try:
                bucket_name = data.get('bucket', 'profile-photo-ai-uploads-raw-dev')
                obj = s3_client.head_object(Bucket=bucket_name, Key=file_key)
                print(f"   ✓ 파일 크기: {obj['ContentLength']} bytes")
                print(f"   ✓ Content-Type: {obj.get('ContentType')}")
                print_result("S3 파일 존재 확인", True)
                
                return True, file_key
            except Exception as e:
                print(f"   ✗ S3 확인 실패: {e}")
                print_result("S3 파일 존재 확인", False, str(e))
                return False, None
        else:
            print(f"   응답: {response.text}")
            print_result("Presigned URL 생성", False, f"HTTP {response.status_code}")
            return False, None
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print_result("전체 테스트", False, str(e))
        return False, None


def test_3_2_image_generation():
    """Phase 3.2: 이미지 생성 플로우 테스트"""
    print_header("Phase 3.2: 이미지 생성 플로우 테스트")
    
    # 이전 테스트에서 file_key 가져오기
    result, file_key = test_3_1_presigned_url()
    if not file_key:
        print("⚠️ file_key가 없어 테스트 건너뜀")
        return False
    
    try:
        # 1. 이미지 생성 요청
        print("\n1️⃣ 이미지 생성 요청...")
        response = requests.post(
            f"{API_BASE_URL}/generate",
            json={
                "fileKey": file_key,
                "prompt": "Create a professional profile photo with clean background"
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer dummy-token"
            }
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            job_id = data.get('jobId')
            print(f"   ✓ jobId: {job_id}")
            print(f"   ✓ status: {data.get('status')}")
            print(f"   ✓ remainingQuota: {data.get('remainingQuota')}")
            print_result("이미지 생성 요청", True)
            
            # 2. SQS 메시지 확인
            print("\n2️⃣ SQS 메시지 확인...")
            try:
                queue_url = f"{LOCALSTACK_ENDPOINT}/000000000000/Profile-Photo-AI-ImageProcess-dev"
                messages = sqs_client.receive_message(
                    QueueUrl=queue_url,
                    MaxNumberOfMessages=1,
                    WaitTimeSeconds=2
                )
                
                if 'Messages' in messages:
                    message = messages['Messages'][0]
                    body = json.loads(message['Body'])
                    print(f"   ✓ SQS 메시지 수신")
                    print(f"   ✓ jobId: {body.get('jobId')}")
                    print(f"   ✓ userId: {body.get('userId')}")
                    print_result("SQS 메시지 발행", True)
                else:
                    print("   ✗ SQS 메시지 없음")
                    print_result("SQS 메시지 발행", False, "메시지 없음")
            except Exception as e:
                print(f"   ✗ SQS 확인 실패: {e}")
                print_result("SQS 메시지 확인", False, str(e))
            
            return True, job_id
        else:
            print(f"   응답: {response.text}")
            print_result("이미지 생성 요청", False, f"HTTP {response.status_code}")
            return False, None
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print_result("전체 테스트", False, str(e))
        return False, None


def test_3_3_dynamodb_data(job_id=None):
    """Phase 3.3: DynamoDB 데이터 검증"""
    print_header("Phase 3.3: DynamoDB 데이터 검증")
    
    try:
        # 1. Users 테이블 확인
        print("\n1️⃣ Users 테이블 확인...")
        users_table = dynamodb.Table('Profile-Photo-AI-Users-dev')
        try:
            response = users_table.scan(Limit=5)
            user_count = response.get('Count', 0)
            print(f"   ✓ 사용자 수: {user_count}")
            if user_count > 0:
                print(f"   ✓ 샘플 사용자: {response['Items'][0].get('userId')}")
            print_result("Users 테이블", True, f"{user_count}명")
        except Exception as e:
            print(f"   ✗ 조회 실패: {e}")
            print_result("Users 테이블", False, str(e))
        
        # 2. UsageLog 테이블 확인
        print("\n2️⃣ UsageLog 테이블 확인...")
        usage_table = dynamodb.Table('Profile-Photo-AI-UsageLog-dev')
        try:
            response = usage_table.scan(Limit=5)
            log_count = response.get('Count', 0)
            print(f"   ✓ 사용량 로그 수: {log_count}")
            if log_count > 0:
                sample = response['Items'][0]
                print(f"   ✓ 샘플: {sample.get('userIdDate')} - count: {sample.get('count')}")
            print_result("UsageLog 테이블", True, f"{log_count}개 로그")
        except Exception as e:
            print(f"   ✗ 조회 실패: {e}")
            print_result("UsageLog 테이블", False, str(e))
        
        # 3. ImageJobs 테이블 확인
        print("\n3️⃣ ImageJobs 테이블 확인...")
        jobs_table = dynamodb.Table('Profile-Photo-AI-ImageJobs-dev')
        try:
            response = jobs_table.scan(Limit=10)
            job_count = response.get('Count', 0)
            print(f"   ✓ 작업 수: {job_count}")
            
            if job_count > 0:
                for item in response['Items']:
                    print(f"   - {item.get('jobId')}: {item.get('status')}")
            
            # 특정 Job 확인
            if job_id:
                job = jobs_table.get_item(Key={'jobId': job_id})
                if 'Item' in job:
                    print(f"   ✓ Job {job_id} 상태: {job['Item'].get('status')}")
                    print_result("특정 Job 조회", True)
                else:
                    print_result("특정 Job 조회", False, "Job 없음")
            
            print_result("ImageJobs 테이블", True, f"{job_count}개 작업")
        except Exception as e:
            print(f"   ✗ 조회 실패: {e}")
            print_result("ImageJobs 테이블", False, str(e))
        
        return True
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print_result("전체 테스트", False, str(e))
        return False


def test_3_4_error_cases():
    """Phase 3.4: 에러 케이스 테스트"""
    print_header("Phase 3.4: 에러 케이스 테스트")
    
    try:
        # 1. 잘못된 파일 형식
        print("\n1️⃣ 잘못된 파일 형식 테스트...")
        response = requests.post(
            f"{API_BASE_URL}/upload",
            json={
                "fileName": "test.exe",
                "fileSize": 1000,
                "contentType": "application/x-msdownload"
            },
            headers={"Content-Type": "application/json"}
        )
        print(f"   Status: {response.status_code}")
        print_result("잘못된 파일 형식", response.status_code == 400, 
                    f"예상: 400, 실제: {response.status_code}")
        
        # 2. 존재하지 않는 파일로 생성 요청
        print("\n2️⃣ 존재하지 않는 파일 테스트...")
        response = requests.post(
            f"{API_BASE_URL}/generate",
            json={
                "fileKey": "uploads/nonexistent/file.jpg",
                "prompt": "test"
            },
            headers={"Content-Type": "application/json"}
        )
        print(f"   Status: {response.status_code}")
        print_result("존재하지 않는 파일", response.status_code == 404,
                    f"예상: 404, 실제: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print_result("전체 테스트", False, str(e))
        return False


def check_localstack_health():
    """LocalStack 상태 확인"""
    print_header("LocalStack 상태 확인")
    
    try:
        response = requests.get(f"{LOCALSTACK_ENDPOINT}/_localstack/health")
        if response.status_code == 200:
            health = response.json()
            print("   서비스 상태:")
            for service, status in health.get('services', {}).items():
                print(f"   - {service}: {status}")
            return True
        return False
    except Exception as e:
        print(f"   ✗ LocalStack 연결 실패: {e}")
        return False


def main():
    """메인 테스트 실행"""
    print("\n" + "="*60)
    print("  ProfilePhotoAI Phase 3 통합 테스트")
    print("="*60)
    
    # LocalStack 상태 확인
    if not check_localstack_health():
        print("\n⚠️ LocalStack이 실행되지 않았습니다.")
        print("   다음 명령어로 시작하세요: make localstack-start")
        return
    
    # 테스트 이미지 확인
    if not Path(TEST_IMAGE_PATH).exists():
        print(f"\n⚠️ 테스트 이미지가 없습니다: {TEST_IMAGE_PATH}")
        return
    
    print(f"\n✓ 테스트 이미지: {TEST_IMAGE_PATH}")
    
    # 테스트 실행
    results = {}
    
    # Phase 3.1
    success, file_key = test_3_1_presigned_url()
    results['3.1'] = success
    
    time.sleep(1)
    
    # Phase 3.2
    if file_key:
        success, job_id = test_3_2_image_generation(file_key)
        results['3.2'] = success
    else:
        results['3.2'] = False
        job_id = None
    
    time.sleep(1)
    
    # Phase 3.3
    results['3.3'] = test_3_3_dynamodb_data(job_id)
    
    time.sleep(1)
    
    # Phase 3.4
    results['3.4'] = test_3_4_error_cases()
    
    # 결과 요약
    print_header("테스트 결과 요약")
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for phase, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"Phase {phase}: {status}")
    
    print(f"\n총 {total}개 중 {passed}개 통과 ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 모든 테스트 통과!")
    else:
        print("\n⚠️ 일부 테스트 실패")


if __name__ == "__main__":
    main()
