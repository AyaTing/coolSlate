// src/components/LoginModal.tsx
import { useEffect, useRef } from "react";
import { useGoogleLogin } from "../hooks/useAuth";

declare global {
  interface Window {
    google: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential: string }) => void;
          }) => void;
          renderButton: (
            element: HTMLElement,
            options: {
              theme?: string;
              size?: string;
              text?: string;
              locale?: string;
            }
          ) => void;
        };
      };
    };
  }
}

interface LoginModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

const LoginModal = ({ isOpen, onClose, onSuccess }: LoginModalProps) => {
  const buttonRef = useRef<HTMLDivElement>(null);
  const loginMutation = useGoogleLogin();

  useEffect(() => {
    if (isOpen && typeof window !== "undefined" && window.google) {
      window.google.accounts.id.initialize({
        client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID,
        callback: (response) => {
          loginMutation.mutate(response.credential, {
            onSuccess: () => {
              onClose();
              onSuccess?.();
            },
          });
        },
      });

      if (buttonRef.current) {
        window.google.accounts.id.renderButton(buttonRef.current, {
          theme: "outline",
          size: "large",
          text: "signin_with",
          locale: "zh-TW",
        });
      }
    }
  }, [isOpen, loginMutation, onClose, onSuccess]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-semibold text-gray-800">
            登入以繼續預約
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl"
            disabled={loginMutation.isPending}
          >
            ✕
          </button>
        </div>

        <div className="text-center">
          <p className="text-gray-600 mb-6">
            請登入您的 Google 帳號以完成預約流程
          </p>

          <div className="flex justify-center mb-4">
            <div ref={buttonRef}></div>
          </div>

          {loginMutation.isPending && (
            <div className="flex items-center justify-center gap-2 text-blue-600">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
              <span>登入中...</span>
            </div>
          )}

          {loginMutation.isError && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm">
              <p className="font-medium">登入失敗</p>
              <p>{loginMutation.error?.message}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default LoginModal;
