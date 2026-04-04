const ORIGINAL_ENV = process.env;

describe('api service', () => {
  let consoleErrorSpy;

  beforeEach(() => {
    jest.resetModules();
    process.env = {
      ...ORIGINAL_ENV,
      REACT_APP_API_BASE_URL: 'https://example.execute-api.ap-northeast-1.amazonaws.com/dev',
    };
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  afterAll(() => {
    process.env = ORIGINAL_ENV;
  });

  it('adds the bearer token in the request interceptor', async () => {
    let requestInterceptor;

    jest.doMock('axios', () => ({
      create: jest.fn(() => ({
        post: jest.fn(),
        get: jest.fn(),
        interceptors: {
          request: {
            use: (handler) => {
              requestInterceptor = handler;
            },
          },
          response: {
            use: jest.fn(),
          },
        },
      })),
    }));

    jest.doMock('./auth', () => ({
      getIdToken: jest.fn(() => 'test-token'),
      isAuthenticated: jest.fn(() => true),
      logout: jest.fn(),
      refreshTokens: jest.fn(),
    }));

    jest.isolateModules(() => {
      require('./api');
    });

    const config = await requestInterceptor({});

    expect(config.headers.Authorization).toBe('Bearer test-token');
  });

  it('normalizes getUserJobs responses', async () => {
    const getMock = jest.fn().mockResolvedValue({
      data: {
        jobs: [{ jobId: 'job_1' }],
        nextToken: 'next-token',
      },
    });

    jest.doMock('axios', () => ({
      create: jest.fn(() => ({
        post: jest.fn(),
        get: getMock,
        interceptors: {
          request: {
            use: jest.fn(),
          },
          response: {
            use: jest.fn(),
          },
        },
      })),
    }));

    jest.doMock('./auth', () => ({
      getIdToken: jest.fn(() => 'test-token'),
      isAuthenticated: jest.fn(() => true),
      logout: jest.fn(),
      refreshTokens: jest.fn(),
    }));

    let api;
    jest.isolateModules(() => {
      api = require('./api');
    });

    await expect(api.getUserJobs(10)).resolves.toEqual({
      jobs: [{ jobId: 'job_1' }],
      nextToken: 'next-token',
      hasMore: false,
    });
  });

  it('logs out and redirects on a 401 response', async () => {
    let responseRejected;
    const logoutMock = jest.fn();
    const originalLocation = window.location;

    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { href: '/generate' },
    });

    jest.doMock('axios', () => ({
      create: jest.fn(() => ({
        post: jest.fn(),
        get: jest.fn(),
        interceptors: {
          request: {
            use: jest.fn(),
          },
          response: {
            use: (_fulfilled, rejected) => {
              responseRejected = rejected;
            },
          },
        },
      })),
    }));

    jest.doMock('./auth', () => ({
      getIdToken: jest.fn(() => 'test-token'),
      isAuthenticated: jest.fn(() => true),
      logout: logoutMock,
      refreshTokens: jest.fn(),
    }));

    jest.isolateModules(() => {
      require('./api');
    });

    const error = { response: { status: 401 } };

    await expect(responseRejected(error)).rejects.toBe(error);
    expect(logoutMock).toHaveBeenCalledTimes(1);
    expect(window.location.href).toBe('/');

    Object.defineProperty(window, 'location', {
      configurable: true,
      value: originalLocation,
    });
  });
});
