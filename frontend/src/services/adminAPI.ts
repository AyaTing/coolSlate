import { type OrderDetail } from "../services/orderAPI";
import { type User } from "../services/authAPI";
const API_BASE_URL = "https://cool-slate.ayating.lol/api";

interface AdminOrdersResponse {
  orders: OrderDetail[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

interface AdminUsersResponse {
  users: User[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

interface AdminUserOrdersResponse {
  user: { id: number; name: string; email: string };
  orders: OrderDetail[];
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

export const getAllUsers = async (params?: {
  page?: number;
  limit?: number;
  search?: string;
}): Promise<AdminUsersResponse> => {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", params.page.toString());
  if (params?.limit) searchParams.set("limit", params.limit.toString());
  if (params?.search) searchParams.set("search", params.search);
  const endpoint = `/admin/users${
    searchParams.toString() ? `?${searchParams}` : ""
  }`;
  return apiCall<AdminUsersResponse>(endpoint, {}, true);
};

export const getAllOrders = async (params?: {
  status?: string;
  payment_status?: string;
  page?: number;
  limit?: number;
}): Promise<AdminOrdersResponse> => {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.payment_status)
    searchParams.set("payment_status", params.payment_status);
  if (params?.page) searchParams.set("page", params.page.toString());
  if (params?.limit) searchParams.set("limit", params.limit.toString());
  const endpoint = `/admin/orders${
    searchParams.toString() ? `?${searchParams}` : ""
  }`;
  return apiCall<AdminOrdersResponse>(endpoint, {}, true);
};

export const getOrderByAdmin = async (
  orderId: number
): Promise<OrderDetail> => {
  return apiCall<OrderDetail>(`/admin/order/${orderId}`, {}, true);
};

export const getUserOrdersByAdmin = async (
  userId: number
): Promise<AdminUserOrdersResponse> => {
  return apiCall<AdminUserOrdersResponse>(
    `/admin/user/${userId}/orders`,
    {},
    true
  );
};
