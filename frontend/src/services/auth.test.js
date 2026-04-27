const ORIGINAL_ENV = process.env;
const ORIGINAL_LOCATION = window.location;
const ORIGINAL_CRYPTO = window.crypto;
const ORIGINAL_FETCH = global.fetch;

const createToken = (payload) => {
  const encoded = window
    .btoa(JSON.stringify(payload))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/g, '');

  return `header.${encoded}.signature`;
};

const setLocation = (overrides = {}) => {
  const location = {
    assign: jest.fn(),
    replace: jest.fn(),
    origin: 'http://localhost:3000',
    pathname: '/',
    search: '',
    ...overrides,
  };

  Object.defineProperty(window, 'location', {
    configurable: true,
    value: location,
  });

  return location;
};

const setCrypto = () => {
  Object.defineProperty(window, 'crypto', {
    configurable: true,
    value: {
      getRandomValues: (values) => {
        for (let index = 0; index < values.length; index += 1) {
          values[index] = (index + 1) % 255;
        }
        return values;
      },
      subtle: {
        digest: async () => new Uint8Array(32).fill(7).buffer,
      },
    },
  });
};

describe('auth service', () => {
  beforeEach(() => {
    jest.resetModules();
    localStorage.clear();
    sessionStorage.clear();
    process.env = {
      ...ORIGINAL_ENV,
      REACT_APP_COGNITO_USER_POOL_ID: 'ap-northeast-2_testpool',
      REACT_APP_COGNITO_CLIENT_ID: 'abcdefghijklmnopqrstuvwxyz',
      REACT_APP_COGNITO_DOMAIN: 'example.auth.ap-northeast-2.amazoncognito.com',
      REACT_APP_REDIRECT_URI: 'http://localhost:3000/callback',
      REACT_APP_LOGOUT_URI: 'http://localhost:3000',
    };
    setLocation();
    setCrypto();
  });

  afterEach(() => {
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: ORIGINAL_LOCATION,
    });
    Object.defineProperty(window, 'crypto', {
      configurable: true,
      value: ORIGINAL_CRYPTO,
    });
    global.fetch = ORIGINAL_FETCH;
  });

  afterAll(() => {
    process.env = ORIGINAL_ENV;
  });

  it('redirects login into the Cognito Hosted UI with PKCE data', async () => {
    const auth = require('./auth');

    await auth.signIn('tester@example.com');

    expect(window.location.assign).toHaveBeenCalledTimes(1);

    const redirectUrl = new URL(window.location.assign.mock.calls[0][0]);
    expect(redirectUrl.pathname).toBe('/login');
    expect(redirectUrl.searchParams.get('client_id')).toBe('abcdefghijklmnopqrstuvwxyz');
    expect(redirectUrl.searchParams.get('redirect_uri')).toBe('http://localhost:3000/callback');
    expect(redirectUrl.searchParams.get('login_hint')).toBe('tester@example.com');
    expect(redirectUrl.searchParams.get('code_challenge')).toBeTruthy();
    expect(redirectUrl.searchParams.get('code_challenge_method')).toBe('S256');
    expect(sessionStorage.getItem('auth.pkce.verifier')).toBeTruthy();
    expect(sessionStorage.getItem('auth.pkce.state')).toBeTruthy();
  });

  it('handles the Hosted UI callback and stores tokens', async () => {
    setLocation({
      pathname: '/callback',
      search: '?code=test-code&state=known-state',
    });
    sessionStorage.setItem('auth.pkce.verifier', 'test-verifier');
    sessionStorage.setItem('auth.pkce.state', 'known-state');
    sessionStorage.setItem('auth.pkce.nonce', 'known-nonce');

    const fetchMock = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        id_token: createToken({
          exp: Math.floor(Date.now() / 1000) + 3600,
          nonce: 'known-nonce',
          email: 'tester@example.com',
        }),
        access_token: 'access-token',
        refresh_token: 'refresh-token',
      }),
    });

    global.fetch = fetchMock;

    const auth = require('./auth');
    const result = await auth.handleAuthCallback();

    expect(result.handled).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(auth.getIdToken()).toBeTruthy();
    expect(auth.getAccessToken()).toBe('access-token');
    expect(auth.getRefreshToken()).toBe('refresh-token');
    expect(auth.isAuthenticated()).toBe(true);
    expect(auth.getUserInfo().email).toBe('tester@example.com');
    expect(localStorage.getItem('idToken')).toBeNull();
    expect(localStorage.getItem('refreshToken')).toBeNull();
    expect(localStorage.getItem('accessToken')).toBeNull();
    expect(localStorage.getItem('userInfo')).toBeNull();
  });

  it('treats a non-expired id token as authenticated', () => {
    const auth = require('./auth');
    sessionStorage.setItem('idToken', createToken({ exp: Math.floor(Date.now() / 1000) + 3600 }));

    expect(auth.isAuthenticated()).toBe(true);
  });

  it('uses session storage for tokens to reduce persistence risk', () => {
    const auth = require('./auth');
    const tokenPayload = createToken({ exp: Math.floor(Date.now() / 1000) + 3600 });
    auth.clearTokens();
    localStorage.setItem('idToken', tokenPayload);
    expect(auth.getIdToken()).toBeNull();
    sessionStorage.setItem('idToken', tokenPayload);
    expect(auth.getIdToken()).toBe(tokenPayload);
  });
});
