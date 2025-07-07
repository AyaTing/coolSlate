import { type CalendarDay } from "../services/servicesAPI.ts";

interface CalendarProps {
  days: CalendarDay[];
  currentYear: number;
  currentMonth: number;
  selectedService: string;
  unifiedData?: Record<string, Record<string, boolean>>;
  onDateSelect?: (date: string) => void;
  onMonthChange?: (year: number, month: number) => void;
  isLoading?: boolean;
}

const Calendar = ({
  days,
  currentYear,
  currentMonth,
  selectedService,
  unifiedData,
  onDateSelect,
  onMonthChange,
  isLoading,
}: CalendarProps) => {
  const firstDayOfMonth = new Date(currentYear, currentMonth - 1, 1).getDay();

  const monthNames = [
    "一月",
    "二月",
    "三月",
    "四月",
    "五月",
    "六月",
    "七月",
    "八月",
    "九月",
    "十月",
    "十一月",
    "十二月",
  ];

  const weekDays = ["日", "一", "二", "三", "四", "五", "六"];

  const goToPreviousMonth = () => {
    if (currentMonth === 1) {
      onMonthChange?.(currentYear - 1, 12);
    } else {
      onMonthChange?.(currentYear, currentMonth - 1);
    }
  };

  const goToNextMonth = () => {
    if (currentMonth === 12) {
      onMonthChange?.(currentYear + 1, 1);
    } else {
      onMonthChange?.(currentYear, currentMonth + 1);
    }
  };

  const goToCurrentMonth = () => {
    const now = new Date();
    onMonthChange?.(now.getFullYear(), now.getMonth() + 1);
  };

  const emptyDays = Array.from({ length: firstDayOfMonth }, (_, i) => i);

  return (
    <div className="bg-white rounded-lg shadow-sm border">
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-4">
          <h3 className="text-lg font-semibold text-gray-800">
            {currentYear} 年 {monthNames[currentMonth - 1]}
          </h3>
          {isLoading && (
            <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={goToPreviousMonth}
            disabled={isLoading}
            className="p-2 rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50 transition-colors"
            title="上一個月"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            </svg>
          </button>

          <button
            onClick={goToCurrentMonth}
            disabled={isLoading}
            className="px-3 py-1 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 transition-colors"
            title="回到本月"
          >
            本月
          </button>

          <button
            onClick={goToNextMonth}
            disabled={isLoading}
            className="p-2 rounded-lg border border-gray-300 hover:bg-gray-50 disabled:opacity-50 transition-colors"
            title="下一個月"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5l7 7-7 7"
              />
            </svg>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-7 gap-0 border-b">
        {weekDays.map((day) => (
          <div
            key={day}
            className="p-3 text-center text-sm font-medium text-gray-600 bg-gray-50"
          >
            {day}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-7 gap-0">
        {emptyDays.map((_, index) => (
          <div
            key={`empty-${index}`}
            className="h-15 md:h-20 border-r border-b border-gray-100"
          />
        ))}

        {days.map((day) => {
          const dayNumber = new Date(day.date).getDate();
          const hasSlots = day.available_slots.length > 0;
          const isBookable = day.is_available_for_booking;
          const dateStr = day.date;

          const otherServicesStatus = unifiedData?.[dateStr] || {};
          const allServices = ["新機安裝", "冷氣保養", "冷氣維修"];
          const conflictingServices = allServices.filter(
            (service) =>
              service !== selectedService &&
              otherServicesStatus[service] === false
          );

          return (
            <div
              key={day.date}
              className={`h-15 md:h-20 border-r border-b border-gray-100 p-2 cursor-pointer transition-colors relative ${
                isBookable
                  ? "hover:bg-blue-50 hover:border-blue-200"
                  : "bg-gray-50"
              } ${day.is_weekend ? "bg-red-50" : ""}`}
              onClick={() => isBookable && onDateSelect?.(day.date)}
            >
              <div className="flex flex-col h-full">
                <div
                  className={`text-sm font-medium ${
                    day.is_weekend ? "text-red-600" : "text-gray-700"
                  } ${isBookable ? "text-blue-600" : "text-gray-400"}`}
                >
                  {dayNumber}
                </div>

                {isBookable && (
                  <div className="flex-1 flex flex-col justify-center items-center">
                    <div className="w-2 h-2 bg-green-500 rounded-full mb-1"></div>
                    <div className="hidden md:block text-xs text-green-600 text-center ">
                      {hasSlots
                        ? `${day.available_slots.length}時段`
                        : "可預約"}
                    </div>
                  </div>
                )}

                {isBookable && conflictingServices.length > 0}

                {day.is_weekend && !isBookable && (
                  <div className="flex-1 flex items-center justify-center">
                    <div className="text-xs text-red-400">週末</div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="p-4 border-t bg-gray-50">
        <div className="flex flex-wrap gap-4 text-xs">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-green-500 rounded-full"></div>
            <span>可預約</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-red-100 rounded"></div>
            <span>週末</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 bg-gray-200 rounded"></div>
            <span>不可預約</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Calendar;
