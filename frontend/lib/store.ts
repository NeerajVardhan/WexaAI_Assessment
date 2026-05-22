import { create } from "zustand";
import { persist } from "zustand/middleware";

type AppState = {
  accessToken?: string;
  organizationId: string;
  setAccessToken: (token?: string) => void;
  setOrganizationId: (organizationId: string) => void;
  clear: () => void;
};

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      accessToken: undefined,
      organizationId: "",
      setAccessToken: (accessToken) => set({ accessToken }),
      setOrganizationId: (organizationId) => set({ organizationId }),
      clear: () => set({ accessToken: undefined, organizationId: "" })
    }),
    { name: "wexa-auth" }
  )
);
