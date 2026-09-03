<template>
  <div class="personal">
    <!-- Hero Header -->
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

    <!-- Main Profile Card -->
    <div class="profile-card" v-loading="loading">
      <!-- 1. Top Identity Banner (Avatar, Name, Role Tag, Supervisor, Action Buttons) -->
      <div class="profile-hero-section">
        <!-- Avatar Block -->
        <div class="avatar-col" @click="avatarDialogVisible = true" :title="t('profile.changeAvatar', '点击更换头像')">
          <div class="user-avatar-circle" :style="{ background: avatarGradient }">
            <img v-if="user?.avatar_url" :src="user.avatar_url" class="user-avatar-image" alt="avatar" />
            <span v-else class="user-avatar-text">{{ userInitials }}</span>
            
            <!-- Hover Camera Overlay -->
            <div class="avatar-hover-overlay">
              <el-icon class="camera-icon"><Camera /></el-icon>
              <span class="change-hint-text">{{ t('profile.changeAvatar', '更换头像') }}</span>
            </div>
          </div>
          <el-button link type="primary" size="small" :icon="PictureFilled" class="change-avatar-btn" @click.stop="avatarDialogVisible = true">
            {{ t('profile.changeAvatar', '更换头像') }}
          </el-button>
        </div>

        <!-- Identity Info Center -->
        <div class="identity-col">
          <div class="identity-name-row">
            <h2 class="user-title-name">{{ userDisplayName }}</h2>
            <el-tag size="default" :type="getRoleTagType(user)" effect="dark" class="role-badge">
              {{ formatRoleName(user) }}
            </el-tag>
            <el-tag size="small" type="success" effect="light" class="status-tag">
              <span class="status-dot"></span>
              {{ t('personal.statusActive', '正常在职') }}
            </el-tag>
          </div>

          <div class="identity-sub-row">
            <span class="identity-chip">
              <span class="chip-label">🔑 {{ t("personal.login") }}:</span>
              <span class="chip-val font-mono">@{{ user?.login_name || '—' }}</span>
            </span>
            <span class="identity-chip">
              <span class="chip-label">🔢 {{ t("personal.employeeNo") }}:</span>
              <code class="emp-code">{{ user?.employee_no || '—' }}</code>
            </span>
          </div>

          <!-- Direct Supervisor Pill -->
          <div class="supervisor-bar">
            <span class="sup-label">👤 {{ t("personal.supervisor") }}:</span>
            <div v-if="user?.direct_supervisor" class="supervisor-pill">
              <span class="sup-avatar">{{ (user.direct_supervisor.display_name || 'S').slice(0, 1).toUpperCase() }}</span>
              <span class="sup-name">{{ formatSupervisorName(user.direct_supervisor) }}</span>
              <el-tag size="small" type="warning" effect="plain" class="sup-role-tag">
                {{ formatSupervisorRole(user.direct_supervisor) }}
              </el-tag>
              <span v-if="user.direct_supervisor.employee_no" class="sup-no">({{ user.direct_supervisor.employee_no }})</span>
            </div>
            <span v-else class="sup-val text-muted">🏛️ {{ t("personal.noSupervisor") }}</span>
          </div>
        </div>

        <!-- Right Side Actions -->
        <div class="actions-col">
          <el-button type="primary" :icon="Edit" class="btn-action-primary" @click="editVisible = true">
            {{ t('common.edit') }}
          </el-button>
          <el-button type="warning" plain :icon="Lock" class="btn-action-secondary" @click="passVisible = true">
            {{ t('profile.changePass') }}
          </el-button>
        </div>
      </div>

      <el-divider class="profile-divider" />

      <!-- 2. Structured 2-Column Information Grid -->
      <div class="info-blocks-grid">
        <!-- Card 1: 🏛️ 组织架构与职务 (Organization & Position) -->
        <div class="info-block-card">
          <div class="block-card-header">
            <span class="block-icon">🏛️</span>
            <span class="block-title">{{ t('personal.orgSection', '组织架构与职务') }}</span>
          </div>
          <div class="block-card-body">
            <!-- 所属部门 -->
            <div class="field-item">
              <span class="field-label">🏢 {{ t("personal.department") }}</span>
              <div class="field-val dept-val-box">
                <template v-if="user?.department_name || user?.department?.name">
                  <span class="dept-badge">
                    {{ formatDeptName(user?.department_name || user?.department?.name || '', user?.department_name_en || user?.department?.name_en) }}
                  </span>
                </template>
                <template v-else>
                  <span class="text-muted">{{ t("admin.unassigned", "未分配部门") }}</span>
                  <el-button link type="primary" size="small" @click="editVisible = true">
                    {{ t('personal.assignDeptNow', '立即分配部门') }}
                  </el-button>
                </template>
              </div>
            </div>

            <!-- 角色职级 -->
            <div class="field-item">
              <span class="field-label">👑 {{ t("personal.role") }}</span>
              <div class="field-val">
                <el-tag size="default" :type="getRoleTagType(user)" effect="light">
                  {{ formatRoleName(user) }} (Level {{ user?.role_level || 10 }})
                </el-tag>
              </div>
            </div>

            <!-- 职位职务 -->
            <div class="field-item">
              <span class="field-label">💼 {{ t("personal.position") }}</span>
              <span class="field-val">{{ formatPosition(user) || t("personal.unspecified", "未设置") }}</span>
            </div>

            <!-- 直属上级 / 汇报对象 -->
            <div class="field-item">
              <span class="field-label">👤 {{ t("personal.supervisor") }}</span>
              <div class="field-val">
                <div v-if="user?.direct_supervisor" class="supervisor-pill">
                  <span class="sup-avatar">{{ (user.direct_supervisor.display_name || 'S').slice(0, 1).toUpperCase() }}</span>
                  <span class="sup-name">{{ formatSupervisorName(user.direct_supervisor) }}</span>
                  <el-tag size="small" type="warning" effect="plain" class="sup-role-tag">
                    {{ formatSupervisorRole(user.direct_supervisor) }}
                  </el-tag>
                  <span v-if="user.direct_supervisor.employee_no" class="sup-no">({{ user.direct_supervisor.employee_no }})</span>
                </div>
                <span v-else class="text-muted">🏛️ {{ t("personal.noSupervisor") }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Card 2: 👤 账号与个人资料 (Account & Personal Details) -->
        <div class="info-block-card">
          <div class="block-card-header">
            <span class="block-icon">👤</span>
            <span class="block-title">{{ t('personal.accountSection', '账号与个人资料') }}</span>
          </div>
          <div class="block-card-body">
            <!-- 手机号码 -->
            <div class="field-item">
              <span class="field-label">📱 {{ t("personal.phone") }}</span>
              <div class="field-val contact-val">
                <span class="font-mono" :class="{ 'text-muted': !user?.phone }">
                  {{ user?.phone || t("personal.unspecified", "未设置") }}
                </span>
                <el-button 
                  v-if="user?.phone" 
                  link 
                  type="primary" 
                  size="small" 
                  :icon="CopyDocument" 
                  class="copy-btn"
                  @click="copyField(user.phone, t('personal.phone'))"
                  :title="t('personal.copyPhone', '复制手机号')"
                />
              </div>
            </div>

            <!-- 电子邮箱 -->
            <div class="field-item">
              <span class="field-label">✉️ {{ t("personal.email") }}</span>
              <div class="field-val contact-val">
                <span class="font-mono" :class="{ 'text-muted': !user?.email }">
                  {{ user?.email || t("personal.unspecified", "未设置") }}
                </span>
                <el-button 
                  v-if="user?.email" 
                  link 
                  type="primary" 
                  size="small" 
                  :icon="CopyDocument" 
                  class="copy-btn"
                  @click="copyField(user.email, t('personal.email'))"
                  :title="t('personal.copyEmail', '复制邮箱')"
                />
              </div>
            </div>

            <!-- 性别 -->
            <div class="field-item">
              <span class="field-label">⚧ {{ t("personal.gender") }}</span>
              <div class="field-val">
                <span class="gender-pill">
                  <span v-if="user?.gender === 'Male'" class="gender-icon male">♂</span>
                  <span v-else-if="user?.gender === 'Female'" class="gender-icon female">♀</span>
                  {{ formatGender(user?.gender) }}
                </span>
              </div>
            </div>

            <!-- 出生日期与年龄 -->
            <div class="field-item">
              <span class="field-label">🎂 {{ t("personal.birthDate") }}</span>
              <div class="field-val">
                <span v-if="user?.birth_date">
                  {{ user.birth_date }}
                  <span v-if="user.age" class="age-badge">({{ user.age }} {{ t('personal.yearsOld', '岁') }})</span>
                </span>
                <span v-else class="text-muted">{{ t("personal.unspecified", "未设置") }}</span>
              </div>
            </div>

            <!-- 账号状态 -->
            <div class="field-item">
              <span class="field-label">🛡️ {{ t("personal.accountStatus") }}</span>
              <div class="field-val">
                <el-tag size="small" type="success" effect="plain" class="status-tag">
                  <span class="status-dot"></span>
                  {{ t('personal.statusActive', '正常在职') }}
                </el-tag>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Edit Dialog (Enhanced 2-Column Responsive Layout) -->
    <el-dialog :title="t('profile.title')" v-model="editVisible" width="560px" class="profile-edit-dialog">
      <el-form :model="editForm" label-position="top" v-loading="editLoading">
        <div class="dialog-form-row">
          <el-form-item :label="t('profile.lastName')" style="flex: 1;">
            <el-input v-model="editForm.last_name" clearable />
          </el-form-item>
          <el-form-item :label="t('profile.firstName')" style="flex: 1;">
            <el-input v-model="editForm.first_name" clearable />
          </el-form-item>
        </div>

        <div class="dialog-form-row">
          <el-form-item :label="t('profile.gender')" style="flex: 1;">
            <el-select v-model="editForm.gender" style="width: 100%" clearable :placeholder="t('personal.gender')">
              <el-option :label="t('personal.male', '男 (Male)')" value="Male" />
              <el-option :label="t('personal.female', '女 (Female)')" value="Female" />
              <el-option :label="t('personal.otherGender', '其他 / 保密 (Other)')" value="Other" />
            </el-select>
          </el-form-item>
          <el-form-item :label="t('profile.birthDate')" style="flex: 1;">
            <el-date-picker v-model="editForm.birth_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
        </div>

        <el-form-item :label="t('profile.dept', '所属部门')">
          <el-select 
            v-model="editForm.department_id" 
            style="width: 100%" 
            clearable 
            filterable 
            :placeholder="t('profile.selectDept', '请选择所属部门')"
          >
            <el-option 
              v-for="d in departmentsList" 
              :key="d.id" 
              :label="formatDeptOptionLabel(d)" 
              :value="d.id" 
            />
          </el-select>
        </el-form-item>

        <el-form-item :label="t('personal.position', '职位职务')">
          <el-input 
            v-model="editForm.position_short" 
            :placeholder="t('personal.positionPlaceholder', '请输入职位名称（如：系统管理员、技术总监等）')" 
            clearable 
          />
        </el-form-item>

        <div class="dialog-form-row">
          <el-form-item :label="t('profile.phone', '手机号码')" style="flex: 1;">
            <el-input v-model="editForm.phone" :placeholder="t('profile.phonePlaceholder', '请输入手机号码')" clearable>
              <template #prefix>
                <el-icon><Phone /></el-icon>
              </template>
            </el-input>
          </el-form-item>
          <el-form-item :label="t('profile.email', '电子邮箱')" style="flex: 1;">
            <el-input v-model="editForm.email" :placeholder="t('profile.emailPlaceholder', '请输入电子邮箱')" clearable>
              <template #prefix>
                <el-icon><Message /></el-icon>
              </template>
            </el-input>
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="saveProfile">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>

    <!-- Password Dialog -->
    <el-dialog :title="t('profile.changePass')" v-model="passVisible" width="450px">
      <el-form :model="passForm" label-position="top" v-loading="passLoading">
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

    <!-- 统计卡片 (Statistics) -->
    <div class="stats-section">
      <div class="stats-header-bar">
        <span class="stats-bar-icon">📊</span>
        <h3 class="stats-title">{{ t("personal.stats") }}</h3>
      </div>
      <div class="stats-grid">
        <el-card class="stat-card" shadow="hover">
          <template #header>
            <div class="stat-card-header">
              <span class="stat-icon">📝</span>
              <span>{{ t("personal.createdDocs") }}</span>
            </div>
          </template>
          <div class="stat-value">{{ stats?.created_docs ?? 0 }}</div>
        </el-card>
        <el-card class="stat-card" shadow="hover">
          <template #header>
            <div class="stat-card-header">
              <span class="stat-icon">🤝</span>
              <span>{{ t("personal.collaboratedDocs") }}</span>
            </div>
          </template>
          <div class="stat-value">{{ stats?.collaborated_docs ?? 0 }}</div>
        </el-card>
        <el-card class="stat-card" shadow="hover">
          <template #header>
            <div class="stat-card-header">
              <span class="stat-icon">✅</span>
              <span>{{ t("personal.approvedDocs") }}</span>
            </div>
          </template>
          <div class="stat-value">{{ stats?.approved_docs ?? 0 }}</div>
        </el-card>
      </div>
    </div>

    <!-- Avatar Selector Dialog -->
    <AvatarSelectorDialog
      v-model="avatarDialogVisible"
      :user="user"
      @success="handleAvatarUpdated"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import api from "@/api/client";
import { useAuthStore } from "@/stores/auth";
import { Edit, Lock, User, Phone, Message, Camera, PictureFilled, CopyDocument } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import AvatarSelectorDialog from "@/components/AvatarSelectorDialog.vue";

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
  last_name?: string;
  first_name?: string;
  display_name?: string;
  login_name: string;
  employee_no: string;
  phone?: string;
  email?: string;
  avatar_url?: string;
  department_id?: number | null;
  department_name?: string;
  department_name_en?: string;
  department?: { id?: number | null; name?: string; name_en?: string; } | null;
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
const authStore = useAuthStore();
const avatarDialogVisible = ref(false);

function handleAvatarUpdated(newAvatarUrl: string) {
  if (user.value) {
    user.value.avatar_url = newAvatarUrl;
  }
}
const user = ref<UserInfo | null>((authStore.user as any) || null);
const stats = ref<Stats | null>(null);
const loading = ref(false);

const avatarGradient = computed(() => {
  if (user.value?.is_super_admin || (user.value?.role_level && user.value?.role_level >= 100)) {
    return "linear-gradient(135deg, #409eff 0%, #7367f0 100%)";
  }
  if (user.value?.is_manager || (user.value?.role_level && user.value?.role_level >= 50)) {
    return "linear-gradient(135deg, #10b981 0%, #059669 100%)";
  }
  return "linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)";
});

const userInitials = computed(() => {
  if (!user.value) return "U";
  if (user.value.display_name) {
    return user.value.display_name.slice(0, 2).toUpperCase();
  }
  const first = user.value.first_name?.charAt(0) || "";
  const last = user.value.last_name?.charAt(0) || "";
  return (last + first).toUpperCase() || (user.value.login_name?.slice(0, 2).toUpperCase() || "U");
});

const userDisplayName = computed(() => {
  if (!user.value) return "";
  if (locale.value === 'zh-CN') {
    if (user.value.display_name) return user.value.display_name;
    const zh = `${user.value.last_name || ''}${user.value.first_name || ''}`.trim();
    return zh || user.value.login_name;
  }
  const en = `${user.value.first_name || ''} ${user.value.last_name || ''}`.trim();
  return en || user.value.display_name || user.value.login_name;
});

const getRoleTagType = (u: any) => {
  if (!u) return 'info';
  if (u.is_super_admin || (u.role_level && u.role_level >= 100)) return 'danger';
  if (u.is_manager || (u.role_level && u.role_level >= 50)) return 'warning';
  return 'primary';
};

const formatDeptName = (name: string, nameEn?: string) => {
  if (!name) return "";
  if (name.includes("最高管理与决策中心") || name === "Board & Executive" || name === "BOARD_EXEC") {
    return locale.value === 'zh-CN' ? '企业最高管理与决策中心 (Board & Executive)' : 'Executive Governance Center (Board & Executive)';
  }
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

const formatGender = (gender?: string) => {
  if (!gender) return t('personal.unspecified', '未设置');
  const g = gender.trim().toLowerCase();
  if (g === 'male' || g === '男') return t('personal.genderMaleShort', '男');
  if (g === 'female' || g === '女') return t('personal.genderFemaleShort', '女');
  return t('personal.genderOtherShort', '其他 / 保密');
};

async function copyField(text: string, label: string) {
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    ElMessage.success(`${label} ${t('personal.copySuccess', '已复制到剪贴板')}！`);
  } catch {
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    ElMessage.success(`${label} ${t('personal.copySuccess', '已复制到剪贴板')}！`);
  }
}

const editVisible = ref(false);
const editLoading = ref(false);
const departmentsList = ref<any[]>([]);

const editForm = ref<{
  first_name: string;
  last_name: string;
  gender: string;
  birth_date: string;
  phone: string;
  email: string;
  department_id: number | null;
  position_short: string;
}>({ 
  first_name: '', 
  last_name: '', 
  gender: '', 
  birth_date: '', 
  phone: '', 
  email: '',
  department_id: null,
  position_short: ''
});

const formatDeptOptionLabel = (d: any) => {
  if (!d) return "";
  const name = locale.value === 'zh-CN' ? d.name : (d.name_en || d.name);
  if (d.level >= 100 || d.code === 'BOARD_EXEC' || d.name?.includes('最高管理与决策中心')) {
    return `🏛️ ${locale.value === 'zh-CN' ? '企业最高管理与决策中心 (Board & Executive)' : 'Executive Governance Center (Board & Executive)'}`;
  }
  const code = d.code ? ` (${d.code})` : '';
  return `${name}${code}`;
};

async function loadDepartments() {
  try {
    const { data } = await api.get("/users/departments");
    departmentsList.value = Array.isArray(data) ? data : [];
  } catch (e) {
    console.error("Failed to load departments:", e);
  }
}

async function loadUserInfo() {
  loading.value = true;
  try {
    const { data } = await api.get("/auth/me");
    user.value = data;
    editForm.value = { 
      first_name: data.first_name || '', 
      last_name: data.last_name || '', 
      gender: data.gender || '', 
      birth_date: data.birth_date || '',
      phone: data.phone || '',
      email: data.email || '',
      department_id: data.department_id || data.department?.id || null,
      position_short: data.position_short || data.position || ''
    };
    if (authStore.user) {
      authStore.user = { ...authStore.user, ...data };
    }
  } catch (error) {
    console.error("Failed to load user info:", error);
  } finally {
    loading.value = false;
  }
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
  } catch (e: any) {
    ElMessage.error(e.response?.data?.error || t('profile.saveFailed'));
  } finally {
    editLoading.value = false;
  }
}

async function loadStats() {
  try {
    const { data } = await api.get("/users/me/stats");
    stats.value = data;
  } catch (error) {
    console.error("Failed to load user stats:", error);
  }
}

onMounted(() => {
  loadUserInfo();
  loadStats();
  loadDepartments();
});
</script>

<style scoped>
.personal {
  padding: 24px;
}

.hero-header {
  background: linear-gradient(135deg, var(--el-color-primary) 0%, #7367f0 130%) !important;
  border-radius: 16px;
  padding: 24px 30px;
  margin-bottom: 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.16);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-icon-ring {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  color: #fff;
  flex-shrink: 0;
}

.page-title {
  margin: 0 0 4px !important;
  font-size: 1.4rem !important;
  font-weight: 800 !important;
  color: #fff !important;
}

.page-sub {
  margin: 0 !important;
  font-size: 0.88rem !important;
  color: rgba(255, 255, 255, 0.85) !important;
}

/* ── Main Profile Card ────────────────────────────── */
.profile-card {
  margin-bottom: 24px;
  padding: 24px 28px;
  background: var(--el-bg-color-overlay);
  border-radius: 14px;
  border: 1px solid var(--el-border-color-lighter);
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.04);
}

.profile-hero-section {
  display: flex;
  align-items: center;
  gap: 24px;
  position: relative;
}

.avatar-col {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.user-avatar-circle {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  overflow: hidden;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 14px rgba(64, 158, 255, 0.2);
  border: 3px solid rgba(255, 255, 255, 0.95);
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}

.avatar-col:hover .user-avatar-circle {
  transform: scale(1.04);
  box-shadow: 0 6px 20px rgba(64, 158, 255, 0.35);
}

.user-avatar-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.user-avatar-text {
  font-size: 26px;
  font-weight: 800;
  color: #ffffff;
  letter-spacing: 1px;
}

.avatar-hover-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.52);
  backdrop-filter: blur(2px);
  color: #ffffff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  opacity: 0;
  transition: opacity 0.2s ease;
  border-radius: 50%;
}

.avatar-col:hover .avatar-hover-overlay {
  opacity: 1;
}

.camera-icon {
  font-size: 20px;
}

.change-hint-text {
  font-size: 11px;
  font-weight: 600;
}

.change-avatar-btn {
  font-size: 12px;
  font-weight: 600;
  padding: 0;
}

/* ── Identity Column ────────────────────────────── */
.identity-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.identity-name-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.user-title-name {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.role-badge {
  font-weight: 600;
  border-radius: 6px;
  font-size: 12px;
  padding: 0 8px;
  height: 24px;
  line-height: 22px;
}

.status-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 600;
  border-radius: 12px;
  padding: 0 10px;
  height: 24px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--el-color-success);
  display: inline-block;
}

.identity-sub-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 13px;
}

.identity-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.chip-label {
  color: var(--el-text-color-secondary);
  font-weight: 500;
}

.chip-val {
  color: var(--el-text-color-primary);
  font-weight: 600;
}

.font-mono {
  font-family: 'JetBrains Mono', Consolas, Monaco, monospace;
}

.emp-code {
  background: var(--el-fill-color-light);
  padding: 2px 8px;
  border-radius: 6px;
  font-family: 'JetBrains Mono', Consolas, Monaco, monospace;
  font-weight: 600;
  color: var(--el-color-primary);
  border: 1px solid var(--el-border-color-lighter);
}

.supervisor-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 13px;
}

.sup-label {
  color: var(--el-text-color-secondary);
  font-weight: 500;
}

.supervisor-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.08), rgba(103, 194, 58, 0.08));
  border: 1px solid rgba(64, 158, 255, 0.25);
  padding: 3px 12px;
  border-radius: 16px;
}

.sup-avatar {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--el-color-primary);
  color: #fff;
  font-size: 11px;
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
  height: 18px;
  line-height: 16px;
  padding: 0 5px;
  font-size: 11px;
  border-radius: 4px;
}

.sup-no {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  font-family: monospace;
}

/* ── Actions Column (Top Right) ─────────────────── */
.actions-col {
  display: flex;
  align-items: center;
  gap: 10px;
  align-self: flex-start;
  padding-top: 2px;
}

.btn-action-primary,
.btn-action-secondary {
  border-radius: 8px;
  font-weight: 600;
  padding: 8px 16px;
}

.profile-divider {
  margin: 18px 0 18px;
  border-color: var(--el-border-color-lighter);
}

/* ── Structured 2-Column Grid ──────────────────────── */
.info-blocks-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 4px;
}

@media (max-width: 880px) {
  .info-blocks-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
}

.info-block-card {
  background: var(--el-fill-color-blank);
  border: 1px solid var(--el-border-color-light);
  border-radius: 12px;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.02);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.info-block-card:hover {
  border-color: var(--el-color-primary-light-5);
  box-shadow: 0 4px 14px rgba(64, 158, 255, 0.08);
}

.block-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.block-icon {
  font-size: 16px;
}

.block-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.block-card-body {
  display: flex;
  flex-direction: column;
}

.field-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 10px 0;
  border-bottom: 1px dashed var(--el-border-color-lighter);
  font-size: 13.5px;
  min-height: 42px;
}

.field-item:last-child {
  border-bottom: none;
  padding-bottom: 2px;
}

.field-item:first-child {
  padding-top: 2px;
}

.field-label {
  color: var(--el-text-color-secondary);
  font-weight: 500;
  font-size: 13.5px;
  flex-shrink: 0;
  min-width: 100px;
}

.field-val {
  color: var(--el-text-color-primary);
  font-weight: 600;
  font-size: 13.5px;
  text-align: right;
  word-break: break-word;
}

.dept-badge {
  color: var(--el-color-primary);
  font-weight: 600;
  background: rgba(64, 158, 255, 0.08);
  padding: 3px 10px;
  border-radius: 6px;
  display: inline-block;
}

.gender-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.gender-icon.male {
  color: #409eff;
  font-weight: bold;
  font-size: 15px;
}

.gender-icon.female {
  color: #f43f5e;
  font-weight: bold;
  font-size: 15px;
}

.age-badge {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  font-weight: 500;
  margin-left: 4px;
}

.contact-val {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.copy-btn {
  padding: 0;
  font-size: 14px;
}

/* ── Dialog Layout ────────────────────────────────── */
.dialog-form-row {
  display: flex;
  gap: 16px;
}

/* ── Statistics Section ──────────────────────────── */
.stats-section {
  margin-top: 14px;
}

.stats-header-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}

.stats-bar-icon {
  font-size: 16px;
}

.stats-title {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.stat-card {
  border-radius: 12px;
  border: 1px solid var(--el-border-color-light);
  transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
}

.stat-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 13px;
}

.stat-icon {
  font-size: 15px;
}

.stat-value {
  font-size: 28px;
  font-weight: 800;
  color: var(--el-color-primary);
  text-align: center;
  padding: 4px 0;
}
</style>