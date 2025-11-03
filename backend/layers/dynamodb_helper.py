import boto3
import uuid
import time
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, List

# DynamoDB 클라이언트 초기화 (LocalStack 지원)
endpoint_url = os.environ.get('AWS_ENDPOINT_URL')
region_name = os.environ.get('AWS_REGION', 'ap-northeast-2')

if endpoint_url:
    print(f"Using LocalStack DynamoDB endpoint: {endpoint_url}")
    dynamodb = boto3.resource('dynamodb', 
                              region_name=region_name,
                              endpoint_url=endpoint_url)
else:
    print(f"Using AWS DynamoDB in region: {region_name}")
    dynamodb = boto3.resource('dynamodb', region_name=region_name)

# 테이블 참조
users_table = dynamodb.Table(os.environ.get('USERS_TABLE'))
usage_log_table = dynamodb.Table(os.environ.get('USAGE_LOG_TABLE'))
image_jobs_table = dynamodb.Table(os.environ.get('IMAGE_JOBS_TABLE'))

class UserService:
    """사용자 관리 서비스"""

    @staticmethod
    def create_or_update_user(user_data: Dict) -> Dict:
        """사용자 생성 또는 업데이트"""
        user_id = user_data['userId']

        item = {
            'userId': user_id,
            'email': user_data['email'],
            'provider': user_data.get('provider', 'google'),
            'displayName': user_data.get('displayName', ''),
            'profileImage': user_data.get('profileImage', ''),
            'lastLoginAt': datetime.utcnow().isoformat(),
        }

        # 새 사용자인 경우 추가 필드
        try:
            response = users_table.get_item(Key={'userId': user_id})
            if 'Item' not in response:
                item['createdAt'] = datetime.utcnow().isoformat()
                item['totalImagesGenerated'] = 0
        except Exception:
            item['createdAt'] = datetime.utcnow().isoformat()
            item['totalImagesGenerated'] = 0

        users_table.put_item(Item=item)
        return item

    @staticmethod
    def get_user(user_id: str) -> Optional[Dict]:
        """사용자 정보 조회"""
        try:
            response = users_table.get_item(Key={'userId': user_id})
            return response.get('Item')
        except Exception as e:
            print(f"Error getting user: {e}")
            return None

    @staticmethod
    def increment_total_images(user_id: str):
        """총 생성 이미지 수 증가"""
        users_table.update_item(
            Key={'userId': user_id},
            UpdateExpression='SET totalImagesGenerated = if_not_exists(totalImagesGenerated, :zero) + :inc',
            ExpressionAttributeValues={
                ':inc': 1,
                ':zero': 0
            }
        )

class UsageService:
    """사용량 관리 서비스"""

    DAILY_LIMIT = int(os.environ.get('DAILY_LIMIT'))

    @staticmethod
    def get_today_usage(user_id: str) -> int:
        """오늘 사용량 조회"""
        today = datetime.utcnow().strftime('%Y-%m-%d')
        user_id_date = f"{user_id}#{today}"

        try:
            response = usage_log_table.get_item(Key={'userIdDate': user_id_date})
            if 'Item' in response:
                return int(response['Item'].get('count', 0))
            return 0
        except Exception as e:
            print(f"Error getting usage: {e}")
            return 0

    @staticmethod
    def can_generate_image(user_id: str) -> tuple[bool, int]:
        """이미지 생성 가능 여부 확인

        Returns:
            (가능 여부, 남은 횟수)
        """
        current_usage = UsageService.get_today_usage(user_id)
        remaining = UsageService.DAILY_LIMIT - current_usage
        return remaining > 0, remaining

    @staticmethod
    def increment_usage(user_id: str) -> int:
        """사용량 증가 및 현재 사용량 반환"""
        today = datetime.utcnow().strftime('%Y-%m-%d')
        user_id_date = f"{user_id}#{today}"

        # TTL 설정 (90일 후)
        ttl = int((datetime.utcnow() + timedelta(days=90)).timestamp())

        response = usage_log_table.update_item(
            Key={'userIdDate': user_id_date},
            UpdateExpression='SET #count = if_not_exists(#count, :zero) + :inc, '
                             'userId = :userId, #date = :date, '
                             'lastUpdated = :lastUpdated, #ttl = :ttl',
            ExpressionAttributeNames={
                '#count': 'count',
                '#date': 'date',
                '#ttl': 'ttl'
            },
            ExpressionAttributeValues={
                ':inc': 1,
                ':zero': 0,
                ':userId': user_id,
                ':date': today,
                ':lastUpdated': datetime.utcnow().isoformat(),
                ':ttl': ttl
            },
            ReturnValues='UPDATED_NEW'
        )

        return int(response['Attributes']['count'])

    @staticmethod
    def get_usage_history(user_id: str, days: int = 7) -> List[Dict]:
        """최근 사용 이력 조회"""
        try:
            response = usage_log_table.query(
                IndexName='UserIdIndex',
                KeyConditionExpression='userId = :userId',
                ExpressionAttributeValues={':userId': user_id},
                ScanIndexForward=False,
                Limit=days
            )
            return response.get('Items', [])
        except Exception as e:
            print(f"Error getting usage history: {e}")
            return []

class ImageJobService:
    """이미지 작업 관리 서비스"""

    @staticmethod
    def create_job(user_id: str, style: str, input_url: str, prompt: str) -> str:
        """새 이미지 작업 생성"""
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        timestamp = datetime.utcnow().isoformat() + 'Z'

        item = {
            'jobId': job_id,
            'userId': user_id,
            'status': 'pending',
            'style': style,
            'inputImageUrl': input_url,
            'prompt': prompt,
            'createdAt': timestamp,
            'updatedAt': timestamp
        }

        image_jobs_table.put_item(Item=item)
        return job_id

    @staticmethod
    def update_job_status(job_id: str, status: str, **kwargs):
        """작업 상태 업데이트"""
        update_expression = 'SET #status = :status, updatedAt = :updatedAt'
        expression_values = {
            ':status': status,
            ':updatedAt': datetime.utcnow().isoformat() + 'Z'
        }
        expression_names = {'#status': 'status'}

        # 추가 필드 업데이트
        if 'output_url' in kwargs:
            update_expression += ', outputImageUrl = :outputUrl'
            expression_values[':outputUrl'] = kwargs['output_url']

        if 'error' in kwargs:
            update_expression += ', #error = :error'
            expression_values[':error'] = kwargs['error']
            expression_names['#error'] = 'error'

        if 'processing_time' in kwargs:
            update_expression += ', processingTime = :processingTime'
            expression_values[':processingTime'] = Decimal(str(kwargs['processing_time']))

        if 'metadata' in kwargs:
            update_expression += ', metadata = :metadata'
            # metadata 내부의 float 값들을 Decimal로 변환
            metadata = kwargs['metadata']
            converted_metadata = {}
            for key, value in metadata.items():
                if isinstance(value, float):
                    converted_metadata[key] = Decimal(str(value))
                else:
                    converted_metadata[key] = value
            expression_values[':metadata'] = converted_metadata

        image_jobs_table.update_item(
            Key={'jobId': job_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values
        )

    @staticmethod
    def get_job(job_id: str) -> Optional[Dict]:
        """작업 정보 조회"""
        try:
            response = image_jobs_table.get_item(Key={'jobId': job_id})
            return response.get('Item')
        except Exception as e:
            print(f"Error getting job: {e}")
            return None

    @staticmethod
    def get_user_jobs(user_id: str, limit: int = 20, status: str = None, last_evaluated_key: Dict = None) -> Dict:
        """사용자의 작업 목록 조회 (최신순, 상태 필터 및 페이지네이션 지원)
        
        Args:
            user_id: 사용자 ID
            limit: 페이지당 결과 수 (기본값: 20)
            status: 상태 필터 (None이면 전체, 'completed', 'failed' 등)
            last_evaluated_key: 페이지네이션을 위한 마지막 키
        
        Returns:
            {
                'jobs': [...],
                'lastEvaluatedKey': {...} or None
            }
        """
        try:
            query_params = {
                'IndexName': 'UserIdCreatedAtIndex',
                'KeyConditionExpression': 'userId = :userId',
                'ExpressionAttributeValues': {':userId': user_id},
                'ScanIndexForward': False,  # 최신순 정렬
                'Limit': limit
            }
            
            # 상태 필터 추가
            if status and status != 'all':
                query_params['FilterExpression'] = '#status = :status'
                query_params['ExpressionAttributeNames'] = {'#status': 'status'}
                query_params['ExpressionAttributeValues'][':status'] = status
            
            # 페이지네이션
            if last_evaluated_key:
                query_params['ExclusiveStartKey'] = last_evaluated_key
            
            response = image_jobs_table.query(**query_params)
            
            return {
                'jobs': response.get('Items', []),
                'lastEvaluatedKey': response.get('LastEvaluatedKey')
            }
        except Exception as e:
            print(f"Error getting user jobs: {e}")
            return {'jobs': [], 'lastEvaluatedKey': None}

    @staticmethod
    def get_jobs_by_status(status: str, limit: int = 100) -> List[Dict]:
        """상태별 작업 조회 (관리자용)"""
        try:
            response = image_jobs_table.query(
                IndexName='StatusIndex',
                KeyConditionExpression='#status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':status': status},
                ScanIndexForward=False,
                Limit=limit
            )
            return response.get('Items', [])
        except Exception as e:
            print(f"Error getting jobs by status: {e}")
            return []
