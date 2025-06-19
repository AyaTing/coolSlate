import { Link, Outlet } from "@tanstack/react-router";
import logoImage_1 from "../assets/images/logo_1.png";
import { useAuth } from "../context/AuthContext";
import { useLogout } from "../hooks/useAuth";
import LoginModal from "../components/LoginModal";
import { useState } from "react";

const MainLayout = () => {
  const { isAuthenticated, user } = useAuth();
  const logoutMutation = useLogout();
  const [showLoginModal, setShowLoginModal] = useState(false);
  const handleLogout = () => {
    logoutMutation.mutate();
  };
  const [showMobileMenu, setShowMobileMenu] = useState(false);
  const isAdmin = user?.role === "admin";
  const closeMobileMenu = () => setShowMobileMenu(false);

  return (
    <div className="flex flex-col min-h-screen bg-[var(--color-bg-main)] text-[var(--color-text-primary)]">
      <header className="m-4 border-none rounded-b bg-[var(--color-bg-main)]/90 backdrop-blur-md sticky top-0 z-50">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 h-16 md:h-20 flex items-center justify-between">
          <Link
            to="/"
            className="container w-40"
            aria-label="回到首頁 - Cool Slate"
          >
            <img
              src={logoImage_1}
              className="block object-cover w-full"
              alt="Cool Slate logo"
            />
          </Link>
          {
            <nav className="hidden md:flex items-center space-x-5 lg:space-x-7 text-m font-medium">
              {/* <Link
                to="/"
                className="p-1.5 text-[var(--color-text-primary)] hover:bg-[var(--color-brand-secondary)] transition-colors"
                activeProps={{
                  className: "text-[var(--color-brand-primary)] font-semibold",
                }}
              >
                選購空調試算
              </Link> */}
              <Link
                preload="render"
                to="/service"
                className="p-1.5 text-[var(--color-text-primary)] hover:bg-[var(--color-brand-secondary)] transition-colors"
                activeProps={{
                  className: "text-[var(--color-brand-primary)] font-semibold",
                }}
              >
                服務預約
              </Link>
              {isAuthenticated ? (
                <>
                  {isAdmin ? (
                    <Link
                      to="/admin"
                      className="p-1.5 text-[var(--color-text-primary)] hover:bg-[var(--color-brand-secondary)] transition-colors"
                      activeProps={{
                        className:
                          "text-[var(--color-brand-primary)] font-semibold",
                      }}
                    >
                      管理後台
                    </Link>
                  ) : null}

                  <Link
                    to="/profile"
                    className="p-1.5 text-[var(--color-text-primary)] hover:bg-[var(--color-brand-secondary)] transition-colors"
                    activeProps={{
                      className:
                        "text-[var(--color-brand-primary)] font-semibold",
                    }}
                  >
                    會員中心
                  </Link>
                </>
              ) : (
                <button
                  onClick={() => setShowLoginModal(true)}
                  className="p-1.5 text-[var(--color-text-primary)] hover:bg-[var(--color-brand-secondary)] transition-colors"
                >
                  會員中心
                </button>
              )}

              {/* <Link
                to="/contact"
                className="p-1.5 text-[var(--color-text-primary)] hover:bg-[var(--color-brand-secondary)] transition-colors"
                activeProps={{
                  className: "text-[var(--color-brand-primary)] font-semibold",
                }}
              >
                聯絡我們
              </Link> */}
              {isAuthenticated ? (
                <button
                  onClick={handleLogout}
                  className="bg-[var(--color-brand-primary)] hover:scale-105 hover:outline-offset-2 text-[var(--color-text-secondary)] py-2 px-5 rounded-md transition-colors text-base font-semibold"
                >
                  登出
                </button>
              ) : (
                <button
                  onClick={() => setShowLoginModal(true)}
                  className="bg-[var(--color-brand-primary)] hover:scale-105 hover:outline-offset-2 text-[var(--color-text-secondary)] py-2 px-5 rounded-md transition-colors text-base font-semibold"
                >
                  登入 / 註冊
                </button>
              )}
            </nav>
          }

          {
            <div className="md:hidden">
              <button
                type="button"
                onClick={() => setShowMobileMenu(true)}
                className="p-2 rounded-md text-[var(--color-text-primary)] hover:text-[var(--color-text-tertiary)] focus:outline-none focus:ring-2 focus:ring-inset focus:ring-[var(--color-brand-secondary)]"
                aria-label="開啟主選單"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={1.5}
                  stroke="currentColor"
                  className="w-7 h-7"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 4.5v15m7.5-7.5h-15"
                  />
                </svg>
              </button>
            </div>
          }
        </div>
      </header>
      {showMobileMenu && (
        <div className="fixed inset-0 bg-[var(--color-text-primary)]/10 flex items-center justify-center z-50">
          <div className="bg-[var(--color-bg-card-secondary)] p-6 rounded-lg max-w-md w-full mx-4">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
                選單
              </h2>
              <button
                onClick={closeMobileMenu}
                className="p-1 rounded-md text-[var(--color-text-primary)] hover:text-[var(--color-text-tertiary)]"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={2}
                  stroke="currentColor"
                  className="w-6 h-6"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            <nav className="flex flex-col space-y-4">
              <Link
                preload="render"
                to="/"
                onClick={closeMobileMenu}
                className="w-full p-3 text-center text-[var(--color-text-primary)] hover:bg-[var(--color-brand-secondary)] transition-colors rounded-md"
                activeProps={{
                  className:
                    "text-[var(--color-brand-primary)] font-semibold bg-[var(--color-brand-secondary)]",
                }}
              >
                首頁
              </Link>
              <Link
                preload="render"
                to="/service"
                onClick={closeMobileMenu}
                className="w-full p-3 text-center text-[var(--color-text-primary)] hover:bg-[var(--color-brand-secondary)] transition-colors rounded-md"
                activeProps={{
                  className:
                    "text-[var(--color-brand-primary)] font-semibold bg-[var(--color-brand-secondary)]",
                }}
              >
                服務預約
              </Link>

              {isAuthenticated ? (
                <>
                  {isAdmin && (
                    <Link
                      to="/admin"
                      onClick={closeMobileMenu}
                      className="w-full p-3 text-center text-[var(--color-text-primary)] hover:bg-[var(--color-brand-secondary)] transition-colors rounded-md"
                      activeProps={{
                        className:
                          "text-[var(--color-brand-primary)] font-semibold bg-[var(--color-brand-secondary)]",
                      }}
                    >
                      管理後台
                    </Link>
                  )}

                  <Link
                    to="/profile"
                    onClick={closeMobileMenu}
                    className="w-full p-3 text-center text-[var(--color-text-primary)] hover:bg-[var(--color-brand-secondary)] transition-colors rounded-md"
                    activeProps={{
                      className:
                        "text-[var(--color-brand-primary)] font-semibold bg-[var(--color-brand-secondary)]",
                    }}
                  >
                    會員中心
                  </Link>

                  <button
                    onClick={() => {
                      handleLogout();
                      closeMobileMenu();
                    }}
                    className="w-full bg-[var(--color-brand-primary)] hover:scale-105 text-[var(--color-text-secondary)] py-3 px-5 rounded-md transition-colors font-semibold"
                  >
                    登出
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={() => {
                      setShowLoginModal(true);
                      closeMobileMenu();
                    }}
                    className="w-full p-3 text-center text-[var(--color-text-primary)] hover:bg-[var(--color-brand-secondary)] transition-colors rounded-md"
                  >
                    會員中心
                  </button>

                  <button
                    onClick={() => {
                      setShowLoginModal(true);
                      closeMobileMenu();
                    }}
                    className="w-full bg-[var(--color-brand-primary)] hover:scale-105 text-[var(--color-text-secondary)] py-3 px-5 rounded-md transition-colors font-semibold"
                  >
                    登入 / 註冊
                  </button>
                </>
              )}
            </nav>
          </div>
        </div>
      )}
      <main className="flex-grow w-full">
        <Outlet />
      </main>
      <footer className="py-8 bg-[var(--color-bg-main)]">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 text-center text-[var(--color-text-tertiary)] text-xs">
          <p>© 2025 Cool Slate 版權所有.</p>
          <p className="mt-1">一站式冷氣預約平台</p>
        </div>
      </footer>
      <LoginModal
        isOpen={showLoginModal}
        onClose={() => setShowLoginModal(false)}
        onSuccess={() => setShowLoginModal(false)}
      />
    </div>
  );
};

export default MainLayout;
