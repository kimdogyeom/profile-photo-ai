"""
로깅 헬퍼 모듈

구조화된 JSON 로그를 출력하여 CloudWatch Logs에서 쉽게 검색하고
Metric Filter로 알람을 설정할 수 있도록 합니다.

사용 예시:
    from logging_helper import StructuredLogger
    
    log = StructuredLogger('MyFunction', context.request_id)
    log.info('user_created', userId='abc123', email='user@example.com')
    log.error('api_failed', error=exception, retryCount=3)
"""

import json
import logging
import os
import re
from datetime import datetime
from typing import Optional, Dict, Any

# 로거 초기화
logger = logging.getLogger()

# 환경 변수에서 로그 레벨 설정 (기본값: INFO)
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))


class StructuredLogger:
    """
    구조화된 JSON 로그를 출력하는 로거
    
    모든 로그는 다음 구조를 따릅니다:
    {
        "timestamp": "2024-01-15T10:30:00.123Z",
        "level": "INFO|WARNING|ERROR",
        "event": "event_name",
        "context": { 
            "userId": "...",
            "jobId": "...",
            ... (개발자가 전달한 비즈니스 데이터)
        },
        "metadata": {
            "functionName": "ImageProcessFunction",
            "requestId": "req_123",
            "region": "ap-northeast-2"
        }
    }
    """
    
    def __init__(self, function_name: str, request_id: Optional[str] = None):
        """
        로거 초기화
        
        Args:
            function_name: Lambda 함수 이름
            request_id: Lambda 요청 ID (context.request_id)
        """
        self.function_name = function_name
        self.request_id = request_id or 'local'
        self.region = os.environ.get('AWS_REGION', 'ap-northeast-2')
    
    def _validate_event_name(self, event: str) -> None:
        """
        이벤트 이름 검증 (snake_case만 허용)
        
        Args:
            event: 이벤트 이름
            
        Raises:
            ValueError: 이벤트 이름이 snake_case가 아닌 경우
        """
        if not re.match(r'^[a-z][a-z0-9_]*$', event):
            raise ValueError(
                f"Invalid event name: '{event}'. "
                f"Event names must be snake_case (lowercase letters, numbers, and underscores)"
            )
    
    def _sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Context 데이터를 JSON 직렬화 가능한 형태로 변환
        
        Args:
            context: Context 데이터
            
        Returns:
            JSON 직렬화 가능한 Context 데이터
        """
        sanitized = {}
        for key, value in context.items():
            # Primitive 타입은 그대로 유지
            if isinstance(value, (str, int, float, bool, type(None))):
                sanitized[key] = value
            # 리스트/딕셔너리는 재귀적으로 처리
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_context(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_context(item) if isinstance(item, dict) else item
                    for item in value
                ]
            # 그 외는 문자열로 변환
            else:
                sanitized[key] = str(value)
        
        return sanitized
    
    def _log(self, level: str, event: str, context: Dict[str, Any], 
             metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        내부 로그 메서드
        
        Args:
            level: 로그 레벨 (INFO, WARNING, ERROR)
            event: 이벤트 이름
            context: 비즈니스 데이터
            metadata: 추가 메타데이터
        """
        # 이벤트 이름 검증
        self._validate_event_name(event)
        
        # Context 데이터 정제
        sanitized_context = self._sanitize_context(context)
        
        # 로그 엔트리 생성
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "event": event,
            "context": sanitized_context,
            "metadata": {
                "functionName": self.function_name,
                "requestId": self.request_id,
                "region": self.region,
                **(metadata or {})
            }
        }
        
        # JSON 직렬화 (ensure_ascii=False로 한글 지원)
        log_message = json.dumps(log_entry, ensure_ascii=False, default=str)
        
        # 로그 레벨에 따라 출력
        if level == "ERROR":
            logger.error(log_message)
        elif level == "WARNING":
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    def info(self, event: str, **context) -> None:
        """
        INFO 레벨 로그 출력
        
        정상적인 작업 흐름을 기록합니다.
        
        Args:
            event: 이벤트 이름 (snake_case)
            **context: 비즈니스 데이터 (키워드 인자)
            
        Example:
            log.info('job_created', 
                userId='abc123', 
                jobId='job_xyz',
                style='professional')
        """
        self._log("INFO", event, context)
    
    def warning(self, event: str, **context) -> None:
        """
        WARNING 레벨 로그 출력
        
        재시도 가능한 오류나 주의가 필요한 상황을 기록합니다.
        
        Args:
            event: 이벤트 이름 (snake_case)
            **context: 비즈니스 데이터 (키워드 인자)
            
        Example:
            log.warning('api_timeout',
                jobId='job_xyz',
                retryCount=2,
                responseTime=35000)
        """
        self._log("WARNING", event, context)
    
    def error(self, event: str, error: Optional[Exception] = None, **context) -> None:
        """
        ERROR 레벨 로그 출력
        
        실패한 작업이나 재시도 불가능한 오류를 기록합니다.
        error 파라미터를 전달하면 errorType과 errorMessage가 자동으로 추가됩니다.
        
        Args:
            event: 이벤트 이름 (snake_case)
            error: Exception 객체 (선택 사항)
            **context: 비즈니스 데이터 (키워드 인자)
            
        Example:
            try:
                result = call_api()
            except APIError as e:
                log.error('api_failed', 
                    error=e,  # errorType, errorMessage 자동 추가
                    jobId='job_xyz',
                    retryCount=3)
        """
        # 에러 정보 자동 추출
        if error:
            context['errorType'] = type(error).__name__
            context['errorMessage'] = str(error)
            
            # 스택 트레이스 추가 (디버그 모드에서만)
            if LOG_LEVEL == 'DEBUG':
                import traceback
                context['stackTrace'] = traceback.format_exc()
        
        self._log("ERROR", event, context)
    
    def debug(self, event: str, **context) -> None:
        """
        DEBUG 레벨 로그 출력 (개발 환경에서만 사용)
        
        상세한 디버깅 정보를 기록합니다.
        LOG_LEVEL이 DEBUG가 아니면 출력되지 않습니다.
        
        Args:
            event: 이벤트 이름 (snake_case)
            **context: 비즈니스 데이터 (키워드 인자)
            
        Example:
            log.debug('api_request_details',
                url='https://api.example.com',
                headers={'Content-Type': 'application/json'},
                body={'key': 'value'})
        """
        if LOG_LEVEL == 'DEBUG':
            self._log("DEBUG", event, context)


# 편의 함수: Lambda 핸들러에서 빠르게 로거 생성
def get_logger(function_name: str, context=None) -> StructuredLogger:
    """
    Lambda 핸들러에서 로거를 쉽게 생성하는 헬퍼 함수
    
    Args:
        function_name: Lambda 함수 이름
        context: Lambda context 객체 (선택 사항)
        
    Returns:
        StructuredLogger 인스턴스
        
    Example:
        def lambda_handler(event, context):
            log = get_logger('MyFunction', context)
            log.info('handler_started')
    """
    request_id = context.request_id if context else None
    return StructuredLogger(function_name, request_id)


# 로그 레벨 확인 함수
def is_debug_enabled() -> bool:
    """
    DEBUG 모드가 활성화되어 있는지 확인
    
    Returns:
        DEBUG 모드 활성화 여부
    """
    return LOG_LEVEL == 'DEBUG'


def is_log_level_enabled(level: str) -> bool:
    """
    특정 로그 레벨이 활성화되어 있는지 확인
    
    Args:
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR)
        
    Returns:
        해당 로그 레벨 활성화 여부
    """
    level_priority = {
        'DEBUG': 0,
        'INFO': 1,
        'WARNING': 2,
        'ERROR': 3
    }
    
    current_priority = level_priority.get(LOG_LEVEL, 1)
    target_priority = level_priority.get(level.upper(), 1)
    
    return target_priority >= current_priority
