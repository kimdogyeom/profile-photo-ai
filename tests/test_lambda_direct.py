#!/usr/bin/env python3
"""
SAM Local 없이 Lambda 함수 직접 테스트
DynamoDB 의존성 없이 Lambda 로직만 검증
"""

import sys
import os
import json
import pytest
from unittest.mock import Mock, patch, MagicMock

# 환경 변수 설정 (import 전에 먼저 설정)
os.environ['UPLOAD_BUCKET'] = 'profile-photo-ai-uploads-raw-dev'
os.environ['RESULT_BUCKET'] = 'profile-photo-ai-results-final-dev'
os.environ['PRESIGNED_URL_EXPIRATION'] = '3600'
os.environ['AWS_DEFAULT_REGION'] = 'ap-northeast-2'
os.environ['Profile-Photo-AI-Users-Table'] = 'Profile-Photo-AI-Users-dev'
os.environ['Profile-Photo-AI-UsageLog-Table'] = 'Profile-Photo-AI-UsageLog-dev'
os.environ['Profile-Photo-AI-ImageJobs-Table'] = 'Profile-Photo-AI-ImageJobs-dev'
os.environ['SQS_QUEUE_URL'] = 'http://localhost:4566/000000000000/Profile-Photo-AI-ImageProcess-dev'
os.environ['DAILY_LIMIT'] = '10'

# Lambda Layer 경로를 sys.path에 추가 (/opt/python 시뮬레이션)
layers_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'layers')
if layers_path not in sys.path:
    sys.path.insert(0, layers_path)

# Lambda 함수 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'lambda', 'file_transfer'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'lambda', 'api'))


@pytest.fixture(autouse=True)
def mock_aws_services():
    """AWS 서비스를 모킹하여 실제 AWS 호출 방지"""
    with patch('boto3.client') as mock_boto_client:
        # S3 클라이언트 모킹
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = 'https://s3.amazonaws.com/test-bucket/presigned-url?signature=xyz'
        mock_s3.head_object.return_value = {'ContentLength': 512000}
        
        # SQS 클라이언트 모킹
        mock_sqs = MagicMock()
        mock_sqs.send_message.return_value = {'MessageId': 'test-message-123'}
        
        # DynamoDB 리소스 모킹
        mock_dynamodb = MagicMock()
        
        # boto3.client() 호출 시 서비스별로 다른 mock 반환
        def client_factory(service_name, **kwargs):
            if service_name == 's3':
                return mock_s3
            elif service_name == 'sqs':
                return mock_sqs
            elif service_name == 'dynamodb':
                return mock_dynamodb
            return MagicMock()
        
        mock_boto_client.side_effect = client_factory
        
        # boto3.resource도 모킹
        with patch('boto3.resource') as mock_boto_resource:
            mock_boto_resource.return_value = mock_dynamodb
            yield {
                'client': mock_boto_client,
                'resource': mock_boto_resource,
                's3': mock_s3,
                'sqs': mock_sqs,
                'dynamodb': mock_dynamodb
            }


def test_file_transfer_presigned_url_generation(mock_aws_services):
    """FileTransfer Lambda - Presigned URL 생성 테스트"""
    from file_transfer import lambda_handler
    
    # 테스트 이벤트
    event = {
        "body": json.dumps({
            "fileName": "test.jpg",
            "fileSize": 512000,
            "contentType": "image/jpeg"
        }),
        "requestContext": {
            "http": {
                "method": "POST",
                "path": "/upload"
            },
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "test-user-123",
                        "email": "test@example.com",
                        "name": "Test User"
                    }
                }
            }
        },
        "headers": {
            "Content-Type": "application/json"
        }
    }
    
    # Lambda 호출
    response = lambda_handler(event, None)
    
    # 응답 검증
    assert response['statusCode'] == 200
    assert 'body' in response
    
    body = json.loads(response['body'])
    assert 'uploadUrl' in body
    assert 'fileKey' in body
    assert 'bucket' in body
    assert 'expiresIn' in body
    
    # S3 클라이언트가 호출되었는지 확인
    mock_aws_services['s3'].generate_presigned_url.assert_called_once()


def test_file_transfer_invalid_file_type(mock_aws_services):
    """FileTransfer Lambda - 잘못된 파일 타입 거부 테스트"""
    from file_transfer import lambda_handler
    
    event = {
        "body": json.dumps({
            "fileName": "test.pdf",  # PDF는 허용되지 않음
            "fileSize": 512000,
            "contentType": "application/pdf"
        }),
        "requestContext": {
            "http": {"method": "POST", "path": "/upload"},
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "test-user-123",
                        "email": "test@example.com"
                    }
                }
            }
        }
    }
    
    response = lambda_handler(event, None)
    
    # 400 에러 반환 확인
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'error' in body


def test_file_transfer_file_too_large(mock_aws_services):
    """FileTransfer Lambda - 파일 크기 초과 거부 테스트"""
    from file_transfer import lambda_handler
    
    event = {
        "body": json.dumps({
            "fileName": "test.jpg",
            "fileSize": 20 * 1024 * 1024,  # 20MB (10MB 제한 초과)
            "contentType": "image/jpeg"
        }),
        "requestContext": {
            "http": {"method": "POST", "path": "/upload"},
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "test-user-123",
                        "email": "test@example.com"
                    }
                }
            }
        }
    }
    
    response = lambda_handler(event, None)
    
    # 400 에러 반환 확인
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'error' in body


def test_api_manager_extract_user_id():
    """ApiManager - 사용자 ID 추출 테스트"""
    from api_manager import extract_user_id
    
    # JWT authorizer 테스트
    event = {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "test-user-123"
                    }
                }
            }
        }
    }
    
    user_id = extract_user_id(event)
    assert user_id == "test-user-123"
    
    # Lambda authorizer 테스트
    event2 = {
        "requestContext": {
            "authorizer": {
                "principalId": "test-user-456"
            }
        }
    }
    
    user_id2 = extract_user_id(event2)
    assert user_id2 == "test-user-456"


def test_api_manager_extract_user_data():
    """ApiManager - 사용자 데이터 추출 테스트"""
    from api_manager import extract_user_data
    
    event = {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "test-user-123",
                        "email": "test@example.com",
                        "name": "Test User"
                    }
                }
            }
        }
    }
    
    user_data = extract_user_data(event)
    
    assert user_data['userId'] == "test-user-123"
    assert user_data['email'] == "test@example.com"
    assert user_data['displayName'] == "Test User"


def test_api_manager_cors_response():
    """ApiManager - CORS 응답 생성 테스트"""
    from api_manager import cors_response
    
    response = cors_response(200, {"message": "success"})
    
    assert response['statusCode'] == 200
    assert 'headers' in response
    assert 'Access-Control-Allow-Origin' in response['headers']
    assert 'Access-Control-Allow-Headers' in response['headers']
    assert 'Access-Control-Allow-Methods' in response['headers']
    
    body = json.loads(response['body'])
    assert body['message'] == "success"


def test_dynamodb_helper_import():
    """dynamodb_helper 모듈 import 테스트"""
    try:
        from dynamodb_helper import UserService, UsageService, ImageJobService
        
        # 클래스가 정의되어 있는지 확인
        assert UserService is not None
        assert UsageService is not None
        assert ImageJobService is not None
        
    except ImportError as e:
        pytest.fail(f"dynamodb_helper import failed: {e}")


if __name__ == "__main__":
    # pytest를 프로그래밍 방식으로 실행
    pytest.main([__file__, '-v', '--tb=short'])
