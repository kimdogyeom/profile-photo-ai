import React, { useEffect, useState } from 'react';
import './AuthModal.css';
import {
  confirmPassword,
  forgotPassword,
  signIn,
  signUp,
} from '../../services/auth';

const VIEW_CONTENT = {
  login: {
    title: '로그인',
    description: 'Cognito Hosted UI로 이동해 로그인합니다.',
    button: '로그인 계속하기',
    footerLabel: '계정이 없으신가요?',
    footerAction: '회원가입',
    footerTarget: 'signup',
  },
  signup: {
    title: '회원가입',
    description: 'Cognito Hosted UI에서 회원가입을 완료합니다.',
    button: '회원가입 계속하기',
    footerLabel: '이미 계정이 있으신가요?',
    footerAction: '로그인',
    footerTarget: 'login',
  },
  forgot: {
    title: '비밀번호 재설정',
    description: 'Cognito Hosted UI의 비밀번호 재설정 화면으로 이동합니다.',
    button: '재설정 페이지 열기',
    footerLabel: '비밀번호를 기억하셨나요?',
    footerAction: '로그인',
    footerTarget: 'login',
  },
  reset: {
    title: '비밀번호 확인',
    description: '인증 코드와 새 비밀번호 입력은 Cognito Hosted UI에서 처리합니다.',
    button: '확인 페이지 열기',
    footerLabel: '다른 도움이 필요하신가요?',
    footerAction: '비밀번호 재설정',
    footerTarget: 'forgot',
  },
};

const AuthModal = ({ isOpen, onClose, initialView = 'login' }) => {
  const [view, setView] = useState(initialView);
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    setView(initialView);
    setEmail('');
    setError('');
    setLoading(false);
  }, [initialView, isOpen]);

  if (!isOpen) return null;

  const resetForm = () => {
    setEmail('');
    setError('');
    setLoading(false);
  };

  const handleClose = () => {
    resetForm();
    setView(initialView);
    onClose();
  };

  const startRedirect = async (action) => {
    setError('');
    setLoading(true);

    try {
      const loginHint = email.trim() || undefined;

      switch (action) {
        case 'login':
          await signIn(loginHint);
          break;
        case 'signup':
          await signUp(loginHint);
          break;
        case 'forgot':
          await forgotPassword(loginHint);
          break;
        case 'reset':
          await confirmPassword(loginHint);
          break;
        default:
          throw new Error('Unknown auth action.');
      }
    } catch (err) {
      setError(err.message || '인증 페이지로 이동하지 못했습니다.');
      setLoading(false);
    }
  };

  const content = VIEW_CONTENT[view] || VIEW_CONTENT.login;

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      handleClose();
    }
  };

  return (
    <div className="auth-modal-backdrop" onClick={handleBackdropClick}>
      <div className="auth-modal-content">
        <button className="auth-modal-close" onClick={handleClose}>×</button>

        <h2 className="auth-modal-title">{content.title}</h2>
        <p className="auth-modal-description">{content.description}</p>

        {error && <div className="auth-modal-error">{error}</div>}

        <div className="auth-modal-form">
          <div className="form-group">
            <label>이메일 (선택)</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              disabled={loading}
              autoFocus
            />
            <small className="form-hint">입력하면 Cognito 화면에 로그인 힌트로 전달됩니다.</small>
          </div>

          <button
            type="button"
            className="auth-modal-btn-primary"
            disabled={loading}
            onClick={() => startRedirect(view)}
          >
            {loading ? '이동 중...' : content.button}
          </button>
        </div>

        <div className="auth-modal-footer">
          <div className="signup-prompt">
            {content.footerLabel}{' '}
            <button
              type="button"
              className="link-button-primary"
              onClick={() => {
                resetForm();
                setView(content.footerTarget);
              }}
            >
              {content.footerAction}
            </button>
          </div>
          <button
            type="button"
            className="link-button"
            onClick={handleClose}
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  );
};

export default AuthModal;
