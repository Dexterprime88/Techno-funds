export const getCredentials = async () => {
  const response = await fetch('/auth/credentials');
  return await response.json();
};

export const setCredentials = async (credentials) => {
  const response = await fetch('/auth/credentials', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(credentials),
  });
  return await response.json();
};

export const generateAccessToken = async (apiKey, apiSecret, requestToken) => {
  const response = await fetch('/auth/generate-token', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      api_key: apiKey,
      api_secret: apiSecret,
      request_token: requestToken,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Failed to generate access token');
  }

  return await response.json();
};

export const getOptionChain = async (instrument) => {
  const response = await fetch(`/kite/option-chain/${instrument}`);
  return await response.json();
};
