<template>
  <div class="user-mgmt-page">
    <div class="hero-header">
      <div class="header-left">
        <div class="header-icon-ring">
          <el-icon><User /></el-icon>
        </div>
        <div>
          <h1 class="page-title">{{ t('nav.users', 'Member Management') }}</h1>
          <p class="page-sub">{{ t("dashboard.subtitle", "Organize departments and manage employee access.") }}</p>
        </div>
      </div>
      <div class="header-right">
        <!-- 视图切换：列表模式 vs 层级拓扑图 -->
        <el-radio-group v-model="viewMode" size="default" class="view-mode-toggle">
          <el-radio-button value="list">
            <el-icon style="margin-right: 4px; vertical-align: middle;"><List /></el-icon>
            {{ t('admin.viewList', '列表模式') }}
          </el-radio-button>
          <el-radio-button value="chart">
            <el-icon style="margin-right: 4px; vertical-align: middle;"><Share /></el-icon>
            {{ t('admin.viewChart', '层级拓扑图') }}
          </el-radio-button>
        </el-radio-group>

        <el-button 
          v-if="auth.user?.is_super_admin" 
          type="primary" 
          plain 
          :icon="Setting" 
          class="role-mgmt-btn"
          @click="openRoleManagement"
        >
          {{ t('admin.roleManagement', '职级与权限配置') }}
        </el-button>
      </div>
    </div>

    <!-- ══════════════ 视图 1：列表明细模式 ══════════════ -->
    <el-card v-if="viewMode === 'list'" shadow="hover" class="mgmt-card">
      <div class="mgmt-toolbar">
        <div class="toolbar-left">
          <el-input
            v-model="searchQuery"
            :placeholder="t('nav.usersSearchPlaceholder')"
            clearable
            class="search-input"
            @input="handleSearch"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>

          <el-select 
            v-if="auth.user?.is_super_admin || (auth.user?.role_level && auth.user?.role_level >= 80)"
            v-model="filterDept" 
            :placeholder="t('profile.dept', 'Department')" 
            clearable 
            class="filter-select"
            @change="loadUsers"
          >
            <el-option 
              v-for="d in deptOptions" 
              :key="d.id" 
              :label="formatDeptDisplayName(d)" 
              :value="d.id" 
            />
          </el-select>

          <el-select 
            v-model="filterRole" 
            :placeholder="t('library.colRole', 'Role')" 
            clearable 
            class="filter-select"
            @change="loadUsers"
          >
            <el-option 
              v-for="r in rolesList" 
              :key="r.id" 
              :label="`${r.name} (L${r.level})`" 
              :value="r.id" 
            />
          </el-select>

          <!-- 💡 列表排序规则选择器 -->
          <el-select 
            v-model="sortOption" 
            :placeholder="t('common.sortBy', '排序方式')" 
            class="filter-select sort-select"
            style="width: 200px"
            @change="handleSortSelectChange"
          >
            <template #prefix><el-icon><Sort /></el-icon></template>
            <el-option label="👑 权限职级 (高 → 低)" value="level_desc" />
            <el-option label="👤 权限职级 (低 → 高)" value="level_asc" />
            <el-option label="🔢 员工编号 (升序 A→Z)" value="employee_no_asc" />
            <el-option label="🔢 员工编号 (降序 Z→A)" value="employee_no_desc" />
            <el-option label="🔤 成员姓名 (A → Z)" value="name_asc" />
            <el-option label="🔤 成员姓名 (Z → A)" value="name_desc" />
            <el-option label="🏢 所属部门 (分组排序)" value="department_asc" />
            <el-option label="🕒 最新创建优先" value="id_desc" />
            <el-option label="⏳ 最早创建优先" value="id_asc" />
          </el-select>
        </div>

        <div class="header-actions" v-if="canManageUsers">
          <el-button 
            v-if="auth.user?.is_super_admin || auth.user?.is_manager" 
            type="primary" 
            :icon="Plus" 
            @click="openAddUser"
          >
            {{ t('admin.addUser', 'Add Member') }}
          </el-button>
          <el-button 
            v-if="auth.user?.is_super_admin" 
            type="success" 
            :icon="Plus" 
            @click="openAddDeptModal()"
          >
            {{ t('admin.addDept', 'Add Department') }}
          </el-button>
          <el-button 
            v-if="auth.user?.is_super_admin" 
            type="danger" 
            :icon="Delete" 
            :disabled="!filterDept" 
            @click="handleDeleteDept"
            :title="!filterDept ? t('admin.deleteDeptWarning') : ''"
          >
            {{ t('admin.deleteDept', 'Delete Department') }}
          </el-button>
          <el-button 
            type="danger" 
            :icon="Delete" 
            :disabled="selectedIds.length === 0" 
            @click="handleBatchDelete"
          >
            {{ t('common.delete') }} ({{ selectedIds.length }})
          </el-button>
        </div>
      </div>

      <el-table 
        v-loading="loading" 
        :data="users" 
        stripe 
        style="width: 100%"
        :default-sort="{ prop: 'role_level', order: 'descending' }"
        @selection-change="handleSelectionChange"
        @sort-change="handleTableSortChange"
      >
        <el-table-column v-if="canManageUsers" type="selection" width="55" />
        <el-table-column prop="employee_no" :label="t('profile.employeeNo')" width="130" sortable="custom" />
        <el-table-column prop="display_name" :label="t('common.name')" min-width="120" sortable="custom" />
        <el-table-column prop="login_name" :label="t('profile.loginName')" width="120" />
        <el-table-column prop="department_name" :label="t('profile.dept')" min-width="160" sortable="custom">
          <template #default="{ row }">
            {{ formatDeptName(row.department_name, row.department_name_en) }}
          </template>
        </el-table-column>
        <el-table-column prop="role_level" :label="t('library.colRole', 'Role / Rank')" width="190" sortable="custom">
          <template #default="{ row }">
            <el-tag :type="getRoleTagType(row)" size="small" effect="light">
              {{ row.role_name || (row.is_super_admin ? t('common.roles.admin') : (row.is_manager ? t('common.roles.manager') : t('common.roles.user'))) }}
            </el-tag>
            <span class="level-pill" :class="getLevelClass(row.role_level)">
              L{{ row.role_level ?? (row.is_super_admin ? 100 : (row.is_manager ? 50 : 10)) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column v-if="canManageUsers" :label="t('common.actions')" width="240" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="editUser(row)">{{ t('common.edit') }}</el-button>
            <el-button type="warning" link :disabled="row.id !== auth.user?.id && isUserSuperiorOrEqual(row)" @click="handleResetPassword(row)">{{ t('admin.resetPass') }}</el-button>
            <el-tooltip v-if="row.id === auth.user?.id || isUserSuperiorOrEqual(row)" :content="row.id === auth.user?.id ? '禁止删除自己' : '禁止删除同级/上级人员'" placement="top">
              <span>
                <el-button v-if="auth.user?.is_super_admin || auth.user?.is_manager" type="danger" link :disabled="true">{{ t('common.delete') }}</el-button>
              </span>
            </el-tooltip>
            <el-button v-else-if="auth.user?.is_super_admin || auth.user?.is_manager" type="danger" link @click="handleDeleteUser(row)">{{ t('common.delete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          size="small"
          background
          layout="prev, pager, next, total"
          :total="total"
          @current-change="loadUsers"
        />
      </div>
    </el-card>

    <!-- ══════════════ 视图 2：组织架构关系树 (Tree Data Structure View) ══════════════ -->
    <div v-else class="org-tree-view-wrapper">
      <!-- Tree Global Controls Toolbar -->
      <div class="tree-controls-toolbar">
        <div class="toolbar-left-info">
          <span class="tree-badge-title">🌲 {{ t('admin.orgTreeTitle', '企业组织架构与领导关系拓扑树') }}</span>
          <span class="tree-sub-tip">
            {{ t('admin.orgTreeCanvasTip', '💡 画布提示：按住空白处拖动可左右/上下平移画布；支持滚轮平移、Ctrl+滚轮缩放；按住部门卡片可调整上下级领导关系。') }}
          </span>
        </div>

        <div class="toolbar-right-tools">
          <!-- 🔍 Department Quick Finder / Search Locator -->
          <div class="dept-search-locator">
            <el-select
              v-model="searchDeptId"
              :placeholder="t('admin.searchDeptPlaceholder', '🔍 查找部门快速定位...')"
              clearable
              filterable
              size="small"
              class="tree-search-select"
              @change="locateDepartment"
              @clear="onClearSearchDept"
            >
              <el-option
                v-for="d in deptOptions"
                :key="d.id"
                :label="formatDeptDisplayName(d)"
                :value="d.id"
              >
                <div class="search-dept-option-row">
                  <span class="search-opt-icon">🏢</span>
                  <span class="search-opt-name">{{ formatDeptName(d.name, d.name_en) }}</span>
                  <span v-if="d.parent_name" class="search-opt-parent">({{ formatDeptName(d.parent_name) }})</span>
                  <el-tag size="small" :type="d.level >= 80 ? 'warning' : 'success'" class="search-opt-tag">
                    L{{ d.level || 50 }}
                  </el-tag>
                </div>
              </el-option>
            </el-select>
          </div>

          <el-button-group size="small">
            <el-tooltip :content="t('admin.fitViewTip', '自适应全览 (Fit View)')" placement="top">
              <el-button :icon="FullScreen" @click="fitTreeToScreen">{{ t('admin.fitView', '自适应') }}</el-button>
            </el-tooltip>
            <el-tooltip :content="t('admin.zoomInTip', '放大画布 (Ctrl+滚轮上)')" placement="top">
              <el-button :icon="ZoomIn" @click="zoomTree(0.1)" />
            </el-tooltip>
            <el-tooltip :content="t('admin.zoomOutTip', '缩小画布 (Ctrl+滚轮下)')" placement="top">
              <el-button :icon="ZoomOut" @click="zoomTree(-0.1)" />
            </el-tooltip>
            <el-tooltip :content="t('admin.resetZoomTip', '重置居中 100%')" placement="top">
              <el-button :icon="Aim" @click="resetTreeZoom">100%</el-button>
            </el-tooltip>
          </el-button-group>

          <el-button-group size="small" style="margin-left: 8px;">
            <el-button :icon="FolderOpened" @click="expandAllNodes">{{ t('admin.expandAll', '全部展开') }}</el-button>
            <el-button :icon="Folder" @click="collapseAllNodes">{{ t('admin.collapseAll', '全部收起') }}</el-button>
          </el-button-group>

          <el-button 
            v-if="auth.user?.is_super_admin" 
            type="success" 
            :icon="Plus" 
            size="small" 
            @click="openAddDeptModal()"
            style="margin-left: 8px;"
          >
            {{ t('admin.addDept', '新增一级部门') }}
          </el-button>
        </div>
      </div>

      <!-- Tree Canvas Container (Pan, Zoom & Responsive Canvas) -->
      <div 
        ref="canvasViewportRef"
        class="tree-canvas-viewport"
        :class="{ 'is-panning': isCanvasPanning }"
        @mousedown="onCanvasMouseDown"
        @wheel.prevent="onCanvasWheel"
        @dragover.prevent
        @drop="onDropCanvasBackground"
      >
        <!-- Floating Canvas Navigator Controls -->
        <div class="canvas-floating-controls">
          <el-tooltip content="自适应全览" placement="top">
            <el-button circle size="small" :icon="FullScreen" @click.stop="fitTreeToScreen" />
          </el-tooltip>
          <el-tooltip content="重置居中 100%" placement="top">
            <el-button circle size="small" :icon="Aim" @click.stop="resetTreeZoom" />
          </el-tooltip>
          <el-tooltip content="放大" placement="top">
            <el-button circle size="small" :icon="ZoomIn" @click.stop="zoomTree(0.1)" />
          </el-tooltip>
          <el-tooltip content="缩小" placement="top">
            <el-button circle size="small" :icon="ZoomOut" @click.stop="zoomTree(-0.1)" />
          </el-tooltip>
        </div>

        <div 
          ref="canvasStageRef"
          class="tree-canvas-stage"
          :style="{ 
            transform: `translate(calc(-50% + ${panTranslateX}px), ${panTranslateY}px) scale(${treeZoomScale})`, 
            transformOrigin: 'top center' 
          }"
        >
          <OrgTreeNode
            v-if="orgTreeData"
            :node="orgTreeData"
            :dragged-node="draggedTreeNode"
            :dragged-member="draggedMember"
            :auth="auth"
            :highlight-dept-id="highlightedSearchDeptId"
            @drag-start="handleTreeDragStart"
            @drag-end="handleTreeDragEnd"
            @drag-over="handleTreeDragOver"
            @drag-leave="handleTreeDragLeave"
            @drop="handleTreeDrop"
            @member-drag-start="handleMemberDragStart"
            @member-drop="handleMemberDrop"
            @add-child="handleAddChildDept"
            @edit="handleEditDeptNode"
            @delete="handleDeleteDeptNode"
            @view-members="handleViewDeptMembers"
            @toggle-collapse="handleToggleCollapse"
          />
        </div>
      </div>
    </div>

    <!-- ── Department Members Detail Drawer ────────────────────────────────────── -->
    <el-drawer
      v-model="deptMembersDrawerVisible"
      :title="currentSelectedDept ? `🏢 ${currentSelectedDept.name} - ${t('admin.directMembersMgmt', '直属成员管理')}` : t('admin.directMembersMgmt', '直属成员管理')"
      size="650px"
      destroy-on-close
    >
      <div v-if="currentSelectedDept" class="dept-drawer-content">
        <!-- Top Summary Card -->
        <div class="dept-summary-card">
          <div class="summary-top">
            <div class="dept-title-group">
              <span class="dept-big-title">{{ currentSelectedDept.name }}</span>
              <el-tag :type="currentSelectedDept.level >= 80 ? 'warning' : 'success'" size="small">
                Level {{ currentSelectedDept.level }}
              </el-tag>
            </div>
            <div class="summary-actions" v-if="isCurrentDeptManageable">
              <el-button type="primary" size="small" :icon="Plus" @click="openAddUserForCurrentDept">
                {{ t('admin.addDirectMember', '新增直属成员') }}
              </el-button>
              <el-button type="success" plain size="small" :icon="Switch" @click="openTransferUserDialog">
                {{ t('admin.transferInMember', '调入成员') }}
              </el-button>
            </div>
          </div>
          <div class="summary-meta">
            <span>👤 {{ t('admin.supervisor', '主管负责人') }}：<strong>{{ currentSelectedDept.leaderName }}</strong></span>
            <span>👥 {{ t('admin.activeMembers', '直属在职人员') }}：<strong>{{ deptMembersList.length }} {{ t('admin.memberCountSuffix', '人') }}</strong></span>
          </div>
        </div>

        <!-- Members Table -->
        <div class="members-table-wrap">
          <el-table 
            :data="deptMembersList" 
            size="small" 
            stripe 
            border 
            style="width: 100%;" 
            :empty-text="t('admin.noDeptMembers', '当前部门暂无成员，可点击上方【新增直属成员】或【调入成员】')"
          >
            <el-table-column :label="t('admin.memberInfo', '成员信息')" min-width="150">
              <template #default="{ row }">
                <div class="user-row-cell">
                  <div class="user-avatar-small">{{ (row.display_name || row.username).slice(0, 1).toUpperCase() }}</div>
                  <div>
                    <div class="user-cell-name">
                      {{ row.display_name }}
                      <el-tag v-if="row.is_manager || row.is_super_admin" size="small" type="danger" effect="dark" style="margin-left: 4px; height: 18px; line-height: 16px; padding: 0 4px;">
                        {{ t('admin.supervisorTag', '主管') }}
                      </el-tag>
                    </div>
                    <div class="user-cell-sub">@{{ row.login_name || row.username }} · {{ row.employee_no }}</div>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="role_name" :label="t('admin.rolePosition', '职级岗位')" min-width="110">
              <template #default="{ row }">
                <span class="level-pill" :class="getLevelClass(row.role_level)">{{ (locale === 'zh-CN' ? row.role_name : (row.role_name_en || row.role_name)) || t('common.roles.user', '普通员工') }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="t('common.actions', '操作')" width="190" align="center" fixed="right" v-if="isCurrentDeptManageable">
              <template #default="{ row }">
                <div class="drawer-row-actions">
                  <el-tooltip :content="row.id === auth.user?.id ? t('admin.cannotChangeSelfSupervisor', '无法更改自己的主管权限') : (isUserSuperiorOrEqual(row) ? t('admin.cannotChangeSuperiorSupervisor', '无法更改同级/上级人员的主管权限') : (row.is_manager ? t('admin.removeSupervisor', '取消主管身份') : t('admin.setSupervisor', '设为部门主管')))" placement="top">
                    <span>
                      <el-button 
                        circle 
                        size="small" 
                        :type="row.is_manager ? 'warning' : 'default'"
                        :icon="UserFilled" 
                        :disabled="row.id === auth.user?.id || isUserSuperiorOrEqual(row)"
                        @click="toggleUserSupervisor(row)" 
                      />
                    </span>
                  </el-tooltip>
                  <el-tooltip :content="t('common.edit', '编辑成员信息')" placement="top">
                    <el-button circle size="small" :icon="Edit" type="primary" @click="editUser(row)" />
                  </el-tooltip>
                  <el-tooltip :content="t('admin.transferOutMember', '调动到其他部门')" placement="top">
                    <el-button circle size="small" :icon="Switch" type="success" @click="openTransferUserOut(row)" />
                  </el-tooltip>
                  <el-tooltip :content="t('admin.resetPass', '重置密码')" placement="top">
                    <el-button circle size="small" :icon="Key" type="info" :disabled="row.id !== auth.user?.id && isUserSuperiorOrEqual(row)" @click="handleResetPassword(row)" />
                  </el-tooltip>
                  <el-tooltip :content="row.id === auth.user?.id ? t('admin.cannotDeleteSelf', '禁止删除自己') : (isUserSuperiorOrEqual(row) ? t('admin.cannotDeleteSuperior', '禁止删除同级/上级人员') : t('admin.deleteUser', '删除成员'))" placement="top">
                    <span>
                      <el-button 
                        circle 
                        size="small" 
                        :icon="Delete" 
                        type="danger" 
                        :disabled="row.id === auth.user?.id || isUserSuperiorOrEqual(row)"
                        @click="handleDeleteUser(row)" 
                      />
                    </span>
                  </el-tooltip>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </el-drawer>

    <!-- ── 调入成员对话框 (Transfer In Dialog) ────────────────────────── -->
    <el-dialog
      v-model="transferInDialogVisible"
      :title="`📥 调入成员至【${selectedDeptForMembers ? formatDeptName(selectedDeptForMembers.name, selectedDeptForMembers.name_en) : ''}】`"
      width="520px"
      class="custom-dialog"
      destroy-on-close
    >
      <div style="padding: 10px 10px 0;">
        <div style="font-size: 13px; color: var(--el-text-color-secondary); margin-bottom: 12px;">
          选择要调入当前部门的成员（支持多选与搜索），确认后将更新其归属部门：
        </div>
        <el-select
          v-model="transferUserIds"
          multiple
          filterable
          placeholder="请选择或搜索要调入的成员"
          style="width: 100%;"
        >
          <el-option
            v-for="u in availableUsersForTransfer"
            :key="u.id"
            :label="`${u.display_name} (@${u.login_name || u.username}) - 原部门: ${u.department_name ? formatDeptName(u.department_name) : '未分配'}`"
            :value="u.id"
          />
        </el-select>
      </div>
      <template #footer>
        <el-button @click="transferInDialogVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="transferLoading" :disabled="transferUserIds.length === 0" @click="submitTransferIn">
          确认调入 ({{ transferUserIds.length }} 人)
        </el-button>
      </template>
    </el-dialog>

    <!-- ── 调离部门对话框 (Transfer Out Dialog) ───────────────────────── -->
    <el-dialog
      v-model="transferOutDialogVisible"
      :title="`📤 调动成员【${userToTransferOut?.display_name || ''}】至新部门`"
      width="460px"
      class="custom-dialog"
      destroy-on-close
    >
      <div style="padding: 10px 10px 0;">
        <el-form label-width="100px">
          <el-form-item label="目标部门" required>
            <el-select v-model="targetDeptForTransfer" placeholder="请选择调入的目标部门" style="width: 100%;">
              <el-option
                v-for="d in deptOptions"
                :key="d.id"
                :label="formatDeptDisplayName(d)"
                :value="d.id"
              />
            </el-select>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="transferOutDialogVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :disabled="!targetDeptForTransfer" @click="submitTransferUserOut">
          确认调动
        </el-button>
      </template>
    </el-dialog>

    <!-- ── Role & Rank Hierarchy Management Modal (List/Drawer) ────────────────── -->
    <el-dialog 
      v-model="roleManagementDialogVisible" 
      :title="t('admin.rolesTitle', '系统职级与权限等级管理')" 
      width="820px" 
      class="custom-dialog"
      destroy-on-close
    >
      <div style="margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center;">
        <div style="color: var(--el-text-color-secondary); font-size: 13px;">
          {{ t('admin.rolesSubtitle', '支持系统管理员自由配置多级职级体系、名称及等级排位顺序') }}
        </div>
        <el-button type="primary" size="small" :icon="Plus" @click="openAddRole">
          {{ t('admin.addRole', '新增职级') }}
        </el-button>
      </div>

      <el-table :data="rolesList" stripe style="width: 100%" size="small" border>
        <el-table-column prop="level" :label="t('admin.roleLevel', '等级排位')" width="100" align="center">
          <template #default="{ row }">
            <span class="level-pill" :class="getLevelClass(row.level)">L{{ row.level }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" :label="t('admin.roleName', '职级名称')" min-width="140">
          <template #default="{ row }">
            <strong>{{ row.name }}</strong>
            <div v-if="row.name_en" style="font-size: 12px; color: var(--el-text-color-secondary);">{{ row.name_en }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="code" :label="t('admin.roleCode', '编码')" width="120" />
        <el-table-column :label="t('admin.canManageUsers', '权限范围')" min-width="200">
          <template #default="{ row }">
            <div style="display: flex; gap: 4px; flex-wrap: wrap;">
              <el-tag v-if="row.can_view_all_docs" type="warning" size="small" effect="plain">跨部门监管/审批</el-tag>
              <el-tag v-if="row.can_manage_users" type="success" size="small" effect="plain">成员管理</el-tag>
              <el-tag v-if="row.can_manage_depts" type="primary" size="small" effect="plain">部门管理</el-tag>
              <span v-if="!row.can_view_all_docs && !row.can_manage_users && !row.can_manage_depts" style="color: var(--el-text-color-placeholder); font-size: 12px;">常规业务操作</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="user_count" :label="t('admin.memberCount', '成员数')" width="80" align="center" />
        <el-table-column :label="t('common.actions')" width="140" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="openEditRole(row)">{{ t('common.edit') }}</el-button>
            <el-button 
              type="danger" 
              link 
              size="small" 
              :disabled="row.is_system || row.code === 'super_admin' || row.user_count > 0"
              @click="handleDeleteRole(row)"
            >
              {{ t('common.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <template #footer>
        <el-button @click="roleManagementDialogVisible = false">{{ t('common.close', '关闭') }}</el-button>
      </template>
    </el-dialog>

    <!-- ── Add / Edit Role Dialog ─────────────────────────────────────────────── -->
    <el-dialog 
      v-model="roleEditDialogVisible" 
      :title="isEditRole ? t('admin.editRole', '编辑职级') : t('admin.addRole', '新增职级')" 
      width="520px" 
      class="custom-dialog"
      destroy-on-close
    >
      <el-form :model="roleForm" label-width="140px" style="padding: 10px 10px 0;">
        <el-form-item :label="t('admin.roleName', '职级名称') + ' (ZH)'" required>
          <el-input v-model="roleForm.name" placeholder="例如：技术总监 / 区域副总裁" />
        </el-form-item>
        <el-form-item :label="t('admin.roleNameEn', '英文名称') + ' (EN)'">
          <el-input v-model="roleForm.name_en" placeholder="e.g. Technical Director / VP" />
        </el-form-item>
        <el-form-item v-if="!isEditRole" :label="t('admin.roleCode', '职级编码')">
          <el-input v-model="roleForm.code" placeholder="例如：director / vp（留空自动生成）" />
        </el-form-item>
        <el-form-item :label="t('admin.roleLevel', '权限等级排位')" required>
          <el-input-number v-model="roleForm.level" :min="1" :max="99" style="width: 150px;" />
          <div style="font-size: 12px; color: var(--el-text-color-secondary); margin-top: 4px;">
            {{ t('admin.roleLevelTip', '等级数值越大代表权限与层级越高。100为超级管理员，50为部门经理基准线。') }}
          </div>
        </el-form-item>
        <el-form-item :label="t('admin.roleDesc', '职级描述')">
          <el-input v-model="roleForm.description" type="textarea" :rows="2" placeholder="填写该职级的业务职责说明..." />
        </el-form-item>
        <el-form-item :label="t('admin.canViewAllDocs', '跨部门全局监管')">
          <el-switch v-model="roleForm.can_view_all_docs" />
        </el-form-item>
        <el-form-item :label="t('admin.canManageUsers', '成员管理权限')">
          <el-switch v-model="roleForm.can_manage_users" />
        </el-form-item>
        <el-form-item :label="t('admin.canManageDepts', '部门管理权限')">
          <el-switch v-model="roleForm.can_manage_depts" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="roleEditDialogVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="roleSubmitLoading" @click="submitRoleForm">{{ t('common.ok') }}</el-button>
      </template>
    </el-dialog>

    <!-- ── Add / Edit Department Dialog ──────────────────────────────────────── -->
    <el-dialog v-model="deptDialogVisible" :title="t('admin.addDept', 'Add New Department')" width="450px" class="custom-dialog">
      <el-form label-width="120px" style="padding: 10px 10px 0;">
        <el-form-item :label="t('common.name') + ' (ZH)'" required>
          <el-input v-model="newDeptName" placeholder="例如：总经办 / 研发中心" />
        </el-form-item>
        <el-form-item :label="t('common.name') + ' (EN)'">
          <el-input v-model="newDeptNameEn" placeholder="e.g. Executive Office / R&D Center" />
        </el-form-item>
        <el-form-item :label="t('admin.parentDept', '上级部门')">
          <el-select v-model="newDeptParentId" clearable :placeholder="t('admin.parentDeptPlaceholder', '请选择上级部门（可选）')" style="width: 100%">
            <el-option 
              v-for="d in availableParentDeptOptions" 
              :key="d.id" 
              :label="formatDeptDisplayName(d)" 
              :value="d.id" 
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('admin.roleLevel', '层级排位')">
          <el-input-number v-model="newDeptLevel" :min="1" :max="maxManageableDeptLevel" style="width: 150px;" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="deptDialogVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="deptLoading" @click="createDept">{{ t('common.ok') }}</el-button>
      </template>
    </el-dialog>

    <!-- ── Add / Edit User Dialog ─────────────────────────────────────────────── -->
    <el-dialog v-model="userDialogVisible" :title="isEdit ? t('profile.editUser') : t('admin.addUser')" width="600px" custom-class="spacious-dialog">
      <el-form :model="userForm" label-width="140px" style="padding: 10px 20px;">
        <el-form-item :label="t('profile.loginName')" required>
          <el-input v-model="userForm.login_name" :disabled="isEdit && editingUserId === auth.user?.id && auth.user?.is_super_admin" />
        </el-form-item>
        <el-form-item :label="t('profile.password')" :required="!isEdit">
          <el-input v-model="userForm.password" type="password" show-password :placeholder="isEdit ? '留空保持原密码不变' : '请输入密码'" />
        </el-form-item>
        <el-form-item :label="t('profile.employeeNo', '员工编号')" required>
          <div style="width: 100%; display: flex; flex-direction: column; gap: 4px;">
            <div style="display: flex; gap: 8px; align-items: center; width: 100%;">
              <el-input 
                v-model="userForm.employee_no" 
                :placeholder="t('admin.autoGeneratedNo', '系统随所选职级自动生成')" 
                readonly
                style="flex: 1;"
              >
                <template #prefix>
                  <span style="font-size: 13px; margin-right: 2px;">🏷️</span>
                </template>
              </el-input>
              <el-tooltip content="根据当前选定职级重新计算并分配最新可用工号" placement="top">
                <el-button 
                  circle 
                  size="small" 
                  :icon="Refresh" 
                  :loading="generatingEmpNo" 
                  @click="fetchAutoEmployeeNo()" 
                />
              </el-tooltip>
              <el-tag type="success" effect="plain" size="small" style="font-weight: 600;">
                ✨ 系统自动生成
              </el-tag>
            </div>
            <div style="font-size: 12px; color: var(--el-text-color-secondary); line-height: 1.4;">
              💡 员工编号根据分配的职级等级自动生成（如普通员工 EMP、经理 MGR、总监 DIR、管理中心 ADM），权限变更时编号智能联动更新。
            </div>
          </div>
        </el-form-item>
        <el-form-item :label="t('profile.firstName')" required>
          <el-input v-model="userForm.first_name" />
        </el-form-item>
        <el-form-item :label="t('profile.lastName')" required>
          <el-input v-model="userForm.last_name" />
        </el-form-item>
        <el-form-item v-if="auth.user?.is_super_admin || auth.user?.is_manager || (auth.user?.role_level && auth.user?.role_level >= 50)" :label="t('profile.dept')" required>
          <el-select v-model="userForm.department_id" style="width: 100%" :placeholder="t('profile.selectDept', '请选择所属部门')">
            <el-option 
              v-for="d in availableParentDeptOptions" 
              :key="d.id" 
              :label="formatDeptDisplayName(d)" 
              :value="d.id" 
            />
          </el-select>
        </el-form-item>

        <el-form-item :label="t('admin.assignRole', '角色与职级')" required>
          <div style="width: 100%;">
            <el-tooltip 
              v-if="isEditingSelf || isEditingSuperiorOrEqual" 
              :content="isEditingSelf ? '🛡️ 安全规范：禁止修改自己的角色与权限等级' : '🛡️ 安全规范：禁止修改同级或上级人员的角色职级'" 
              placement="top"
            >
              <div style="width: 100%;">
                <el-select v-model="userForm.role_id" style="width: 100%" :disabled="true" :placeholder="t('admin.assignRole')">
                  <el-option 
                    v-for="r in rolesList" 
                    :key="r.id" 
                    :label="`${r.name} (等级 L${r.level})${r.description ? ' - ' + r.description : ''}`" 
                    :value="r.id" 
                  />
                </el-select>
              </div>
            </el-tooltip>
            <el-select 
              v-else 
              v-model="userForm.role_id" 
              style="width: 100%" 
              :placeholder="t('admin.assignRole')"
              @change="onRoleChange"
            >
              <el-option 
                v-for="r in availableRolesForAssign" 
                :key="r.id" 
                :label="`${r.name} (等级 L${r.level})${r.description ? ' - ' + r.description : ''}`" 
                :value="r.id" 
              />
            </el-select>
            <div v-if="isEditingSelf || isEditingSuperiorOrEqual" style="font-size: 12px; color: #e6a23c; margin-top: 5px; display: flex; align-items: center; gap: 4px;">
              <span>🛡️ {{ isEditingSelf ? '按系统安全规范，成员无法更改自己的权限等级' : '按系统安全规范，无法更改同级或上级人员的权限等级' }}</span>
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <div style="padding: 10px 20px;">
          <el-button @click="userDialogVisible = false">{{ t('common.cancel') }}</el-button>
          <el-button type="primary" :loading="userLoading" @click="createUser">{{ t('common.ok') }}</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from "vue";
import { useI18n } from "vue-i18n";
import api from "@/api/client";
import { 
  Plus, Delete, Edit, User, Search, Setting, List, Share,
  ZoomIn, ZoomOut, Aim, FolderOpened, Folder, FullScreen,
  Switch, Key, UserFilled, Refresh, Sort
} from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useAuthStore } from "@/stores/auth";
import OrgTreeNode, { type OrgTreeNodeData, type TreeDropPayload } from "@/components/OrgTreeNode.vue";

const { t, locale, te } = useI18n();
const auth = useAuthStore();
const viewMode = ref<"list" | "chart">("chart");
const users = ref<any[]>([]);
const rolesList = ref<any[]>([]);
const deptOptions = ref<any[]>([]);

// 💡 列表模式排序状态
const sortBy = ref<string>("level");
const sortOrder = ref<string>("desc");
const sortOption = ref<string>("level_desc");

// 💡 基础成员管理编辑权限判断（经理以上或角色等级>=50）
const canManageUsers = computed(() => {
  return Boolean(
    auth.user?.is_super_admin || 
    auth.user?.is_manager || 
    (auth.user?.role_level && auth.user?.role_level >= 50)
  );
});

const formatDeptName = (name: string, nameEn?: string) => {
  if (!name) return "";
  if (te(`dept.${name}`)) return t(`dept.${name}`);
  if (nameEn && te(`dept.${nameEn}`)) return t(`dept.${nameEn}`);
  return locale.value === 'zh-CN' ? name : (nameEn || name);
};

const formatDeptDisplayName = (d: any) => {
  const base = formatDeptName(d.name, d.name_en);
  if (d.parent_name) {
    return `${base} (上级: ${formatDeptName(d.parent_name)})`;
  }
  return base;
};

function getRoleTagType(row: any) {
  const level = row.role_level ?? (row.is_super_admin ? 100 : (row.is_manager ? 50 : 10));
  if (level >= 100 || row.is_super_admin) return "danger";
  if (level >= 80) return "warning";
  if (level >= 50 || row.is_manager) return "success";
  return "info";
}

function getLevelClass(level?: number) {
  if (!level) return "level-staff";
  if (level >= 100) return "level-admin";
  if (level >= 80) return "level-director";
  if (level >= 50) return "level-manager";
  return "level-staff";
}

// ══════════════ 组织架构关系树数据模型与构建 (Tree Structure) ══════════════
const treeZoomScale = ref(1.0);
const panTranslateX = ref(0);
const panTranslateY = ref(0);
const isCanvasPanning = ref(false);
let panStartX = 0;
let panStartY = 0;
let panInitialX = 0;
let panInitialY = 0;

const canvasViewportRef = ref<HTMLElement | null>(null);
const canvasStageRef = ref<HTMLElement | null>(null);

const draggedTreeNode = ref<OrgTreeNodeData | null>(null);
const draggedMember = ref<{ member: any; sourceNode: OrgTreeNodeData } | null>(null);
const collapsedNodeIds = ref<Set<string | number>>(new Set());

const allUsers = ref<any[]>([]);

async function loadAllUsers() {
  try {
    const { data } = await api.get("/users", {
      params: { size: 1000 }
    });
    allUsers.value = data.items || [];
  } catch (err) {
    console.error("Failed to load all users", err);
  }
}

const currentUsersList = computed(() => {
  return allUsers.value.length > 0 ? allUsers.value : users.value;
});

const deptMembersDrawerVisible = ref(false);
const selectedDeptForMembers = ref<any>(null);

const deptMembersList = computed(() => {
  if (!selectedDeptForMembers.value) return [];
  if (selectedDeptForMembers.value.type === 'root') {
    // 💡 仅展示属于最高决策中心/未分配下级部门的直属成员，不再包含下级各部门人员
    return currentUsersList.value.filter(u => !u.department_id || !deptOptions.value.some(d => d.id === u.department_id));
  }
  const deptId = Number(selectedDeptForMembers.value.id);
  return currentUsersList.value.filter(u => u.department_id === deptId);
});

const currentSelectedDept = computed(() => {
  if (!selectedDeptForMembers.value) return null;
  if (selectedDeptForMembers.value.type === 'root') {
    const rootMembers = currentUsersList.value.filter(u => !u.department_id || !deptOptions.value.some(d => d.id === u.department_id));
    const leader = rootMembers.find(u => u.is_super_admin) || currentUsersList.value.find(u => u.is_super_admin);
    const rootTitle = locale.value === 'zh-CN' ? '企业最高管理与决策中心 (Board & Executive)' : 'Executive Governance Center';
    const rootLeaderRole = locale.value === 'zh-CN' ? '系统最高决策者' : (leader?.role_name_en || 'System Super Administrator');
    const rootBoardName = locale.value === 'zh-CN' ? '系统最高决策委员会' : 'Executive Governance Board';
    return {
      id: 'root-decision',
      name: rootTitle,
      name_en: 'Executive Governance Center',
      type: 'root',
      level: 100,
      leaderName: leader ? `${leader.display_name} (${rootLeaderRole})` : rootBoardName,
      memberCount: rootMembers.length
    };
  }
  const deptId = Number(selectedDeptForMembers.value.id);
  const dept = deptOptions.value.find(d => d.id === deptId);
  const deptUsers = currentUsersList.value.filter(u => u.department_id === deptId);
  let leader = deptUsers.find(u => u.is_manager || u.is_super_admin);
  if (!leader && deptUsers.length > 0) {
    leader = [...deptUsers].sort((a, b) => (b.role_level || 0) - (a.role_level || 0))[0];
  }
  const leaderRole = leader ? (locale.value === 'zh-CN' ? (leader.role_name || t('admin.supervisor')) : (leader.role_name_en || leader.role_name || t('admin.supervisor'))) : '';
  return {
    id: deptId,
    name: dept ? formatDeptName(dept.name, dept.name_en) : selectedDeptForMembers.value.name,
    name_en: dept?.name_en || selectedDeptForMembers.value.name_en,
    type: 'dept',
    level: dept?.level || selectedDeptForMembers.value.level || 50,
    leaderName: leader ? `${leader.display_name} (${leaderRole})` : t('admin.unassigned', '主管未指定'),
    memberCount: deptUsers.length
  };
});

const isCurrentDeptManageable = computed(() => {
  if (!selectedDeptForMembers.value) return false;
  if (auth.user?.is_super_admin || (auth.user?.role_level && auth.user?.role_level >= 100)) return true;
  if (!auth.user?.is_manager && !(auth.user?.role_level && auth.user?.role_level >= 50)) return false;
  if (selectedDeptForMembers.value.type === 'root') return false;
  
  const targetId = Number(selectedDeptForMembers.value.id);
  const myDeptId = auth.user?.department_id;
  if (!myDeptId) return false;
  if (targetId === myDeptId) return true;
  
  // 递归检查是否属于当前主管管辖的下属子部门
  const getSubDeptIds = (pId: number): number[] => {
    const directChildren = deptOptions.value.filter(d => d.parent_id === pId).map(d => d.id);
    let all = [...directChildren];
    for (const cId of directChildren) {
      all = all.concat(getSubDeptIds(cId));
    }
    return all;
  };
  const myScope = getSubDeptIds(myDeptId);
  return myScope.includes(targetId);
});

const availableParentDeptOptions = computed(() => {
  if (auth.user?.is_super_admin || (auth.user?.role_level && auth.user?.role_level >= 100)) {
    return deptOptions.value;
  }
  const myDeptId = auth.user?.department_id;
  if (!myDeptId) return [];
  const getSubDeptIds = (pId: number): number[] => {
    const directChildren = deptOptions.value.filter(d => d.parent_id === pId).map(d => d.id);
    let all = [...directChildren];
    for (const cId of directChildren) {
      all = all.concat(getSubDeptIds(cId));
    }
    return all;
  };
  const scopeIds = [myDeptId, ...getSubDeptIds(myDeptId)];
  return deptOptions.value.filter(d => scopeIds.includes(d.id));
});

const maxManageableDeptLevel = computed(() => {
  if (auth.user?.is_super_admin || (auth.user?.role_level && auth.user?.role_level >= 100)) {
    return 99;
  }
  return auth.user?.role_level ? Math.min(99, auth.user.role_level) : (auth.user?.is_manager ? 50 : 40);
});

// ── 画布平移与缩放边界限制逻辑 ───────────────────────────────────────
function clampPan(x: number, y: number): { x: number; y: number } {
  if (!canvasViewportRef.value || !canvasStageRef.value) return { x, y };
  const vpWidth = canvasViewportRef.value.clientWidth || 1000;
  const vpHeight = canvasViewportRef.value.clientHeight || 600;
  const stageW = (canvasStageRef.value.scrollWidth || 1200) * treeZoomScale.value;
  const stageH = (canvasStageRef.value.scrollHeight || 700) * treeZoomScale.value;

  // 限制左右平移最大距离，确保树形内容始终停留在可视区域内
  const limitX = Math.max(260, (stageW + vpWidth) / 2 - 200);
  const limitTop = 160; // 限制顶部最多向下偏移 160px
  const limitBottom = Math.max(200, (stageH + vpHeight) / 2 - 120); // 限制底部最多向上偏移

  const clampedX = Math.max(-limitX, Math.min(limitX, x));
  const clampedY = Math.max(-limitBottom, Math.min(limitTop, y));
  return { x: clampedX, y: clampedY };
}

function onCanvasMouseDown(e: MouseEvent) {
  // If user clicked inside an interactive button, modal, or node card, don't pan canvas
  const target = e.target as HTMLElement;
  if (target.closest('.org-tree-node-card') || target.closest('.el-button') || target.closest('.collapse-toggle-btn') || target.closest('.canvas-floating-controls')) {
    return;
  }
  if (e.button !== 0 && e.button !== 1) return; // Left or Middle click

  isCanvasPanning.value = true;
  panStartX = e.clientX;
  panStartY = e.clientY;
  panInitialX = panTranslateX.value;
  panInitialY = panTranslateY.value;

  window.addEventListener('mousemove', onCanvasMouseMove);
  window.addEventListener('mouseup', onCanvasMouseUp);
}

function onCanvasMouseMove(e: MouseEvent) {
  if (!isCanvasPanning.value) return;
  const dx = e.clientX - panStartX;
  const dy = e.clientY - panStartY;
  const clamped = clampPan(panInitialX + dx, panInitialY + dy);
  panTranslateX.value = Math.round(clamped.x);
  panTranslateY.value = Math.round(clamped.y);
}

function onCanvasMouseUp() {
  isCanvasPanning.value = false;
  window.removeEventListener('mousemove', onCanvasMouseMove);
  window.removeEventListener('mouseup', onCanvasMouseUp);
}

function onCanvasWheel(e: WheelEvent) {
  if (e.ctrlKey || e.metaKey) {
    const delta = e.deltaY < 0 ? 0.08 : -0.08;
    zoomTree(delta);
  } else {
    let nextX = panTranslateX.value;
    let nextY = panTranslateY.value;
    if (e.shiftKey) {
      nextX -= e.deltaY;
    } else {
      nextX -= e.deltaX;
      nextY -= e.deltaY;
    }
    const clamped = clampPan(nextX, nextY);
    panTranslateX.value = clamped.x;
    panTranslateY.value = clamped.y;
  }
}

function zoomTree(delta: number) {
  treeZoomScale.value = Math.min(2.0, Math.max(0.25, Number((treeZoomScale.value + delta).toFixed(2))));
  const clamped = clampPan(panTranslateX.value, panTranslateY.value);
  panTranslateX.value = clamped.x;
  panTranslateY.value = clamped.y;
}

function resetTreeZoom() {
  treeZoomScale.value = 1.0;
  panTranslateX.value = 0;
  panTranslateY.value = 0;
}

function fitTreeToScreen() {
  if (!canvasViewportRef.value || !canvasStageRef.value) return;
  const vpWidth = canvasViewportRef.value.clientWidth - 100;
  const stageWidth = canvasStageRef.value.scrollWidth || 1400;
  if (stageWidth > vpWidth && vpWidth > 200) {
    const scale = Math.max(0.35, Math.min(1.0, Number((vpWidth / stageWidth).toFixed(2))));
    treeZoomScale.value = scale;
  } else {
    treeZoomScale.value = 1.0;
  }
  panTranslateX.value = 0;
  panTranslateY.value = 0;
}

onUnmounted(() => {
  window.removeEventListener('mousemove', onCanvasMouseMove);
  window.removeEventListener('mouseup', onCanvasMouseUp);
  window.removeEventListener('dragend', handleTreeDragEnd);
});

function expandAllNodes() {
  collapsedNodeIds.value.clear();
}

function collapseAllNodes() {
  const set = new Set<string | number>();
  deptOptions.value.forEach(d => {
    const hasKids = deptOptions.value.some(c => c.parent_id === d.id);
    if (hasKids) set.add(d.id);
  });
  collapsedNodeIds.value = set;
}

function handleToggleCollapse(node: OrgTreeNodeData) {
  if (collapsedNodeIds.value.has(node.id)) {
    collapsedNodeIds.value.delete(node.id);
  } else {
    collapsedNodeIds.value.add(node.id);
  }
}

// ── 拓扑树快速查找与聚焦定位功能 (Department Finder & Spotlight) ──────
const searchDeptId = ref<number | string | null>(null);
const highlightedSearchDeptId = ref<number | string | null>(null);
let highlightTimer: any = null;

function onClearSearchDept() {
  searchDeptId.value = null;
  highlightedSearchDeptId.value = null;
  if (highlightTimer) clearTimeout(highlightTimer);
}

function locateDepartment(deptId: number | string | null) {
  if (!deptId) {
    highlightedSearchDeptId.value = null;
    return;
  }
  const targetId = Number(deptId);
  const dept = deptOptions.value.find(d => d.id === targetId);
  if (!dept) return;

  // 1. 递归展开目标部门的所有祖先节点，确保不会因为被父节点折叠而隐藏
  const expandAncestors = (pId: number | null) => {
    if (!pId) return;
    collapsedNodeIds.value.delete(pId);
    const parent = deptOptions.value.find(d => d.id === pId);
    if (parent && parent.parent_id) {
      expandAncestors(parent.parent_id);
    }
  };
  if (dept.parent_id) {
    expandAncestors(dept.parent_id);
  }

  // 2. 赋予醒目的高亮脉冲光晕动画
  highlightedSearchDeptId.value = targetId;
  if (highlightTimer) clearTimeout(highlightTimer);
  highlightTimer = setTimeout(() => {
    highlightedSearchDeptId.value = null;
  }, 4500);

  // 3. 在下一个渲染周期平滑居中平移画布到该部门卡片
  nextTick(() => {
    setTimeout(() => {
      const cardEl = document.getElementById(`org-node-${targetId}`);
      if (cardEl && canvasViewportRef.value) {
        const vpRect = canvasViewportRef.value.getBoundingClientRect();
        const cardRect = cardEl.getBoundingClientRect();

        const cardCenterX = cardRect.left + cardRect.width / 2;
        const cardCenterY = cardRect.top + cardRect.height / 2;
        const vpCenterX = vpRect.left + vpRect.width / 2;
        const vpCenterY = vpRect.top + vpRect.height / 2;

        const deltaX = vpCenterX - cardCenterX;
        const deltaY = vpCenterY - cardCenterY;

        const nextX = panTranslateX.value + deltaX;
        const nextY = panTranslateY.value + deltaY;
        const clamped = clampPan(nextX, nextY);

        panTranslateX.value = Math.round(clamped.x);
        panTranslateY.value = Math.round(clamped.y);

        ElMessage.success(`🎯 已成功定位至【${dept.name}】！`);
      } else {
        ElMessage.success(`🎯 已选中【${dept.name}】！`);
      }
    }, 60);
  });
}

const orgTreeData = computed<OrgTreeNodeData>(() => {
  // 1. Build map of department user count and supervisors
  const deptUsersMap = new Map<number, any[]>();
  currentUsersList.value.forEach(u => {
    if (u.department_id) {
      if (!deptUsersMap.has(u.department_id)) deptUsersMap.set(u.department_id, []);
      deptUsersMap.get(u.department_id)!.push(u);
    }
  });

  // 2. Map all departments into raw OrgTreeNodeData
  const nodeMap = new Map<number, OrgTreeNodeData>();
  deptOptions.value.forEach(d => {
    const deptUsers = deptUsersMap.get(d.id) || [];
    // Find leader: manager, super_admin, or highest role_level
    let leader = deptUsers.find(u => u.is_manager || u.is_super_admin);
    if (!leader && deptUsers.length > 0) {
      leader = [...deptUsers].sort((a, b) => (b.role_level || 0) - (a.role_level || 0))[0];
    }

    const leaderRole = leader ? (locale.value === 'zh-CN' ? (leader.role_name || t('admin.supervisor')) : (leader.role_name_en || leader.role_name || t('admin.supervisor'))) : '';
    nodeMap.set(d.id, {
      id: d.id,
      name: formatDeptName(d.name, d.name_en),
      name_en: d.name_en,
      type: 'dept',
      level: d.level || 50,
      parentId: d.parent_id || null,
      leaderName: leader ? `${leader.display_name} (${leaderRole})` : undefined,
      memberCount: deptUsers.length,
      members: deptUsers,
      children: [],
      collapsed: collapsedNodeIds.value.has(d.id),
      raw: d
    });
  });

  // 3. Assemble parent-child tree relationships
  const rootDepts: OrgTreeNodeData[] = [];
  nodeMap.forEach(node => {
    if (node.parentId && nodeMap.has(node.parentId)) {
      const parent = nodeMap.get(node.parentId)!;
      parent.children.push(node);
    } else {
      rootDepts.push(node);
    }
  });

  // Sort children by level desc then name
  nodeMap.forEach(node => {
    node.children.sort((a, b) => (b.level - a.level) || a.name.localeCompare(b.name));
  });
  rootDepts.sort((a, b) => (b.level - a.level) || a.name.localeCompare(b.name));

  // 4. Create Top Root Node: 企业最高管理与决策中心
  // 💡 根节点仅包含未分配到下级具体部门或直属最高决策层的成员
  const rootMembers = currentUsersList.value.filter(u => !u.department_id || !deptOptions.value.some(d => d.id === u.department_id));
  const rootLeader = rootMembers.find(u => u.is_super_admin) || currentUsersList.value.find(u => u.is_super_admin);
  const rootRoleLabel = locale.value === 'zh-CN' ? '系统最高决策者' : (rootLeader?.role_name_en || 'System Super Administrator');
  const rootBoardLabel = locale.value === 'zh-CN' ? '系统最高决策委员会' : 'Executive Governance Board';
  const rootNodeTitle = locale.value === 'zh-CN' ? '企业最高管理与决策中心 (Board & Executive)' : 'Executive Governance Center';
  const rootNode: OrgTreeNodeData = {
    id: 'root-decision',
    name: rootNodeTitle,
    name_en: 'Executive Governance Center',
    type: 'root',
    level: 100,
    parentId: null,
    leaderName: rootLeader ? `${rootLeader.display_name} (${rootRoleLabel})` : rootBoardLabel,
    memberCount: rootMembers.length,
    members: rootMembers,
    children: rootDepts,
    collapsed: collapsedNodeIds.value.has('root-decision'),
    raw: null
  };

  return rootNode;
});

// ── Tree Drag & Drop Handlers ─────────────────────────────────
function handleTreeDragStart(node: OrgTreeNodeData, _e: DragEvent) {
  draggedTreeNode.value = node;
  draggedMember.value = null;
}

function handleTreeDragEnd() {
  draggedTreeNode.value = null;
  draggedMember.value = null;
}

function handleTreeDragOver(_node: OrgTreeNodeData, _e: DragEvent) {
  // Handled inside OrgTreeNode
}

function handleTreeDragLeave(_node: OrgTreeNodeData, _e: DragEvent) {
  // Handled inside OrgTreeNode
}

function handleMemberDragStart(member: any, sourceNode: OrgTreeNodeData, _e: DragEvent) {
  draggedMember.value = { member, sourceNode };
  draggedTreeNode.value = null;
}

async function handleMemberDrop({ member, sourceNode, targetNode }: { member: any; sourceNode: OrgTreeNodeData; targetNode: OrgTreeNodeData }) {
  draggedMember.value = null;
  if (!member || !targetNode) return;
  if (sourceNode.id === targetNode.id) return;

  const targetDeptId = targetNode.type === 'root' ? null : Number(targetNode.id);
  try {
    await api.patch(`/users/${member.id}`, {
      department_id: targetDeptId
    });

    // 💡 Optimistic UI update: instantly move member to new department in local allUsers cache
    const u = allUsers.value.find(user => user.id === member.id);
    if (u) {
      u.department_id = targetDeptId;
      u.department_name = targetNode.type === 'root' ? null : targetNode.name;
    }

    ElMessage.success(`🎉 已成功将【${member.display_name}】从【${sourceNode.name}】调动至【${targetNode.name}】！`);
    await Promise.all([loadAllUsers(), loadUsers(), loadDepts()]);
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || t('common.failed'));
  }
}

async function handleTreeDrop(payload: TreeDropPayload | OrgTreeNodeData) {
  let targetNode: OrgTreeNodeData;
  let position: 'above' | 'peer' | 'below' = 'below';
  if ('targetNode' in payload) {
    targetNode = payload.targetNode;
    position = payload.position || 'below';
  } else {
    targetNode = payload;
  }

  const source = draggedTreeNode.value;
  draggedTreeNode.value = null;
  if (!source) return;
  if (source.id === targetNode.id) return;
  if (source.type === 'root') return;

  const sourceDeptId = Number(source.id);
  const targetDeptId = Number(targetNode.id);

  // 1. 如果放置到顶级组织决策中心（Root）上：调整为一级部门（Level 50）
  if (targetNode.type === 'root') {
    try {
      await api.patch(`/users/departments/${sourceDeptId}`, { parent_id: null, level: 50 });
      ElMessage.success(`已将【${source.name}】调整为一级职能部门（Level 50）！`);
      await Promise.all([loadDepts(), loadAllUsers(), loadUsers()]);
    } catch (err: any) {
      ElMessage.error(err.response?.data?.error || t('common.failed'));
    }
    return;
  }

  // 2. ↔️ 平行位置（peer）：与目标部门保持同级平行关系，享有相同的上级部门及完全一致的 Level（如 Level 50）
  if (position === 'peer') {
    try {
      const targetParentId = targetNode.parentId ? Number(targetNode.parentId) : null;
      const peerLevel = targetNode.level || 50;
      await api.patch(`/users/departments/${sourceDeptId}`, {
        parent_id: targetParentId,
        level: peerLevel
      });
      ElMessage.success(`已将【${source.name}】调整为与【${targetNode.name}】同级的平行部门（保持 Level ${peerLevel}）！`);
      await Promise.all([loadDepts(), loadAllUsers(), loadUsers()]);
    } catch (err: any) {
      ElMessage.error(err.response?.data?.error || t('common.failed'));
    }
    return;
  }

  // 3. 🔼 上方位置（above）：成为目标部门的上级领导部门
  if (position === 'above') {
    try {
      const oldTargetParentId = targetNode.parentId ? Number(targetNode.parentId) : null;
      const targetLevel = targetNode.level || 50;
      const newLeaderLevel = Math.min(90, targetLevel + 10);

      // 第一步：将当前部门挂接至目标部门原本的上级位置，并赋予更高的层级
      await api.patch(`/users/departments/${sourceDeptId}`, {
        parent_id: oldTargetParentId,
        level: newLeaderLevel
      });
      // 第二步：将目标部门的上级变更为当前部门
      await api.patch(`/users/departments/${targetDeptId}`, {
        parent_id: sourceDeptId,
        level: targetLevel
      });

      ElMessage.success(`已成功将【${source.name}】设置为【${targetNode.name}】的上级领导部门！`);
      await Promise.all([loadDepts(), loadAllUsers(), loadUsers()]);
    } catch (err: any) {
      ElMessage.error(err.response?.data?.error || t('common.failed'));
    }
    return;
  }

  // 4. 🔽 下方位置（below）：成为目标部门的下属部门 / 协作团队
  if (position === 'below') {
    const targetLvl = targetNode.level || 50;
    const newSubLvl = Math.max(10, targetLvl - 10);

    try {
      await api.patch(`/users/departments/${sourceDeptId}`, {
        parent_id: targetDeptId,
        level: newSubLvl
      });
      ElMessage.success(`已成功将【${source.name}】调整为【${targetNode.name}】的下级部门（Level ${newSubLvl}）！`);
      await Promise.all([loadDepts(), loadAllUsers(), loadUsers()]);
    } catch (err: any) {
      ElMessage.error(err.response?.data?.error || t('common.failed'));
    }
    return;
  }
}

async function onDropCanvasBackground(_e: DragEvent) {
  const source = draggedTreeNode.value;
  draggedTreeNode.value = null;
  if (!source || source.type === 'root') return;
  if (!auth.user?.is_super_admin) {
    ElMessage.warning('仅系统最高决策者有权将部门提升为顶层一级部门');
    return;
  }

  // 拖放到空白画布背景上，自动平移为一级职能部门（Level 50）
  try {
    await api.patch(`/users/departments/${source.id}`, { parent_id: null, level: 50 });
    ElMessage.success(`已将【${source.name}】移至一级职能部门（Level 50）！`);
    await Promise.all([loadDepts(), loadAllUsers(), loadUsers()]);
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || t('common.failed'));
  }
}

function handleAddChildDept(parentNode: OrgTreeNodeData) {
  if (parentNode.type === 'root') {
    openAddDeptModal(null, 50);
  } else {
    openAddDeptModal(Number(parentNode.id), Math.max(10, (parentNode.level || 50) - 10));
  }
}

function handleEditDeptNode(node: OrgTreeNodeData) {
  if (node.type === 'root') return;
  const dept = deptOptions.value.find(d => d.id === node.id);
  if (dept) {
    newDeptName.value = dept.name;
    newDeptNameEn.value = dept.name_en || "";
    newDeptParentId.value = dept.parent_id || null;
    newDeptLevel.value = dept.level || 50;
    editingDeptId.value = dept.id;
    deptDialogVisible.value = true;
  }
}

async function handleDeleteDeptNode(node: OrgTreeNodeData) {
  const dept = deptOptions.value.find(d => d.id === node.id);
  if (dept) {
    deleteSpecificDept(dept);
  }
}

function handleViewDeptMembers(node: OrgTreeNodeData) {
  selectedDeptForMembers.value = node;
  deptMembersDrawerVisible.value = true;
  loadAllUsers();
}

function openAddUserForCurrentDept() {
  if (!selectedDeptForMembers.value) return;
  isEdit.value = false;
  editingUserId.value = null;
  const defaultRole = rolesList.value.find(r => r.code === "staff") || rolesList.value[rolesList.value.length - 1];
  const targetDeptId = selectedDeptForMembers.value.type === 'root' ? null : Number(selectedDeptForMembers.value.id);
  userForm.value = {
    login_name: "",
    password: "",
    employee_no: "",
    first_name: "",
    last_name: "",
    department_id: targetDeptId,
    role_id: defaultRole?.id ?? null
  };
  if (defaultRole) {
    fetchAutoEmployeeNo(defaultRole.id);
  }
  userDialogVisible.value = true;
}

// ── 调入成员逻辑 (Transfer In) ────────────────────────────────
const transferInDialogVisible = ref(false);
const transferUserIds = ref<number[]>([]);
const transferLoading = ref(false);

const availableUsersForTransfer = computed(() => {
  if (!selectedDeptForMembers.value) return [];
  const targetDeptId = selectedDeptForMembers.value.type === 'root' ? null : Number(selectedDeptForMembers.value.id);
  return currentUsersList.value.filter(u => u.department_id !== targetDeptId);
});

function openTransferUserDialog() {
  transferUserIds.value = [];
  transferInDialogVisible.value = true;
}

async function submitTransferIn() {
  if (!selectedDeptForMembers.value || transferUserIds.value.length === 0) return;
  transferLoading.value = true;
  try {
    const targetDeptId = selectedDeptForMembers.value.type === 'root' ? null : Number(selectedDeptForMembers.value.id);
    for (const uid of transferUserIds.value) {
      await api.patch(`/users/${uid}`, { department_id: targetDeptId });
      const u = allUsers.value.find(user => user.id === uid);
      if (u) {
        u.department_id = targetDeptId;
      }
    }
    ElMessage.success(`已成功调入 ${transferUserIds.value.length} 名成员！`);
    transferInDialogVisible.value = false;
    transferUserIds.value = [];
    await Promise.all([loadAllUsers(), loadUsers(), loadDepts()]);
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || t('common.failed'));
  } finally {
    transferLoading.value = false;
  }
}

// ── 调离部门逻辑 (Transfer Out) ────────────────────────────────
const transferOutDialogVisible = ref(false);
const userToTransferOut = ref<any>(null);
const targetDeptForTransfer = ref<number | null>(null);

function openTransferUserOut(user: any) {
  userToTransferOut.value = user;
  targetDeptForTransfer.value = null;
  transferOutDialogVisible.value = true;
}

async function submitTransferUserOut() {
  if (!userToTransferOut.value) return;
  try {
    const targetDept = targetDeptForTransfer.value;
    await api.patch(`/users/${userToTransferOut.value.id}`, {
      department_id: targetDept
    });
    const u = allUsers.value.find(user => user.id === userToTransferOut.value.id);
    if (u) {
      u.department_id = targetDept;
    }
    ElMessage.success(`已将【${userToTransferOut.value.display_name}】调动至目标部门！`);
    transferOutDialogVisible.value = false;
    await Promise.all([loadAllUsers(), loadUsers(), loadDepts()]);
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || t('common.failed'));
  }
}

// ── 设为主管 / 取消主管 (Toggle Supervisor) ───────────────────
async function toggleUserSupervisor(user: any) {
  if (user.id === auth.user?.id) {
    return ElMessage.warning("🛡️ 安全规范：无法更改自己的主管权限");
  }
  if (isUserSuperiorOrEqual(user)) {
    return ElMessage.warning("🛡️ 安全规范：无法更改同级或上级人员的主管权限");
  }
  const newIsManager = !user.is_manager;
  try {
    const managerRole = rolesList.value.find(r => r.level >= 50 && r.level < 100) || rolesList.value[0];
    const staffRole = rolesList.value.find(r => r.code === "staff") || rolesList.value[rolesList.value.length - 1];
    
    await api.patch(`/users/${user.id}`, {
      is_manager: newIsManager,
      role_id: newIsManager ? managerRole?.id : staffRole?.id
    });
    ElMessage.success(newIsManager ? `已成功将【${user.display_name}】设为部门主管！` : `已取消【${user.display_name}】的主管身份`);
    await Promise.all([loadUsers(), loadAllUsers(), loadDepts()]);
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || t('common.failed'));
  }
}

// ══════════════ 职级配置 Modal 与表单逻辑 ══════════════
const roleManagementDialogVisible = ref(false);
const roleEditDialogVisible = ref(false);
const isEditRole = ref(false);
const editingRoleId = ref<number | null>(null);
const roleSubmitLoading = ref(false);
const roleForm = ref({
  name: "",
  name_en: "",
  code: "",
  level: 10,
  description: "",
  can_manage_users: false,
  can_manage_depts: false,
  can_view_all_docs: false
});

async function loadRoles() {
  try {
    const { data } = await api.get("/users/roles");
    rolesList.value = data || [];
  } catch (err) {
    console.error("Failed to load roles", err);
  }
}

function openRoleManagement() {
  loadRoles();
  roleManagementDialogVisible.value = true;
}

function openAddRole() {
  isEditRole.value = false;
  editingRoleId.value = null;
  roleForm.value = {
    name: "",
    name_en: "",
    code: "",
    level: 20,
    description: "",
    can_manage_users: false,
    can_manage_depts: false,
    can_view_all_docs: false
  };
  roleEditDialogVisible.value = true;
}

function openEditRole(role: any) {
  isEditRole.value = true;
  editingRoleId.value = role.id;
  roleForm.value = {
    name: role.name,
    name_en: role.name_en || "",
    code: role.code,
    level: role.level || 10,
    description: role.description || "",
    can_manage_users: Boolean(role.can_manage_users),
    can_manage_depts: Boolean(role.can_manage_depts),
    can_view_all_docs: Boolean(role.can_view_all_docs)
  };
  roleEditDialogVisible.value = true;
}

async function submitRoleForm() {
  if (!roleForm.value.name || !roleForm.value.code) {
    return ElMessage.warning(t("admin.fillRequired", "请填写完整的职级名称和英文标识代码"));
  }
  roleSubmitLoading.value = true;
  try {
    if (isEditRole.value && editingRoleId.value) {
      await api.patch(`/users/roles/${editingRoleId.value}`, roleForm.value);
      ElMessage.success(t("admin.roleUpdated", "职级信息更新成功"));
    } else {
      await api.post("/users/roles", roleForm.value);
      ElMessage.success(t("admin.roleCreated", "新职级创建成功"));
    }
    roleEditDialogVisible.value = false;
    await loadRoles();
    await loadUsers();
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || t('common.failed'));
  } finally {
    roleSubmitLoading.value = false;
  }
}

async function handleDeleteRole(role: any) {
  try {
    await ElMessageBox.confirm(
      t('admin.deleteRoleConfirm', `确定要删除职级 "${role.name}" 吗？`),
      t('common.warning'),
      { type: 'warning', confirmButtonClass: 'el-button--danger' }
    );
    await api.delete(`/users/roles/${role.id}`);
    ElMessage.success(t('admin.roleDeleted', '职级删除成功'));
    loadRoles();
    loadUsers();
  } catch (err: any) {
    if (err !== 'cancel') {
      ElMessage.error(err.response?.data?.error || t('common.failed'));
    }
  }
}

const availableRolesForAssign = computed(() => {
  if (auth.user?.is_super_admin) {
    return rolesList.value;
  }
  const myLevel = auth.user?.role_level ?? (auth.user?.is_manager ? 50 : 10);
  return rolesList.value.filter(r => r.level < myLevel);
});

const isEditingSelf = computed(() => {
  return isEdit.value && editingUserId.value === auth.user?.id;
});

function isUserSuperiorOrEqual(targetUser: any): boolean {
  if (!targetUser) return false;
  if (targetUser.id === auth.user?.id) return false; // Self handled separately
  // Super admin can manage lower-level staff, but not another super admin (level 100)
  if (auth.user?.is_super_admin) {
    const isTargetSuper = targetUser.is_super_admin || targetUser.role_level >= 100;
    return Boolean(isTargetSuper && targetUser.id !== auth.user?.id);
  }
  const myLevel = auth.user?.role_level ?? (auth.user?.is_manager ? 50 : 10);
  const targetLevel = targetUser.is_super_admin ? 100 : (targetUser.role_level ?? (targetUser.is_manager ? 50 : 10));
  return targetLevel >= myLevel;
}

const isEditingSuperiorOrEqual = computed(() => {
  if (!isEdit.value || !editingUserId.value) return false;
  if (isEditingSelf.value) return true;
  const target = currentUsersList.value.find(u => u.id === editingUserId.value) || users.value.find(u => u.id === editingUserId.value);
  if (!target) return false;
  return isUserSuperiorOrEqual(target);
});

async function handleResetPassword(user: any) {
  try {
    const { value: newPassword } = await ElMessageBox.prompt(
      t('admin.newPassHint'),
      t('admin.resetPassTitle'),
      {
        confirmButtonText: t('common.ok'),
        cancelButtonText: t('common.cancel'),
        inputType: 'password'
      }
    );
    
    if (newPassword) {
      await api.post(`/users/${user.id}/reset-password`, { password: newPassword });
      ElMessage.success(t('common.success'));
    }
  } catch (err) {
    // Cancelled
  }
}

// ══════════════ 基础成员与部门管理数据 ══════════════
const total = ref(0);
const loading = ref(false);
const currentPage = ref(1);
const pageSize = ref(15);
const searchQuery = ref("");
const filterDept = ref<number | null>(null);
const filterRole = ref<number | null>(null);
const selectedIds = ref<number[]>([]);

let searchTimer: any = null;
function handleSearch() {
  if (searchTimer) clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    currentPage.value = 1;
    loadUsers();
  }, 400);
}

const isEdit = ref(false);
const editingUserId = ref<number | null>(null);
const deptDialogVisible = ref(false);
const deptLoading = ref(false);
const newDeptName = ref("");
const newDeptNameEn = ref("");
const newDeptParentId = ref<number | null>(null);
const newDeptLevel = ref<number>(50);

const userDialogVisible = ref(false);
const userLoading = ref(false);
const userForm = ref({
  login_name: "",
  password: "",
  employee_no: "",
  first_name: "",
  last_name: "",
  department_id: null as number | null,
  role_id: null as number | null
});

const editingDeptId = ref<number | null>(null);

async function loadDepts() {
  const { data } = await api.get("/users/departments");
  deptOptions.value = data || [];
}

function openAddDeptModal(parentId: number | null = null, defaultLevel: number = 50) {
  editingDeptId.value = null;
  newDeptName.value = "";
  newDeptNameEn.value = "";
  newDeptParentId.value = parentId;
  newDeptLevel.value = defaultLevel;
  deptDialogVisible.value = true;
}

const generatingEmpNo = ref(false);

async function fetchAutoEmployeeNo(roleId?: number) {
  const targetRoleId = roleId || userForm.value.role_id;
  if (!targetRoleId) return;
  generatingEmpNo.value = true;
  try {
    const { data } = await api.get("/users/generate-employee-no", {
      params: {
        role_id: targetRoleId,
        exclude_user_id: isEdit.value ? (editingUserId.value ?? undefined) : undefined
      }
    });
    if (data.employee_no) {
      userForm.value.employee_no = data.employee_no;
    }
  } catch (err) {
    console.error("Failed to auto-generate employee number", err);
  } finally {
    generatingEmpNo.value = false;
  }
}

function onRoleChange(newRoleId: number) {
  fetchAutoEmployeeNo(newRoleId);
}

function openAddUser() {
  isEdit.value = false;
  editingUserId.value = null;
  const defaultRole = rolesList.value.find(r => r.code === "staff") || rolesList.value[rolesList.value.length - 1];
  userForm.value = {
    login_name: "",
    password: "",
    employee_no: "",
    first_name: "",
    last_name: "",
    department_id: auth.user?.is_super_admin ? null : (auth.user?.department_id ?? null),
    role_id: defaultRole?.id ?? null
  };
  if (defaultRole) {
    fetchAutoEmployeeNo(defaultRole.id);
  }
  userDialogVisible.value = true;
}

function editUser(row: any) {
  isEdit.value = true;
  editingUserId.value = row.id;
  userForm.value = {
    login_name: row.login_name,
    password: "",
    employee_no: row.employee_no,
    first_name: row.display_name.split(' ')[1] || row.display_name,
    last_name: row.display_name.split(' ')[0] || "",
    department_id: row.department_id,
    role_id: row.role_id || (rolesList.value.find(r => r.level === row.role_level)?.id ?? null)
  };
  userDialogVisible.value = true;
}

async function handleDeleteUser(user: any) {
  try {
    await ElMessageBox.confirm(
      t('admin.deleteUserConfirm', `确定要删除成员【${user.display_name}】吗？此操作不可撤销。`),
      t('common.warning'),
      { 
        type: 'warning', 
        confirmButtonClass: 'el-button--danger',
        confirmButtonText: t('common.ok', '确定'),
        cancelButtonText: t('common.cancel', '取消')
      }
    );
    await api.delete(`/users/${user.id}`);
    ElMessage.success(t('common.success'));
    await Promise.all([loadUsers(), loadAllUsers(), loadDepts()]);
  } catch (err: any) {
    if (err !== 'cancel' && err !== 'close') {
      ElMessage.error(err.response?.data?.error || t('common.failed'));
    }
  }
}

async function createUser() {
  if (!userForm.value.department_id && auth.user?.department_id) {
    userForm.value.department_id = auth.user.department_id;
  }
  const isDeptMissing = auth.user?.is_super_admin && !userForm.value.department_id;
  if (!userForm.value.login_name || (!isEdit.value && !userForm.value.password) || isDeptMissing) {
    return ElMessage.warning("Please fill required fields");
  }
  userLoading.value = true;
  try {
    if (isEdit.value && editingUserId.value) {
      await api.patch(`/users/${editingUserId.value}`, userForm.value);
    } else {
      await api.post("/users", userForm.value);
    }
    ElMessage.success(t('common.success'));
    userDialogVisible.value = false;
    await Promise.all([loadUsers(), loadAllUsers(), loadRoles(), loadDepts()]);
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || t('common.failed'));
  } finally {
    userLoading.value = false;
  }
}

function handleSortSelectChange(val: string) {
  if (!val) {
    sortBy.value = "level";
    sortOrder.value = "desc";
    sortOption.value = "level_desc";
  } else {
    const parts = val.split("_");
    const ord = parts.pop() as "asc" | "desc";
    const field = parts.join("_");
    sortBy.value = field;
    sortOrder.value = ord;
  }
  currentPage.value = 1;
  loadUsers();
}

function handleTableSortChange({ prop, order }: { prop: string; order: "ascending" | "descending" | null }) {
  if (!order || !prop) {
    sortBy.value = "level";
    sortOrder.value = "desc";
    sortOption.value = "level_desc";
  } else {
    const ord = order === "ascending" ? "asc" : "desc";
    let field = prop;
    if (prop === "role_level" || prop === "role_name") field = "level";
    if (prop === "department_name") field = "department";
    if (prop === "display_name") field = "name";
    if (prop === "employee_no") field = "employee_no";

    sortBy.value = field;
    sortOrder.value = ord;
    sortOption.value = `${field}_${ord}`;
  }
  currentPage.value = 1;
  loadUsers();
}

async function loadUsers() {
  loading.value = true;
  try {
    const { data } = await api.get("/users", {
      params: { 
        page: currentPage.value, 
        size: pageSize.value,
        management: 1,
        search: searchQuery.value,
        department_id: filterDept.value,
        role_id: filterRole.value,
        sort_by: sortBy.value,
        order: sortOrder.value
      }
    });
    users.value = data.items || [];
    total.value = data.total || 0;
  } finally {
    loading.value = false;
  }
}

function handleSelectionChange(items: any[]) {
  selectedIds.value = items.map(u => u.id);
}

async function handleBatchDelete() {
  try {
    await ElMessageBox.confirm(
      t('editor.deleteUserConfirm'),
      t('common.warning'),
      { type: 'warning' }
    );
    const { data } = await api.post("/users/batch-delete", { user_ids: selectedIds.value });
    ElMessage.success(data.message);
    await Promise.all([loadUsers(), loadAllUsers()]);
  } catch {}
}

async function createDept() {
  if (!newDeptName.value.trim()) return;
  deptLoading.value = true;
  try {
    if (editingDeptId.value) {
      await api.patch(`/users/departments/${editingDeptId.value}`, {
        name: newDeptName.value.trim(),
        name_en: newDeptNameEn.value.trim(),
        parent_id: newDeptParentId.value,
        level: newDeptLevel.value
      });
      ElMessage.success('部门信息更新成功');
    } else {
      await api.post("/users/departments", { 
        name: newDeptName.value.trim(),
        name_en: newDeptNameEn.value.trim(),
        parent_id: newDeptParentId.value || undefined,
        level: newDeptLevel.value
      });
      ElMessage.success(t('common.success'));
    }
    deptDialogVisible.value = false;
    editingDeptId.value = null;
    newDeptName.value = "";
    newDeptNameEn.value = "";
    newDeptParentId.value = null;
    newDeptLevel.value = 50;
    await Promise.all([loadDepts(), loadUsers(), loadAllUsers()]);
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || t('common.failed'));
  } finally {
    deptLoading.value = false;
  }
}

async function deleteSpecificDept(dept: any) {
  try {
    await ElMessageBox.confirm(
      `确定要删除部门 "${formatDeptName(dept.name)}" 吗？只能删除没有成员的空部门。`,
      t('common.warning'),
      { type: 'warning', confirmButtonClass: 'el-button--danger' }
    );
    await api.delete(`/users/departments/${dept.id}`);
    ElMessage.success(t('common.success'));
    await Promise.all([loadDepts(), loadUsers(), loadAllUsers()]);
  } catch (err: any) {
    if (err !== 'cancel') {
      ElMessage.error(err.response?.data?.error || t('common.failed'));
    }
  }
}

async function handleDeleteDept() {
  if (!filterDept.value) return;
  try {
    await ElMessageBox.confirm(
      t('admin.deleteDeptConfirm'),
      t('common.warning'),
      { type: 'warning', confirmButtonClass: 'el-button--danger' }
    );
    await api.delete(`/users/departments/${filterDept.value}`);
    ElMessage.success(t('common.success'));
    filterDept.value = null;
    await Promise.all([loadDepts(), loadUsers(), loadAllUsers()]);
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || t('common.failed'));
  }
}

onMounted(() => {
  loadUsers();
  loadAllUsers();
  loadDepts();
  loadRoles();
  window.addEventListener('dragend', handleTreeDragEnd);
});
</script>

<style scoped>
.user-mgmt-page {
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

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
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

.view-mode-toggle {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  padding: 2px;
}

.role-mgmt-btn {
  background: rgba(255, 255, 255, 0.2) !important;
  color: #fff !important;
  border: 1px solid rgba(255, 255, 255, 0.4) !important;
  backdrop-filter: blur(8px);
  font-weight: 600;
  transition: all 0.2s ease;
}

.role-mgmt-btn:hover {
  background: #fff !important;
  color: var(--el-color-primary) !important;
}

/* ── 列表模式卡片 ────────────────────────────────────────── */
.mgmt-card {
  border-radius: 16px;
  padding: 8px;
}

.mgmt-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  gap: 16px;
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.search-input {
  width: 240px;
}

.filter-select {
  width: 180px;
}

.pagination {
  margin-top: 24px;
  display: flex;
  justify-content: flex-end;
}

/* ══════════════ 组织架构树 (Tree Data Structure View) ══════════════ */
.org-tree-view-wrapper {
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border-radius: 16px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
  overflow: hidden;
  min-height: calc(100vh - 210px);
}

.tree-controls-toolbar {
  padding: 14px 24px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.toolbar-left-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.tree-badge-title {
  font-size: 15px;
  font-weight: 800;
  color: #0f172a;
}

.tree-sub-tip {
  font-size: 12px;
  color: #475569;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  padding: 4px 10px;
  border-radius: 6px;
}

.toolbar-right-tools {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.dept-search-locator {
  display: flex;
  align-items: center;
}

.tree-search-select {
  width: 220px;
}

.search-dept-option-row {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
}

.search-opt-icon {
  font-size: 14px;
}

.search-opt-name {
  font-weight: 600;
  color: #1e293b;
  max-width: 130px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.search-opt-parent {
  font-size: 11px;
  color: #64748b;
  max-width: 90px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.search-opt-tag {
  margin-left: auto;
  font-weight: 700;
  font-size: 10px;
  height: 18px;
  line-height: 16px;
  padding: 0 4px;
}

.tree-canvas-viewport {
  flex: 1;
  position: relative;
  overflow: hidden;
  padding: 0;
  background: radial-gradient(circle, #cbd5e1 1.2px, transparent 1.2px);
  background-size: 24px 24px;
  background-color: #f8fafc;
  min-height: 640px;
  cursor: grab;
  user-select: none;
}

.tree-canvas-viewport.is-panning {
  cursor: grabbing !important;
}

.tree-canvas-stage {
  position: absolute;
  top: 40px;
  left: 50%;
  display: inline-flex;
  justify-content: center;
  align-items: flex-start;
  padding-bottom: 80px;
  transition: transform 0.05s ease-out;
  transform-origin: top center;
  will-change: transform;
}

.canvas-floating-controls {
  position: absolute;
  bottom: 24px;
  right: 24px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid #e2e8f0;
  padding: 6px 8px;
  border-radius: 30px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  display: flex;
  gap: 6px;
  align-items: center;
  z-index: 100;
  backdrop-filter: blur(8px);
}

/* ── Department Members Drawer Styles ────────────────────────── */
.dept-drawer-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dept-summary-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 16px;
}

.summary-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.dept-big-title {
  font-size: 17px;
  font-weight: 800;
  color: #0f172a;
}

.summary-meta {
  display: flex;
  gap: 20px;
  font-size: 13px;
  color: #475569;
}

.user-row-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-avatar-small {
  width: 32px;
  height: 32px;
  border-radius: 16px;
  background: var(--el-color-primary);
  color: #ffffff;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.user-cell-name {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
  display: flex;
  align-items: center;
}

.user-cell-sub {
  font-size: 11px;
  color: #94a3b8;
}

.dept-title-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.summary-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.drawer-row-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}
.level-pill {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 10px;
  margin-left: 6px;
  vertical-align: middle;
}

.level-admin {
  background: #fee2e2;
  color: #b91c1c;
  border: 1px solid #fca5a5;
}

.level-director {
  background: #fef3c7;
  color: #b45309;
  border: 1px solid #fcd34d;
}

.level-manager {
  background: #dcfce7;
  color: #15803d;
  border: 1px solid #86efac;
}

.level-staff {
  background: #f3f4f6;
  color: #4b5563;
  border: 1px solid #e5e7eb;
}
</style>
