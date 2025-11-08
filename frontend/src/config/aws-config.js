// AWS Configuration for ProfilePhotoAI Frontend
// Environment variables are injected during build

const config = {
  // API Gateway - MUST be set via environment variables
  apiEndpoint: process.env.REACT_APP_API_ENDPOINT || '',
  
  // AWS Region
  region: process.env.REACT_APP_AWS_REGION || 'ap-northeast-2',
  
  // Cognito Configuration - MUST be set via environment variables
  cognito: {
    userPoolId: process.env.REACT_APP_COGNITO_USER_POOL_ID || '',
    clientId: process.env.REACT_APP_COGNITO_CLIENT_ID || '',
    domain: process.env.REACT_APP_COGNITO_DOMAIN || '',
    redirectUri: process.env.REACT_APP_REDIRECT_URI || 'http://localhost:3000/callback',
  },
  
  // Environment
  environment: process.env.REACT_APP_ENVIRONMENT || 'development',
  
  // OAuth Providers
  oauthProviders: {
    google: 'Google',
  },
};

// Helper functions
export const getCognitoAuthUrl = (provider) => {
  const { domain, clientId, redirectUri } = config.cognito;
  
  // Remove any https:// prefix from domain if present
  const cleanDomain = domain.replace(/^https?:\/\//, '');
  
  // Construct auth domain
  const authDomain = cleanDomain.includes('amazoncognito.com') 
    ? cleanDomain 
    : `${cleanDomain}.auth.${config.region}.amazoncognito.com`;
  
  const url = `https://${authDomain}/oauth2/authorize?` +
    `client_id=${clientId}&` +
    `response_type=code&` +
    `scope=openid+email+profile&` +
    `redirect_uri=${encodeURIComponent(redirectUri)}&` +
    `identity_provider=${provider}`;
  
  console.log('🔐 Google OAuth URL:', {
    provider,
    domain,
    cleanDomain,
    authDomain,
    clientId,
    redirectUri,
    fullUrl: url
  });
  
  return url;
};

export const getCognitoLogoutUrl = () => {
  const { domain, clientId } = config.cognito;
  
  // Remove any https:// prefix from domain if present
  const cleanDomain = domain.replace(/^https?:\/\//, '');
  
  const authDomain = cleanDomain.includes('amazoncognito.com') 
    ? cleanDomain 
    : `${cleanDomain}.auth.${config.region}.amazoncognito.com`;
  
  const logoutUri = config.cognito.redirectUri.replace('/callback', '');
  
  return `https://${authDomain}/logout?` +
    `client_id=${clientId}&` +
    `logout_uri=${encodeURIComponent(logoutUri)}`;
};

// Log configuration in development
if (config.environment === 'development') {
  console.log('🔧 AWS Config:', {
    apiEndpoint: config.apiEndpoint,
    region: config.region,
    userPoolId: config.cognito.userPoolId,
    clientId: config.cognito.clientId,
    redirectUri: config.cognito.redirectUri,
  });
}

export default config;
