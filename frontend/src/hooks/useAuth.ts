import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "@tanstack/react-router";
import {
  googleLogin,
  getCurrentUser,
  logout as logoutAPI,
  type LoginResponse,
} from "../services/authAPI";
import { useAuth as useAuthContext } from "../context/AuthContext";

export const useGoogleLogin = () => {
  const { login } = useAuthContext();
  const queryClient = useQueryClient();
  return useMutation<LoginResponse, Error, string>({
    mutationFn: (idToken: string) => googleLogin(idToken),
    onSuccess: (data: LoginResponse) => {
      login(data.token, data.user);
      queryClient.setQueryData(["auth", "user"], data.user);
    },
    onError: (error: Error) => {
      console.error("Google 登入失敗:", error.message);
    },
  });
};

export const useLogout = () => {
  const { logout } = useAuthContext();
  const queryClient = useQueryClient();
  const router = useRouter();
  return useMutation({
    mutationFn: logoutAPI,
    onSuccess: () => {
      queryClient.clear();
      logout();

      router.navigate({ to: "/" });
    },
    onError: (error: Error) => {
      console.error("Google 登出失敗，仍清除本地狀態:", error.message);
      queryClient.clear();
      logout();
      router.navigate({ to: "/" });
    },
  });
};

export const useCurrentUser = () => {
  const { isAuthenticated } = useAuthContext();

  return useQuery({
    queryKey: ["auth", "user"],
    queryFn: getCurrentUser,
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });
};

export const useHasRole = (role: string) => {
  const { user } = useAuthContext();
  return user?.role === role;
};

export const useIsAdmin = () => {
  return useHasRole("admin");
};
