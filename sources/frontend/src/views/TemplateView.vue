<template>
  <div class="page-wrapper" v-loading="loading">
    <div class="hero-header">
      <div class="header-left">
        <div class="header-icon-ring">
          <el-icon><CopyDocument /></el-icon>
        </div>
        <div>
          <h1 class="page-title">{{ t("templates.title") }}</h1>
          <p class="page-sub">{{ t("templates.subtitle") }}</p>
        </div>
      </div>
    </div>

    <!-- Search / Filter Bar -->
    <div class="toolbar">
      <el-input
        v-model="searchQuery"
        :placeholder="t('templates.searchPlaceholder', 'Search templates...')"
        clearable
        class="search-input"
        id="template-search-input"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-tag class="count-tag" type="info" effect="plain">
        {{ filteredItems.length }} {{ t('templates.count', 'templates') }}
      </el-tag>
    </div>

    <!-- Empty state -->
    <el-empty
      v-if="filteredItems.length === 0 && !loading"
      :description="searchQuery ? t('templates.noResults', 'No matching templates') : t('templates.noTemplates', 'No templates available')"
      class="gallery-empty"
    />

    <!-- Template Cards Grid -->
    <div class="template-grid" v-if="filteredItems.length > 0">
      <div
        v-for="item in filteredItems"
        :key="item.id"
        class="template-card"
        :class="{ 'is-lowcode-card': item.is_low_code }"
        @click="useTemplate(item)"
        :id="`template-card-${item.id}`"
      >
        <!-- Card accent ribbon -->
        <div class="card-ribbon" :class="{ 'lowcode-ribbon': item.is_low_code }" />

        <div class="card-body">
          <!-- Icon & Mode Tag -->
          <div class="card-top-row">
            <div class="card-icon-wrap" :class="{ 'lowcode-icon-wrap': item.is_low_code }">
              <el-icon class="card-icon-el"><component :is="getIconComponent(item.icon)" /></el-icon>
            </div>
            <el-tag v-if="item.is_low_code" size="small" type="success" effect="light" class="lowcode-pill">
              🎨 零代码表单
            </el-tag>
          </div>

          <!-- Text -->
          <h3 class="card-title">{{ t(`templates.templateNames.${item.title}`, item.title) }}</h3>
          <p class="card-desc">{{ item.description || t('templates.noDescription', 'Standard document template') }}</p>

          <!-- Meta -->
          <div class="card-meta">
            <el-tag size="small" effect="plain" class="meta-tag">
              <el-icon style="margin-right:3px"><User /></el-icon>{{ item.owner_name }}
            </el-tag>
          </div>
        </div>

        <!-- Use CTA -->
        <div class="card-footer">
          <span class="use-btn" :class="{ 'lowcode-use-btn': item.is_low_code }">
            <el-icon><component :is="item.is_low_code ? Tickets : DocumentAdd" /></el-icon>
            {{ item.is_low_code ? t('lowcode.fillFormAction', '填写表单并生成') : t('templates.useTemplate', '使用模板') }}
          </span>
        </div>
      </div>
    </div>

    <!-- Low-Code Form Runtime Modal -->
    <LowCodeFormRuntimeDialog
      v-model="runtimeDialogVisible"
      :template-data="activeTemplate"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import api from '@/api/client';
import LowCodeFormRuntimeDialog from '@/components/LowCodeFormRuntimeDialog.vue';
import {
  CopyDocument, Search, User, DocumentAdd,
  Document, Tickets, DataAnalysis, Calendar, Money,
  Files, Folder, Memo, Postcard, Collection, Briefcase, Management,
  Monitor, PieChart, Stamp, List
} from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';

const { t } = useI18n();
const router = useRouter();
const loading = ref(false);
const items = ref<any[]>([]);
const searchQuery = ref('');

const runtimeDialogVisible = ref(false);
const activeTemplate = ref<any>(null);

const ICON_COMPONENTS: Record<string, any> = {
  Document, Tickets, Files, Folder, Memo, Postcard, Collection,
  Briefcase, Management, DataAnalysis, Monitor, Calendar,
  Money, PieChart, Stamp, List
};

function getIconComponent(name: string) {
  return ICON_COMPONENTS[name] || Document;
}

const filteredItems = computed(() => {
  const q = searchQuery.value.trim().toLowerCase();
  if (!q) return items.value;
  return items.value.filter(i =>
    i.title.toLowerCase().includes(q) ||
    (i.description || '').toLowerCase().includes(q)
  );
});

async function loadData() {
  loading.value = true;
  try {
    const { data } = await api.get('/templates');
    items.value = data.items || [];
  } catch (err) {
    ElMessage.error(t('common.failed', 'Failed to load templates'));
  } finally {
    loading.value = false;
  }
}

async function useTemplate(item: any) {
  if (item.is_low_code) {
    activeTemplate.value = item;
    runtimeDialogVisible.value = true;
    return;
  }

  loading.value = true;
  try {
    const { data } = await api.post(`/templates/${item.id}/create-from`);
    ElMessage.success(t('templates.createdSuccessfully', 'Document created from template'));
    router.push(`/doc/${data.id}`);
  } catch (err) {
    ElMessage.error(t('common.failed', 'Failed to create document'));
  } finally {
    loading.value = false;
  }
}

onMounted(loadData);
</script>

<style scoped>
.page-wrapper {
  padding: 0 0 40px;
}

.hero-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 32px 40px;
  background: linear-gradient(135deg, var(--el-color-primary) 0%, #7367f0 130%) !important;
  border-radius: 16px;
  margin-bottom: 24px;
  box-shadow: 0 8px 24px rgba(16, 185, 129, 0.15);
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

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  gap: 12px;
}

.search-input {
  width: 280px;
}

.count-tag {
  font-size: 12px;
}

.gallery-empty {
  margin-top: 60px;
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.template-card {
  background: #fff;
  border-radius: 14px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.03);
  display: flex;
  flex-direction: column;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}

.template-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 28px rgba(0,0,0,0.08);
  border-color: var(--el-color-primary);
}

.card-ribbon {
  height: 4px;
  background: linear-gradient(90deg, var(--el-color-primary), #6ee7b7);
}

.card-ribbon.lowcode-ribbon {
  background: linear-gradient(90deg, var(--el-color-primary), #6ee7b7);
}

.card-body {
  padding: 20px 20px 16px;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.card-top-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.card-icon-wrap {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: #fffbeb;
  color: var(--el-color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  transition: all 0.2s;
}

.card-icon-wrap.lowcode-icon-wrap {
  background: #fffbeb;
  color: var(--el-color-primary);
}

.template-card:hover .card-icon-wrap {
  background: var(--el-color-primary);
  color: #fff;
}

.card-title {
  margin: 0 0 8px;
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.card-desc {
  margin: 0 0 16px;
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
  flex: 1;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-footer {
  padding: 12px 20px;
  border-top: 1px solid #f1f5f9;
  background: #fafafa;
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.use-btn {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-color-primary);
  display: flex;
  align-items: center;
  gap: 4px;
  transition: all 0.2s;
}

.use-btn.lowcode-use-btn {
  color: var(--el-color-primary);
}

.template-card:hover .use-btn {
  gap: 6px;
}
</style>
