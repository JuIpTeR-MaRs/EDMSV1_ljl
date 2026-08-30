<template>
  <div class="admin-tmpl-page" v-loading="loading">
    <!-- Page Header -->
    <div class="hero-header">
      <div class="header-left">
        <div class="header-icon-ring">
          <el-icon><Grid /></el-icon>
        </div>
        <div>
          <h1 class="page-title">{{ t('templates.adminTitle', 'Template Management') }}</h1>
          <p class="page-sub">{{ t('templates.adminSubtitle', 'Create, edit, and publish templates for all employees.') }}</p>
        </div>
      </div>
      <div class="header-actions-group">
        <el-button type="primary" class="hero-action-btn" :icon="Plus" @click="openCreate" id="create-template-btn" size="large">
          {{ t('templates.create', 'New Template') }}
        </el-button>
      </div>
    </div>

    <!-- Stats Strip -->
    <div class="stats-strip">
      <div class="stat-card">
        <span class="stat-num">{{ auth.user?.is_super_admin ? items.length : ownItems.length }}</span>
        <span class="stat-label">{{ auth.user?.is_super_admin ? t('templates.statTotal', 'Total Templates') : t('personal.createdDocs', 'My Templates') }}</span>
      </div>
      <div class="stat-card published">
        <span class="stat-num">{{ publishedCount }}</span>
        <span class="stat-label">{{ t('templates.statPublished', 'Published') }}</span>
      </div>
      <div class="stat-card draft">
        <span class="stat-num">{{ draftCount }}</span>
        <span class="stat-label">{{ t('templates.statDraft', 'Draft') }}</span>
      </div>
    </div>

    <!-- Templates Table -->
    <div class="table-card">
      <div class="table-toolbar">
        <el-input
          v-model="search"
          :placeholder="t('templates.searchPlaceholder', 'Search templates...')"
          clearable
          class="table-search"
          id="admin-template-search"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-radio-group v-model="filterStatus" size="small">
          <el-radio-button value="all">{{ t('common.ok', 'All') }}</el-radio-button>
          <el-radio-button value="published">{{ t('templates.statPublished', 'Published') }}</el-radio-button>
          <el-radio-button value="draft">{{ t('templates.statDraft', 'Draft') }}</el-radio-button>
        </el-radio-group>
      </div>

      <el-table
        :data="filteredItems"
        border
        stripe
        class="tmpl-table"
        empty-text="No templates found"
        id="admin-template-table"
      >
        <el-table-column prop="title" :label="t('templates.colTitle', 'Title')" min-width="180">
          <template #default="{ row }">
            <div class="title-cell">
              <el-icon class="title-icon"><component :is="getIconComponent(row.icon)" /></el-icon>
              <span>{{ row.title }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column :label="t('lowcode.tmplType', '模板模式')" width="170" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_low_code" type="success" effect="light" size="small" class="type-tag">
              🎨 零代码表单 ({{ row.fields_count || 0 }}项)
            </el-tag>
            <el-tag v-else type="info" effect="plain" size="small" class="type-tag">
              📝 标准富文本
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="description" :label="t('templates.colDesc', 'Description')" min-width="220">
          <template #default="{ row }">
            <span class="desc-text">{{ row.description || '—' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="owner_name" :label="t('templates.colOwner', 'Author')" width="130" />

        <el-table-column prop="updated_at" :label="t('templates.colUpdated', 'Last Updated')" width="160">
          <template #default="{ row }">
            <span class="date-text">{{ formatDate(row.updated_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column :label="t('templates.colStatus', 'Status')" width="110" align="center">
          <template #default="{ row }">
            <el-tag
              :type="row.is_public ? 'success' : 'warning'"
              effect="dark"
              size="small"
              class="status-tag"
            >
              {{ row.is_public ? t('templates.statusPublished', 'Published') : t('templates.statusDraft', 'Draft') }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column :label="t('common.actions', 'Actions')" width="260" align="center" fixed="right">
          <template #default="{ row }">
            <div class="action-btns" v-if="canManage(row)">
              <!-- Low-Code Visual Designer (Only for low-code templates) -->
              <el-tooltip v-if="row.is_low_code" :content="t('lowcode.designForm', '🎨 零代码表单设计器')" placement="top">
                <el-button
                  size="small"
                  type="success"
                  :icon="MagicStick"
                  circle
                  @click="openDesigner(row)"
                  :id="`tmpl-design-${row.id}`"
                />
              </el-tooltip>
              <!-- Edit in rich editor (Only for standard rich-text templates) -->
              <el-tooltip v-else :content="t('templates.editContent', 'Edit Content in Editor')" placement="top">
                <el-button
                  size="small"
                  type="primary"
                  :icon="Edit"
                  circle
                  @click="openInEditor(row)"
                  :id="`tmpl-edit-${row.id}`"
                />
              </el-tooltip>
              <!-- Edit meta -->
              <el-tooltip :content="t('templates.editMeta', 'Edit Info')" placement="top">
                <el-button
                  size="small"
                  :icon="EditPen"
                  circle
                  @click="openEdit(row)"
                  :id="`tmpl-meta-${row.id}`"
                />
              </el-tooltip>
              <!-- Publish / Unpublish -->
              <el-tooltip :content="row.is_public ? t('templates.unpublish', 'Unpublish') : t('templates.publish', 'Publish')" placement="top">
                <el-button
                  size="small"
                  :type="row.is_public ? 'warning' : 'success'"
                  :icon="row.is_public ? Hide : View"
                  circle
                  @click="togglePublish(row)"
                  :id="`tmpl-pub-${row.id}`"
                />
              </el-tooltip>
              <!-- Delete -->
              <el-tooltip :content="t('common.delete', 'Delete')" placement="top">
                <el-popconfirm
                  :title="t('templates.deleteConfirm', 'Permanently delete this template?')"
                  @confirm="deleteTemplate(row)"
                  :confirm-button-text="t('common.ok', 'OK')"
                  :cancel-button-text="t('common.cancel', 'Cancel')"
                >
                  <template #reference>
                    <el-button
                      size="small"
                      type="danger"
                      :icon="Delete"
                      circle
                      :id="`tmpl-del-${row.id}`"
                    />
                  </template>
                </el-popconfirm>
              </el-tooltip>
            </div>

            <!-- Read-only state for templates created by other users (e.g. Admin) -->
            <div class="action-btns" v-else>
              <el-tooltip v-if="row.is_low_code" content="👀 表单填报预览与试用" placement="top">
                <el-button
                  size="small"
                  type="primary"
                  plain
                  :icon="View"
                  @click="openRuntimePreview(row)"
                >
                  预览
                </el-button>
              </el-tooltip>
              <el-tooltip v-else content="👀 查看模板内容" placement="top">
                <el-button
                  size="small"
                  type="info"
                  plain
                  :icon="View"
                  @click="openInEditor(row)"
                >
                  查看
                </el-button>
              </el-tooltip>
              <el-tag type="info" size="small" effect="plain" style="font-size: 11px; margin-left: 2px;">
                🔒 仅创建者可管理
              </el-tag>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Create / Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="editMode === 'create' ? t('templates.create', 'New Template') : t('templates.editMeta', 'Edit Template Info')"
      width="520px"
      destroy-on-close
      id="template-form-dialog"
    >
      <el-form :model="form" label-position="top" ref="formRef" :rules="rules">
        <el-form-item :label="t('templates.colTitle', 'Title')" prop="title">
          <el-input v-model="form.title" :placeholder="t('templates.titlePlaceholder', 'e.g. Meeting Minutes')" maxlength="512" show-word-limit />
        </el-form-item>
        <el-form-item :label="t('templates.colDesc', 'Description')" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            :placeholder="t('templates.descPlaceholder', 'Short description shown in the gallery...')"
            maxlength="512"
            show-word-limit
          />
        </el-form-item>
        <el-form-item :label="t('templates.colIcon', 'Template Icon')">
          <div class="icon-picker">
            <div
              v-for="item in availableIcons"
              :key="item.name"
              class="icon-item"
              :class="{ active: form.icon === item.name }"
              @click="form.icon = item.name"
            >
              <el-icon><component :is="item.icon" /></el-icon>
            </div>
          </div>
        </el-form-item>
        <el-form-item :label="t('lowcode.tmplMode', '模板类型')" v-if="editMode === 'create'">
          <el-radio-group v-model="form.tmplType">
            <el-radio-button value="lowcode">🎨 零代码表单 (拖拽组件/智能数据源/审批流)</el-radio-button>
            <el-radio-button value="rich">📝 传统富文本 (自由排版/文档编辑)</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="t('templates.colStatus', 'Status')">
          <el-switch
            v-model="form.is_public"
            :active-text="t('templates.statusPublished', 'Published')"
            :inactive-text="t('templates.statusDraft', 'Draft')"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">{{ t('common.cancel', 'Cancel') }}</el-button>
          <el-button type="primary" :loading="saving" @click="submitForm" id="save-template-btn">
            {{ editMode === 'create' ? t('templates.createAndDesign', '创建并进入设计器') : t('common.save', 'Save') }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- Low-Code Visual Designer Fullscreen Modal -->
    <LowCodeFormDesigner
      v-model="designerVisible"
      :template-data="currentDesignerTemplate"
      @saved="loadData"
    />

    <!-- Low-Code Form Runtime Modal (For Previewing) -->
    <LowCodeFormRuntimeDialog
      v-model="runtimeDialogVisible"
      :template-data="activePreviewTemplate"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import api from '@/api/client';
import { useAuthStore } from '@/stores/auth';
import { ElMessage } from 'element-plus';
import LowCodeFormDesigner from '@/components/LowCodeFormDesigner.vue';
import LowCodeFormRuntimeDialog from '@/components/LowCodeFormRuntimeDialog.vue';
import {
  Plus, Edit, EditPen, Delete, Search, MagicStick,
  Document, View, Hide, Grid,
  Tickets, Files, Folder, Memo, Postcard, Collection,
  Briefcase, Management, DataAnalysis, Monitor, Calendar,
  Money, PieChart, Stamp, List
} from '@element-plus/icons-vue';

const { t } = useI18n();
const router = useRouter();
const auth = useAuthStore();
const loading = ref(false);
const saving = ref(false);
const items = ref<any[]>([]);
const search = ref('');
const filterStatus = ref<'all' | 'published' | 'draft'>('all');
const dialogVisible = ref(false);
const editMode = ref<'create' | 'edit'>('create');
const editingId = ref<number | null>(null);
const formRef = ref<any>(null);

const designerVisible = ref(false);
const currentDesignerTemplate = ref<any>(null);

const runtimeDialogVisible = ref(false);
const activePreviewTemplate = ref<any>(null);

function openRuntimePreview(row: any) {
  activePreviewTemplate.value = row;
  runtimeDialogVisible.value = true;
}

const form = reactive({ 
  title: '', 
  description: '', 
  is_public: false, 
  icon: 'Tickets',
  tmplType: 'lowcode' 
});

const availableIcons = [
  { name: 'Tickets', icon: Tickets },
  { name: 'Document', icon: Document },
  { name: 'Money', icon: Money },
  { name: 'Calendar', icon: Calendar },
  { name: 'Files', icon: Files },
  { name: 'Folder', icon: Folder },
  { name: 'Memo', icon: Memo },
  { name: 'Postcard', icon: Postcard },
  { name: 'Collection', icon: Collection },
  { name: 'Briefcase', icon: Briefcase },
  { name: 'Management', icon: Management },
  { name: 'DataAnalysis', icon: DataAnalysis },
  { name: 'Monitor', icon: Monitor },
  { name: 'PieChart', icon: PieChart },
  { name: 'Stamp', icon: Stamp },
  { name: 'List', icon: List }
];

function getIconComponent(name: string) {
  const found = availableIcons.find(i => i.name === name);
  return found ? found.icon : Tickets;
}

const rules = {
  title: [{ required: true, message: t('common.requiredFields', 'Required'), trigger: 'blur' }]
};

const ownItems = computed(() => items.value.filter(i => i.owner_id === auth.user?.id));
const publishedCount = computed(() => ownItems.value.filter(i => i.is_public).length);
const draftCount = computed(() => ownItems.value.filter(i => !i.is_public).length);

const filteredItems = computed(() => {
  let list = items.value;
  if (filterStatus.value === 'published') list = list.filter(i => i.is_public);
  if (filterStatus.value === 'draft') list = list.filter(i => !i.is_public);
  const q = search.value.trim().toLowerCase();
  if (q) list = list.filter(i => i.title.toLowerCase().includes(q) || (i.description || '').toLowerCase().includes(q));
  return list;
});

const canManage = (row: any) => {
  if (!auth.user || !row) return false;
  // 超级管理员（L100）具备全公司所有模板的管理权限
  if (auth.user.is_super_admin || (auth.user.role_level && auth.user.role_level >= 100)) {
    return true;
  }
  // 其余成员（包含部门主管）仅能编辑和管理自己创建的模板
  return row.owner_id === auth.user.id;
};

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleString();
}

async function loadData() {
  loading.value = true;
  try {
    const { data } = await api.get('/templates/admin');
    items.value = data.items || [];
  } catch {
    ElMessage.error(t('common.failed', 'Failed to load'));
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editMode.value = 'create';
  editingId.value = null;
  Object.assign(form, { title: '', description: '', is_public: false, icon: 'Tickets', tmplType: 'lowcode' });
  dialogVisible.value = true;
}

function openEdit(row: any) {
  if (!canManage(row)) {
    return ElMessage.warning(t('templates.noPermission', '您无权编辑他人创建的模板'));
  }
  editMode.value = 'edit';
  editingId.value = row.id;
  Object.assign(form, { 
    title: row.title, 
    description: row.description, 
    is_public: row.is_public, 
    icon: row.icon || 'Document',
    tmplType: row.is_low_code ? 'lowcode' : 'rich'
  });
  dialogVisible.value = true;
}

function openDesigner(row: any) {
  if (!canManage(row)) {
    return ElMessage.warning(t('templates.noPermission', '您无权编辑他人创建的模板'));
  }
  currentDesignerTemplate.value = row;
  designerVisible.value = true;
}

function openInEditor(row: any) {
  router.push(`/doc/${row.id}`);
}

async function submitForm() {
  await formRef.value?.validate();
  saving.value = true;
  try {
    if (editMode.value === 'create') {
      const payload: any = { ...form };
      if (form.tmplType === 'lowcode') {
        payload.template_schema = {
          form_type: 'low_code',
          fields: [
            { id: 'f_title', label: '申请事项 / 项目名称', type: 'text', placeholder: '请输入事项名称', required: true },
            { id: 'f_dept', label: '申请部门', type: 'dept_select', required: true },
            { id: 'f_date', label: '申请日期', type: 'date', required: true },
            { id: 'f_desc', label: '申请事由与说明', type: 'textarea', placeholder: '请详细阐述申请事由...', required: true }
          ]
        };
      }
      const { data } = await api.post('/templates/admin', payload);
      ElMessage.success(t('templates.createSuccess', '模板创建成功！'));
      dialogVisible.value = false;
      await loadData();

      if (form.tmplType === 'lowcode') {
        openDesigner(data);
      } else {
        router.push(`/doc/${data.id}`);
      }
    } else {
      await api.patch(`/templates/admin/${editingId.value}`, { ...form });
      ElMessage.success(t('common.success', 'Saved'));
      dialogVisible.value = false;
      await loadData();
    }
  } catch {
    ElMessage.error(t('common.failed', 'Operation failed'));
  } finally {
    saving.value = false;
  }
}

async function togglePublish(row: any) {
  if (!canManage(row)) {
    return ElMessage.warning(t('templates.noPermission', '您无权修改他人创建的模板状态'));
  }
  const endpoint = row.is_public
    ? `/templates/admin/${row.id}/unpublish`
    : `/templates/admin/${row.id}/publish`;
  try {
    await api.post(endpoint);
    row.is_public = !row.is_public;
    ElMessage.success(row.is_public ? t('templates.publishSuccess', 'Template published!') : t('templates.unpublishSuccess', 'Template unpublished.'));
  } catch {
    ElMessage.error(t('common.failed', 'Operation failed'));
  }
}

async function deleteTemplate(row: any) {
  if (!canManage(row)) {
    return ElMessage.warning(t('templates.noPermission', '您无权删除他人创建的模板'));
  }
  try {
    await api.delete(`/templates/admin/${row.id}`);
    ElMessage.success(t('templates.deleteSuccess', 'Template deleted'));
    await loadData();
  } catch {
    ElMessage.error(t('common.failed', 'Operation failed'));
  }
}

onMounted(loadData);
</script>

<style scoped>
.admin-tmpl-page {
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
  flex-wrap: wrap;
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

.hero-action-btn {
  background: rgba(255, 255, 255, 0.2) !important;
  color: #fff !important;
  border: 1px solid rgba(255, 255, 255, 0.4) !important;
  backdrop-filter: blur(8px);
  font-weight: 700;
  transition: all 0.2s ease;
}

.hero-action-btn:hover {
  background: #fff !important;
  color: var(--el-color-primary) !important;
}

.stats-strip {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.stat-card {
  flex: 1;
  min-width: 140px;
  background: #fff;
  border-radius: 12px;
  padding: 16px 20px;
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  box-shadow: 0 2px 6px rgba(0,0,0,0.02);
}

.stat-num {
  font-size: 1.6rem;
  font-weight: 800;
  color: #1e293b;
}

.stat-label {
  font-size: 0.8rem;
  color: #64748b;
  margin-top: 4px;
}

.stat-card.published .stat-num { color: #16a34a; }
.stat-card.draft .stat-num { color: #d97706; }

.table-card {
  background: #fff;
  border-radius: 14px;
  border: 1px solid #e2e8f0;
  padding: 20px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.03);
}

.table-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  gap: 12px;
  flex-wrap: wrap;
}

.table-search {
  width: 260px;
}

.title-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.title-icon {
  font-size: 18px;
  color: var(--el-color-primary);
}

.desc-text {
  color: #64748b;
  font-size: 13px;
}

.date-text {
  font-size: 12px;
  color: #94a3b8;
}

.action-btns {
  display: flex;
  gap: 6px;
  justify-content: center;
}

.icon-picker {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 8px;
  margin-top: 8px;
}

.icon-item {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
  cursor: pointer;
  font-size: 18px;
  color: #64748b;
  transition: all 0.15s ease;
}

.icon-item:hover, .icon-item.active {
  border-color: var(--el-color-primary);
  color: var(--el-color-primary);
  background: #f0fdf4;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
