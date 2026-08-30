<template>
  <div class="personal">
    <div class="hero-header">
      <div class="header-left">
        <div class="header-icon-ring">
          <el-icon><User /></el-icon>
        </div>
        <div>
          <h1 class="page-title">{{ t("personal.title") }}</h1>
          <p class="page-sub">{{ t("dashboard.subtitle", "View and update your personal information and statistics.") }}</p>
        </div>
      </div>
    </div>
      <div class="profile">
        <div class="avatar">
          <el-avatar :size="100" :src="avatarUrl">{{ userInitials }}</el-avatar>
        </div>
        <div class="info">
          <h2>{{ userDisplayName }}</h2>
          <div class="detail">
            <span class="detail-label">{{ t("personal.department") }}:</span>
            <span class="detail-value font-medium">{{ formatDeptName(user?.department_name || '', user?.department_name_en) }}</span>
          </div>
          <div class="detail">
            <span class="detail-label">{{ t("personal.role") }}:</span>
            <el-tag size="small" :type="user?.role_level && user?.role_level >= 80 ? 'warning' : 'primary'" effect="light">
              {{ formatRoleName(user) }}
            </el-tag>
          </div>
          <div class="detail supervisor-detail">
            <span class="detail-label">👤 {{ t("personal.supervisor") }}:</span>
            <div v-if="user?.direct_supervisor" class="supervisor-badge-box">
              <span class="sup-avatar">{{ (user.direct_supervisor.display_name || 'S').slice(0, 1).toUpperCase() }}</span>
              <span class="sup-name">{{ formatSupervisorName(user.direct_supervisor) }}</span>
              <el-tag size="small" type="warning" effect="plain" class="sup-role-tag">
                {{ formatSupervisorRole(user.direct_supervisor) }}
              </el-tag>
              <span v-if="user.direct_supervisor.employee_no" class="sup-no">({{ user.direct_supervisor.employee_no }})</span>
            </div>
            <span v-else class="detail-value text-muted">{{ t("personal.noSupervisor") }}</span>
          </div>
          <div class="detail" v-if="user?.position_full_name || user?.position_short">
            <span class="detail-label">{{ t("personal.position") }}:</span>
            <span class="detail-value">{{ formatPosition(user) }}</span>
          </div>
          <div class="detail">
            <span class="detail-label">{{ t("personal.login") }}:</span>
            <span class="detail-value">{{ user?.login_name }}</span>
          </div>
          <div class="detail">
            <span class="detail-label">{{ t("personal.employeeNo") }}:</span>
            <code class="emp-code">{{ user?.employee_no }}</code>
          </div>
          <div class="detail" v-if="user?.gender">
            <span class="detail-label">{{ t("personal.gender") }}:</span>
            <span class="detail-value">{{ user.gender === 'Male' ? t("personal.male") : t("personal.female") }}</span>
          </div>
          <div class="detail" v-if="user?.birth_date">
            <span class="detail-label">{{ t("personal.birthDate") }}:</span>
            <span class="detail-value">{{ user.birth_date }} ({{ t("personal.age") }}: {{ user.age }})</span>
          </div>
          <div style="margin-top: 16px;">
            <el-button type="primary" :icon="Edit" @click="editVisible = true">{{ t('common.edit') }}</el-button>
            <el-button type="warning" :icon="Lock" @click="passVisible = true">{{ t('profile.changePass') }}</el-button>
          </div>
        </div>
      </div>

      <!-- Edit Dialog -->
      <el-dialog :title="t('profile.title')" v-model="editVisible" width="500px">
        <el-form :model="editForm" label-width="100px" v-loading="editLoading">
          <el-form-item :label="t('profile.firstName')">
            <el-input v-model="editForm.first_name" />
          </el-form-item>
          <el-form-item :label="t('profile.lastName')">
            <el-input v-model="editForm.last_name" />
          </el-form-item>
          <el-form-item :label="t('profile.gender')">
            <el-select v-model="editForm.gender" style="width: 100%">
              <el-option label="Male" value="Male" />
              <el-option label="Female" value="Female" />
              <el-option label="Other" value="Other" />
            </el-select>
          </el-form-item>
          <el-form-item :label="t('profile.birthDate')">
            <el-date-picker v-model="editForm.birth_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="editVisible = false">{{ t('common.cancel') }}</el-button>
          <el-button type="primary" @click="saveProfile">{{ t('common.save') }}</el-button>
        </template>
      </el-dialog>

      <!-- Password Dialog -->
      <el-dialog :title="t('profile.changePass')" v-model="passVisible" width="450px">
        <el-form :model="passForm" label-width="120px" v-loading="passLoading">
          <el-form-item :label="t('profile.oldPass')">
            <el-input v-model="passForm.old_password" type="password" show-password />
          </el-form-item>
          <el-form-item :label="t('profile.newPass')">
            <el-input v-model="passForm.new_password" type="password" show-password />
          </el-form-item>
          <el-form-item :label="t('profile.confirmPass')">
            <el-input v-model="passForm.confirm_password" type="password" show-password />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="passVisible = false">{{ t('common.cancel') }}</el-button>
          <el-button type="primary" @click="handleUpdatePassword">{{ t('common.save') }}</el-button>
        </template>
      </el-dialog>
      <div class="stats">
        <h3>{{ t("personal.stats") }}</h3>
        <div class="stats-grid">
          <el-card class="stat-card">
            <template #header>
              <span>{{ t("personal.createdDocs") }}</span>
            </template>
            <div class="stat-value">{{ stats?.created_docs || 0 }}</div>
          </el-card>
          <el-card class="stat-card">
            <template #header>
              <span>{{ t("personal.collaboratedDocs") }}</span>
            </template>
            <div class="stat-value">{{ stats?.collaborated_docs || 0 }}</div>
          </el-card>
          <el-card class="stat-card">
            <template #header>
              <span>{{ t("personal.approvedDocs") }}</span>
            </template>
            <div class="stat-value">{{ stats?.approved_docs || 0 }}</div>
          </el-card>
        </div>
      </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import api from "@/api/client";
import { Edit, Lock, User } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";

interface DirectSupervisor {
  id?: number | null;
  display_name: string;
  display_name_en?: string;
  role_title?: string;
  role_title_en?: string;
  employee_no?: string;
  department_name?: string;
  department_name_en?: string;
  is_board?: boolean;
}

interface UserInfo {
  id: number;
  last_name: string;
  first_name: string;
  display_name?: string;
  login_name: string;
  employee_no: string;
  department_name: string;
  department_name_en?: string;
  position_short?: string;
  position_full_name?: string;
  role_name?: string;
  role_name_en?: string;
  role_level?: number;
  birth_date?: string;
  gender?: string;
  age?: number;
  is_manager?: boolean;
  is_super_admin?: boolean;
  direct_supervisor?: DirectSupervisor | null;
}

interface Stats {
  created_docs: number;
  collaborated_docs: number;
  approved_docs: number;
}

const { t, locale, te } = useI18n();
const user = ref<UserInfo | null>(null);
const stats = ref<Stats | null>(null);

const avatarUrl = computed(() => {
  return "https://via.placeholder.com/100";
});

const userInitials = computed(() => {
  if (!user.value) return "";
  const first = user.value.first_name?.charAt(0) || "";
  const last = user.value.last_name?.charAt(0) || "";
  return (first + last).toUpperCase() || (user.value.login_name?.charAt(0).toUpperCase() || "U");
});

const userDisplayName = computed(() => {
  if (!user.value) return "";
  if (locale.value === 'zh-CN') {
    return `${user.value.last_name || ''}${user.value.first_name || ''}`.trim() || user.value.login_name;
  }
  const fullEn = `${user.value.first_name || ''} ${user.value.last_name || ''}`.trim();
  return fullEn || user.value.login_name;
});

const formatDeptName = (name: string, nameEn?: string) => {
  if (!name) return "";
  if (te(`dept.${name}`)) return t(`dept.${name}`);
  if (nameEn && te(`dept.${nameEn}`)) return t(`dept.${nameEn}`);
  return locale.value === 'zh-CN' ? name : (nameEn || name);
};

const formatRoleName = (u: any) => {
  if (!u) return "";
  if (locale.value === 'zh-CN') {
    return u.role_name || (u.is_super_admin ? t('common.roles.admin') : (u.is_manager ? t('common.roles.manager') : t('common.roles.user')));
  }
  return u.role_name_en || u.role_name || (u.is_super_admin ? t('common.roles.admin') : (u.is_manager ? t('common.roles.manager') : t('common.roles.user')));
};

const formatSupervisorName = (sup: DirectSupervisor) => {
  if (!sup) return "";
  if (locale.value === 'zh-CN') return sup.display_name;
  return sup.display_name_en || sup.display_name;
};

const formatSupervisorRole = (sup: DirectSupervisor) => {
  if (!sup) return "";
  if (locale.value === 'zh-CN') return sup.role_title || t('admin.supervisor');
  return sup.role_title_en || sup.role_title || t('admin.supervisor');
};

const formatPosition = (u: any) => {
  if (!u) return "";
  const posKey = u.position_full_name || u.position_short;
  if (posKey && te('pos.' + posKey)) return t('pos.' + posKey);
  return posKey || "";
};

const editVisible = ref(false);
const editLoading = ref(false);
const editForm = ref({ first_name: '', last_name: '', gender: '', birth_date: '' });

async function loadUserInfo() {
  try {
    const { data } = await api.get("/auth/me");
    user.value = data;
    editForm.value = { ...data };
  } catch (error) {}
}

const passVisible = ref(false);
const passLoading = ref(false);
const passForm = ref({ old_password: '', new_password: '', confirm_password: '' });

async function handleUpdatePassword() {
  if (passForm.value.new_password !== passForm.value.confirm_password) {
    return ElMessage.error(t('profile.passMismatch'));
  }
  
  passLoading.value = true;
  try {
    await api.post("/auth/change-password", passForm.value);
    ElMessage.success(t('profile.passSuccess'));
    passVisible.value = false;
    passForm.value = { old_password: '', new_password: '', confirm_password: '' };
  } catch (e: any) {
    ElMessage.error(e.response?.data?.error || t('common.failed'));
  } finally {
    passLoading.value = false;
  }
}

async function saveProfile() {
  if (!user.value) return;
  editLoading.value = true;
  try {
    await api.patch(`/users/${user.value.id}`, editForm.value);
    ElMessage.success(t('profile.saveSuccess'));
    editVisible.value = false;
    await loadUserInfo();
  } catch (e) {
    ElMessage.error(t('profile.saveFailed'));
  } finally {
    editLoading.value = false;
  }
}

async function loadStats() {
  try {
    const { data } = await api.get("/stats");
    stats.value = data;
  } catch (error) {}
}

onMounted(() => {
  loadUserInfo();
  loadStats();
});
</script>

<style scoped>
.personal {
  padding: 24px;
}

.hero-header {
  background: linear-gradient(135deg, var(--el-color-primary) 0%, #7367f0 130%) !important;
  border-radius: 20px;
  padding: 28px 32px;
  margin-bottom: 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 8px 32px rgba(99, 102, 241, 0.18);
  border: 1px solid rgba(255,255,255,0.2);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-icon-ring {
  width: 52px; height: 52px;
  border-radius: 50%;
  background: rgba(255,255,255,0.18);
  display: flex; align-items: center; justify-content: center;
  font-size: 24px;
  color: #fff;
  flex-shrink: 0;
}

.page-title {
  margin: 0 0 4px !important;
  font-size: 1.5rem !important;
  font-weight: 800 !important;
  color: #fff !important;
}

.page-sub {
  margin: 0 !important;
  font-size: 0.9rem !important;
  color: rgba(255,255,255,0.8) !important;
}

.profile {
  display: flex;
  align-items: flex-start;
  margin-bottom: 32px;
  padding: 28px;
  background: var(--el-bg-color-overlay);
  border-radius: 16px;
  border: 1px solid var(--el-border-color-lighter);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
}

.avatar {
  margin-right: 32px;
  flex-shrink: 0;
}

.info {
  flex: 1;
}

.info h2 {
  margin: 0 0 18px 0;
  font-size: 24px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.detail {
  margin-bottom: 10px;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.detail-label {
  color: var(--el-text-color-secondary);
  min-width: 140px;
  font-weight: 500;
}

.detail-value {
  color: var(--el-text-color-primary);
}

.emp-code {
  background: var(--el-fill-color-light);
  padding: 2px 8px;
  border-radius: 6px;
  font-family: monospace;
  font-weight: 600;
  color: var(--el-color-primary);
}

.supervisor-detail {
  margin-top: 4px;
  margin-bottom: 12px;
}

.supervisor-badge-box {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.08), rgba(103, 194, 58, 0.08));
  border: 1px solid rgba(64, 158, 255, 0.25);
  padding: 4px 12px;
  border-radius: 20px;
}

.sup-avatar {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--el-color-primary);
  color: #fff;
  font-size: 12px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
}

.sup-name {
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.sup-role-tag {
  height: 20px;
  line-height: 18px;
  padding: 0 6px;
  border-radius: 4px;
}

.sup-no {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  font-family: monospace;
}

.stats h3 {
  margin: 0 0 16px 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.stat-card {
  text-align: center;
  border-radius: 12px;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--el-color-primary);
  margin-top: 8px;
}
</style>