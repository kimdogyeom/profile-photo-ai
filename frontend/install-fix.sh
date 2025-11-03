#!/bin/bash
echo "Trying to install react-scripts..."

# Method 1: Install with exact versions
npm install react-scripts@5.0.1 \
  @babel/core@7.23.0 \
  webpack@5.89.0 \
  --save-dev --legacy-peer-deps

# Check if installed
if [ -f "node_modules/.bin/react-scripts" ]; then
  echo "✅ Success! react-scripts installed"
  ls -la node_modules/.bin/react-scripts
else
  echo "❌ Failed to install react-scripts"
  echo "Checking node_modules..."
  ls node_modules/ | grep -i script
fi
