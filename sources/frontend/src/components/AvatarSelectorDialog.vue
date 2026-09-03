<template>
  <el-dialog
    v-model="visible"
    :title="t('profile.changeAvatar', '更换用户头像')"
    width="580px"
    class="avatar-selector-dialog"
    destroy-on-close
    append-to-body
  >
    <div class="avatar-dialog-body">
      <!-- Current Avatar Preview Header -->
      <div class="current-avatar-banner">
        <div class="banner-avatar-wrap">
          <div class="avatar-circle-preview" :style="{ background: userGradient }">
            <img v-if="currentPreviewUrl" :src="currentPreviewUrl" class="preview-img" alt="avatar" />
            <span v-else class="preview-initials">{{ userInitials }}</span>
          </div>
        </div>
        <div class="banner-info">
          <h4 class="user-name">{{ displayName }}</h4>
          <span class="avatar-status-hint">
            {{ currentPreviewUrl ? (isCustomAvatar ? t('profile.newAvatar', '已选择新头像（待保存）') : t('profile.currentAvatar', '当前个性化头像')) : t('profile.resetDefaultAvatar', '默认首字母徽章头像') }}
          </span>
        </div>
      </div>

      <!-- Mode Tabs -->
      <el-tabs v-model="activeTab" class="avatar-tabs">
        <!-- ── TAB 1: 本地图片上传 ──────────────────────────────────────── -->
        <el-tab-pane name="upload">
          <template #label>
            <span class="tab-label-text">
              <el-icon><Upload /></el-icon>
              <span>{{ t('profile.uploadAvatar', '本地上传') }}</span>
            </span>
          </template>

          <div class="tab-pane-content">
            <!-- Drag & Drop Zone -->
            <div 
              class="upload-dropzone" 
              :class="{ 'is-dragover': isDragOver, 'has-file': Boolean(selectedFile) }"
              @dragover.prevent="isDragOver = true"
              @dragleave.prevent="isDragOver = false"
              @drop.prevent="handleDropFile"
              @click="triggerFileInput"
            >
              <input 
                ref="fileInputRef" 
                type="file" 
                accept="image/png,image/jpeg,image/jpg,image/webp,image/gif,image/svg+xml" 
                class="hidden-file-input" 
                @change="handleFileInputChange" 
              />
              
              <div v-if="!selectedFile" class="dropzone-empty">
                <el-icon class="dropzone-icon"><PictureFilled /></el-icon>
                <div class="dropzone-title">{{ t('profile.dragOrClickAvatar', '拖拽图片至此处，或点击选择本地文件') }}</div>
                <div class="dropzone-tip">{{ t('profile.avatarUploadTip', '支持 JPG、PNG、WebP、GIF、SVG 格式图片，文件大小不超过 5MB') }}</div>
              </div>

              <div v-else class="dropzone-selected">
                <div class="selected-file-preview">
                  <img :src="localPreviewUrl" class="local-img" alt="local preview" />
                </div>
                <div class="selected-file-meta">
                  <span class="file-name">{{ selectedFile.name }}</span>
                  <span class="file-size">({{ formatFileSize(selectedFile.size) }})</span>
                  <el-button link type="primary" size="small" @click.stop="triggerFileInput">
                    {{ t('common.edit', '重新选择') }}
                  </el-button>
                </div>
              </div>
            </div>

            <!-- Previews Grid -->
            <div v-if="selectedFile || currentPreviewUrl" class="live-previews-bar">
              <span class="preview-label">效果预览：</span>
              <div class="previews-row">
                <div class="preview-item">
                  <div class="preview-circle-large">
                    <img v-if="currentPreviewUrl" :src="currentPreviewUrl" alt="circle large" />
                    <span v-else>{{ userInitials }}</span>
                  </div>
                  <span class="size-hint">96px</span>
                </div>
                <div class="preview-item">
                  <div class="preview-circle-medium">
                    <img v-if="currentPreviewUrl" :src="currentPreviewUrl" alt="circle medium" />
                    <span v-else>{{ userInitials }}</span>
                  </div>
                  <span class="size-hint">48px</span>
                </div>
                <div class="preview-item">
                  <div class="preview-circle-small">
                    <img v-if="currentPreviewUrl" :src="currentPreviewUrl" alt="circle small" />
                    <span v-else>{{ userInitials }}</span>
                  </div>
                  <span class="size-hint">32px</span>
                </div>
                <div class="preview-item">
                  <div class="preview-square-medium">
                    <img v-if="currentPreviewUrl" :src="currentPreviewUrl" alt="square medium" />
                    <span v-else>{{ userInitials }}</span>
                  </div>
                  <span class="size-hint">方形</span>
                </div>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <!-- ── TAB 2: 精选预设头像 ────────────────────────────────────── -->
        <el-tab-pane name="presets">
          <template #label>
            <span class="tab-label-text">
              <el-icon><Collection /></el-icon>
              <span>{{ t('profile.presetAvatar', '精选预设') }}</span>
            </span>
          </template>

          <div class="tab-pane-content">
            <!-- Category Filter Buttons -->
            <div class="category-filter-row">
              <el-radio-group v-model="selectedCategory" size="small">
                <el-radio-button label="all">全部 ({{ allPresets.length }})</el-radio-button>
                <el-radio-button label="business">{{ t('profile.catBusiness', '商务职场') }}</el-radio-button>
                <el-radio-button label="tech">{{ t('profile.catTech', '3D 极客') }}</el-radio-button>
                <el-radio-button label="cute">{{ t('profile.catCute', '萌趣卡通') }}</el-radio-button>
                <el-radio-button label="gradient">{{ t('profile.catGradient', '炫彩几何') }}</el-radio-button>
              </el-radio-group>
            </div>

            <!-- Presets Grid -->
            <div class="presets-grid-container">
              <div 
                v-for="(item, idx) in filteredPresets" 
                :key="idx" 
                class="preset-card-item"
                :class="{ 'is-selected': selectedPresetDataUrl === item.dataUrl || (!selectedFile && currentPreviewUrl === item.dataUrl) }"
                @click="selectPreset(item)"
              >
                <div class="preset-avatar-circle" :style="{ background: item.bg || '#f1f5f9' }">
                  <img :src="item.dataUrl" class="preset-img" :alt="item.name" />
                </div>
                <span class="preset-name">{{ item.name }}</span>
                <span v-if="selectedPresetDataUrl === item.dataUrl || (!selectedFile && currentPreviewUrl === item.dataUrl)" class="selected-badge">
                  ✓
                </span>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <!-- ── TAB 3: 恢复默认首字母 ──────────────────────────────────── -->
        <el-tab-pane name="default">
          <template #label>
            <span class="tab-label-text">
              <el-icon><RefreshRight /></el-icon>
              <span>{{ t('profile.resetDefaultAvatar', '恢复默认') }}</span>
            </span>
          </template>

          <div class="tab-pane-content reset-tab-content">
            <div class="default-initials-preview-box">
              <div class="avatar-circle-preview large" :style="{ background: userGradient }">
                <span class="preview-initials">{{ userInitials }}</span>
              </div>
              <div class="default-desc-wrap">
                <h4>{{ t('profile.resetDefaultAvatar', '恢复系统默认首字母徽章') }}</h4>
                <p>根据您的角色职级和姓名智能生成专属渐变色徽章头像，清空已设置的自定义图片。</p>
              </div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <template #footer>
      <div class="dialog-footer-wrap">
        <el-button @click="visible = false">{{ t('common.cancel', '取消') }}</el-button>
        <el-button 
          type="primary" 
          :loading="saving" 
          :disabled="!isSaveAllowed"
          @click="handleSaveAvatar"
        >
          {{ t('common.save', '保存头像') }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import api from "@/api/client";
import { useAuthStore } from "@/stores/auth";
import { ElMessage } from "element-plus";
import { Upload, PictureFilled, Collection, RefreshRight } from "@element-plus/icons-vue";

const { t, locale } = useI18n();
const authStore = useAuthStore();

const props = withDefaults(
  defineProps<{
    modelValue: boolean;
    user?: any;
  }>(),
  {
    modelValue: false,
    user: null
  }
);

const emit = defineEmits<{
  (e: "update:modelValue", val: boolean): void;
  (e: "success", avatarUrl: string): void;
}>();

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit("update:modelValue", val)
});

const currentUserData = computed(() => {
  return props.user || authStore.user || {};
});

const activeTab = ref<"upload" | "presets" | "default">("upload");
const fileInputRef = ref<HTMLInputElement | null>(null);
const selectedFile = ref<File | null>(null);
const localPreviewUrl = ref<string>("");
const isDragOver = ref(false);
const selectedPresetDataUrl = ref<string>("");
const resetToDefault = ref(false);
const saving = ref(false);

const selectedCategory = ref<string>("all");

// ── Watch modelValue to reset transient state ──────────────────────────────────────────
watch(
  () => props.modelValue,
  (val) => {
    if (val) {
      selectedFile.value = null;
      localPreviewUrl.value = "";
      selectedPresetDataUrl.value = "";
      resetToDefault.value = false;
      activeTab.value = "upload";
    }
  }
);

const displayName = computed(() => {
  const u = currentUserData.value;
  if (!u) return "";
  if (locale.value === 'zh-CN') {
    if (u.display_name) return u.display_name;
    const zh = `${u.last_name || ''}${u.first_name || ''}`.trim();
    return zh || u.login_name || "";
  }
  return u.display_name || `${u.first_name || ''} ${u.last_name || ''}`.trim() || u.login_name || "";
});

const userInitials = computed(() => {
  const u = currentUserData.value;
  if (!u) return "U";
  if (u.display_name) return u.display_name.slice(0, 2).toUpperCase();
  if (u.first_name || u.last_name) {
    return `${u.last_name || ''}${u.first_name || ''}`.slice(0, 2).toUpperCase();
  }
  return u.login_name ? u.login_name.slice(0, 2).toUpperCase() : "U";
});

const userGradient = computed(() => {
  const u = currentUserData.value;
  const lvl = u?.role_level ?? (u?.is_super_admin ? 100 : (u?.is_manager ? 50 : 10));
  if (lvl >= 100 || u?.is_super_admin) {
    return "linear-gradient(135deg, #409eff 0%, #7367f0 100%)";
  }
  if (lvl >= 50 || u?.is_manager) {
    return "linear-gradient(135deg, #10b981 0%, #059669 100%)";
  }
  return "linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)";
});

const currentPreviewUrl = computed(() => {
  if (resetToDefault.value || activeTab.value === 'default') {
    return "";
  }
  if (selectedFile.value && localPreviewUrl.value) {
    return localPreviewUrl.value;
  }
  if (selectedPresetDataUrl.value) {
    return selectedPresetDataUrl.value;
  }
  return currentUserData.value?.avatar_url || "";
});

const isCustomAvatar = computed(() => {
  return Boolean(selectedFile.value || selectedPresetDataUrl.value);
});

const isSaveAllowed = computed(() => {
  if (activeTab.value === 'default') return true;
  if (activeTab.value === 'upload') return Boolean(selectedFile.value);
  if (activeTab.value === 'presets') return Boolean(selectedPresetDataUrl.value);
  return false;
});

// ── Upload Methods ──────────────────────────────────────────────────────────
function triggerFileInput() {
  fileInputRef.value?.click();
}

function handleFileInputChange(e: Event) {
  const target = e.target as HTMLInputElement;
  if (target.files && target.files[0]) {
    setFile(target.files[0]);
  }
}

function handleDropFile(e: DragEvent) {
  isDragOver.value = false;
  if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) {
    setFile(e.dataTransfer.files[0]);
  }
}

function setFile(file: File) {
  const allowed = ["image/jpeg", "image/png", "image/webp", "image/gif", "image/svg+xml"];
  if (!allowed.includes(file.type)) {
    return ElMessage.warning(t('profile.avatarUploadTip', "请选择 JPG, PNG, WebP, GIF 或 SVG 图片！"));
  }
  if (file.size > 5 * 1024 * 1024) {
    return ElMessage.warning("图片大小不能超过 5MB！");
  }
  selectedFile.value = file;
  selectedPresetDataUrl.value = "";
  resetToDefault.value = false;

  const reader = new FileReader();
  reader.onload = (event) => {
    localPreviewUrl.value = event.target?.result as string;
  };
  reader.readAsDataURL(file);
}

function formatFileSize(bytes: number) {
  if (!bytes) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

// ── Preset Avatars Library (Inline High-Quality Vector SVG Data-URLs) ────────
function createSvgDataUrl(svgString: string): string {
  return `data:image/svg+xml;utf8,${encodeURIComponent(svgString)}`;
}

const allPresets = [
  // ── 1. 商务职场 ───────────────────────────────────────────────────────────
  {
    name: "Executive Blue",
    category: "business",
    bg: "linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)",
    dataUrl: createSvgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="50" fill="#2563eb"/>
        <circle cx="50" cy="36" r="18" fill="#ffffff"/>
        <path d="M22 84 C22 64, 34 56, 50 56 C66 56, 78 64, 78 84 Z" fill="#ffffff"/>
        <polygon points="50,56 46,74 50,84 54,74" fill="#1e40af"/>
      </svg>
    `)
  },
  {
    name: "Director Gold",
    category: "business",
    bg: "linear-gradient(135deg, #78350f 0%, #d97706 100%)",
    dataUrl: createSvgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="50" fill="#d97706"/>
        <circle cx="50" cy="36" r="18" fill="#fef3c7"/>
        <path d="M22 84 C22 64, 34 56, 50 56 C66 56, 78 64, 78 84 Z" fill="#fef3c7"/>
        <polygon points="50,56 46,74 50,84 54,74" fill="#92400e"/>
      </svg>
    `)
  },
  {
    name: "Manager Emerald",
    category: "business",
    bg: "linear-gradient(135deg, #064e3b 0%, #10b981 100%)",
    dataUrl: createSvgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="50" fill="#059669"/>
        <circle cx="50" cy="36" r="18" fill="#ecfdf5"/>
        <path d="M22 84 C22 64, 34 56, 50 56 C66 56, 78 64, 78 84 Z" fill="#ecfdf5"/>
        <polygon points="50,56 46,74 50,84 54,74" fill="#065f46"/>
      </svg>
    `)
  },
  {
    name: "Professional Slate",
    category: "business",
    bg: "linear-gradient(135deg, #0f172a 0%, #475569 100%)",
    dataUrl: createSvgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="50" fill="#334155"/>
        <circle cx="50" cy="36" r="18" fill="#f8fafc"/>
        <path d="M22 84 C22 64, 34 56, 50 56 C66 56, 78 64, 78 84 Z" fill="#f8fafc"/>
        <polygon points="50,56 46,74 50,84 54,74" fill="#0f172a"/>
      </svg>
    `)
  },

  // ── 2. 3D 极客 ────────────────────────────────────────────────────────────
  {
    name: "Cyber Bot",
    category: "tech",
    bg: "linear-gradient(135deg, #312e81 0%, #4f46e5 100%)",
    dataUrl: createSvgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="50" fill="#4338ca"/>
        <rect x="26" y="30" width="48" height="38" rx="10" fill="#e0e7ff"/>
        <circle cx="38" cy="46" r="5" fill="#4f46e5"/>
        <circle cx="62" cy="46" r="5" fill="#4f46e5"/>
        <rect x="38" y="56" width="24" height="4" rx="2" fill="#4f46e5"/>
        <line x1="50" y1="20" x2="50" y2="30" stroke="#e0e7ff" stroke-width="4"/>
        <circle cx="50" cy="18" r="4" fill="#38bdf8"/>
      </svg>
    `)
  },
  {
    name: "Matrix Neon",
    category: "tech",
    bg: "linear-gradient(135deg, #022c22 0%, #065f46 100%)",
    dataUrl: createSvgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="50" fill="#0f172a"/>
        <circle cx="50" cy="50" r="42" fill="none" stroke="#22c55e" stroke-width="3" stroke-dasharray="8 4"/>
        <polygon points="50,26 72,66 28,66" fill="none" stroke="#4ade80" stroke-width="4"/>
        <circle cx="50" cy="52" r="8" fill="#22c55e"/>
      </svg>
    `)
  },
  {
    name: "AI Core",
    category: "tech",
    bg: "linear-gradient(135deg, #581c87 0%, #a855f7 100%)",
    dataUrl: createSvgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="50" fill="#7e22ce"/>
        <circle cx="50" cy="50" r="24" fill="#f3e8ff"/>
        <circle cx="50" cy="50" r="16" fill="#a855f7"/>
        <circle cx="50" cy="50" r="8" fill="#ffffff"/>
        <line x1="50" y1="12" x2="50" y2="26" stroke="#f3e8ff" stroke-width="3"/>
        <line x1="50" y1="74" x2="50" y2="88" stroke="#f3e8ff" stroke-width="3"/>
        <line x1="12" y1="50" x2="26" y2="50" stroke="#f3e8ff" stroke-width="3"/>
        <line x1="74" y1="50" x2="88" y2="50" stroke="#f3e8ff" stroke-width="3"/>
      </svg>
    `)
  },
  {
    name: "Quantum Shield",
    category: "tech",
    bg: "linear-gradient(135deg, #1e1b4b 0%, #3730a3 100%)",
    dataUrl: createSvgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="50" fill="#1e1b4b"/>
        <path d="M50 20 L76 34 L76 62 C76 76, 50 86, 50 86 C50 86, 24 76, 24 62 L24 34 Z" fill="#6366f1"/>
        <path d="M50 28 L68 40 L68 60 C68 70, 50 78, 50 78 C50 78, 32 70, 32 60 L32 40 Z" fill="#ffffff"/>
        <circle cx="50" cy="54" r="8" fill="#4f46e5"/>
      </svg>
    `)
  },

  // ── 3. 萌趣卡通 ───────────────────────────────────────────────────────────
  {
    name: "Lucky Cat",
    category: "cute",
    bg: "linear-gradient(135deg, #fff1f2 0%, #ffe4e6 100%)",
    dataUrl: createSvgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="50" fill="#f43f5e"/>
        <!-- Ears -->
        <polygon points="26,40 32,20 48,34" fill="#ffe4e6"/>
        <polygon points="74,40 68,20 52,34" fill="#ffe4e6"/>
        <!-- Head -->
        <circle cx="50" cy="54" r="26" fill="#ffffff"/>
        <!-- Eyes -->
        <circle cx="40" cy="50" r="3.5" fill="#1e293b"/>
        <circle cx="60" cy="50" r="3.5" fill="#1e293b"/>
        <!-- Nose & Mouth -->
        <polygon points="50,56 47,54 53,54" fill="#f43f5e"/>
        <path d="M46 60 Q50 64 54 60" fill="none" stroke="#1e293b" stroke-width="2"/>
        <!-- Cheeks -->
        <circle cx="34" cy="56" r="4" fill="#fca5a5" opacity="0.6"/>
        <circle cx="66" cy="56" r="4" fill="#fca5a5" opacity="0.6"/>
      </svg>
    `)
  },
  {
    name: "Smart Owl",
    category: "cute",
    bg: "linear-gradient(135deg, #fefce8 0%, #fef08a 100%)",
    dataUrl: createSvgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="50" fill="#eab308"/>
        <!-- Owl Body -->
        <circle cx="50" cy="54" r="28" fill="#ffffff"/>
        <!-- Eyes Circles -->
        <circle cx="39" cy="48" r="10" fill="#fef08a"/>
        <circle cx="61" cy="48" r="10" fill="#fef08a"/>
        <circle cx="39" cy="48" r="5" fill="#713f12"/>
        <circle cx="61" cy="48" r="5" fill="#713f12"/>
        <!-- Beak -->
        <polygon points="50,54 46,60 54,60" fill="#ca8a04"/>
      </svg>
    `)
  },
  {
    name: "Happy Shiba",
    category: "cute",
    bg: "linear-gradient(135deg, #ffedd5 0%, #fed7aa 100%)",
    dataUrl: createSvgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="50" fill="#f97316"/>
        <!-- Ears -->
        <polygon points="26,38 34,16 48,32" fill="#f97316"/>
        <polygon points="74,38 66,16 52,32" fill="#f97316"/>
        <polygon points="30,36 34,22 44,32" fill="#ffffff"/>
        <polygon points="70,36 66,22 56,32" fill="#ffffff"/>
        <!-- Face -->
        <circle cx="50" cy="54" r="26" fill="#fb923c"/>
        <path d="M34 58 C34 72, 66 72, 66 58 Z" fill="#ffffff"/>
        <!-- Eyes -->
        <circle cx="38" cy="48" r="3.5" fill="#1e293b"/>
        <circle cx="62" cy="48" r="3.5" fill="#1e293b"/>
        <!-- Nose -->
        <circle cx="50" cy="58" r="4" fill="#1e293b"/>
      </svg>
    `)
  },
  {
    name: "Cozy Bear",
    category: "cute",
    bg: "linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)",
    dataUrl: createSvgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="50" fill="#14b8a6"/>
        <circle cx="30" cy="30" r="10" fill="#0d9488"/>
        <circle cx="70" cy="30" r="10" fill="#0d9488"/>
        <circle cx="50" cy="54" r="26" fill="#ffffff"/>
        <circle cx="40" cy="48" r="3.5" fill="#134e4a"/>
        <circle cx="60" cy="48" r="3.5" fill="#134e4a"/>
        <ellipse cx="50" cy="60" rx="9" ry="7" fill="#ccfbf1"/>
        <circle cx="50" cy="57" r="3.5" fill="#134e4a"/>
      </svg>
    `)
  },

  // ── 4. 炫彩几何 ───────────────────────────────────────────────────────────
  {
    name: "Aurora Waves",
    category: "gradient",
    bg: "linear-gradient(135deg, #ec4899 0%, #8b5cf6 50%, #3b82f6 100%)",
    dataUrl: createSvgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <defs>
          <linearGradient id="g1" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#ec4899"/>
            <stop offset="50%" stop-color="#8b5cf6"/>
            <stop offset="100%" stop-color="#3b82f6"/>
          </linearGradient>
        </defs>
        <circle cx="50" cy="50" r="50" fill="url(#g1)"/>
        <circle cx="50" cy="50" r="24" fill="none" stroke="#ffffff" stroke-width="4" opacity="0.8"/>
        <circle cx="50" cy="50" r="12" fill="#ffffff"/>
      </svg>
    `)
  },
  {
    name: "Sunset Hex",
    category: "gradient",
    bg: "linear-gradient(135deg, #f43f5e 0%, #fb923c 100%)",
    dataUrl: createSvgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <defs>
          <linearGradient id="g2" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#f43f5e"/>
            <stop offset="100%" stop-color="#fb923c"/>
          </linearGradient>
        </defs>
        <circle cx="50" cy="50" r="50" fill="url(#g2)"/>
        <polygon points="50,22 74,36 74,64 50,78 26,64 26,36" fill="none" stroke="#ffffff" stroke-width="4"/>
        <polygon points="50,34 62,42 62,58 50,66 38,58 38,42" fill="#ffffff" opacity="0.9"/>
      </svg>
    `)
  },
  {
    name: "Emerald Prism",
    category: "gradient",
    bg: "linear-gradient(135deg, #10b981 0%, #06b6d4 100%)",
    dataUrl: createSvgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <defs>
          <linearGradient id="g3" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#10b981"/>
            <stop offset="100%" stop-color="#06b6d4"/>
          </linearGradient>
        </defs>
        <circle cx="50" cy="50" r="50" fill="url(#g3)"/>
        <rect x="30" y="30" width="40" height="40" rx="8" transform="rotate(45 50 50)" fill="none" stroke="#ffffff" stroke-width="4"/>
        <circle cx="50" cy="50" r="8" fill="#ffffff"/>
      </svg>
    `)
  },
  {
    name: "Galaxy Orbit",
    category: "gradient",
    bg: "linear-gradient(135deg, #1e1b4b 0%, #4338ca 100%)",
    dataUrl: createSvgDataUrl(`
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <defs>
          <linearGradient id="g4" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#312e81"/>
            <stop offset="100%" stop-color="#6366f1"/>
          </linearGradient>
        </defs>
        <circle cx="50" cy="50" r="50" fill="url(#g4)"/>
        <ellipse cx="50" cy="50" rx="34" ry="12" fill="none" stroke="#a5b4fc" stroke-width="3" transform="rotate(-30 50 50)"/>
        <circle cx="50" cy="50" r="14" fill="#ffffff"/>
      </svg>
    `)
  }
];

const filteredPresets = computed(() => {
  if (selectedCategory.value === 'all') return allPresets;
  return allPresets.filter(p => p.category === selectedCategory.value);
});

function selectPreset(preset: any) {
  selectedPresetDataUrl.value = preset.dataUrl;
  selectedFile.value = null;
  resetToDefault.value = false;
}

// ── Save Avatar Handler ─────────────────────────────────────────────────────
async function handleSaveAvatar() {
  const targetUserId = currentUserData.value?.id;
  if (!targetUserId) {
    return ElMessage.error("未找到目标用户信息");
  }

  saving.value = true;
  try {
    let finalAvatarUrl = "";

    if (activeTab.value === 'default') {
      // 1. Reset to default
      await api.patch(`/users/${targetUserId}`, { avatar_url: "" });
      finalAvatarUrl = "";
      ElMessage.success(t('profile.avatarResetSuccess', "已恢复为默认首字母头像"));
    } else if (activeTab.value === 'upload' && selectedFile.value) {
      // 2. Upload file
      const formData = new FormData();
      formData.append("file", selectedFile.value);
      const isSelf = targetUserId === authStore.user?.id;
      const endpoint = isSelf ? "/users/avatar" : `/users/${targetUserId}/avatar`;
      const { data } = await api.post(endpoint, formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      finalAvatarUrl = data.avatar_url;
      ElMessage.success(t('profile.avatarUploadSuccess', "头像已成功更新！"));
    } else if (activeTab.value === 'presets' && selectedPresetDataUrl.value) {
      // 3. Preset avatar
      await api.patch(`/users/${targetUserId}`, { avatar_url: selectedPresetDataUrl.value });
      finalAvatarUrl = selectedPresetDataUrl.value;
      ElMessage.success(t('profile.avatarUploadSuccess', "头像已成功更新！"));
    }

    // Sync to auth store if modifying current logged in user
    if (authStore.user && authStore.user.id === targetUserId) {
      authStore.user = {
        ...authStore.user,
        avatar_url: finalAvatarUrl
      };
    }

    emit("success", finalAvatarUrl);
    visible.value = false;
  } catch (err: any) {
    console.error("Save avatar error:", err);
    ElMessage.error(err.response?.data?.error || t('profile.avatarUploadFailed', "头像保存失败"));
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped>
.avatar-selector-dialog :deep(.el-dialog__body) {
  padding: 0;
  max-height: 520px;
  overflow-y: auto;
}

.avatar-dialog-body {
  padding: 16px 20px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ── Current Avatar Banner ─────────────────────────────────── */
.current-avatar-banner {
  display: flex;
  align-items: center;
  gap: 16px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  padding: 12px 16px;
}

.banner-avatar-wrap {
  width: 54px;
  height: 54px;
  flex-shrink: 0;
}

.avatar-circle-preview {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
  border: 2px solid #ffffff;
}

.avatar-circle-preview.large {
  width: 88px;
  height: 88px;
}

.preview-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.preview-initials {
  color: #ffffff;
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 0.5px;
}

.avatar-circle-preview.large .preview-initials {
  font-size: 32px;
}

.banner-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.user-name {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.avatar-status-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

/* ── Tab Styling ───────────────────────────────────────────── */
.avatar-tabs {
  margin-top: 4px;
}

.tab-label-text {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
}

.tab-pane-content {
  padding: 12px 0 6px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ── Dropzone ──────────────────────────────────────────────── */
.upload-dropzone {
  border: 2px dashed var(--el-border-color);
  border-radius: 12px;
  background: var(--el-fill-color-blank);
  padding: 28px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.25s ease;
  position: relative;
}

.upload-dropzone:hover,
.upload-dropzone.is-dragover {
  border-color: var(--el-color-primary);
  background: rgba(64, 158, 255, 0.04);
}

.upload-dropzone.has-file {
  border-style: solid;
  border-color: var(--el-color-primary-light-5);
  background: var(--el-fill-color-light);
  padding: 16px 20px;
}

.hidden-file-input {
  display: none;
}

.dropzone-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.dropzone-icon {
  font-size: 40px;
  color: var(--el-color-primary);
  opacity: 0.85;
}

.dropzone-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.dropzone-tip {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

.dropzone-selected {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

.selected-file-preview {
  width: 58px;
  height: 58px;
  border-radius: 50%;
  overflow: hidden;
  border: 2px solid var(--el-color-primary);
  flex-shrink: 0;
}

.local-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.selected-file-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.file-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

/* ── Live Previews Bar ─────────────────────────────────────── */
.live-previews-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  background: var(--el-fill-color-light);
  padding: 12px 16px;
  border-radius: 10px;
  border: 1px solid var(--el-border-color-lighter);
}

.preview-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-secondary);
  flex-shrink: 0;
}

.previews-row {
  display: flex;
  align-items: flex-end;
  gap: 16px;
}

.preview-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.size-hint {
  font-size: 10px;
  color: var(--el-text-color-placeholder);
}

.preview-circle-large {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  overflow: hidden;
  border: 1.5px solid var(--el-border-color);
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-circle-large img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.preview-circle-medium {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  overflow: hidden;
  border: 1.5px solid var(--el-border-color);
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-circle-medium img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.preview-circle-small {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  overflow: hidden;
  border: 1px solid var(--el-border-color);
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-circle-small img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.preview-square-medium {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  overflow: hidden;
  border: 1.5px solid var(--el-border-color);
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-square-medium img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* ── Presets Grid ──────────────────────────────────────────── */
.category-filter-row {
  margin-bottom: 8px;
}

.presets-grid-container {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  max-height: 280px;
  overflow-y: auto;
  padding: 4px;
}

.preset-card-item {
  position: relative;
  border: 2px solid var(--el-border-color-lighter);
  background: var(--el-bg-color);
  border-radius: 12px;
  padding: 10px 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.preset-card-item:hover {
  transform: translateY(-2px);
  border-color: var(--el-color-primary-light-3);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.15);
}

.preset-card-item.is-selected {
  border-color: var(--el-color-primary);
  background: rgba(64, 158, 255, 0.05);
}

.preset-avatar-circle {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
}

.preset-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.preset-name {
  font-size: 11px;
  font-weight: 600;
  color: var(--el-text-color-regular);
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  width: 100%;
}

.selected-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  width: 20px;
  height: 20px;
  background: var(--el-color-primary);
  color: #ffffff;
  border-radius: 50%;
  font-size: 11px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

/* ── Reset Tab ─────────────────────────────────────────────── */
.reset-tab-content {
  padding: 20px 0;
}

.default-initials-preview-box {
  display: flex;
  align-items: center;
  gap: 20px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  padding: 20px 24px;
}

.default-desc-wrap h4 {
  margin: 0 0 6px;
  font-size: 15px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.default-desc-wrap p {
  margin: 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
}

.dialog-footer-wrap {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
