import React, { useEffect, useState } from 'react';
import { getUserInfo } from '../services/api';
import './UsageQuota.css';

export const UsageQuota = ({ refreshKey = 0 }) => {
  const [usage, setUsage] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchUsage();
  }, [refreshKey]);

  const fetchUsage = async () => {
    try {
      const data = await getUserInfo();
      setUsage({
        remaining: data.remainingQuota,
        limit: data.dailyLimit,
        used: data.dailyLimit - data.remainingQuota
      });
    } catch (error) {
      console.error('Failed to fetch usage:', error);
      setUsage({
        remaining: 0,
        limit: 0,
        used: 0,
        error: true
      });
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="usage-loading">Loading...</div>;
  if (usage?.error) return <div className="usage-loading">사용량 정보를 불러오지 못했습니다.</div>;

  const percentage = usage.limit > 0 ? (usage.used / usage.limit) * 100 : 0;

  return (
    <div className="usage-quota">
      <div className="usage-header">
        <span>오늘의 사용량</span>
        <span className="usage-count">
          {usage.used} / {usage.limit}
        </span>
      </div>
      
      <div className="usage-bar">
        <div
          className="usage-fill"
          style={{ width: `${percentage}%` }}
        />
      </div>
      
      <div className="usage-remaining">
        {usage.remaining > 0 ? (
          <span>남은 생성 횟수: {usage.remaining}회</span>
        ) : (
          <span className="usage-exceeded">
            오늘의 사용량을 모두 소진했습니다. 내일 다시 시도해주세요.
          </span>
        )}
      </div>
    </div>
  );
};
