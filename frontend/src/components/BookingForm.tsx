// src/components/BookingForm.tsx
import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  checkUnitsAvailability,
  checkBookingFeasibility,
} from "../services/servicesAPI";

interface EquipmentItem {
  name: string;
  model: string;
  price: number;
  quantity: number;
}

interface BookingSlot {
  preferred_date: string;
  preferred_time: string;
  contact_name: string;
  contact_phone: string;
}

interface BookingFormData {
  service_type: string;
  location_address: string;
  unit_count: number;
  notes: string;
  booking_slots: BookingSlot[];
  equipment_details?: EquipmentItem[];
}

interface BookingFormProps {
  serviceType: string;
  selectedDate: string | null;
  selectedTime: string | null;
  onSubmit: (data: BookingFormData) => void;
  onCancel: () => void;
}

// 模擬商品資料（新機安裝用）
const MOCK_PRODUCTS = [
  {
    name: "大金變頻冷暖氣機",
    model: "FTXS-50LVLT",
    price: 45000,
    image: "🌡️",
    description: "適用4-6坪，一級能效，靜音運轉",
  },
  {
    name: "三菱電機變頻冷氣",
    model: "MSZ-FH35VA",
    price: 38000,
    image: "❄️",
    description: "適用3-5坪，快速冷房，省電節能",
  },
  {
    name: "國際牌變頻冷暖氣",
    model: "CS-UX36BA2",
    price: 42000,
    image: "🔥",
    description: "適用5-7坪，冷暖兼具，智慧控制",
  },
];

const determineRegion = (address: string): string => {
  const keywords = ["台北", "新北"];
  if (keywords.some((keyword) => address.includes(keyword))) {
    return "雙北";
  }
  return "其他地區";
};

const calculatePrice = (
  serviceType: string,
  unitCount: number,
  equipmentItems: EquipmentItem[] = [],
  locationAddress: string
): number => {
  switch (serviceType) {
    case "新機安裝":
      return equipmentItems.reduce(
        (total, item) => total + item.price * item.quantity,
        0
      );
    case "冷氣保養":
      return 2000 + Math.max(0, unitCount - 1) * 1000;
    case "冷氣維修":
      const region = determineRegion(locationAddress);
      return region === "雙北" ? 500 : 1000;
    default:
      return 0;
  }
};

const BookingForm = ({
  serviceType,
  selectedDate,
  selectedTime,
  onSubmit,
  onCancel,
}: BookingFormProps) => {
  const [formData, setFormData] = useState<BookingFormData>({
    service_type: serviceType,
    location_address: "",
    unit_count: 1,
    notes: "",
    booking_slots: [],
    equipment_details: [],
  });

  const [cart, setCart] = useState<EquipmentItem[]>([]);

  const [errors, setErrors] = useState<Record<string, string>>({});

  const { data: unitsCheck } = useQuery({
    queryKey: [
      "check-units",
      selectedDate,
      selectedTime,
      serviceType,
      formData.unit_count,
    ],
    queryFn: () =>
      checkUnitsAvailability(
        selectedDate!,
        selectedTime!,
        serviceType,
        formData.unit_count
      ),
    enabled: !!(
      selectedDate &&
      selectedTime &&
      (serviceType === "新機安裝" || serviceType === "冷氣保養") &&
      formData.unit_count > 0
    ),
    staleTime: 30000,
  });

  const { data: bookingCheck } = useQuery({
    queryKey: [
      "check-booking",
      selectedDate,
      selectedTime,
      serviceType,
      formData.unit_count,
    ],
    queryFn: () =>
      checkBookingFeasibility(
        selectedDate!,
        selectedTime!,
        serviceType,
        formData.unit_count
      ),
    enabled: !!(selectedDate && selectedTime && formData.unit_count > 0),
    staleTime: 30000,
  });

  useEffect(() => {
    if (selectedDate && selectedTime) {
      setFormData((prev) => ({
        ...prev,
        booking_slots: [
          {
            preferred_date: selectedDate,
            preferred_time: selectedTime,
            contact_name: "",
            contact_phone: "",
          },
        ],
      }));
    }
  }, [selectedDate, selectedTime]);

  useEffect(() => {
    setFormData((prev) => ({
      ...prev,
      service_type: serviceType,
      unit_count: serviceType === "新機安裝" ? 1 : prev.unit_count,
      equipment_details: serviceType === "新機安裝" ? [] : undefined,
    }));
    setCart([]);
  }, [serviceType]);

  useEffect(() => {
    if (serviceType === "新機安裝") {
      setFormData((prev) => ({
        ...prev,
        equipment_details: cart,
        unit_count: cart.reduce((total, item) => total + item.quantity, 0),
      }));
    }
  }, [cart, serviceType]);

  const totalAmount = calculatePrice(
    serviceType,
    formData.unit_count,
    serviceType === "新機安裝" ? cart : [],
    formData.location_address
  );

  const updateBasicInfo = (
    field: keyof BookingFormData,
    value: string | number
  ) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }));
    if (field === "location_address" && serviceType === "冷氣維修") {
    }
  };

  const updateContactInfo = (
    field: "contact_name" | "contact_phone",
    value: string
  ) => {
    setFormData((prev) => ({
      ...prev,
      booking_slots: prev.booking_slots.map((slot) => ({
        ...slot,
        [field]: value,
      })),
    }));
  };

  const addToCart = (product: (typeof MOCK_PRODUCTS)[0]) => {
    const existingItem = cart.find((item) => item.model === product.model);

    if (existingItem) {
      setCart(
        cart.map((item) =>
          item.model === product.model
            ? { ...item, quantity: item.quantity + 1 }
            : item
        )
      );
    } else {
      setCart([
        ...cart,
        {
          name: product.name,
          model: product.model,
          price: product.price,
          quantity: 1,
        },
      ]);
    }
  };

  const updateCartQuantity = (model: string, quantity: number) => {
    if (quantity <= 0) {
      setCart(cart.filter((item) => item.model !== model));
    } else {
      setCart(
        cart.map((item) =>
          item.model === model ? { ...item, quantity } : item
        )
      );
    }
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.location_address.trim()) {
      newErrors.location_address = "請輸入服務地址";
    }

    if (!selectedDate || !selectedTime) {
      newErrors.slot = "請選擇預約時段";
    }

    if (formData.booking_slots.length > 0) {
      const slot = formData.booking_slots[0];
      if (!slot.contact_name.trim()) {
        newErrors.contact_name = "請輸入聯絡人姓名";
      }
      if (!slot.contact_phone.trim()) {
        newErrors.contact_phone = "請輸入聯絡人電話";
      }
    }
    if (serviceType === "新機安裝" && cart.length === 0) {
      newErrors.equipment = "請至少選擇一項商品";
    }

    if (
      (serviceType === "冷氣保養" || serviceType === "冷氣維修") &&
      formData.unit_count <= 0
    ) {
      newErrors.unit_count = "台數必須大於 0";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (validateForm()) {
      onSubmit(formData);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 max-h-[80vh] overflow-y-auto">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-semibold text-[var(--color-text-primary)]">
          預約 {serviceType}
        </h3>
        <button
          onClick={onCancel}
          className="text-gray-500 hover:text-gray-700 p-2"
          title="關閉"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {selectedDate && selectedTime && (
          <div
            className={`border rounded-lg p-4 ${
              bookingCheck && !bookingCheck.is_bookable
                ? "bg-red-50 border-red-200"
                : "bg-blue-50 border-blue-200"
            }`}
          >
            <h4
              className={`font-medium mb-2 ${
                bookingCheck && !bookingCheck.is_bookable
                  ? "text-red-800"
                  : "text-blue-800"
              }`}
            >
              預約時段
            </h4>
            <p
              className={
                bookingCheck && !bookingCheck.is_bookable
                  ? "text-red-700"
                  : "text-blue-700"
              }
            >
              {selectedDate} {selectedTime}
            </p>
            {bookingCheck && !bookingCheck.is_bookable && (
              <p className="text-red-600 text-sm mt-1">
                ⚠️ 此時段可能無法預約，建議選擇其他時段
              </p>
            )}
          </div>
        )}

        {errors.slot && <p className="text-red-500 text-sm">{errors.slot}</p>}

        <div className="space-y-4">
          <h4 className="font-medium text-[var(--color-text-primary)]">
            基本資訊
          </h4>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              服務地址 <span className="text-red-500">*</span>
            </label>
            <textarea
              value={formData.location_address}
              onChange={(e) =>
                updateBasicInfo("location_address", e.target.value)
              }
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                errors.location_address ? "border-red-500" : "border-gray-300"
              }`}
              placeholder="請輸入詳細地址"
              rows={2}
            />
            {errors.location_address && (
              <p className="text-red-500 text-sm mt-1">
                {errors.location_address}
              </p>
            )}
          </div>

          {(serviceType === "冷氣保養" || serviceType === "冷氣維修") && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                台數 <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                min="1"
                max="8"
                value={formData.unit_count}
                onChange={(e) =>
                  updateBasicInfo("unit_count", parseInt(e.target.value) || 1)
                }
                className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                  errors.unit_count ? "border-red-500" : "border-gray-300"
                }`}
              />

              {serviceType === "冷氣保養" &&
                unitsCheck &&
                !unitsCheck.can_book && (
                  <div className="mt-2 p-3 rounded-lg text-sm bg-red-50 border border-red-200 text-red-700">
                    ❌ 無法預約 {formData.unit_count} 台，最多可預約{" "}
                    {unitsCheck.max_available} 台
                    <button
                      type="button"
                      onClick={() =>
                        updateBasicInfo("unit_count", unitsCheck.max_available)
                      }
                      className="ml-2 text-blue-600 hover:text-blue-800 underline"
                    >
                      調整為 {unitsCheck.max_available} 台
                    </button>
                  </div>
                )}

              {errors.unit_count && (
                <p className="text-red-500 text-sm mt-1">{errors.unit_count}</p>
              )}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              備註
            </label>
            <textarea
              value={formData.notes}
              onChange={(e) => updateBasicInfo("notes", e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="其他需求或注意事項"
              rows={3}
            />
          </div>
        </div>

        {serviceType === "新機安裝" && (
          <div className="space-y-4">
            <h4 className="font-medium text-[var(--color-text-primary)]">
              選擇商品
            </h4>

            {errors.equipment && (
              <p className="text-red-500 text-sm">{errors.equipment}</p>
            )}

            <div className="grid gap-4">
              {MOCK_PRODUCTS.map((product) => (
                <div
                  key={product.model}
                  className="border border-gray-200 rounded-lg p-4"
                >
                  <div className="flex items-start gap-2 md:gap-4">
                    <div className="text-lg md:text-4xl">{product.image}</div>
                    <div className="flex-1">
                      <h5 className="font-medium text-gray-900">
                        {product.name}
                      </h5>
                      <p className="text-sm text-gray-500">{product.model}</p>
                      <p className="text-sm text-gray-600 mt-1">
                        {product.description}
                      </p>
                      <p className="text-lg font-semibold text-[var(--color-brand-primary)] mt-2">
                        NT$ {product.price.toLocaleString()}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => addToCart(product)}
                      className="px-4 py-2 bg-[var(--color-brand-primary)] text-white rounded-lg hover:opacity-90 text-sm"
                    >
                      加入
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {cart.length > 0 && (
              <div className="border-t pt-4">
                <h5 className="font-medium text-gray-900 mb-3">已選商品</h5>

                {unitsCheck && !unitsCheck.can_book && (
                  <div className="mb-3 p-3 rounded-lg text-sm bg-red-50 border border-red-200 text-red-700">
                    ❌ 無法安裝 {formData.unit_count} 台，此時段最多可安裝{" "}
                    {unitsCheck.max_available} 台
                    <div className="mt-1 text-xs">
                      請減少商品數量或選擇其他時段
                    </div>
                  </div>
                )}

                <div className="space-y-2">
                  {cart.map((item) => (
                    <div
                      key={item.model}
                      className="flex-col space-y-1 md:flex-row flex items-center justify-between bg-gray-50 p-3 rounded-lg"
                    >
                      <div>
                        <p className="font-medium">{item.name}</p>
                        <p className="text-sm text-gray-500">{item.model}</p>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() =>
                              updateCartQuantity(item.model, item.quantity - 1)
                            }
                            className="w-8 h-8 border border-gray-300 rounded flex items-center justify-center hover:bg-gray-100"
                          >
                            -
                          </button>
                          <span className="w-8 text-center">
                            {item.quantity}
                          </span>
                          <button
                            type="button"
                            onClick={() =>
                              updateCartQuantity(item.model, item.quantity + 1)
                            }
                            className="w-8 h-8 border border-gray-300 rounded flex items-center justify-center hover:bg-gray-100"
                          >
                            +
                          </button>
                        </div>
                        <p className="font-medium min-w-[80px] text-right">
                          NT$ {(item.price * item.quantity).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        <div className="space-y-4">
          <h4 className="font-medium text-[var(--color-text-primary)]">
            聯絡人資訊
          </h4>

          <div className="grid md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                聯絡人姓名 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={formData.booking_slots[0]?.contact_name || ""}
                onChange={(e) =>
                  updateContactInfo("contact_name", e.target.value)
                }
                className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                  errors.contact_name ? "border-red-500" : "border-gray-300"
                }`}
                placeholder="聯絡人姓名"
              />
              {errors.contact_name && (
                <p className="text-red-500 text-sm mt-1">
                  {errors.contact_name}
                </p>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                聯絡人電話 <span className="text-red-500">*</span>
              </label>
              <input
                type="tel"
                value={formData.booking_slots[0]?.contact_phone || ""}
                onChange={(e) =>
                  updateContactInfo("contact_phone", e.target.value)
                }
                className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                  errors.contact_phone ? "border-red-500" : "border-gray-300"
                }`}
                placeholder="09xxxxxxxx"
              />
              {errors.contact_phone && (
                <p className="text-red-500 text-sm mt-1">
                  {errors.contact_phone}
                </p>
              )}
            </div>
          </div>
        </div>
        <div className="border-t pt-4">
          <div className="flex justify-between items-center">
            <span className="text-lg font-medium">預估總金額</span>
            <span className="text-2xl font-bold text-[var(--color-brand-primary)]">
              NT$ {totalAmount.toLocaleString()}
            </span>
          </div>
          {serviceType === "冷氣維修" && (
            <p className="text-sm text-gray-500 mt-1">
              * 實際費用將根據維修內容調整
            </p>
          )}
        </div>

        <div className="flex gap-3 pt-4">
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          >
            取消
          </button>
          <button
            type="submit"
            className="flex-1 px-4 py-2 bg-[var(--color-brand-primary)] text-[var(--color-text-secondary)] rounded-lg hover:opacity-90 transition-colors"
          >
            確認預約
          </button>
        </div>
      </form>
    </div>
  );
};

export default BookingForm;
