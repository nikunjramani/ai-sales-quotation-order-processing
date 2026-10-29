import { create } from "zustand";

// Client state only: which tool's Enable dialog is open, and the one-time values (a link
// code) from the Enable answer. The server never sends those again, so they live here until
// the page is reloaded; "Enable" again makes new ones. Never stored in the browser.
interface ConnectionSetup {
  enabling: string | null; // provider key of the open Enable dialog
  once: Record<string, Record<string, string>>; // connection ID -> one-time values
  open: (providerKey: string) => void;
  close: () => void;
  remember: (connectionId: string, values: Record<string, string>) => void;
}

export const useConnectionSetup = create<ConnectionSetup>()((set) => ({
  enabling: null,
  once: {},
  open: (providerKey) => set({ enabling: providerKey }),
  close: () => set({ enabling: null }),
  remember: (connectionId, values) =>
    set((state) => ({ once: { ...state.once, [connectionId]: values } })),
}));
