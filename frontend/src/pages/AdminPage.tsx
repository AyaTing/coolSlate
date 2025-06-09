import { useState, useEffect, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  getAllOrders,
  getAllUsers,
  getOrderByAdmin,
  getUserOrdersByAdmin,
} from "../services/adminAPI";
import { type OrderDetail } from "../services/orderAPI";
import {
  toFrontendPaymentStatus,
  toFrontendOrderStatus,
} from "../services/orderAPI";
import { toFrontendServiceType } from "../services/servicesAPI";

type AdminOptionsType =
  | "待辦總覽"
  | "行事曆"
  | "未完工追蹤"
  | "會員名冊"
  | "訂單總表"
  | "設備清單";

type CaseTagType = "等待排程" | "七日內" | "二週內" | "二週以上" | "取消申請中";

interface OrderCardProps {
  order: OrderDetail;
  onClick: () => void;
}

const adminOptions: AdminOptionsType[] = ["未完工追蹤", "會員名冊", "訂單總表"];
const caseTags: CaseTagType[] = [
  "等待排程",
  "七日內",
  "二週內",
  "二週以上",
  "取消申請中",
];

const AdminPage = () => {
  const [selectedOption, setSelectedOption] =
    useState<AdminOptionsType>("未完工追蹤");
  const [orderId, setOrderId] = useState<number | null>(null);
  const [userId, setUserId] = useState<number | null>(null);
  const [usersPage, setUsersPage] = useState<number>(1);
  const [ordersPage, setOrdersPage] = useState<number>(1);
  const [searchUser, setSearchUser] = useState<string>("");
  const [orderStatus, setOrderStatus] = useState<string>("");
  const [paymentStatus, setPaymentStatus] = useState<string>("");
  const [serviceType, setServiceType] = useState<string>("");

  useEffect(() => {
    if (selectedOption === "訂單總表") {
      setOrdersPage(1);
    }
  }, [selectedOption, orderStatus, paymentStatus, serviceType]);

  const { data: orders } = useQuery({
    queryKey: [
      "admin-orders",
      {
        status: orderStatus,
        payment_status: paymentStatus,
        page: ordersPage,
      },
    ],
    queryFn: () =>
      getAllOrders({
        status: orderStatus || undefined,
        payment_status: paymentStatus || undefined,
        page: ordersPage,
        limit: selectedOption === "未完工追蹤" ? 9999 : 20,
      }),
  });

  const { data: users } = useQuery({
    queryKey: ["admin-users", { page: usersPage, search: searchUser }],
    queryFn: () =>
      getAllUsers({
        page: usersPage,
        limit: 10,
        search: searchUser || undefined,
      }),
  });
  const { data: orderDetail } = useQuery({
    queryKey: ["admin-order-detail", orderId],
    queryFn: () => getOrderByAdmin(orderId!),
    enabled: !!orderId,
  });
  const { data: userOrders } = useQuery({
    queryKey: ["admin-user-orders", userId],
    queryFn: () => getUserOrdersByAdmin(userId!),
    enabled: !!userId,
  });

  const OrderCard = ({ order, onClick }: OrderCardProps) => {
    const today = new Date();
    const bookingDateStr = order.booking_slots[0]?.preferred_date;
    const bookingDate = new Date(bookingDateStr);

    return (
      <button
        onClick={onClick}
        className="w-full flex flex-wrap flex-col p-1.5 bg-[var(--color-bg-card-secondary)] hover:bg-[var(--color-brand-secondary-light)] mb-4 rounded-lg"
      >
        <p>
          {order.service_type === "INSTALLATION"
            ? "❄️ 新機安裝"
            : order.service_type === "MAINTENANCE"
            ? "🧼 冷氣保養"
            : "⚙️ 冷氣維修"}{" "}
          <span className="ml-1 font-bold text-red-500 opacity-70">
            {bookingDate < today ? "已過期" : ""}
          </span>
        </p>

        <p>
          {order.booking_slots?.length > 0 && order.booking_slots[0]
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
          {orderDetail.status === "precancel" && (
            <p className="mt-4 font-bold text-red-500 opacity-70">
              需先進行退款處理。
            </p>
          )}
          <div className="flex gap-2 mt-4 justify-end">
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

  const filterOrdersByCaseTag = (caseTag: CaseTagType) => {
    if (!orders?.orders) return [];
    const today = new Date();
    const sevenDaysFromNow = new Date(today);
    sevenDaysFromNow.setDate(today.getDate() + 7);
    const twoWeeksFromNow = new Date(today);
    twoWeeksFromNow.setDate(today.getDate() + 14);
    const filtered =
      orders.orders.filter((order) => {
        const bookingDateStr = order.booking_slots[0]?.preferred_date;
        if (!bookingDateStr) return false;
        const bookingDate = new Date(bookingDateStr);
        switch (caseTag) {
          case "等待排程":
            return (
              (order.status === "pending_schedule" ||
                order.status === "paid") &&
              order.payment_status === "paid"
            );
          case "七日內":
            return (
              order.status === "scheduled" && bookingDate <= sevenDaysFromNow
            );
          case "二週內":
            return (
              order.status === "scheduled" &&
              bookingDate > sevenDaysFromNow &&
              bookingDate <= twoWeeksFromNow
            );
          case "二週以上":
            return (
              order.status === "scheduled" && bookingDate > twoWeeksFromNow
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

  const userOrdersList = () => {
    if (!userId) {
      return (
        <div className="flex items-center justify-center h-full text-[var(--color-text-tertiary)]">
          <p>請選擇一個會員查看其訂單</p>
        </div>
      );
    }
    if (!userOrders?.orders || userOrders.orders.length === 0) {
      return (
        <div className="flex items-center justify-center h-full text-[var(--color-text-tertiary)]">
          <p>此會員沒有訂單</p>
        </div>
      );
    }
    const sortedOrders =
      userOrders.orders?.slice().sort((a, b) => {
        const dateA = a.booking_slots[0]?.preferred_date || "";
        const dateB = b.booking_slots[0]?.preferred_date || "";
        return dateB.localeCompare(dateA);
      }) || [];
    return (
      <div className="space-y-4">
        <div className="flex justify-between border-b-2">
          <h2 className="text-lg font-semibold mb-4 not-first-of-type:">
            會員 {userOrders.user.name}
          </h2>
          <h3 className="text-lg font-semibold mb-4">
            共 {userOrders.orders.length} 筆訂單
          </h3>
        </div>
        <div className="space-y-3 max-h-[600px] overflow-y-auto">
          {sortedOrders?.map((order) => (
            <div
              key={order.order_id}
              className="p-4 rounded-lg shadow-md  border-gray-200/50 hover:border-[var(--color-brand-primary)]/50 border hover:shadow-md hover:bg-[var(--color-brand-secondary-light)]  transition-shadow cursor-pointer"
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
  };

  const adminContent = (): ReactNode => {
    switch (selectedOption) {
      case "未完工追蹤":
        return (
          <div className="grid lg:grid-cols-5 gap-4">
            {caseTags.map((caseTag) => {
              const filteredOrders = filterOrdersByCaseTag(caseTag);
              return (
                <div
                  key={caseTag}
                  className="p-5 rounded-lg shadow-md hover:shadow-lg transition-shadow border border-gray-200/50 hover:border-[var(--color-brand-primary)]/50  text-[var(--color-text-primary)]  flex flex-col max-h-[700px] overflow-y-auto "
                >
                  <h3 className="p-4 flex justify-center border-b-2 mb-4">
                    {caseTag}
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
      case "會員名冊":
        return (
          <div className="grid lg:grid-cols-2 gap-12">
            <div className="p-5 rounded-lg shadow-md hover:shadow-lg transition-shadow border border-gray-200/50 hover:border-[var(--color-brand-primary)]/50  text-[var(--color-text-primary)]  flex flex-col max-h-[700px] overflow-y-auto">
              <input
                type="text"
                placeholder="搜尋使用者..."
                className="px-3 py-2 border border-[var(--color-brand-primary)]/50 rounded-lg mb-4"
                value={searchUser}
                onChange={(e) => setSearchUser(e.target.value)}
              />{" "}
              <div className="grid gap-4">
                {users?.users?.map((user) => (
                  <button
                    onClick={() => setUserId(user.id)}
                    key={user.id}
                    className="rounded-lg p-4 bg-[var(--color-bg-card-secondary)] hover:bg-[var(--color-brand-secondary-light)]"
                  >
                    <div className="text-left pl-4">
                      <h3 className="font-bold">
                        {user.name}{" "}
                        <span className="text-sm font-medium text-[var(--color-text-tertiary)]">
                          {user.role === "admin" ? "管理員" : "一般會員"}
                        </span>
                      </h3>
                      <p>{user.email}</p>
                    </div>
                  </button>
                ))}
              </div>
            </div>
            <div className="p-5 rounded-lg shadow-md hover:shadow-lg transition-shadow border border-gray-200/50 hover:border-[var(--color-brand-primary)]/50  text-[var(--color-text-primary)]  flex flex-col max-h-[700px] overflow-y-auto">
              {userOrdersList()}
            </div>
          </div>
        );
      case "訂單總表":
        const allOrders = orders?.orders || [];
        const filteredByServiceType = serviceType
          ? allOrders.filter((order) => order.service_type === serviceType)
          : allOrders;
        const sortedOrders =
          filteredByServiceType.slice().sort((a, b) => {
            const dateA = a.booking_slots[0]?.preferred_date || "";
            const dateB = b.booking_slots[0]?.preferred_date || "";
            return dateB.localeCompare(dateA);
          }) || [];
        return (
          <div className="space-y-4">
            <div className="space-x-4">
              <select
                value={orderStatus}
                onChange={(e) => setOrderStatus(e.target.value)}
                className="px-3 py-2 border border-[var(--color-brand-primary)]/50 rounded-lg mb-4"
              >
                <option value="">所有狀態</option>
                <option value="pending_schedule">待排程</option>
                <option value="scheduled">已排程</option>
                <option value="completed">已完成</option>
                <option value="cancelled">已取消</option>
                <option value="precancel">取消申請中</option>
              </select>

              <select
                value={paymentStatus}
                onChange={(e) => setPaymentStatus(e.target.value)}
                className="px-3 py-2 border border-[var(--color-brand-primary)]/50 rounded-lg mb-4"
              >
                <option value="">所有付款狀態</option>
                <option value="pending">待付款</option>
                <option value="paid">已付款</option>
                <option value="refunded">已退款</option>
              </select>

              <select
                value={serviceType}
                onChange={(e) => setServiceType(e.target.value)}
                className="px-3 py-2 border border-[var(--color-brand-primary)]/50 rounded-lg mb-4"
              >
                <option value="">所有服務類型</option>
                <option value="INSTALLATION">新機安裝</option>
                <option value="MAINTENANCE">冷氣保養</option>
                <option value="REPAIR">冷氣維修</option>
              </select>
            </div>
            <div className="space-y-3 max-h-[600px] overflow-y-auto">
              {sortedOrders?.map((order) => (
                <div
                  key={order.order_id}
                  className="p-4 rounded-lg shadow-md  border-gray-200/50 hover:border-[var(--color-brand-primary)]/50 border hover:shadow-md hover:bg-[var(--color-brand-secondary-light)]  transition-shadow cursor-pointer"
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
            管理後台
          </h1>
        </div>
        <div className="mb-8">
          <div className="flex flex-wrap gap-4 justify-center">
            {adminOptions.map((option) => {
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
          {adminContent()}
          <OrderModal />
        </div>
      </div>
    </div>
  );
};

export default AdminPage;
