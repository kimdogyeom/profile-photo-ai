const requiredEnv = {
  REACT_APP_API_BASE_URL: /^https?:\/\/.+/u,
  REACT_APP_AWS_REGION: /^[a-z]{2}-[a-z]+-\d$/u,
  REACT_APP_COGNITO_USER_POOL_ID: /^[a-z]{2}-[a-z]+-\d_[A-Za-z0-9]+$/u,
  REACT_APP_COGNITO_CLIENT_ID: /^[A-Za-z0-9]{10,}$/u,
};

const errors = [];

for (const [name, pattern] of Object.entries(requiredEnv)) {
  const value = process.env[name];

  if (!value) {
    errors.push(`${name} is missing`);
    continue;
  }

  if (!pattern.test(value)) {
    errors.push(`${name} has an invalid format: ${value}`);
  }
}

if (errors.length > 0) {
  console.error("Frontend environment validation failed:");
  for (const error of errors) {
    console.error(`- ${error}`);
  }
  process.exit(1);
}

console.log("Frontend environment validation passed.");
