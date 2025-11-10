#!/usr/bin/env python3
"""
로깅 헬퍼 단위 테스트

로깅 헬퍼의 기본 기능을 테스트합니다.
"""

import sys
import os

# Lambda Layer 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../backend/layers'))

from logging_helper import StructuredLogger, get_logger, is_debug_enabled
import json


class MockContext:
    """Lambda Context Mock"""
    def __init__(self):
        self.request_id = 'test-request-123'
        self.function_name = 'TestFunction'


def test_basic_info_log():
    """기본 INFO 로그 테스트"""
    print("\n=== Test 1: Basic INFO Log ===")
    log = StructuredLogger('TestFunction', 'req-123')
    
    log.info('user_created',
        userId='user-abc',
        email='test@example.com',
        accountType='premium')
    
    print("✅ INFO log test passed")


def test_warning_log():
    """WARNING 로그 테스트"""
    print("\n=== Test 2: WARNING Log ===")
    log = StructuredLogger('TestFunction', 'req-456')
    
    log.warning('api_slow_response',
        jobId='job-xyz',
        responseTime=35000,
        threshold=30000)
    
    print("✅ WARNING log test passed")


def test_error_log_with_exception():
    """Exception을 포함한 ERROR 로그 테스트"""
    print("\n=== Test 3: ERROR Log with Exception ===")
    log = StructuredLogger('TestFunction', 'req-789')
    
    try:
        # 의도적으로 에러 발생
        result = 1 / 0
    except ZeroDivisionError as e:
        log.error('calculation_failed',
            error=e,
            operation='division',
            operand1=1,
            operand2=0)
    
    print("✅ ERROR log with exception test passed")


def test_error_log_without_exception():
    """Exception 없는 ERROR 로그 테스트"""
    print("\n=== Test 4: ERROR Log without Exception ===")
    log = StructuredLogger('TestFunction', 'req-101')
    
    log.error('quota_exceeded',
        userId='user-abc',
        currentUsage=15,
        dailyLimit=15)
    
    print("✅ ERROR log without exception test passed")


def test_invalid_event_name():
    """잘못된 이벤트 이름 테스트"""
    print("\n=== Test 5: Invalid Event Name (should fail) ===")
    log = StructuredLogger('TestFunction', 'req-202')
    
    try:
        # CamelCase는 허용되지 않음
        log.info('UserCreated', userId='user-abc')
        print("❌ Should have raised ValueError")
    except ValueError as e:
        print(f"✅ Correctly rejected invalid event name: {e}")


def test_complex_context():
    """복잡한 Context 데이터 테스트"""
    print("\n=== Test 6: Complex Context Data ===")
    log = StructuredLogger('TestFunction', 'req-303')
    
    log.info('job_created',
        userId='user-abc',
        jobId='job-xyz',
        config={
            'style': 'professional',
            'resolution': '1024x1024',
            'format': 'png'
        },
        metadata={
            'source': 'web',
            'version': '1.0.0'
        },
        tags=['ai', 'profile', 'photo'])
    
    print("✅ Complex context data test passed")


def test_get_logger_helper():
    """get_logger 헬퍼 함수 테스트"""
    print("\n=== Test 7: get_logger Helper ===")
    
    context = MockContext()
    log = get_logger('MyFunction', context)
    
    log.info('handler_started',
        eventType='test_event',
        timestamp='2024-01-15T10:30:00Z')
    
    print("✅ get_logger helper test passed")


def test_debug_log():
    """DEBUG 로그 테스트"""
    print("\n=== Test 8: DEBUG Log (depends on LOG_LEVEL) ===")
    
    log = StructuredLogger('TestFunction', 'req-404')
    
    log.debug('api_request_details',
        url='https://api.example.com/generate',
        method='POST',
        headers={'Content-Type': 'application/json'})
    
    if is_debug_enabled():
        print("✅ DEBUG log test passed (DEBUG mode enabled)")
    else:
        print("ℹ️  DEBUG log not output (LOG_LEVEL is not DEBUG)")


def test_log_structure():
    """로그 구조 검증 테스트"""
    print("\n=== Test 9: Log Structure Validation ===")
    
    import io
    import logging
    
    # 로그 캡처를 위한 핸들러 추가
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    
    test_logger = logging.getLogger()
    test_logger.addHandler(handler)
    
    log = StructuredLogger('TestFunction', 'req-505')
    log.info('test_event', key1='value1', key2=123)
    
    # 로그 출력 가져오기
    log_output = log_stream.getvalue()
    
    # JSON 파싱 테스트
    try:
        log_data = json.loads(log_output.strip())
        
        # 필수 필드 확인
        assert 'timestamp' in log_data, "Missing 'timestamp' field"
        assert 'level' in log_data, "Missing 'level' field"
        assert 'event' in log_data, "Missing 'event' field"
        assert 'context' in log_data, "Missing 'context' field"
        assert 'metadata' in log_data, "Missing 'metadata' field"
        
        # 메타데이터 필드 확인
        assert log_data['metadata']['functionName'] == 'TestFunction'
        assert log_data['metadata']['requestId'] == 'req-505'
        
        # Context 데이터 확인
        assert log_data['context']['key1'] == 'value1'
        assert log_data['context']['key2'] == 123
        
        print("✅ Log structure validation passed")
        print(f"   Sample output: {json.dumps(log_data, indent=2, ensure_ascii=False)}")
        
    except json.JSONDecodeError as e:
        print(f"❌ Log is not valid JSON: {e}")
    except AssertionError as e:
        print(f"❌ Log structure validation failed: {e}")
    finally:
        test_logger.removeHandler(handler)


def run_all_tests():
    """모든 테스트 실행"""
    print("=" * 60)
    print("로깅 헬퍼 단위 테스트 시작")
    print("=" * 60)
    
    tests = [
        test_basic_info_log,
        test_warning_log,
        test_error_log_with_exception,
        test_error_log_without_exception,
        test_invalid_event_name,
        test_complex_context,
        test_get_logger_helper,
        test_debug_log,
        test_log_structure
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ Test failed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"테스트 결과: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("✅ All tests passed!")
        return 0
    else:
        print(f"❌ {failed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
