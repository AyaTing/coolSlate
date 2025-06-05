import { useQuery } from "@tanstack/react-query";
import {
  createCheckoutSession,
  getPaymentStatus,
} from "../services/paymentAPI";

interface PaymentModalProps {
  orderId: number;
  isOpen: boolean;
  onPaymentSuccess?: () => void;
  onClose?: () => void;
}

const PaymentModal = ({
  orderId,
  isOpen,
  onPaymentSuccess,
  onClose,
}: PaymentModalProps) => {
  if (!isOpen) return null;

  const { data: paymentStatus } = useQuery({
    queryKey: ["payment-status", orderId],
    queryFn: () => getPaymentStatus(orderId),
    refetchInterval: 5000,
  });

  const {
    data: checkoutSession,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["checkout-session", orderId],
    queryFn: () => createCheckoutSession(orderId),
    enabled: !!orderId && paymentStatus?.payment_status === "unpaid",
  });

  const handlePayment = () => {
    if (checkoutSession?.session_url) {
      window.location.href = checkoutSession.session_url;
    }
  };

  return (
    <dialog
      open={isOpen}
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 backdrop:bg-black backdrop:bg-opacity-50"
    >
      <div className="bg-white rounded-xl shadow-2xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <header className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-800">完成付款</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors p-1"
            aria-label="關閉"
          >
            <svg
              className="w-6 h-6"
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
        </header>

        {/* Content */}
        <main className="p-6">
          {/* 付款完成狀態 */}
          {paymentStatus?.payment_status === "paid" && (
            <section className="text-center">
              <div
                className="text-green-500 text-5xl mb-4"
                role="img"
                aria-label="成功"
              >
                ✅
              </div>
              <h3 className="text-xl font-semibold text-gray-800 mb-3">
                付款完成！
              </h3>
              <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
                <p className="text-green-700 font-medium">
                  訂單 {paymentStatus.order_number}
                </p>
                <p className="text-green-600 text-sm mt-1">
                  金額：NT$ {paymentStatus.total_amount.toLocaleString()}
                </p>
              </div>
              <button
                onClick={onPaymentSuccess}
                className="w-full bg-green-600 text-white py-3 px-4 rounded-lg hover:bg-green-700 transition-colors font-medium"
              >
                確認
              </button>
            </section>
          )}

          {/* 載入中狀態 */}
          {isLoading && (
            <section className="text-center py-8">
              <div
                className="animate-spin rounded-full h-10 w-10 border-b-2 border-[var(--color-brand-primary)] mx-auto mb-4"
                role="status"
                aria-label="載入中"
              ></div>
              <p className="text-gray-600">準備付款頁面中...</p>
            </section>
          )}

          {/* 錯誤狀態 */}
          {error && (
            <section className="text-center">
              <div
                className="text-red-500 text-5xl mb-4"
                role="img"
                aria-label="錯誤"
              >
                ❌
              </div>
              <h3 className="text-xl font-semibold text-gray-800 mb-3">
                無法準備付款頁面
              </h3>
              <p className="text-gray-600 mb-6">
                {error.message || "請稍後再試"}
              </p>
              <div className="space-y-3">
                <button
                  onClick={() => window.location.reload()}
                  className="w-full bg-red-600 text-white py-3 px-4 rounded-lg hover:bg-red-700 transition-colors font-medium"
                >
                  重試
                </button>
                <button
                  onClick={onClose}
                  className="w-full border border-gray-300 text-gray-700 py-3 px-4 rounded-lg hover:bg-gray-50 transition-colors font-medium"
                >
                  取消
                </button>
              </div>
            </section>
          )}

          {/* 準備付款狀態 */}
          {checkoutSession && paymentStatus?.payment_status === "unpaid" && (
            <section>
              <header className="text-center mb-6">
                <div
                  className="text-[var(--color-brand-primary)] text-5xl mb-4"
                  role="img"
                  aria-label="付款"
                >
                  💳
                </div>
                <h3 className="text-xl font-semibold text-gray-800 mb-2">
                  前往 Stripe 付款
                </h3>
              </header>

              {paymentStatus && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                  <p className="text-blue-700 font-medium">
                    訂單編號：{paymentStatus.order_number}
                  </p>
                  <p className="text-blue-600 text-sm mt-1">
                    金額：NT$ {paymentStatus.total_amount.toLocaleString()}
                  </p>
                </div>
              )}

              <div className="space-y-3">
                <button
                  onClick={handlePayment}
                  className="w-full bg-[var(--color-brand-primary)] text-[var(--color-brand-secondary)] py-4 px-4 rounded-lg hover:bg-[var(--color-brand-secondary-light)] transition-colors font-semibold text-lg"
                >
                  前往 Stripe 付款 →
                </button>
                <button
                  onClick={onClose}
                  className="w-full border border-gray-300 text-gray-700 py-3 px-4 rounded-lg hover:bg-gray-50 transition-colors font-medium"
                >
                  稍後付款
                </button>
              </div>
            </section>
          )}
        </main>
      </div>
    </dialog>
  );
};

export default PaymentModal;
