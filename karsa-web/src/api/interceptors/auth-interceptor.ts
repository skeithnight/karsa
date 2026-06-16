export function withAuth(options: RequestInit = {}): RequestInit {
  // TODO: Read token from secure storage or context
  const token = undefined;
  
  if (!token) {
    return options;
  }
  
  return {
    ...options,
    headers: {
      ...options.headers,
      Authorization: `Bearer ${token}`
    }
  };
}
