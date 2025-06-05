const API_BASE_URL = "https://cool-slate.ayating.lol/api";
// const API_BASE_URL = "http://0.0.0.0:8000/api";

export interface User {
  id: number;
  email: string;
  name: string;
  role: string;
}

export interface LoginResponse {
  user: User;
  token: string;
}

async function apiCall<T>(
  endpoint: string,
  options?: RequestInit,
  requireAuth = false
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
    ...((options?.headers as Record<string, string>) || {}),
  };

  if (requireAuth) {
    const token = localStorage.getItem("auth_token");
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    } else {
      throw new Error("找不到認證 token，請重新登入");
    }
  }
  try {
    const response = await fetch(url, {
      ...options,
      headers,
      credentials: "omit", // 不使用 cookies
    });
    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}`;
      try {
        const errorText = await response.text();
        console.error(`錯誤回應:`, errorText);
        const errorData = JSON.parse(errorText);
        errorMessage = errorData.detail || errorData.message || errorText;
      } catch (parseError) {
        console.error("無法解析錯誤訊息:", parseError);
      }
      throw new Error(errorMessage);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error(`API連接失敗:`, error);
    if (error instanceof TypeError && error.message.includes("fetch")) {
      throw new Error("網路連線失敗，請檢查網路連線");
    }

    throw error;
  }
}

export const googleLogin = async (idToken: string): Promise<LoginResponse> => {
  return apiCall<LoginResponse>("/login", {
    method: "POST",
    body: JSON.stringify(idToken),
  });
};

export const getCurrentUser = async (): Promise<User> => {
  return apiCall<User>(
    "/user",
    {
      method: "GET",
    },
    true
  );
};

export const logout = async (): Promise<{ message: string }> => {
  return apiCall<{ message: string }>(
    "/logout",
    {
      method: "POST",
    },
    true
  );
};
