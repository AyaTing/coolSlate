const API_BASE_URL = "https://cool-slate.ayating.lol/api";
// const API_BASE_URL = "http://0.0.0.0:8000/api";

export interface CheckoutSessionRequest {
  order_id: number;
}

export interface CheckoutSessionResponse {
  session_url: string;
  session_id: string;
  order_id: number;
  expires_at: string;
}

export interface PaymentStatusResponse {
  order_id: number;
  order_number: string;
  payment_status: "unpaid" | "paid" | "refunded";
  order_status: string;
  total_amount: number;
  created_at: string;
  updated_at: string;
}

export const createCheckoutSession = async (
  orderId: number
): Promise<CheckoutSessionResponse> => {
  const token = localStorage.getItem("auth_token");
  const headers: { [key: string]: string } = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(
    `${API_BASE_URL}/payment/create-checkout-session`,
    {
      method: "POST",
      headers,
      body: JSON.stringify({ order_id: orderId }),
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "創建付款頁面失敗");
  }

  return response.json();
};

export const getPaymentStatus = async (
  orderId: number
): Promise<PaymentStatusResponse> => {
  const token = localStorage.getItem("auth_token");
  const headers: { [key: string]: string } = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}/payment/status/${orderId}`, {
    headers,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "查詢付款狀態失敗");
  }

  return response.json();
};
