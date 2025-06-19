import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  getServiceCalendar,
  getUnifiedCalendar,
  getServiceTypes,
  type OrderRequest,
} from "../services/servicesAPI.ts";
import Calendar from "../components/Calendar";
import BookingForm from "../components/BookingForm";
import { useBooking } from "../hooks/useBooking";
import PaymentModal from "../components/PaymentModal";
import { useAuth } from "../context/AuthContext";
import LoginModal from "../components/LoginModal";

type ServiceType = "新機安裝" | "冷氣保養" | "冷氣維修";

interface BookingFormData {
  service_type: string;
  location_address: string;
  unit_count: number;
  notes: string;
  booking_slots: Array<{
    preferred_date: string;
    preferred_time: string;
    contact_name: string;
    contact_phone: string;
  }>;
  equipment_details?: Array<{
    name: string;
    model: string;
    price: number;
    quantity: number;
  }>;
}

const ServicePage = () => {
  const [selectedService, setSelectedService] =
    useState<ServiceType>("新機安裝");
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [selectedTime, setSelectedTime] = useState<string | null>(null);
  const [isBookingFormOpen, setIsBookingFormOpen] = useState(false);

  const { isAuthenticated } = useAuth();
  const [showLoginModal, setShowLoginModal] = useState(false);

  const currentDate = new Date();
  const [currentYear, setCurrentYear] = useState(currentDate.getFullYear());
  const [currentMonth, setCurrentMonth] = useState(currentDate.getMonth() + 1);

  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [orderIdForPayment, setOrderIdForPayment] = useState<number | null>(
    null
  );

  const serviceTypeOptions: ServiceType[] = [
    "新機安裝",
    "冷氣保養",
    "冷氣維修",
  ];

  const {
    createBooking,
    isLoading: isSubmitting,
    isSuccess,
    isError,
    errorMessage,
    data,
    reset,
  } = useBooking();

  const { data: serviceTypes } = useQuery({
    queryKey: ["service-types"],
    queryFn: getServiceTypes,
    staleTime: 5 * 60 * 1000,
  });

  const { data: unifiedCalendarData } = useQuery({
    queryKey: ["unified-calendar", currentYear, currentMonth],
    queryFn: () => getUnifiedCalendar(currentYear, currentMonth),
    staleTime: 2 * 60 * 1000,
  });

  const {
    data: calendarData,
    isLoading,
    error: calendarError,
    isError: isCalendarError,
  } = useQuery({
    queryKey: ["calendar", selectedService, currentYear, currentMonth],
    queryFn: () => {
      return getServiceCalendar(selectedService, currentYear, currentMonth);
    },
    enabled: !!selectedService,
  });

  const selectedDayData = selectedDate
    ? calendarData?.days.find((day) => day.date === selectedDate)
    : null;

  const handleDateSelect = (date: string) => {
    setSelectedDate(date);
    setSelectedTime(null);
  };

  const handleMonthChange = (year: number, month: number) => {
    setCurrentYear(year);
    setCurrentMonth(month);
    setSelectedDate(null);
    setSelectedTime(null);
  };

  const handleTimeSlotSelect = async (time: string) => {
    setSelectedTime(time);
    if (!isAuthenticated) {
      setShowLoginModal(true);
      return;
    }
    setIsBookingFormOpen(true);
  };

  const handleLoginSuccess = () => {
    setShowLoginModal(false);
    setIsBookingFormOpen(true);
  };

  const handleBookingSubmit = (formData: BookingFormData) => {
    console.log("提交預約資料：", formData);

    const orderRequest: OrderRequest = {
      service_type: selectedService,
      location_address: formData.location_address,
      unit_count: formData.unit_count,
      notes: formData.notes || undefined,
      booking_slots: formData.booking_slots,
      equipment_details: formData.equipment_details || undefined,
    };

    createBooking(orderRequest);
  };

  const handleBookingCancel = () => {
    setIsBookingFormOpen(false);
    reset();
  };

  useEffect(() => {
    if (isSuccess && data) {
      setOrderIdForPayment(data.order_id);
      setShowPaymentModal(true);
      setIsBookingFormOpen(false);
    }
  }, [isSuccess, data]);

  const handlePaymentSuccess = () => {
    alert(`付款完成！感謝您的預約。`);
    setShowPaymentModal(false);
    setOrderIdForPayment(null);
    setSelectedDate(null);
    setSelectedTime(null);
    setIsBookingFormOpen(false);
    reset();
  };

  const handlePaymentCancel = () => {
    setShowPaymentModal(false);
    setOrderIdForPayment(null);
  };

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl md:text-4xl font-bold text-[var(--color-text-primary)] mb-4">
            冷氣服務預約
          </h1>
        </div>

        <div className="mb-8">
          <div className="flex flex-wrap gap-4 justify-center">
            {serviceTypeOptions.map((serviceName) => {
              const serviceInfo = serviceTypes?.find(
                (s) => s.name === serviceName
              );

              return (
                <button
                  key={serviceName}
                  onClick={() => {
                    setSelectedService(serviceName);
                    setSelectedDate(null);
                    setSelectedTime(null);
                    setIsBookingFormOpen(false);
                  }}
                  disabled={isLoading}
                  className={`px-4 md:px-6 py-3 rounded-lg font-medium transition-all disabled:opacity-50 ${
                    selectedService === serviceName
                      ? "bg-[var(--color-brand-primary)] text-[var(--color-text-secondary)] shadow-lg"
                      : "bg-[var(--color-bg-card)] text-[var(--color-text-primary)] hover:bg-[var(--color-brand-primary-light)] hover:shadow-md"
                  }`}
                >
                  {serviceName}
                  {serviceInfo && (
                    <span className="block text-xs opacity-75">
                      {serviceInfo.pricing_type === "unit_count" &&
                        "按台數計費"}
                      {serviceInfo.pricing_type === "location" && "按單次計費"}
                      {serviceInfo.pricing_type === "equipment" && "按設備計費"}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        <div className="bg-gradient-to-br from-[var(--color-brand-primary-light)]/10 via-transparent to-[var(--color-bg-main))  rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-6 text-[var(--color-text-primary)]">
            選擇 {selectedService} 的預約時段
          </h2>

          {isCalendarError && (
            <div className="text-center py-12">
              <p className="text-red-500 mb-4">
                載入失敗：{calendarError?.message || "未知錯誤"}
              </p>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-[var(--color-brand-primary)] text-[var(--color-text-secondary)] rounded-lg hover:opacity-90"
              >
                重新載入
              </button>
            </div>
          )}

          {(calendarData || isLoading) && !isCalendarError && (
            <div className="grid lg:grid-cols-2 gap-8">
              <div>
                <Calendar
                  days={calendarData?.days || []}
                  currentYear={currentYear}
                  currentMonth={currentMonth}
                  selectedService={selectedService}
                  unifiedData={unifiedCalendarData?.calendar_data}
                  onDateSelect={handleDateSelect}
                  onMonthChange={handleMonthChange}
                  isLoading={isLoading}
                />
              </div>

              <div>
                {!isBookingFormOpen ? (
                  <div className="bg-[var(--color-bg-card)] rounded-lg shadow-md p-6">
                    <h3 className="text-xl font-semibold mb-4 text-[var(--color-text-primary)]">
                      可預約時段
                    </h3>

                    {isLoading && (
                      <div className="text-center py-8">
                        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[var(--color-brand-primary)] mx-auto mb-4"></div>
                      </div>
                    )}

                    {!selectedDate && !isLoading && (
                      <div className="text-center py-8 text-[var(--color-text-tertiary)]">
                        <div className="mb-4 flex items-center justify-center">
                          <svg
                            width="48"
                            height="48"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="#d1d5db"
                            stroke-width="2"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                          >
                            <path d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                          </svg>
                        </div>
                        <p>請點擊月曆選擇日期</p>
                      </div>
                    )}

                    {selectedDate &&
                      selectedDayData &&
                      selectedDayData.available_slots.length === 0 &&
                      !isLoading && (
                        <div className="text-center py-8">
                          <p className="text-[var(--color-text-secondary)]">
                            {selectedDate} 沒有可預約的時段
                          </p>
                          <p className="text-sm mt-1 text-gray-500">
                            請選擇其他日期
                          </p>
                        </div>
                      )}

                    {selectedDate &&
                      selectedDayData &&
                      selectedDayData.available_slots.length > 0 &&
                      !isLoading && (
                        <div>
                          <div className="mb-6">
                            <p className="font-medium text-[var(--color-text-primary)]">
                              {selectedDate} (
                              {selectedDayData.is_weekend ? "週末" : "平日"})
                            </p>
                          </div>

                          <div className="space-y-2 max-h-96 overflow-y-auto">
                            {selectedDayData.available_slots.map((slot) => (
                              <div
                                key={slot.time}
                                className="flex items-center justify-between p-3 border border-gray-200 rounded-lg hover:border-[var(--color-brand-primary)] hover:bg-blue-50 transition-colors"
                              >
                                <div>
                                  <p className="font-medium text-[var(--color-text-primary)]">
                                    {typeof slot.time === "string"
                                      ? slot.time.slice(0, 5)
                                      : slot.time}
                                  </p>
                                  <p className="text-sm text-[var(--color-text-tertiary)]">
                                    可用人力：{slot.available_workers} 人
                                  </p>
                                </div>
                                <button
                                  onClick={() =>
                                    handleTimeSlotSelect(
                                      typeof slot.time === "string"
                                        ? slot.time.slice(0, 5)
                                        : slot.time
                                    )
                                  }
                                  className="px-4 py-2 bg-[var(--color-brand-primary)] text-[var(--color-text-secondary)] rounded-md hover:opacity-90 text-sm"
                                >
                                  選擇
                                </button>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                  </div>
                ) : (
                  <div className="relative">
                    <BookingForm
                      serviceType={selectedService}
                      selectedDate={selectedDate}
                      selectedTime={selectedTime}
                      onSubmit={handleBookingSubmit}
                      onCancel={handleBookingCancel}
                    />

                    {isSubmitting && (
                      <div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center rounded-lg">
                        <div className="text-center">
                          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--color-brand-primary)] mx-auto mb-4"></div>
                          <p className="text-[var(--color-text-secondary)]">
                            預約提交中...
                          </p>
                        </div>
                      </div>
                    )}

                    {isError && (
                      <div className="absolute top-4 left-4 right-4 bg-red-50 border border-red-200 rounded-lg p-4">
                        <p className="text-red-600 font-medium">預約失敗</p>
                        <p className="text-red-500 text-sm mt-1">
                          {errorMessage || "未知錯誤，請稍後再試"}
                        </p>
                        <button
                          onClick={reset}
                          className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
                        >
                          重試
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
      <LoginModal
        isOpen={showLoginModal}
        onClose={() => setShowLoginModal(false)}
        onSuccess={handleLoginSuccess}
      />
      {orderIdForPayment && (
        <PaymentModal
          orderId={orderIdForPayment}
          isOpen={showPaymentModal}
          onPaymentSuccess={handlePaymentSuccess}
          onClose={handlePaymentCancel}
        />
      )}
    </div>
  );
};

export default ServicePage;
