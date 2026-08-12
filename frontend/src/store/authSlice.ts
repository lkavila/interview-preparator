import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import type { User } from "../lib/types";

interface AuthState {
  token: string | null;
  user: User | null;
}

const stored = localStorage.getItem("auth");
const initialState: AuthState = stored ? JSON.parse(stored) : { token: null, user: null };

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    setCredentials(state, action: PayloadAction<{ token: string; user: User }>) {
      state.token = action.payload.token;
      state.user = action.payload.user;
      localStorage.setItem("auth", JSON.stringify(state));
    },
    setUser(state, action: PayloadAction<User>) {
      state.user = action.payload;
      localStorage.setItem("auth", JSON.stringify(state));
    },
    logout(state) {
      state.token = null;
      state.user = null;
      localStorage.removeItem("auth");
    },
  },
});

export const { setCredentials, setUser, logout } = authSlice.actions;
export default authSlice.reducer;
