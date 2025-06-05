import {
  createRouter,
  createRootRoute,
  createRoute,
  redirect,
} from "@tanstack/react-router";

import HomePage from "./pages/HomePage";
import ServicePage from "./pages/ServicePage";
import ProfilePage from "./pages/ProfilePage";
import AdminPage from "./pages/AdminPage";
import MainLayout from "./layouts/MainLayout";

const requireAuthBeforeLoad = async () => {
  const token = localStorage.getItem("auth_token");
  const savedUser = localStorage.getItem("auth_user");
  if (!token || !savedUser) {
    throw redirect({
      to: "/",
    });
  }
  try {
    const user = JSON.parse(savedUser);
    return { user, token };
  } catch (error) {
    console.error("使用者資料損壞，清除認證狀態:", error);
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");
    throw redirect({ to: "/" });
  }
};

const requireAdminBeforeLoad = async () => {
  const authData = await requireAuthBeforeLoad();
  if (authData.user?.role !== "admin") {
    throw redirect({
      to: "/profile",
      search: {
        error: "需要管理員權限",
      },
    });
  }
  return authData;
};

const rootRoute = createRootRoute({
  component: MainLayout,
});

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: HomePage,
});

const serviceRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/service",
  component: ServicePage,
});

const profileRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/profile",
  beforeLoad: requireAuthBeforeLoad,
  component: ProfilePage,
});

const adminRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/admin",
  beforeLoad: requireAdminBeforeLoad,
  component: AdminPage,
});

const paymentSuccessRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/payment/success",
  beforeLoad: () => {
    const urlParams = new URLSearchParams(window.location.search);
    const orderId = urlParams.get("order_id");
    alert(
      `付款成功！訂單編號：${orderId || ""}。感謝您的預約，我們會盡快與您聯繫。`
    );
    throw redirect({ to: "/profile" });
  },
  component: () => null, // 不會執行到這裡
});

// 付款取消重定向路由
const paymentCancelRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/payment/cancel",
  beforeLoad: () => {
    const urlParams = new URLSearchParams(window.location.search);
    const orderId = urlParams.get("order_id");
    alert(`付款已取消，訂單編號：${orderId || ""}。如需協助請聯繫客服。`);
    throw redirect({ to: "/profile" });
  },
  component: () => null,
});

const routeTree = rootRoute.addChildren([
  indexRoute,
  serviceRoute,
  paymentSuccessRoute,
  paymentCancelRoute,
  profileRoute,
  adminRoute,
]);

export const router = createRouter({
  routeTree,
  defaultPreload: "intent",
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

export { requireAuthBeforeLoad, requireAdminBeforeLoad };
