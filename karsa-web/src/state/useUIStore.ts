import { create } from 'zustand';

interface UIState {
  isSidebarCollapsed: boolean;
  toggleSidebar: () => void;
  isSearchOpen: boolean;
  setSearchOpen: (open: boolean) => void;
  toggleSearch: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  isSidebarCollapsed: false,
  toggleSidebar: () => set((state) => ({ isSidebarCollapsed: !state.isSidebarCollapsed })),
  isSearchOpen: false,
  setSearchOpen: (open) => set({ isSearchOpen: open }),
  toggleSearch: () => set((state) => ({ isSearchOpen: !state.isSearchOpen })),
}));
