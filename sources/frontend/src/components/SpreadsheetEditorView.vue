<template>
  <div 
    class="spreadsheet-editor-root" 
    v-loading="loading"
    @mouseup="onGlobalMouseUp"
    @keydown="onGlobalKeyDown"
    tabindex="0"
    ref="rootContainerRef"
  >
    <!-- 1. Clean Modern Header Bar (No deep green, standard clean UI) -->
    <div class="header-bar">
      <div class="header-left">
        <el-tooltip :content="t('common.back', '返回上一页')" placement="bottom" :show-after="400">
          <el-button class="back-btn" :icon="Back" @click="goBack" :disabled="isGeneratingTitle">
            {{ t('common.back', '返回') }}
          </el-button>
        </el-tooltip>
        
        <el-input 
          v-model="title" 
          class="title-input"
          :disabled="!canEdit || isGeneratingTitle" 
          @blur="saveTitle"
          :placeholder="t('common.untitled', '未命名表格')"
        />

        <el-tooltip :content="t('editor.aiGenerateTitleTip', 'AI 智能识别表格内容，提炼并自动填写精炼标题')" placement="bottom" :show-after="300">
          <el-button 
            v-if="canEdit"
            type="success" 
            plain 
            size="small"
            :loading="isGeneratingTitle"
            :disabled="isGeneratingTitle"
            @click="handleGenerateTitle"
            style="margin-left: 8px; font-weight: 500;"
          >
            <el-icon v-if="!isGeneratingTitle" style="margin-right: 4px;"><MagicStick /></el-icon>
            {{ isGeneratingTitle ? t('editor.aiGeneratingTitle', 'AI 提炼中...') : t('editor.aiGenerateTitle', 'AI 生成标题') }}
          </el-button>
        </el-tooltip>

        <el-tag type="success" effect="plain" class="doc-type-badge">
          Excel 表格
        </el-tag>

        <el-tag :type="statusTagType" class="status-tag">
          {{ statusLabel }}
        </el-tag>

        <span class="save-status-text">{{ saveHint }}</span>
      </div>

      <div class="header-right">
        <!-- Online Collaborators Avatars -->
        <div class="collab-avatars" v-if="collabUsers.length">
          <el-tooltip v-for="u in collabUsers" :key="u.id" :content="u.name" placement="bottom">
            <div class="avatar-dot" :style="{ backgroundColor: u.color }">
              {{ u.name.charAt(0).toUpperCase() }}
            </div>
          </el-tooltip>
        </div>

        <!-- Approval Shortcuts for Approvers -->
        <div v-if="meta.can_approve" class="approval-shortcuts">
          <el-button type="success" size="small" @click="handleApprove">{{ t("inbox.approve", "同意") }}</el-button>
          <el-button type="danger" size="small" @click="handleReject">{{ t("inbox.reject", "驳回") }}</el-button>
        </div>

        <!-- AI Assistant Button -->
        <el-button 
          type="primary" 
          class="ai-header-btn"
          size="small"
          @click="openAiDrawer('chat')"
        >
          <svg class="svg-icon sparkle-icon" viewBox="0 0 24 24" width="14" height="14">
            <path fill="currentColor" d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8L12 2z"/>
          </svg>
          {{ t('editor.sheetAi.copilotBtn', 'AI 助手') }}
        </el-button>

        <!-- Save Button -->
        <el-button 
          v-if="canEdit" 
          type="primary" 
          size="small" 
          :icon="Check" 
          :loading="saving" 
          @click="saveNow"
        >
          {{ t('editor.save', '保存') }}
        </el-button>

        <!-- Actions Dropdown -->
        <el-dropdown trigger="click">
          <el-button size="small">
            {{ t("editor.actions", "操作") }} <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-if="canEdit && meta.status === 'draft'" @click="showApprovalDialog = true">
                <el-icon><Promotion /></el-icon> {{ t("editor.startApproval", "发起审批") }}
              </el-dropdown-item>
              <el-dropdown-item v-if="meta.can_manage_permissions" @click="showShareDialog = true">
                <el-icon><Share /></el-icon> {{ t("library.share", "共享与权限") }}
              </el-dropdown-item>
              <el-dropdown-item @click="openVersionHistory">
                <el-icon><Document /></el-icon> {{ t("editor.versionHistory", "版本历史") }}
              </el-dropdown-item>
              <el-dropdown-item @click="printSpreadsheet">
                <el-icon><Printer /></el-icon> 打印表格
              </el-dropdown-item>
              <el-dropdown-item @click="handleExportExcel">
                <el-icon><Download /></el-icon> {{ t("editor.exportXlsx", "导出 Excel (.xlsx)") }}
              </el-dropdown-item>
              <el-dropdown-item v-if="isOwner || isAdmin" divided style="color: var(--el-color-danger)" @click="confirmDeleteDoc">
                <el-icon><Delete /></el-icon> {{ t("editor.delete", "删除表格") }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <!-- 2. Ribbon Tabs Header Navigation -->
    <div class="ribbon-tabs-nav">
      <button 
        class="ribbon-tab-btn" 
        :class="{ active: activeRibbonTab === 'home' }"
        @click="activeRibbonTab = 'home'"
      >
        开始
      </button>
      <button 
        class="ribbon-tab-btn" 
        :class="{ active: activeRibbonTab === 'insert' }"
        @click="activeRibbonTab = 'insert'"
      >
        插入
      </button>
      <button 
        class="ribbon-tab-btn" 
        :class="{ active: activeRibbonTab === 'formulas' }"
        @click="activeRibbonTab = 'formulas'"
      >
        公式
      </button>
      <button 
        class="ribbon-tab-btn" 
        :class="{ active: activeRibbonTab === 'data' }"
        @click="activeRibbonTab = 'data'"
      >
        数据
      </button>
      <button 
        class="ribbon-tab-btn" 
        :class="{ active: activeRibbonTab === 'view' }"
        @click="activeRibbonTab = 'view'"
      >
        视图
      </button>
      <button 
        class="ribbon-tab-btn ai-tab-btn" 
        :class="{ active: activeRibbonTab === 'ai' }"
        @click="activeRibbonTab = 'ai'"
      >
        <svg class="svg-icon" viewBox="0 0 24 24" width="13" height="13" style="margin-right: 3px;">
          <path fill="currentColor" d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8L12 2z"/>
        </svg>
        AI 助手
      </button>
    </div>

    <!-- 3. Ribbon Content Panel with Grouped Functional Blocks -->
    <div class="ribbon-content-panel" v-if="canEdit">

      <!-- ── Tab 1: 开始 (Home) ── -->
      <div v-show="activeRibbonTab === 'home'" class="ribbon-tab-pane">
        
        <!-- Group 1: 剪贴板 (Clipboard) -->
        <div class="ribbon-group">
          <div class="group-controls-row">
            <!-- Big Paste Button -->
            <button class="ribbon-big-btn" @click="handlePasteSelection" title="粘贴 (Ctrl+V)">
              <svg class="svg-icon big-icon" viewBox="0 0 24 24" width="22" height="22">
                <path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>
                <rect x="8" y="2" width="8" height="4" rx="1" ry="1" fill="none" stroke="currentColor" stroke-width="1.8"/>
              </svg>
              <span>粘贴</span>
            </button>

            <!-- Small Cut, Copy, Format Painter Stack -->
            <div class="ribbon-small-stack">
              <button class="ribbon-mini-btn" @click="handleCutSelection" title="剪切 (Ctrl+X)">
                <svg class="svg-icon" viewBox="0 0 24 24" width="14" height="14">
                  <circle cx="6" cy="6" r="3" fill="none" stroke="currentColor" stroke-width="1.8"/>
                  <circle cx="6" cy="18" r="3" fill="none" stroke="currentColor" stroke-width="1.8"/>
                  <line x1="8.59" y1="7.41" x2="20" y2="18.82" stroke="currentColor" stroke-width="1.8"/>
                  <line x1="8.59" y1="16.59" x2="20" y2="5.18" stroke="currentColor" stroke-width="1.8"/>
                </svg>
                <span>剪切</span>
              </button>
              <button class="ribbon-mini-btn" @click="handleCopySelection" title="复制 (Ctrl+C)">
                <svg class="svg-icon" viewBox="0 0 24 24" width="14" height="14">
                  <rect x="9" y="9" width="13" height="13" rx="2" fill="none" stroke="currentColor" stroke-width="1.8"/>
                  <path fill="none" stroke="currentColor" stroke-width="1.8" d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                </svg>
                <span>复制</span>
              </button>
              <button class="ribbon-mini-btn" :class="{ active: isFormatPainting }" @click="toggleFormatPainter" title="格式刷">
                <svg class="svg-icon" viewBox="0 0 24 24" width="14" height="14">
                  <path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" d="M18.37 2.63L14 7l3 3 4.37-4.37a2.12 2.12 0 1 0-3-3zM14 7L4 17l-1 4 4-1 10-10"/>
                </svg>
                <span>格式刷</span>
              </button>
            </div>
          </div>
          <div class="group-label">剪贴板</div>
        </div>

        <div class="ribbon-divider"></div>

        <!-- Group 2: 字体 (Font) -->
        <div class="ribbon-group">
          <div class="group-controls-col">
            <!-- Row 1: Font Family & Size -->
            <div class="sub-row">
              <el-select v-model="currentFontFamily" size="small" style="width: 105px" @change="setFontFamily">
                <el-option label="宋体" value="SimSun, serif" />
                <el-option label="微软雅黑" value="Microsoft YaHei, sans-serif" />
                <el-option label="Arial" value="Arial, sans-serif" />
                <el-option label="Times New Roman" value="'Times New Roman', serif" />
                <el-option label="Consolas" value="Consolas, monospace" />
              </el-select>

              <el-select v-model="currentFontSize" size="small" style="width: 68px" @change="setFontSize">
                <el-option v-for="sz in [9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 36]" :key="sz" :label="`${sz}`" :value="sz" />
              </el-select>

              <button class="ribbon-btn-square" @click="stepFontSize(1)" title="增大字号">A<sup>+</sup></button>
              <button class="ribbon-btn-square" @click="stepFontSize(-1)" title="减小字号">A<sup>-</sup></button>
            </div>

            <!-- Row 2: Styles, Borders, Colors -->
            <div class="sub-row">
              <button class="ribbon-btn-square" :class="{ active: currentCellStyle.bl }" @click="toggleStyle('bl')" title="加粗 (Ctrl+B)">
                <b>B</b>
              </button>
              <button class="ribbon-btn-square" :class="{ active: currentCellStyle.it }" @click="toggleStyle('it')" title="倾斜 (Ctrl+I)">
                <i>I</i>
              </button>
              <button class="ribbon-btn-square" :class="{ active: currentCellStyle.un }" @click="toggleStyle('un')" title="下划线 (Ctrl+U)">
                <u>U</u>
              </button>
              <button class="ribbon-btn-square" :class="{ active: currentCellStyle.cl }" @click="toggleStyle('cl')" title="删除线">
                <s>S</s>
              </button>

              <!-- Borders Dropdown -->
              <el-dropdown trigger="click" @command="applyBorder">
                <button class="ribbon-btn-square dropdown-sq-btn" title="边框设置">
                  <svg class="svg-icon" viewBox="0 0 24 24" width="14" height="14">
                    <rect x="3" y="3" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8"/>
                    <line x1="3" y1="12" x2="21" y2="12" stroke="currentColor" stroke-width="1.2"/>
                    <line x1="12" y1="3" x2="12" y2="21" stroke="currentColor" stroke-width="1.2"/>
                  </svg>
                  <el-icon class="sub-arrow"><ArrowDown /></el-icon>
                </button>
                <template #dropdown>
                  <el-dropdown-menu class="border-dropdown-menu">
                    <el-dropdown-item command="all">所有框线</el-dropdown-item>
                    <el-dropdown-item command="thick">粗外侧框线</el-dropdown-item>
                    <el-dropdown-item command="outer">外侧框线</el-dropdown-item>
                    <el-dropdown-item command="top" divided>上框线</el-dropdown-item>
                    <el-dropdown-item command="bottom">下框线</el-dropdown-item>
                    <el-dropdown-item command="left">左框线</el-dropdown-item>
                    <el-dropdown-item command="right">右框线</el-dropdown-item>
                    <el-dropdown-item command="none" divided style="color: #f56c6c;">无框线</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>

              <!-- Background Color Picker -->
              <div class="ribbon-color-btn" title="填充颜色">
                <svg class="svg-icon" viewBox="0 0 24 24" width="14" height="14">
                  <path fill="none" stroke="currentColor" stroke-width="1.8" d="M19 11L13 5 4.5 13.5c-.8.8-.8 2.2 0 3l3 3c.8.8 2.2.8 3 0L19 11z"/>
                  <path fill="currentColor" d="M19 15a3 3 0 1 1-3 3"/>
                </svg>
                <span class="color-stripe" :style="{ backgroundColor: currentCellStyle.bg || '#ffffff' }"></span>
                <input type="color" :value="currentCellStyle.bg || '#ffffff'" @change="e => setCellColor('bg', (e.target as HTMLInputElement).value)" class="native-color-inp" />
              </div>

              <!-- Font Color Picker -->
              <div class="ribbon-color-btn" title="字体颜色">
                <span class="font-color-char">A</span>
                <span class="color-stripe" :style="{ backgroundColor: currentCellStyle.fc || '#000000' }"></span>
                <input type="color" :value="currentCellStyle.fc || '#000000'" @change="e => setCellColor('fc', (e.target as HTMLInputElement).value)" class="native-color-inp" />
              </div>
            </div>
          </div>
          <div class="group-label">字体</div>
        </div>

        <div class="ribbon-divider"></div>

        <!-- Group 3: 对齐方式 (Alignment) -->
        <div class="ribbon-group">
          <div class="group-controls-col">
            <!-- Row 1: Vertical Align & Wrap Text -->
            <div class="sub-row">
              <button class="ribbon-btn-square" :class="{ active: currentCellStyle.vt === 'top' }" @click="setCellVAlign('top')" title="顶部对齐">
                <svg class="svg-icon" viewBox="0 0 24 24" width="14" height="14">
                  <line x1="4" y1="4" x2="20" y2="4" stroke="currentColor" stroke-width="2"/>
                  <rect x="8" y="8" width="8" height="10" fill="none" stroke="currentColor" stroke-width="1.5"/>
                </svg>
              </button>
              <button class="ribbon-btn-square" :class="{ active: currentCellStyle.vt === 'middle' || !currentCellStyle.vt }" @click="setCellVAlign('middle')" title="垂直居中">
                <svg class="svg-icon" viewBox="0 0 24 24" width="14" height="14">
                  <line x1="4" y1="12" x2="20" y2="12" stroke="currentColor" stroke-width="2"/>
                  <rect x="8" y="6" width="8" height="12" fill="none" stroke="currentColor" stroke-width="1.5"/>
                </svg>
              </button>
              <button class="ribbon-btn-square" :class="{ active: currentCellStyle.vt === 'bottom' }" @click="setCellVAlign('bottom')" title="底部对齐">
                <svg class="svg-icon" viewBox="0 0 24 24" width="14" height="14">
                  <line x1="4" y1="20" x2="20" y2="20" stroke="currentColor" stroke-width="2"/>
                  <rect x="8" y="6" width="8" height="10" fill="none" stroke="currentColor" stroke-width="1.5"/>
                </svg>
              </button>

              <button class="ribbon-mini-btn" :class="{ active: currentCellStyle.tb === 1 }" @click="toggleTextWrap" title="自动换行" style="margin-left: 6px;">
                <svg class="svg-icon" viewBox="0 0 24 24" width="14" height="14">
                  <line x1="3" y1="6" x2="21" y2="6" stroke="currentColor" stroke-width="1.8"/>
                  <path fill="none" stroke="currentColor" stroke-width="1.8" d="M3 12h14a3 3 0 0 1 0 6H13"/>
                  <polyline points="15 15 12 18 15 21" stroke="currentColor" stroke-width="1.8" fill="none"/>
                </svg>
                <span>自动换行</span>
              </button>
            </div>

            <!-- Row 2: Horizontal Align & Merge -->
            <div class="sub-row">
              <button class="ribbon-btn-square" :class="{ active: currentCellStyle.ht === 'left' }" @click="setCellAlign('left')" title="左对齐">
                <svg class="svg-icon" viewBox="0 0 24 24" width="14" height="14">
                  <line x1="4" y1="6" x2="20" y2="6" stroke="currentColor" stroke-width="1.8"/>
                  <line x1="4" y1="12" x2="14" y2="12" stroke="currentColor" stroke-width="1.8"/>
                  <line x1="4" y1="18" x2="18" y2="18" stroke="currentColor" stroke-width="1.8"/>
                </svg>
              </button>
              <button class="ribbon-btn-square" :class="{ active: currentCellStyle.ht === 'center' }" @click="setCellAlign('center')" title="居中对齐">
                <svg class="svg-icon" viewBox="0 0 24 24" width="14" height="14">
                  <line x1="4" y1="6" x2="20" y2="6" stroke="currentColor" stroke-width="1.8"/>
                  <line x1="7" y1="12" x2="17" y2="12" stroke="currentColor" stroke-width="1.8"/>
                  <line x1="5" y1="18" x2="19" y2="18" stroke="currentColor" stroke-width="1.8"/>
                </svg>
              </button>
              <button class="ribbon-btn-square" :class="{ active: currentCellStyle.ht === 'right' }" @click="setCellAlign('right')" title="右对齐">
                <svg class="svg-icon" viewBox="0 0 24 24" width="14" height="14">
                  <line x1="4" y1="6" x2="20" y2="6" stroke="currentColor" stroke-width="1.8"/>
                  <line x1="10" y1="12" x2="20" y2="12" stroke="currentColor" stroke-width="1.8"/>
                  <line x1="6" y1="18" x2="20" y2="18" stroke="currentColor" stroke-width="1.8"/>
                </svg>
              </button>

              <button class="ribbon-mini-btn" :class="{ active: isCurrentSelectionMerged }" @click="toggleMergeCells" title="合并后居中" style="margin-left: 6px;">
                <svg class="svg-icon" viewBox="0 0 24 24" width="14" height="14">
                  <rect x="3" y="5" width="18" height="14" rx="1" fill="none" stroke="currentColor" stroke-width="1.8"/>
                  <line x1="9" y1="12" x2="15" y2="12" stroke="currentColor" stroke-width="2"/>
                  <polyline points="11 10 9 12 11 14" stroke="currentColor" stroke-width="1.5" fill="none"/>
                  <polyline points="13 10 15 12 13 14" stroke="currentColor" stroke-width="1.5" fill="none"/>
                </svg>
                <span>{{ isCurrentSelectionMerged ? '取消合并' : '合并居中' }}</span>
              </button>
            </div>
          </div>
          <div class="group-label">对齐方式</div>
        </div>

        <div class="ribbon-divider"></div>

        <!-- Group 4: 数字 (Number) -->
        <div class="ribbon-group">
          <div class="group-controls-col">
            <div class="sub-row">
              <el-select v-model="currentNumFormat" size="small" style="width: 130px" @change="applyNumberFormat">
                <el-option label="常规" value="general" />
                <el-option label="数值" value="number" />
                <el-option label="货币 (¥)" value="currency_cny" />
                <el-option label="百分比 (%)" value="percent" />
                <el-option label="千分位逗号" value="comma" />
                <el-option label="短日期 (YYYY-MM-DD)" value="date" />
                <el-option label="文本" value="text" />
              </el-select>
            </div>
            <div class="sub-row">
              <button class="ribbon-btn-square" @click="applyNumberFormat('currency_cny')" title="货币 (¥)">
                <b>¥</b>
              </button>
              <button class="ribbon-btn-square" @click="applyNumberFormat('percent')" title="百分比 (%)">
                <b>%</b>
              </button>
              <button class="ribbon-btn-square" @click="applyNumberFormat('comma')" title="千分位 (,)">
                <b>,</b>
              </button>
              <button class="ribbon-btn-square" @click="applyNumberFormat('inc_decimal')" title="增加小数位数">
                .00<sup>→</sup>
              </button>
              <button class="ribbon-btn-square" @click="applyNumberFormat('dec_decimal')" title="减少小数位数">
                .0<sup>←</sup>
              </button>
            </div>
          </div>
          <div class="group-label">数字</div>
        </div>

        <div class="ribbon-divider"></div>

        <!-- Group 5: 样式 (Styles) -->
        <div class="ribbon-group">
          <div class="group-controls-row">
            <el-dropdown trigger="click" @command="applyConditionalFormat">
              <button class="ribbon-big-btn" title="条件格式">
                <svg class="svg-icon big-icon" viewBox="0 0 24 24" width="22" height="22">
                  <rect x="3" y="3" width="18" height="18" rx="2" fill="none" stroke="currentColor" stroke-width="1.8"/>
                  <rect x="6" y="6" width="5" height="5" fill="#f87171"/>
                  <rect x="13" y="6" width="5" height="5" fill="#60a5fa"/>
                  <rect x="6" y="13" width="5" height="5" fill="#34d399"/>
                  <rect x="13" y="13" width="5" height="5" fill="#fbbf24"/>
                </svg>
                <span>条件格式 <el-icon class="el-icon--right"><ArrowDown /></el-icon></span>
              </button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="gt">突出显示：大于...</el-dropdown-item>
                  <el-dropdown-item command="lt">突出显示：小于...</el-dropdown-item>
                  <el-dropdown-item command="contains">突出显示：包含文本...</el-dropdown-item>
                  <el-dropdown-item command="databar" divided>渐变数据条 (Data Bars)</el-dropdown-item>
                  <el-dropdown-item command="colorscale">三色色阶 (Color Scale)</el-dropdown-item>
                  <el-dropdown-item command="clear" divided style="color: #f56c6c;">清除条件格式</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
          <div class="group-label">样式</div>
        </div>

        <div class="ribbon-divider"></div>

        <!-- Group 6: 单元格 (Cells) -->
        <div class="ribbon-group">
          <div class="group-controls-row">
            <div class="ribbon-small-stack">
              <el-dropdown trigger="click" @command="handleCellInsert">
                <button class="ribbon-mini-btn">
                  <svg class="svg-icon" viewBox="0 0 24 24" width="14" height="14">
                    <path fill="none" stroke="currentColor" stroke-width="1.8" d="M12 5v14M5 12h14"/>
                  </svg>
                  <span>插入 <el-icon><ArrowDown /></el-icon></span>
                </button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="row_above">在上方插入行</el-dropdown-item>
                    <el-dropdown-item command="row_below">在下方插入行</el-dropdown-item>
                    <el-dropdown-item command="col_left">在左侧插入列</el-dropdown-item>
                    <el-dropdown-item command="col_right">在右侧插入列</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>

              <el-dropdown trigger="click" @command="handleCellDelete">
                <button class="ribbon-mini-btn">
                  <svg class="svg-icon" viewBox="0 0 24 24" width="14" height="14" style="color: #f56c6c;">
                    <line x1="5" y1="12" x2="19" y2="12" stroke="currentColor" stroke-width="2"/>
                  </svg>
                  <span>删除 <el-icon><ArrowDown /></el-icon></span>
                </button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="row">删除整行</el-dropdown-item>
                    <el-dropdown-item command="col">删除整列</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>

              <button class="ribbon-mini-btn" @click="autoFitCurrentCol" title="自适应列宽">
                <svg class="svg-icon" viewBox="0 0 24 24" width="14" height="14">
                  <line x1="4" y1="12" x2="20" y2="12" stroke="currentColor" stroke-width="1.8"/>
                  <polyline points="8 8 4 12 8 16" stroke="currentColor" stroke-width="1.8" fill="none"/>
                  <polyline points="16 8 20 12 16 16" stroke="currentColor" stroke-width="1.8" fill="none"/>
                </svg>
                <span>自适应列宽</span>
              </button>
            </div>
          </div>
          <div class="group-label">单元格</div>
        </div>

        <div class="ribbon-divider"></div>

        <!-- Group 7: 编辑 (Editing) -->
        <div class="ribbon-group">
          <div class="group-controls-row">
            <div class="ribbon-small-stack">
              <!-- AutoSum Dropdown -->
              <el-dropdown trigger="click" @command="insertFormula">
                <button class="ribbon-mini-btn">
                  <span style="font-size: 14px; font-weight: bold; margin-right: 2px;">∑</span>
                  <span>自动求和 <el-icon><ArrowDown /></el-icon></span>
                </button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="SUM">求和 (SUM)</el-dropdown-item>
                    <el-dropdown-item command="AVERAGE">平均值 (AVERAGE)</el-dropdown-item>
                    <el-dropdown-item command="COUNT">计数 (COUNT)</el-dropdown-item>
                    <el-dropdown-item command="MAX">最大值 (MAX)</el-dropdown-item>
                    <el-dropdown-item command="MIN">最小值 (MIN)</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>

              <!-- Sort & Filter Dropdown -->
              <el-dropdown trigger="click" @command="handleSortFilterCmd">
                <button class="ribbon-mini-btn">
                  <svg class="svg-icon" viewBox="0 0 24 24" width="14" height="14">
                    <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" fill="none" stroke="currentColor" stroke-width="1.8"/>
                  </svg>
                  <span>排序和筛选 <el-icon><ArrowDown /></el-icon></span>
                </button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="sort_asc">升序排列 (A → Z)</el-dropdown-item>
                    <el-dropdown-item command="sort_desc">降序排列 (Z → A)</el-dropdown-item>
                    <el-dropdown-item command="filter" divided>{{ isFilterEnabled ? '关闭筛选' : '开启数据筛选' }}</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>

              <!-- Find & Replace Button -->
              <button class="ribbon-mini-btn" @click="openFindReplace('find')">
                <svg class="svg-icon" viewBox="0 0 24 24" width="14" height="14">
                  <circle cx="11" cy="11" r="8" fill="none" stroke="currentColor" stroke-width="1.8"/>
                  <line x1="21" y1="21" x2="16.65" y2="16.65" stroke="currentColor" stroke-width="1.8"/>
                </svg>
                <span>查找和选择</span>
              </button>
            </div>
          </div>
          <div class="group-label">编辑</div>
        </div>

      </div>

      <!-- ── Tab 2: 插入 (Insert) ── -->
      <div v-show="activeRibbonTab === 'insert'" class="ribbon-tab-pane">
        <!-- Group: 数据图表 -->
        <div class="ribbon-group">
          <div class="group-controls-row">
            <button class="ribbon-big-btn" @click="insertChartType('bar')">
              <svg class="svg-icon big-icon" viewBox="0 0 24 24" width="22" height="22">
                <rect x="4" y="10" width="3" height="10" fill="currentColor"/>
                <rect x="10.5" y="4" width="3" height="16" fill="currentColor"/>
                <rect x="17" y="7" width="3" height="13" fill="currentColor"/>
              </svg>
              <span>柱状图</span>
            </button>
            <button class="ribbon-big-btn" @click="insertChartType('line')">
              <svg class="svg-icon big-icon" viewBox="0 0 24 24" width="22" height="22">
                <polyline points="4 16 9 9 14 14 20 6" fill="none" stroke="currentColor" stroke-width="2"/>
                <circle cx="4" cy="16" r="1.5" fill="currentColor"/>
                <circle cx="9" cy="9" r="1.5" fill="currentColor"/>
                <circle cx="14" cy="14" r="1.5" fill="currentColor"/>
                <circle cx="20" cy="6" r="1.5" fill="currentColor"/>
              </svg>
              <span>折线图</span>
            </button>
            <button class="ribbon-big-btn" @click="insertChartType('pie')">
              <svg class="svg-icon big-icon" viewBox="0 0 24 24" width="22" height="22">
                <path d="M21.21 15.89A10 10 0 1 1 8 2.83" fill="none" stroke="currentColor" stroke-width="2"/>
                <path d="M22 12A10 10 0 0 0 12 2v10z" fill="currentColor"/>
              </svg>
              <span>饼图</span>
            </button>
            <button class="ribbon-big-btn" @click="insertChartType('area')">
              <svg class="svg-icon big-icon" viewBox="0 0 24 24" width="22" height="22">
                <polygon points="4 18 9 11 15 15 20 7 20 18" fill="rgba(64,158,255,0.35)" stroke="currentColor" stroke-width="1.5"/>
              </svg>
              <span>面积图</span>
            </button>
            <button class="ribbon-big-btn" @click="insertChartType('radar')">
              <svg class="svg-icon big-icon" viewBox="0 0 24 24" width="22" height="22">
                <polygon points="12 2 21 8 18 19 6 19 3 8" fill="none" stroke="currentColor" stroke-width="1.5"/>
                <polygon points="12 6 17 10 15 16 9 16 7 10" fill="rgba(99,102,241,0.25)" stroke="currentColor" stroke-width="1.5"/>
              </svg>
              <span>雷达图</span>
            </button>
          </div>
          <div class="group-label">图表 (基于当前选区)</div>
        </div>

        <div class="ribbon-divider"></div>

        <!-- Group: 插图与多媒体 -->
        <div class="ribbon-group">
          <div class="group-controls-row">
            <el-upload
              :show-file-list="false"
              accept="image/*"
              action="#"
              :before-upload="handleInsertImage"
            >
              <button class="ribbon-big-btn">
                <svg class="svg-icon big-icon" viewBox="0 0 24 24" width="22" height="22">
                  <rect x="3" y="3" width="18" height="18" rx="2" fill="none" stroke="currentColor" stroke-width="1.8"/>
                  <circle cx="8.5" cy="8.5" r="1.5" fill="currentColor"/>
                  <polyline points="21 15 16 10 5 21" stroke="currentColor" stroke-width="1.5" fill="none"/>
                </svg>
                <span>插入图片</span>
              </button>
            </el-upload>

            <el-upload
              :show-file-list="false"
              accept=".xlsx,.xls,.csv"
              action="#"
              :before-upload="handleImportExcel"
            >
              <button class="ribbon-big-btn">
                <svg class="svg-icon big-icon" viewBox="0 0 24 24" width="22" height="22">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" fill="none" stroke="currentColor" stroke-width="1.8"/>
                </svg>
                <span>导入 Excel</span>
              </button>
            </el-upload>
          </div>
          <div class="group-label">插图与数据导入</div>
        </div>

        <div class="ribbon-divider"></div>

        <!-- Group: 工作表 -->
        <div class="ribbon-group">
          <div class="group-controls-row">
            <button class="ribbon-big-btn" @click="addNewSheet">
              <svg class="svg-icon big-icon" viewBox="0 0 24 24" width="22" height="22">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" fill="none" stroke="currentColor" stroke-width="1.8"/>
                <line x1="12" y1="11" x2="12" y2="17" stroke="currentColor" stroke-width="1.8"/>
                <line x1="9" y1="14" x2="15" y2="14" stroke="currentColor" stroke-width="1.8"/>
              </svg>
              <span>新建工作表</span>
            </button>
          </div>
          <div class="group-label">工作表管理</div>
        </div>
      </div>

      <!-- ── Tab 3: 公式 (Formulas) ── -->
      <div v-show="activeRibbonTab === 'formulas'" class="ribbon-tab-pane">
        <div class="ribbon-group">
          <div class="group-controls-row">
            <button class="ribbon-big-btn" @click="openAiDrawer('formula')">
              <span class="fx-large-icon"><i>fx</i></span>
              <span>插入函数</span>
            </button>
            <button class="ribbon-mini-btn" @click="insertFormula('SUM')"><b>SUM</b> 求和</button>
            <button class="ribbon-mini-btn" @click="insertFormula('AVERAGE')"><b>AVERAGE</b> 平均值</button>
            <button class="ribbon-mini-btn" @click="insertFormula('COUNT')"><b>COUNT</b> 计数</button>
            <button class="ribbon-mini-btn" @click="insertFormula('MAX')"><b>MAX</b> 最大值</button>
            <button class="ribbon-mini-btn" @click="insertFormula('MIN')"><b>MIN</b> 最小值</button>
            <button class="ribbon-mini-btn" @click="insertFormula('IF')"><b>IF</b> 逻辑判断</button>
          </div>
          <div class="group-label">常用函数库</div>
        </div>

        <div class="ribbon-divider"></div>

        <div class="ribbon-group">
          <div class="group-controls-row">
            <button class="ribbon-big-btn ai-special-btn" @click="openAiDrawer('formula')">
              <svg class="svg-icon big-icon" viewBox="0 0 24 24" width="22" height="22">
                <path fill="currentColor" d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8L12 2z"/>
              </svg>
              <span>AI 智能公式助手</span>
            </button>
          </div>
          <div class="group-label">智能公式</div>
        </div>
      </div>

      <!-- ── Tab 4: 数据 (Data) ── -->
      <div v-show="activeRibbonTab === 'data'" class="ribbon-tab-pane">
        <!-- Group: 排序和筛选 -->
        <div class="ribbon-group">
          <div class="group-controls-row">
            <button class="ribbon-big-btn" @click="sortSelection('asc')">
              <svg class="svg-icon big-icon" viewBox="0 0 24 24" width="22" height="22">
                <path d="M3 6h18M3 12h12M3 18h6" stroke="currentColor" stroke-width="2" fill="none"/>
                <polyline points="18 14 20 12 22 14" stroke="currentColor" stroke-width="2" fill="none"/>
                <line x1="20" y1="12" x2="20" y2="20" stroke="currentColor" stroke-width="2"/>
              </svg>
              <span>升序 (A → Z)</span>
            </button>
            <button class="ribbon-big-btn" @click="sortSelection('desc')">
              <svg class="svg-icon big-icon" viewBox="0 0 24 24" width="22" height="22">
                <path d="M3 6h18M3 12h12M3 18h6" stroke="currentColor" stroke-width="2" fill="none"/>
                <polyline points="18 18 20 20 22 18" stroke="currentColor" stroke-width="2" fill="none"/>
                <line x1="20" y1="20" x2="20" y2="12" stroke="currentColor" stroke-width="2"/>
              </svg>
              <span>降序 (Z → A)</span>
            </button>
            <button class="ribbon-big-btn" :class="{ active: isFilterEnabled }" @click="toggleAutoFilter">
              <svg class="svg-icon big-icon" viewBox="0 0 24 24" width="22" height="22">
                <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" fill="none" stroke="currentColor" stroke-width="1.8"/>
              </svg>
              <span>{{ isFilterEnabled ? '关闭筛选' : '自动筛选' }}</span>
            </button>
          </div>
          <div class="group-label">排序和筛选</div>
        </div>

        <div class="ribbon-divider"></div>

        <!-- Group: 数据清洗与处理 -->
        <div class="ribbon-group">
          <div class="group-controls-row">
            <button class="ribbon-big-btn" @click="openAiDrawer('process')">
              <svg class="svg-icon big-icon" viewBox="0 0 24 24" width="22" height="22">
                <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" stroke="currentColor" stroke-width="1.8"/>
              </svg>
              <span>智能数据清洗</span>
            </button>
            <button class="ribbon-big-btn" @click="openAiDrawer('insights')">
              <svg class="svg-icon big-icon" viewBox="0 0 24 24" width="22" height="22">
                <path d="M22 12h-4l-3 9L9 3l-3 9H2" fill="none" stroke="currentColor" stroke-width="2"/>
              </svg>
              <span>数据深度洞察</span>
            </button>
          </div>
          <div class="group-label">数据工具与分析</div>
        </div>
      </div>

      <!-- ── Tab 5: 视图 (View) ── -->
      <div v-show="activeRibbonTab === 'view'" class="ribbon-tab-pane">
        <!-- Group: 冻结窗格 -->
        <div class="ribbon-group">
          <div class="group-controls-row">
            <el-dropdown trigger="click" @command="toggleFreezePane">
              <button class="ribbon-big-btn">
                <svg class="svg-icon big-icon" viewBox="0 0 24 24" width="22" height="22">
                  <rect x="3" y="3" width="18" height="18" rx="2" fill="none" stroke="currentColor" stroke-width="1.8"/>
                  <line x1="3" y1="8" x2="21" y2="8" stroke="currentColor" stroke-width="2"/>
                  <line x1="8" y1="3" x2="8" y2="21" stroke="currentColor" stroke-width="2"/>
                </svg>
                <span>冻结窗格 <el-icon><ArrowDown /></el-icon></span>
              </button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="top">{{ isFrozenTopRow ? '✓ ' : '' }}冻结首行</el-dropdown-item>
                  <el-dropdown-item command="first_col">{{ isFrozenFirstCol ? '✓ ' : '' }}冻结首列</el-dropdown-item>
                  <el-dropdown-item command="unfreeze" divided>取消所有冻结</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
          <div class="group-label">窗口冻结</div>
        </div>

        <div class="ribbon-divider"></div>

        <!-- Group: 历史版本与打印 -->
        <div class="ribbon-group">
          <div class="group-controls-row">
            <button class="ribbon-big-btn" @click="openVersionHistory">
              <svg class="svg-icon big-icon" viewBox="0 0 24 24" width="22" height="22">
                <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="1.8"/>
                <polyline points="12 6 12 12 16 14" stroke="currentColor" stroke-width="1.8" fill="none"/>
              </svg>
              <span>版本历史</span>
            </button>
            <button class="ribbon-big-btn" @click="printSpreadsheet">
              <svg class="svg-icon big-icon" viewBox="0 0 24 24" width="22" height="22">
                <polyline points="6 9 6 2 18 2 18 9" stroke="currentColor" stroke-width="1.8" fill="none"/>
                <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" stroke="currentColor" stroke-width="1.8" fill="none"/>
                <rect x="6" y="14" width="12" height="8" fill="none" stroke="currentColor" stroke-width="1.8"/>
              </svg>
              <span>打印表格</span>
            </button>
          </div>
          <div class="group-label">输出与历史</div>
        </div>
      </div>

      <!-- ── Tab 6: AI 助手 (AI Copilot) ── -->
      <div v-show="activeRibbonTab === 'ai'" class="ribbon-tab-pane">
        <div class="ribbon-group">
          <div class="group-controls-row">
            <button class="ribbon-big-btn ai-special-btn" @click="openAiDrawer('formula')">
              <span style="font-weight: bold; font-size: 16px;">fx</span>
              <span>智能公式</span>
            </button>
            <button class="ribbon-big-btn ai-special-btn" @click="openAiDrawer('generate')">
              <svg class="svg-icon big-icon" viewBox="0 0 24 24" width="22" height="22">
                <rect x="3" y="3" width="18" height="18" rx="2" fill="none" stroke="currentColor" stroke-width="1.8"/>
                <line x1="3" y1="9" x2="21" y2="9" stroke="currentColor" stroke-width="1.5"/>
                <line x1="9" y1="21" x2="9" y2="9" stroke="currentColor" stroke-width="1.5"/>
              </svg>
              <span>智能建表</span>
            </button>
            <button class="ribbon-big-btn ai-special-btn" @click="openAiDrawer('insights')">
              <svg class="svg-icon big-icon" viewBox="0 0 24 24" width="22" height="22">
                <path d="M22 12h-4l-3 9L9 3l-3 9H2" fill="none" stroke="currentColor" stroke-width="2"/>
              </svg>
              <span>数据洞察</span>
            </button>
            <button class="ribbon-big-btn ai-special-btn" @click="openAiDrawer('process')">
              <svg class="svg-icon big-icon" viewBox="0 0 24 24" width="22" height="22">
                <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4" stroke="currentColor" stroke-width="1.8"/>
              </svg>
              <span>选区处理</span>
            </button>
            <button class="ribbon-big-btn ai-special-btn" @click="openAiDrawer('chat')">
              <svg class="svg-icon big-icon" viewBox="0 0 24 24" width="22" height="22">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" fill="none" stroke="currentColor" stroke-width="1.8"/>
              </svg>
              <span>表格对话</span>
            </button>
          </div>
          <div class="group-label">AI 表格 Copilot 综合工具箱</div>
        </div>
      </div>

    </div>

    <!-- 4. Excel Standard Formula Bar -->
    <div class="formula-bar">
      <div class="cell-address-box">{{ selectionAddressText }}</div>
      
      <div class="formula-bar-actions">
        <button class="fx-action-btn" title="取消" @click="cancelCellEdit">✕</button>
        <button class="fx-action-btn confirm" title="输入" @click="commitActiveCell">✓</button>
        <button class="fx-action-btn fx-text" title="插入函数" @click="openAiDrawer('formula')"><i>fx</i></button>
      </div>

      <div class="formula-input-wrapper">
        <input 
          ref="formulaInputRef"
          type="text" 
          v-model="activeCellFormula" 
          :disabled="isCurrentCellLocked"
          :placeholder="currentCellLocker ? `🔒 该单元格正由 [${currentCellLocker.name}] 占用，已锁定保护` : '输入数值、文本或公式（例如 =SUM(A1:A10)）'"
          class="formula-input"
          :class="{ 'formula-input-locked': isCurrentCellLocked && !!currentCellLocker }"
          @input="onFormulaInputChange"
          @keydown.enter="commitActiveCell"
        />
      </div>
    </div>

    <!-- 5. Interactive Spreadsheet Canvas / Table View -->
    <div 
      class="sheet-viewport-container" 
      ref="gridContainerRef"
      @mousemove="onResizerMouseMove"
    >
      <!-- Column Resize Guide Line -->
      <div 
        v-if="isColResizing" 
        class="resize-guide-col"
        :style="{ left: `${resizerGuidePos}px` }"
      ></div>

      <!-- Row Resize Guide Line -->
      <div 
        v-if="isRowResizing" 
        class="resize-guide-row"
        :style="{ top: `${resizerGuidePos}px` }"
      ></div>

      <div class="sheet-grid-wrapper" :style="gridWrapperStyle">
        
        <!-- Floating Images Layer -->
        <div class="floating-images-layer" v-if="currentSheet">
          <div 
            v-for="img in currentSheet.images" 
            :key="img.id"
            class="floating-image-item"
            :style="{
              left: `${img.x || 80}px`,
              top: `${img.y || 60}px`,
              width: `${img.width || 200}px`,
              height: `${img.height || 150}px`
            }"
            @mousedown.stop="startDragImage($event, img)"
          >
            <img :src="img.src" alt="floating image" class="img-content" />
            <span v-if="canEdit" class="img-delete-btn" @click.stop="deleteImage(img.id)">✕</span>
          </div>
        </div>

        <!-- Floating Dynamic ECharts Layer -->
        <div class="floating-charts-layer" v-if="currentSheet && currentSheet.charts">
          <div
            v-for="chart in currentSheet.charts"
            :key="chart.id"
            class="floating-chart-card"
            :style="{
              left: `${chart.x || 120}px`,
              top: `${chart.y || 80}px`,
              width: `${chart.width || 420}px`,
              height: `${chart.height || 280}px`
            }"
            @mousedown.stop="startDragChart($event, chart)"
          >
            <div class="chart-card-header">
              <span class="chart-drag-handle">⠿ {{ chart.title }}</span>
              <div class="chart-header-actions" @mousedown.stop>
                <el-select v-model="chart.type" size="small" style="width: 90px;" @change="refreshChartDom(chart.id)">
                  <el-option label="柱状图" value="bar" />
                  <el-option label="折线图" value="line" />
                  <el-option label="饼图" value="pie" />
                  <el-option label="面积图" value="area" />
                  <el-option label="雷达图" value="radar" />
                </el-select>
                <button class="chart-act-btn" @click="exportChartPng(chart.id)" title="导出高清PNG">📷</button>
                <button class="chart-act-btn danger" @click="deleteChart(chart.id)" title="删除图表">✕</button>
              </div>
            </div>
            <div :id="`chart-container-${chart.id}`" class="chart-render-body"></div>
          </div>
        </div>

        <!-- Main Spreadsheet Table Grid -->
        <table class="spreadsheet-table" cellspacing="0" cellpadding="0">
          <thead>
            <tr :class="{ 'sticky-top-frozen': isFrozenTopRow }">
              <!-- Corner Header -->
              <th class="corner-header" @click="selectAllCells">#</th>
              <!-- Column Headers (A, B, C...) with Draggable Column Resizer -->
              <th 
                v-for="c in colCount" 
                :key="c" 
                class="col-header"
                :class="{ 
                  'col-selected': isColSelected(c - 1),
                  'sticky-first-col': isFrozenFirstCol && c === 1
                }"
                :style="{ width: `${getColumnWidth(c - 1)}px`, minWidth: `${getColumnWidth(c - 1)}px`, maxWidth: `${getColumnWidth(c - 1)}px` }"
                @click="selectColumn(c - 1, $event)"
                @contextmenu.prevent="openColContextMenu($event, c - 1)"
              >
                <div class="col-header-content">
                  <span class="header-text">{{ getColName(c - 1) }}</span>
                  <!-- Auto Filter Funnel Trigger -->
                  <span 
                    v-if="isFilterEnabled" 
                    class="filter-funnel-icon"
                    :class="{ active: columnFilters[c - 1]?.size }"
                    @click.stop="openFilterDropdown(c - 1, $event)"
                    title="数据筛选"
                  >
                    ▼
                  </span>
                </div>
                <!-- Right border column resizer handle -->
                <div 
                  class="col-resizer-handle" 
                  @mousedown.stop="startColResize(c - 1, $event)"
                  @dblclick.stop="autoFitColumnWidth(c - 1)"
                ></div>
              </th>

              <!-- Right edge add-column header -->
              <th 
                v-if="canEdit"
                class="col-header col-header-add-edge" 
                title="向右添加列"
                @click="appendCols(appendColCount)"
              >
                <div class="add-col-inner">
                  <el-icon><Plus /></el-icon>
                  <span>添加列</span>
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr 
              v-for="r in rowCount" 
              :key="r" 
              v-show="!hiddenRows.has(r - 1)"
              :style="{ height: `${getRowHeight(r - 1)}px` }"
            >
              <!-- Row Header (1, 2, 3...) with Draggable Row Resizer -->
              <td 
                class="row-header" 
                :class="{ 
                  'row-selected': isRowSelected(r - 1),
                  'sticky-first-col': isFrozenFirstCol
                }" 
                @click="selectRow(r - 1, $event)"
                @contextmenu.prevent="openRowContextMenu($event, r - 1)"
              >
                <span class="header-text">{{ r }}</span>
                <!-- Bottom border row resizer handle -->
                <div 
                  class="row-resizer-handle" 
                  @mousedown.stop="startRowResize(r - 1, $event)"
                ></div>
              </td>
              
              <!-- Cells (Supports Merged Cell Spanning & Multi-selection) -->
              <template v-for="c in colCount" :key="c">
                <td 
                  v-if="!getCellMergeInfo(r - 1, c - 1).isSlave"
                  class="cell-item"
                  :rowspan="getCellMergeInfo(r - 1, c - 1).rs"
                  :colspan="getCellMergeInfo(r - 1, c - 1).cs"
                  :class="{ 
                    'cell-active-primary': isPrimaryActiveCell(r - 1, c - 1),
                    'cell-in-selection': isCellInSelection(r - 1, c - 1),
                    'sel-edge-top': isSelEdgeTop(r - 1, c - 1),
                    'sel-edge-bottom': isSelEdgeBottom(r - 1, c - 1),
                    'sel-edge-left': isSelEdgeLeft(r - 1, c - 1),
                    'sel-edge-right': isSelEdgeRight(r - 1, c - 1),
                    'cell-find-matched': isCellFindMatched(r - 1, c - 1),
                    'cell-collab-active': isCellCollabActive(r - 1, c - 1),
                    'sticky-first-col-cell': isFrozenFirstCol && c === 1
                  }"
                  :style="[getCellComputedStyle(r - 1, c - 1), getCollabUserAtCell(r - 1, c - 1) ? { outline: '2px solid ' + getCollabUserAtCell(r - 1, c - 1)?.color, outlineOffset: '-2px' } : {}]"
                  @mousedown="onCellMouseDown(r - 1, c - 1, $event)"
                  @mouseenter="onCellMouseEnter(r - 1, c - 1)"
                  @dblclick="onCellDoubleClick(r - 1, c - 1)"
                  @contextmenu.prevent="openContextMenu($event, r - 1, c - 1)"
                >
                  <!-- In-place Inline Cell Editor (Word-like Edit mode with I-beam cursor, text drag-selection & Shift+Enter support) -->
                  <textarea 
                    v-if="isEditing && editingRow === r - 1 && editingCol === c - 1"
                    v-model="activeCellFormula"
                    class="cell-inline-textarea"
                    @mousedown.stop
                    @click.stop
                    @dblclick.stop
                    @blur="commitActiveCell"
                    @input="onInlineTextareaInput($event)"
                    @keydown.enter.exact="handleCellEnterPress($event)"
                    @keydown.enter.shift.stop="handleCellShiftEnterPress($event)"
                    @keydown.enter.alt.stop="handleCellShiftEnterPress($event)"
                    @keydown.tab.prevent="moveNextCell"
                    @keydown.esc="cancelCellEdit"
                    rows="1"
                  ></textarea>
                  <!-- Rendered Cell Value -->
                  <span v-else class="cell-rendered-val">
                    {{ getCellDisplayValue(r - 1, c - 1) }}
                  </span>

                  <!-- Fill Handle: rendered on the bottom-rightmost selected cell -->
                  <div 
                    v-if="isSelectionBottomRightCorner(r - 1, c - 1) && canEdit && !isEditing"
                    class="fill-handle-square"
                    @mousedown.stop="startFillHandleDrag($event)"
                    title="拖拽自动填充"
                  ></div>

                  <!-- Remote Collaborator Cursor Tag with Mini Avatar -->
                  <span 
                    v-if="getCollabUserAtCell(r - 1, c - 1)" 
                    class="collab-cell-badge"
                    :style="{ backgroundColor: getCollabUserAtCell(r - 1, c - 1)?.color }"
                  >
                    <span class="collab-mini-avatar" :style="{ backgroundColor: getCollabUserAtCell(r - 1, c - 1)?.color }">
                      <img v-if="getCollabUserAtCell(r - 1, c - 1)?.avatar" :src="getCollabUserAtCell(r - 1, c - 1)?.avatar" />
                      <span v-else>{{ (getCollabUserAtCell(r - 1, c - 1)?.name || 'U').charAt(0).toUpperCase() }}</span>
                    </span>
                    <span class="collab-badge-lock-icon">🔒</span>
                    <span class="collab-badge-name">{{ getCollabUserAtCell(r - 1, c - 1)?.name }}</span>
                    <span v-if="getCollabUserAtCell(r - 1, c - 1)?.isEditing" class="collab-editing-dot" title="正在编辑中"></span>
                  </span>

                  <!-- Collaborator Hover Popover Card on Mouse Hover -->
                  <div 
                    v-if="getCollabUserAtCell(r - 1, c - 1)"
                    class="collab-hover-card"
                  >
                    <div class="collab-hover-avatar" :style="{ backgroundColor: getCollabUserAtCell(r - 1, c - 1)?.color }">
                      <img v-if="getCollabUserAtCell(r - 1, c - 1)?.avatar" :src="getCollabUserAtCell(r - 1, c - 1)?.avatar" />
                      <span v-else>{{ (getCollabUserAtCell(r - 1, c - 1)?.name || 'U').charAt(0).toUpperCase() }}</span>
                    </div>
                    <div class="collab-hover-info">
                      <div class="collab-hover-name">
                        <span>{{ getCollabUserAtCell(r - 1, c - 1)?.name }}</span>
                        <span class="collab-hover-status">（{{ getCollabUserAtCell(r - 1, c - 1)?.isEditing ? '正在编辑…' : '正在查看' }}）</span>
                      </div>
                      <div class="collab-hover-tip">🔒 单元格已被锁定保护</div>
                    </div>
                  </div>
                  <!-- Live Edit Preview Bubble -->
                  <div
                    v-if="getCollabUserAtCell(r - 1, c - 1)?.isEditing"
                    class="collab-live-edit-bubble"
                    :style="{ borderColor: getCollabUserAtCell(r - 1, c - 1)?.color }"
                  >
                    {{ getCollabUserAtCell(r - 1, c - 1)?.editValue }}<span class="live-cursor-blink">|</span>
                  </div>
                </td>
              </template>
              <td v-if="canEdit" class="cell-item cell-add-edge" @click="appendCols(appendColCount)" title="向右添加列"></td>
            </tr>
          </tbody>
        </table>

        <!-- Bottom Append Rows & Columns Bar (matching user screenshot) -->
        <div class="bottom-append-bar" v-if="canEdit">
          <div class="append-section">
            <el-icon class="append-plus-icon"><Plus /></el-icon>
            <span class="append-label">向下添加</span>
            <el-input-number 
              v-model="appendRowCount" 
              :min="1" 
              :max="5000" 
              :step="50" 
              size="small" 
              controls-position="right"
              class="append-input-num"
              @keyup.enter="appendRows(appendRowCount)"
            />
            <span class="append-unit">行</span>
            <el-button type="primary" size="small" @click="appendRows(appendRowCount)" class="append-action-btn">
              添加
            </el-button>
            <div class="quick-append-tags">
              <span class="quick-tag" @click="appendRows(50)">+50</span>
              <span class="quick-tag" @click="appendRows(100)">+100</span>
              <span class="quick-tag" @click="appendRows(200)">+200</span>
              <span class="quick-tag" @click="appendRows(500)">+500</span>
            </div>
          </div>

          <div class="append-divider"></div>

          <div class="append-section">
            <el-icon class="append-plus-icon"><Plus /></el-icon>
            <span class="append-label">向右添加</span>
            <el-input-number 
              v-model="appendColCount" 
              :min="1" 
              :max="200" 
              :step="5" 
              size="small" 
              controls-position="right"
              class="append-input-num"
              @keyup.enter="appendCols(appendColCount)"
            />
            <span class="append-unit">列</span>
            <el-button type="success" size="small" @click="appendCols(appendColCount)" class="append-action-btn">
              添加
            </el-button>
            <div class="quick-append-tags">
              <span class="quick-tag" @click="appendCols(5)">+5</span>
              <span class="quick-tag" @click="appendCols(10)">+10</span>
              <span class="quick-tag" @click="appendCols(26)">+26</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 6. Right-Click Context Menu -->
    <div 
      v-if="contextMenuVisible" 
      ref="contextMenuRef"
      class="spreadsheet-context-menu"
      :style="{ left: `${contextMenuX}px`, top: `${contextMenuY}px` }"
      @click.stop
    >
      <div class="menu-item ai-item" @click="openAiDrawer('process')">AI 智能清洗与处理选区</div>
      <div class="menu-item ai-item" @click="openAiDrawer('insights')">AI 深度洞察当前数据</div>
      <div class="menu-item ai-item" @click="openAiDrawer('formula')">AI 针对当前单元格生成公式</div>
      <div class="menu-divider"></div>
      <div class="menu-item" @click="insertChartType('bar')">插入柱状图</div>
      <div class="menu-item" @click="insertChartType('line')">插入折线图</div>
      <div class="menu-divider"></div>
      <div class="menu-item" @click="handleCopySelection">复制 (Ctrl+C)</div>
      <div class="menu-item" @click="handleCutSelection">剪切 (Ctrl+X)</div>
      <div class="menu-item" @click="handlePasteSelection">粘贴 (Ctrl+V)</div>
      <div class="menu-divider"></div>
      <div class="menu-item" @click="insertRowAbove">在上方插入 1 行</div>
      <div class="menu-item" @click="insertRowBelow">在下方插入 1 行</div>
      <div class="menu-item" @click="insertColLeft">在左侧插入 1 列</div>
      <div class="menu-item" @click="insertColRight">在右侧插入 1 列</div>
      <div class="menu-divider"></div>
      <div class="menu-item danger" @click="deleteCurrentRow">删除整行</div>
      <div class="menu-item danger" @click="deleteCurrentCol">删除整列</div>
      <div class="menu-divider"></div>
      <div class="menu-item" @click="toggleMergeCells">
        {{ isCurrentSelectionMerged ? '取消合并 / 拆分单元格' : '合并居中' }}
      </div>
      <div v-if="isCurrentSelectionMerged" class="menu-item" @click="unmergeCells">
        拆分所选单元格
      </div>
      <div class="menu-item" @click="clearSelectionContent">清除内容 (Delete)</div>
      <div class="menu-divider"></div>
      <div class="menu-item" @click="sortSelection('asc')">升序排列 (A → Z)</div>
      <div class="menu-item" @click="sortSelection('desc')">降序排列 (Z → A)</div>
    </div>

    <!-- 7. Bottom Sheet Tabs Bar & Live Aggregates -->
    <div class="sheet-tabs-bar">
      <div class="sheet-tabs-scroll">
        <div 
          v-for="s in workbook.sheets" 
          :key="s.id" 
          class="sheet-tab"
          :class="{ active: s.id === workbook.activeSheetId }"
          @click="switchSheet(s.id)"
          @dblclick="promptRenameSheet(s)"
        >
          <span class="tab-name">{{ s.name }}</span>
          <span v-if="workbook.sheets.length > 1 && canEdit" class="tab-close" @click.stop="deleteSheet(s.id)">✕</span>
        </div>

        <button v-if="canEdit" class="add-sheet-btn" @click="addNewSheet" title="新增工作表">
          +
        </button>
      </div>

      <!-- Live Quick Aggregates on Selection -->
      <div class="live-aggregates-bar">
        <el-tooltip content="点击复制数值" placement="top">
          <span class="agg-pill" @click="copyAggValue(selectionAggregates.count)">计数: <b>{{ selectionAggregates.count }}</b></span>
        </el-tooltip>
        <el-tooltip content="点击复制求和数值" placement="top" v-if="selectionAggregates.numCount > 0">
          <span class="agg-pill" @click="copyAggValue(selectionAggregates.sum)">求和: <b>{{ selectionAggregates.sum.toLocaleString() }}</b></span>
        </el-tooltip>
        <el-tooltip content="点击复制平均值" placement="top" v-if="selectionAggregates.numCount > 0">
          <span class="agg-pill" @click="copyAggValue(selectionAggregates.avg)">平均值: <b>{{ selectionAggregates.avg.toLocaleString() }}</b></span>
        </el-tooltip>
        <el-tooltip content="点击复制最大值" placement="top" v-if="selectionAggregates.numCount > 1">
          <span class="agg-pill" @click="copyAggValue(selectionAggregates.max)">最大值: <b>{{ selectionAggregates.max }}</b></span>
        </el-tooltip>
        <el-tooltip content="点击复制最小值" placement="top" v-if="selectionAggregates.numCount > 1">
          <span class="agg-pill" @click="copyAggValue(selectionAggregates.min)">最小值: <b>{{ selectionAggregates.min }}</b></span>
        </el-tooltip>
        <span class="sheet-dim-text">行: {{ rowCount }} | 列: {{ colCount }}</span>
      </div>
    </div>

    <!-- 8. Find & Replace Floating Modal -->
    <div v-if="showFindDialog" class="find-replace-modal" @mousedown.stop>
      <div class="find-modal-header">
        <span class="find-modal-title">{{ findMode === 'find' ? '查找' : '查找与替换' }}</span>
        <button class="find-close-btn" @click="showFindDialog = false">✕</button>
      </div>
      <div class="find-modal-body">
        <div class="find-input-row">
          <label>查找内容:</label>
          <el-input v-model="findQuery" size="small" placeholder="输入搜索文本" @input="performFind" @keydown.enter="findNext" />
        </div>
        <div class="find-input-row" v-if="findMode === 'replace'">
          <label>替换为:</label>
          <el-input v-model="replaceQuery" size="small" placeholder="输入替换文本" />
        </div>
        <div class="find-options-row">
          <el-checkbox v-model="findMatchCase" size="small" @change="performFind">区分大小写</el-checkbox>
          <el-checkbox v-model="findMatchEntire" size="small" @change="performFind">单元格完全匹配</el-checkbox>
          <span class="find-count-hint" v-if="matchedCells.length">
            第 {{ currentMatchIndex + 1 }} / {{ matchedCells.length }} 项
          </span>
          <span class="find-count-hint" v-else-if="findQuery">未找到匹配项</span>
        </div>
        <div class="find-actions-row">
          <el-button size="small" @click="findPrev" :disabled="!matchedCells.length">上一个</el-button>
          <el-button size="small" type="primary" @click="findNext" :disabled="!matchedCells.length">下一个</el-button>
          <template v-if="findMode === 'replace' && canEdit">
            <el-button size="small" type="warning" @click="performReplace">替换</el-button>
            <el-button size="small" type="danger" @click="performReplaceAll">全部替换</el-button>
          </template>
        </div>
      </div>
    </div>

    <!-- 9. Column Header Auto-Filter Popup Dropdown -->
    <div 
      v-if="filterDropdownVisible" 
      class="filter-dropdown-popup"
      :style="{ left: `${filterDropdownX}px`, top: `${filterDropdownY}px` }"
      @click.stop
    >
      <div class="filter-popup-header">
        <span>筛选: {{ getColName(activeFilterCol ?? 0) }} 列</span>
        <button class="filter-close-btn" @click="filterDropdownVisible = false">✕</button>
      </div>
      <div class="filter-search-box">
        <el-input v-model="filterSearchText" size="small" placeholder="搜索值..." clearable />
      </div>
      <div class="filter-values-list">
        <div 
          v-for="val in filteredUniqueValues" 
          :key="val"
          class="filter-val-item"
          @click="toggleFilterValueItem(val)"
        >
          <el-checkbox :model-value="!isFilterValueExcluded(val)">
            {{ val === '' ? '(空白)' : val }}
          </el-checkbox>
        </div>
      </div>
      <div class="filter-popup-footer">
        <el-button size="small" link @click="selectAllFilterValues">全选</el-button>
        <el-button size="small" link @click="clearAllFilterValues">清空</el-button>
        <el-button size="small" type="primary" @click="applyFilterAndClose">确定</el-button>
      </div>
    </div>

    <!-- 10. Version History Drawer -->
    <el-drawer
      v-model="showVersionDrawer"
      title="表格版本历史"
      size="380px"
      direction="rtl"
      destroy-on-close
    >
      <div class="version-list-wrapper" v-loading="loadingVersions">
        <div v-if="!versionList.length" class="empty-versions">暂无历史版本记录</div>
        <div v-for="(ver, idx) in versionList" :key="ver.id" class="version-card-item">
          <div class="ver-header">
            <span class="ver-badge">v{{ versionList.length - idx }}</span>
            <span class="ver-time">{{ ver.created_at }}</span>
          </div>
          <div class="ver-author">修改人: {{ ver.creator_name || '系统' }}</div>
          <div class="ver-actions">
            <el-button size="small" type="primary" plain @click="restoreSpecificVersion(ver)">
              恢复此版本
            </el-button>
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- 11. AI Copilot Dedicated Side Drawer -->
    <el-drawer
      v-model="showAiDrawer"
      title="AI 电子表格 Copilot"
      size="460px"
      direction="rtl"
      class="sheet-ai-drawer"
      destroy-on-close
    >
      <el-tabs v-model="aiActiveTab" class="ai-copilot-tabs">
        <!-- Tab 1: AI Formula Copilot -->
        <el-tab-pane label="智能公式" name="formula">
          <div class="ai-panel-body">
            <div class="context-info-bar">
              <el-tag size="small" type="primary">目标单元格: {{ getColName(startCol) }}{{ startRow + 1 }}</el-tag>
              <el-tag size="small" type="info" style="margin-left: 6px;">选区: {{ selectionAddressText }}</el-tag>
            </div>

            <div class="ai-prompt-input-box">
              <el-input
                v-model="aiFormulaQuery"
                type="textarea"
                :rows="3"
                :placeholder="t('editor.sheetAi.formulaPlaceholder', '描述你想计算什么，例如：求前5行大于100的平均值')"
              />
              <div class="quick-tags-row">
                <span class="quick-tag-label">快捷示例:</span>
                <el-tag size="small" effect="plain" class="clickable-tag" @click="aiFormulaQuery = '求前10行总和'">求和</el-tag>
                <el-tag size="small" effect="plain" class="clickable-tag" @click="aiFormulaQuery = '计算前5行的平均值'">平均值</el-tag>
                <el-tag size="small" effect="plain" class="clickable-tag" @click="aiFormulaQuery = '统计数值大于等于60的及格人数'">条件计数</el-tag>
                <el-tag size="small" effect="plain" class="clickable-tag" @click="aiFormulaQuery = '找出这一列的最大值和最小值'">极值</el-tag>
              </div>
              <el-button 
                type="primary" 
                style="width: 100%; margin-top: 10px;" 
                :loading="aiFormulaLoading" 
                @click="generateAiFormula"
              >
                生成公式
              </el-button>
            </div>

            <!-- Result Card -->
            <div v-if="aiGeneratedFormulaResult" class="ai-result-card">
              <div class="result-header">
                <span class="result-title">推荐公式:</span>
                <el-button type="success" size="small" @click="applyGeneratedFormula">
                  {{ t('editor.sheetAi.applyFormula', '填入当前单元格') }}
                </el-button>
              </div>
              <div class="code-formula-box">{{ aiGeneratedFormulaResult.formula }}</div>
              <p class="result-desc"><b>解析：</b>{{ aiGeneratedFormulaResult.explanation }}</p>
              <p v-if="aiGeneratedFormulaResult.alternative" class="result-alt">
                <b>备选写法：</b><code>{{ aiGeneratedFormulaResult.alternative }}</code>
              </p>
            </div>
          </div>
        </el-tab-pane>

        <!-- Tab 2: AI Table Generator -->
        <el-tab-pane label="智能建表" name="generate">
          <div class="ai-panel-body">
            <div class="ai-prompt-input-box">
              <el-input
                v-model="aiTablePrompt"
                type="textarea"
                :rows="3"
                :placeholder="t('editor.sheetAi.generateTablePlaceholder', '输入你想生成的表格主题，例如：2026年Q1各部门财务预算表')"
              />
              <div class="quick-tags-row">
                <span class="quick-tag-label">推荐模板:</span>
                <el-tag size="small" effect="plain" class="clickable-tag" @click="aiTablePrompt = '2026年度科技公司季度财务预算表'">财务预算</el-tag>
                <el-tag size="small" effect="plain" class="clickable-tag" @click="aiTablePrompt = '研发团队成员月度绩效与KPI考核评分表'">绩效考核</el-tag>
                <el-tag size="small" effect="plain" class="clickable-tag" @click="aiTablePrompt = '电商平台各品类季度销售明细与毛利率统计'">销售明细</el-tag>
                <el-tag size="small" effect="plain" class="clickable-tag" @click="aiTablePrompt = '公司固定资产与IT设备采购清单'">设备清单</el-tag>
              </div>
              <div style="display: flex; gap: 12px; margin-top: 10px;">
                <el-input-number v-model="aiTableRowCount" :min="3" :max="20" size="small" controls-position="right" label="数据行数" style="width: 120px;" />
                <el-button 
                  type="primary" 
                  style="flex: 1;" 
                  :loading="aiTableLoading" 
                  @click="generateAiTable"
                >
                  一键生成表格
                </el-button>
              </div>
            </div>

            <!-- Preview & Insert -->
            <div v-if="aiGeneratedTableResult" class="ai-result-card">
              <div class="result-header">
                <span class="result-title">工作表：{{ aiGeneratedTableResult.sheet_name }}</span>
                <el-button type="primary" size="small" @click="insertGeneratedTableAsSheet">
                  {{ t('editor.sheetAi.insertAsNewSheet', '插入为新工作表') }}
                </el-button>
              </div>
              <div class="table-preview-mini">
                <table class="preview-table">
                  <thead>
                    <tr>
                      <th v-for="h in aiGeneratedTableResult.headers" :key="h">{{ h }}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(row, rIdx) in aiGeneratedTableResult.rows.slice(0, 4)" :key="rIdx">
                      <td v-for="(cell, cIdx) in row" :key="cIdx">{{ cell }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div class="preview-hint">（已生成 {{ aiGeneratedTableResult.rows.length }} 行数据，包含表头与合计公式）</div>
            </div>
          </div>
        </el-tab-pane>

        <!-- Tab 3: AI Data Insights -->
        <el-tab-pane label="数据洞察" name="insights">
          <div class="ai-panel-body">
            <div class="context-info-bar">
              <span>当前分析工作表: <b>{{ currentSheet?.name }}</b></span>
            </div>
            <el-button 
              type="warning" 
              style="width: 100%; margin-bottom: 12px;" 
              :loading="aiInsightsLoading" 
              @click="analyzeAiInsights"
            >
              一键扫描数据洞察
            </el-button>

            <div v-if="aiInsightsResult" class="insights-content-wrapper">
              <div class="insight-box summary-box">
                <h4>核心摘要</h4>
                <p>{{ aiInsightsResult.summary }}</p>
              </div>

              <div class="metrics-grid" v-if="aiInsightsResult.key_metrics?.length">
                <div v-for="m in aiInsightsResult.key_metrics" :key="m.label" class="metric-card">
                  <div class="metric-label">{{ m.label }}</div>
                  <div class="metric-val">{{ m.value }}</div>
                </div>
              </div>

              <div class="insight-box" v-if="aiInsightsResult.trends?.length">
                <h4>趋势分析</h4>
                <ul>
                  <li v-for="(tr, idx) in aiInsightsResult.trends" :key="idx">{{ tr }}</li>
                </ul>
              </div>

              <div class="insight-box danger-box" v-if="aiInsightsResult.anomalies?.length">
                <h4>异常预警</h4>
                <ul>
                  <li v-for="(an, idx) in aiInsightsResult.anomalies" :key="idx">{{ an }}</li>
                </ul>
              </div>

              <div class="insight-box success-box" v-if="aiInsightsResult.recommendations?.length">
                <h4>业务建议</h4>
                <ul>
                  <li v-for="(rc, idx) in aiInsightsResult.recommendations" :key="idx">{{ rc }}</li>
                </ul>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <!-- Tab 4: AI Smart Range Actions -->
        <el-tab-pane label="选区处理" name="process">
          <div class="ai-panel-body">
            <div class="context-info-bar">
              <el-tag size="small" type="success">选区: {{ selectionAddressText }}</el-tag>
            </div>

            <div class="actions-stack">
              <el-button 
                class="action-card-btn" 
                :loading="aiProcessLoading" 
                @click="processRangeAction('clean')"
              >
                <div class="action-btn-title">智能数据清洗</div>
                <div class="action-btn-sub">自动去除多余空格、标准化日期格式与异常字符</div>
              </el-button>

              <el-button 
                class="action-card-btn" 
                :loading="aiProcessLoading" 
                @click="processRangeAction('translate', 'en')"
              >
                <div class="action-btn-title">批量翻译为英文</div>
                <div class="action-btn-sub">对选区内的中文文本一键翻译为英文</div>
              </el-button>

              <el-button 
                class="action-card-btn" 
                :loading="aiProcessLoading" 
                @click="processRangeAction('translate', 'zh')"
              >
                <div class="action-btn-title">批量翻译为中文</div>
                <div class="action-btn-sub">对选区内的英文/多语种文本翻译为中文</div>
              </el-button>

              <el-button 
                class="action-card-btn" 
                :loading="aiProcessLoading" 
                @click="processRangeAction('autofill')"
              >
                <div class="action-btn-title">智能推断并补全</div>
                <div class="action-btn-sub">分析前序单元格数据逻辑，智能补全后续空格内容</div>
              </el-button>
            </div>
          </div>
        </el-tab-pane>

        <!-- Tab 5: Chat with Sheet -->
        <el-tab-pane label="表格问答" name="chat">
          <div class="ai-chat-tab-body">
            <div class="chat-messages-scroll" ref="aiChatScrollRef">
              <div v-for="(msg, i) in aiChatMessages" :key="i" :class="['chat-msg-row', msg.role]">
                <div class="msg-avatar">{{ msg.role === 'user' ? '用户' : 'AI' }}</div>
                <div class="msg-bubble">
                  <div class="msg-text">{{ msg.content }}</div>
                </div>
              </div>
              <div v-if="aiChatStreaming" class="chat-msg-row assistant">
                <div class="msg-avatar">AI</div>
                <div class="msg-bubble"><span class="typing-dots">AI 思考中...</span></div>
              </div>
            </div>

            <div class="chat-input-box">
              <el-input
                v-model="aiChatInput"
                type="textarea"
                :rows="2"
                :placeholder="t('editor.sheetAi.chatPlaceholder', '对当前表格数据提问，例如：哪个产品利润最高？')"
                @keydown.enter.prevent="sendAiChatMessage"
              />
              <el-button 
                type="primary" 
                size="small" 
                style="margin-top: 8px; width: 100%;" 
                :loading="aiChatStreaming" 
                @click="sendAiChatMessage"
              >
                发送提问
              </el-button>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-drawer>

    <!-- Share Dialog -->
    <DocumentShareDialog 
      v-if="showShareDialog"
      v-model="showShareDialog"
      :document-id="docId"
      @saved="onPermissionsSaved"
    />

    <!-- Start Approval Dialog -->
    <el-dialog v-model="showApprovalDialog" :title="t('editor.approvalTitle', '发起审批流程')" width="480px">
      <el-form label-position="top">
        <el-form-item label="审批流类型">
          <el-radio-group v-model="approvalType">
            <el-radio value="parallel">并行审批 (无顺序)</el-radio>
            <el-radio value="sequential">顺序审批 (指定流程)</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="选择审批人">
          <el-select v-model="selectedApprovers" multiple style="width: 100%" placeholder="请选择审批人员">
            <el-option v-for="u in usersList" :key="u.id" :label="u.display_name || u.login_name" :value="u.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showApprovalDialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="submittingApproval" @click="submitApprovalFlow">{{ t('common.confirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, onUnmounted, nextTick, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter, onBeforeRouteLeave } from "vue-router";
import api from "@/api/client";
import { useAuthStore } from "@/stores/auth";
import { ElMessage, ElMessageBox, ElLoading } from "element-plus";
import * as XLSX from "xlsx";
import * as echarts from "echarts";
import { io, Socket } from "socket.io-client";
import {
  Back, Check, Download, ArrowDown, Promotion, Share, Document, Delete, Printer, MagicStick, Plus
} from "@element-plus/icons-vue";
import DocumentShareDialog from "@/components/DocumentShareDialog.vue";

interface CellData {
  v?: any;
  m?: string;
  f?: string;
  t?: string;
  nf?: string;
}

interface CellBorders {
  t?: string;
  b?: string;
  l?: string;
  r?: string;
}

interface CellStyle {
  ff?: string;
  bl?: number;
  it?: number;
  un?: number;
  cl?: number;
  fs?: number;
  fc?: string;
  bg?: string;
  ht?: string;
  vt?: string;
  tb?: number;
  bd?: CellBorders;
}

interface FloatingImage {
  id: string;
  src: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

interface FloatingChart {
  id: string;
  title: string;
  type: "bar" | "line" | "pie" | "area" | "radar";
  range: { r1: number; c1: number; r2: number; c2: number };
  x: number;
  y: number;
  width: number;
  height: number;
}

interface ConditionalRule {
  id: string;
  type: "gt" | "lt" | "contains" | "databar" | "colorscale";
  val?: any;
  r1: number;
  c1: number;
  r2: number;
  c2: number;
}

interface MergedCell {
  r: number;
  c: number;
  rs: number;
  cs: number;
}

interface Sheet {
  id: string;
  name: string;
  rowCount: number;
  colCount: number;
  cells: Record<string, CellData>;
  styles: Record<string, CellStyle>;
  images: FloatingImage[];
  charts: FloatingChart[];
  mergedCells: MergedCell[];
  cfRules?: ConditionalRule[];
  columnWidths: Record<string, number>;
  rowHeights: Record<string, number>;
}

interface Workbook {
  type: string;
  activeSheetId: string;
  sheets: Sheet[];
}

const props = defineProps<{
  docId: number;
  initialDocData?: any;
}>();

const emit = defineEmits(["updated"]);

const { t } = useI18n();
const router = useRouter();
const authStore = useAuthStore();

// ── State Variables ───────────────────────────────────
const loading = ref(false);
const saving = ref(false);
const saveHint = ref("");
const meta = ref<any>(props.initialDocData || {});
const title = ref(meta.value.title || "Untitled");

// Active Ribbon Tab (home, insert, formulas, data, view, ai)
const activeRibbonTab = ref("home");

const showShareDialog = ref(false);
const showApprovalDialog = ref(false);
const approvalType = ref("parallel");
const selectedApprovers = ref<number[]>([]);
const submittingApproval = ref(false);
const usersList = ref<any[]>([]);

// ── Freeze Panes & Auto-Filter State ──────────────────
const isFrozenTopRow = ref(false);
const isFrozenFirstCol = ref(false);
const isFilterEnabled = ref(false);
const columnFilters = ref<Record<number, Set<string>>>({});
const filterDropdownVisible = ref(false);
const activeFilterCol = ref<number | null>(null);
const filterDropdownX = ref(0);
const filterDropdownY = ref(0);
const filterSearchText = ref("");

// ── Find & Replace State ──────────────────────────────
const showFindDialog = ref(false);
const findMode = ref<"find" | "replace">("find");
const findQuery = ref("");
const replaceQuery = ref("");
const findMatchCase = ref(false);
const findMatchEntire = ref(false);
const matchedCells = ref<Array<{ r: number; c: number }>>([]);
const currentMatchIndex = ref(0);

// ── Version History Drawer State ──────────────────────
const showVersionDrawer = ref(false);
const loadingVersions = ref(false);
const versionList = ref<any[]>([]);

// ── AI Copilot Drawer State ───────────────────────────
const showAiDrawer = ref(false);
const aiActiveTab = ref("formula");

const aiFormulaQuery = ref("");
const aiFormulaLoading = ref(false);
const aiGeneratedFormulaResult = ref<any>(null);

const aiTablePrompt = ref("");
const aiTableRowCount = ref(6);
const aiTableLoading = ref(false);
const aiGeneratedTableResult = ref<any>(null);

const aiInsightsLoading = ref(false);
const aiInsightsResult = ref<any>(null);

const aiProcessLoading = ref(false);

const aiChatInput = ref("");
const aiChatStreaming = ref(false);
const aiChatMessages = ref<Array<{ role: 'user' | 'assistant'; content: string }>>([
  { role: 'assistant', content: '您好！我是您的电子表格 AI Copilot。您可以让我帮您编写公式、生成完整工作表、深度洞察数据趋势或批量处理选区数据。' }
]);
const aiChatScrollRef = ref<HTMLDivElement | null>(null);

// Workbook core reactive data
const workbook = ref<Workbook>({
  type: "spreadsheet",
  activeSheetId: "sheet_1",
  sheets: [
    {
      id: "sheet_1",
      name: "Sheet1",
      rowCount: 60,
      colCount: 26,
      cells: {},
      styles: {},
      images: [],
      charts: [],
      mergedCells: [],
      cfRules: [],
      columnWidths: {},
      rowHeights: {}
    }
  ]
});

// ── Multi-Cell Selection State ────────────────────────
const startRow = ref(0);
const startCol = ref(0);
const endRow = ref(0);
const endCol = ref(0);
const isSelecting = ref(false);

const isEditing = ref(false);
const editingRow = ref(0);
const editingCol = ref(0);
const activeCellFormula = ref("");
const formulaInputRef = ref<HTMLInputElement | null>(null);
const gridContainerRef = ref<HTMLDivElement | null>(null);
const rootContainerRef = ref<HTMLDivElement | null>(null);

// ── Format Painter & Undo/Redo Stacks ─────────────────
const isFormatPainting = ref(false);
const copiedStyle = ref<CellStyle | null>(null);
const undoStack = ref<string[]>([]);
const redoStack = ref<string[]>([]);

// ── Right-Click Context Menu State ────────────────────
const contextMenuRef = ref<HTMLElement | null>(null);
const contextMenuVisible = ref(false);
const contextMenuX = ref(0);
const contextMenuY = ref(0);

// ── Column & Row Resizing State ───────────────────────
const isColResizing = ref(false);
const resizingColIdx = ref(0);
const colResizeStartX = ref(0);
const colResizeInitWidth = ref(0);

const isRowResizing = ref(false);
const resizingRowIdx = ref(0);
const rowResizeStartY = ref(0);
const rowResizeInitHeight = ref(0);

const resizerGuidePos = ref(0);

// ── Fill Handle State ─────────────────────────────────
const isDraggingFill = ref(false);

// ── Socket & Collaborators ────────────────────────────
let socket: Socket | null = null;
const collabUsers = ref<Array<{ id: string; name: string; avatar?: string; color: string; sheetId?: string; row?: number; col?: number; isEditing?: boolean; editValue?: string }>>([]);

// ── Computed Properties ───────────────────────────────
const canEdit = computed(() => !!meta.value.can_edit);
const isOwner = computed(() => !!meta.value.is_owner);
const isAdmin = computed(() => !!authStore.user?.is_super_admin);

const statusTagType = computed(() => {
  const s = meta.value.status;
  if (s === "approved") return "success";
  if (s === "in_approval") return "warning";
  if (s === "rejected") return "danger";
  return "info";
});

const statusLabel = computed(() => {
  const s = meta.value.status || "draft";
  return t(`editor.status.${s}`, s);
});

const currentSheet = computed(() => {
  return workbook.value.sheets.find(s => s.id === workbook.value.activeSheetId) || workbook.value.sheets[0]!;
});

const rowCount = computed(() => currentSheet.value?.rowCount || 60);
const colCount = computed(() => currentSheet.value?.colCount || 26);

// Selection bounds
const selMinRow = computed(() => Math.min(startRow.value, endRow.value));
const selMaxRow = computed(() => Math.max(startRow.value, endRow.value));
const selMinCol = computed(() => Math.min(startCol.value, endCol.value));
const selMaxCol = computed(() => Math.max(startCol.value, endCol.value));

const selectionAddressText = computed(() => {
  const startAddr = `${getColName(selMinCol.value)}${selMinRow.value + 1}`;
  if (selMinRow.value === selMaxRow.value && selMinCol.value === selMaxCol.value) {
    return startAddr;
  }
  const endAddr = `${getColName(selMaxCol.value)}${selMaxRow.value + 1}`;
  return `${startAddr}:${endAddr}`;
});

const currentCellStyle = computed(() => {
  const key = `${startRow.value}_${startCol.value}`;
  return currentSheet.value?.styles?.[key] || {};
});

const currentFontFamily = computed({
  get: () => currentCellStyle.value.ff || "Microsoft YaHei, sans-serif",
  set: (val: string) => setFontFamily(val)
});

const currentFontSize = computed({
  get: () => currentCellStyle.value.fs || 11,
  set: (val: number) => setFontSize(val)
});

const currentNumFormat = computed({
  get: () => {
    const key = `${startRow.value}_${startCol.value}`;
    return currentSheet.value?.cells?.[key]?.nf || "general";
  },
  set: (val: string) => applyNumberFormat(val)
});

const isCurrentSelectionMerged = computed(() => {
  const list = currentSheet.value?.mergedCells || [];
  const r1 = selMinRow.value;
  const r2 = selMaxRow.value;
  const c1 = selMinCol.value;
  const c2 = selMaxCol.value;
  return list.some(m => {
    const mr1 = m.r;
    const mr2 = m.r + m.rs - 1;
    const mc1 = m.c;
    const mc2 = m.c + m.cs - 1;
    return !(r2 < mr1 || r1 > mr2 || c2 < mc1 || c1 > mc2);
  });
});

// Live Aggregates on Selection
const selectionAggregates = computed(() => {
  let count = 0;
  let numCount = 0;
  let sum = 0;
  let min = Infinity;
  let max = -Infinity;

  for (let r = selMinRow.value; r <= selMaxRow.value; r++) {
    for (let c = selMinCol.value; c <= selMaxCol.value; c++) {
      const val = getRawCellValue(r, c, currentSheet.value, new Set());
      if (val !== "" && val !== null && val !== undefined) {
        count++;
        const n = Number(val);
        if (!isNaN(n)) {
          numCount++;
          sum += n;
          if (n < min) min = n;
          if (n > max) max = n;
        }
      }
    }
  }

  const avg = numCount > 0 ? (sum / numCount) : 0;
  return {
    count,
    numCount,
    sum: numCount > 0 ? Number(sum.toFixed(2)) : 0,
    avg: numCount > 0 ? Number(avg.toFixed(2)) : 0,
    min: numCount > 0 && min !== Infinity ? min : 0,
    max: numCount > 0 && max !== -Infinity ? max : 0
  };
});

// Filtered Hidden Rows
const hiddenRows = computed<Set<number>>(() => {
  const set = new Set<number>();
  if (!isFilterEnabled.value) return set;

  Object.entries(columnFilters.value).forEach(([colStr, excludedVals]) => {
    const colIdx = Number(colStr);
    if (!excludedVals || excludedVals.size === 0) return;

    for (let r = 1; r < rowCount.value; r++) {
      const cellVal = getCellDisplayValue(r, colIdx);
      if (excludedVals.has(cellVal)) {
        set.add(r);
      }
    }
  });

  return set;
});

const gridWrapperStyle = computed(() => {
  return {
    minWidth: "100%",
    position: "relative" as const
  };
});

// ── Helpers ───────────────────────────────────────────
function getColName(index: number): string {
  let name = "";
  let num = index;
  while (num >= 0) {
    name = String.fromCharCode((num % 26) + 65) + name;
    num = Math.floor(num / 26) - 1;
  }
  return name;
}

function colNameToIndex(colStr: string): number {
  let idx = 0;
  for (let i = 0; i < colStr.length; i++) {
    idx = idx * 26 + (colStr.charCodeAt(i) - 64);
  }
  return idx - 1;
}

function getColumnWidth(colIndex: number): number {
  return currentSheet.value?.columnWidths?.[String(colIndex)] || 100;
}

function getRowHeight(rowIndex: number): number {
  return currentSheet.value?.rowHeights?.[String(rowIndex)] || 26;
}

// ── Merged Cell Helpers ───────────────────────────────
function getCellMergeInfo(r: number, c: number): { isMaster: boolean; isSlave: boolean; rs: number; cs: number } {
  const mergedList = currentSheet.value?.mergedCells || [];
  for (const m of mergedList) {
    if (r === m.r && c === m.c) {
      return { isMaster: true, isSlave: false, rs: m.rs, cs: m.cs };
    }
    if (r >= m.r && r < m.r + m.rs && c >= m.c && c < m.c + m.cs) {
      return { isMaster: false, isSlave: true, rs: 1, cs: 1 };
    }
  }
  return { isMaster: false, isSlave: false, rs: 1, cs: 1 };
}

function getCellComputedStyle(r: number, c: number): Record<string, any> {
  const key = `${r}_${c}`;
  const st = currentSheet.value?.styles?.[key];
  const styleObj: Record<string, any> = {};

  if (st) {
    if (st.ff) styleObj.fontFamily = st.ff;
    if (st.bl) styleObj.fontWeight = "bold";
    if (st.it) styleObj.fontStyle = "italic";
    if (st.un) styleObj.textDecoration = "underline";
    if (st.cl) styleObj.textDecoration = (styleObj.textDecoration ? styleObj.textDecoration + " " : "") + "line-through";
    if (st.fs) styleObj.fontSize = `${st.fs}px`;
    if (st.fc) styleObj.color = st.fc;
    if (st.bg) styleObj.backgroundColor = st.bg;
    if (st.ht) styleObj.textAlign = st.ht;
    if (st.vt) {
      if (st.vt === 'top') styleObj.verticalAlign = 'top';
      else if (st.vt === 'bottom') styleObj.verticalAlign = 'bottom';
      else styleObj.verticalAlign = 'middle';
    }
    if (st.tb) {
      styleObj.whiteSpace = "normal";
      styleObj.wordBreak = "break-all";
    }
    if (st.bd) {
      if (st.bd.t) styleObj.borderTop = st.bd.t;
      if (st.bd.b) styleObj.borderBottom = st.bd.b;
      if (st.bd.l) styleObj.borderLeft = st.bd.l;
      if (st.bd.r) styleObj.borderRight = st.bd.r;
    }
  }

  // Conditional formatting evaluation
  const rules = currentSheet.value?.cfRules || [];
  for (const rule of rules) {
    if (r >= rule.r1 && r <= rule.r2 && c >= rule.c1 && c <= rule.c2) {
      const val = getRawCellValue(r, c, currentSheet.value, new Set());
      const numVal = Number(val);

      if (rule.type === "gt" && !isNaN(numVal) && numVal > Number(rule.val)) {
        styleObj.backgroundColor = "#fee2e2";
        styleObj.color = "#991b1b";
      } else if (rule.type === "lt" && !isNaN(numVal) && numVal < Number(rule.val)) {
        styleObj.backgroundColor = "#dcfce7";
        styleObj.color = "#166534";
      } else if (rule.type === "contains" && String(val).includes(String(rule.val))) {
        styleObj.backgroundColor = "#fef3c7";
        styleObj.color = "#92400e";
      } else if (rule.type === "databar" && !isNaN(numVal)) {
        const pct = Math.min(Math.max(numVal, 0), 100);
        styleObj.background = `linear-gradient(to right, rgba(59, 130, 246, 0.28) ${pct}%, transparent ${pct}%)`;
      } else if (rule.type === "colorscale" && !isNaN(numVal)) {
        if (numVal > 60) styleObj.backgroundColor = "#dcfce7";
        else if (numVal >= 30) styleObj.backgroundColor = "#fef3c7";
        else styleObj.backgroundColor = "#fee2e2";
      }
    }
  }

  return styleObj;
}

// ── Selection State Query Helpers ─────────────────────
function isCellInSelection(r: number, c: number): boolean {
  if (getLockingCollaborator(r, c)) return false;
  return r >= selMinRow.value && r <= selMaxRow.value && c >= selMinCol.value && c <= selMaxCol.value;
}

function isPrimaryActiveCell(r: number, c: number): boolean {
  if (getLockingCollaborator(r, c)) return false;
  return r === startRow.value && c === startCol.value;
}

function isSelEdgeTop(r: number, c: number): boolean {
  return isCellInSelection(r, c) && r === selMinRow.value;
}

function isSelEdgeBottom(r: number, c: number): boolean {
  return isCellInSelection(r, c) && r === selMaxRow.value;
}

function isSelEdgeLeft(r: number, c: number): boolean {
  return isCellInSelection(r, c) && c === selMinCol.value;
}

function isSelEdgeRight(r: number, c: number): boolean {
  return isCellInSelection(r, c) && c === selMaxCol.value;
}

function isSelectionBottomRightCorner(r: number, c: number): boolean {
  if (getLockingCollaborator(r, c)) return false;
  return r === selMaxRow.value && c === selMaxCol.value;
}

function isColSelected(c: number): boolean {
  return c >= selMinCol.value && c <= selMaxCol.value && selMinRow.value === 0 && selMaxRow.value === rowCount.value - 1;
}

function isRowSelected(r: number): boolean {
  return r >= selMinRow.value && r <= selMaxRow.value && selMinCol.value === 0 && selMaxCol.value === colCount.value - 1;
}

function isCellFindMatched(r: number, c: number): boolean {
  return matchedCells.value.some(m => m.r === r && m.c === c);
}

// ── Formula Evaluator Engine ──────────────────────────
function evaluateFormula(formulaStr: string, sheet: Sheet, visited = new Set<string>()): any {
  if (!formulaStr.startsWith("=")) return formulaStr;
  const expr = formulaStr.slice(1).trim();

  const sumMatch = expr.match(/^SUM\(([A-Z]+[0-9]+):([A-Z]+[0-9]+)\)$/i);
  if (sumMatch) {
    const vals = getRangeValues(sumMatch[1]!, sumMatch[2]!, sheet, visited);
    return vals.reduce((acc, curr) => acc + (Number(curr) || 0), 0);
  }

  const avgMatch = expr.match(/^AVERAGE\(([A-Z]+[0-9]+):([A-Z]+[0-9]+)\)$/i);
  if (avgMatch) {
    const vals = getRangeValues(avgMatch[1]!, avgMatch[2]!, sheet, visited);
    if (!vals.length) return 0;
    const sum = vals.reduce((acc, curr) => acc + (Number(curr) || 0), 0);
    return (sum / vals.length).toFixed(2);
  }

  const countMatch = expr.match(/^COUNT\(([A-Z]+[0-9]+):([A-Z]+[0-9]+)\)$/i);
  if (countMatch) {
    const vals = getRangeValues(countMatch[1]!, countMatch[2]!, sheet, visited);
    return vals.filter(v => v !== "" && v !== null && v !== undefined).length;
  }

  const maxMatch = expr.match(/^MAX\(([A-Z]+[0-9]+):([A-Z]+[0-9]+)\)$/i);
  if (maxMatch) {
    const vals = getRangeValues(maxMatch[1]!, maxMatch[2]!, sheet, visited).map(Number).filter(n => !isNaN(n));
    return vals.length ? Math.max(...vals) : 0;
  }

  const minMatch = expr.match(/^MIN\(([A-Z]+[0-9]+):([A-Z]+[0-9]+)\)$/i);
  if (minMatch) {
    const vals = getRangeValues(minMatch[1]!, minMatch[2]!, sheet, visited).map(Number).filter(n => !isNaN(n));
    return vals.length ? Math.min(...vals) : 0;
  }

  try {
    const replaced = expr.replace(/([A-Z]+)([0-9]+)/g, (_match, colPart, rowPart) => {
      const c = colNameToIndex(colPart);
      const r = parseInt(rowPart, 10) - 1;
      const cellVal = getRawCellValue(r, c, sheet, visited);
      const num = Number(cellVal);
      return isNaN(num) ? "0" : String(num);
    });
    if (/^[0-9+\-*/().\s]+$/.test(replaced)) {
      return Function(`"use strict"; return (${replaced})`)();
    }
  } catch {
    return "#VALUE!";
  }

  return formulaStr;
}

function getRangeValues(startAddr: string, endAddr: string, sheet: Sheet, visited: Set<string>): any[] {
  const m1 = startAddr.match(/([A-Z]+)([0-9]+)/i);
  const m2 = endAddr.match(/([A-Z]+)([0-9]+)/i);
  if (!m1 || !m2) return [];
  const c1 = colNameToIndex(m1[1]!.toUpperCase());
  const r1 = parseInt(m1[2]!, 10) - 1;
  const c2 = colNameToIndex(m2[1]!.toUpperCase());
  const r2 = parseInt(m2[2]!, 10) - 1;

  const minR = Math.min(r1, r2);
  const maxR = Math.max(r1, r2);
  const minC = Math.min(c1, c2);
  const maxC = Math.max(c1, c2);

  const values: any[] = [];
  for (let r = minR; r <= maxR; r++) {
    for (let c = minC; c <= maxC; c++) {
      values.push(getRawCellValue(r, c, sheet, visited));
    }
  }
  return values;
}

function getRawCellValue(r: number, c: number, sheet: Sheet, visited: Set<string>): any {
  const key = `${r}_${c}`;
  if (visited.has(key)) return 0;
  const cell = sheet?.cells?.[key];
  if (!cell) return 0;
  if (cell.f) {
    visited.add(key);
    const result = evaluateFormula(cell.f, sheet, visited);
    visited.delete(key);
    return result;
  }
  return cell.v ?? 0;
}

function getCellDisplayValue(r: number, c: number): string {
  const sheet = currentSheet.value;
  if (!sheet) return "";
  const key = `${r}_${c}`;
  const cell = sheet.cells?.[key];
  if (!cell) return "";
  if (cell.f) {
    const computed = evaluateFormula(cell.f, sheet);
    return computed !== undefined && computed !== null ? String(computed) : "";
  }
  return cell.m || (cell.v !== undefined && cell.v !== null ? String(cell.v) : "");
}

// ── Undo / Redo History Stack ─────────────────────────
function pushUndoState() {
  const snapshot = JSON.stringify(workbook.value);
  undoStack.value.push(snapshot);
  if (undoStack.value.length > 30) {
    undoStack.value.shift();
  }
  redoStack.value = [];
}

function undo() {
  if (!undoStack.value.length) return;
  const currentSnapshot = JSON.stringify(workbook.value);
  redoStack.value.push(currentSnapshot);
  const previous = undoStack.value.pop()!;
  workbook.value = JSON.parse(previous);
  scheduleAutoSave();
  ElMessage.info("已撤销");
}

function redo() {
  if (!redoStack.value.length) return;
  const currentSnapshot = JSON.stringify(workbook.value);
  undoStack.value.push(currentSnapshot);
  const nextState = redoStack.value.pop()!;
  workbook.value = JSON.parse(nextState);
  scheduleAutoSave();
  ElMessage.info("已重做");
}

// ── Selection & Mouse Drag Handlers ───────────────────
function onCellMouseDown(r: number, c: number, event: MouseEvent) {
  // If currently in-place editing another cell, commit its value immediately before moving selection!
  if (isEditing.value) {
    commitCellEdit();
  }

  // 🔒 严格禁止选中他人已占用的锁定单元格，避免选框重叠
  const locker = getLockingCollaborator(r, c);
  if (locker) {
    isSelecting.value = false;
    ElMessage({
      message: `该单元格已被 [${locker.name}] 占用，禁止选中！`,
      type: "warning",
      duration: 1500
    });
    return;
  }

  if (event.button === 2) {
    if (!isCellInSelection(r, c)) {
      startRow.value = r;
      startCol.value = c;
      endRow.value = r;
      endCol.value = c;
    }
    return;
  }

  contextMenuVisible.value = false;

  if (isFormatPainting.value && copiedStyle.value) {
    pushUndoState();
    const key = `${r}_${c}`;
    if (!currentSheet.value.styles) currentSheet.value.styles = {};
    currentSheet.value.styles[key] = JSON.parse(JSON.stringify(copiedStyle.value));
    isFormatPainting.value = false;
    copiedStyle.value = null;
    scheduleAutoSave();
    ElMessage.success("已应用格式");
    return;
  }

  isSelecting.value = true;

  // Handle Merged Cell click: select the whole merged bounding box
  const mergeInfo = getCellMergeInfo(r, c);
  if (mergeInfo.isMaster) {
    startRow.value = r;
    startCol.value = c;
    endRow.value = r + mergeInfo.rs - 1;
    endCol.value = c + mergeInfo.cs - 1;
  } else if (mergeInfo.isSlave) {
    const master = currentSheet.value?.mergedCells?.find(m => r >= m.r && r < m.r + m.rs && c >= m.c && c < m.c + m.cs);
    if (master) {
      startRow.value = master.r;
      startCol.value = master.c;
      endRow.value = master.r + master.rs - 1;
      endCol.value = master.c + master.cs - 1;
      r = master.r;
      c = master.c;
    } else {
      startRow.value = r;
      startCol.value = c;
      endRow.value = r;
      endCol.value = c;
    }
  } else {
    startRow.value = r;
    startCol.value = c;
    endRow.value = r;
    endCol.value = c;
  }

  const key = `${r}_${c}`;
  const cell = currentSheet.value?.cells?.[key];
  activeCellFormula.value = cell?.f || (cell?.v !== undefined && cell?.v !== null ? String(cell.v) : "");
  broadcastAwareness();

  // Listen to window drag events for continuous boundary auto-scroll
  lastDragMouseX = event.clientX;
  lastDragMouseY = event.clientY;
  window.addEventListener("mousemove", onWindowDragMouseMove);
  window.addEventListener("mouseup", onWindowDragMouseUp);
}

// ── Auto-Scroll During Drag Selection ─────────────────
let autoScrollAnimFrame: number | null = null;
let lastDragMouseX = 0;
let lastDragMouseY = 0;

function getCellAtScrollCoords(relX: number, relY: number): { r: number; c: number } {
  const rowTotal = currentSheet.value?.rowCount || 60;
  const colTotal = currentSheet.value?.colCount || 26;

  let currY = 0;
  let r = 0;
  while (r < rowTotal - 1) {
    const h = getRowHeight(r);
    if (currY + h > relY) break;
    currY += h;
    r++;
  }

  let currX = 0;
  let c = 0;
  while (c < colTotal - 1) {
    const w = getColumnWidth(c);
    if (currX + w > relX) break;
    currX += w;
    c++;
  }

  return {
    r: Math.max(0, Math.min(rowTotal - 1, r)),
    c: Math.max(0, Math.min(colTotal - 1, c))
  };
}

function updateSelectionFromMousePos(clientX: number, clientY: number) {
  const container = gridContainerRef.value;
  if (!container || !currentSheet.value) return;

  const rect = container.getBoundingClientRect();
  const rowHeaderWidth = 46;
  const colHeaderHeight = 24;

  // Relative coordinate inside the table body content
  const relX = container.scrollLeft + (clientX - rect.left) - rowHeaderWidth;
  const relY = container.scrollTop + (clientY - rect.top) - colHeaderHeight;

  const cell = getCellAtScrollCoords(relX, relY);

  if (isSelecting.value) {
    endRow.value = cell.r;
    endCol.value = cell.c;
  }
}

function startAutoScrollLoop() {
  if (autoScrollAnimFrame !== null) return;

  function step() {
    if (!isSelecting.value && !isDraggingFill.value) {
      stopAutoScrollLoop();
      return;
    }

    const container = gridContainerRef.value;
    if (container) {
      const rect = container.getBoundingClientRect();
      const edgeThreshold = 45; // distance from edge in px to trigger auto-scroll
      let scrollDeltaX = 0;
      let scrollDeltaY = 0;

      // Bottom edge: scroll down
      if (lastDragMouseY > rect.bottom - edgeThreshold) {
        const dist = lastDragMouseY - (rect.bottom - edgeThreshold);
        scrollDeltaY = Math.min(35, Math.max(4, dist * 0.4));
      } 
      // Top edge: scroll up
      else if (lastDragMouseY < rect.top + 24 + edgeThreshold && lastDragMouseY > 0) {
        const dist = (rect.top + 24 + edgeThreshold) - lastDragMouseY;
        scrollDeltaY = -Math.min(35, Math.max(4, dist * 0.4));
      }

      // Right edge: scroll right
      if (lastDragMouseX > rect.right - edgeThreshold) {
        const dist = lastDragMouseX - (rect.right - edgeThreshold);
        scrollDeltaX = Math.min(35, Math.max(4, dist * 0.4));
      } 
      // Left edge: scroll left
      else if (lastDragMouseX < rect.left + 46 + edgeThreshold && lastDragMouseX > 0) {
        const dist = (rect.left + 46 + edgeThreshold) - lastDragMouseX;
        scrollDeltaX = -Math.min(35, Math.max(4, dist * 0.4));
      }

      if (scrollDeltaX !== 0 || scrollDeltaY !== 0) {
        container.scrollLeft += scrollDeltaX;
        container.scrollTop += scrollDeltaY;
        // As the table scrolls, the cell under the mouse changes, update selection immediately!
        updateSelectionFromMousePos(lastDragMouseX, lastDragMouseY);
      }
    }

    autoScrollAnimFrame = requestAnimationFrame(step);
  }

  autoScrollAnimFrame = requestAnimationFrame(step);
}

function stopAutoScrollLoop() {
  if (autoScrollAnimFrame !== null) {
    cancelAnimationFrame(autoScrollAnimFrame);
    autoScrollAnimFrame = null;
  }
}

function onWindowDragMouseMove(e: MouseEvent) {
  if (!isSelecting.value && !isDraggingFill.value) return;

  lastDragMouseX = e.clientX;
  lastDragMouseY = e.clientY;

  // Update selection under current mouse position
  updateSelectionFromMousePos(e.clientX, e.clientY);

  // Check if near edge to run auto-scroll
  const container = gridContainerRef.value;
  if (container) {
    const rect = container.getBoundingClientRect();
    const edgeThreshold = 45;
    const isNearEdge =
      e.clientY > rect.bottom - edgeThreshold ||
      (e.clientY < rect.top + 24 + edgeThreshold && e.clientY > 0) ||
      e.clientX > rect.right - edgeThreshold ||
      (e.clientX < rect.left + 46 + edgeThreshold && e.clientX > 0);

    if (isNearEdge) {
      startAutoScrollLoop();
    } else {
      stopAutoScrollLoop();
    }
  }
}

function onWindowDragMouseUp() {
  stopAutoScrollLoop();
  onGlobalMouseUp();
  window.removeEventListener("mousemove", onWindowDragMouseMove);
  window.removeEventListener("mouseup", onWindowDragMouseUp);
}

function onCellMouseEnter(r: number, c: number) {
  if (isSelecting.value) {
    endRow.value = r;
    endCol.value = c;
  }
}

function onGlobalMouseUp() {
  stopAutoScrollLoop();
  isSelecting.value = false;
  isDraggingFill.value = false;
  window.removeEventListener("mousemove", onWindowDragMouseMove);
  window.removeEventListener("mouseup", onWindowDragMouseUp);
  
  if (isColResizing.value) {
    isColResizing.value = false;
    scheduleAutoSave();
    broadcastDimensions();
  }
  if (isRowResizing.value) {
    isRowResizing.value = false;
    scheduleAutoSave();
    broadcastDimensions();
  }
}

function selectAllCells() {
  startRow.value = 0;
  startCol.value = 0;
  endRow.value = rowCount.value - 1;
  endCol.value = colCount.value - 1;
}

function selectRow(r: number, event: MouseEvent) {
  if (event.shiftKey) {
    endRow.value = r;
  } else {
    startRow.value = r;
    endRow.value = r;
  }
  startCol.value = 0;
  endCol.value = colCount.value - 1;
}

function selectColumn(c: number, event: MouseEvent) {
  if (event.shiftKey) {
    endCol.value = c;
  } else {
    startCol.value = c;
    endCol.value = c;
  }
  startRow.value = 0;
  endRow.value = rowCount.value - 1;
}

// ── In-place Editing ──────────────────────────────────
function focusAndPositionTextarea(placeCursorAtEnd: boolean = true) {
  nextTick(() => {
    const el = document.querySelector(".cell-inline-textarea") as HTMLTextAreaElement | null;
    if (el) {
      el.focus();
      if (placeCursorAtEnd) {
        const len = el.value.length;
        el.setSelectionRange(len, len);
      }
      autoResizeTextarea(el);
    }
  });
}

function autoResizeTextarea(el: HTMLTextAreaElement | null) {
  if (!el) return;
  el.style.height = "auto";
  el.style.height = Math.max(26, el.scrollHeight) + "px";
}

function onInlineTextareaInput(e: Event) {
  const el = e.target as HTMLTextAreaElement;
  activeCellFormula.value = el.value;
  autoResizeTextarea(el);
}

function handleCellShiftEnterPress(e: KeyboardEvent) {
  e.preventDefault();
  const el = (e.target as HTMLTextAreaElement) || document.querySelector(".cell-inline-textarea");
  if (!el) return;
  const start = el.selectionStart || 0;
  const end = el.selectionEnd || 0;
  const val = activeCellFormula.value || "";
  activeCellFormula.value = val.substring(0, start) + "\n" + val.substring(end);
  nextTick(() => {
    el.selectionStart = el.selectionEnd = start + 1;
    autoResizeTextarea(el as HTMLTextAreaElement);
  });
}

function handleCellEnterPress(e: KeyboardEvent) {
  e.preventDefault();
  commitActiveCell();
  if (startRow.value < rowCount.value - 1) {
    tryMoveSelection(startRow.value + 1, startCol.value);
  }
}

function onCellDoubleClick(r: number, c: number) {
  if (!canEdit.value) return;
  const locker = getLockingCollaborator(r, c);
  if (locker) {
    ElMessage.warning(`该单元格当前正由 [${locker.name}] 编辑，已被锁定保护！`);
    return;
  }
  startRow.value = r;
  startCol.value = c;
  endRow.value = r;
  endCol.value = c;
  editingRow.value = r;
  editingCol.value = c;
  const key = `${r}_${c}`;
  const cell = currentSheet.value?.cells?.[key];
  activeCellFormula.value = cell?.f || (cell?.v !== undefined && cell?.v !== null ? String(cell.v) : "");
  isEditing.value = true;
  focusAndPositionTextarea(true);
}

function startEditingWithChar(r: number, c: number, char: string) {
  if (!canEdit.value) return;
  const locker = getLockingCollaborator(r, c);
  if (locker) {
    ElMessage.warning(`该单元格已被 [${locker.name}] 锁定，禁止覆盖编辑！`);
    return;
  }
  startRow.value = r;
  startCol.value = c;
  endRow.value = r;
  endCol.value = c;
  editingRow.value = r;
  editingCol.value = c;
  activeCellFormula.value = char;
  isEditing.value = true;
  focusAndPositionTextarea(true);
}

function commitCellEdit() {
  if (!isEditing.value || !canEdit.value || !currentSheet.value) {
    isEditing.value = false;
    return;
  }
  const r = editingRow.value;
  const c = editingCol.value;
  isEditing.value = false;
  
  if (r < 0 || c < 0) return;
  pushUndoState();
  const key = `${r}_${c}`;
  if (!currentSheet.value.cells) currentSheet.value.cells = {};
  
  const val = activeCellFormula.value;
  if (val === "" || val === undefined || val === null) {
    delete currentSheet.value.cells[key];
  } else if (typeof val === "string" && val.startsWith("=")) {
    currentSheet.value.cells[key] = { f: val, t: "f" };
  } else {
    const num = Number(val);
    const isNum = !isNaN(num) && String(val).trim() !== "";
    currentSheet.value.cells[key] = {
      v: isNum ? num : val,
      m: String(val),
      t: isNum ? "n" : "s"
    };
  }
  scheduleAutoSave();
  broadcastCellUpdate(r, c, currentSheet.value.cells[key]);
}

function onFormulaInputChange() {
  if (!canEdit.value || !currentSheet.value) return;
  const locker = getLockingCollaborator(startRow.value, startCol.value);
  if (locker) {
    ElMessage.warning(`该单元格已被 [${locker.name}] 锁定保护，无法修改！`);
    return;
  }
  pushUndoState();
  const key = `${startRow.value}_${startCol.value}`;
  if (!currentSheet.value.cells) currentSheet.value.cells = {};
  
  const val = activeCellFormula.value;
  if (val === "" || val === undefined || val === null) {
    delete currentSheet.value.cells[key];
  } else if (typeof val === "string" && val.startsWith("=")) {
    currentSheet.value.cells[key] = { f: val, t: "f" };
  } else {
    const num = Number(val);
    const isNum = !isNaN(num) && String(val).trim() !== "";
    currentSheet.value.cells[key] = {
      v: isNum ? num : val,
      m: String(val),
      t: isNum ? "n" : "s"
    };
  }
  scheduleAutoSave();
  broadcastCellUpdate(startRow.value, startCol.value, currentSheet.value.cells[key]);
}

function commitActiveCell() {
  if (isEditing.value) {
    commitCellEdit();
  } else {
    onFormulaInputChange();
  }
}

function cancelCellEdit() {
  isEditing.value = false;
  const key = `${startRow.value}_${startCol.value}`;
  const cell = currentSheet.value?.cells?.[key];
  activeCellFormula.value = cell?.f || (cell?.v !== undefined && cell?.v !== null ? String(cell.v) : "");
}

function moveNextCell() {
  commitActiveCell();
  let nextR = startRow.value;
  let nextC = startCol.value + 1;
  if (nextC >= colCount.value) {
    nextC = 0;
    nextR++;
  }
  if (nextR < rowCount.value) {
    tryMoveSelection(nextR, nextC);
  }
}

function insertFormula(fnName: string) {
  activeCellFormula.value = `=${fnName}(A1:A5)`;
  onFormulaInputChange();
  formulaInputRef.value?.focus();
}

// ── Merge & Unmerge Cells ─────────────────────────────
function toggleMergeCells() {
  if (!canEdit.value || !currentSheet.value) return;
  if (isEditing.value) commitCellEdit();

  const r1 = selMinRow.value;
  const r2 = selMaxRow.value;
  const c1 = selMinCol.value;
  const c2 = selMaxCol.value;

  // 🔒 协同编辑并发保护：校验选区内是否包含他人正在编辑的单元格
  for (let r = r1; r <= r2; r++) {
    for (let c = c1; c <= c2; c++) {
      const locker = getLockingCollaborator(r, c);
      if (locker) {
        ElMessage.warning(`选区包含正由 [${locker.name}] 编辑的单元格，已锁定保护无法执行合并/拆分！`);
        return;
      }
    }
  }

  pushUndoState();
  contextMenuVisible.value = false;

  if (!currentSheet.value.mergedCells) currentSheet.value.mergedCells = [];

  // Check if current selection intersects with ANY existing merged cell
  const intersectingIndices: number[] = [];
  currentSheet.value.mergedCells.forEach((m, idx) => {
    const mr1 = m.r;
    const mr2 = m.r + m.rs - 1;
    const mc1 = m.c;
    const mc2 = m.c + m.cs - 1;
    const hasOverlap = !(r2 < mr1 || r1 > mr2 || c2 < mc1 || c1 > mc2);
    if (hasOverlap) {
      intersectingIndices.push(idx);
    }
  });

  if (intersectingIndices.length > 0) {
    // If overlapping any merged cells, unmerge / split them!
    currentSheet.value.mergedCells = currentSheet.value.mergedCells.filter((_, idx) => !intersectingIndices.includes(idx));
    scheduleAutoSave();
    broadcastMergedCells();
    ElMessage.success("已拆分单元格");
    return;
  }

  // Otherwise, merge selection (must span >= 2 cells)
  const rs = r2 - r1 + 1;
  const cs = c2 - c1 + 1;
  if (rs <= 1 && cs <= 1) {
    ElMessage.warning("请先框选多个单元格再进行合并");
    return;
  }

  currentSheet.value.mergedCells.push({
    r: r1,
    c: c1,
    rs,
    cs
  });

  // Apply default center alignment to merged cell master
  if (!currentSheet.value.styles) currentSheet.value.styles = {};
  const masterKey = `${r1}_${c1}`;
  currentSheet.value.styles[masterKey] = {
    ...(currentSheet.value.styles[masterKey] || {}),
    ht: "center",
    vt: "middle"
  };

  scheduleAutoSave();
  broadcastMergedCells();
  ElMessage.success("已合并居中单元格");
}

function unmergeCells() {
  if (!canEdit.value || !currentSheet.value) return;
  if (!currentSheet.value.mergedCells) return;

  const r1 = selMinRow.value;
  const r2 = selMaxRow.value;
  const c1 = selMinCol.value;
  const c2 = selMaxCol.value;

  // 🔒 协同编辑并发保护
  for (let r = r1; r <= r2; r++) {
    for (let c = c1; c <= c2; c++) {
      const locker = getLockingCollaborator(r, c);
      if (locker) {
        ElMessage.warning(`选区包含正由 [${locker.name}] 编辑的单元格，已锁定保护无法拆分！`);
        return;
      }
    }
  }

  pushUndoState();
  currentSheet.value.mergedCells = currentSheet.value.mergedCells.filter(m => {
    const mr1 = m.r;
    const mr2 = m.r + m.rs - 1;
    const mc1 = m.c;
    const mc2 = m.c + m.cs - 1;
    return (r2 < mr1 || r1 > mr2 || c2 < mc1 || c1 > mc2);
  });
  scheduleAutoSave();
  broadcastMergedCells();
  ElMessage.success("已拆分单元格");
}

// ── Font & Alignment Formatting ───────────────────────
function setFontFamily(ff: string) {
  if (!canEdit.value || !currentSheet.value) return;
  pushUndoState();
  if (!currentSheet.value.styles) currentSheet.value.styles = {};

  let skippedCount = 0;
  for (let r = selMinRow.value; r <= selMaxRow.value; r++) {
    for (let c = selMinCol.value; c <= selMaxCol.value; c++) {
      if (getLockingCollaborator(r, c)) { skippedCount++; continue; }
      const key = `${r}_${c}`;
      currentSheet.value.styles[key] = { ...(currentSheet.value.styles[key] || {}), ff };
    }
  }
  scheduleAutoSave();
  broadcastStyles();
  if (skippedCount > 0) ElMessage.warning(`已自动保护跳过 ${skippedCount} 个他人锁定的单元格`);
}

function setFontSize(size: number) {
  if (!canEdit.value || !currentSheet.value) return;
  pushUndoState();
  if (!currentSheet.value.styles) currentSheet.value.styles = {};

  let skippedCount = 0;
  for (let r = selMinRow.value; r <= selMaxRow.value; r++) {
    for (let c = selMinCol.value; c <= selMaxCol.value; c++) {
      if (getLockingCollaborator(r, c)) { skippedCount++; continue; }
      const key = `${r}_${c}`;
      currentSheet.value.styles[key] = { ...(currentSheet.value.styles[key] || {}), fs: size };
    }
  }
  scheduleAutoSave();
  broadcastStyles();
  if (skippedCount > 0) ElMessage.warning(`已自动保护跳过 ${skippedCount} 个他人锁定的单元格`);
}

function stepFontSize(delta: number) {
  const current = currentFontSize.value || 11;
  const next = Math.max(8, Math.min(72, current + delta));
  setFontSize(next);
}

function toggleStyle(prop: keyof CellStyle) {
  if (!canEdit.value || !currentSheet.value) return;
  pushUndoState();
  if (!currentSheet.value.styles) currentSheet.value.styles = {};

  const currentVal = currentCellStyle.value[prop];
  const newVal = currentVal ? 0 : 1;

  let skippedCount = 0;
  for (let r = selMinRow.value; r <= selMaxRow.value; r++) {
    for (let c = selMinCol.value; c <= selMaxCol.value; c++) {
      if (getLockingCollaborator(r, c)) { skippedCount++; continue; }
      const key = `${r}_${c}`;
      currentSheet.value.styles[key] = { ...(currentSheet.value.styles[key] || {}), [prop]: newVal };
    }
  }
  scheduleAutoSave();
  broadcastStyles();
  if (skippedCount > 0) ElMessage.warning(`已自动保护跳过 ${skippedCount} 个他人锁定的单元格`);
}

function setCellColor(prop: "fc" | "bg", color: string) {
  if (!canEdit.value || !currentSheet.value) return;
  pushUndoState();
  if (!currentSheet.value.styles) currentSheet.value.styles = {};

  let skippedCount = 0;
  for (let r = selMinRow.value; r <= selMaxRow.value; r++) {
    for (let c = selMinCol.value; c <= selMaxCol.value; c++) {
      if (getLockingCollaborator(r, c)) { skippedCount++; continue; }
      const key = `${r}_${c}`;
      currentSheet.value.styles[key] = { ...(currentSheet.value.styles[key] || {}), [prop]: color };
    }
  }
  scheduleAutoSave();
  broadcastStyles();
  if (skippedCount > 0) ElMessage.warning(`已自动保护跳过 ${skippedCount} 个他人锁定的单元格`);
}

function setCellAlign(align: "left" | "center" | "right") {
  if (!canEdit.value || !currentSheet.value) return;
  pushUndoState();
  if (!currentSheet.value.styles) currentSheet.value.styles = {};

  let skippedCount = 0;
  for (let r = selMinRow.value; r <= selMaxRow.value; r++) {
    for (let c = selMinCol.value; c <= selMaxCol.value; c++) {
      if (getLockingCollaborator(r, c)) { skippedCount++; continue; }
      const key = `${r}_${c}`;
      currentSheet.value.styles[key] = { ...(currentSheet.value.styles[key] || {}), ht: align };
    }
  }
  scheduleAutoSave();
  broadcastStyles();
  if (skippedCount > 0) ElMessage.warning(`已自动保护跳过 ${skippedCount} 个他人锁定的单元格`);
}

function setCellVAlign(valign: "top" | "middle" | "bottom") {
  if (!canEdit.value || !currentSheet.value) return;
  pushUndoState();
  if (!currentSheet.value.styles) currentSheet.value.styles = {};

  let skippedCount = 0;
  for (let r = selMinRow.value; r <= selMaxRow.value; r++) {
    for (let c = selMinCol.value; c <= selMaxCol.value; c++) {
      if (getLockingCollaborator(r, c)) { skippedCount++; continue; }
      const key = `${r}_${c}`;
      currentSheet.value.styles[key] = { ...(currentSheet.value.styles[key] || {}), vt: valign };
    }
  }
  scheduleAutoSave();
  broadcastStyles();
  if (skippedCount > 0) ElMessage.warning(`已自动保护跳过 ${skippedCount} 个他人锁定的单元格`);
}

function toggleTextWrap() {
  if (!canEdit.value || !currentSheet.value) return;
  pushUndoState();
  if (!currentSheet.value.styles) currentSheet.value.styles = {};

  const currentWrap = currentCellStyle.value.tb === 1 ? 0 : 1;
  let skippedCount = 0;
  for (let r = selMinRow.value; r <= selMaxRow.value; r++) {
    for (let c = selMinCol.value; c <= selMaxCol.value; c++) {
      if (getLockingCollaborator(r, c)) { skippedCount++; continue; }
      const key = `${r}_${c}`;
      currentSheet.value.styles[key] = { ...(currentSheet.value.styles[key] || {}), tb: currentWrap };
    }
  }
  scheduleAutoSave();
  broadcastStyles();
  if (skippedCount > 0) ElMessage.warning(`已自动保护跳过 ${skippedCount} 个他人锁定的单元格`);
}

function toggleFormatPainter() {
  if (isFormatPainting.value) {
    isFormatPainting.value = false;
    copiedStyle.value = null;
  } else {
    isFormatPainting.value = true;
    copiedStyle.value = JSON.parse(JSON.stringify(currentCellStyle.value));
    ElMessage.info("已复制格式，请点击目标单元格涂抹");
  }
}

// ── Number & Data Formatting ──────────────────────────
function applyNumberFormat(fmt: string) {
  if (!canEdit.value || !currentSheet.value) return;
  pushUndoState();

  for (let r = selMinRow.value; r <= selMaxRow.value; r++) {
    for (let c = selMinCol.value; c <= selMaxCol.value; c++) {
      const key = `${r}_${c}`;
      const cell = currentSheet.value.cells?.[key];
      if (!cell || cell.v === undefined) continue;

      cell.nf = fmt;
      const num = Number(cell.v);
      if (fmt === "currency_cny" && !isNaN(num)) {
        cell.m = `¥${num.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
      } else if (fmt === "percent" && !isNaN(num)) {
        cell.m = `${(num * (num < 1 ? 100 : 1)).toFixed(2)}%`;
      } else if (fmt === "comma" && !isNaN(num)) {
        cell.m = num.toLocaleString();
      } else if (fmt === "inc_decimal" && !isNaN(num)) {
        cell.m = num.toFixed(3);
      } else if (fmt === "dec_decimal" && !isNaN(num)) {
        cell.m = num.toFixed(1);
      } else if (fmt === "general") {
        cell.m = String(cell.v);
      }
    }
  }

  scheduleAutoSave();
  ElMessage.success("已应用数字格式");
}

// ── Full Borders System ───────────────────────────────
function applyBorder(type: string) {
  if (!canEdit.value || !currentSheet.value) return;
  pushUndoState();
  if (!currentSheet.value.styles) currentSheet.value.styles = {};

  const color = "#000000";
  const border1px = `1px solid ${color}`;
  const border2px = `2px solid ${color}`;

  for (let r = selMinRow.value; r <= selMaxRow.value; r++) {
    for (let c = selMinCol.value; c <= selMaxCol.value; c++) {
      const key = `${r}_${c}`;
      const st = currentSheet.value.styles[key] || {};
      const bd: CellBorders = { ...(st.bd || {}) };

      if (type === "all") {
        bd.t = border1px;
        bd.b = border1px;
        bd.l = border1px;
        bd.r = border1px;
      } else if (type === "thick") {
        if (r === selMinRow.value) bd.t = border2px;
        if (r === selMaxRow.value) bd.b = border2px;
        if (c === selMinCol.value) bd.l = border2px;
        if (c === selMaxCol.value) bd.r = border2px;
      } else if (type === "outer") {
        if (r === selMinRow.value) bd.t = border1px;
        if (r === selMaxRow.value) bd.b = border1px;
        if (c === selMinCol.value) bd.l = border1px;
        if (c === selMaxCol.value) bd.r = border1px;
      } else if (type === "top") {
        if (r === selMinRow.value) bd.t = border1px;
      } else if (type === "bottom") {
        if (r === selMaxRow.value) bd.b = border1px;
      } else if (type === "left") {
        if (c === selMinCol.value) bd.l = border1px;
      } else if (type === "right") {
        if (c === selMaxCol.value) bd.r = border1px;
      } else if (type === "none") {
        delete st.bd;
      }

      if (type !== "none") {
        st.bd = bd;
      }
      currentSheet.value.styles[key] = st;
    }
  }

  scheduleAutoSave();
  broadcastStyles();
  ElMessage.success("边框已设置");
}

// ── Conditional Formatting Rules ──────────────────────
async function applyConditionalFormat(type: string) {
  if (!canEdit.value || !currentSheet.value) return;
  if (!currentSheet.value.cfRules) currentSheet.value.cfRules = [];

  if (type === "clear") {
    pushUndoState();
    currentSheet.value.cfRules = currentSheet.value.cfRules.filter(
      r => !(r.r1 >= selMinRow.value && r.r2 <= selMaxRow.value && r.c1 >= selMinCol.value && r.c2 <= selMaxCol.value)
    );
    scheduleAutoSave();
    return ElMessage.success("已清除选中区域的条件格式");
  }

  if (type === "databar" || type === "colorscale") {
    pushUndoState();
    currentSheet.value.cfRules.push({
      id: `cf_${Date.now()}`,
      type: type as any,
      r1: selMinRow.value,
      c1: selMinCol.value,
      r2: selMaxRow.value,
      c2: selMaxCol.value
    });
    scheduleAutoSave();
    return ElMessage.success("已应用视觉格式");
  }

  try {
    const { value } = await ElMessageBox.prompt(
      type === "contains" ? "请输入包含的文本：" : "请输入阈值数值：",
      "配置条件格式",
      { confirmButtonText: "确定", cancelButtonText: "取消" }
    );
    if (value !== null && value !== undefined) {
      pushUndoState();
      currentSheet.value.cfRules.push({
        id: `cf_${Date.now()}`,
        type: type as any,
        val: value,
        r1: selMinRow.value,
        c1: selMinCol.value,
        r2: selMaxRow.value,
        c2: selMaxCol.value
      });
      scheduleAutoSave();
      ElMessage.success("已添加条件格式规则");
    }
  } catch {}
}

// ── Cells Insert / Delete / AutoFit ───────────────────
function handleCellInsert(cmd: string) {
  if (cmd === "row" || cmd === "row_above") insertRowAbove();
  else if (cmd === "row_below") insertRowBelow();
  else if (cmd === "col" || cmd === "col_left") insertColLeft();
  else if (cmd === "col_right") insertColRight();
}

function handleCellDelete(cmd: string) {
  if (cmd === "row") deleteCurrentRow();
  else if (cmd === "col") deleteCurrentCol();
}

function autoFitCurrentCol() {
  autoFitColumnWidth(startCol.value);
}

function handleSortFilterCmd(cmd: string) {
  if (cmd === "sort_asc") sortSelection("asc");
  else if (cmd === "sort_desc") sortSelection("desc");
  else if (cmd === "filter") toggleAutoFilter();
}

// ── Freeze Panes ──────────────────────────────────────
function toggleFreezePane(command: string) {
  if (command === "top") {
    isFrozenTopRow.value = !isFrozenTopRow.value;
    ElMessage.info(isFrozenTopRow.value ? "已冻结首行" : "已解冻首行");
  } else if (command === "first_col") {
    isFrozenFirstCol.value = !isFrozenFirstCol.value;
    ElMessage.info(isFrozenFirstCol.value ? "已冻结首列" : "已解冻首列");
  } else if (command === "unfreeze") {
    isFrozenTopRow.value = false;
    isFrozenFirstCol.value = false;
    ElMessage.info("已取消所有冻结");
  }
}

// ── Auto Filter ───────────────────────────────────────
function toggleAutoFilter() {
  isFilterEnabled.value = !isFilterEnabled.value;
  if (!isFilterEnabled.value) {
    columnFilters.value = {};
    ElMessage.info("已关闭数据筛选");
  } else {
    ElMessage.success("已开启表头数据筛选");
  }
}

function openFilterDropdown(colIdx: number, e: MouseEvent) {
  activeFilterCol.value = colIdx;
  filterSearchText.value = "";
  filterDropdownX.value = e.clientX;
  filterDropdownY.value = e.clientY + 12;
  filterDropdownVisible.value = true;
}

const uniqueValuesInActiveCol = computed(() => {
  if (activeFilterCol.value === null) return [];
  const set = new Set<string>();
  for (let r = 1; r < rowCount.value; r++) {
    set.add(getCellDisplayValue(r, activeFilterCol.value));
  }
  return Array.from(set);
});

const filteredUniqueValues = computed(() => {
  const search = filterSearchText.value.toLowerCase();
  return uniqueValuesInActiveCol.value.filter(v => v.toLowerCase().includes(search));
});

function isFilterValueExcluded(val: string): boolean {
  if (activeFilterCol.value === null) return false;
  return columnFilters.value[activeFilterCol.value]?.has(val) || false;
}

function toggleFilterValueItem(val: string) {
  if (activeFilterCol.value === null) return;
  if (!columnFilters.value[activeFilterCol.value]) {
    columnFilters.value[activeFilterCol.value] = new Set();
  }
  const set = columnFilters.value[activeFilterCol.value]!;
  if (set.has(val)) {
    set.delete(val);
  } else {
    set.add(val);
  }
}

function selectAllFilterValues() {
  if (activeFilterCol.value === null) return;
  columnFilters.value[activeFilterCol.value] = new Set();
}

function clearAllFilterValues() {
  if (activeFilterCol.value === null) return;
  columnFilters.value[activeFilterCol.value] = new Set(uniqueValuesInActiveCol.value);
}

function applyFilterAndClose() {
  filterDropdownVisible.value = false;
  ElMessage.success("筛选已应用");
}

// ── Find & Replace ────────────────────────────────────
function openFindReplace(mode: "find" | "replace") {
  findMode.value = mode;
  showFindDialog.value = true;
  nextTick(() => performFind());
}

function performFind() {
  matchedCells.value = [];
  currentMatchIndex.value = 0;
  if (!findQuery.value || !currentSheet.value) return;

  const q = findMatchCase.value ? findQuery.value : findQuery.value.toLowerCase();

  for (let r = 0; r < rowCount.value; r++) {
    for (let c = 0; c < colCount.value; c++) {
      const val = getCellDisplayValue(r, c);
      const checkVal = findMatchCase.value ? val : val.toLowerCase();
      if (findMatchEntire.value ? checkVal === q : checkVal.includes(q)) {
        matchedCells.value.push({ r, c });
      }
    }
  }

  if (matchedCells.value.length) {
    focusMatchedCell(0);
  }
}

function findNext() {
  if (!matchedCells.value.length) return;
  currentMatchIndex.value = (currentMatchIndex.value + 1) % matchedCells.value.length;
  focusMatchedCell(currentMatchIndex.value);
}

function findPrev() {
  if (!matchedCells.value.length) return;
  currentMatchIndex.value = (currentMatchIndex.value - 1 + matchedCells.value.length) % matchedCells.value.length;
  focusMatchedCell(currentMatchIndex.value);
}

function focusMatchedCell(idx: number) {
  const match = matchedCells.value[idx];
  if (!match) return;
  startRow.value = match.r;
  startCol.value = match.c;
  endRow.value = match.r;
  endCol.value = match.c;
}

function performReplace() {
  if (!matchedCells.value.length || !canEdit.value || !currentSheet.value) return;
  pushUndoState();
  const match = matchedCells.value[currentMatchIndex.value];
  if (!match) return;

  const key = `${match.r}_${match.c}`;
  const curr = getCellDisplayValue(match.r, match.c);
  const regex = new RegExp(findQuery.value, findMatchCase.value ? "g" : "gi");
  const replaced = curr.replace(regex, replaceQuery.value);

  if (!currentSheet.value.cells) currentSheet.value.cells = {};
  currentSheet.value.cells[key] = { v: replaced, m: replaced, t: "s" };

  scheduleAutoSave();
  performFind();
  ElMessage.success("已替换当前匹配项");
}

function performReplaceAll() {
  if (!matchedCells.value.length || !canEdit.value || !currentSheet.value) return;
  pushUndoState();
  let count = 0;
  const regex = new RegExp(findQuery.value, findMatchCase.value ? "g" : "gi");

  matchedCells.value.forEach(m => {
    const key = `${m.r}_${m.c}`;
    const curr = getCellDisplayValue(m.r, m.c);
    const replaced = curr.replace(regex, replaceQuery.value);
    if (!currentSheet.value.cells) currentSheet.value.cells = {};
    currentSheet.value.cells[key] = { v: replaced, m: replaced, t: "s" };
    count++;
  });

  scheduleAutoSave();
  performFind();
  ElMessage.success(`已全部替换 ${count} 处匹配项`);
}

// ── Interactive Charts System (ECharts) ───────────────
function insertChartType(type: "bar" | "line" | "pie" | "area" | "radar") {
  if (!currentSheet.value) return;
  pushUndoState();
  if (!currentSheet.value.charts) currentSheet.value.charts = [];

  const newChart: FloatingChart = {
    id: `chart_${Date.now()}`,
    title: `${getColName(selMinCol.value)}${selMinRow.value + 1}:${getColName(selMaxCol.value)}${selMaxRow.value + 1} 数据可视化`,
    type,
    range: {
      r1: selMinRow.value,
      c1: selMinCol.value,
      r2: selMaxRow.value,
      c2: selMaxCol.value
    },
    x: 100,
    y: 60,
    width: 440,
    height: 300
  };

  currentSheet.value.charts.push(newChart);
  scheduleAutoSave();
  broadcastFullSheetSync();
  nextTick(() => renderChartDom(newChart));
  ElMessage.success("图表已插入表格画布");
}

const chartInstances = new Map<string, echarts.ECharts>();

function renderChartDom(chart: FloatingChart) {
  const dom = document.getElementById(`chart-container-${chart.id}`);
  if (!dom) return;

  if (chartInstances.has(chart.id)) {
    chartInstances.get(chart.id)!.dispose();
  }

  const chartInst = echarts.init(dom);
  chartInstances.set(chart.id, chartInst);

  const categories: string[] = [];
  const seriesData: Array<{ name: string; type: string; data: number[]; areaStyle?: any }> = [];

  const isMultiRow = chart.range.r2 > chart.range.r1;
  const isMultiCol = chart.range.c2 > chart.range.c1;

  if (isMultiRow && isMultiCol) {
    for (let r = chart.range.r1 + 1; r <= chart.range.r2; r++) {
      categories.push(getCellDisplayValue(r, chart.range.c1) || `行${r + 1}`);
    }

    for (let c = chart.range.c1 + 1; c <= chart.range.c2; c++) {
      const headerName = getCellDisplayValue(chart.range.r1, c) || `列${getColName(c)}`;
      const vals: number[] = [];
      for (let r = chart.range.r1 + 1; r <= chart.range.r2; r++) {
        vals.push(Number(getRawCellValue(r, c, currentSheet.value, new Set())) || 0);
      }
      seriesData.push({
        name: headerName,
        type: chart.type === "area" ? "line" : chart.type,
        data: vals,
        areaStyle: chart.type === "area" ? {} : undefined
      });
    }
  } else {
    for (let r = chart.range.r1; r <= chart.range.r2; r++) {
      for (let c = chart.range.c1; c <= chart.range.c2; c++) {
        categories.push(`${getColName(c)}${r + 1}`);
      }
    }
    const vals: number[] = [];
    for (let r = chart.range.r1; r <= chart.range.r2; r++) {
      for (let c = chart.range.c1; c <= chart.range.c2; c++) {
        vals.push(Number(getRawCellValue(r, c, currentSheet.value, new Set())) || 0);
      }
    }
    seriesData.push({
      name: "数值",
      type: chart.type === "area" ? "line" : chart.type,
      data: vals,
      areaStyle: chart.type === "area" ? {} : undefined
    });
  }

  let option: any = {};
  if (chart.type === "pie") {
    option = {
      tooltip: { trigger: "item" },
      legend: { bottom: "5%" },
      series: [
        {
          name: "占比",
          type: "pie",
          radius: ["40%", "70%"],
          data: categories.map((name, i) => ({ name, value: seriesData[0]?.data[i] || 0 }))
        }
      ]
    };
  } else if (chart.type === "radar") {
    option = {
      radar: {
        indicator: categories.map(name => ({ name, max: 100 }))
      },
      series: [
        {
          type: "radar",
          data: seriesData.map(s => ({ name: s.name, value: s.data }))
        }
      ]
    };
  } else {
    option = {
      tooltip: { trigger: "axis" },
      legend: { top: "5%" },
      grid: { left: "3%", right: "4%", bottom: "3%", containLabel: true },
      xAxis: { type: "category", data: categories },
      yAxis: { type: "value" },
      series: seriesData
    };
  }

  chartInst.setOption(option);
}

function refreshChartDom(chartId: string) {
  const chart = currentSheet.value?.charts?.find(c => c.id === chartId);
  if (chart) renderChartDom(chart);
}

function deleteChart(chartId: string) {
  if (!currentSheet.value) return;
  pushUndoState();
  currentSheet.value.charts = currentSheet.value.charts.filter(c => c.id !== chartId);
  if (chartInstances.has(chartId)) {
    chartInstances.get(chartId)!.dispose();
    chartInstances.delete(chartId);
  }
  scheduleAutoSave();
  ElMessage.success("图表已删除");
}

function exportChartPng(chartId: string) {
  const inst = chartInstances.get(chartId);
  if (!inst) return;
  const url = inst.getDataURL({ type: "png", pixelRatio: 2, backgroundColor: "#fff" });
  const a = document.createElement("a");
  a.href = url;
  a.download = `chart_${chartId}.png`;
  a.click();
}

let draggingChart: FloatingChart | null = null;
let chartDragStartX = 0;
let chartDragStartY = 0;
let chartInitX = 0;
let chartInitY = 0;

function startDragChart(e: MouseEvent, chart: FloatingChart) {
  if (!canEdit.value) return;
  draggingChart = chart;
  chartDragStartX = e.clientX;
  chartDragStartY = e.clientY;
  chartInitX = chart.x || 0;
  chartInitY = chart.y || 0;

  window.addEventListener("mousemove", onChartMouseMove);
  window.addEventListener("mouseup", onChartMouseUp);
}

function onChartMouseMove(e: MouseEvent) {
  if (!draggingChart) return;
  const dx = e.clientX - chartDragStartX;
  const dy = e.clientY - chartDragStartY;
  draggingChart.x = Math.max(0, chartInitX + dx);
  draggingChart.y = Math.max(0, chartInitY + dy);
}

function onChartMouseUp() {
  if (draggingChart) {
    scheduleAutoSave();
    draggingChart = null;
  }
  window.removeEventListener("mousemove", onChartMouseMove);
  window.removeEventListener("mouseup", onChartMouseUp);
}

// ── Version History ───────────────────────────────────
async function openVersionHistory() {
  showVersionDrawer.value = true;
  loadingVersions.value = true;
  try {
    const { data } = await api.get(`/documents/${props.docId}/versions`);
    versionList.value = data.items || [];
  } catch {
    ElMessage.error("获取版本历史失败");
  } finally {
    loadingVersions.value = false;
  }
}

async function restoreSpecificVersion(ver: any) {
  try {
    await ElMessageBox.confirm(`确定要恢复到 ${ver.created_at} 的历史版本吗？`, "恢复版本", { type: "warning" });
    const { data } = await api.get(`/documents/${props.docId}/versions/${ver.id}/content`);
    if (data?.content_json) {
      pushUndoState();
      workbook.value = JSON.parse(data.content_json);
      await saveNow();
      showVersionDrawer.value = false;
      ElMessage.success("已恢复到指定历史版本");
    }
  } catch {}
}

function printSpreadsheet() {
  window.print();
}

function copyAggValue(val: any) {
  navigator.clipboard.writeText(String(val));
  ElMessage.success(`已复制: ${val}`);
}

// ── Interactive Column & Row Resizing ─────────────────
function startColResize(colIdx: number, e: MouseEvent) {
  isColResizing.value = true;
  resizingColIdx.value = colIdx;
  colResizeStartX.value = e.clientX;
  colResizeInitWidth.value = getColumnWidth(colIdx);
  resizerGuidePos.value = e.clientX;
  window.addEventListener("mousemove", onColResizeMouseMove);
  window.addEventListener("mouseup", onColResizeMouseUp);
}

function onColResizeMouseMove(e: MouseEvent) {
  if (!isColResizing.value) return;
  const dx = e.clientX - colResizeStartX.value;
  const newWidth = Math.max(35, colResizeInitWidth.value + dx);
  if (!currentSheet.value.columnWidths) currentSheet.value.columnWidths = {};
  currentSheet.value.columnWidths[String(resizingColIdx.value)] = newWidth;
  resizerGuidePos.value = e.clientX;
}

function onColResizeMouseUp() {
  isColResizing.value = false;
  scheduleAutoSave();
  window.removeEventListener("mousemove", onColResizeMouseMove);
  window.removeEventListener("mouseup", onColResizeMouseUp);
}

function autoFitColumnWidth(colIdx: number) {
  let maxLen = 4;
  for (let r = 0; r < rowCount.value; r++) {
    const val = getCellDisplayValue(r, colIdx);
    if (val && val.length > maxLen) {
      maxLen = val.length;
    }
  }
  const fitWidth = Math.min(Math.max(maxLen * 12 + 24, 60), 300);
  if (!currentSheet.value.columnWidths) currentSheet.value.columnWidths = {};
  currentSheet.value.columnWidths[String(colIdx)] = fitWidth;
  scheduleAutoSave();
}

function startRowResize(rowIdx: number, e: MouseEvent) {
  isRowResizing.value = true;
  resizingRowIdx.value = rowIdx;
  rowResizeStartY.value = e.clientY;
  rowResizeInitHeight.value = getRowHeight(rowIdx);
  resizerGuidePos.value = e.clientY;
  window.addEventListener("mousemove", onRowResizeMouseMove);
  window.addEventListener("mouseup", onRowResizeMouseUp);
}

function onRowResizeMouseMove(e: MouseEvent) {
  if (!isRowResizing.value) return;
  const dy = e.clientY - rowResizeStartY.value;
  const newHeight = Math.max(20, rowResizeInitHeight.value + dy);
  if (!currentSheet.value.rowHeights) currentSheet.value.rowHeights = {};
  currentSheet.value.rowHeights[String(resizingRowIdx.value)] = newHeight;
  resizerGuidePos.value = e.clientY;
}

function onRowResizeMouseUp() {
  isRowResizing.value = false;
  scheduleAutoSave();
  window.removeEventListener("mousemove", onRowResizeMouseMove);
  window.removeEventListener("mouseup", onRowResizeMouseUp);
}

function onResizerMouseMove() {}

// ── Fill Handle Dragging ──────────────────────────────
function startFillHandleDrag(e: MouseEvent) {
  isDraggingFill.value = true;
  lastDragMouseX = e.clientX;
  lastDragMouseY = e.clientY;
  e.preventDefault();
  window.addEventListener("mousemove", onWindowDragMouseMove);
  window.addEventListener("mouseup", onFillHandleMouseUp);
}

function onFillHandleMouseUp() {
  if (!isDraggingFill.value) return;
  stopAutoScrollLoop();
  isDraggingFill.value = false;
  window.removeEventListener("mousemove", onWindowDragMouseMove);
  window.removeEventListener("mouseup", onFillHandleMouseUp);
  scheduleAutoSave();
}

// ── Context Menu & Clipboard ──────────────────────────
function positionContextMenu(clientX: number, clientY: number) {
  const estWidth = 220;
  const estHeight = 440;
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  const margin = 10;

  let initialX = clientX;
  let initialY = clientY;

  // Pre-calculate to avoid bottom/right flash
  if (initialY + estHeight > viewportHeight - margin) {
    initialY = Math.max(margin, clientY - estHeight);
  }
  if (initialX + estWidth > viewportWidth - margin) {
    initialX = Math.max(margin, clientX - estWidth);
  }

  contextMenuX.value = Math.round(initialX);
  contextMenuY.value = Math.round(initialY);
  contextMenuVisible.value = true;

  // Exact adaptive calculation after DOM update
  nextTick(() => {
    if (!contextMenuRef.value) return;
    const rect = contextMenuRef.value.getBoundingClientRect();
    const w = rect.width || estWidth;
    const h = rect.height || estHeight;

    let x = clientX;
    let y = clientY;

    // Bottom collision detection (flip upwards like Excel)
    if (y + h > viewportHeight - margin) {
      const upY = clientY - h;
      if (upY >= margin) {
        y = upY;
      } else {
        y = Math.max(margin, viewportHeight - h - margin);
      }
    }

    // Right collision detection (flip leftwards like Excel)
    if (x + w > viewportWidth - margin) {
      const leftX = clientX - w;
      if (leftX >= margin) {
        x = leftX;
      } else {
        x = Math.max(margin, viewportWidth - w - margin);
      }
    }

    if (x < margin) x = margin;
    if (y < margin) y = margin;

    contextMenuX.value = Math.round(x);
    contextMenuY.value = Math.round(y);
  });
}

function openContextMenu(e: MouseEvent, r: number, c: number) {
  if (!isCellInSelection(r, c)) {
    startRow.value = r;
    startCol.value = c;
    endRow.value = r;
    endCol.value = c;
  }
  positionContextMenu(e.clientX, e.clientY);
}

function openRowContextMenu(e: MouseEvent, r: number) {
  if (r < selMinRow.value || r > selMaxRow.value || startCol.value !== 0 || endCol.value !== colCount.value - 1) {
    selectRow(r, e);
  }
  positionContextMenu(e.clientX, e.clientY);
}

function openColContextMenu(e: MouseEvent, c: number) {
  if (c < selMinCol.value || c > selMaxCol.value || startRow.value !== 0 || endRow.value !== rowCount.value - 1) {
    selectColumn(c, e);
  }
  positionContextMenu(e.clientX, e.clientY);
}

async function handleCopySelection() {
  contextMenuVisible.value = false;
  const rowsData: string[] = [];
  for (let r = selMinRow.value; r <= selMaxRow.value; r++) {
    const rowVals: string[] = [];
    for (let c = selMinCol.value; c <= selMaxCol.value; c++) {
      rowVals.push(getCellDisplayValue(r, c));
    }
    rowsData.push(rowVals.join("\t"));
  }
  const text = rowsData.join("\n");
  try {
    await navigator.clipboard.writeText(text);
    ElMessage.success("已复制到剪贴板");
  } catch {}
}

function handleCutSelection() {
  handleCopySelection();
  clearSelectionContent();
}

async function handlePasteSelection() {
  contextMenuVisible.value = false;
  pushUndoState();
  try {
    const text = await navigator.clipboard.readText();
    if (!text) return;
    const lines = text.split(/\r?\n/);
    if (!currentSheet.value.cells) currentSheet.value.cells = {};

    lines.forEach((line, rOffset) => {
      const targetR = selMinRow.value + rOffset;
      if (targetR < rowCount.value) {
        const cols = line.split("\t");
        cols.forEach((val, cOffset) => {
          const targetC = selMinCol.value + cOffset;
          if (targetC < colCount.value) {
            if (getLockingCollaborator(targetR, targetC)) {
              return; // 保护协作他人正占用的单元格
            }
            const key = `${targetR}_${targetC}`;
            const num = Number(val);
            const isNum = !isNaN(num) && val.trim() !== "";
            currentSheet.value.cells[key] = {
              v: isNum ? num : val,
              m: val,
              t: isNum ? "n" : "s"
            };
          }
        });
      }
    });

    scheduleAutoSave();
    broadcastBatchCells();
    ElMessage.success("已粘贴");
  } catch {
    ElMessage.warning("请允许浏览器访问剪贴板");
  }
}

function clearSelectionContent() {
  contextMenuVisible.value = false;
  pushUndoState();
  if (!currentSheet.value.cells) return;

  let skippedCount = 0;
  for (let r = selMinRow.value; r <= selMaxRow.value; r++) {
    for (let c = selMinCol.value; c <= selMaxCol.value; c++) {
      if (getLockingCollaborator(r, c)) {
        skippedCount++;
        continue;
      }
      const key = `${r}_${c}`;
      delete currentSheet.value.cells[key];
    }
  }
  if (skippedCount > 0) {
    ElMessage.warning(`已跳过 ${skippedCount} 个他人正在编辑的锁定单元格`);
  } else {
    ElMessage.success("已清空选区内容");
  }
  activeCellFormula.value = "";
  scheduleAutoSave();
  broadcastBatchCells();
}

function sortSelection(order: "asc" | "desc") {
  // 🔒 协同保护：检查排序列及选中区域是否包含他人正在编辑的单元格
  for (let r = selMinRow.value; r <= selMaxRow.value; r++) {
    for (let c = selMinCol.value; c <= selMaxCol.value; c++) {
      const locker = getLockingCollaborator(r, c);
      if (locker) {
        ElMessage.warning(`选区包含正由 [${locker.name}] 编辑的单元格，已锁定保护无法执行排序！`);
        return;
      }
    }
  }
  contextMenuVisible.value = false;
  pushUndoState();
  const sortCol = selMinCol.value;
  const rows: Array<{ r: number; val: any; cells: Record<number, CellData> }> = [];

  for (let r = selMinRow.value; r <= selMaxRow.value; r++) {
    const cellVals: Record<number, CellData> = {};
    for (let c = selMinCol.value; c <= selMaxCol.value; c++) {
      const key = `${r}_${c}`;
      if (currentSheet.value.cells?.[key]) {
        cellVals[c] = { ...currentSheet.value.cells[key] };
      }
    }
    rows.push({
      r,
      val: getRawCellValue(r, sortCol, currentSheet.value, new Set()),
      cells: cellVals
    });
  }

  rows.sort((a, b) => {
    const vA = a.val;
    const vB = b.val;
    if (typeof vA === "number" && typeof vB === "number") {
      return order === "asc" ? vA - vB : vB - vA;
    }
    return order === "asc" ? String(vA).localeCompare(String(vB)) : String(vB).localeCompare(String(vA));
  });

  rows.forEach((sortedRow, idx) => {
    const targetR = selMinRow.value + idx;
    for (let c = selMinCol.value; c <= selMaxCol.value; c++) {
      const key = `${targetR}_${c}`;
      if (sortedRow.cells[c]) {
        currentSheet.value.cells[key] = sortedRow.cells[c];
      } else {
        delete currentSheet.value.cells[key];
      }
    }
  });

  scheduleAutoSave();
  broadcastBatchCells();
  ElMessage.success(`已${order === "asc" ? "升序" : "降序"}排列`);
}

function tryMoveSelection(targetR: number, targetC: number) {
  if (targetR < 0 || targetR >= rowCount.value || targetC < 0 || targetC >= colCount.value) return;
  const locker = getLockingCollaborator(targetR, targetC);
  if (locker) {
    ElMessage({
      message: `单元格已被 [${locker.name}] 占用锁定，无法移入`,
      type: "warning",
      duration: 1000
    });
    return;
  }
  startRow.value = targetR;
  startCol.value = targetC;
  endRow.value = targetR;
  endCol.value = targetC;
  const key = `${targetR}_${targetC}`;
  const cell = currentSheet.value?.cells?.[key];
  activeCellFormula.value = cell?.f || (cell?.v !== undefined && cell?.v !== null ? String(cell.v) : "");
  broadcastAwareness();
}

// ── Global Keyboard Shortcuts ─────────────────────────
function onGlobalKeyDown(e: KeyboardEvent) {
  if (isEditing.value) return;

  if (e.ctrlKey || e.metaKey) {
    if (e.key.toLowerCase() === "z") {
      e.preventDefault();
      if (e.shiftKey) redo(); else undo();
    } else if (e.key.toLowerCase() === "y") {
      e.preventDefault();
      redo();
    } else if (e.key.toLowerCase() === "f") {
      e.preventDefault();
      openFindReplace("find");
    } else if (e.key.toLowerCase() === "h") {
      e.preventDefault();
      openFindReplace("replace");
    } else if (e.key.toLowerCase() === "c") {
      e.preventDefault();
      handleCopySelection();
    } else if (e.key.toLowerCase() === "x") {
      e.preventDefault();
      handleCutSelection();
    } else if (e.key.toLowerCase() === "v") {
      handlePasteSelection();
    } else if (e.key.toLowerCase() === "b") {
      e.preventDefault();
      toggleStyle("bl");
    } else if (e.key.toLowerCase() === "i") {
      e.preventDefault();
      toggleStyle("it");
    } else if (e.key.toLowerCase() === "u") {
      e.preventDefault();
      toggleStyle("un");
    }
  } else if (e.key === "Escape") {
    showFindDialog.value = false;
    filterDropdownVisible.value = false;
  } else if (e.key === "Enter" || e.key === "F2") {
    e.preventDefault();
    onCellDoubleClick(startRow.value, startCol.value);
  } else if (e.key === "Delete" || e.key === "Backspace") {
    e.preventDefault();
    clearSelectionContent();
  } else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey && e.key !== "Tab") {
    if (canEdit.value) {
      e.preventDefault();
      startEditingWithChar(startRow.value, startCol.value, e.key);
    }
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    tryMoveSelection(startRow.value - 1, startCol.value);
  } else if (e.key === "ArrowDown") {
    e.preventDefault();
    tryMoveSelection(startRow.value + 1, startCol.value);
  } else if (e.key === "ArrowLeft") {
    e.preventDefault();
    tryMoveSelection(startRow.value, startCol.value - 1);
  } else if (e.key === "ArrowRight") {
    e.preventDefault();
    tryMoveSelection(startRow.value, startCol.value + 1);
  }
}

// ── Row / Column Insert & Delete ──────────────────────
const appendRowCount = ref(200);
const appendColCount = ref(10);

function insertRow(position: 'above' | 'below' = 'above') {
  if (!currentSheet.value || !canEdit.value) return;
  pushUndoState();
  contextMenuVisible.value = false;

  const rMin = Math.min(startRow.value, endRow.value);
  const rMax = Math.max(startRow.value, endRow.value);
  const targetRow = position === 'above' ? rMin : rMax + 1;
  const count = 1;

  // 1. Shift cells
  const oldCells = currentSheet.value.cells || {};
  const newCells: Record<string, CellData> = {};
  for (const k of Object.keys(oldCells)) {
    const parts = k.split('_');
    const r = parseInt(parts[0], 10);
    const c = parseInt(parts[1], 10);
    if (r < targetRow) {
      newCells[k] = oldCells[k];
    } else {
      newCells[`${r + count}_${c}`] = oldCells[k];
    }
  }
  currentSheet.value.cells = newCells;

  // 2. Shift styles
  const oldStyles = currentSheet.value.styles || {};
  const newStyles: Record<string, CellStyle> = {};
  for (const k of Object.keys(oldStyles)) {
    const parts = k.split('_');
    const r = parseInt(parts[0], 10);
    const c = parseInt(parts[1], 10);
    if (r < targetRow) {
      newStyles[k] = oldStyles[k];
    } else {
      newStyles[`${r + count}_${c}`] = oldStyles[k];
    }
  }
  currentSheet.value.styles = newStyles;

  // 3. Shift rowHeights
  const oldHeights = currentSheet.value.rowHeights || {};
  const newHeights: Record<string, number> = {};
  for (const rStr of Object.keys(oldHeights)) {
    const r = parseInt(rStr, 10);
    if (r < targetRow) {
      newHeights[r] = oldHeights[r];
    } else {
      newHeights[r + count] = oldHeights[r];
    }
  }
  currentSheet.value.rowHeights = newHeights;

  // 4. Update mergedCells
  if (currentSheet.value.mergedCells) {
    currentSheet.value.mergedCells = currentSheet.value.mergedCells.map(m => {
      if (m.r >= targetRow) {
        return { ...m, r: m.r + count };
      } else if (targetRow > m.r && targetRow < m.r + m.rs) {
        return { ...m, rs: m.rs + count };
      }
      return m;
    });
  }

  // 5. Increment rowCount
  currentSheet.value.rowCount = (currentSheet.value.rowCount || 60) + count;

  // 6. Update selection focus
  if (position === 'below') {
    startRow.value = targetRow;
    endRow.value = targetRow;
  }

  scheduleAutoSave();
  broadcastFullSheetSync();
  ElMessage.success(position === 'above' ? "已在上方插入 1 行" : "已在下方插入 1 行");
}

function insertRowAbove() {
  insertRow('above');
}

function insertRowBelow() {
  insertRow('below');
}

function insertCol(position: 'left' | 'right' = 'left') {
  if (!currentSheet.value || !canEdit.value) return;
  pushUndoState();
  contextMenuVisible.value = false;

  const cMin = Math.min(startCol.value, endCol.value);
  const cMax = Math.max(startCol.value, endCol.value);
  const targetCol = position === 'left' ? cMin : cMax + 1;
  const count = 1;

  // 1. Shift cells
  const oldCells = currentSheet.value.cells || {};
  const newCells: Record<string, CellData> = {};
  for (const k of Object.keys(oldCells)) {
    const parts = k.split('_');
    const r = parseInt(parts[0], 10);
    const c = parseInt(parts[1], 10);
    if (c < targetCol) {
      newCells[k] = oldCells[k];
    } else {
      newCells[`${r}_${c + count}`] = oldCells[k];
    }
  }
  currentSheet.value.cells = newCells;

  // 2. Shift styles
  const oldStyles = currentSheet.value.styles || {};
  const newStyles: Record<string, CellStyle> = {};
  for (const k of Object.keys(oldStyles)) {
    const parts = k.split('_');
    const r = parseInt(parts[0], 10);
    const c = parseInt(parts[1], 10);
    if (c < targetCol) {
      newStyles[k] = oldStyles[k];
    } else {
      newStyles[`${r}_${c + count}`] = oldStyles[k];
    }
  }
  currentSheet.value.styles = newStyles;

  // 3. Shift columnWidths
  const oldWidths = currentSheet.value.columnWidths || {};
  const newWidths: Record<string, number> = {};
  for (const cStr of Object.keys(oldWidths)) {
    const c = parseInt(cStr, 10);
    if (c < targetCol) {
      newWidths[c] = oldWidths[c];
    } else {
      newWidths[c + count] = oldWidths[c];
    }
  }
  currentSheet.value.columnWidths = newWidths;

  // 4. Update mergedCells
  if (currentSheet.value.mergedCells) {
    currentSheet.value.mergedCells = currentSheet.value.mergedCells.map(m => {
      if (m.c >= targetCol) {
        return { ...m, c: m.c + count };
      } else if (targetCol > m.c && targetCol < m.c + m.cs) {
        return { ...m, cs: m.cs + count };
      }
      return m;
    });
  }

  // 5. Increment colCount
  currentSheet.value.colCount = (currentSheet.value.colCount || 26) + count;

  // 6. Update selection focus
  if (position === 'right') {
    startCol.value = targetCol;
    endCol.value = targetCol;
  }

  scheduleAutoSave();
  broadcastFullSheetSync();
  ElMessage.success(position === 'left' ? "已在左侧插入 1 列" : "已在右侧插入 1 列");
}

function insertColLeft() {
  insertCol('left');
}

function insertColRight() {
  insertCol('right');
}

function deleteCurrentRow() {
  if (!currentSheet.value || !canEdit.value || currentSheet.value.rowCount <= 1) return;
  const rStart = Math.min(startRow.value, endRow.value);
  const rEnd = Math.max(startRow.value, endRow.value);
  const count = rEnd - rStart + 1;

  // 🔒 协同保护：检查待删除行是否有他人正在编辑
  for (let r = rStart; r <= rEnd; r++) {
    for (let c = 0; c < colCount.value; c++) {
      const locker = getLockingCollaborator(r, c);
      if (locker) {
        ElMessage.warning(`第 ${r + 1} 行包含 [${locker.name}] 正在编辑的单元格，禁止删除！`);
        return;
      }
    }
  }

  pushUndoState();
  contextMenuVisible.value = false;

  // 1. Shift cells (drop [rStart, rEnd], shift r > rEnd by -count)
  const oldCells = currentSheet.value.cells || {};
  const newCells: Record<string, CellData> = {};
  for (const k of Object.keys(oldCells)) {
    const parts = k.split('_');
    const r = parseInt(parts[0], 10);
    const c = parseInt(parts[1], 10);
    if (r < rStart) {
      newCells[k] = oldCells[k];
    } else if (r > rEnd) {
      newCells[`${r - count}_${c}`] = oldCells[k];
    }
  }
  currentSheet.value.cells = newCells;

  // 2. Shift styles
  const oldStyles = currentSheet.value.styles || {};
  const newStyles: Record<string, CellStyle> = {};
  for (const k of Object.keys(oldStyles)) {
    const parts = k.split('_');
    const r = parseInt(parts[0], 10);
    const c = parseInt(parts[1], 10);
    if (r < rStart) {
      newStyles[k] = oldStyles[k];
    } else if (r > rEnd) {
      newStyles[`${r - count}_${c}`] = oldStyles[k];
    }
  }
  currentSheet.value.styles = newStyles;

  // 3. Shift rowHeights
  const oldHeights = currentSheet.value.rowHeights || {};
  const newHeights: Record<string, number> = {};
  for (const rStr of Object.keys(oldHeights)) {
    const r = parseInt(rStr, 10);
    if (r < rStart) {
      newHeights[r] = oldHeights[r];
    } else if (r > rEnd) {
      newHeights[r - count] = oldHeights[r];
    }
  }
  currentSheet.value.rowHeights = newHeights;

  // 4. Update mergedCells
  if (currentSheet.value.mergedCells) {
    const newMerged: MergedCell[] = [];
    for (const m of currentSheet.value.mergedCells) {
      const mEnd = m.r + m.rs - 1;
      if (m.r >= rStart && mEnd <= rEnd) {
        continue;
      }
      if (mEnd < rStart) {
        newMerged.push(m);
        continue;
      }
      if (m.r > rEnd) {
        newMerged.push({ ...m, r: m.r - count });
        continue;
      }
      const overlapStart = Math.max(m.r, rStart);
      const overlapEnd = Math.min(mEnd, rEnd);
      const deletedSpan = overlapEnd - overlapStart + 1;
      const newRs = m.rs - deletedSpan;
      if (newRs > 0) {
        const newR = m.r >= rStart ? rStart : m.r;
        newMerged.push({ ...m, r: newR, rs: newRs });
      }
    }
    currentSheet.value.mergedCells = newMerged;
  }

  // 5. Decrement rowCount
  currentSheet.value.rowCount = Math.max(1, (currentSheet.value.rowCount || 60) - count);

  // 6. Reset selection
  startRow.value = Math.min(rStart, currentSheet.value.rowCount - 1);
  endRow.value = startRow.value;

  scheduleAutoSave();
  broadcastFullSheetSync();
  ElMessage.success(`已删除 ${count} 行`);
}

function deleteCurrentCol() {
  if (!currentSheet.value || !canEdit.value || currentSheet.value.colCount <= 1) return;
  const cStart = Math.min(startCol.value, endCol.value);
  const cEnd = Math.max(startCol.value, endCol.value);
  const count = cEnd - cStart + 1;

  // 🔒 协同保护：检查待删除列是否有他人正在编辑
  for (let c = cStart; c <= cEnd; c++) {
    for (let r = 0; r < rowCount.value; r++) {
      const locker = getLockingCollaborator(r, c);
      if (locker) {
        ElMessage.warning(`第 ${getColName(c)} 列包含 [${locker.name}] 正在编辑的单元格，禁止删除！`);
        return;
      }
    }
  }

  pushUndoState();
  contextMenuVisible.value = false;

  // 1. Shift cells (drop [cStart, cEnd], shift c > cEnd by -count)
  const oldCells = currentSheet.value.cells || {};
  const newCells: Record<string, CellData> = {};
  for (const k of Object.keys(oldCells)) {
    const parts = k.split('_');
    const r = parseInt(parts[0], 10);
    const c = parseInt(parts[1], 10);
    if (c < cStart) {
      newCells[k] = oldCells[k];
    } else if (c > cEnd) {
      newCells[`${r}_${c - count}`] = oldCells[k];
    }
  }
  currentSheet.value.cells = newCells;

  // 2. Shift styles
  const oldStyles = currentSheet.value.styles || {};
  const newStyles: Record<string, CellStyle> = {};
  for (const k of Object.keys(oldStyles)) {
    const parts = k.split('_');
    const r = parseInt(parts[0], 10);
    const c = parseInt(parts[1], 10);
    if (c < cStart) {
      newStyles[k] = oldStyles[k];
    } else if (c > cEnd) {
      newStyles[`${r}_${c - count}`] = oldStyles[k];
    }
  }
  currentSheet.value.styles = newStyles;

  // 3. Shift columnWidths
  const oldWidths = currentSheet.value.columnWidths || {};
  const newWidths: Record<string, number> = {};
  for (const cStr of Object.keys(oldWidths)) {
    const c = parseInt(cStr, 10);
    if (c < cStart) {
      newWidths[c] = oldWidths[c];
    } else if (c > cEnd) {
      newWidths[c - count] = oldWidths[c];
    }
  }
  currentSheet.value.columnWidths = newWidths;

  // 4. Update mergedCells
  if (currentSheet.value.mergedCells) {
    const newMerged: MergedCell[] = [];
    for (const m of currentSheet.value.mergedCells) {
      const mEnd = m.c + m.cs - 1;
      if (m.c >= cStart && mEnd <= cEnd) {
        continue;
      }
      if (mEnd < cStart) {
        newMerged.push(m);
        continue;
      }
      if (m.c > cEnd) {
        newMerged.push({ ...m, c: m.c - count });
        continue;
      }
      const overlapStart = Math.max(m.c, cStart);
      const overlapEnd = Math.min(mEnd, cEnd);
      const deletedSpan = overlapEnd - overlapStart + 1;
      const newCs = m.cs - deletedSpan;
      if (newCs > 0) {
        const newC = m.c >= cStart ? cStart : m.c;
        newMerged.push({ ...m, c: newC, cs: newCs });
      }
    }
    currentSheet.value.mergedCells = newMerged;
  }

  // 5. Decrement colCount
  currentSheet.value.colCount = Math.max(1, (currentSheet.value.colCount || 26) - count);

  // 6. Reset selection
  startCol.value = Math.min(cStart, currentSheet.value.colCount - 1);
  endCol.value = startCol.value;

  scheduleAutoSave();
  broadcastFullSheetSync();
  ElMessage.success(`已删除 ${count} 列`);
}

// ── Append Rows & Columns at Edges ─────────────────────
function appendRows(count: number = 200) {
  if (!currentSheet.value || !canEdit.value) return;
  const validCount = Math.max(1, Math.min(5000, Number(count) || 100));
  pushUndoState();
  currentSheet.value.rowCount = (currentSheet.value.rowCount || 60) + validCount;
  scheduleAutoSave();
  broadcastDimensions();
  ElMessage.success(`已向下添加 ${validCount} 行，当前共 ${currentSheet.value.rowCount} 行`);
  
  nextTick(() => {
    if (gridContainerRef.value) {
      gridContainerRef.value.scrollTo({
        top: gridContainerRef.value.scrollHeight,
        behavior: 'smooth'
      });
    }
  });
}

function appendCols(count: number = 10) {
  if (!currentSheet.value || !canEdit.value) return;
  const validCount = Math.max(1, Math.min(500, Number(count) || 10));
  pushUndoState();
  currentSheet.value.colCount = (currentSheet.value.colCount || 26) + validCount;
  scheduleAutoSave();
  broadcastDimensions();
  ElMessage.success(`已向右添加 ${validCount} 列，当前共 ${currentSheet.value.colCount} 列`);
  
  nextTick(() => {
    if (gridContainerRef.value) {
      gridContainerRef.value.scrollTo({
        left: gridContainerRef.value.scrollWidth,
        behavior: 'smooth'
      });
    }
  });
}

// ── Sheet Management ──────────────────────────────────
function switchSheet(sheetId: string) {
  workbook.value.activeSheetId = sheetId;
  startRow.value = 0;
  startCol.value = 0;
  endRow.value = 0;
  endCol.value = 0;
  nextTick(() => {
    currentSheet.value?.charts?.forEach(c => renderChartDom(c));
  });
}

function addNewSheet() {
  pushUndoState();
  const count = workbook.value.sheets.length + 1;
  const newSheet: Sheet = {
    id: `sheet_${Date.now()}`,
    name: `Sheet${count}`,
    rowCount: 60,
    colCount: 26,
    cells: {},
    styles: {},
    images: [],
    charts: [],
    mergedCells: [],
    cfRules: [],
    columnWidths: {},
    rowHeights: {}
  };
  workbook.value.sheets.push(newSheet);
  workbook.value.activeSheetId = newSheet.id;
  scheduleAutoSave();
  broadcastWorkbookStructure();
  ElMessage.success("已添加工作表");
}

async function promptRenameSheet(sheet: Sheet) {
  if (!canEdit.value) return;
  try {
    const { value } = await ElMessageBox.prompt("请输入工作表名称", "重命名工作表", {
      inputValue: sheet.name,
      confirmButtonText: t("common.confirm", "确定"),
      cancelButtonText: t("common.cancel", "取消")
    });
    if (value && value.trim()) {
      pushUndoState();
      sheet.name = value.trim();
      scheduleAutoSave();
      broadcastWorkbookStructure();
    }
  } catch {}
}

function deleteSheet(sheetId: string) {
  if (workbook.value.sheets.length <= 1) return;
  pushUndoState();
  workbook.value.sheets = workbook.value.sheets.filter(s => s.id !== sheetId);
  if (workbook.value.activeSheetId === sheetId) {
    workbook.value.activeSheetId = workbook.value.sheets[0]!.id;
  }
  scheduleAutoSave();
  broadcastWorkbookStructure();
  ElMessage.success("已删除工作表");
}

// ── Image Handling ────────────────────────────────────
async function handleInsertImage(file: File) {
  try {
    const fd = new FormData();
    fd.append("file", file);
    const { data } = await api.post("/documents/upload-image", fd);
    if (data.url && currentSheet.value) {
      pushUndoState();
      if (!currentSheet.value.images) currentSheet.value.images = [];
      currentSheet.value.images.push({
        id: `img_${Date.now()}`,
        src: data.url,
        x: 100,
        y: 80,
        width: 220,
        height: 150
      });
      scheduleAutoSave();
      broadcastFullSheetSync();
      ElMessage.success("图片已插入表格");
    }
  } catch {
    ElMessage.error("图片上传失败");
  }
  return false;
}

function deleteImage(imgId: string) {
  if (!currentSheet.value) return;
  pushUndoState();
  currentSheet.value.images = currentSheet.value.images.filter(i => i.id !== imgId);
  scheduleAutoSave();
  broadcastFullSheetSync();
}

let draggingImg: FloatingImage | null = null;
let dragStartX = 0;
let dragStartY = 0;
let imgInitialX = 0;
let imgInitialY = 0;

function startDragImage(e: MouseEvent, img: FloatingImage) {
  if (!canEdit.value) return;
  draggingImg = img;
  dragStartX = e.clientX;
  dragStartY = e.clientY;
  imgInitialX = img.x || 0;
  imgInitialY = img.y || 0;

  window.addEventListener("mousemove", onImageMouseMove);
  window.addEventListener("mouseup", onImageMouseUp);
}

function onImageMouseMove(e: MouseEvent) {
  if (!draggingImg) return;
  const dx = e.clientX - dragStartX;
  const dy = e.clientY - dragStartY;
  draggingImg.x = Math.max(0, imgInitialX + dx);
  draggingImg.y = Math.max(0, imgInitialY + dy);
}

function onImageMouseUp() {
  if (draggingImg) {
    scheduleAutoSave();
    draggingImg = null;
  }
  window.removeEventListener("mousemove", onImageMouseMove);
  window.removeEventListener("mouseup", onImageMouseUp);
}

// ── Excel Import / Export ─────────────────────────────
async function handleImportExcel(file: File) {
  loading.value = true;
  try {
    const buffer = await file.arrayBuffer();
    const wb = XLSX.read(buffer, { type: "array", cellStyles: true });
    
    const parsedSheets: Sheet[] = [];
    wb.SheetNames.forEach((name, sIdx) => {
      const ws = wb.Sheets[name]!;
      const cells: Record<string, CellData> = {};
      const styles: Record<string, CellStyle> = {};
      
      const range = XLSX.utils.decode_range(ws["!ref"] || "A1:Z60");
      const rCount = Math.max(range.e.r + 20, 60);
      const cCount = Math.max(range.e.c + 5, 26);

      for (let R = range.s.r; R <= range.e.r; ++R) {
        for (let C = range.s.c; C <= range.e.c; ++C) {
          const cellAddr = XLSX.utils.encode_cell({ r: R, c: C });
          const cell = ws[cellAddr];
          if (cell) {
            const key = `${R}_${C}`;
            cells[key] = {
              v: cell.v,
              m: cell.w || String(cell.v || ""),
              f: cell.f ? `=${cell.f}` : undefined,
              t: cell.t || "s"
            };
          }
        }
      }

      parsedSheets.push({
        id: `sheet_${sIdx + 1}`,
        name: name || `Sheet${sIdx + 1}`,
        rowCount: rCount,
        colCount: cCount,
        cells,
        styles,
        images: [],
        charts: [],
        mergedCells: [],
        cfRules: [],
        columnWidths: {},
        rowHeights: {}
      });
    });

    if (parsedSheets.length) {
      pushUndoState();
      workbook.value = {
        type: "spreadsheet",
        activeSheetId: parsedSheets[0]!.id,
        sheets: parsedSheets
      };
      await saveNow();
      ElMessage.success(t("library.importExcelSuccess", "Excel 导入成功"));
    }
  } catch (err) {
    console.error(err);
    ElMessage.error(t("library.importExcelFailed", "Excel 导入失败"));
  } finally {
    loading.value = false;
  }
  return false;
}

async function handleExportExcel() {
  try {
    const token = authStore.token;
    const res = await fetch(`/api/documents/${props.docId}/export.xlsx`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (!res.ok) throw new Error("Export failed");
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title.value || "spreadsheet"}.xlsx`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    ElMessage.success("已成功导出 Excel");
  } catch {
    ElMessage.error(t("editor.exportFailed", "导出失败"));
  }
}

// ── AI Copilot Features Implementation ────────────────
function openAiDrawer(tab: string = "formula") {
  contextMenuVisible.value = false;
  aiActiveTab.value = tab;
  showAiDrawer.value = true;
}

async function generateAiFormula() {
  if (!aiFormulaQuery.value.trim()) {
    return ElMessage.warning("请输入您想要计算的内容描述");
  }
  aiFormulaLoading.value = true;
  try {
    const targetAddr = `${getColName(startCol.value)}${startRow.value + 1}`;
    const { data } = await api.post("/ai/spreadsheet/formula", {
      query: aiFormulaQuery.value.trim(),
      cell_address: targetAddr,
      range_context: selectionAddressText.value,
      sheet_sample: getSheetSampleString()
    });
    if (data && data.data) {
      aiGeneratedFormulaResult.value = data.data;
      ElMessage.success("公式生成成功！");
    }
  } catch {
    ElMessage.error("AI 公式生成失败");
  } finally {
    aiFormulaLoading.value = false;
  }
}

function applyGeneratedFormula() {
  if (!aiGeneratedFormulaResult.value?.formula) return;
  activeCellFormula.value = aiGeneratedFormulaResult.value.formula;
  onFormulaInputChange();
  showAiDrawer.value = false;
  ElMessage.success(`已应用公式 ${activeCellFormula.value} 到当前单元格`);
}

async function generateAiTable() {
  if (!aiTablePrompt.value.trim()) {
    return ElMessage.warning("请输入建表主题需求");
  }
  aiTableLoading.value = true;
  try {
    const { data } = await api.post("/ai/spreadsheet/generate-table", {
      prompt: aiTablePrompt.value.trim(),
      row_count: aiTableRowCount.value,
      col_count: 5
    });
    if (data && data.data) {
      aiGeneratedTableResult.value = data.data;
      ElMessage.success("智能表格生成完成！");
    }
  } catch {
    ElMessage.error("智能建表生成失败");
  } finally {
    aiTableLoading.value = false;
  }
}

function insertGeneratedTableAsSheet() {
  const result = aiGeneratedTableResult.value;
  if (!result || !result.headers) return;
  pushUndoState();

  const newSheetId = `sheet_${Date.now()}`;
  const sheetName = result.sheet_name || `AI_${workbook.value.sheets.length + 1}`;
  const cells: Record<string, CellData> = {};
  const styles: Record<string, CellStyle> = {};
  const columnWidths: Record<string, number> = {};

  result.headers.forEach((h: string, cIdx: number) => {
    cells[`0_${cIdx}`] = { v: h, m: h, t: "s" };
    styles[`0_${cIdx}`] = { bl: 1, bg: "#f4f5f7", ht: "center" };
    if (result.column_widths?.[cIdx]) {
      columnWidths[String(cIdx)] = result.column_widths[cIdx];
    }
  });

  const rows = result.rows || [];
  rows.forEach((row: any[], rIdx: number) => {
    const r = rIdx + 1;
    row.forEach((val: any, cIdx: number) => {
      const key = `${r}_${cIdx}`;
      if (typeof val === "string" && val.startsWith("=")) {
        cells[key] = { f: val, t: "f" };
      } else {
        const num = Number(val);
        const isNum = !isNaN(num) && val !== "" && val !== null;
        cells[key] = {
          v: isNum ? num : val,
          m: String(val ?? ""),
          t: isNum ? "n" : "s"
        };
      }
    });
  });

  if (result.summary_row && result.summary_row.length) {
    const r = rows.length + 1;
    result.summary_row.forEach((val: any, cIdx: number) => {
      const key = `${r}_${cIdx}`;
      styles[key] = { bl: 1, bg: "#fafafa" };
      if (typeof val === "string" && val.startsWith("=")) {
        cells[key] = { f: val, t: "f" };
      } else {
        cells[key] = { v: val, m: String(val ?? ""), t: "s" };
      }
    });
  }

  const newSheet: Sheet = {
    id: newSheetId,
    name: sheetName,
    rowCount: Math.max(rows.length + 20, 60),
    colCount: Math.max(result.headers.length + 5, 26),
    cells,
    styles,
    images: [],
    charts: [],
    mergedCells: [],
    cfRules: [],
    columnWidths,
    rowHeights: {}
  };

  workbook.value.sheets.push(newSheet);
  workbook.value.activeSheetId = newSheetId;
  scheduleAutoSave();
  showAiDrawer.value = false;
  ElMessage.success(`已插入全新工作表《${sheetName}》`);
}

async function analyzeAiInsights() {
  if (!currentSheet.value) return;
  aiInsightsLoading.value = true;
  try {
    const headers: string[] = [];
    for (let c = 0; c < colCount.value; c++) {
      const val = getCellDisplayValue(0, c);
      if (val) headers.push(val);
    }

    const rowsSample: any[][] = [];
    for (let r = 1; r < Math.min(rowCount.value, 30); r++) {
      const rowVals: any[] = [];
      let hasData = false;
      for (let c = 0; c < (headers.length || 10); c++) {
        const val = getCellDisplayValue(r, c);
        if (val) hasData = true;
        rowVals.push(val);
      }
      if (hasData) rowsSample.push(rowVals);
    }

    const { data } = await api.post("/ai/spreadsheet/insights", {
      sheet_name: currentSheet.value.name,
      headers: headers.length ? headers : ["列A", "列B", "列C"],
      rows_sample: rowsSample,
      total_rows: rowsSample.length
    });

    if (data && data.data) {
      aiInsightsResult.value = data.data;
      ElMessage.success("数据洞察分析已完成！");
    }
  } catch {
    ElMessage.error("数据洞察分析失败");
  } finally {
    aiInsightsLoading.value = false;
  }
}

async function processRangeAction(action: string, targetLang: string = "en") {
  aiProcessLoading.value = true;
  try {
    const rangeData: any[][] = [];
    for (let r = selMinRow.value; r <= selMaxRow.value; r++) {
      const row: any[] = [];
      for (let c = selMinCol.value; c <= selMaxCol.value; c++) {
        row.push(getCellDisplayValue(r, c));
      }
      rangeData.push(row);
    }

    const { data } = await api.post("/ai/spreadsheet/process-range", {
      action,
      range_data: rangeData,
      target_lang: targetLang
    });

    if (data && data.data?.processed_data) {
      pushUndoState();
      const processed = data.data.processed_data;
      processed.forEach((pRow: any[], rOffset: number) => {
        const targetR = selMinRow.value + rOffset;
        pRow.forEach((val: any, cOffset: number) => {
          const targetC = selMinCol.value + cOffset;
          const key = `${targetR}_${targetC}`;
          const num = Number(val);
          const isNum = !isNaN(num) && String(val).trim() !== "";
          currentSheet.value.cells[key] = {
            v: isNum ? num : val,
            m: String(val ?? ""),
            t: isNum ? "n" : "s"
          };
        });
      });
      scheduleAutoSave();
      ElMessage.success(data.data.summary || "选区处理完成");
    }
  } catch {
    ElMessage.error("选区处理失败");
  } finally {
    aiProcessLoading.value = false;
  }
}

async function sendAiChatMessage() {
  const query = aiChatInput.value.trim();
  if (!query) return;
  aiChatInput.value = "";
  aiChatMessages.value.push({ role: 'user', content: query });
  aiChatStreaming.value = true;

  try {
    const docContext = `当前电子表格《${title.value}》工作表《${currentSheet.value.name}》数据概要：\n${getSheetSampleString()}`;
    const token = authStore.token;
    const response = await fetch("/api/ai/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({
        messages: aiChatMessages.value,
        doc_context: docContext
      })
    });

    if (!response.body) throw new Error("No stream");
    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let aiMsg = "";
    aiChatMessages.value.push({ role: 'assistant', content: "" });
    const lastIdx = aiChatMessages.value.length - 1;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split("\n");
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const dataStr = line.replace("data: ", "").trim();
          if (dataStr === "[DONE]") break;
          try {
            const parsed = JSON.parse(dataStr);
            if (parsed.content) {
              aiMsg += parsed.content;
              aiChatMessages.value[lastIdx]!.content = aiMsg;
            }
          } catch {}
        }
      }
    }
  } catch {
    aiChatMessages.value.push({ role: 'assistant', content: '抱歉，回答遇到了问题，请重试。' });
  } finally {
    aiChatStreaming.value = false;
  }
}

function getSheetSampleString(): string {
  const lines: string[] = [];
  for (let r = 0; r < Math.min(rowCount.value, 15); r++) {
    const rowVals: string[] = [];
    for (let c = 0; c < Math.min(colCount.value, 10); c++) {
      rowVals.push(getCellDisplayValue(r, c));
    }
    lines.push(rowVals.join(" | "));
  }
  return lines.join("\n");
}

// ── Persistence & Auto-Save ───────────────────────────
let autoSaveTimer: number | null = null;
const isDirty = ref(false);

function scheduleAutoSave() {
  isDirty.value = true;
  saveHint.value = "未保存更改...";
  if (autoSaveTimer) clearTimeout(autoSaveTimer);
  autoSaveTimer = window.setTimeout(() => {
    saveNow();
  }, 1000);
}

async function saveNow(): Promise<boolean> {
  if (!canEdit.value) return true;
  if (isEditing.value) {
    commitCellEdit();
  }
  saving.value = true;
  saveHint.value = "正在保存...";
  try {
    const contentStr = JSON.stringify(workbook.value);
    await api.put(`/documents/${props.docId}/content`, {
      content_json: contentStr
    });
    isDirty.value = false;
    saveHint.value = `已于 ${new Date().toLocaleTimeString()} 保存`;
    emit("updated");
    return true;
  } catch (e) {
    saveHint.value = "保存失败";
    return false;
  } finally {
    saving.value = false;
  }
}

async function saveTitle() {
  if (!canEdit.value || !title.value.trim()) return;
  try {
    await api.patch(`/documents/${props.docId}`, { title: title.value.trim() });
    ElMessage.success("标题已更新");
    emit("updated");
  } catch {}
}

async function loadDocumentData() {
  loading.value = true;
  try {
    const { data } = await api.get(`/documents/${props.docId}`);
    meta.value = data;
    title.value = data.title;
    
    let rawJson = data.content_json;
    if (!rawJson && data.current_version_id) {
      try {
        const verRes = await api.get(`/documents/${props.docId}/versions/${data.current_version_id}/content`);
        rawJson = verRes.data?.content_json;
      } catch {}
    }
    
    if (rawJson) {
      try {
        const parsed = typeof rawJson === "string" ? JSON.parse(rawJson) : rawJson;
        if (parsed && Array.isArray(parsed.sheets) && parsed.sheets.length > 0) {
          workbook.value = parsed;
        }
      } catch (e) {
        console.error("Failed to parse sheet json:", e);
      }
    }
    nextTick(() => {
      currentSheet.value?.charts?.forEach(c => renderChartDom(c));
    });
  } catch {
    ElMessage.error("加载表格失败");
  } finally {
    loading.value = false;
  }
}

// ── Real-Time Socket Collaboration ────────────────────
function setupSocket() {
  const url = import.meta.env.VITE_SOCKET_URL || "";
  socket = io(url || undefined, { path: "/socket.io", transports: ["websocket", "polling"] });

  socket.on("connect", () => {
    socket?.emit("join_document", { document_id: props.docId });
    broadcastAwareness();
  });

  socket.on("spreadsheet_update", (msg: any) => {
    if (msg.document_id === props.docId && msg.payload) {
      const p = msg.payload;
      const targetSheet = workbook.value.sheets.find(s => s.id === p.sheetId);

      // 1. Single cell update
      if (p.action === "cell_update" || (p.r !== undefined && p.c !== undefined && p.action === undefined)) {
        if (targetSheet) {
          if (!targetSheet.cells) targetSheet.cells = {};
          const key = `${p.r}_${p.c}`;
          if (p.cell) {
            targetSheet.cells[key] = p.cell;
          } else {
            delete targetSheet.cells[key];
          }
        }
      }
      // 2. Batch cells update
      else if (p.action === "batch_cells_update") {
        if (targetSheet) {
          if (!targetSheet.cells) targetSheet.cells = {};
          if (p.cells) {
            Object.assign(targetSheet.cells, p.cells);
          }
          if (p.deletedKeys && Array.isArray(p.deletedKeys)) {
            p.deletedKeys.forEach((k: string) => delete targetSheet.cells[k]);
          }
        }
      }
      // 3. Merged cells update
      else if (p.action === "merged_cells_update") {
        if (targetSheet) {
          targetSheet.mergedCells = p.mergedCells || [];
          if (p.styles) {
            if (!targetSheet.styles) targetSheet.styles = {};
            Object.assign(targetSheet.styles, p.styles);
          }
        }
      }
      // 4. Styles update
      else if (p.action === "styles_update") {
        if (targetSheet) {
          if (!targetSheet.styles) targetSheet.styles = {};
          if (p.styles) {
            Object.assign(targetSheet.styles, p.styles);
          }
        }
      }
      // 5. Dimensions update
      else if (p.action === "dimensions_update") {
        if (targetSheet) {
          if (p.columnWidths) targetSheet.columnWidths = { ...(targetSheet.columnWidths || {}), ...p.columnWidths };
          if (p.rowHeights) targetSheet.rowHeights = { ...(targetSheet.rowHeights || {}), ...p.rowHeights };
          if (p.rowCount !== undefined) targetSheet.rowCount = p.rowCount;
          if (p.colCount !== undefined) targetSheet.colCount = p.colCount;
        }
      }
      // 6. Workbook structure update (sheets add/delete/rename)
      else if (p.action === "workbook_structure_update") {
        if (p.sheets) {
          workbook.value.sheets = p.sheets;
        }
      }
      // 7. Full sheet sync
      else if (p.action === "sheet_sync") {
        if (targetSheet && p.sheetData) {
          Object.assign(targetSheet, p.sheetData);
          nextTick(() => {
            targetSheet.charts?.forEach(c => renderChartDom(c));
          });
        }
      }
    }
  });

  socket.on("spreadsheet_awareness", (msg: any) => {
    if (msg.document_id === props.docId && msg.payload) {
      const user = msg.payload;
      if (user.isLeft) {
        collabUsers.value = collabUsers.value.filter(u => u.id !== user.id);
        return;
      }
      const idx = collabUsers.value.findIndex(u => u.id === user.id);
      if (idx >= 0) {
        collabUsers.value[idx] = user;
      } else {
        collabUsers.value.push(user);
      }
    }
  });
}

function broadcastSheetMutation(payload: any) {
  socket?.emit("spreadsheet_update", {
    document_id: props.docId,
    payload: {
      sheetId: workbook.value.activeSheetId,
      ...payload
    }
  });
}

function broadcastCellUpdate(r: number, c: number, cell: CellData | undefined) {
  broadcastSheetMutation({
    action: "cell_update",
    r,
    c,
    cell
  });
}

function broadcastBatchCells(cells?: Record<string, CellData>, deletedKeys?: string[]) {
  broadcastSheetMutation({
    action: "batch_cells_update",
    cells: cells || currentSheet.value?.cells || {},
    deletedKeys
  });
}

function broadcastMergedCells() {
  if (!currentSheet.value) return;
  broadcastSheetMutation({
    action: "merged_cells_update",
    mergedCells: currentSheet.value.mergedCells || [],
    styles: currentSheet.value.styles || {}
  });
}

function broadcastStyles() {
  if (!currentSheet.value) return;
  broadcastSheetMutation({
    action: "styles_update",
    styles: currentSheet.value.styles || {}
  });
}

function broadcastDimensions() {
  if (!currentSheet.value) return;
  broadcastSheetMutation({
    action: "dimensions_update",
    rowCount: currentSheet.value.rowCount,
    colCount: currentSheet.value.colCount,
    columnWidths: currentSheet.value.columnWidths,
    rowHeights: currentSheet.value.rowHeights
  });
}

function broadcastWorkbookStructure() {
  socket?.emit("spreadsheet_update", {
    document_id: props.docId,
    payload: {
      action: "workbook_structure_update",
      sheets: JSON.parse(JSON.stringify(workbook.value.sheets)),
      activeSheetId: workbook.value.activeSheetId
    }
  });
}

function broadcastFullSheetSync() {
  if (!currentSheet.value) return;
  broadcastSheetMutation({
    action: "sheet_sync",
    sheetData: JSON.parse(JSON.stringify(currentSheet.value))
  });
}

watch(collabUsers, () => {
  if (getLockingCollaborator(startRow.value, startCol.value)) {
    for (let offset = 1; offset < 30; offset++) {
      const nextR = startRow.value + offset;
      if (nextR < rowCount.value && !getLockingCollaborator(nextR, startCol.value)) {
        tryMoveSelection(nextR, startCol.value);
        break;
      }
    }
  }
}, { deep: true });

// --- Live Collaboration Watcher ---
watch([startRow, startCol, isEditing, activeCellFormula], () => {
  broadcastAwareness();
}, { deep: true });

function broadcastAwareness() {
  const user = authStore.user;
  if (!user) return;
  const colors = ["#409eff", "#67c23a", "#e6a23c", "#f56c6c", "#8e44ad", "#e84393", "#00cec9", "#fdcb6e"];
  const color = colors[(user.id || 0) % colors.length];

  socket?.emit("spreadsheet_awareness", {
    document_id: props.docId,
    payload: {
      id: String(user.id),
      name: user.display_name || user.login_name,
      avatar: (user as any).avatar_url || (user as any).avatar || "",
      color: color,
      sheetId: workbook.value.activeSheetId,
      row: startRow.value,
      col: startCol.value,
      isEditing: isEditing.value,
      editValue: isEditing.value ? activeCellFormula.value : undefined
    }
  });
}

function getLockingCollaborator(r: number, c: number) {
  const currentSheetId = workbook.value?.activeSheetId;
  return collabUsers.value.find(u => 
    u.id !== String(authStore.user?.id) && 
    u.row === r && 
    u.col === c && 
    (!u.sheetId || u.sheetId === currentSheetId)
  );
}

function isCellCollabActive(r: number, c: number): boolean {
  return !!getLockingCollaborator(r, c);
}

function getCollabUserAtCell(r: number, c: number) {
  return getLockingCollaborator(r, c);
}

const currentCellLocker = computed(() => getLockingCollaborator(startRow.value, startCol.value));
const isCurrentCellLocked = computed(() => !canEdit.value || !!currentCellLocker.value);

const isGeneratingTitle = ref(false);

onBeforeRouteLeave((_to, _from, next) => {
  if (isGeneratingTitle.value) {
    ElMessage.warning(t('editor.aiGeneratingTitleBlock', 'AI 正在自动识别并填写标题，请勿离开...'));
    next(false);
  } else {
    next();
  }
});

async function handleGenerateTitle() {
  if (isGeneratingTitle.value) return;

  const parts: string[] = [];
  const sheetList = workbook.value?.sheets || [];
  if (sheetList.length) {
    for (const s of sheetList.slice(0, 3)) {
      const sName = s.name || "工作表";
      const sampleVals: string[] = [];
      const cells = s.cells || {};
      for (const k of Object.keys(cells).slice(0, 30)) {
        const val = cells[k]?.v ?? cells[k]?.m ?? "";
        if (val) sampleVals.push(String(val));
      }
      parts.push(`工作表: ${sName}\n数据内容: ${sampleVals.join(", ")}`);
    }
  }

  const text = parts.join("\n\n").trim();
  if (!text || text.length < 5) {
    ElMessage.warning(t("editor.aiTitleEmptyWarning", "文档内容过少或为空，无法识别生成标题，请先录入文档内容。"));
    return;
  }

  isGeneratingTitle.value = true;
  const loadingInstance = ElLoading.service({
    lock: true,
    text: "AI 正在深度识别表格信息并提炼精简标题，请勿离开...",
    background: "rgba(0, 0, 0, 0.45)",
  });

  try {
    const { data } = await api.post("/ai/generate-title", {
      content: text.slice(0, 4000),
      doc_id: props.docId,
      doc_type: "spreadsheet",
      ai_model: "deepseek"
    });

    if (data && data.title && data.title !== "无法识别") {
      title.value = data.title;
      await saveTitle();
      ElMessage.success(t("editor.aiTitleSuccess", { title: data.title }));
    } else {
      ElMessage.warning(data?.error || t("editor.aiTitleUnrecognized", "无法确定文档的总结内容，无法识别生成有效标题。"));
    }
  } catch (err: any) {
    console.error("AI Title generation error:", err);
    const msg = err.response?.data?.error || t("editor.aiTitleUnrecognized", "无法确定文档的总结内容，无法识别生成有效标题。");
    ElMessage.warning(msg);
  } finally {
    isGeneratingTitle.value = false;
    loadingInstance.close();
  }
}

function goBack() {
  if (isGeneratingTitle.value) {
    ElMessage.warning(t('editor.aiGeneratingTitleBlock', 'AI 正在自动识别并填写标题，请勿离开...'));
    return;
  }
  router.back();
}

async function handleApprove() {
  try {
    await api.post(`/approvals/decide`, {
      document_id: props.docId,
      decision: "approved",
      participant_id: meta.value.pending_participant_id
    });
    ElMessage.success("已同意审批");
    loadDocumentData();
  } catch {}
}

async function handleReject() {
  try {
    await api.post(`/approvals/decide`, {
      document_id: props.docId,
      decision: "rejected",
      participant_id: meta.value.pending_participant_id
    });
    ElMessage.success("已驳回");
    loadDocumentData();
  } catch {}
}

async function submitApprovalFlow() {
  if (!selectedApprovers.value.length) {
    return ElMessage.warning("请选择审批人");
  }
  submittingApproval.value = true;
  try {
    await api.post(`/documents/${props.docId}/approval/start`, {
      flow_type: approvalType.value,
      approver_ids: selectedApprovers.value
    });
    ElMessage.success("审批已发起");
    showApprovalDialog.value = false;
    loadDocumentData();
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || "发起审批失败");
  } finally {
    submittingApproval.value = false;
  }
}

function onPermissionsSaved() {
  loadDocumentData();
}

async function confirmDeleteDoc() {
  try {
    await ElMessageBox.confirm(
      t("editor.deleteDocConfirm", "确定要永久删除这篇表格文档吗？此操作不可撤销。"),
      t("common.confirm", "提示"),
      { type: "warning" }
    );
    await api.delete(`/documents/${props.docId}`);
    ElMessage.success(t("editor.deleteSuccess", "文档已删除"));
    router.push({ name: "library" });
  } catch {}
}

async function loadUsersList() {
  try {
    const { data } = await api.get("/users");
    usersList.value = data.items || [];
  } catch {}
}

function handleBeforeUnload(e: BeforeUnloadEvent) {
  if (isGeneratingTitle.value) {
    e.preventDefault();
    e.returnValue = "";
    return "";
  }
  if (isDirty.value || isEditing.value) {
    if (isEditing.value) commitCellEdit();
    try {
      const token = localStorage.getItem("token") || "";
      const url = import.meta.env.VITE_API_URL || "/api";
      fetch(`${url}/documents/${props.docId}/content`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ content_json: JSON.stringify(workbook.value) }),
        keepalive: true
      });
    } catch {}
    e.preventDefault();
    e.returnValue = "";
  }
}

onMounted(() => {
  // If initialDocData already has content_json, initialize immediately
  if (props.initialDocData?.content_json) {
    try {
      const raw = props.initialDocData.content_json;
      const parsed = typeof raw === "string" ? JSON.parse(raw) : raw;
      if (parsed && Array.isArray(parsed.sheets) && parsed.sheets.length > 0) {
        workbook.value = parsed;
      }
    } catch {}
  }

  loadDocumentData();
  setupSocket();
  loadUsersList();
  window.addEventListener("click", () => {
    contextMenuVisible.value = false;
    filterDropdownVisible.value = false;
  });
  window.addEventListener("beforeunload", handleBeforeUnload);
});

onBeforeUnmount(async () => {
  stopAutoScrollLoop();
  window.removeEventListener("mousemove", onWindowDragMouseMove);
  window.removeEventListener("mouseup", onWindowDragMouseUp);
  window.removeEventListener("beforeunload", handleBeforeUnload);
  if (autoSaveTimer) {
    clearTimeout(autoSaveTimer);
    autoSaveTimer = null;
  }
  if (isEditing.value) {
    commitCellEdit();
  }
  if (isDirty.value) {
    await saveNow();
  }
});

onUnmounted(() => {
  if (socket) {
    socket.emit("spreadsheet_awareness", {
      document_id: props.docId,
      payload: {
        id: String(authStore.user?.id),
        isLeft: true
      }
    });
    socket.emit("leave_document", { document_id: props.docId });
    socket.disconnect();
  }
  chartInstances.forEach(inst => inst.dispose());
  chartInstances.clear();
});
</script>

<style scoped>
.spreadsheet-editor-root {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: var(--el-bg-color-page);
  overflow: hidden;
  outline: none;
}

/* ── 1. Top Header Bar (Clean Modern) ───────────────── */
.header-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 16px;
  background: var(--el-bg-color-overlay);
  border-bottom: 1px solid var(--el-border-color-lighter);
  flex-shrink: 0;
  gap: 12px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
}

.title-input {
  width: 260px;
  font-weight: 600;
}

.doc-type-badge {
  font-weight: 600;
  border-radius: 4px;
}

.save-status-text {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ai-header-btn {
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
  border: none;
  color: #ffffff;
  font-weight: 600;
}

.ai-header-btn:hover {
  background: linear-gradient(135deg, #4338ca 0%, #6d28d9 100%);
}

.collab-avatars {
  display: flex;
  align-items: center;
  margin-right: 8px;
}

.avatar-dot {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  color: #fff;
  font-size: 11px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-left: -6px;
  border: 2px solid #fff;
  cursor: default;
}

/* ── 2. Ribbon Tabs Navigation Bar ───────────────────── */
.ribbon-tabs-nav {
  display: flex;
  align-items: center;
  background: #f1f5f9;
  border-bottom: 1px solid #cbd5e1;
  padding: 0 12px;
  gap: 2px;
  flex-shrink: 0;
}

.ribbon-tab-btn {
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 500;
  color: #475569;
  background: transparent;
  border: 1px solid transparent;
  border-bottom: none;
  border-radius: 4px 4px 0 0;
  cursor: pointer;
  display: flex;
  align-items: center;
  transition: all 0.15s;
}

.ribbon-tab-btn:hover {
  background: rgba(255, 255, 255, 0.6);
  color: #1e293b;
}

.ribbon-tab-btn.active {
  background: #ffffff;
  color: var(--el-color-primary);
  font-weight: 600;
  border-color: #cbd5e1 #cbd5e1 #ffffff;
  margin-bottom: -1px;
  z-index: 2;
}

.ribbon-tab-btn.ai-tab-btn {
  color: #7c3aed;
}

.ribbon-tab-btn.ai-tab-btn.active {
  color: #7c3aed;
  background: #ffffff;
}

/* ── 3. Ribbon Content Panel & Groups ────────────────── */
.ribbon-content-panel {
  background: #ffffff;
  border-bottom: 1px solid #cbd5e1;
  padding: 4px 12px 2px 12px;
  height: 98px;
  flex-shrink: 0;
  overflow-x: auto;
  overflow-y: hidden;
}

.ribbon-tab-pane {
  display: flex;
  align-items: stretch;
  height: 100%;
  gap: 6px;
}

.ribbon-group {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 0 4px;
  height: 100%;
}

.group-controls-row {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
}

.group-controls-col {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
  flex: 1;
}

.sub-row {
  display: flex;
  align-items: center;
  gap: 3px;
}

.group-label {
  text-align: center;
  font-size: 11px;
  color: #94a3b8;
  padding-bottom: 2px;
  user-select: none;
  font-weight: 500;
}

.ribbon-divider {
  width: 1px;
  height: 70px;
  background: #e2e8f0;
  margin: auto 4px;
  flex-shrink: 0;
}

/* Ribbon Button Styles */
.ribbon-big-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 50px;
  height: 64px;
  padding: 4px 6px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 4px;
  cursor: pointer;
  color: #334155;
  font-size: 11px;
  gap: 4px;
  transition: all 0.15s;
}

.ribbon-big-btn:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.ribbon-big-btn.active {
  background: #e0f2fe;
  border-color: #7dd3fc;
  color: #0284c7;
}

.ribbon-big-btn.ai-special-btn {
  color: #6d28d9;
}

.ribbon-big-btn.ai-special-btn:hover {
  background: #f5f3ff;
  border-color: #ddd6fe;
}

.ribbon-small-stack {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 3px;
}

.ribbon-mini-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 22px;
  padding: 0 6px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 3px;
  cursor: pointer;
  color: #334155;
  font-size: 11px;
  white-space: nowrap;
  transition: all 0.15s;
}

.ribbon-mini-btn:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.ribbon-mini-btn.active {
  background: #e0f2fe;
  color: #0284c7;
  border-color: #7dd3fc;
}

.ribbon-btn-square {
  width: 24px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 3px;
  cursor: pointer;
  color: #334155;
  font-size: 12px;
  transition: all 0.15s;
}

.ribbon-btn-square:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.ribbon-btn-square.active {
  background: #e0f2fe;
  color: #0284c7;
  border-color: #7dd3fc;
}

.dropdown-sq-btn {
  width: 32px;
  gap: 2px;
}

.sub-arrow {
  font-size: 9px;
  color: #64748b;
}

/* Color Buttons with Stripe */
.ribbon-color-btn {
  position: relative;
  width: 24px;
  height: 22px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 1px solid transparent;
  border-radius: 3px;
  cursor: pointer;
}

.ribbon-color-btn:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.font-color-char {
  font-weight: 900;
  font-size: 13px;
  line-height: 12px;
}

.color-stripe {
  position: absolute;
  bottom: 2px;
  width: 16px;
  height: 3px;
  border-radius: 1px;
}

.native-color-inp {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
  width: 100%;
  height: 100%;
}

.svg-icon {
  display: inline-block;
  flex-shrink: 0;
}

.svg-icon.big-icon {
  color: #475569;
}

.fx-large-icon {
  font-family: 'Times New Roman', serif;
  font-style: italic;
  font-weight: bold;
  font-size: 20px;
  color: #2563eb;
}

/* ── 4. Excel Formula Bar ────────────────────────────── */
.formula-bar {
  display: flex;
  align-items: center;
  padding: 3px 12px;
  background: #ffffff;
  border-bottom: 1px solid #cbd5e1;
  gap: 6px;
  flex-shrink: 0;
  height: 30px;
}

.cell-address-box {
  min-width: 65px;
  text-align: center;
  font-family: Consolas, Monaco, monospace;
  font-weight: 700;
  font-size: 12px;
  padding: 2px 6px;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  border-radius: 3px;
  color: #0f172a;
}

.formula-bar-actions {
  display: flex;
  align-items: center;
  gap: 2px;
}

.fx-action-btn {
  border: none;
  background: transparent;
  font-size: 12px;
  color: #64748b;
  cursor: pointer;
  padding: 2px 5px;
  border-radius: 3px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.fx-action-btn:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.fx-action-btn.confirm:hover {
  color: #16a34a;
}

.fx-action-btn.fx-text {
  font-family: 'Times New Roman', serif;
  font-style: italic;
  font-weight: bold;
  font-size: 14px;
  color: #2563eb;
}

.formula-input-wrapper {
  flex: 1;
}

.formula-input {
  width: 100%;
  padding: 2px 8px;
  border: 1px solid #e2e8f0;
  border-radius: 3px;
  font-size: 13px;
  font-family: 'JetBrains Mono', Consolas, Monaco, monospace;
  outline: none;
}

.formula-input:focus {
  border-color: #3b82f6;
}

/* ── 5. Spreadsheet Viewport & Table Grid ────────────── */
.sheet-viewport-container {
  flex: 1;
  overflow: auto;
  background: #ffffff;
  position: relative;
  user-select: none;
}

.resize-guide-col {
  position: fixed;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--el-color-primary);
  pointer-events: none;
  z-index: 99;
}

.resize-guide-row {
  position: fixed;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--el-color-primary);
  pointer-events: none;
  z-index: 99;
}

.floating-images-layer, .floating-charts-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 10;
}

.floating-image-item {
  position: absolute;
  pointer-events: auto;
  border: 1px dashed var(--el-color-primary);
  background: rgba(255, 255, 255, 0.8);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  cursor: move;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  overflow: hidden;
}

.img-content {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.img-delete-btn {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  font-size: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

/* Floating Chart Card */
.floating-chart-card {
  position: absolute;
  pointer-events: auto;
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
  border: 1px solid var(--el-border-color-light);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 12;
}

.chart-card-header {
  height: 34px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 8px;
  cursor: move;
}

.chart-drag-handle {
  font-weight: 600;
  font-size: 12px;
  color: #334155;
  display: flex;
  align-items: center;
  gap: 4px;
}

.chart-header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.chart-act-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 12px;
  padding: 2px 4px;
  border-radius: 4px;
}

.chart-act-btn:hover {
  background: #e2e8f0;
}

.chart-act-btn.danger:hover {
  color: #ef4444;
}

.chart-render-body {
  flex: 1;
  width: 100%;
  min-height: 200px;
}

.spreadsheet-table {
  border-collapse: collapse;
  table-layout: fixed;
  user-select: none;
}

/* Sticky Freeze Styles */
.sticky-top-frozen {
  position: sticky;
  top: 0;
  z-index: 6;
}

.sticky-first-col {
  position: sticky;
  left: 0;
  z-index: 5;
  background: #f4f5f7 !important;
}

.sticky-first-col-cell {
  position: sticky;
  left: 46px;
  z-index: 3;
  background-color: #ffffff;
}

.corner-header {
  width: 46px;
  min-width: 46px;
  height: 24px;
  background: #f8fafc;
  border-right: 1px solid #dcdfe6;
  border-bottom: 1px solid #dcdfe6;
  position: sticky;
  top: 0;
  left: 0;
  z-index: 8;
  font-size: 11px;
  color: #94a3b8;
  cursor: pointer;
  text-align: center;
}

.col-header {
  height: 24px;
  background: #f8fafc;
  border-right: 1px solid #dcdfe6;
  border-bottom: 1px solid #dcdfe6;
  position: sticky;
  top: 0;
  z-index: 5;
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  text-align: center;
  cursor: pointer;
  position: relative;
}

.col-header.col-selected {
  background: #e0f2fe;
  color: #0284c7;
}

.col-header-content {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  padding: 0 4px;
}

.filter-funnel-icon {
  font-size: 9px;
  margin-left: 4px;
  color: #94a3b8;
  padding: 1px 2px;
  border-radius: 2px;
}

.filter-funnel-icon:hover, .filter-funnel-icon.active {
  color: #2563eb;
  background: #e0f2fe;
}

.col-resizer-handle {
  position: absolute;
  top: 0;
  right: -3px;
  width: 6px;
  height: 100%;
  cursor: col-resize;
  z-index: 7;
}

.col-resizer-handle:hover {
  background: #3b82f6;
}

.row-header {
  width: 46px;
  min-width: 46px;
  background: #f8fafc;
  border-right: 1px solid #dcdfe6;
  border-bottom: 1px solid #dcdfe6;
  position: sticky;
  left: 0;
  z-index: 4;
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  text-align: center;
  cursor: pointer;
  position: relative;
}

.row-header.row-selected {
  background: #e0f2fe;
  color: #0284c7;
}

.row-resizer-handle {
  position: absolute;
  bottom: -3px;
  left: 0;
  width: 100%;
  height: 6px;
  cursor: row-resize;
  z-index: 7;
}

.row-resizer-handle:hover {
  background: #3b82f6;
}

.cell-item {
  border-right: 1px solid #e2e8f0;
  border-bottom: 1px solid #e2e8f0;
  padding: 2px 5px;
  font-size: 12px;
  position: relative;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: cell;
  background-color: #ffffff;
}

.cell-item.cell-in-selection {
  background-color: rgba(59, 130, 246, 0.12) !important;
}

.cell-item.cell-active-primary {
  background-color: #ffffff !important;
}

.cell-item.sel-edge-top {
  border-top: 2px solid #2563eb !important;
}

.cell-item.sel-edge-bottom {
  border-bottom: 2px solid #2563eb !important;
}

.cell-item.sel-edge-left {
  border-left: 2px solid #2563eb !important;
}

.cell-item.sel-edge-right {
  border-right: 2px solid #2563eb !important;
}

.cell-item.cell-find-matched {
  outline: 2px dashed #f59e0b;
  outline-offset: -2px;
  background-color: #fef3c7 !important;
}

.fill-handle-square {
  position: absolute;
  bottom: -4px;
  right: -4px;
  width: 7px;
  height: 7px;
  background: #2563eb;
  border: 1px solid #ffffff;
  cursor: crosshair;
  z-index: 9;
}



.cell-inline-textarea {
  position: absolute;
  inset: 0;
  width: 100%;
  min-height: 100%;
  border: 2px solid #2563eb;
  outline: none;
  background: #ffffff;
  font-size: 12px;
  font-family: inherit;
  color: inherit;
  padding: 2px 4px;
  margin: 0;
  box-sizing: border-box;
  z-index: 20;
  resize: none;
  overflow: hidden;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.4;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  cursor: text !important;
  user-select: text !important;
}

.cell-rendered-val {
  display: block;
  width: 100%;
  height: 100%;
  min-height: 22px;
  line-height: 1.4;
  white-space: pre-wrap;
  word-break: break-word;
  overflow: hidden;
  text-overflow: ellipsis;
  user-select: none;
}

.collab-cell-badge {
  position: absolute;
  top: -22px;
  left: -2px;
  font-size: 11px;
  color: #fff;
  padding: 1px 6px 1px 3px;
  border-radius: 4px 4px 4px 0;
  pointer-events: none;
  z-index: 26;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 3px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
}

.collab-mini-avatar {
  width: 15px;
  height: 15px;
  border-radius: 50%;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.35);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  font-weight: bold;
  flex-shrink: 0;
}

.collab-mini-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.collab-badge-name {
  max-width: 90px;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 500;
}

.collab-editing-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background-color: #52c41a;
  box-shadow: 0 0 4px #52c41a;
  animation: pulse-dot 1s infinite alternate;
}
@keyframes pulse-dot { from { opacity: 0.4; } to { opacity: 1; } }

/* ── Collaborator Cell Hover Card ── */
.collab-hover-card {
  position: absolute;
  bottom: calc(100% + 6px);
  left: 50%;
  transform: translateX(-50%);
  background: #1f1f1f;
  color: #ffffff;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
  display: none;
  align-items: center;
  gap: 8px;
  z-index: 35;
  white-space: nowrap;
  pointer-events: none;
  border: 1px solid rgba(255, 255, 255, 0.15);
}

.collab-hover-card::after {
  content: "";
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 5px solid transparent;
  border-top-color: #1f1f1f;
}

.cell-item:hover .collab-hover-card {
  display: flex;
}

.collab-hover-avatar {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: bold;
  color: #fff;
  flex-shrink: 0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.collab-hover-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.collab-hover-info {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
  text-align: left;
}

.collab-hover-name {
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 4px;
}

.collab-hover-status {
  font-size: 11px;
  color: #ffd666;
  font-weight: normal;
}

.collab-hover-tip {
  font-size: 10px;
  color: #bfbfbf;
}

.collab-live-edit-bubble {
  position: absolute;
  top: 100%;
  left: -2px;
  min-width: 80px;
  background: white;
  border: 2px solid;
  border-radius: 0 4px 4px 4px;
  padding: 4px 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  font-size: 12px;
  color: #333;
  z-index: 25;
  white-space: pre-wrap;
  word-break: break-word;
  pointer-events: none;
}
.live-cursor-blink {
  animation: blink 1s step-end infinite;
}
@keyframes blink { 50% { opacity: 0; } }

/* ── 6. Context Menu ─────────────────────────────────── */
.spreadsheet-context-menu {
  position: fixed;
  z-index: 2000;
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.16), 0 2px 6px rgba(0, 0, 0, 0.08);
  border: 1px solid var(--el-border-color-lighter);
  padding: 5px 0;
  min-width: 200px;
  max-width: 260px;
  max-height: calc(100vh - 20px);
  overflow-y: auto;
  font-size: 13px;
  user-select: none;
}

.spreadsheet-context-menu::-webkit-scrollbar {
  width: 5px;
}
.spreadsheet-context-menu::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 4px;
}
.spreadsheet-context-menu::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.menu-item {
  padding: 6px 16px;
  cursor: pointer;
  color: var(--el-text-color-primary);
  transition: background 0.15s;
}

.menu-item.ai-item {
  color: #7c3aed;
  font-weight: 600;
  background: rgba(124, 58, 237, 0.04);
}

.menu-item.ai-item:hover {
  background: rgba(124, 58, 237, 0.1);
  color: #6d28d9;
}

.menu-item:hover {
  background: var(--el-fill-color-light);
  color: var(--el-color-primary);
}

.menu-item.danger:hover {
  color: #f56c6c;
}

.menu-divider {
  height: 1px;
  background: var(--el-border-color-lighter);
  margin: 4px 0;
}

/* ── 7. Bottom Sheet Tabs Bar & Live Aggregates ──────── */
.sheet-tabs-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f8fafc;
  border-top: 1px solid #cbd5e1;
  padding: 0 12px;
  height: 30px;
  flex-shrink: 0;
  gap: 16px;
}

.sheet-tabs-scroll {
  display: flex;
  align-items: center;
  gap: 3px;
  overflow-x: auto;
}

.sheet-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 12px;
  background: #e2e8f0;
  border-radius: 4px 4px 0 0;
  font-size: 12px;
  font-weight: 500;
  color: #475569;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s;
}

.sheet-tab.active {
  background: #ffffff;
  color: #2563eb;
  font-weight: 600;
  border-color: #cbd5e1 #cbd5e1 #ffffff;
}

.tab-close {
  font-size: 10px;
  color: #94a3b8;
  border-radius: 50%;
  width: 14px;
  height: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.tab-close:hover {
  background: rgba(0, 0, 0, 0.1);
  color: #f56c6c;
}

.add-sheet-btn {
  width: 20px;
  height: 20px;
  border-radius: 3px;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  font-size: 13px;
  font-weight: bold;
  color: #64748b;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.add-sheet-btn:hover {
  color: #2563eb;
  border-color: #2563eb;
}

.live-aggregates-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
}

.agg-pill {
  background: #ffffff;
  border: 1px solid #dcdfe6;
  padding: 1px 6px;
  border-radius: 3px;
  color: #475569;
  cursor: pointer;
  transition: all 0.15s;
}

.agg-pill:hover {
  background: #e0f2fe;
  border-color: #7dd3fc;
  color: #0284c7;
}

.sheet-dim-text {
  color: var(--el-text-color-secondary);
  margin-left: 6px;
}

/* ── 8. Find & Replace Modal ─────────────────────────── */
.find-replace-modal {
  position: fixed;
  top: 130px;
  right: 40px;
  z-index: 120;
  width: 320px;
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  border: 1px solid var(--el-border-color-light);
  overflow: hidden;
}

.find-modal-header {
  background: #f8fafc;
  padding: 8px 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #e2e8f0;
}

.find-modal-title {
  font-weight: 600;
  font-size: 13px;
}

.find-close-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 13px;
  color: #94a3b8;
}

.find-modal-body {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.find-input-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: #475569;
}

.find-options-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
}

.find-count-hint {
  font-size: 11px;
  color: #64748b;
  font-weight: 600;
}

.find-actions-row {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  margin-top: 4px;
}

/* ── 9. Filter Popup ─────────────────────────────────── */
.filter-dropdown-popup {
  position: fixed;
  z-index: 110;
  width: 220px;
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  border: 1px solid var(--el-border-color-lighter);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.filter-popup-header {
  padding: 8px 10px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.filter-close-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  color: #94a3b8;
}

.filter-search-box {
  padding: 6px 10px;
}

.filter-values-list {
  max-height: 180px;
  overflow-y: auto;
  padding: 4px 10px;
}

.filter-val-item {
  padding: 2px 0;
  cursor: pointer;
}

.filter-popup-footer {
  padding: 6px 10px;
  border-top: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* ── 10. Version History Drawer ──────────────────────── */
.version-list-wrapper {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 4px;
}

.version-card-item {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px;
}

.ver-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.ver-badge {
  background: var(--el-color-primary-light-8);
  color: var(--el-color-primary);
  font-weight: bold;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
}

.ver-time {
  font-size: 11px;
  color: #64748b;
}

.ver-author {
  font-size: 12px;
  color: #334155;
  margin-bottom: 8px;
}

.ver-actions {
  display: flex;
  justify-content: flex-end;
}

.empty-versions {
  text-align: center;
  color: #94a3b8;
  padding: 30px 0;
  font-size: 13px;
}

/* ── 11. AI Copilot Drawer Styles ────────────────────── */
.sheet-ai-drawer :deep(.el-drawer__header) {
  margin-bottom: 8px;
  font-weight: bold;
  color: #6d28d9;
}

.ai-copilot-tabs :deep(.el-tabs__item) {
  font-size: 13px;
  font-weight: 600;
}

.ai-panel-body {
  padding: 4px 8px;
}

.context-info-bar {
  margin-bottom: 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  display: flex;
  align-items: center;
}

.ai-prompt-input-box {
  background: #fcfcfd;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 16px;
}

.quick-tags-row {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.quick-tag-label {
  font-size: 11px;
  color: var(--el-text-color-secondary);
}

.clickable-tag {
  cursor: pointer;
  transition: all 0.15s;
}

.clickable-tag:hover {
  color: var(--el-color-primary);
  border-color: var(--el-color-primary);
  transform: translateY(-1px);
}

.ai-result-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px;
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.result-title {
  font-weight: bold;
  font-size: 13px;
  color: #1e293b;
}

.code-formula-box {
  font-family: 'JetBrains Mono', Consolas, Monaco, monospace;
  font-size: 15px;
  font-weight: bold;
  color: #2563eb;
  background: #ffffff;
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  margin-bottom: 8px;
}

.result-desc {
  font-size: 12px;
  color: #475569;
  line-height: 1.5;
  margin: 4px 0;
}

.result-alt {
  font-size: 12px;
  color: #64748b;
  margin: 4px 0;
}

.table-preview-mini {
  max-height: 140px;
  overflow: auto;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  margin-bottom: 6px;
}

.preview-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
}

.preview-table th, .preview-table td {
  border: 1px solid #e2e8f0;
  padding: 4px 6px;
  white-space: nowrap;
}

.preview-table th {
  background: #f1f5f9;
  font-weight: 600;
}

.preview-hint {
  font-size: 11px;
  color: #64748b;
}

/* Insights Display */
.insights-content-wrapper {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.insight-box {
  background: #f8fafc;
  border-radius: 8px;
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
}

.insight-box h4 {
  margin: 0 0 6px 0;
  font-size: 13px;
  color: #1e293b;
}

.insight-box p {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: #475569;
}

.insight-box ul {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  color: #475569;
  line-height: 1.6;
}

.danger-box {
  background: #fef2f2;
  border-color: #fecaca;
}

.danger-box h4 {
  color: #b91c1c;
}

.success-box {
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.success-box h4 {
  color: #15803d;
}

.metrics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.metric-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 8px;
  text-align: center;
}

.metric-label {
  font-size: 11px;
  color: #64748b;
}

.metric-val {
  font-size: 16px;
  font-weight: bold;
  color: #2563eb;
  margin-top: 2px;
}

/* Actions Stack */
.actions-stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.action-card-btn {
  height: auto;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  text-align: left;
  border-radius: 8px;
  border: 1px solid var(--el-border-color-light);
}

.action-btn-title {
  font-weight: bold;
  font-size: 13px;
  color: var(--el-text-color-primary);
  margin-bottom: 2px;
}

.action-btn-sub {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  white-space: normal;
  line-height: 1.4;
}

/* Chat Tab */
.ai-chat-tab-body {
  display: flex;
  flex-direction: column;
  height: 480px;
}

.chat-messages-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chat-msg-row {
  display: flex;
  gap: 8px;
}

.chat-msg-row.user {
  flex-direction: row-reverse;
}

.msg-avatar {
  font-size: 12px;
  font-weight: bold;
  padding: 4px 6px;
  border-radius: 4px;
  background: #e2e8f0;
  height: fit-content;
}

.msg-bubble {
  max-width: 80%;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.5;
}

.chat-msg-row.user .msg-bubble {
  background: var(--el-color-primary);
  color: #ffffff;
}

.chat-msg-row.assistant .msg-bubble {
  background: #f1f5f9;
  color: #1e293b;
  border: 1px solid #e2e8f0;
}

.chat-input-box {
  margin-top: 8px;
  border-top: 1px solid var(--el-border-color-lighter);
  padding-top: 8px;
}

.collab-badge-lock-icon {
  font-size: 9px;
  margin-right: 2px;
}
.formula-input-locked {
  background-color: #fffbe6 !important;
  color: #d48806 !important;
  cursor: not-allowed !important;
  border-color: #ffe58f !important;
}

/* ── Bottom & Right Edge Append Bars ─────────────────── */
.bottom-append-bar {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 10px 16px;
  background: #ffffff;
  border-top: 1px solid #e2e8f0;
  border-bottom: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  font-size: 13px;
  color: #475569;
  user-select: none;
  min-width: fit-content;
}

.bottom-append-bar .append-section {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bottom-append-bar .append-plus-icon {
  font-size: 14px;
  color: #2563eb;
  font-weight: bold;
}

.bottom-append-bar .append-label {
  font-weight: 500;
  color: #334155;
}

.bottom-append-bar .append-input-num {
  width: 90px;
}

.bottom-append-bar .append-unit {
  color: #64748b;
  font-weight: 500;
}

.bottom-append-bar .append-action-btn {
  font-weight: 500;
  padding: 4px 14px;
}

.bottom-append-bar .quick-append-tags {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: 6px;
}

.bottom-append-bar .quick-tag {
  display: inline-block;
  padding: 2px 8px;
  font-size: 11px;
  color: #64748b;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.bottom-append-bar .quick-tag:hover {
  color: #2563eb;
  background: #eff6ff;
  border-color: #bfdbfe;
}

.bottom-append-bar .append-divider {
  width: 1px;
  height: 20px;
  background: #e2e8f0;
}

.col-header-add-edge {
  width: 76px !important;
  min-width: 76px !important;
  max-width: 76px !important;
  background: #f8fafc !important;
  cursor: pointer !important;
  transition: background 0.15s;
  border-left: 1px dashed #cbd5e1 !important;
}

.col-header-add-edge:hover {
  background: #eff6ff !important;
  color: #2563eb !important;
}

.add-col-inner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  font-size: 12px;
  color: #64748b;
}

.col-header-add-edge:hover .add-col-inner {
  color: #2563eb;
}

.cell-add-edge {
  width: 76px !important;
  min-width: 76px !important;
  max-width: 76px !important;
  background: #fafbfc !important;
  border-left: 1px dashed #e2e8f0 !important;
  border-right: none !important;
  cursor: pointer;
}

.cell-add-edge:hover {
  background: #eff6ff !important;
}

</style>
