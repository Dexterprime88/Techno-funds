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

export const getOptionChain = async (instrument) => {
  const response = await fetch(`/kite/option-chain/${instrument}`);
  return await response.json();
};
