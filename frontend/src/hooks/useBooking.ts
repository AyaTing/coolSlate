// src/hooks/useBooking.ts
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  createOrder,
  type OrderRequest,
  type OrderResponse,
} from "../services/servicesAPI";

export const useBooking = () => {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (orderData: OrderRequest) => createOrder(orderData),
    onSuccess: (data: OrderResponse) => {
      console.log("✅ 預約成功:", data);

      queryClient.invalidateQueries({
        queryKey: ["calendar"],
      });
      queryClient.invalidateQueries({
        queryKey: ["unified-calendar"],
      });
      queryClient.invalidateQueries({
        queryKey: ["check-booking"],
      });
      queryClient.invalidateQueries({
        queryKey: ["check-units"],
      });
    },
    onError: (error: Error) => {
      console.error("❌ 預約失敗:", error);
    },
  });

  return {
    createBooking: mutation.mutate,
    isLoading: mutation.isPending,
    isSuccess: mutation.isSuccess,
    isError: mutation.isError,
    errorMessage: mutation.error?.message,
    data: mutation.data,
    reset: mutation.reset,
  };
};
