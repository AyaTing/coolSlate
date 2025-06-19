// const API_BASE_URL = "https://cool-slate.ayating.lol/api";
const API_BASE_URL = "https://coolslate.ayating.lol/api";

export interface OrderDetail {
  order_id: number;
  order_number: string;
  user_id: number;
  service_type: string;
  location_address: string;
  location_lat?: number;
  location_lng?: number;
  total_amount: number;
  status: string;
  payment_status: string;
  equipment_details?: Array<{ [k: string]: string }>;
  notes?: string;
  booking_slots: Array<{
    preferred_date: string;
    preferred_time: string;
    contact_name: string;
    contact_phone: string;
    is_primary: boolean;
    is_selected: boolean;
  }>;
  created_at: string;
  updated_at: string;
  scheduling_feedback?: string;
}

const PAYMENT_STATUS_MAP = {
  paid: "已付款",
  unpaid: "未付款",
  refunded: "已退款",
} as const;

const ORDER_STATUS_MAP = {
  pending: "預約中，等待付款",
  pending_schedule: "預約中，等待排程",
  scheduled: "已排程",
  completed: "已完成",
  cancelled: "已取消",
  precancel: "取消申請中",
  scheduling_failed: "排程失敗",
} as const;

export function toFrontendPaymentStatus(backendStatus: string): string {
  return (
    PAYMENT_STATUS_MAP[backendStatus as keyof typeof PAYMENT_STATUS_MAP] ||
    backendStatus
  );
}

export function toFrontendOrderStatus(backendStatus: string): string {
  return (
    ORDER_STATUS_MAP[backendStatus as keyof typeof ORDER_STATUS_MAP] ||
    backendStatus
  );
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

export const getUserOrders = async (): Promise<OrderDetail[]> => {
  return apiCall<OrderDetail[]>(
    "/orders",
    {
      method: "GET",
    },
    true
  );
};

export const getOrderDetail = async (orderId: number): Promise<OrderDetail> => {
  return apiCall<OrderDetail>(
    `/order/${orderId}`,
    {
      method: "GET",
    },
    true
  );
};

export const requestCancelOrder = async (
  orderId: number
): Promise<{ message: string }> => {
  return apiCall<{ message: string }>(
    `/order/${orderId}/cancel-request`,
    { method: "PATCH" },
    true
  );
};
