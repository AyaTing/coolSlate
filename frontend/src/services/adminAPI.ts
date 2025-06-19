import { type OrderDetail } from "../services/orderAPI";
import { type User } from "../services/authAPI";
// const API_BASE_URL = "https://cool-slate.ayating.lol/api";
const API_BASE_URL = "https://coolslate.ayating.lol/api";

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

interface AdminScheduleOrderResponse {
  success: boolean;
  order_id: number;
  schedule_id: number;
  scheduled_date: string;
  scheduled_time: string;
  estimated_end_time: string;
  email_sent: boolean;
}
interface AdminRefundResponse {
  success: boolean;
  message: string;
  refund_user: string;
  refund_time: string;
}
interface AdminCancelOrderResponse {
  success: boolean;
  message: string;
  email_sent: boolean;
}

interface AdminUploadFileResponse {
  success: boolean;
  message: string;
  completion_file_name: string;
  completion_file_url: string;
}

interface AdminCompletionResponse {
  success: boolean;
  message: string;
}

interface AdminGetFileResponse {
  order_id: number;
  order_number: string;
  completion_file_name: string;
  completion_file_url: string;
}

async function apiCall<T>(
  endpoint: string,
  options?: RequestInit,
  requireAuth = false,
  isFormData = false
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...((options?.headers as Record<string, string>) || {}),
  };
  if (!isFormData) {
    headers["Content-Type"] = "application/json";
  }

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

export const scheduleOrderByAdmin = async (
  orderId: number
): Promise<AdminScheduleOrderResponse> => {
  return apiCall<AdminScheduleOrderResponse>(
    `/admin/scheduling/${orderId}`,
    { method: "POST" },
    true
  );
};

export const updateRefundStatusByAdmin = async (
  orderId: number,
  refundUser: string
): Promise<AdminRefundResponse> => {
  return apiCall<AdminRefundResponse>(
    `/admin/order/${orderId}/refund`,
    { method: "PATCH", body: JSON.stringify({ refund_user: refundUser }) },
    true
  );
};

export const cancelOrderByAdmin = async (
  orderId: number
): Promise<AdminCancelOrderResponse> => {
  return apiCall<AdminCancelOrderResponse>(
    `/admin/order/${orderId}/cancel`,
    { method: "POST" },
    true
  );
};

export const uploadCompletionFileByAdmin = async (
  orderId: number,
  file: File
): Promise<AdminUploadFileResponse> => {
  const formData = new FormData();
  formData.append("file", file);
  return apiCall<AdminUploadFileResponse>(
    `/admin/order/${orderId}/completion`,
    { method: "POST", body: formData },
    true,
    true
  );
};

export const updateCompletionStatusByAdmin = async (
  orderId: number
): Promise<AdminCompletionResponse> => {
  return apiCall<AdminCompletionResponse>(
    `/admin/order/${orderId}/completion`,
    { method: "PATCH" },
    true
  );
};

export const getCompletionFileByAdmin = async (
  orderId: number
): Promise<AdminGetFileResponse> => {
  return apiCall<AdminGetFileResponse>(
    `/admin/order/${orderId}/completion`,
    {},
    true
  );
};
