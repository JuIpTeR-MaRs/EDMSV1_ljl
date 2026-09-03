<template>
  <div class="tree-branch-container" :class="{ 'is-root-branch': node.type === 'root' }">
    <!-- The Node Card -->
    <div 
      class="org-tree-node-card"
      :id="`org-node-${node.id}`"
      :data-dept-id="node.id"
      :class="[
        `node-type-${node.type}`,
        `tier-${getLevelCategory(node.level)}`,
        { 
          'is-dragging': isDraggingSelf,
          'is-drop-hover': isDropTarget,
          'drop-pos-above': isDropTarget && dropZonePosition === 'above',
          'drop-pos-peer': isDropTarget && dropZonePosition === 'peer',
          'drop-pos-below': isDropTarget && dropZonePosition === 'below',
          'is-highlighted-search': isSearchedHighlight,
          'has-children': node.children && node.children.length > 0,
          'is-leaf': !node.children || node.children.length === 0,
          'is-collapsed-node': node.collapsed
        }
      ]"
      :draggable="node.type !== 'root' && isNodeManageable"
      @dragstart.stop="onDragStart($event)"
      @dragend.stop="onDragEnd"
      @dragover.stop.prevent="onDragOver($event)"
      @dragleave.stop="onDragLeave"
      @drop.stop="onDrop($event)"
    >
      <!-- Drop Halo & Action Guide -->
      <div v-if="isDropTarget" class="drop-action-tooltip" :class="`drop-pos-${dropZonePosition}`">
        <template v-if="draggedMember">
          <span class="drop-guide-icon">↳</span>
          <span>{{ t('admin.dropTransferMember', { name: draggedMember.member?.display_name }, `调入 【${draggedMember.member?.display_name}】 到本部门`) }}</span>
        </template>
        <template v-else-if="node.type === 'root'">
          <span class="drop-guide-icon">↳</span>
          <span>{{ t('admin.dropSetFunctionalDept', '设为 一级职能部门 (Level 50)') }}</span>
        </template>
        <template v-else-if="dropZonePosition === 'above'">
          <span class="drop-guide-icon">🔼</span>
          <span>{{ t('admin.dropSetSuperior', { name: formatNodeDisplayName(node) }, `设为 【${formatNodeDisplayName(node)}】 的上级部门（领导关系）`) }}</span>
        </template>
        <template v-else-if="dropZonePosition === 'below'">
          <span class="drop-guide-icon">🔽</span>
          <span>{{ t('admin.dropSetSubordinate', { name: formatNodeDisplayName(node) }, `设为 【${formatNodeDisplayName(node)}】 的下级协作组（下属模式）`) }}</span>
        </template>
        <template v-else>
          <span class="drop-guide-icon">↔️</span>
          <span>{{ t('admin.dropSetPeer', { name: formatNodeDisplayName(node), level: node.level }, `设为与 【${formatNodeDisplayName(node)}】 同级的平行部门 (保持 Level ${node.level})`) }}</span>
        </template>
      </div>

      <!-- Top Header Row: Icon, Tag, Level -->
      <div class="node-top-bar">
        <div class="node-type-badge">
          <span class="node-emoji">{{ getNodeIcon(node) }}</span>
          <span class="node-type-title">{{ getNodeTypeLabel(node) }}</span>
        </div>
        <span class="node-level-pill" :class="`pill-${getLevelCategory(node.level)}`">
          L{{ node.level }}
        </span>
      </div>

      <!-- Main Name & Subtitle -->
      <div class="node-title-box">
        <div class="node-primary-name" :title="formatNodeDisplayName(node)">{{ formatNodeDisplayName(node) }}</div>
        <div v-if="formatNodeSubName(node)" class="node-sub-name">{{ formatNodeSubName(node) }}</div>
      </div>

      <!-- Meta info: Supervisor & Member count -->
      <div class="node-meta-grid">
        <div class="meta-item leader-item" :title="node.leaderName ? `${t('admin.supervisor')}: ${node.leaderName}` : t('admin.unassigned')">
          <span class="meta-icon">👤</span>
          <span class="meta-text">{{ node.leaderName || t('admin.unassigned') }}</span>
        </div>
        <div 
          class="meta-item members-item" 
          @click.stop="$emit('view-members', node)" 
          :title="t('admin.viewDirectMembers', '点击查看直属成员列表')"
        >
          <span class="meta-icon">👥</span>
          <span class="meta-text font-semibold">{{ formatMemberCount(node.memberCount || 0) }}</span>
        </div>
      </div>

      <!-- Direct Member Pills Preview with Drag-and-Drop Transfer Support -->
      <div v-if="node.members && node.members.length > 0" class="node-members-pills-row">
        <div 
          v-for="m in node.members.slice(0, 3)" 
          :key="m.id" 
          class="tree-member-pill"
          :class="{ 
            'is-manager-pill': m.is_manager || m.is_super_admin,
            'is-dragging-member': draggedMember?.member?.id === m.id
          }"
          :draggable="isNodeManageable"
          @dragstart.stop="onMemberDragStart(m, node, $event)"
          @dragend.stop="onDragEnd"
          @click.stop="$emit('member-click', m, node)"
          :title="locale === 'zh-CN' ? `点击查看【${m.display_name}】个人信息小卡 (按住可拖拽调动部门)` : `Click to view profile card for 【${m.display_name}】 (Drag to transfer)`"
        >
          <img v-if="m.avatar_url" :src="m.avatar_url" class="pill-avatar-img" alt="avatar" />
          <span v-else class="pill-avatar-letter">{{ (m.display_name || m.username).slice(0, 1).toUpperCase() }}</span>
          <span class="pill-display-name">{{ m.display_name }}</span>
          <span v-if="m.is_manager || m.is_super_admin" class="pill-manager-crown">👑</span>
        </div>
        <div 
          v-if="node.members.length > 3" 
          class="tree-member-more-tag"
          @click.stop="$emit('view-members', node)"
          :title="locale === 'zh-CN' ? `点击查看全部 ${node.members.length} 名直属成员` : `Click to view all ${node.members.length} members`"
        >
          +{{ node.members.length - 3 }}
        </div>
      </div>

      <!-- Hover Quick Actions -->
      <div class="node-hover-actions">
        <el-tooltip v-if="isNodeManageable" :content="t('admin.addChildDept', '添加下级部门/协作组')" placement="top" :hide-after="0">
          <el-button circle size="small" :icon="Plus" type="primary" @click.stop="$emit('add-child', node)" />
        </el-tooltip>
        <el-tooltip v-if="isNodeManageable && node.type !== 'root'" :content="t('admin.editDept', '编辑部门信息与层级')" placement="top" :hide-after="0">
          <el-button circle size="small" :icon="Edit" @click.stop="$emit('edit', node)" />
        </el-tooltip>
        <el-tooltip :content="t('admin.viewDirectMembers', '查看/管理直属成员')" placement="top" :hide-after="0">
          <el-button circle size="small" :icon="User" type="info" @click.stop="$emit('view-members', node)" />
        </el-tooltip>
        <el-tooltip 
          v-if="isNodeManageable && node.type === 'dept' && (!node.children || node.children.length === 0)" 
          :content="t('admin.deleteDept', '删除部门')" 
          placement="top" 
          :hide-after="0"
        >
          <el-button circle size="small" :icon="Delete" type="danger" @click.stop="$emit('delete', node)" />
        </el-tooltip>
      </div>

      <!-- Expand / Collapse Button -->
      <div 
        v-if="node.children && node.children.length > 0"
        class="collapse-toggle-btn"
        :class="{ 'is-collapsed': node.collapsed }"
        @click.stop="$emit('toggle-collapse', node)"
        :title="node.collapsed ? (locale === 'zh-CN' ? `点击展开 ${node.children.length} 个下级部门` : `Click to expand ${node.children.length} departments`) : (locale === 'zh-CN' ? '点击收起下级分支' : 'Click to collapse branch')"
      >
        <span class="toggle-symbol">{{ node.collapsed ? `+ ${node.children.length}` : '−' }}</span>
      </div>
    </div>

    <!-- Tree Branches and Children (Recursive) -->
    <div 
      v-if="node.children && node.children.length > 0 && !node.collapsed"
      class="tree-children-block"
    >
      <!-- Trunk Line from parent down -->
      <div class="trunk-vertical-line"></div>

      <!-- Horizontal bus line connecting siblings -->
      <div 
        v-if="node.children.length > 1" 
        class="bus-horizontal-bar"
      ></div>

      <!-- Siblings Container -->
      <div class="siblings-row">
        <div 
          v-for="child in node.children" 
          :key="child.id" 
          class="child-branch-wrapper"
        >
          <!-- Drop Line from bus down to child node -->
          <div class="child-drop-line"></div>

          <!-- Recursive Child Node -->
          <OrgTreeNode 
            :node="child"
            :dragged-node="draggedNode"
            :dragged-member="draggedMember"
            :auth="auth"
            :parent-is-manageable="isNodeManageable"
            :highlight-dept-id="highlightDeptId"
            @drag-start="(n, e) => $emit('drag-start', n, e)"
            @drag-end="(e) => $emit('drag-end', e)"
            @drag-over="(n, e) => $emit('drag-over', n, e)"
            @drag-leave="(n, e) => $emit('drag-leave', n, e)"
            @drop="(data) => $emit('drop', data)"
            @member-drag-start="(m, s, e) => $emit('member-drag-start', m, s, e)"
            @member-drop="(data) => $emit('member-drop', data)"
            @member-click="(m, n) => $emit('member-click', m, n)"
            @add-child="(p) => $emit('add-child', p)"
            @edit="(n) => $emit('edit', n)"
            @delete="(n) => $emit('delete', n)"
            @view-members="(n) => $emit('view-members', n)"
            @toggle-collapse="(n) => $emit('toggle-collapse', n)"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { useI18n } from "vue-i18n";
import { Plus, Edit, Delete, User } from "@element-plus/icons-vue";

const { t, locale } = useI18n();

export interface OrgTreeNodeData {
  id: string | number;
  name: string;
  name_en?: string;
  type: "root" | "dept" | "role";
  level: number;
  parentId: number | null;
  leaderName?: string;
  memberCount: number;
  members?: any[];
  children: OrgTreeNodeData[];
  collapsed?: boolean;
  raw: any;
}

export interface TreeDropPayload {
  targetNode: OrgTreeNodeData;
  position: 'above' | 'peer' | 'below';
  event?: DragEvent;
}

const props = withDefaults(
  defineProps<{
    node: OrgTreeNodeData;
    draggedNode?: OrgTreeNodeData | null;
    draggedMember?: { member: any; sourceNode: OrgTreeNodeData } | null;
    auth?: any;
    parentIsManageable?: boolean;
    highlightDeptId?: number | string | null;
  }>(),
  {
    draggedNode: null,
    draggedMember: null,
    auth: null,
    parentIsManageable: false,
    highlightDeptId: null
  }
);

const emit = defineEmits<{
  (e: "drag-start", node: OrgTreeNodeData, event: DragEvent): void;
  (e: "drag-end", event?: DragEvent): void;
  (e: "drag-over", node: OrgTreeNodeData, event: DragEvent): void;
  (e: "drag-leave", node: OrgTreeNodeData, event: DragEvent): void;
  (e: "drop", data: TreeDropPayload): void;
  (e: "member-drag-start", member: any, sourceNode: OrgTreeNodeData, event: DragEvent): void;
  (e: "member-drop", data: { member: any; sourceNode: OrgTreeNodeData; targetNode: OrgTreeNodeData }): void;
  (e: "member-click", member: any, node: OrgTreeNodeData): void;
  (e: "add-child", parentNode: OrgTreeNodeData): void;
  (e: "edit", node: OrgTreeNodeData): void;
  (e: "delete", node: OrgTreeNodeData): void;
  (e: "view-members", node: OrgTreeNodeData): void;
  (e: "toggle-collapse", node: OrgTreeNodeData): void;
}>();

const isDropTarget = ref(false);
const dropZonePosition = ref<'above' | 'peer' | 'below' | null>(null);

const isDraggingSelf = computed(() => {
  return props.draggedNode?.id === props.node.id;
});

const isSearchedHighlight = computed(() => {
  if (!props.highlightDeptId) return false;
  return props.highlightDeptId === props.node.id || Number(props.highlightDeptId) === Number(props.node.id);
});

const isNodeManageable = computed(() => {
  if (!props.auth?.user) return false;
  if (props.auth.user.is_super_admin || (props.auth.user.role_level && props.auth.user.role_level >= 100)) return true;
  if (!props.auth.user.is_manager && !(props.auth.user.role_level && props.auth.user.role_level >= 50)) return false;
  if (props.node.type === 'root') return false;
  
  const myDeptId = props.auth.user.department_id;
  if (myDeptId && Number(props.node.id) === Number(myDeptId)) return true;
  
  return props.parentIsManageable || false;
});

function getLevelCategory(level?: number): string {
  const lvl = level || 50;
  if (lvl >= 100) return "admin";
  if (lvl >= 80) return "director";
  if (lvl >= 50) return "manager";
  return "staff";
}

function getNodeIcon(node: OrgTreeNodeData): string {
  if (node.type === "root") return "👑";
  if (node.level >= 80) return "🏛️";
  if (node.level >= 50) return "🏢";
  return "📂";
}

function getNodeTypeLabel(node: OrgTreeNodeData): string {
  if (node.type === "root") return t("admin.nodeTypeRoot", "最高管理与决策中心");
  if (node.level >= 80) return t("admin.nodeTypeDirector", "高级管理中心");
  if (node.level >= 50) return t("admin.nodeTypeManager", "一级职能部门");
  return t("admin.nodeTypeStaff", "基础业务 / 协作团队");
}

function formatNodeDisplayName(node: OrgTreeNodeData): string {
  if (node.type === 'root') {
    return locale.value === 'zh-CN' ? node.name : (node.name_en || node.name);
  }
  if (locale.value === 'zh-CN') {
    return node.name;
  }
  return node.name_en || node.name;
}

function formatNodeSubName(node: OrgTreeNodeData): string {
  if (node.type === 'root') {
    return locale.value === 'zh-CN' ? (node.name_en || '') : node.name;
  }
  if (locale.value === 'zh-CN') {
    return node.name_en || '';
  }
  return node.name_en ? node.name : '';
}

function formatMemberCount(count: number): string {
  if (locale.value === 'zh-CN') {
    return `${count} 名成员`;
  }
  return count === 1 ? '1 Member' : `${count} Members`;
}

function isDescendant(parent: OrgTreeNodeData, potentialChild: OrgTreeNodeData): boolean {
  if (!parent || !potentialChild) return false;
  if (parent.id === potentialChild.id) return true;
  if (!parent.children || parent.children.length === 0) return false;
  return parent.children.some((c) => isDescendant(c, potentialChild));
}

function onDragStart(e: DragEvent) {
  if (props.node.type === "root" || !isNodeManageable.value) return;
  if (e.dataTransfer) {
    e.dataTransfer.setData("text/plain", String(props.node.id));
    e.dataTransfer.effectAllowed = "move";
  }
  emit("drag-start", props.node, e);
}

function onMemberDragStart(member: any, sourceNode: OrgTreeNodeData, e: DragEvent) {
  if (!isNodeManageable.value) return;
  if (e.dataTransfer) {
    e.dataTransfer.setData("text/plain", JSON.stringify({ memberId: member.id, sourceDeptId: sourceNode.id }));
    e.dataTransfer.effectAllowed = "move";
  }
  emit("member-drag-start", member, sourceNode, e);
}

function onDragEnd(e?: DragEvent) {
  isDropTarget.value = false;
  dropZonePosition.value = null;
  emit("drag-end", e);
}

function onDragOver(e: DragEvent) {
  if (!isNodeManageable.value && props.node.type !== 'root') return;
  if (props.node.type === 'root' && !props.auth?.user?.is_super_admin) return;

  if (props.draggedMember) {
    // If dragging a member, allow dropping onto any department except the source department itself
    if (props.draggedMember.sourceNode.id === props.node.id) return;
    isDropTarget.value = true;
    return;
  }

  if (!props.draggedNode) return;
  if (props.draggedNode.id === props.node.id) return;
  // Prevent dragging a parent into its own descendant tree!
  if (isDescendant(props.draggedNode, props.node)) return;

  isDropTarget.value = true;

  if (props.node.type === "root") {
    dropZonePosition.value = "below";
  } else {
    const cardEl = e.currentTarget as HTMLElement;
    if (cardEl && cardEl.getBoundingClientRect) {
      const rect = cardEl.getBoundingClientRect();
      const offsetY = e.clientY - rect.top;
      const ratio = offsetY / rect.height;

      if (ratio < 0.3) {
        dropZonePosition.value = "above"; // 上方：上级领导
      } else if (ratio < 0.7) {
        dropZonePosition.value = "peer";  // 中间：同级平行
      } else {
        dropZonePosition.value = "below"; // 下方：下级协作
      }
    } else {
      dropZonePosition.value = "peer";
    }
  }

  emit("drag-over", props.node, e);
}

function onDragLeave(_e: DragEvent) {
  isDropTarget.value = false;
  dropZonePosition.value = null;
  emit("drag-leave", props.node, _e);
}

function onDrop(e: DragEvent) {
  if (!isNodeManageable.value && props.node.type !== 'root') return;
  if (props.node.type === 'root' && !props.auth?.user?.is_super_admin) return;

  const pos = dropZonePosition.value || (props.node.type === "root" ? "below" : "peer");
  isDropTarget.value = false;
  dropZonePosition.value = null;

  if (props.draggedMember) {
    if (props.draggedMember.sourceNode.id === props.node.id) return;
    emit("member-drop", {
      member: props.draggedMember.member,
      sourceNode: props.draggedMember.sourceNode,
      targetNode: props.node
    });
    return;
  }

  if (!props.draggedNode) return;
  if (props.draggedNode.id === props.node.id) return;
  if (isDescendant(props.draggedNode, props.node)) return;

  emit("drop", {
    targetNode: props.node,
    position: pos,
    event: e
  });
}
</script>

<style scoped>
/* ── Tree Branch Container ───────────────────────────────────── */
.tree-branch-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
}

/* ── Node Card Styling ───────────────────────────────────────── */
.org-tree-node-card {
  width: 230px;
  background: #ffffff;
  border: 1.5px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px 14px;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.05);
  position: relative;
  transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1);
  user-select: none;
  cursor: grab;
  box-sizing: border-box;
}

.org-tree-node-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  border-color: #94a3b8;
}

.org-tree-node-card.is-dragging {
  opacity: 0.35;
  border: 2px dashed #64748b;
  transform: scale(0.96);
}

/* Drop target halo indicator */
.org-tree-node-card.is-drop-hover {
  transform: scale(1.03);
  transition: all 0.16s ease;
}

.org-tree-node-card.is-drop-hover.drop-pos-above {
  border: 2px solid #3b82f6 !important;
  border-top: 4px solid #2563eb !important;
  background: #eff6ff !important;
  box-shadow: 0 -4px 16px rgba(37, 99, 235, 0.35), 0 0 0 3px rgba(59, 130, 246, 0.2) !important;
}

.org-tree-node-card.is-drop-hover.drop-pos-peer {
  border: 2px solid #10b981 !important;
  background: #f0fdf4 !important;
  box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.28) !important;
}

.org-tree-node-card.is-drop-hover.drop-pos-below {
  border: 2px solid #8b5cf6 !important;
  border-bottom: 4px solid #7c3aed !important;
  background: #f5f3ff !important;
  box-shadow: 0 6px 18px rgba(124, 58, 237, 0.35), 0 0 0 3px rgba(139, 92, 246, 0.2) !important;
}

/* ── Searched Department Spotlight Animation ────────────────── */
.org-tree-node-card.is-highlighted-search {
  border: 2.5px solid #f59e0b !important;
  box-shadow: 0 0 0 6px rgba(245, 158, 11, 0.45), 0 12px 30px rgba(245, 158, 11, 0.3) !important;
  animation: searchGlowPulse 1.2s infinite ease-in-out;
  z-index: 30 !important;
}

@keyframes searchGlowPulse {
  0%, 100% {
    transform: scale(1.06);
    box-shadow: 0 0 0 6px rgba(245, 158, 11, 0.5), 0 12px 32px rgba(245, 158, 11, 0.35);
  }
  50% {
    transform: scale(1.02);
    box-shadow: 0 0 0 12px rgba(245, 158, 11, 0.15), 0 6px 18px rgba(245, 158, 11, 0.2);
  }
}

.drop-action-tooltip {
  position: absolute;
  top: -36px;
  left: 50%;
  transform: translateX(-50%);
  background: #0f172a;
  color: #ffffff;
  font-size: 11.5px;
  padding: 4px 12px;
  border-radius: 20px;
  white-space: nowrap;
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.22);
  display: flex;
  align-items: center;
  gap: 5px;
  z-index: 50;
  pointer-events: none;
}

.drop-action-tooltip.drop-pos-above {
  background: #1e40af;
  border: 1px solid #60a5fa;
  box-shadow: 0 6px 16px rgba(30, 64, 175, 0.4);
}

.drop-action-tooltip.drop-pos-peer {
  background: #065f46;
  border: 1px solid #34d399;
  box-shadow: 0 6px 16px rgba(6, 95, 70, 0.4);
}

.drop-action-tooltip.drop-pos-below {
  background: #5b21b6;
  border: 1px solid #a78bfa;
  box-shadow: 0 6px 16px rgba(91, 33, 182, 0.4);
}

.drop-guide-icon {
  font-weight: bold;
  font-size: 13px;
}

/* ── Tier Color Accents ──────────────────────────────────────── */
.org-tree-node-card.tier-admin {
  border-top: 4px solid #ef4444;
  background: linear-gradient(180deg, #fff5f5 0%, #ffffff 40%);
}
.org-tree-node-card.tier-director {
  border-top: 4px solid #f59e0b;
  background: linear-gradient(180deg, #fffbeb 0%, #ffffff 40%);
}
.org-tree-node-card.tier-manager {
  border-top: 4px solid #10b981;
  background: linear-gradient(180deg, #f0fdf4 0%, #ffffff 40%);
}
.org-tree-node-card.tier-staff {
  border-top: 4px solid #3b82f6;
  background: linear-gradient(180deg, #eff6ff 0%, #ffffff 40%);
}

/* ── Top Bar ─────────────────────────────────────────────────── */
.node-top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.node-type-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
}

.node-emoji {
  font-size: 14px;
}

.node-level-pill {
  font-size: 10px;
  font-weight: 800;
  padding: 2px 6px;
  border-radius: 10px;
  color: #ffffff;
}

.pill-admin { background: linear-gradient(135deg, #ef4444, #dc2626); }
.pill-director { background: linear-gradient(135deg, #f59e0b, #d97706); }
.pill-manager { background: linear-gradient(135deg, #10b981, #059669); }
.pill-staff { background: linear-gradient(135deg, #3b82f6, #2563eb); }

/* ── Title Box ───────────────────────────────────────────────── */
.node-title-box {
  margin-bottom: 8px;
}

.node-primary-name {
  font-size: 14px;
  font-weight: 800;
  color: #0f172a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.3;
}

.node-sub-name {
  font-size: 11px;
  color: #94a3b8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── Meta info row ───────────────────────────────────────────── */
.node-meta-grid {
  display: flex;
  flex-direction: column;
  gap: 4px;
  background: #f8fafc;
  border: 1px solid #f1f5f9;
  border-radius: 6px;
  padding: 6px 8px;
  font-size: 11px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #475569;
}

.members-item {
  cursor: pointer;
  color: #2563eb;
  transition: color 0.15s;
}

.members-item:hover {
  color: #1d4ed8;
  text-decoration: underline;
}

.meta-icon {
  font-size: 12px;
}

.meta-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.font-semibold {
  font-weight: 600;
}

/* ── Direct Member Pills Row ─────────────────────────────────── */
.node-members-pills-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px dashed #e2e8f0;
}

.tree-member-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 2px 6px 2px 3px;
  font-size: 11px;
  color: #334155;
  cursor: grab;
  transition: all 0.18s ease;
  user-select: none;
}

.tree-member-pill:hover {
  background: #e2e8f0;
  border-color: #cbd5e1;
  transform: translateY(-1px);
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.08);
}

.tree-member-pill:active {
  cursor: grabbing;
}

.tree-member-pill.is-manager-pill {
  background: #fef3c7;
  border-color: #fde68a;
  color: #92400e;
  font-weight: 600;
}

.tree-member-pill.is-dragging-member {
  opacity: 0.4;
  border-style: dashed;
}

.pill-avatar-img {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}

.pill-avatar-letter {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  background: #3b82f6;
  color: #ffffff;
  border-radius: 50%;
  font-size: 9px;
  font-weight: bold;
  flex-shrink: 0;
}

.is-manager-pill .pill-avatar-letter {
  background: #d97706;
}

.pill-display-name {
  max-width: 68px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pill-manager-crown {
  font-size: 10px;
}

.tree-member-more-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 1px 5px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  font-size: 10px;
  font-weight: bold;
  color: #64748b;
  cursor: pointer;
  transition: all 0.15s;
}

.tree-member-more-tag:hover {
  background: #e2e8f0;
  color: #1e293b;
}

/* ── Hover Actions Bar ───────────────────────────────────────── */
.node-hover-actions {
  position: absolute;
  top: -12px;
  right: 8px;
  display: flex;
  gap: 4px;
  opacity: 0;
  transform: translateY(4px);
  transition: all 0.2s ease;
  background: rgba(255, 255, 255, 0.95);
  padding: 3px 6px;
  border-radius: 20px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.12);
  border: 1px solid #e2e8f0;
  z-index: 10;
}

.org-tree-node-card:hover .node-hover-actions {
  opacity: 1;
  transform: translateY(0);
}

/* ── Expand / Collapse Trigger Button ────────────────────────── */
.collapse-toggle-btn {
  position: absolute;
  bottom: -12px;
  left: 50%;
  transform: translateX(-50%);
  width: 24px;
  height: 24px;
  border-radius: 12px;
  background: #ffffff;
  border: 1.5px solid #64748b;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
  transition: all 0.2s ease;
  z-index: 5;
}

.collapse-toggle-btn:hover {
  background: var(--el-color-primary);
  border-color: var(--el-color-primary);
  color: #ffffff;
  transform: translateX(-50%) scale(1.15);
}

.collapse-toggle-btn.is-collapsed {
  width: auto;
  padding: 0 8px;
  background: #f1f5f9;
  border-color: #0284c7;
  color: #0284c7;
  font-weight: bold;
}

.toggle-symbol {
  font-size: 11px;
  font-weight: 800;
  line-height: 1;
}

/* ── Tree Connectors (Vertical Trunk & Horizontal Bus Lines) ── */
.tree-children-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-top: 14px;
  position: relative;
  width: 100%;
}

.trunk-vertical-line {
  width: 2px;
  height: 24px;
  background: #94a3b8;
}

.bus-horizontal-bar {
  height: 2px;
  background: #94a3b8;
  width: 100%;
  margin-top: -1px;
  border-radius: 1px;
}

.siblings-row {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  gap: 28px;
  width: 100%;
  position: relative;
}

.child-branch-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
}

.child-drop-line {
  width: 2px;
  height: 20px;
  background: #94a3b8;
}

/* Trim horizontal bus bar edges so line stops at first and last child centers */
.siblings-row > .child-branch-wrapper:first-child::before {
  content: "";
  position: absolute;
  top: -2px;
  left: 0;
  width: 50%;
  height: 4px;
  background: #f8fafc;
}

.siblings-row > .child-branch-wrapper:last-child::after {
  content: "";
  position: absolute;
  top: -2px;
  right: 0;
  width: 50%;
  height: 4px;
  background: #f8fafc;
}

/* If only one child, no trimming pseudo elements needed */
.siblings-row > .child-branch-wrapper:only-child::before,
.siblings-row > .child-branch-wrapper:only-child::after {
  display: none !important;
}

@keyframes pulse {
  0%, 100% { transform: translateX(-50%) scale(1); }
  50% { transform: translateX(-50%) scale(1.08); }
}
</style>
