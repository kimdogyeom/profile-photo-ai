"""
통계 집계 Lambda 함수
매일 1회 실행되어 CloudWatch Logs를 분석하고 리포트를 생성합니다.
"""

import boto3
import json
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
import requests

# AWS Lambda Powertools
from aws_lambda_powertools import Logger

# Powertools 초기화
logger = Logger()

logs_client = boto3.client('logs')

ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
LOG_GROUP_NAME = f'/aws/lambda/profile-photo-ai-ImageProcess-{ENVIRONMENT}'
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL', '')


@logger.inject_lambda_context
def lambda_handler(event, context):
    """
    매일 1회 실행되어 지난 24시간 통계를 집계하고 비즈니스 리포트 생성
    """
    logger.info("일일 리포트 생성 시작", environment=ENVIRONMENT)
    
    # 지난 24시간 데이터 수집
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=24)
    
    logger.info("조회 기간", start=start_time.isoformat(), end=end_time.isoformat())
    
    try:
        # 1. 스타일별 이미지 생성 수 집계
        logger.info("스타일별 통계 조회 중")
        style_stats = query_style_statistics(start_time, end_time)
        
        # 2. 시간대별 사용 패턴
        logger.info("시간대별 패턴 조회 중")
        hourly_pattern = query_hourly_pattern(start_time, end_time)
        
        # 3. 성공률 및 실패 원인 분석
        logger.info("성공률 조회 중")
        success_rate = query_success_rate(start_time, end_time)
        
        # 4. 처리 시간 통계
        logger.info("처리 시간 통계 조회 중")
        processing_times = query_processing_times(start_time, end_time)
        
        # 5. 실패 원인 분석
        logger.info("실패 원인 조회 중")
        failure_reasons = query_failure_reasons(start_time, end_time)
        
        # 리포트 생성
        report = generate_report(
            start_time, end_time,
            style_stats, hourly_pattern, success_rate, 
            processing_times, failure_reasons
        )
        
        # Discord로 리포트 전송
        if DISCORD_WEBHOOK_URL:
            send_discord_report(report)
            logger.info("Discord로 리포트 전송 완료")
        else:
            logger.warning("Discord Webhook이 설정되지 않음. 리포트는 로그에만 기록됨")
            logger.info("일일 리포트", report=report)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': '일일 리포트 생성 완료',
                'timestamp': end_time.isoformat(),
                'period': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat()
                }
            })
        }
        
    except Exception as e:
        logger.exception("일일 리포트 생성 중 오류 발생", error=str(e))
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': '일일 리포트 생성 실패',
                'error': str(e)
            })
        }


def query_style_statistics(start_time: datetime, end_time: datetime) -> List[List[Dict[str, str]]]:
    """
    CloudWatch Logs Insights로 스타일별 생성 수 쿼리
    """
    query = """
    fields @timestamp, style
    | filter event = "job_completed"
    | stats count() by style
    """
    
    return run_logs_insights_query(query, start_time, end_time)


def query_hourly_pattern(start_time: datetime, end_time: datetime) -> List[List[Dict[str, str]]]:
    """
    시간대별 사용 패턴
    """
    query = """
    fields @timestamp
    | filter event = "job_completed"
    | stats count() as count by bin(1h) as hour
    """
    
    return run_logs_insights_query(query, start_time, end_time)


def query_success_rate(start_time: datetime, end_time: datetime) -> List[List[Dict[str, str]]]:
    """
    성공률 및 실패 원인 분석
    """
    query = """
    fields @timestamp, event, errorType
    | filter event = "job_completed" or event = "job_failed"
    | stats 
        count() as total,
        sum(case when event = "job_completed" then 1 else 0 end) as success,
        sum(case when event = "job_failed" then 1 else 0 end) as failed
    """
    
    return run_logs_insights_query(query, start_time, end_time)


def query_processing_times(start_time: datetime, end_time: datetime) -> List[List[Dict[str, str]]]:
    """
    전체 처리 시간 통계 (다운로드 + 생성 + 업로드)
    """
    query = """
    fields @timestamp, processingTime
    | filter event = "job_completed"
    | stats avg(processingTime) as avg_total,
            pct(processingTime, 50) as p50,
            pct(processingTime, 95) as p95
    """
    
    return run_logs_insights_query(query, start_time, end_time)


def query_failure_reasons(start_time: datetime, end_time: datetime) -> List[List[Dict[str, str]]]:
    """
    실패 원인별 집계
    """
    query = """
    fields @timestamp, errorType
    | filter event = "job_failed"
    | stats count() as count by errorType
    """
    
    return run_logs_insights_query(query, start_time, end_time)


def run_logs_insights_query(query: str, start_time: datetime, end_time: datetime) -> List[List[Dict[str, str]]]:
    """
    CloudWatch Logs Insights 쿼리 실행
    """
    try:
        logger.debug("Logs Insights 쿼리 시작", query_preview=query[:100])
        
        # 쿼리 시작
        response = logs_client.start_query(
            logGroupName=LOG_GROUP_NAME,
            startTime=int(start_time.timestamp()),
            endTime=int(end_time.timestamp()),
            queryString=query
        )
        
        query_id = response['queryId']
        logger.debug("쿼리 시작됨", query_id=query_id)
        
        # 쿼리 완료 대기 (최대 30초)
        max_wait = 30
        elapsed = 0
        
        while elapsed < max_wait:
            result = logs_client.get_query_results(queryId=query_id)
            status = result['status']
            
            if status == 'Complete':
                logger.info("쿼리 완료", query_id=query_id, results_count=len(result['results']))
                return result['results']
            elif status == 'Failed' or status == 'Cancelled':
                raise Exception(f"쿼리 실패: {status}")
            
            time.sleep(1)
            elapsed += 1
        
        raise Exception(f"{max_wait}초 후 쿼리 타임아웃")
        
    except Exception as e:
        logger.error("Logs Insights 쿼리 실행 중 오류", error=str(e), query_preview=query[:100])
        return []


def generate_report(start_time, end_time, style_stats, hourly_pattern, success_rate, processing_times, failure_reasons):
    """
    비즈니스 리포트 생성
    """
    report_lines = []
    report_lines.append(f"# 📊 ProfilePhotoAI 일일 리포트")
    report_lines.append(f"**기간**: {start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%Y-%m-%d %H:%M')} (UTC)")
    report_lines.append("")
    
    # 1. 스타일별 통계
    report_lines.append("## 🎨 스타일별 이미지 생성 수")
    if style_stats:
        for row in style_stats:
            style = count = None
            for field in row:
                if field['field'] == 'style':
                    style = field['value']
                elif field['field'] == 'count()':
                    count = field['value']
            if style:
                report_lines.append(f"- **{style}**: {count}건")
    else:
        report_lines.append("- 데이터 없음")
    report_lines.append("")
    
    # 2. 성공률
    report_lines.append("## ✅ 성공률")
    if success_rate and len(success_rate) > 0:
        row = success_rate[0]
        total = success = failed = 0
        for field in row:
            if field['field'] == 'total':
                total = int(field['value'])
            elif field['field'] == 'success':
                success = int(field['value'])
            elif field['field'] == 'failed':
                failed = int(field['value'])
        
        success_rate_pct = (success / total * 100) if total > 0 else 0
        report_lines.append(f"- **전체**: {total}건")
        report_lines.append(f"- **성공**: {success}건 ({success_rate_pct:.1f}%)")
        report_lines.append(f"- **실패**: {failed}건 ({100-success_rate_pct:.1f}%)")
    else:
        report_lines.append("- 데이터 없음")
    report_lines.append("")
    
    # 3. 실패 원인
    report_lines.append("## ❌ 실패 원인")
    if failure_reasons:
        for row in failure_reasons:
            error_type = count = None
            for field in row:
                if field['field'] == 'errorType':
                    error_type = field['value']
                elif field['field'] == 'count':
                    count = field['value']
            if error_type:
                report_lines.append(f"- **{error_type}**: {count}건")
    else:
        report_lines.append("- 실패 없음 ✨")
    report_lines.append("")
    
    # 4. 처리 시간
    report_lines.append("## ⏱️ 평균 처리 시간")
    if processing_times and len(processing_times) > 0:
        row = processing_times[0]
        for field in row:
            if field['field'] == 'avg_total':
                avg_ms = float(field['value'])
                report_lines.append(f"- **평균**: {avg_ms/1000:.1f}초")
            elif field['field'] == 'p50':
                p50_ms = float(field['value'])
                report_lines.append(f"- **P50**: {p50_ms/1000:.1f}초")
            elif field['field'] == 'p95':
                p95_ms = float(field['value'])
                report_lines.append(f"- **P95**: {p95_ms/1000:.1f}초")
    else:
        report_lines.append("- 데이터 없음")
    report_lines.append("")
    
    # 5. 시간대별 패턴
    report_lines.append("## 📈 시간대별 사용 패턴 (상위 5개)")
    if hourly_pattern:
        # 시간대별로 정렬 (카운트 높은 순)
        sorted_hours = []
        for row in hourly_pattern:
            hour = count = None
            for field in row:
                if field['field'] == 'hour':
                    hour = field['value']
                elif field['field'] == 'count':
                    count = int(field['value'])
            if hour and count:
                sorted_hours.append((hour, count))
        
        sorted_hours.sort(key=lambda x: x[1], reverse=True)
        for i, (hour, count) in enumerate(sorted_hours[:5], 1):
            report_lines.append(f"{i}. **{hour[:13]}**: {count}건")
    else:
        report_lines.append("- 데이터 없음")
    
    return "\n".join(report_lines)


def send_discord_report(report_text):
    """
    Discord Webhook으로 리포트 전송
    """
    if not DISCORD_WEBHOOK_URL:
        logger.warning("Discord Webhook URL이 설정되지 않음")
        return
    
    payload = {
        "content": report_text
    }
    
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        if response.status_code == 204:
            logger.info("Discord Webhook 전송 성공")
        else:
            logger.warning("Discord Webhook 전송 실패", status_code=response.status_code, response=response.text[:200])
    except Exception as e:
        logger.error("Discord Webhook 전송 중 오류 발생", error=str(e))
