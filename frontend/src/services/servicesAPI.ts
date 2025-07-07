import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000,
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

// const API_BASE_URL = "https://cool-slate.ayating.lol/api";
const API_BASE_URL = "https://coolslate.ayating.lol/api";

// 服務類型對照表：前端中文 -> 後端英文
const SERVICE_TYPE_MAP = {
  新機安裝: "INSTALLATION",
  冷氣保養: "MAINTENANCE",
  冷氣維修: "REPAIR",
} as const;

// 反向對照：後端英文 -> 前端中文
const SERVICE_TYPE_REVERSE_MAP = {
  INSTALLATION: "新機安裝",
  MAINTENANCE: "冷氣保養",
  REPAIR: "冷氣維修",
} as const;

export interface SlotDetail {
  time: string;
  available_workers: number;
}

export interface CalendarDay {
  date: string;
  available_slots: SlotDetail[];
  is_available_for_booking: boolean;
  is_weekend: boolean;
}

export interface CalendarResponse {
  service_type: string;
  days: CalendarDay[];
  booking_range: {
    from_date: string;
    to_date: string;
  };
  current_month: number;
  current_year: number;
}

export interface ServiceTypeInfo {
  name: string;
  required_workers: number;
  base_duration_hours: number;
  additional_duration_hours: number;
  booking_advance_months: number;
  pricing_type: string;
}

export interface UnifiedCalendarResponse {
  calendar_data: Record<string, Record<string, boolean>>;
  current_month: number;
  current_year: number;
}

export interface BookingFeasibilityResponse {
  is_bookable: boolean;
  service_info: {
    service_type: string;
    unit_count: number;
    required_hours: number;
    required_workers: number;
  };
  time_slots: Array<{
    time: string;
    available_workers: number;
    required_workers: number;
  }>;
  estimated_end_time: string;
}

export interface UnitsCheckResponse {
  can_book: boolean;
  requested_units: number;
  max_available: number;
}

export interface EquipmentItem {
  name: string;
  model: string;
  price: number;
  quantity: number;
}

export interface BookingSlot {
  preferred_date: string;
  preferred_time: string;
  contact_name: string;
  contact_phone: string;
}

export interface OrderRequest {
  service_type: string;
  location_address: string;
  location_lat?: number;
  location_lng?: number;
  unit_count: number;
  notes?: string;
  booking_slots: BookingSlot[];
  equipment_details?: EquipmentItem[];
}

export interface OrderResponse {
  order_id: number;
  order_number: string;
  total_amount: number;
  booking_slots: Array<{
    date: string;
    time: string;
    contact_name: string;
    contact_phone: string;
    is_primary: boolean;
    is_available: boolean;
  }>;
  status: string;
  service_type: string;
}

export interface ProductResponse {
  id: number;
  name: string;
  model: string;
  price: number;
  image: string;
  description?: string;
  category: string;
  is_active: boolean;
}

const toBackendServiceType = (frontendType: string): string => {
  const mapped =
    SERVICE_TYPE_MAP[frontendType as keyof typeof SERVICE_TYPE_MAP];
  if (!mapped) {
    return frontendType;
  }

  return mapped;
};

export const toFrontendServiceType = (backendType: string): string => {
  const mapped =
    SERVICE_TYPE_REVERSE_MAP[
      backendType as keyof typeof SERVICE_TYPE_REVERSE_MAP
    ];
  if (!mapped) {
    return backendType;
  }
  return mapped;
};

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
        console.error(`Error Response:`, errorText);

        const errorData = JSON.parse(errorText);
        errorMessage = errorData.detail || errorData.message || errorText;
      } catch (parseError) {
        console.error("無法解析錯誤:", parseError);
      }

      throw new Error(errorMessage);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error(`API Failed:`, error);

    if (error instanceof TypeError && error.message.includes("fetch")) {
      throw new Error("網路連線失敗");
    }

    throw error;
  }
}

export const getServiceTypes = async (): Promise<ServiceTypeInfo[]> => {
  const data = await apiCall<ServiceTypeInfo[]>("/calendar/service", {}, false);

  return data.map((service) => ({
    ...service,
    name: toFrontendServiceType(service.name),
  }));
};

export const getServiceCalendar = async (
  serviceType: string,
  year?: number,
  month?: number
): Promise<CalendarResponse> => {
  const backendServiceType = toBackendServiceType(serviceType);

  const params = new URLSearchParams();
  if (year) params.set("year", year.toString());
  if (month) params.set("month", month.toString());

  const queryString = params.toString();
  const endpoint = `/calendar/${encodeURIComponent(backendServiceType)}${
    queryString ? `?${queryString}` : ""
  }`;

  const data = await apiCall<CalendarResponse>(endpoint, {}, false);

  return {
    ...data,
    service_type: toFrontendServiceType(data.service_type),
  };
};

export const getUnifiedCalendar = async (
  year?: number,
  month?: number
): Promise<UnifiedCalendarResponse> => {
  const params = new URLSearchParams();
  if (year) params.set("year", year.toString());
  if (month) params.set("month", month.toString());

  const endpoint = `/calendar/unified${params.toString() ? `?${params}` : ""}`;
  const data = await apiCall<UnifiedCalendarResponse>(endpoint, {}, false);

  const convertedCalendarData: Record<string, Record<string, boolean>> = {};

  Object.entries(data.calendar_data).forEach(([date, services]) => {
    convertedCalendarData[date] = {};
    Object.entries(services).forEach(([serviceType, isAvailable]) => {
      const frontendServiceType = toFrontendServiceType(serviceType);
      convertedCalendarData[date][frontendServiceType] = isAvailable;
    });
  });

  return {
    ...data,
    calendar_data: convertedCalendarData,
  };
};

export const checkBookingFeasibility = async (
  targetDate: string,
  targetTime: string,
  serviceType: string,
  unitCount: number
): Promise<BookingFeasibilityResponse> => {
  const backendServiceType = toBackendServiceType(serviceType);

  const params = new URLSearchParams({
    target_date: targetDate,
    target_time: targetTime,
    service_type: backendServiceType,
    unit_count: unitCount.toString(),
  });

  const data = await apiCall<BookingFeasibilityResponse>(
    `/calendar/check-booking?${params}`,
    {},
    false
  );

  return {
    ...data,
    service_info: {
      ...data.service_info,
      service_type: toFrontendServiceType(data.service_info.service_type),
    },
  };
};

export const checkUnitsAvailability = async (
  targetDate: string,
  targetTime: string,
  serviceType: string,
  unitCount: number
): Promise<UnitsCheckResponse> => {
  const backendServiceType = toBackendServiceType(serviceType);

  const params = new URLSearchParams({
    target_date: targetDate,
    target_time: targetTime,
    service_type: backendServiceType,
    unit_count: unitCount.toString(),
  });

  return apiCall<UnitsCheckResponse>(
    `/calendar/check-units?${params}`,
    {},
    false
  );
};

export const createOrder = async (
  orderData: OrderRequest
): Promise<OrderResponse> => {
  const backendOrderData = {
    ...orderData,
    service_type: toBackendServiceType(orderData.service_type),
    unit_count: Number(orderData.unit_count),
    notes: orderData.notes?.trim() || undefined,
    location_lat: orderData.location_lat || undefined,
    location_lng: orderData.location_lng || undefined,
  };

  const data = await apiCall<OrderResponse>(
    "/order",
    {
      method: "POST",
      body: JSON.stringify(backendOrderData),
    },
    true
  );

  return {
    ...data,
    service_type: toFrontendServiceType(data.service_type),
  };
};

export const getProducts = async (): Promise<ProductResponse[]> => {
  return await apiCall<ProductResponse[]>("/products", {}, false);
};
