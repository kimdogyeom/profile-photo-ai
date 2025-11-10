"""
통계 집계 Lambda 함수
매 1시간마다 실행되어 CloudWatch Logs를 분석하고 Custom Metrics를 발행합니다.
"""

import boto3
import json
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

logs_client = boto3.client('logs')
cloudwatch_client = boto3.client('cloudwatch')

ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
LOG_GROUP_NAME = f'/aws/lambda/ProfilePhotoAI-ImageProcess-{ENVIRONMENT}'
NAMESPACE = f'ProfilePhotoAI/{ENVIRONMENT}/Statistics'


def lambda_handler(event, context):
    """
    1시간 단위로 실행되어 통계를 집계하고 Custom Metrics 발행
    """
    print(f"Starting statistics aggregation for environment: {ENVIRONMENT}")
    
    # 1시간 전부터 현재까지의 데이터 수집
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=1)
    
    print(f"Query period: {start_time.isoformat()} to {end_time.isoformat()}")
    
    try:
        # 1. 스타일별 이미지 생성 수 집계
        print("Querying style statistics...")
        style_stats = query_style_statistics(start_time, end_time)
        publish_style_metrics(style_stats)
        print(f"Published {len(style_stats)} style metrics")
        
        # 2. Gemini API 응답 시간 통계
        print("Querying API response times...")
        api_response_time = query_api_response_times(start_time, end_time)
        publish_response_time_metrics(api_response_time)
        print("Published API response time metrics")
        
        # 3. 성공률 및 실패 원인 분석
        print("Querying success rate...")
        success_rate = query_success_rate(start_time, end_time)
        publish_success_rate_metrics(success_rate)
        print("Published success rate metrics")
        
        # 4. 처리 시간 통계
        print("Querying processing times...")
        processing_times = query_processing_times(start_time, end_time)
        publish_processing_time_metrics(processing_times)
        print("Published processing time metrics")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Statistics aggregated successfully',
                'timestamp': end_time.isoformat(),
                'period': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat()
                }
            })
        }
        
    except Exception as e:
        print(f"Error aggregating statistics: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Failed to aggregate statistics',
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


def query_api_response_times(start_time: datetime, end_time: datetime) -> List[List[Dict[str, str]]]:
    """
    Gemini API 응답 시간 통계 (평균, p50, p95, p99)
    """
    query = """
    fields @timestamp, responseTime
    | filter event = "gemini_api_success"
    | stats avg(responseTime) as avg_time, 
            pct(responseTime, 50) as p50, 
            pct(responseTime, 95) as p95, 
            pct(responseTime, 99) as p99,
            max(responseTime) as max_time,
            min(responseTime) as min_time
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
    fields @timestamp, processingTime, generationTime, downloadTime, uploadTime
    | filter event = "job_completed"
    | stats avg(processingTime) as avg_total,
            avg(generationTime) as avg_generation,
            avg(downloadTime) as avg_download,
            avg(uploadTime) as avg_upload,
            pct(processingTime, 95) as p95_total
    """
    
    return run_logs_insights_query(query, start_time, end_time)


def run_logs_insights_query(query: str, start_time: datetime, end_time: datetime) -> List[List[Dict[str, str]]]:
    """
    CloudWatch Logs Insights 쿼리 실행
    """
    try:
        # 쿼리 시작
        response = logs_client.start_query(
            logGroupName=LOG_GROUP_NAME,
            startTime=int(start_time.timestamp()),
            endTime=int(end_time.timestamp()),
            queryString=query
        )
        
        query_id = response['queryId']
        print(f"Started query {query_id}")
        
        # 쿼리 완료 대기 (최대 30초)
        max_wait = 30
        elapsed = 0
        
        while elapsed < max_wait:
            result = logs_client.get_query_results(queryId=query_id)
            status = result['status']
            
            if status == 'Complete':
                print(f"Query {query_id} completed with {len(result['results'])} results")
                return result['results']
            elif status == 'Failed' or status == 'Cancelled':
                raise Exception(f"Query failed with status: {status}")
            
            time.sleep(1)
            elapsed += 1
        
        raise Exception(f"Query timeout after {max_wait} seconds")
        
    except Exception as e:
        print(f"Error running Logs Insights query: {str(e)}")
        print(f"Query: {query}")
        return []


def publish_style_metrics(style_stats: List[List[Dict[str, str]]]):
    """
    스타일별 메트릭을 CloudWatch Custom Metrics로 발행
    """
    if not style_stats:
        print("No style statistics to publish")
        return
    
    metric_data = []
    
    for row in style_stats:
        style = None
        count = 0
        
        for field in row:
            if field['field'] == 'style':
                style = field['value']
            elif field['field'] == 'count()':
                count = int(field['value'])
        
        if style:
            metric_data.append({
                'MetricName': 'ImageGenerationByStyle',
                'Dimensions': [
                    {'Name': 'Style', 'Value': style}
                ],
                'Value': count,
                'Unit': 'Count',
                'Timestamp': datetime.utcnow()
            })
    
    if metric_data:
        cloudwatch_client.put_metric_data(
            Namespace=NAMESPACE,
            MetricData=metric_data
        )
        print(f"Published {len(metric_data)} style metrics to {NAMESPACE}")


def publish_response_time_metrics(api_stats: List[List[Dict[str, str]]]):
    """
    API 응답 시간 메트릭 발행
    """
    if not api_stats or len(api_stats) == 0:
        print("No API response time statistics to publish")
        return
    
    row = api_stats[0]
    metrics = {}
    
    for field in row:
        field_name = field['field']
        value = float(field['value'])
        metrics[field_name] = value
    
    metric_data = [
        {
            'MetricName': 'GeminiAPIResponseTime',
            'Dimensions': [{'Name': 'Statistic', 'Value': 'Average'}],
            'Value': metrics.get('avg_time', 0),
            'Unit': 'Milliseconds',
            'Timestamp': datetime.utcnow()
        },
        {
            'MetricName': 'GeminiAPIResponseTime',
            'Dimensions': [{'Name': 'Statistic', 'Value': 'P50'}],
            'Value': metrics.get('p50', 0),
            'Unit': 'Milliseconds',
            'Timestamp': datetime.utcnow()
        },
        {
            'MetricName': 'GeminiAPIResponseTime',
            'Dimensions': [{'Name': 'Statistic', 'Value': 'P95'}],
            'Value': metrics.get('p95', 0),
            'Unit': 'Milliseconds',
            'Timestamp': datetime.utcnow()
        },
        {
            'MetricName': 'GeminiAPIResponseTime',
            'Dimensions': [{'Name': 'Statistic', 'Value': 'P99'}],
            'Value': metrics.get('p99', 0),
            'Unit': 'Milliseconds',
            'Timestamp': datetime.utcnow()
        },
        {
            'MetricName': 'GeminiAPIResponseTime',
            'Dimensions': [{'Name': 'Statistic', 'Value': 'Max'}],
            'Value': metrics.get('max_time', 0),
            'Unit': 'Milliseconds',
            'Timestamp': datetime.utcnow()
        },
        {
            'MetricName': 'GeminiAPIResponseTime',
            'Dimensions': [{'Name': 'Statistic', 'Value': 'Min'}],
            'Value': metrics.get('min_time', 0),
            'Unit': 'Milliseconds',
            'Timestamp': datetime.utcnow()
        }
    ]
    
    cloudwatch_client.put_metric_data(
        Namespace=NAMESPACE,
        MetricData=metric_data
    )
    print(f"Published {len(metric_data)} API response time metrics to {NAMESPACE}")


def publish_success_rate_metrics(success_stats: List[List[Dict[str, str]]]):
    """
    성공률 메트릭 발행
    """
    if not success_stats or len(success_stats) == 0:
        print("No success rate statistics to publish")
        return
    
    row = success_stats[0]
    total = 0
    success = 0
    failed = 0
    
    for field in row:
        if field['field'] == 'total':
            total = int(field['value'])
        elif field['field'] == 'success':
            success = int(field['value'])
        elif field['field'] == 'failed':
            failed = int(field['value'])
    
    success_rate = (success / total * 100) if total > 0 else 0
    
    metric_data = [
        {
            'MetricName': 'JobSuccessRate',
            'Value': success_rate,
            'Unit': 'Percent',
            'Timestamp': datetime.utcnow()
        },
        {
            'MetricName': 'TotalJobs',
            'Value': total,
            'Unit': 'Count',
            'Timestamp': datetime.utcnow()
        },
        {
            'MetricName': 'SuccessfulJobs',
            'Value': success,
            'Unit': 'Count',
            'Timestamp': datetime.utcnow()
        },
        {
            'MetricName': 'FailedJobs',
            'Value': failed,
            'Unit': 'Count',
            'Timestamp': datetime.utcnow()
        }
    ]
    
    cloudwatch_client.put_metric_data(
        Namespace=NAMESPACE,
        MetricData=metric_data
    )
    print(f"Published success rate metrics: {success_rate:.2f}% ({success}/{total}) to {NAMESPACE}")


def publish_processing_time_metrics(processing_stats: List[List[Dict[str, str]]]):
    """
    처리 시간 메트릭 발행
    """
    if not processing_stats or len(processing_stats) == 0:
        print("No processing time statistics to publish")
        return
    
    row = processing_stats[0]
    metrics = {}
    
    for field in row:
        field_name = field['field']
        value = float(field['value'])
        metrics[field_name] = value
    
    metric_data = [
        {
            'MetricName': 'ProcessingTime',
            'Dimensions': [{'Name': 'Stage', 'Value': 'Total'}],
            'Value': metrics.get('avg_total', 0),
            'Unit': 'Milliseconds',
            'Timestamp': datetime.utcnow()
        },
        {
            'MetricName': 'ProcessingTime',
            'Dimensions': [{'Name': 'Stage', 'Value': 'Generation'}],
            'Value': metrics.get('avg_generation', 0),
            'Unit': 'Milliseconds',
            'Timestamp': datetime.utcnow()
        },
        {
            'MetricName': 'ProcessingTime',
            'Dimensions': [{'Name': 'Stage', 'Value': 'Download'}],
            'Value': metrics.get('avg_download', 0),
            'Unit': 'Milliseconds',
            'Timestamp': datetime.utcnow()
        },
        {
            'MetricName': 'ProcessingTime',
            'Dimensions': [{'Name': 'Stage', 'Value': 'Upload'}],
            'Value': metrics.get('avg_upload', 0),
            'Unit': 'Milliseconds',
            'Timestamp': datetime.utcnow()
        },
        {
            'MetricName': 'ProcessingTimeP95',
            'Value': metrics.get('p95_total', 0),
            'Unit': 'Milliseconds',
            'Timestamp': datetime.utcnow()
        }
    ]
    
    cloudwatch_client.put_metric_data(
        Namespace=NAMESPACE,
        MetricData=metric_data
    )
    print(f"Published {len(metric_data)} processing time metrics to {NAMESPACE}")
