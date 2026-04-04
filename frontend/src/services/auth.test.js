jest.mock('amazon-cognito-identity-js', () => ({
  AuthenticationDetails: class AuthenticationDetails {},
  CognitoUser: class CognitoUser {
    authenticateUser() {}
    refreshSession() {}
  },
  CognitoUserAttribute: class CognitoUserAttribute {},
  CognitoUserPool: class CognitoUserPool {
    signUp() {}
    getCurrentUser() {
      return null;
    }
  },
  CognitoRefreshToken: class CognitoRefreshToken {},
}));

const ORIGINAL_ENV = process.env;

const createToken = (payload) => {
  const encoded = window.btoa(JSON.stringify(payload)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
  return `header.${encoded}.signature`;
};

describe('auth service', () => {
  beforeEach(() => {
    jest.resetModules();
    localStorage.clear();
    process.env = { ...ORIGINAL_ENV };
  });

  afterAll(() => {
    process.env = ORIGINAL_ENV;
  });

  it('rejects sign in when Cognito config is missing', async () => {
    delete process.env.REACT_APP_COGNITO_USER_POOL_ID;
    delete process.env.REACT_APP_COGNITO_CLIENT_ID;

    const auth = require('./auth');

    await expect(auth.signIn('tester@example.com', 'secret')).rejects.toThrow('Cognito configuration is missing.');
  });

  it('treats a non-expired id token as authenticated', () => {
    process.env.REACT_APP_COGNITO_USER_POOL_ID = 'ap-northeast-1_testpool';
    process.env.REACT_APP_COGNITO_CLIENT_ID = 'abcdefghijklmnopqrstuvwxyz';

    const auth = require('./auth');
    localStorage.setItem('idToken', createToken({ exp: Math.floor(Date.now() / 1000) + 3600 }));

    expect(auth.isAuthenticated()).toBe(true);
  });
});
