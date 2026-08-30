<template>
  <div class="page-wrapper">
    <div class="hero-header">
      <div class="header-left">
        <div class="header-icon-ring">
          <el-icon><Message /></el-icon>
        </div>
        <div>
          <h1 class="page-title">{{ t("inbox.title") }}</h1>
          <p class="page-sub">{{ t("dashboard.subtitle", "Track and manage your document approval tasks.") }}</p>
        </div>
      </div>
    </div>
    
    <div class="edms-content-card">
      <el-tabs v-model="activeTab" class="custom-tabs">
        <el-tab-pane :label="t('inbox.pendingMyApproval')" name="pending">
          <div class="toolbar">
            <el-button @click="load" :loading="loading" :icon="Refresh">{{ t("inbox.refresh") }}</el-button>
            <el-input
              v-model="searchQuery"
              :placeholder="t('editor.searchPlaceholder')"
              :prefix-icon="Search"
              clearable
              style="width: 250px; margin-left: auto;"
            />
          </div>

          <el-table :data="paginatedItems" stripe style="width: 100%">
            <el-table-column type="expand">
              <template #default="{ row }">
                <div class="progress-details">
                  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <h4 style="margin: 0;">{{ t("inbox.progressDetails") }}</h4>
                    <el-button size="small" type="primary" plain :icon="MagicStick" @click="getAiSummary(row.flow_id)" :loading="summarizing[row.flow_id]">
                      ✨ AI 智能总结
                    </el-button>
                  </div>
                  <div class="initiator-info">
                    <strong>{{ t("inbox.initiator") }}:</strong> {{ row.initiator_name }}
                  </div>
                  <el-table :data="row.details" size="small" border style="width: 100%">
                    <el-table-column prop="user_name" :label="t('inbox.participant')" />
                    <el-table-column :label="t('inbox.decision')">
                      <template #default="{ row: p }">
                        <el-tag :type="getDecisionType(p.decision)" size="small">
                          {{ getDecisionLabel(p.decision) }}
                        </el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column prop="reason" :label="t('inbox.reason')" show-overflow-tooltip />
                  </el-table>
                </div>
              </template>
            </el-table-column>
            
            <el-table-column :label="t('inbox.colDocId')" width="140">
              <template #default="{ row }">
                {{ row.doc_number || (row.document_id ? '#' + row.document_id : '-') }}
              </template>
            </el-table-column>
            
            <el-table-column :label="t('inbox.colTitle')" min-width="200" show-overflow-tooltip>
              <template #default="{ row }">
                <template v-if="row.flow_type === 'registration'">
                  {{ t('inbox.userRegistration') }}: {{ row.initiator_name }}
                </template>
                <template v-else>
                  {{ row.title }}
                </template>
              </template>
            </el-table-column>

            <el-table-column :label="t('inbox.colFlow')" width="140">
              <template #default="{ row }">
                <el-tag size="small" type="info">{{ row.flow_type === 'parallel' ? t('editor.parallel') : t('editor.sequential') }}</el-tag>
              </template>
            </el-table-column>

            <el-table-column :label="t('inbox.colProgress')" width="120">
              <template #default="{ row }">
                <span style="font-weight: 600; color: var(--el-color-primary);">{{ row.progress.done }}</span> / {{ row.progress.total }}
              </template>
            </el-table-column>
            
            <el-table-column :label="t('inbox.colSubmittedAt')" width="180">
              <template #default="{ row }">
                <div style="font-size: 13px; color: var(--el-text-color-secondary);">
                  {{ formatLocalDate(row.submitted_at) }}
                </div>
              </template>
            </el-table-column>

            <el-table-column :label="t('inbox.colActions')" width="380" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" size="small" @click="$router.push(`/doc/${row.doc_number || row.document_id}`)">
                  {{ t("library.open") }}
                </el-button>

                <el-button type="success" size="small" @click="decide(row.participant_id, 'approve')">
                  {{ t("inbox.approve") }}
                </el-button>

                <el-button type="warning" size="small" plain :icon="Position" @click="openForward(row)">
                  {{ t("inbox.forward") }}
                </el-button>

                <el-button type="danger" size="small" @click="openReject(row)">
                  {{ t("inbox.reject") }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pagination-wrapper">
            <el-pagination
              v-model:current-page="currentPage"
              :page-size="pageSize"
              size="small"
              background
              layout="prev, pager, next, total"
              :total="filteredItems.length"
            />
          </div>
        </el-tab-pane>

        <!-- 已办审批 (Handled Approvals) -->
        <el-tab-pane :label="t('inbox.handledApprovals')" name="handled">
          <div class="toolbar" style="align-items: center; gap: 12px;">
            <el-button @click="load" :loading="loading" :icon="Refresh">{{ t("inbox.refresh") }}</el-button>
            <div class="stats-pills" style="display: flex; gap: 8px; flex-wrap: wrap;">
              <el-tag type="info" effect="plain" round size="small">
                {{ t("inbox.totalHandled") }}: <strong>{{ handledStats.total }}</strong>
              </el-tag>
              <el-tag type="success" effect="plain" round size="small">
                {{ t("inbox.statsApproved") }}: <strong>{{ handledStats.approved }}</strong>
              </el-tag>
              <el-tag type="warning" effect="plain" round size="small">
                {{ t("inbox.statsForwarded") }}: <strong>{{ handledStats.forwarded }}</strong>
              </el-tag>
              <el-tag type="danger" effect="plain" round size="small">
                {{ t("inbox.statsRejected") }}: <strong>{{ handledStats.rejected }}</strong>
              </el-tag>
            </div>
            <el-input
              v-model="searchHandledQuery"
              :placeholder="t('editor.searchPlaceholder')"
              :prefix-icon="Search"
              clearable
              style="width: 250px; margin-left: auto;"
            />
          </div>

          <el-table :data="paginatedHandledItems" stripe style="width: 100%">
            <el-table-column type="expand">
              <template #default="{ row }">
                <div class="progress-details">
                  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <h4 style="margin: 0;">{{ t("inbox.progressDetails") }}</h4>
                    <el-button size="small" type="primary" plain :icon="MagicStick" @click="getAiSummary(row.flow_id)" :loading="summarizing[row.flow_id]">
                      ✨ AI 智能总结
                    </el-button>
                  </div>
                  <div class="initiator-info">
                    <strong>{{ t("inbox.initiator") }}:</strong> {{ row.initiator_name }}
                  </div>
                  <el-table :data="row.details" size="small" border style="width: 100%">
                    <el-table-column prop="user_name" :label="t('inbox.participant')" />
                    <el-table-column :label="t('inbox.decision')">
                      <template #default="{ row: p }">
                        <el-tag :type="getDecisionType(p.decision)" size="small">
                          {{ getDecisionLabel(p.decision) }}
                        </el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column prop="reason" :label="t('inbox.reason')" show-overflow-tooltip />
                  </el-table>
                </div>
              </template>
            </el-table-column>

            <el-table-column :label="t('inbox.colDocId')" width="140">
              <template #default="{ row }">
                {{ row.doc_number || (row.document_id ? '#' + row.document_id : '-') }}
              </template>
            </el-table-column>

            <el-table-column :label="t('inbox.colTitle')" min-width="200" show-overflow-tooltip>
              <template #default="{ row }">
                <template v-if="row.flow_type === 'registration'">
                  {{ t('inbox.userRegistration') }}: {{ row.initiator_name }}
                </template>
                <template v-else>
                  {{ row.title }}
                </template>
              </template>
            </el-table-column>

            <el-table-column :label="t('inbox.colFlow')" width="130">
              <template #default="{ row }">
                <el-tag size="small" type="info">{{ row.flow_type === 'parallel' ? t('editor.parallel') : t('editor.sequential') }}</el-tag>
              </template>
            </el-table-column>

            <el-table-column :label="t('library.colStatus')" width="120">
              <template #default="{ row }">
                <el-tag :type="getFlowStatusType(row.flow_status)" size="small">
                  {{ getFlowStatusLabel(row.flow_status) }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column :label="t('inbox.myDecision')" width="140">
              <template #default="{ row }">
                <el-tag :type="getDecisionType(row.my_decision)" size="small">
                  {{ getDecisionLabel(row.my_decision) }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column :label="t('inbox.myReason')" min-width="160" show-overflow-tooltip>
              <template #default="{ row }">
                <span v-if="row.my_reason">{{ row.my_reason }}</span>
                <span v-else style="color: var(--el-text-color-placeholder);">-</span>
              </template>
            </el-table-column>

            <el-table-column :label="t('inbox.decidedAt')" width="180">
              <template #default="{ row }">
                <div style="font-size: 13px; color: var(--el-text-color-secondary);">
                  {{ formatLocalDate(row.my_decided_at || row.submitted_at) }}
                </div>
              </template>
            </el-table-column>

            <el-table-column :label="t('inbox.colActions')" width="120" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" size="small" @click="$router.push(`/doc/${row.doc_number || row.document_id}`)">
                  {{ t("library.open") }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pagination-wrapper">
            <el-pagination
              v-model:current-page="currentHandledPage"
              :page-size="pageSize"
              size="small"
              background
              layout="prev, pager, next, total"
              :total="filteredHandledItems.length"
            />
          </div>
        </el-tab-pane>

        <el-tab-pane :label="t('inbox.mySubmissions')" name="mine">
          <div class="toolbar">
            <el-button @click="load" :loading="loading" :icon="Refresh">{{ t("inbox.refresh") }}</el-button>
            <el-input
              v-model="searchMineQuery"
              :placeholder="t('editor.searchPlaceholder')"
              :prefix-icon="Search"
              clearable
              style="width: 250px; margin-left: auto;"
            />
          </div>

          <el-table :data="paginatedMineApps" stripe style="width: 100%">
            <el-table-column type="expand">
              <template #default="{ row }">
                <div class="progress-details">
                  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <h4 style="margin: 0;">{{ t("inbox.progressDetails") }}</h4>
                    <el-button size="small" type="primary" plain :icon="MagicStick" @click="getAiSummary(row.flow_id)" :loading="summarizing[row.flow_id]">
                      ✨ AI 智能总结
                    </el-button>
                  </div>
                  <div class="initiator-info">
                    <strong>{{ t("inbox.initiator") }}:</strong> {{ row.initiator_name }}
                  </div>
                  <el-table :data="row.details" size="small" border style="width: 100%">
                    <el-table-column prop="user_name" :label="t('inbox.participant')" />
                    <el-table-column :label="t('inbox.decision')">
                      <template #default="{ row: p }">
                        <el-tag :type="getDecisionType(p.decision)" size="small">
                          {{ getDecisionLabel(p.decision) }}
                        </el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column prop="reason" :label="t('inbox.reason')" show-overflow-tooltip />
                  </el-table>
                </div>
              </template>
            </el-table-column>

            <el-table-column :label="t('inbox.colDocId')" width="140">
              <template #default="{ row }">
                {{ row.doc_number || (row.document_id ? '#' + row.document_id : '-') }}
              </template>
            </el-table-column>

            <el-table-column :label="t('inbox.colTitle')" min-width="200" show-overflow-tooltip>
              <template #default="{ row }">
                <template v-if="row.flow_type === 'registration'">
                  {{ t('inbox.userRegistration') }}: {{ row.initiator_name }}
                </template>
                <template v-else>
                  {{ row.title }}
                </template>
              </template>
            </el-table-column>

            <el-table-column :label="t('library.colStatus')" width="120">
              <template #default="{ row }">
                <el-tag :type="getFlowStatusType(row.flow_status)" size="small">
                  {{ getFlowStatusLabel(row.flow_status) }}
                </el-tag>
              </template>
            </el-table-column>

            <el-table-column :label="t('inbox.colFlow')" width="140">
              <template #default="{ row }">
                <el-tag size="small" type="info">{{ row.flow_type === 'parallel' ? t('editor.parallel') : t('editor.sequential') }}</el-tag>
              </template>
            </el-table-column>

            <el-table-column :label="t('inbox.colProgress')" width="120">
              <template #default="{ row }">
                <span style="font-weight: 600; color: var(--el-color-primary);">{{ row.progress.done }}</span> / {{ row.progress.total }}
              </template>
            </el-table-column>

            <el-table-column :label="t('inbox.colSubmittedAt')" width="180">
              <template #default="{ row }">
                <div style="font-size: 13px; color: var(--el-text-color-secondary);">
                  {{ formatLocalDate(row.submitted_at) }}
                </div>
              </template>
            </el-table-column>

            <el-table-column :label="t('inbox.colActions')" width="200" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" size="small" @click="$router.push(`/doc/${row.doc_number || row.document_id}`)">
                  {{ t("library.open") }}
                </el-button>

                <el-button v-if="row.flow_status === 'active'" type="warning" size="small" plain @click="recall(row.document_id)">
                  {{ t("inbox.recall") }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pagination-wrapper">
            <el-pagination
              v-model:current-page="currentMinePage"
              :page-size="pageSize"
              size="small"
              background
              layout="prev, pager, next, total"
              :total="filteredMineApps.length"
            />
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <el-dialog v-model="rejectDlg" :title="t('inbox.rejectTitle')" width="420px" class="custom-dialog">
      <div style="margin-bottom: 8px;">{{ t("inbox.reasonPrompt", "Please provide a reason for rejection:") }}</div>
      <el-input v-model="rejectReason" type="textarea" :rows="4" placeholder="..." />
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="rejectDlg = false">{{ t("inbox.cancel") }}</el-button>
          <el-button type="danger" @click="confirmReject">{{ t("inbox.reject") }}</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- Forward Dialog -->
    <el-dialog v-model="forwardDlg" :title="t('inbox.forwardTitle')" width="480px" class="custom-dialog" destroy-on-close>
      <div style="margin-bottom: 12px; color: var(--el-text-color-secondary); font-size: 13px;">
        在同意当前审批的基础上，将该审批单流转给指定人员继续审核。
      </div>
      <div style="margin-bottom: 12px; display: flex; gap: 8px;">
        <el-select v-model="forwardDeptId" clearable :placeholder="t('profile.dept', '部门筛选')" style="width: 150px">
          <el-option v-for="d in deptOptions" :key="d.id" :label="d.name" :value="d.id" />
        </el-select>
        <el-select
          v-model="forwardTargetUserId"
          filterable
          :placeholder="t('inbox.selectNextApprover')"
          style="flex: 1"
        >
          <el-option
            v-for="u in filteredForwardUsers"
            :key="u.id"
            :label="`${u.last_name || ''}${u.first_name || ''} (${u.login_name || u.employee_no})${u.department_name ? ' - ' + u.department_name : ''}`"
            :value="u.id"
          />
        </el-select>
      </div>
      <div style="margin-bottom: 8px; font-size: 13px; font-weight: 500;">{{ t("inbox.forwardReason") }}</div>
      <el-input
        v-model="forwardReason"
        type="textarea"
        :rows="3"
        :placeholder="t('inbox.forwardReasonPlaceholder')"
      />
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="forwardDlg = false">{{ t("inbox.cancel") }}</el-button>
          <el-button type="primary" :loading="forwardLoading" @click="confirmForward">
            {{ t("inbox.confirmForward") }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- AI Summary Dialog -->
    <el-dialog v-model="summaryDlg" title="✨ AI 审批意见总结" width="500px">
      <div v-if="currentSummary" class="markdown-body" v-html="currentSummary"></div>
      <div v-else>正在生成总结...</div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, reactive } from "vue";
import { useI18n } from "vue-i18n";
import api from "@/api/client";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh, Search, Message, MagicStick, Position } from "@element-plus/icons-vue"; // 引入图标
import { formatLocalDate } from "@/utils/date";
import { marked } from "marked";

const { t } = useI18n();
const activeTab = ref("pending");
const items = ref<InboxRow[]>([]);
const myApps = ref<any[]>([]);
const handledItems = ref<any[]>([]);
const handledStats = ref({ total: 0, approved: 0, forwarded: 0, rejected: 0 });
const loading = ref(false);
const rejectPid = ref<number | null>(null);
const rejectDlg = ref(false);
const rejectReason = ref("");

// Forward State
const forwardDlg = ref(false);
const forwardPid = ref<number | null>(null);
const forwardReason = ref("");
const forwardTargetUserId = ref<number | null>(null);
const forwardDeptId = ref<number | null>(null);
const forwardLoading = ref(false);
const deptOptions = ref<any[]>([]);
const userOptions = ref<any[]>([]);
const currentUserId = ref<number | null>(null);

// Search & Pagination
const searchQuery = ref("");
const searchMineQuery = ref("");
const searchHandledQuery = ref("");
const currentPage = ref(1);
const pageSize = ref(10);
const currentMinePage = ref(1);
const currentHandledPage = ref(1);

const filteredItems = computed(() => {
  if (!searchQuery.value) return items.value;
  const q = searchQuery.value.toLowerCase();
  return items.value.filter(item => 
    item.title?.toLowerCase().includes(q) || 
    String(item.document_id).includes(q) ||
    String(item.doc_number || '').toLowerCase().includes(q)
  );
});

const paginatedItems = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return filteredItems.value.slice(start, start + pageSize.value);
});

const filteredMineApps = computed(() => {
  // 💡 核心优化：始终过滤掉状态为 'cancelled' (已撤销) 的申请
  const baseList = myApps.value.filter(item => item.flow_status !== 'cancelled');
  
  if (!searchMineQuery.value) return baseList;
  
  const q = searchMineQuery.value.toLowerCase();
  return baseList.filter(item => 
    item.title?.toLowerCase().includes(q) || 
    String(item.document_id).includes(q) ||
    String(item.doc_number || '').toLowerCase().includes(q)
  );
});

const paginatedMineApps = computed(() => {
  const start = (currentMinePage.value - 1) * pageSize.value;
  return filteredMineApps.value.slice(start, start + pageSize.value);
});

const filteredHandledItems = computed(() => {
  if (!searchHandledQuery.value) return handledItems.value;
  const q = searchHandledQuery.value.toLowerCase();
  return handledItems.value.filter(item => 
    item.title?.toLowerCase().includes(q) || 
    String(item.document_id).includes(q) ||
    String(item.doc_number || '').toLowerCase().includes(q) ||
    item.initiator_name?.toLowerCase().includes(q) ||
    item.my_reason?.toLowerCase().includes(q)
  );
});

const paginatedHandledItems = computed(() => {
  const start = (currentHandledPage.value - 1) * pageSize.value;
  return filteredHandledItems.value.slice(start, start + pageSize.value);
});

const filteredForwardUsers = computed(() => {
  return userOptions.value.filter(u => {
    if (currentUserId.value && u.id === currentUserId.value) return false;
    if (forwardDeptId.value && u.department_id !== forwardDeptId.value) return false;
    return true;
  });
});

interface Participant {
  user_id: number;
  user_name: string;
  decision: string | null;
  reason: string | null;
  step_order: number;
}

interface InboxRow {
  participant_id: number;
  flow_id: number;
  document_id: number;
  doc_number?: string;
  title: string;
  initiator_name: string;
  flow_type: string;
  flow_status: string;
  progress: { done: number; total: number };
  submitted_at?: string;
  details?: Participant[];
}

async function loadForwardOptions() {
  try {
    const [deptRes, userRes, meRes] = await Promise.all([
      api.get("/users/departments"),
      api.get("/users", { params: { size: 500 } }),
      api.get("/users/me")
    ]);
    deptOptions.value = deptRes.data || [];
    userOptions.value = userRes.data?.items || [];
    currentUserId.value = meRes.data?.id || null;
  } catch (err) {
    console.error("Failed to load users or departments for forward", err);
  }
}

async function load() {
  loading.value = true;
  try {
    const [res1, res2, res3] = await Promise.all([
      api.get("/approvals/inbox"),
      api.get("/approvals/my-applications"),
      api.get("/approvals/handled"),
      loadForwardOptions()
    ]);
    items.value = res1.data.items || [];
    myApps.value = res2.data.items || [];
    handledItems.value = res3.data.items || [];
    handledStats.value = res3.data.stats || { total: 0, approved: 0, forwarded: 0, rejected: 0 };
  } finally {
    loading.value = false;
  }
}

async function decide(participantId: number, decision: "approve" | "reject" | "forward", reason?: string, targetUserId?: number) {
  await api.post(`/approvals/participants/${participantId}/decision`, {
    decision,
    reason: reason || undefined,
    target_user_id: targetUserId || undefined,
  });
  ElMessage.success(t("inbox.submitted"));
  load();
}

async function recall(docId: number) {
  try {
    await ElMessageBox.confirm(
      t("inbox.recallConfirm"),
      t("common.warning", "Warning"),
      { type: "warning" }
    );
    await api.post(`/documents/${docId}/recall`);
    ElMessage.success(t("inbox.recallSuccess"));
    load();
  } catch (err) {
    // Ignore cancel
  }
}

function getDecisionType(decision: string | null) {
  if (decision === "approve") return "success";
  if (decision === "forward") return "warning";
  if (decision === "reject") return "danger";
  return "info";
}

function getDecisionLabel(decision: string | null) {
  if (decision === "approve") return t("inbox.approve");
  if (decision === "forward") return t("inbox.statusForwarded");
  if (decision === "reject") return t("inbox.reject");
  return t("inbox.statusPending");
}

function getFlowStatusType(status: string) {
  switch (status) {
    case "active": return "primary";
    case "completed": return "success";
    case "rejected": return "danger";
    case "cancelled": return "info";
    default: return "info";
  }
}

function getFlowStatusLabel(status: string) {
  switch (status) {
    case "active": return t("library.statusInApproval");
    case "completed": return t("library.statusApproved");
    case "rejected": return t("library.statusRejected");
    case "cancelled": return t("inbox.recallSuccess");
    default: return status;
  }
}

function openReject(row: InboxRow) {
  rejectPid.value = row.participant_id;
  rejectReason.value = "";
  rejectDlg.value = true;
}

function confirmReject() {
  if (!rejectPid.value || !rejectReason.value.trim()) {
    ElMessage.warning(t("inbox.reasonRequired"));
    return;
  }
  decide(rejectPid.value, "reject", rejectReason.value);
  rejectDlg.value = false;
}

function openForward(row: InboxRow) {
  forwardPid.value = row.participant_id;
  forwardReason.value = "";
  forwardTargetUserId.value = null;
  forwardDeptId.value = null;
  forwardDlg.value = true;
}

async function confirmForward() {
  if (!forwardPid.value) return;
  if (!forwardTargetUserId.value) {
    ElMessage.warning(t("inbox.targetApproverRequired"));
    return;
  }
  forwardLoading.value = true;
  try {
    await api.post(`/approvals/participants/${forwardPid.value}/decision`, {
      decision: "forward",
      target_user_id: forwardTargetUserId.value,
      reason: forwardReason.value || undefined,
    });
    ElMessage.success(t("inbox.forwardSuccess"));
    forwardDlg.value = false;
    load();
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || t("common.failed", "Failed"));
  } finally {
    forwardLoading.value = false;
  }
}

const summaryDlg = ref(false);
const currentSummary = ref("");
const summarizing = reactive<Record<number, boolean>>({});

async function getAiSummary(flowId: number) {
  if (!flowId) return;
  summarizing[flowId] = true;
  summaryDlg.value = true;
  currentSummary.value = "";
  try {
    const { data } = await api.get(`/approvals/${flowId}/ai-summary`);
    if (data.code === 200) {
      currentSummary.value = await marked.parse(data.data);
    }
  } catch (err) {
    currentSummary.value = "生成摘要失败，请重试。";
  } finally {
    summarizing[flowId] = false;
  }
}

onMounted(load);
</script>

<style scoped>
/* Base Markdown styles */
.markdown-body :deep(p) { margin: 0 0 10px; }
.markdown-body :deep(p:last-child) { margin-bottom: 0; }
.markdown-body :deep(ul), .markdown-body :deep(ol) { margin-top: 0; padding-left: 20px; }
.markdown-body :deep(pre) { background: #f6f8fa; padding: 10px; border-radius: 4px; overflow-x: auto; }
.markdown-body :deep(code) { background: #f6f8fa; padding: 2px 4px; border-radius: 4px; font-family: monospace; }
.page-wrapper {
  padding: 0 0 40px;
}

/* ── Page Header (Hero Style) ────────────────────────────────── */
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

.table-card {
  border-radius: 12px;
  border: 1px solid var(--el-border-color-lighter);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.04);
}

.toolbar {
  margin-bottom: 16px;
  display: flex;
}

.custom-tabs {
  margin-top: -10px;
}

.progress-details {
  padding: 15px 40px;
  background-color: var(--el-fill-color-extra-light);
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.progress-details h4 {
  margin: 0 0 12px;
  font-size: 14px;
  color: var(--el-text-color-primary);
  display: flex;
  align-items: center;
}

.progress-details h4::before {
  content: "";
  width: 4px;
  height: 14px;
  background: var(--el-color-primary);
  margin-right: 8px;
  border-radius: 2px;
}
.initiator-info {
  margin-bottom: 12px;
  font-size: 14px;
  color: var(--el-text-color-regular);
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>