import { useAuth } from "../context/AuthContext";
import { useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { useQueryClient } from "@tanstack/react-query";
import {
  getUserOrders,
  getOrderDetail,
  requestCancelOrder,
  type OrderDetail,
} from "../services/orderAPI";
import PaymentModal from "../components/PaymentModal";
import {
  toFrontendPaymentStatus,
  toFrontendOrderStatus,
} from "../services/orderAPI";

import { toFrontendServiceType } from "../services/servicesAPI";

type OptionsType = "會員概覽" | "進度查詢" | "訂單列表" | "設備清單";
type StatusTagType = "預約中" | "已排程" | "已結案（三個月內）" | "取消申請中";
interface OrderCardProps {
  order: OrderDetail;
  onClick: () => void;
}

const options: OptionsType[] = ["會員概覽", "進度查詢", "訂單列表"];
const statusTags: StatusTagType[] = [
  "預約中",
  "已排程",
  "已結案（三個月內）",
  "取消申請中",
];

const ProfilePage = () => {
  const [selectedOption, setSelectedOption] = useState<OptionsType>("會員概覽");
  const [orderId, setOrderId] = useState<number | null>(null);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [paymentOrderId, setPaymentOrderId] = useState<number | null>(null);
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const { data: orders } = useQuery({
    queryKey: ["orders"],
    queryFn: getUserOrders,
    staleTime: 5 * 60 * 1000,
  });

  const { data: orderDetail } = useQuery({
    queryKey: ["orderDetail", orderId],
    queryFn: () => getOrderDetail(orderId!),
    enabled: !!orderId,
  });

  const OrderCard = ({ order, onClick }: OrderCardProps) => {
    return (
      <button
        onClick={onClick}
        className="w-full flex flex-wrap flex-col p-1.5 bg-[var(--color-bg-card-secondary)] hover:bg-[var(--color-bg-card-tertiary)] mb-4 rounded-lg"
      >
        <p>
          {order.service_type === "INSTALLATION"
            ? "❄️ 新機安裝"
            : order.service_type === "MAINTENANCE"
            ? "🧼 冷氣保養"
            : "⚙️ 冷氣維修"}
          <span className="ml-1 font-bold text-red-500 opacity-70">
            {order.payment_status === "unpaid" ? "未付款" : ""}
          </span>
          <span className="ml-1 font-bold text-red-500 opacity-70">
            {order.status === "cancelled" && order.payment_status === "refunded"
              ? "已取消及退款"
              : ""}
          </span>
        </p>

        <p>
          {order.booking_slots?.length > 0
            ? String(order.booking_slots[0].preferred_date) +
              " " +
              String(order.booking_slots[0].preferred_time.slice(0, 5))
            : "無日期"}
        </p>
      </button>
    );
  };

  const OrderModal = () => {
    if (!orderId || !orderDetail) return null;
    const handlePayment = () => {
      setPaymentOrderId(orderDetail.order_id);
      setShowPaymentModal(true);
      setOrderId(null);
    };
    const canCancel = () => {
      if (orderDetail.payment_status !== "paid") return false;
      if (orderDetail.status === "precancel") return false;
      if (orderDetail.status === "cancelled") return false;
      if (orderDetail.status === "completed") return false;
      const bookingDate = new Date(
        orderDetail.booking_slots[0]?.preferred_date
      );
      const threeDaysFromNow = new Date();
      threeDaysFromNow.setDate(threeDaysFromNow.getDate() + 3);
      return bookingDate > threeDaysFromNow;
    };
    const cancelRequestModel = () => {
      setShowCancelConfirm(true);
    };

    return (
      <div className="fixed inset-0 bg-[var(--color-text-primary)]/10 flex items-center justify-center z-50 ">
        <div className="bg-[var(--color-bg-card-secondary)]  p-6 rounded-lg max-w-md w-full mx-4">
          <h3 className="text-lg font-bold mb-4">訂單詳情</h3>

          <div className="space-y-3 ">
            <p>訂單編號：{orderDetail.order_number}</p>
            <p>服務類型：{toFrontendServiceType(orderDetail.service_type)}</p>
            <p>服務狀態：{toFrontendOrderStatus(orderDetail.status)}</p>
            <p>
              付款狀態：{toFrontendPaymentStatus(orderDetail.payment_status)}
            </p>
            <p>預約日期：{orderDetail.booking_slots[0]?.preferred_date}</p>
            <p>
              預約時間：
              {orderDetail.booking_slots[0]?.preferred_time.slice(0, 5)}
            </p>
            <p>聯絡人：{orderDetail.booking_slots[0]?.contact_name}</p>
            <p>聯絡電話：{orderDetail.booking_slots[0]?.contact_phone}</p>
            <p>金額：NT$ {orderDetail.total_amount}</p>
          </div>
          {orderDetail.payment_status === "unpaid" && (
            <p className="mt-4 font-bold text-red-500 opacity-70">
              預約後若未付款，訂單將會於30分鐘後自動刪除，敬請留意。
            </p>
          )}
          {orderDetail.payment_status === "refunded" && (
            <p className="mt-4 font-bold text-red-500 opacity-70">
              已完成取消及退款作業。
            </p>
          )}
          {orderDetail.status === "precancel" && (
            <p className="mt-4 font-bold text-red-500 opacity-70">
              專人核對處理中。
            </p>
          )}
          {canCancel() && (
            <p className="mt-4 font-bold text-red-500 opacity-70">
              僅接受預定日期三日前提出申請取消。
            </p>
          )}
          <div className="flex gap-2 mt-4 justify-between">
            {orderDetail.payment_status === "unpaid" && (
              <button
                onClick={handlePayment}
                className="px-4 py-2 bg-[var(--color-brand-primary)] text-[var(--color-text-secondary)] rounded"
              >
                立即付款
              </button>
            )}
            {canCancel() && (
              <button
                onClick={cancelRequestModel}
                className="px-4 py-2 bg-[var(--color-text-tertiary)]/10 text-[var(--color-text-primary)] rounded"
              >
                申請取消
              </button>
            )}
            <span></span>
            <button
              onClick={() => setOrderId(null)}
              className="px-4 py-2 bg-[var(--color-text-tertiary)] text-[var(--color-text-secondary)] rounded"
            >
              關閉
            </button>
          </div>
        </div>
      </div>
    );
  };
  const CancelConfirmModal = () => {
    if (!showCancelConfirm) return null;
    const handleConfirmCancel = async () => {
      try {
        await requestCancelOrder(orderDetail!.order_id);
        setShowCancelConfirm(false);
        setOrderId(null);
        queryClient.invalidateQueries({
          predicate: (query) =>
            query.queryKey[0] === "orders" ||
            query.queryKey[0] === "orderDetail",
        });
      } catch (error) {
        console.error(error);
        alert("申請失敗，請重試");
      }
    };

    return (
      <div className="fixed inset-0 bg-[var(--color-text-primary)]/10 flex items-center justify-center z-50 ">
        <div className="bg-[var(--color-bg-card-secondary)]  p-6 rounded-lg max-w-md w-full mx-4">
          <h3 className="text-lg font-bold mb-4">確認取消申請</h3>
          <p className="mb-6 text-[var(--color-text-primary)]">
            確定要申請取消此訂單嗎？此操作無法復原。
          </p>
          <div className="flex gap-3 justify-end">
            <button
              onClick={() => setShowCancelConfirm(false)}
              className="px-4 py-2 bg-[var(--color-brand-primary)] text-[var(--color-text-secondary)] rounded"
            >
              取消
            </button>
            <button
              onClick={handleConfirmCancel}
              className="px-4 py-2 bg-red-500 opacity-70 text-[var(--color-text-secondary)] rounded"
            >
              確認申請
            </button>
          </div>
        </div>
      </div>
    );
  };

  const filterOrdersByStatus = (status: StatusTagType) => {
    const filtered =
      orders?.filter((order) => {
        switch (status) {
          case "預約中":
            return (
              order.status === "pending" || order.status === "pending_schedule"
            );

          case "已排程":
            return order.status === "scheduled";

          case "已結案（三個月內）":
            const bookingDate = new Date(
              order.booking_slots[0]?.preferred_date
            );
            const threeMonthsAgo = new Date();
            threeMonthsAgo.setMonth(threeMonthsAgo.getMonth() - 3);
            return (
              (order.status === "completed" || order.status === "cancelled") &&
              bookingDate >= threeMonthsAgo
            );

          case "取消申請中":
            return order.status === "precancel";

          default:
            return false;
        }
      }) || [];
    return filtered.sort((a, b) => {
      const dateA = a.booking_slots[0]?.preferred_date || "";
      const dateB = b.booking_slots[0]?.preferred_date || "";
      return dateA.localeCompare(dateB);
    });
  };

  const profileContent = (): ReactNode => {
    switch (selectedOption) {
      case "會員概覽":
        const unpaidOrders =
          orders?.filter((o) => o.payment_status === "unpaid").length || 0;
        const scheduledOrders =
          orders?.filter((o) => o.status === "scheduled").length || 0;
        return (
          <div className="grid lg:grid-cols-2 gap-8">
            <div className="space-y-4 p-10 rounded-lg shadow-md bg-gradient-to-br from-[var(--color-brand-primary-light)]/10  via-[var(--color-bg-card-tertiary)] to-[var(--color-bg-card-tertiary)]  hover:shadow-lg transition-shadow border border-gray-200/50 hover:border-[var(--color-brand-primary)]/50  text-[var(--color-text-primary)]">
              <h2 className="text-xl font-semibold">會員資訊</h2>
              <div className="space-y-2">
                <p>
                  <strong>姓名：</strong>
                  {user?.name}
                </p>
                <p>
                  <strong>電子郵件：</strong>
                  {user?.email}
                </p>
                <p>
                  <strong>會員等級：</strong>
                  {user?.role === "customer" ? "一般會員" : user?.role}
                </p>
              </div>
            </div>
            <div className="space-y-4 p-10  rounded-lg shadow-md hover:shadow-lg transition-shadow border border-gray-200/50 hover:border-[var(--color-brand-primary)]/50  text-[var(--color-text-primary)] ">
              <h2 className="text-xl font-semibold">服務概覽</h2>
              <div className="grid grid-cols-2 gap-4 ">
                <div className="bg-[var(--color-bg-card-secondary)] hover:bg-[var(--color-bg-card-tertiary)] p-4 rounded-lg text-center space-y-4">
                  <p className="text-2xl font-bold ">{scheduledOrders}</p>
                  <p className="text-sm ">已排程，等待施作</p>
                </div>
                <div className="bg-[var(--color-bg-card-secondary)] hover:bg-[var(--color-bg-card-tertiary)] p-4 rounded-lg text-center space-y-4">
                  <p className="text-2xl font-bold ">{unpaidOrders}</p>
                  <p className="text-sm">待付款</p>
                </div>
              </div>
            </div>
          </div>
        );
      case "進度查詢":
        return (
          <div className="grid lg:grid-cols-4 gap-4">
            {statusTags.map((statusTag) => {
              const filteredOrders = filterOrdersByStatus(statusTag);

              return (
                <div
                  key={statusTag}
                  className="p-5 rounded-lg shadow-md hover:shadow-lg transition-shadow border border-gray-200/50 hover:border-[var(--color-brand-primary)]/50  text-[var(--color-text-primary)]  flex flex-col max-h-[700px] overflow-y-auto "
                >
                  <h3 className="p-4 flex justify-center border-b-2 mb-4">
                    {statusTag}
                  </h3>
                  {filteredOrders.map((order) => (
                    <OrderCard
                      key={order.order_id}
                      order={order}
                      onClick={() => setOrderId(order.order_id)}
                    />
                  ))}
                </div>
              );
            })}
          </div>
        );
      case "訂單列表":
        const sortedOrders =
          orders?.slice().sort((a, b) => {
            const dateA = a.booking_slots[0]?.preferred_date || "";
            const dateB = b.booking_slots[0]?.preferred_date || "";
            return dateB.localeCompare(dateA);
          }) || [];
        return (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold mb-4">所有訂單</h2>
            <div className="space-y-3 max-h-[600px] overflow-y-auto">
              {sortedOrders?.map((order) => (
                <div
                  key={order.order_id}
                  className="p-4 rounded-lg shadow-md  border-gray-200/50 hover:border-[var(--color-brand-primary)]/50 border hover:shadow-md hover:bg-[var(--color-bg-card-tertiary)]  transition-shadow cursor-pointer"
                  onClick={() => setOrderId(order.order_id)}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="font-medium">
                        {toFrontendServiceType(order.service_type)}
                      </h3>
                      <p className="text-sm text-gray-600">
                        {order.booking_slots[0]?.preferred_date}{" "}
                        {order.booking_slots[0]?.preferred_time.slice(0, 5)}
                      </p>
                      <p className="text-sm text-gray-600">
                        訂單編號：{order.order_number}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-medium">
                        NT$ {order.total_amount?.toLocaleString()}
                      </p>
                      <span className="text-xs bg-gray-100 px-2 py-1 rounded">
                        {toFrontendOrderStatus(order.status)}
                      </span>
                      <span className="text-xs bg-blue-100 px-2 py-1 rounded ml-1">
                        {toFrontendPaymentStatus(order.payment_status)}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      default:
        return <div>建置中</div>;
    }
  };

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl md:text-4xl font-bold text-[var(--color-text-primary)] mb-4">
            會員服務中心
          </h1>
        </div>
        <div className="mb-8">
          <div className="flex flex-wrap gap-4 justify-center">
            {options.map((option) => {
              return (
                <button
                  key={option}
                  onClick={() => {
                    setSelectedOption(option);
                  }}
                  className={`px-6 py-3 rounded-lg font-medium transition-all disabled:opacity-50 ${
                    selectedOption === option
                      ? "bg-[var(--color-brand-primary)] text-[var(--color-text-secondary)] shadow-lg"
                      : "bg-[var(--color-bg-card)] text-[var(--color-text-primary)] hover:bg-[var(--color-brand-primary-light)] hover:shadow-md"
                  }`}
                >
                  {option}
                </button>
              );
            })}
          </div>
        </div>
        <div className="bg-gradient-to-br from-[var(--color-brand-primary-light)]/10 via-transparent to-[var(--color-bg-main)]  rounded-lg shadow-md p-6">
          {profileContent()}
          <OrderModal />
          <CancelConfirmModal />
        </div>
      </div>
      {paymentOrderId && (
        <PaymentModal
          orderId={paymentOrderId}
          isOpen={showPaymentModal}
          onPaymentSuccess={() => {
            setShowPaymentModal(false);
            setPaymentOrderId(null);
          }}
          onClose={() => {
            setShowPaymentModal(false);
            setPaymentOrderId(null);
          }}
        />
      )}
    </div>
  );
};

export default ProfilePage;
