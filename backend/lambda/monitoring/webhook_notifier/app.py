"""
CloudWatch Alarm Webhook Notifier
CloudWatch Alarm → SNS → Lambda → Discord Webhook

개선 사항:
- 알람 심각도 표시 (P0: Critical, P1: Warning)
- CloudWatch Logs Insights 직접 링크
- 알람 메트릭 상세 정보
- 컨텍스트 정보 추가
"""

import json
import os
import urllib3
from datetime import datetime
from urllib.parse import quote

# AWS Lambda Powertools
from aws_lambda_powertools import Logger

# Powertools 초기화
logger = Logger()

http = urllib3.PoolManager()

# 환경 변수
WEBHOOK_URL = os.environ['WEBHOOK_URL']
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
AWS_REGION = os.environ.get('AWS_REGION', 'ap-northeast-1')


@logger.inject_lambda_context
def lambda_handler(event, context):
    """
    CloudWatch Alarm → SNS → Lambda → Webhook
    SNS 메시지를 파싱하여 Discord로 전송
    """
    logger.info("SNS 메시지 처리 시작", records_count=len(event['Records']))
    
    for record in event['Records']:
        try:
            # SNS 메시지 파싱
            sns_message = json.loads(record['Sns']['Message'])
            
            alarm_name = sns_message.get('AlarmName', 'Unknown')
            new_state = sns_message.get('NewStateValue', 'UNKNOWN')
            old_state = sns_message.get('OldStateValue', 'UNKNOWN')
            reason = sns_message.get('NewStateReason', 'No reason provided')
            timestamp = sns_message.get('StateChangeTime', datetime.utcnow().isoformat())
            alarm_description = sns_message.get('AlarmDescription', '')
            
            # 알람 상세 정보
            trigger = sns_message.get('Trigger', {})
            namespace = trigger.get('Namespace', '')
            metric_name = trigger.get('MetricName', '')
            dimensions = trigger.get('Dimensions', [])
            threshold = trigger.get('Threshold', 0)
            comparison = trigger.get('ComparisonOperator', '')
            evaluation_periods = trigger.get('EvaluationPeriods', 1)
            period = trigger.get('Period', 60)
            
            logger.info("알람 정보 파싱 완료",
                alarm_name=alarm_name,
                state_change=f"{old_state} → {new_state}",
                metric=metric_name)
            
            # 알람 심각도 판단
            severity = determine_severity(alarm_name)
            
            # CloudWatch 링크 생성
            logs_link = generate_logs_insights_link(alarm_name, namespace, metric_name)
            alarm_link = generate_alarm_link(alarm_name)
            
            # Discord 메시지 생성
            payload = format_discord_message(
                alarm_name=alarm_name,
                state=new_state,
                old_state=old_state,
                reason=reason,
                timestamp=timestamp,
                description=alarm_description,
                severity=severity,
                namespace=namespace,
                metric_name=metric_name,
                dimensions=dimensions,
                threshold=threshold,
                comparison=comparison,
                evaluation_periods=evaluation_periods,
                period=period,
                logs_link=logs_link,
                alarm_link=alarm_link
            )
            
            # Webhook 전송
            response = http.request(
                'POST',
                WEBHOOK_URL,
                body=json.dumps(payload),
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status == 204:
                logger.info("Webhook 전송 성공", alarm_name=alarm_name)
            else:
                logger.warning("Webhook 전송 실패", 
                    alarm_name=alarm_name,
                    status_code=response.status,
                    response_body=response.data.decode('utf-8')[:200])
        
        except Exception as e:
            logger.exception("SNS 메시지 처리 중 오류 발생", 
                error=str(e),
                alarm_name=alarm_name if 'alarm_name' in locals() else 'Unknown')
    
    return {'statusCode': 200, 'body': json.dumps({'message': 'Processed successfully'})}


def determine_severity(alarm_name: str) -> str:
    """
    알람 이름에서 심각도 추출
    P0 = Critical (즉시 대응 필요)
    P1 = Warning (모니터링 필요)
    P2 = Info (참고용)
    """
    alarm_upper = alarm_name.upper()
    
    if 'P0' in alarm_upper or 'CRITICAL' in alarm_upper:
        severity = 'P0'
    elif 'P1' in alarm_upper or 'WARNING' in alarm_upper:
        severity = 'P1'
    elif 'P2' in alarm_upper or 'INFO' in alarm_upper:
        severity = 'P2'
    else:
        severity = 'P1'  # Default
    
    logger.debug("알람 심각도 판단", alarm_name=alarm_name, severity=severity)
    return severity


def generate_logs_insights_link(alarm_name: str, namespace: str, metric_name: str) -> str:
    """
    CloudWatch Logs Insights 쿼리 링크 생성
    """
    # 알람 타입별 로그 그룹 매핑
    log_group = ''
    query = ''
    
    if 'ImageProcess' in alarm_name:
        log_group = f'/aws/lambda/profile-photo-ai-image-process-{ENVIRONMENT}'
        if 'Error' in alarm_name:
            query = 'fields @timestamp, level, event, error, errorType, jobId | filter level = "ERROR" | sort @timestamp desc | limit 20'
        elif 'Nova' in alarm_name or 'ImageGeneration' in alarm_name:
            query = 'fields @timestamp, event, jobId, responseTimeMs, error | filter event = "nova_api_error" or event = "nova_api_slow_response" | sort @timestamp desc | limit 20'
        else:
            query = 'fields @timestamp, level, event, jobId, error | filter level = "ERROR" or level = "WARNING" | sort @timestamp desc | limit 20'

    elif 'ApiManager' in alarm_name:
        log_group = f'/aws/lambda/profile-photo-ai-api-manager-{ENVIRONMENT}'
        query = 'fields @timestamp, level, event, userId, error | filter level = "ERROR" or level = "WARNING" | sort @timestamp desc | limit 20'

    elif 'FileTransfer' in alarm_name:
        log_group = f'/aws/lambda/profile-photo-ai-file-transfer-{ENVIRONMENT}'
        query = 'fields @timestamp, level, event, userId, error | filter level = "ERROR" or level = "WARNING" | sort @timestamp desc | limit 20'

    else:
        # Default query
        log_group = f'/aws/lambda/profile-photo-ai-image-process-{ENVIRONMENT}'
        query = 'fields @timestamp, level, event, error | filter level = "ERROR" | sort @timestamp desc | limit 20'
    
    if not log_group:
        logger.debug("로그 그룹 매핑 없음", alarm_name=alarm_name)
        return None
    
    # CloudWatch Logs Insights URL 생성
    base_url = f"https://{AWS_REGION}.console.aws.amazon.com/cloudwatch/home"
    
    # 쿼리 인코딩
    query_encoded = quote(query)
    log_group_encoded = quote(log_group)
    
    # 시간 범위: 지난 1시간
    end_time = int(datetime.utcnow().timestamp() * 1000)
    start_time = end_time - (3600 * 1000)  # 1시간 전
    
    url = f"{base_url}?region={AWS_REGION}#logsV2:logs-insights$3FqueryDetail$3D~(end~{end_time}~start~{start_time}~timeType~'ABSOLUTE~unit~'seconds~editorString~'{query_encoded}~source~(~'{log_group_encoded}))"
    
    logger.debug("Logs Insights 링크 생성 완료", alarm_name=alarm_name, log_group=log_group)
    return url


def generate_alarm_link(alarm_name: str) -> str:
    """
    CloudWatch Alarm 상세 페이지 링크 생성
    """
    alarm_name_encoded = quote(alarm_name)
    link = f"https://{AWS_REGION}.console.aws.amazon.com/cloudwatch/home?region={AWS_REGION}#alarmsV2:alarm/{alarm_name_encoded}"
    
    logger.debug("알람 링크 생성 완료", alarm_name=alarm_name)
    return link


def format_discord_message(
    alarm_name: str,
    state: str,
    old_state: str,
    reason: str,
    timestamp: str,
    description: str,
    severity: str,
    namespace: str,
    metric_name: str,
    dimensions: list,
    threshold: float,
    comparison: str,
    evaluation_periods: int,
    period: int,
    logs_link: str,
    alarm_link: str
) -> dict:
    """
    Discord Embed 메시지 포맷 (풍부한 정보 포함)
    """
    # 상태별 색상 및 이모지
    if state == 'ALARM':
        if severity == 'P0':
            color = 0xFF0000  # Red (Critical)
            emoji = '🚨'
            severity_text = '**CRITICAL**'
        else:
            color = 0xFFA500  # Orange (Warning)
            emoji = '⚠️'
            severity_text = '**WARNING**'
    elif state == 'OK':
        color = 0x00FF00  # Green
        emoji = '✅'
        severity_text = 'RESOLVED'
    elif state == 'INSUFFICIENT_DATA':
        color = 0x808080  # Gray
        emoji = '❓'
        severity_text = 'INSUFFICIENT DATA'
    else:
        color = 0x0000FF  # Blue
        emoji = 'ℹ️'
        severity_text = 'UNKNOWN'
    
    # 타이틀
    title = f"{emoji} {severity_text} - {alarm_name}"
    
    # 설명 (알람 description이 있으면 표시)
    description_text = description if description else reason
    
    # Fields 구성
    fields = [
        {
            "name": "📊 Status Change",
            "value": f"{old_state} → **{state}**",
            "inline": True
        },
        {
            "name": "🏷️ Severity",
            "value": severity_text,
            "inline": True
        },
        {
            "name": "🕐 Timestamp",
            "value": format_timestamp(timestamp),
            "inline": True
        }
    ]
    
    # 메트릭 정보 추가
    if metric_name:
        metric_info = f"**Namespace**: `{namespace}`\n"
        metric_info += f"**Metric**: `{metric_name}`\n"
        
        if dimensions:
            dim_str = ', '.join([f"{d['name']}={d['value']}" for d in dimensions])
            metric_info += f"**Dimensions**: `{dim_str}`\n"
        
        # Threshold 정보
        comparison_text = format_comparison_operator(comparison)
        metric_info += f"**Threshold**: {comparison_text} {threshold}\n"
        metric_info += f"**Period**: {evaluation_periods} period(s) of {period}s"
        
        fields.append({
            "name": "📈 Metric Details",
            "value": metric_info,
            "inline": False
        })
    
    # 링크 추가
    links = []
    if logs_link:
        links.append(f"[🔍 View Logs]({logs_link})")
    if alarm_link:
        links.append(f"[⚙️ Alarm Details]({alarm_link})")
    
    if links:
        fields.append({
            "name": "🔗 Quick Links",
            "value": ' | '.join(links),
            "inline": False
        })
    
    # Footer
    footer_text = f"Environment: {ENVIRONMENT.upper()} | Region: {AWS_REGION}"
    
    return {
        "embeds": [{
            "title": title,
            "description": description_text,
            "color": color,
            "fields": fields,
            "footer": {
                "text": footer_text
            },
            "timestamp": timestamp
        }]
    }


def format_timestamp(timestamp_str: str) -> str:
    """
    ISO 8601 타임스탬프를 Discord 타임스탬프 포맷으로 변환
    """
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        unix_timestamp = int(dt.timestamp())
        # Discord timestamp format: <t:unix_timestamp:F> (Full date/time)
        return f"<t:{unix_timestamp}:F>"
    except:
        return timestamp_str


def format_comparison_operator(operator: str) -> str:
    """
    비교 연산자를 읽기 쉬운 형태로 변환
    """
    mapping = {
        'GreaterThanOrEqualToThreshold': '≥',
        'GreaterThanThreshold': '>',
        'LessThanThreshold': '<',
        'LessThanOrEqualToThreshold': '≤',
        'LessThanLowerOrGreaterThanUpperThreshold': '< lower or > upper'
    }
    return mapping.get(operator, operator)
