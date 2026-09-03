<template>
  <el-dialog
    v-model="visible"
    :title="t('personal.memberProfileCard', '成员个人信息卡')"
    width="480px"
    class="member-profile-card-dialog"
    destroy-on-close
    append-to-body
    :show-close="true"
  >
    <div class="member-card-container" v-loading="loading">
      <!-- Top Banner Header -->
      <div class="card-hero-banner" :style="{ background: headerGradient }">
        <div class="banner-pattern-overlay"></div>
        <div class="banner-level-tag">
          <span class="level-chip">L{{ memberData?.role_level ?? 10 }}</span>
        </div>
      </div>

      <!-- Avatar & Identity Info -->
      <div class="card-identity-section">
        <div class="avatar-wrapper" :style="{ borderColor: avatarBorderColor }">
          <div class="avatar-circle" :style="{ background: avatarGradient }">
            <img v-if="memberData?.avatar_url" :src="memberData.avatar_url" class="avatar-image-src" alt="avatar" />
            <span v-else>{{ userInitials }}</span>
          </div>
          <span v-if="memberData?.is_manager || memberData?.is_super_admin" class="avatar-crown-badge" title="主管/负责人">
            👑
          </span>
        </div>

        <div class="identity-text">
          <div class="name-row">
            <h3 class="member-name">{{ displayName }}</h3>
            <el-tag :type="roleTagType" size="small" effect="dark" class="role-pill">
              {{ roleTitle }}
            </el-tag>
          </div>
          <div class="sub-identity-row">
            <span class="login-name-badge">@{{ memberData?.login_name || '—' }}</span>
            <code class="emp-no-badge">{{ memberData?.employee_no || '—' }}</code>
            <el-tag v-if="memberData?.registration_status === 'active' || !memberData?.registration_status" size="small" type="success" effect="plain" class="status-tag">
              ● {{ t('personal.statusActive', '在职') }}
            </el-tag>
          </div>
        </div>
      </div>

      <!-- Detail Info Sections -->
      <div class="card-body-content">
        <!-- 1. 组织与汇报 -->
        <div class="info-group-card">
          <div class="group-title">
            <el-icon><OfficeBuilding /></el-icon>
            <span>{{ t('personal.department', '组织与归属') }}</span>
          </div>
          
          <div class="info-row">
            <span class="info-key">🏢 {{ t('personal.department', '所属部门') }}:</span>
            <span class="info-val highlight-dept">
              {{ formatDeptName(memberData?.department_name, memberData?.department_name_en) || t('admin.unassigned', '未分配部门') }}
            </span>
          </div>

          <div class="info-row" v-if="memberData?.position_full_name || memberData?.position_short">
            <span class="info-key">💼 {{ t('personal.position', '职务岗位') }}:</span>
            <span class="info-val">{{ formatPosition(memberData) }}</span>
          </div>

          <div class="info-row supervisor-row">
            <span class="info-key">👤 {{ t('personal.supervisor', '直属主管') }}:</span>
            <div v-if="memberData?.direct_supervisor" class="sup-mini-pill">
              <span class="sup-avatar-letter">{{ (memberData.direct_supervisor.display_name || 'S').slice(0, 1).toUpperCase() }}</span>
              <span class="sup-name-text">{{ formatSupervisorName(memberData.direct_supervisor) }}</span>
              <el-tag size="small" type="warning" effect="plain" class="sup-role-tag">
                {{ formatSupervisorRole(memberData.direct_supervisor) }}
              </el-tag>
            </div>
            <span v-else class="info-val text-muted">{{ t('personal.noSupervisor', '最高决策层 / 董事会') }}</span>
          </div>
        </div>

        <!-- 2. 联系方式 -->
        <div class="info-group-card contact-group">
          <div class="group-title">
            <el-icon><Phone /></el-icon>
            <span>{{ t('personal.contactInfo', '联系方式') }}</span>
          </div>

          <div class="info-row contact-row">
            <span class="info-key">📱 {{ t('personal.phone', '手机号码') }}:</span>
            <div class="contact-val-wrap">
              <span class="info-val font-mono" :class="{ 'text-muted': !memberData?.phone }">
                {{ memberData?.phone || t('personal.unspecified', '未设置') }}
              </span>
              <el-tooltip v-if="memberData?.phone" :content="t('personal.copyPhone', '复制手机号')" placement="top">
                <el-button link size="small" :icon="CopyDocument" @click="copyText(memberData.phone, t('personal.phone', '手机号'))" />
              </el-tooltip>
            </div>
          </div>

          <div class="info-row contact-row">
            <span class="info-key">✉️ {{ t('personal.email', '电子邮箱') }}:</span>
            <div class="contact-val-wrap">
              <span class="info-val font-mono" :class="{ 'text-muted': !memberData?.email }">
                {{ memberData?.email || t('personal.unspecified', '未设置') }}
              </span>
              <el-tooltip v-if="memberData?.email" :content="t('personal.copyEmail', '复制邮箱')" placement="top">
                <el-button link size="small" :icon="CopyDocument" @click="copyText(memberData.email, t('personal.email', '邮箱'))" />
              </el-tooltip>
            </div>
          </div>
        </div>

        <!-- 3. 个人档案 -->
        <div class="info-group-card" v-if="memberData?.gender || memberData?.birth_date">
          <div class="group-title">
            <el-icon><User /></el-icon>
            <span>{{ t('profile.title', '个人档案') }}</span>
          </div>

          <div class="info-row" v-if="memberData?.gender">
            <span class="info-key">⚧ {{ t('personal.gender', '性别') }}:</span>
            <span class="info-val">{{ memberData.gender === 'Male' ? t('personal.male', '男') : (memberData.gender === 'Female' ? t('personal.female', '女') : memberData.gender) }}</span>
          </div>

          <div class="info-row" v-if="memberData?.birth_date">
            <span class="info-key">🎂 {{ t('personal.birthDate', '出生日期') }}:</span>
            <span class="info-val">{{ memberData.birth_date }} <span v-if="memberData.age" class="text-muted">({{ t('personal.age', '年龄') }}: {{ memberData.age }})</span></span>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer-actions">
        <el-button 
          v-if="memberData?.phone || memberData?.email" 
          type="info" 
          plain 
          size="default" 
          :icon="CopyDocument" 
          @click="copyAllContactInfo"
        >
          {{ t('personal.copySuccess', '一键复制联系方式') }}
        </el-button>
        <el-button 
          v-if="canEdit" 
          type="primary" 
          size="default" 
          :icon="Edit" 
          @click="$emit('edit-user', memberData)"
        >
          {{ t('personal.editMember', '编辑成员') }}
        </el-button>
        <el-button @click="visible = false">{{ t('common.close', '关闭') }}</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import api from "@/api/client";
import { ElMessage } from "element-plus";
import { 
  OfficeBuilding, Phone, User, CopyDocument, Edit
} from "@element-plus/icons-vue";

const { t, locale, te } = useI18n();

const props = withDefaults(
  defineProps<{
    modelValue: boolean;
    user: any;
    canEdit?: boolean;
  }>(),
  {
    modelValue: false,
    user: null,
    canEdit: false
  }
);

const emit = defineEmits<{
  (e: "update:modelValue", val: boolean): void;
  (e: "edit-user", user: any): void;
}>();

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit("update:modelValue", val)
});

const memberData = ref<any>(null);
const loading = ref(false);

watch(
  () => [props.modelValue, props.user],
  async ([isVis, currUser]) => {
    if (isVis && currUser) {
      memberData.value = { ...currUser };
      if (currUser.id) {
        await loadFullUserDetail(currUser.id);
      }
    }
  },
  { immediate: true }
);

async function loadFullUserDetail(userId: number) {
  loading.value = true;
  try {
    const { data } = await api.get(`/users/${userId}`);
    if (data) {
      memberData.value = { ...memberData.value, ...data };
    }
  } catch (err) {
    // If endpoint fails, keep existing basic user data
    console.warn("Failed to load user full profile:", err);
  } finally {
    loading.value = false;
  }
}

const userInitials = computed(() => {
  const u = memberData.value;
  if (!u) return "U";
  if (u.display_name) return u.display_name.slice(0, 2).toUpperCase();
  if (u.username) return u.username.slice(0, 2).toUpperCase();
  if (u.first_name || u.last_name) {
    return `${u.last_name || ''}${u.first_name || ''}`.slice(0, 2).toUpperCase();
  }
  return u.login_name ? u.login_name.slice(0, 2).toUpperCase() : "U";
});

const displayName = computed(() => {
  const u = memberData.value;
  if (!u) return "";
  if (locale.value === 'zh-CN') {
    if (u.display_name) return u.display_name;
    const zh = `${u.last_name || ''}${u.first_name || ''}`.trim();
    return zh || u.username || u.login_name;
  }
  const en = `${u.first_name || ''} ${u.last_name || ''}`.trim();
  return en || u.display_name || u.username || u.login_name;
});

const roleTitle = computed(() => {
  const u = memberData.value;
  if (!u) return "";
  if (locale.value === 'zh-CN') {
    return u.role_name || (u.is_super_admin ? t('common.roles.admin') : (u.is_manager ? t('common.roles.manager') : t('common.roles.user')));
  }
  return u.role_name_en || u.role_name || (u.is_super_admin ? t('common.roles.admin') : (u.is_manager ? t('common.roles.manager') : t('common.roles.user')));
});

const roleTagType = computed(() => {
  const u = memberData.value;
  if (!u) return 'info';
  const lvl = u.role_level ?? (u.is_super_admin ? 100 : (u.is_manager ? 50 : 10));
  if (lvl >= 100 || u.is_super_admin) return 'danger';
  if (lvl >= 80) return 'warning';
  if (lvl >= 50 || u.is_manager) return 'success';
  return 'primary';
});

const headerGradient = computed(() => {
  const u = memberData.value;
  const lvl = u?.role_level ?? (u?.is_super_admin ? 100 : (u?.is_manager ? 50 : 10));
  if (lvl >= 100 || u?.is_super_admin) {
    return 'linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #db2777 100%)';
  }
  if (lvl >= 80) {
    return 'linear-gradient(135deg, #d97706 0%, #ea580c 50%, #e11d48 100%)';
  }
  if (lvl >= 50 || u?.is_manager) {
    return 'linear-gradient(135deg, #059669 0%, #10b981 50%, #0284c7 100%)';
  }
  return 'linear-gradient(135deg, #2563eb 0%, #3b82f6 50%, #6366f1 100%)';
});

const avatarGradient = computed(() => {
  const u = memberData.value;
  const lvl = u?.role_level ?? (u?.is_super_admin ? 100 : (u?.is_manager ? 50 : 10));
  if (lvl >= 100 || u?.is_super_admin) {
    return 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)';
  }
  if (lvl >= 80) {
    return 'linear-gradient(135deg, #f59e0b 0%, #ea580c 100%)';
  }
  if (lvl >= 50 || u?.is_manager) {
    return 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
  }
  return 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)';
});

const avatarBorderColor = computed(() => {
  const u = memberData.value;
  const lvl = u?.role_level ?? (u?.is_super_admin ? 100 : (u?.is_manager ? 50 : 10));
  if (lvl >= 100 || u?.is_super_admin) return '#c084fc';
  if (lvl >= 80) return '#fcd34d';
  if (lvl >= 50 || u?.is_manager) return '#6ee7b7';
  return '#93c5fd';
});

const formatDeptName = (name?: string, nameEn?: string) => {
  if (!name) return "";
  if (name.includes("最高管理与决策中心") || name === "Board & Executive" || name === "BOARD_EXEC") {
    return locale.value === 'zh-CN' ? '企业最高管理与决策中心 (Board & Executive)' : 'Executive Governance Center (Board & Executive)';
  }
  if (te(`dept.${name}`)) return t(`dept.${name}`);
  if (nameEn && te(`dept.${nameEn}`)) return t(`dept.${nameEn}`);
  return locale.value === 'zh-CN' ? name : (nameEn || name);
};

const formatPosition = (u: any) => {
  if (!u) return "";
  const posKey = u.position_full_name || u.position_short;
  if (posKey && te('pos.' + posKey)) return t('pos.' + posKey);
  return posKey || "";
};

const formatSupervisorName = (sup: any) => {
  if (!sup) return "";
  if (locale.value === 'zh-CN') return sup.display_name;
  return sup.display_name_en || sup.display_name;
};

const formatSupervisorRole = (sup: any) => {
  if (!sup) return "";
  if (locale.value === 'zh-CN') return sup.role_title || t('admin.supervisor');
  return sup.role_title_en || sup.role_title || t('admin.supervisor');
};

async function copyText(text: string, label: string) {
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    ElMessage.success(`${label} ${t('personal.copySuccess', '已复制到剪贴板')}！`);
  } catch (err) {
    // Fallback copy
    const textarea = document.createElement('textarea');
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    ElMessage.success(`${label} ${t('personal.copySuccess', '已复制到剪贴板')}！`);
  }
}

async function copyAllContactInfo() {
  const u = memberData.value;
  if (!u) return;
  const lines = [
    `姓名: ${displayName.value}`,
    `工号: ${u.employee_no || ''}`,
    `部门: ${formatDeptName(u.department_name, u.department_name_en)}`,
    u.phone ? `手机: ${u.phone}` : '',
    u.email ? `邮箱: ${u.email}` : '',
  ].filter(Boolean).join('\n');

  await copyText(lines, t('personal.contactInfo', '联系方式'));
}
</script>

<style scoped>
.member-profile-card-dialog :deep(.el-dialog__body) {
  padding: 0;
  overflow: hidden;
  border-radius: 12px;
}

.member-card-container {
  position: relative;
  background: var(--el-bg-color);
}

/* ── Top Hero Banner ───────────────────────────────────────── */
.card-hero-banner {
  height: 96px;
  position: relative;
  display: flex;
  justify-content: flex-end;
  align-items: flex-start;
  padding: 12px 16px;
  overflow: hidden;
}

.banner-pattern-overlay {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(rgba(255, 255, 255, 0.2) 1px, transparent 1px);
  background-size: 12px 12px;
  opacity: 0.6;
}

.banner-level-tag {
  position: relative;
  z-index: 2;
}

.level-chip {
  background: rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(6px);
  color: #fff;
  font-size: 13px;
  font-weight: 800;
  padding: 4px 10px;
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  letter-spacing: 0.5px;
}

/* ── Identity & Avatar Section ─────────────────────────────── */
.card-identity-section {
  display: flex;
  align-items: flex-end;
  gap: 16px;
  padding: 0 20px 14px;
  margin-top: -42px;
  position: relative;
  z-index: 3;
}

.avatar-wrapper {
  position: relative;
  width: 78px;
  height: 78px;
  border-radius: 50%;
  border: 3px solid #fff;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  flex-shrink: 0;
  background: #fff;
}

.avatar-circle {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 26px;
  font-weight: 800;
}

.avatar-image-src {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-crown-badge {
  position: absolute;
  bottom: -4px;
  right: -4px;
  background: #fff;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
}

.identity-text {
  flex: 1;
  padding-bottom: 2px;
}

.name-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.member-name {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  line-height: 1.2;
}

.role-pill {
  font-weight: 600;
  border-radius: 6px;
}

.sub-identity-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  flex-wrap: wrap;
}

.login-name-badge {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  font-family: monospace;
}

.emp-no-badge {
  font-family: monospace;
  font-size: 12px;
  background: var(--el-fill-color-light);
  color: var(--el-color-primary);
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 600;
  border: 1px solid var(--el-border-color-lighter);
}

.status-tag {
  height: 20px;
  line-height: 18px;
  padding: 0 6px;
  font-size: 11px;
}

/* ── Body Info Cards ───────────────────────────────────────── */
.card-body-content {
  padding: 8px 20px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-group-card {
  background: var(--el-fill-color-lighter);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.group-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  border-bottom: 1px solid var(--el-border-color-extra-light);
  padding-bottom: 6px;
}

.info-row {
  display: flex;
  align-items: center;
  font-size: 13px;
  line-height: 1.4;
}

.info-key {
  width: 120px;
  color: var(--el-text-color-secondary);
  font-weight: 500;
  flex-shrink: 0;
}

.info-val {
  color: var(--el-text-color-primary);
  font-weight: 500;
  word-break: break-all;
}

.highlight-dept {
  color: var(--el-color-primary);
  font-weight: 600;
}

.font-mono {
  font-family: monospace;
}

.text-muted {
  color: var(--el-text-color-placeholder) !important;
}

.supervisor-row {
  align-items: center;
}

.sup-mini-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-light);
  padding: 2px 10px 2px 4px;
  border-radius: 16px;
}

.sup-avatar-letter {
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

.sup-name-text {
  font-weight: 600;
  font-size: 12px;
  color: var(--el-text-color-primary);
}

.sup-role-tag {
  height: 18px;
  line-height: 16px;
  padding: 0 4px;
  font-size: 11px;
}

.contact-val-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
}

.dialog-footer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
