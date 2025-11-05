import React, { useEffect, useState } from 'react';
import { handleCallback } from '../services/auth';

export const CallbackPage = () => {
  const [status, setStatus] = useState('processing');
  const [error, setError] = useState(null);

  useEffect(() => {
    const processCallback = async () => {
      // Get authorization code from URL
      const params = new URLSearchParams(window.location.search);
      const code = params.get('code');
      const errorParam = params.get('error');
      const errorDescription = params.get('error_description');

      console.log('🔍 Callback params:', {
        code: code ? 'present' : 'missing',
        error: errorParam,
        errorDescription,
        fullUrl: window.location.href
      });

      if (errorParam) {
        const errorMessage = errorDescription 
          ? `로그인 실패: ${errorParam} - ${decodeURIComponent(errorDescription)}`
          : `로그인 실패: ${errorParam}`;
        setError(errorMessage);
        setStatus('error');
        console.error('❌ OAuth error:', { errorParam, errorDescription });
        return;
      }

      if (!code) {
        setError('인증 코드가 없습니다.');
        setStatus('error');
        console.error('❌ No authorization code found');
        return;
      }

      try {
        console.log('🔄 Exchanging code for tokens...');
        // Exchange code for tokens
        await handleCallback(code);
        console.log('✅ Token exchange successful');
        setStatus('success');
        
        // Redirect to main page after 1 second
        setTimeout(() => {
          window.location.href = '/';
        }, 1000);
      } catch (err) {
        console.error('❌ Callback error:', err);
        setError(`로그인 처리 중 오류: ${err.message || '알 수 없는 오류'}`);
        setStatus('error');
      }
    };

    processCallback();
  }, []);

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        {status === 'processing' && (
          <>
            <div style={styles.spinner}></div>
            <h2>로그인 처리 중...</h2>
            <p>잠시만 기다려주세요.</p>
          </>
        )}
        
        {status === 'success' && (
          <>
            <div style={styles.successIcon}>✓</div>
            <h2>로그인 성공!</h2>
            <p>메인 페이지로 이동합니다...</p>
          </>
        )}
        
        {status === 'error' && (
          <>
            <div style={styles.errorIcon}>✕</div>
            <h2>로그인 실패</h2>
            <p>{error}</p>
            <button 
              onClick={() => window.location.href = '/'}
              style={styles.button}
            >
              메인 페이지로 돌아가기
            </button>
          </>
        )}
      </div>
    </div>
  );
};

const styles = {
  container: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    minHeight: '100vh',
    backgroundColor: '#f5f5f5'
  },
  card: {
    backgroundColor: 'white',
    padding: '40px',
    borderRadius: '8px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
    textAlign: 'center',
    maxWidth: '400px'
  },
  spinner: {
    border: '4px solid #f3f3f3',
    borderTop: '4px solid #3498db',
    borderRadius: '50%',
    width: '50px',
    height: '50px',
    animation: 'spin 1s linear infinite',
    margin: '0 auto 20px'
  },
  successIcon: {
    fontSize: '60px',
    color: '#4CAF50',
    marginBottom: '20px'
  },
  errorIcon: {
    fontSize: '60px',
    color: '#f44336',
    marginBottom: '20px'
  },
  button: {
    marginTop: '20px',
    padding: '10px 20px',
    backgroundColor: '#3498db',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '16px'
  }
};
