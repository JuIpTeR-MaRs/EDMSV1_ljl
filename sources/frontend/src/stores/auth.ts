import { defineStore } from "pinia";
import { ref, computed } from "vue";
import api from "@/api/client";

export const useAuthStore = defineStore("auth", () => {
  const token = ref<string | null>(sessionStorage.getItem("edms_token"));
  const user = ref<{
    id: number;
    login_name: string;
    display_name: string;
    employee_no: string;
    department_id?: number;
    is_manager?: boolean;
    is_super_admin?: boolean;
    role_id?: number;
    role_name?: string;
    role_name_en?: string;
    role_level?: number;
    role_code?: string;
  } | null>(null);

  const isAuthenticated = computed(() => !!token.value);

  function setToken(t: string | null) {
    token.value = t;
    if (t) sessionStorage.setItem("edms_token", t);
    else sessionStorage.removeItem("edms_token");
  }

  async function login(loginName: string, password?: string, captchaAnswer?: string, captchaToken?: string) {
    const { data } = await api.post("/auth/login", { 
      login_name: loginName, 
      password,
      captcha_answer: captchaAnswer,
      captcha_token: captchaToken
    });
    setToken(data.access_token);
    user.value = data.user;
    applyThemeByRole();
    return data;
  }

  async function fetchMe() {
    if (!token.value) return;
    const { data } = await api.get("/auth/me");
    user.value = data;
    applyThemeByRole();
  }

  function applyThemeByRole() {
    const htmlEl = document.documentElement;
    if (!user.value) {
      htmlEl.removeAttribute("data-theme");
      return;
    }

    if (user.value.is_super_admin || (user.value.role_level && user.value.role_level >= 100)) {
      htmlEl.setAttribute("data-theme", "admin");
    } else if (user.value.is_manager || (user.value.role_level && user.value.role_level >= 50)) {
      htmlEl.setAttribute("data-theme", "manager");
    } else {
      htmlEl.removeAttribute("data-theme");
    }
  }

  function logout() {
    setToken(null);
    user.value = null;
  }

  return { token, user, isAuthenticated, login, fetchMe, logout, setToken, applyThemeByRole };
});
