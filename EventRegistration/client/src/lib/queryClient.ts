import { QueryClient, QueryFunction } from "@tanstack/react-query";

async function throwIfResNotOk(res: Response) {
  if (!res.ok) {
    const text = (await res.text()) || res.statusText;
    throw new Error(`${res.status}: ${text}`);
  }
}

// Generiere eine zufällige API-Token für die aktuelle Browsersitzung, um CSRF-Angriffe zu verhindern
const API_TOKEN = sessionStorage.getItem('api_security_token') || 
  Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);

// Token in sessionStorage speichern, wenn es neu ist
if (!sessionStorage.getItem('api_security_token')) {
  sessionStorage.setItem('api_security_token', API_TOKEN);
}

export async function apiRequest(
  method: string,
  url: string,
  data?: unknown | undefined,
): Promise<Response> {
  const res = await fetch(url, {
    method,
    headers: {
      ...(data ? { "Content-Type": "application/json" } : {}),
      "X-Security-Token": API_TOKEN, // Sicherheitstoken für CSRF-Schutz hinzufügen
      "X-Client-Version": "1.0.0"    // Client-Version für API-Versionsvalidierung
    },
    body: data ? JSON.stringify(data) : undefined,
    credentials: "include",
  });

  await throwIfResNotOk(res);
  return res;
}

type UnauthorizedBehavior = "returnNull" | "throw";
export const getQueryFn: <T>(options: {
  on401: UnauthorizedBehavior;
}) => QueryFunction<T> =
  ({ on401: unauthorizedBehavior }) =>
  async ({ queryKey }) => {
    const res = await fetch(queryKey[0] as string, {
      credentials: "include",
      headers: {
        "X-Security-Token": API_TOKEN, // Konsistenten Token für alle API-Anfragen verwenden
        "X-Client-Version": "1.0.0"    // Client-Version für API-Versionsvalidierung
      }
    });

    if (unauthorizedBehavior === "returnNull" && res.status === 401) {
      return null;
    }

    await throwIfResNotOk(res);
    return await res.json();
  };

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      queryFn: getQueryFn({ on401: "throw" }),
      refetchInterval: false,
      refetchOnWindowFocus: false,
      staleTime: Infinity,
      retry: false,
    },
    mutations: {
      retry: false,
    },
  },
});
