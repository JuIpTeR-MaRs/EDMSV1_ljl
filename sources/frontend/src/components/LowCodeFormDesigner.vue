<template>
  <el-dialog
    v-model="visible"
    :title="t('lowcode.designerTitle', '🎨 零代码 / 低代码智能表单设计器')"
    fullscreen
    destroy-on-close
    class="lowcode-designer-dialog"
    :show-close="true"
  >
    <div class="designer-container">
      <!-- ── Top Toolbar ────────────────────────────────────────── -->
      <div class="designer-toolbar">
        <div class="toolbar-left">
          <div class="template-badge">
            <el-icon class="badge-icon"><component :is="getIconComponent(currentTemplate?.icon)" /></el-icon>
            <span class="tmpl-name">{{ currentTemplate?.title || t('templates.untitled', '未命名模板') }}</span>
          </div>
          <el-tag type="success" size="small" effect="plain" class="schema-tag">
            {{ fields.length }} {{ t('lowcode.fieldsCount', '个组件字段') }}
          </el-tag>
        </div>

        <div class="toolbar-center">
          <el-radio-group v-model="activeTab" size="small">
            <el-radio-button value="design">
              <el-icon style="margin-right: 4px;"><EditPen /></el-icon>{{ t('lowcode.designMode', '可视化设计') }}
            </el-radio-button>
            <el-radio-button value="preview">
              <el-icon style="margin-right: 4px;"><View /></el-icon>{{ t('lowcode.previewMode', '填单实机预览') }}
            </el-radio-button>
          </el-radio-group>
        </div>

        <div class="toolbar-right">
          <el-button type="warning" plain :icon="MagicStick" @click="openAiModal" size="small">
            {{ t('lowcode.aiGenerate', '✨ AI 智能生成') }}
          </el-button>
          <el-button :icon="Refresh" size="small" @click="resetFields">
            {{ t('common.refresh', '重置') }}
          </el-button>
          <el-button type="primary" :icon="Check" :loading="saving" @click="saveDesignerSchema" size="small">
            {{ t('common.save', '保存表单定义') }}
          </el-button>
        </div>
      </div>

      <!-- ── 3-Column Designer Layout ──────────────────────────── -->
      <div class="designer-body" v-if="activeTab === 'design'">
        <!-- Column 1: Component Library Palette -->
        <div class="palette-panel">
          <div class="panel-header">
            <el-icon><Grid /></el-icon>
            <span>{{ t('lowcode.componentLibrary', '组件库 (点击/拖拽添加)') }}</span>
          </div>
          <div class="palette-scroll">
            <!-- 1. 基础输入 -->
            <div class="palette-group-title">{{ t('lowcode.basicInputs', '基础输入控件') }}</div>
            <div class="palette-grid">
              <div 
                v-for="comp in BASIC_COMPONENTS" 
                :key="comp.type" 
                class="palette-item"
                draggable="true"
                @dragstart="onPaletteDragStart($event, comp)"
                @click="addComponent(comp)"
              >
                <el-icon class="item-icon"><component :is="comp.icon" /></el-icon>
                <span class="item-label">{{ comp.label }}</span>
              </div>
            </div>

            <!-- 2. 选项与量表题型 -->
            <div class="palette-group-title" style="margin-top: 16px;">{{ t('lowcode.choiceInputs', '选项与量表题型') }}</div>
            <div class="palette-grid">
              <div 
                v-for="comp in CHOICE_COMPONENTS" 
                :key="comp.type" 
                class="palette-item"
                draggable="true"
                @dragstart="onPaletteDragStart($event, comp)"
                @click="addComponent(comp)"
              >
                <el-icon class="item-icon"><component :is="comp.icon" /></el-icon>
                <span class="item-label">{{ comp.label }}</span>
              </div>
            </div>

            <!-- 3. 高级凭证与明细表格 -->
            <div class="palette-group-title" style="margin-top: 16px;">{{ t('lowcode.advancedInputs', '高级凭证与明细表格') }}</div>
            <div class="palette-grid">
              <div 
                v-for="comp in ADVANCED_COMPONENTS" 
                :key="comp.type" 
                class="palette-item"
                draggable="true"
                @dragstart="onPaletteDragStart($event, comp)"
                @click="addComponent(comp)"
              >
                <el-icon class="item-icon"><component :is="comp.icon" /></el-icon>
                <span class="item-label">{{ comp.label }}</span>
              </div>
            </div>

            <!-- 4. 常用人员与业务预设 -->
            <div class="palette-group-title" style="margin-top: 16px;">{{ t('lowcode.presetInputs', '常用人员与业务预设') }}</div>
            <div class="palette-grid">
              <div 
                v-for="comp in PRESET_COMPONENTS" 
                :key="comp.type" 
                class="palette-item"
                draggable="true"
                @dragstart="onPaletteDragStart($event, comp)"
                @click="addComponent(comp)"
              >
                <el-icon class="item-icon"><component :is="comp.icon" /></el-icon>
                <span class="item-label">{{ comp.label }}</span>
              </div>
            </div>

            <!-- 5. 排版与辅助 -->
            <div class="palette-group-title" style="margin-top: 16px;">{{ t('lowcode.layoutInputs', '排版与辅助') }}</div>
            <div class="palette-grid">
              <div 
                v-for="comp in LAYOUT_COMPONENTS" 
                :key="comp.type" 
                class="palette-item"
                draggable="true"
                @dragstart="onPaletteDragStart($event, comp)"
                @click="addComponent(comp)"
              >
                <el-icon class="item-icon"><component :is="comp.icon" /></el-icon>
                <span class="item-label">{{ comp.label }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Column 2: Interactive Canvas -->
        <div 
          class="canvas-panel" 
          @dragover.prevent 
          @drop="onCanvasDrop"
        >
          <div class="canvas-header">
            <span class="canvas-title">{{ currentTemplate?.title || '表单设计画布' }}</span>
            <span class="canvas-sub">{{ t('lowcode.canvasTip', '可拖动调整顺序，点击选中进行右侧属性定制') }}</span>
          </div>

          <div class="canvas-content">
            <div v-if="fields.length === 0" class="canvas-empty" @click="addComponent(BASIC_COMPONENTS[0])">
              <el-icon class="empty-icon"><Plus /></el-icon>
              <div class="empty-title">{{ t('lowcode.emptyCanvas', '从左侧点击或拖入组件开始设计') }}</div>
              <div class="empty-desc">或者点击右上角【✨ AI 智能生成】一句话生成全套表单</div>
            </div>

            <!-- List of Drag-and-Drop Form Field Cards on Canvas -->
            <div 
              v-for="(field, idx) in fields" 
              :key="field.id"
              class="canvas-field-card"
              :class="{ 'is-selected': selectedFieldId === field.id, 'is-dragging': draggedFieldIdx === idx }"
              draggable="true"
              @dragstart="onFieldCardDragStart($event, idx)"
              @dragover.prevent="onFieldCardDragOver($event, idx)"
              @drop.stop="onFieldCardDrop($event, idx)"
              @click="selectedFieldId = field.id"
            >
              <div class="field-drag-handle" title="按住拖拽调整顺序">⠿</div>

              <div class="field-preview-body">
                <div class="field-header">
                  <span v-if="field.required" class="required-star">*</span>
                  <span class="field-label-text">{{ field.label }}</span>
                  <span class="field-type-tag">{{ getComponentTypeLabel(field.type) }}</span>
                  <span class="field-key-badge">#{{ field.id }}</span>
                </div>

                <!-- Preview Input Element -->
                <div class="field-control-stub">
                  <el-input v-if="field.type === 'text'" :placeholder="field.placeholder || '请输入文本...'" disabled />
                  <el-input v-else-if="field.type === 'textarea'" type="textarea" :rows="2" :placeholder="field.placeholder || '请输入详细说明...'" disabled />
                  
                  <!-- 纯数字 / 数量 -->
                  <div v-else-if="field.type === 'number'" style="display: flex; align-items: center; gap: 8px; width: 220px;">
                    <el-input-number :placeholder="field.placeholder || '请输入数值'" :precision="field.precision" disabled style="flex: 1;" />
                    <span v-if="field.unit" style="font-size: 13px; color: var(--el-text-color-secondary); font-weight: 500;">{{ field.unit }}</span>
                  </div>

                  <!-- 财务金额 -->
                  <div v-else-if="field.type === 'amount'" style="display: flex; align-items: center; gap: 6px; width: 220px;">
                    <span style="font-size: 14px; font-weight: bold; color: #67c23a;">￥</span>
                    <el-input-number :placeholder="field.placeholder || '0.00'" :precision="2" disabled style="flex: 1;" />
                    <span style="font-size: 13px; color: var(--el-text-color-secondary);">{{ field.unit || '元' }}</span>
                  </div>

                  <el-date-picker v-else-if="field.type === 'date'" type="date" :placeholder="field.placeholder || '选择日期'" disabled style="width: 200px;" />
                  <el-date-picker v-else-if="field.type === 'daterange'" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" disabled style="width: 280px;" />
                  <el-date-picker v-else-if="field.type === 'time'" type="datetime" placeholder="选择具体时间 (年月日 时:分)" format="YYYY-MM-DD HH:mm" disabled style="width: 220px;" />
                  <el-date-picker v-else-if="field.type === 'timerange'" type="datetimerange" range-separator="至" start-placeholder="开始时间" end-placeholder="结束时间" format="YYYY-MM-DD HH:mm" disabled style="width: 320px;" />
                  
                  <el-slider v-else-if="field.type === 'slider'" :model-value="field.defaultValue || 50" disabled style="width: 260px;" />
                  
                  <el-select v-else-if="field.type === 'select'" :placeholder="field.allowOther ? '请选择或输入自定义选项...' : (field.placeholder || '请选择...')" disabled style="width: 240px;">
                    <el-option v-for="opt in (field.options || [])" :key="opt" :label="opt" :value="opt" />
                    <el-option v-if="field.allowOther" label="其他 (自定义填写)" value="__other__" />
                  </el-select>
                  <div v-else-if="field.type === 'radio'" class="stub-options-wrap">
                    <el-radio-group disabled>
                      <el-radio v-for="opt in (field.options || ['选项1', '选项2'])" :key="opt" :value="opt">{{ opt }}</el-radio>
                      <el-radio v-if="field.allowOther" value="__other__">其他 (可填写内容)</el-radio>
                    </el-radio-group>
                  </div>
                  <div v-else-if="field.type === 'checkbox'" class="stub-options-wrap">
                    <el-checkbox-group disabled>
                      <el-checkbox v-for="opt in (field.options || ['选项A', '选项B'])" :key="opt" :value="opt">{{ opt }}</el-checkbox>
                      <el-checkbox v-if="field.allowOther" value="__other__">其他 (可填写内容)</el-checkbox>
                    </el-checkbox-group>
                  </div>

                  <el-switch v-else-if="field.type === 'switch'" :active-text="field.activeText || '是'" :inactive-text="field.inactiveText || '否'" disabled />
                  <el-rate v-else-if="field.type === 'rate'" :model-value="field.defaultValue || 4" disabled />

                  <!-- NPS 净推荐值量表 -->
                  <div v-else-if="field.type === 'nps'" class="stub-nps-wrap">
                    <div class="stub-nps-bar">
                      <span v-for="n in 11" :key="n-1" class="nps-block" :class="{'is-active': n === 10}">{{ n-1 }}</span>
                    </div>
                    <div class="nps-labels">
                      <span>{{ field.minLabel || '0 不太可能' }}</span>
                      <span>{{ field.maxLabel || '10 极有可能' }}</span>
                    </div>
                  </div>

                  <!-- 排序题 -->
                  <div v-else-if="field.type === 'ranking'" class="stub-rank-list">
                    <div v-for="(opt, oIdx) in (field.options || ['方案A', '方案B', '方案C'])" :key="oIdx" class="stub-rank-item">
                      <span class="rank-badge">{{ Number(oIdx) + 1 }}</span>
                      <span class="rank-text">{{ opt }}</span>
                      <el-icon class="rank-icon"><Rank /></el-icon>
                    </div>
                  </div>

                  <!-- 常用人员与业务预设 -->
                  <el-input v-else-if="field.type === 'phone'" :placeholder="field.placeholder || '请输入11位手机号码'" disabled style="width: 220px;" />
                  <el-radio-group v-else-if="field.type === 'gender'" disabled>
                    <el-radio value="男">👨 男</el-radio>
                    <el-radio value="女">👩 女</el-radio>
                    <el-radio value="保密">🔒 保密</el-radio>
                  </el-radio-group>
                  <el-input v-else-if="field.type === 'email'" :placeholder="field.placeholder || '请输入电子邮箱 (如 name@company.com)'" disabled style="width: 260px;" />

                  <!-- 组织选择器 -->
                  <el-select v-else-if="field.type === 'dept_select'" placeholder="选择所属部门 (自动关联)" disabled style="width: 240px;">
                    <el-option label="技术研发部" value="1" />
                  </el-select>
                  <el-select v-else-if="field.type === 'user_select'" placeholder="选择经办人 / 责任人" disabled style="width: 240px;">
                    <el-option label="张经理" value="1" />
                  </el-select>

                  <!-- 高级凭证与子表 -->
                  <div v-else-if="field.type === 'signature'" class="stub-signature-box">
                    <el-icon class="stub-sig-icon"><Stamp /></el-icon>
                    <span class="stub-sig-text">✍️ 手写电子签名区 (支持鼠标/触屏在线签字与印章留痕)</span>
                  </div>

                  <div v-else-if="field.type === 'image_upload'" class="stub-image-box">
                    <el-icon class="stub-img-icon"><Picture /></el-icon>
                    <span class="stub-img-text">📷 现场照片 / 质检与发票图片上传区 (点击选择或拍照)</span>
                  </div>

                  <div v-else-if="field.type === 'subform'" class="stub-subform-box">
                    <div class="subform-top">
                      <span class="subform-title">📋 {{ field.label }} (动态自增明细子表)</span>
                      <span class="subform-add-tag">+ 添加一行</span>
                    </div>
                    <div class="subform-cols-row">
                      <span 
                        v-for="col in (field.columns || [{label: '明细项名称'}, {label: '数量'}, {label: '单价/预算'}, {label: '备注'}])" 
                        :key="col.label" 
                        class="col-badge"
                      >
                        {{ col.label }}
                      </span>
                    </div>
                  </div>
                  
                  <div v-else-if="field.type === 'attachment'" class="stub-attachment-box">
                    <el-icon><Paperclip /></el-icon>
                    <span>点击或拖拽上传附件凭证 (支持 PDF, Word, Excel, 压缩包)</span>
                  </div>

                  <el-alert v-else-if="field.type === 'alert'" :title="field.label || '业务说明'" :type="field.alertType || 'info'" :closable="false" />
                  <el-divider v-else-if="field.type === 'divider'">{{ field.label }}</el-divider>
                </div>
              </div>

              <!-- Quick Operations on Field Card -->
              <div class="field-actions">
                <el-button circle size="small" :icon="Top" :disabled="idx === 0" @click.stop="moveField(idx, -1)" title="上移" />
                <el-button circle size="small" :icon="Bottom" :disabled="idx === fields.length - 1" @click.stop="moveField(idx, 1)" title="下移" />
                <el-button circle size="small" :icon="CopyDocument" @click.stop="duplicateField(idx)" title="复制" />
                <el-button circle size="small" :icon="Delete" type="danger" @click.stop="deleteField(idx)" title="删除" />
              </div>
            </div>
          </div>
        </div>

        <!-- Column 3: Property Inspector -->
        <div class="inspector-panel">
          <div class="panel-header">
            <el-icon><Setting /></el-icon>
            <span>{{ t('lowcode.inspectorTitle', '属性与校验配置') }}</span>
          </div>

          <div class="inspector-scroll" v-if="selectedField">
            <el-form label-position="top" size="small">
              <el-form-item :label="t('lowcode.fieldLabel', '字段标题')" required>
                <el-input v-model="selectedField.label" placeholder="例如：报销金额 / 请假起止日期" />
              </el-form-item>

              <el-form-item :label="t('lowcode.fieldId', '字段键名 (Key)')">
                <el-input v-model="selectedField.id" placeholder="例如：f_amount" />
              </el-form-item>

              <el-form-item :label="t('lowcode.placeholder', '提示占位符')" v-if="hasPlaceholder(selectedField.type)">
                <el-input v-model="selectedField.placeholder" placeholder="例如：请输入事项描述..." />
              </el-form-item>

              <el-form-item :label="t('lowcode.required', '必填项校验')" v-if="!['divider', 'alert'].includes(selectedField.type)">
                <el-switch v-model="selectedField.required" :active-text="t('common.yes', '必填')" :inactive-text="t('common.no', '非必填')" />
              </el-form-item>

              <!-- Number (纯数字) specific -->
              <template v-if="selectedField.type === 'number'">
                <el-form-item :label="t('lowcode.minVal', '最小值')">
                  <el-input-number v-model="selectedField.min" style="width: 100%;" />
                </el-form-item>
                <el-form-item :label="t('lowcode.maxVal', '最大值')">
                  <el-input-number v-model="selectedField.max" style="width: 100%;" />
                </el-form-item>
                <el-form-item label="增减步长 (Step)">
                  <el-input-number v-model="selectedField.step" :min="0.01" :step="1" style="width: 100%;" />
                </el-form-item>
                <el-form-item label="小数保留位数 (Precision)">
                  <el-input-number v-model="selectedField.precision" :min="0" :max="4" style="width: 100%;" />
                  <div style="font-size: 12px; color: var(--el-text-color-secondary); margin-top: 2px;">0 代表纯整数，1~4 代表小数位数</div>
                </el-form-item>
                <el-form-item label="数量单位 / 后缀 (Unit)">
                  <el-input v-model="selectedField.unit" placeholder="例如：个 / 件 / 天 / 小时 / 台 / %" />
                </el-form-item>
              </template>

              <!-- Amount (财务金额) specific -->
              <template v-if="selectedField.type === 'amount'">
                <el-form-item :label="t('lowcode.minVal', '最小金额')">
                  <el-input-number v-model="selectedField.min" :min="0" style="width: 100%;" />
                </el-form-item>
                <el-form-item :label="t('lowcode.maxVal', '最大金额')">
                  <el-input-number v-model="selectedField.max" style="width: 100%;" />
                </el-form-item>
                <el-form-item label="增减步长 (Step)">
                  <el-input-number v-model="selectedField.step" :min="1" :step="10" style="width: 100%;" />
                </el-form-item>
                <el-form-item label="币种单位">
                  <el-input v-model="selectedField.unit" placeholder="元" />
                </el-form-item>
              </template>

              <!-- Switch specific -->
              <template v-if="selectedField.type === 'switch'">
                <el-form-item label="开启状态文案">
                  <el-input v-model="selectedField.activeText" placeholder="是" />
                </el-form-item>
                <el-form-item label="关闭状态文案">
                  <el-input v-model="selectedField.inactiveText" placeholder="否" />
                </el-form-item>
              </template>

              <!-- Rate specific -->
              <template v-if="selectedField.type === 'rate'">
                <el-form-item label="默认打星评级">
                  <el-rate v-model="selectedField.defaultValue" />
                </el-form-item>
              </template>

              <!-- Slider specific -->
              <template v-if="selectedField.type === 'slider'">
                <el-form-item label="默认百分比进度">
                  <el-slider v-model="selectedField.defaultValue" />
                </el-form-item>
              </template>

              <!-- Options for Select / Radio / Checkbox -->
              <template v-if="['select', 'radio', 'checkbox'].includes(selectedField.type)">
                <el-form-item :label="t('lowcode.optionsConfig', '选项列表配置')">
                  <div class="options-list">
                    <div v-for="(_, oIdx) in (selectedField.options || [])" :key="oIdx" class="option-row">
                      <el-input v-model="selectedField.options[oIdx]" size="small" />
                      <el-button circle size="small" :icon="Delete" type="danger" @click="removeOption(Number(oIdx))" />
                    </div>
                    <el-button size="small" :icon="Plus" type="primary" plain @click="addOption" style="width: 100%; margin-top: 8px;">
                      {{ t('lowcode.addOption', '添加新选项') }}
                    </el-button>
                  </div>
                </el-form-item>

                <!-- 💡 允许填写“其他”自定义输入项 -->
                <el-form-item label="自定义‘其他’选项">
                  <el-switch 
                    v-model="selectedField.allowOther" 
                    active-text="允许填写‘其他’内容" 
                    inactive-text="仅限固定选项" 
                  />
                </el-form-item>

                <el-form-item label="‘其他’输入框占位提示" v-if="selectedField.allowOther">
                  <el-input 
                    v-model="selectedField.otherPlaceholder" 
                    placeholder="例如：请输入其他具体情况说明..." 
                    size="small" 
                  />
                </el-form-item>
              </template>

              <!-- Ranking specific -->
              <template v-if="selectedField.type === 'ranking'">
                <el-form-item label="待排序选项列表">
                  <div class="options-list">
                    <div v-for="(_, oIdx) in (selectedField.options || [])" :key="oIdx" class="option-row">
                      <el-input v-model="selectedField.options[oIdx]" size="small" />
                      <el-button circle size="small" :icon="Delete" type="danger" @click="removeOption(Number(oIdx))" />
                    </div>
                    <el-button size="small" :icon="Plus" type="primary" plain @click="addOption" style="width: 100%; margin-top: 8px;">
                      添加排序选项
                    </el-button>
                  </div>
                </el-form-item>
              </template>

              <!-- NPS specific -->
              <template v-if="selectedField.type === 'nps'">
                <el-form-item label="最低分文案 (0分)">
                  <el-input v-model="selectedField.minLabel" placeholder="0 不太可能" />
                </el-form-item>
                <el-form-item label="最高分文案 (10分)">
                  <el-input v-model="selectedField.maxLabel" placeholder="10 极有可能" />
                </el-form-item>
              </template>

              <!-- Subform specific -->
              <template v-if="selectedField.type === 'subform'">
                <el-form-item label="子表格列字段配置">
                  <div class="options-list">
                    <div v-for="(col, cIdx) in (selectedField.columns || [])" :key="cIdx" class="option-row" style="gap: 6px; margin-bottom: 6px;">
                      <el-input v-model="col.label" placeholder="列名 (如: 物品名称)" size="small" style="flex: 1;" />
                      <el-select v-model="col.type" size="small" style="width: 90px;">
                        <el-option label="文本" value="text" />
                        <el-option label="数字" value="number" />
                        <el-option label="日期" value="date" />
                      </el-select>
                      <el-button circle size="small" :icon="Delete" type="danger" @click="selectedField.columns.splice(Number(cIdx), 1)" />
                    </div>
                    <el-button size="small" :icon="Plus" type="primary" plain @click="addSubformColumn" style="width: 100%; margin-top: 6px;">
                      添加子表字段列
                    </el-button>
                  </div>
                </el-form-item>
              </template>

              <!-- Phone specific -->
              <template v-if="selectedField.type === 'phone'">
                <el-form-item label="手机号输入提示">
                  <el-input v-model="selectedField.placeholder" placeholder="请输入11位手机号码" />
                </el-form-item>
              </template>

              <!-- Email specific -->
              <template v-if="selectedField.type === 'email'">
                <el-form-item label="邮箱输入提示">
                  <el-input v-model="selectedField.placeholder" placeholder="请输入电子邮箱" />
                </el-form-item>
              </template>

              <!-- Alert Type -->
              <template v-if="selectedField.type === 'alert'">
                <el-form-item :label="t('lowcode.alertType', '提示样式')">
                  <el-select v-model="selectedField.alertType" style="width: 100%;">
                    <el-option label="信息提示 (Info)" value="info" />
                    <el-option label="成功提示 (Success)" value="success" />
                    <el-option label="警示提示 (Warning)" value="warning" />
                    <el-option label="紧急错误 (Error)" value="error" />
                  </el-select>
                </el-form-item>
              </template>
            </el-form>
          </div>

          <div class="inspector-empty" v-else>
            <el-icon class="empty-icon"><Pointer /></el-icon>
            <div>{{ t('lowcode.noFieldSelected', '请在中间画布点击选中一个组件进行属性配置') }}</div>
          </div>
        </div>
      </div>

      <!-- ── Live Preview Mode ──────────────────────────────────── -->
      <div class="preview-mode-container" v-else>
        <div class="preview-card">
          <div class="preview-header">
            <h2 class="preview-title">{{ currentTemplate?.title }}</h2>
            <p class="preview-sub">{{ currentTemplate?.description || '员工填报实机预览模式' }}</p>
          </div>

          <el-form :model="previewFormData" label-position="top" class="preview-form">
            <el-row :gutter="20">
              <el-col 
                v-for="field in fields" 
                :key="field.id" 
                :span="['textarea', 'divider', 'alert', 'attachment', 'daterange'].includes(field.type) ? 24 : 12"
              >
                <el-form-item :label="field.label" :required="field.required">
                  <el-input v-if="field.type === 'text'" v-model="previewFormData[field.id]" :placeholder="field.placeholder" />
                  <el-input v-else-if="field.type === 'textarea'" type="textarea" :rows="3" v-model="previewFormData[field.id]" :placeholder="field.placeholder" />
                  
                  <!-- 纯数字 / 数量 -->
                  <div v-else-if="field.type === 'number'" style="display: flex; align-items: center; gap: 8px; width: 100%;">
                    <el-input-number 
                      v-model="previewFormData[field.id]" 
                      :min="field.min" 
                      :max="field.max" 
                      :step="field.step || 1" 
                      :precision="field.precision !== undefined ? field.precision : undefined" 
                      :placeholder="field.placeholder || '请输入数值'" 
                      style="flex: 1;" 
                    />
                    <el-tag v-if="field.unit" type="info" effect="plain">{{ field.unit }}</el-tag>
                  </div>

                  <!-- 财务金额 -->
                  <div v-else-if="field.type === 'amount'" style="width: 100%;">
                    <div style="display: flex; align-items: center; gap: 8px; width: 100%;">
                      <span style="font-size: 15px; font-weight: bold; color: #67c23a;">￥</span>
                      <el-input-number 
                        v-model="previewFormData[field.id]" 
                        :min="field.min !== undefined ? field.min : 0" 
                        :max="field.max" 
                        :step="field.step || 10" 
                        :precision="2" 
                        :placeholder="field.placeholder || '0.00'" 
                        style="flex: 1;" 
                      />
                      <span style="font-size: 13px; color: var(--el-text-color-secondary);">{{ field.unit || '元' }}</span>
                    </div>
                    <div v-if="previewFormData[field.id]" style="font-size: 12px; color: #67c23a; margin-top: 4px;">
                      💰 人民币大写: {{ convertToChineseCapital(previewFormData[field.id]) }}
                    </div>
                  </div>
                  <el-date-picker v-else-if="field.type === 'date'" v-model="previewFormData[field.id]" type="date" value-format="YYYY-MM-DD" style="width: 100%;" />
                  <el-date-picker v-else-if="field.type === 'daterange'" v-model="previewFormData[field.id]" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" style="width: 100%;" />
                  <el-date-picker v-else-if="field.type === 'time'" v-model="previewFormData[field.id]" type="datetime" placeholder="选择具体时间 (年月日 时:分)" format="YYYY-MM-DD HH:mm" value-format="YYYY-MM-DD HH:mm" style="width: 100%;" />
                  <el-date-picker v-else-if="field.type === 'timerange'" v-model="previewFormData[field.id]" type="datetimerange" range-separator="至" start-placeholder="开始时间 (年月日 时:分)" end-placeholder="结束时间 (年月日 时:分)" format="YYYY-MM-DD HH:mm" value-format="YYYY-MM-DD HH:mm" style="width: 100%;" />
                  
                  <el-slider v-else-if="field.type === 'slider'" v-model="previewFormData[field.id]" />
                  
                  <!-- 11. Select with Other support -->
                  <div v-else-if="field.type === 'select'" style="width: 100%;">
                    <el-select 
                      v-model="previewFormData[field.id]" 
                      :filterable="field.allowOther" 
                      :allow-create="field.allowOther" 
                      default-first-option 
                      :placeholder="field.allowOther ? '请选择或输入自定义选项...' : (field.placeholder || '请选择')" 
                      style="width: 100%;"
                    >
                      <el-option v-for="opt in (field.options || [])" :key="opt" :label="opt" :value="opt" />
                      <el-option v-if="field.allowOther" label="其他 (自定义填写)" value="__other__" />
                    </el-select>
                    <el-input 
                      v-if="field.allowOther && previewFormData[field.id] === '__other__'" 
                      v-model="previewOtherInputs[field.id]" 
                      :placeholder="field.otherPlaceholder || '请输入其他具体内容...'" 
                      size="small" 
                      style="margin-top: 6px;" 
                    />
                  </div>

                  <!-- 12. Radio with Other support -->
                  <div v-else-if="field.type === 'radio'" style="width: 100%;">
                    <el-radio-group v-model="previewFormData[field.id]">
                      <el-radio v-for="opt in (field.options || [])" :key="opt" :value="opt">{{ opt }}</el-radio>
                      <el-radio v-if="field.allowOther" value="__other__">其他</el-radio>
                    </el-radio-group>
                    <el-input 
                      v-if="field.allowOther && previewFormData[field.id] === '__other__'" 
                      v-model="previewOtherInputs[field.id]" 
                      :placeholder="field.otherPlaceholder || '请输入其他具体说明...'" 
                      size="small" 
                      style="margin-top: 6px;" 
                    />
                  </div>

                  <!-- 13. Checkbox with Other support -->
                  <div v-else-if="field.type === 'checkbox'" style="width: 100%;">
                    <el-checkbox-group v-model="previewFormData[field.id]">
                      <el-checkbox v-for="opt in (field.options || [])" :key="opt" :value="opt">{{ opt }}</el-checkbox>
                      <el-checkbox v-if="field.allowOther" value="__other__">其他</el-checkbox>
                    </el-checkbox-group>
                    <el-input 
                      v-if="field.allowOther && Array.isArray(previewFormData[field.id]) && previewFormData[field.id].includes('__other__')" 
                      v-model="previewOtherInputs[field.id]" 
                      :placeholder="field.otherPlaceholder || '请输入其他具体说明...'" 
                      size="small" 
                      style="margin-top: 6px;" 
                    />
                  </div>

                  <!-- 14. NPS 0-10 Rating -->
                  <div v-else-if="field.type === 'nps'" style="width: 100%;">
                    <div class="preview-nps-bar">
                      <button 
                        type="button" 
                        v-for="n in 11" 
                        :key="n-1" 
                        class="nps-btn" 
                        :class="{'active': previewFormData[field.id] === (n-1)}"
                        @click="previewFormData[field.id] = (n-1)"
                      >
                        {{ n-1 }}
                      </button>
                    </div>
                    <div class="nps-labels">
                      <span>{{ field.minLabel || '0 不太可能' }}</span>
                      <span>{{ field.maxLabel || '10 极有可能' }}</span>
                    </div>
                  </div>

                  <!-- 15. Ranking Sort -->
                  <div v-else-if="field.type === 'ranking'" style="width: 100%;">
                    <div class="rank-preview-list">
                      <div v-for="(opt, oIdx) in (field.options || [])" :key="oIdx" class="rank-preview-item">
                        <span class="rank-badge">{{ Number(oIdx) + 1 }}</span>
                        <span>{{ opt }}</span>
                      </div>
                    </div>
                  </div>

                  <!-- 16. Phone -->
                  <el-input 
                    v-else-if="field.type === 'phone'" 
                    v-model="previewFormData[field.id]" 
                    :placeholder="field.placeholder || '请输入11位手机号码'" 
                    maxlength="11" 
                  >
                    <template #prefix><el-icon><Iphone /></el-icon></template>
                  </el-input>

                  <!-- 17. Gender -->
                  <el-radio-group v-else-if="field.type === 'gender'" v-model="previewFormData[field.id]">
                    <el-radio value="男">👨 男</el-radio>
                    <el-radio value="女">👩 女</el-radio>
                    <el-radio value="保密">🔒 保密</el-radio>
                  </el-radio-group>

                  <!-- 18. Email -->
                  <el-input 
                    v-else-if="field.type === 'email'" 
                    v-model="previewFormData[field.id]" 
                    :placeholder="field.placeholder || '请输入电子邮箱'" 
                  >
                    <template #prefix><el-icon><Message /></el-icon></template>
                  </el-input>

                  <!-- 19. Signature -->
                  <div v-else-if="field.type === 'signature'" class="preview-sig-stub">
                    <el-icon><Stamp /></el-icon>
                    <span>✍️ [手写在线电子签名：填报时开启签名板签字]</span>
                  </div>

                  <!-- 20. Image Upload -->
                  <div v-else-if="field.type === 'image_upload'" class="preview-img-stub">
                    <el-icon><Picture /></el-icon>
                    <span>📷 [现场照片 / 凭证图片上传：填报时支持选择图片与缩略图预览]</span>
                  </div>

                  <!-- 21. Dynamic Subform Table -->
                  <div v-else-if="field.type === 'subform'" class="preview-subform-stub">
                    <div class="subform-preview-head">
                      <strong>📋 {{ field.label }} (自增明细表)</strong>
                      <el-tag size="small" type="primary">+ 添加一行</el-tag>
                    </div>
                    <div class="subform-cols-desc">
                      包含列：{{ (field.columns || []).map((c: any) => c.label).join(' | ') }}
                    </div>
                  </div>

                  <el-switch v-else-if="field.type === 'switch'" v-model="previewFormData[field.id]" :active-text="field.activeText || '是'" :inactive-text="field.inactiveText || '否'" />
                  <el-rate v-else-if="field.type === 'rate'" v-model="previewFormData[field.id]" />

                  <el-select v-else-if="field.type === 'dept_select'" v-model="previewFormData[field.id]" style="width: 100%;">
                    <el-option label="技术研发部" value="研发部" />
                    <el-option label="统筹管理部" value="统筹管理部" />
                    <el-option label="财务部" value="财务部" />
                  </el-select>
                  <el-select v-else-if="field.type === 'user_select'" v-model="previewFormData[field.id]" style="width: 100%;">
                    <el-option label="张三 (主管)" value="张三" />
                    <el-option label="李四 (专员)" value="李四" />
                  </el-select>
                  
                  <div v-else-if="field.type === 'attachment'" class="stub-attachment-box">
                    <el-icon><Paperclip /></el-icon>
                    <span>📎 凭证附件上传演示框</span>
                  </div>

                  <el-alert v-else-if="field.type === 'alert'" :title="field.label" :type="field.alertType || 'info'" :closable="false" />
                  <el-divider v-else-if="field.type === 'divider'">{{ field.label }}</el-divider>
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>

          <div class="preview-footer">
            <el-button type="primary" size="large" @click="testSubmitPreview">
              {{ t('lowcode.testGenerate', '模拟生成标准文档') }}
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- ── AI Form Generator Modal ────────────────────────────── -->
    <el-dialog
      v-model="aiModalVisible"
      :title="t('lowcode.aiModalTitle', '✨ AI 智能一键生成表单模板')"
      width="540px"
      append-to-body
    >
      <div style="font-size: 13px; color: #64748b; margin-bottom: 12px;">
        {{ t('lowcode.aiTip', '输入您的业务单据需求（如：请假申请、固定资产采购、出差报销单），AI 将自动生成全套控件与排版规则：') }}
      </div>
      <el-input
        v-model="aiPromptInput"
        type="textarea"
        :rows="4"
        :placeholder="t('lowcode.aiPlaceholder', '例如：帮我设计一个服务器采购申请模板，包含设备配置、采购预算、预计使用部门、经办人、交付日期及采购原因。')"
      />
      <div class="ai-quick-tags">
        <span class="quick-label">快捷模板推荐:</span>
        <el-tag size="small" class="clickable-tag" @click="aiPromptInput = '行政办公用品采购申请单，包含物品清单、预算金额、领用人、部门、发票凭证附件及使用事由'">办公用品采购</el-tag>
        <el-tag size="small" class="clickable-tag" @click="aiPromptInput = '员工请假出差申请单，包含请假类型、起止日期区间、时间段范围、工作交接人、是否加急及事由说明'">请假与出差</el-tag>
        <el-tag size="small" class="clickable-tag" @click="aiPromptInput = '项目立项申报书，包含项目名称、负责人、协同部门、预算估算、完成进度滑块、优先级评星及立项附件'">项目立项申报</el-tag>
      </div>

      <template #footer>
        <el-button @click="aiModalVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="aiGenerating" :icon="MagicStick" @click="executeAiGenerate">
          {{ t('lowcode.generateNow', '立即智能生成') }}
        </el-button>
      </template>
    </el-dialog>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import api from "@/api/client";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  MagicStick, EditPen, View, Refresh, Check, Plus, Delete, Top, Bottom, CopyDocument,
  Grid, Setting, Pointer, Document, Tickets, Money, Calendar, Timer,
  List, CircleCheck, Folder, User, Warning, Operation, Memo, Management,
  Paperclip, Star, Switch as SwitchIcon, Histogram, Picture, Iphone, Message, Rank, Trophy, Stamp, Female,
  Odometer
} from "@element-plus/icons-vue";

const props = defineProps<{
  modelValue: boolean;
  templateData: any;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", val: boolean): void;
  (e: "saved", schema: any): void;
}>();

const { t } = useI18n();

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit("update:modelValue", val)
});

const currentTemplate = ref<any>(null);
const activeTab = ref<"design" | "preview">("design");
const fields = ref<any[]>([]);
const selectedFieldId = ref<string | null>(null);
const saving = ref(false);

const draggedFieldIdx = ref<number | null>(null);
const draggedPaletteComp = ref<any | null>(null);

const previewFormData = ref<Record<string, any>>({});
const previewOtherInputs = ref<Record<string, string>>({});

// ── Component Library Definitions ─────────────────────────────
const BASIC_COMPONENTS = [
  { type: "text", label: "单行文本 (Text)", icon: EditPen, placeholder: "请输入文本...", defaultLabel: "单行文本" },
  { type: "textarea", label: "多行文本 (Textarea)", icon: Memo, placeholder: "请输入详细说明...", defaultLabel: "详细描述" },
  { type: "number", label: "纯数字 / 数量 (Number)", icon: Odometer, placeholder: "请输入数值/数量...", min: 0, step: 1, precision: 0, defaultLabel: "数量 / 计数", unit: "" },
  { type: "amount", label: "财务金额 / 预算 (Amount)", icon: Money, placeholder: "0.00", min: 0, step: 10, precision: 2, defaultLabel: "金额 / 预算 (元)", unit: "元" },
  { type: "date", label: "单一日期 (Date)", icon: Calendar, placeholder: "选择日期", defaultLabel: "发生日期" },
  { type: "daterange", label: "📅 日期区间 (Date Range)", icon: Calendar, defaultLabel: "起止日期" },
  { type: "time", label: "🕒 具体时间 (带年月日时分)", icon: Timer, placeholder: "选择时间", defaultLabel: "具体时间" },
  { type: "timerange", label: "⏰ 起止时间 (带年月日时分)", icon: Timer, defaultLabel: "起止时间" },
  { type: "slider", label: "📊 进度滑块 (0~100%)", icon: Histogram, defaultLabel: "完成进度" }
];

const CHOICE_COMPONENTS = [
  { type: "select", label: "下拉单选 (Select)", icon: List, options: ["选项1", "选项2", "选项3"], allowOther: false, otherPlaceholder: "请输入自定义选项...", defaultLabel: "类型选择" },
  { type: "radio", label: "单选框组 (Radio)", icon: CircleCheck, options: ["普通", "加急", "特急"], allowOther: false, otherPlaceholder: "请输入其他具体说明...", defaultLabel: "紧急程度" },
  { type: "checkbox", label: "多选框组 (Checkbox)", icon: Operation, options: ["开发环境", "测试环境", "生产环境"], allowOther: false, otherPlaceholder: "请输入其他具体说明...", defaultLabel: "适用范围" },
  { type: "switch", label: "🔘 是否开关 (Switch)", icon: SwitchIcon, activeText: "是", inactiveText: "否", defaultLabel: "是否加急办理" },
  { type: "rate", label: "⭐ 优先级评级 (Rate)", icon: Star, defaultValue: 4, defaultLabel: "重要等级" },
  { type: "nps", label: "📊 NPS量表 (0~10分)", icon: Trophy, minLabel: "0 不太可能", maxLabel: "10 极有可能", defaultLabel: "推荐意愿 / 综合满意度" },
  { type: "ranking", label: "🔢 选项排序题 (Ranking)", icon: Rank, options: ["方案A", "方案B", "方案C"], defaultLabel: "需求优先级排序" }
];

const ADVANCED_COMPONENTS = [
  { type: "signature", label: "✍️ 手写电子签名 (Sign)", icon: Stamp, defaultLabel: "经办人手写电子签名" },
  { type: "image_upload", label: "🖼️ 图片/照片上传 (Image)", icon: Picture, defaultLabel: "现场照片 / 凭证图片" },
  { 
    type: "subform", 
    label: "➕ 自增明细表格 (Subform)", 
    icon: Grid, 
    columns: [
      { id: "c_name", label: "物品/明细名称", type: "text" },
      { id: "c_qty", label: "数量", type: "number" },
      { id: "c_price", label: "单价/金额(元)", type: "amount" },
      { id: "c_remark", label: "备注说明", type: "text" }
    ],
    defaultLabel: "采购/费用报销明细清单" 
  },
  { type: "attachment", label: "📎 凭证附件上传 (File)", icon: Paperclip, defaultLabel: "相关凭证附件" }
];

const PRESET_COMPONENTS = [
  { type: "phone", label: "📱 手机号码 (Phone)", icon: Iphone, placeholder: "请输入11位手机号码", defaultLabel: "联系电话" },
  { type: "gender", label: "⚥ 性别选择 (Gender)", icon: Female, defaultLabel: "性别" },
  { type: "email", label: "📧 电子邮箱 (Email)", icon: Message, placeholder: "请输入电子邮箱 (如 name@company.com)", defaultLabel: "电子邮箱" },
  { type: "dept_select", label: "🏢 部门选择器 (Dept)", icon: Folder, defaultLabel: "申请部门" },
  { type: "user_select", label: "👤 人员选择器 (User)", icon: User, defaultLabel: "责任人 / 经办人" }
];

const LAYOUT_COMPONENTS = [
  { type: "alert", label: "说明提示 (Alert)", icon: Warning, alertType: "info", defaultLabel: "填报说明与办理须知" },
  { type: "divider", label: "分组分割线 (Divider)", icon: Management, defaultLabel: "业务明细分组" }
];

const ICON_MAP: Record<string, any> = {
  Document, Tickets, Money, Calendar, Timer, List, CircleCheck, Folder, User, Warning, Operation, Memo, Management,
  Paperclip, Star, Switch: SwitchIcon, Histogram, Picture, Iphone, Message, Rank, Trophy, Stamp, Female, Odometer
};

function convertToChineseCapital(n: number | string | null | undefined): string {
  if (n === null || n === undefined || n === "") return "";
  const num = Number(n);
  if (isNaN(num)) return "";
  if (num === 0) return "零元整";
  
  const fraction = ["角", "分"];
  const digit = ["零", "壹", "贰", "叁", "肆", "伍", "陆", "柒", "捌", "玖"];
  const unit = [
    ["元", "万", "亿"],
    ["", "拾", "佰", "仟"]
  ];
  const head = num < 0 ? "负" : "";
  let absNum = Math.abs(num);
  
  let s = "";
  for (let i = 0; i < fraction.length; i++) {
    s += (digit[Math.floor(absNum * 10 * Math.pow(10, i)) % 10] + fraction[i]).replace(/零./, "");
  }
  s = s || "整";
  absNum = Math.floor(absNum);
  
  for (let i = 0; i < unit[0].length && absNum > 0; i++) {
    let p = "";
    for (let j = 0; j < unit[1].length && absNum > 0; j++) {
      p = digit[absNum % 10] + unit[1][j] + p;
      absNum = Math.floor(absNum / 10);
    }
    s = p.replace(/(零.)*零$/, "").replace(/^$/, "零") + unit[0][i] + s;
  }
  return head + s.replace(/(零.)*零元/, "元").replace(/(零.)+/g, "零").replace(/^整$/, "零元整");
}

function getIconComponent(name?: string) {
  if (!name) return Document;
  return ICON_MAP[name] || Document;
}

function getComponentTypeLabel(type: string) {
  const all = [
    ...BASIC_COMPONENTS, 
    ...CHOICE_COMPONENTS, 
    ...ADVANCED_COMPONENTS, 
    ...PRESET_COMPONENTS, 
    ...LAYOUT_COMPONENTS
  ];
  const found = all.find(c => c.type === type);
  return found ? found.label.split(" ")[0] : type;
}

function hasPlaceholder(type: string) {
  return ["text", "textarea", "number", "amount", "date", "time", "select", "phone", "email"].includes(type);
}

const selectedField = computed(() => {
  return fields.value.find(f => f.id === selectedFieldId.value) || null;
});

function addSubformColumn() {
  if (!selectedField.value) return;
  if (!selectedField.value.columns) selectedField.value.columns = [];
  const colIdx = selectedField.value.columns.length + 1;
  selectedField.value.columns.push({
    id: `col_${Date.now().toString(36)}`,
    label: `明细字段${colIdx}`,
    type: "text"
  });
}

// Watch template prop and load schema
watch(() => props.templateData, (val) => {
  if (val) {
    currentTemplate.value = val;
    if (val.template_schema && val.template_schema.fields) {
      fields.value = JSON.parse(JSON.stringify(val.template_schema.fields));
    } else {
      // Default initial schema
      fields.value = [
        { id: "f_title", label: "事项 / 项目名称", type: "text", placeholder: "请输入事项简述", required: true },
        { id: "f_dept", label: "申请部门", type: "dept_select", required: true },
        { id: "f_dates", label: "起止日期区间", type: "daterange", required: true },
        { id: "f_reason", label: "申请事由及详细说明", type: "textarea", placeholder: "请详细填写申请背景...", required: true },
        { id: "f_files", label: "相关附件凭证", type: "attachment", required: false }
      ];
    }
    selectedFieldId.value = fields.value.length > 0 ? fields.value[0].id : null;
    initPreviewData();
  }
}, { immediate: true });

function initPreviewData() {
  const map: Record<string, any> = {};
  fields.value.forEach(f => {
    if (f.type === "checkbox" || f.type === "daterange" || f.type === "timerange" || f.type === "attachment" || f.type === "image_upload" || f.type === "subform") {
      map[f.id] = [];
    } else if (f.type === "switch") {
      map[f.id] = false;
    } else if (f.type === "slider") {
      map[f.id] = f.defaultValue || 50;
    } else if (f.type === "rate") {
      map[f.id] = f.defaultValue || 4;
    } else if (f.type === "nps") {
      map[f.id] = 10;
    } else if (f.type === "gender") {
      map[f.id] = "男";
    } else if (f.defaultValue !== undefined) {
      map[f.id] = f.defaultValue;
    } else {
      map[f.id] = "";
    }
  });
  previewFormData.value = map;
}

// ── Drag & Drop Handlers on Canvas ────────────────────────────
function onPaletteDragStart(e: DragEvent, comp: any) {
  draggedPaletteComp.value = comp;
  if (e.dataTransfer) {
    e.dataTransfer.setData("text/plain", comp.type);
  }
}

function onCanvasDrop(_e: DragEvent) {
  if (draggedPaletteComp.value) {
    addComponent(draggedPaletteComp.value);
    draggedPaletteComp.value = null;
  }
}

function onFieldCardDragStart(e: DragEvent, idx: number) {
  draggedFieldIdx.value = idx;
  if (e.dataTransfer) {
    e.dataTransfer.setData("text/plain", String(idx));
  }
}

function onFieldCardDragOver(e: DragEvent, _idx: number) {
  e.preventDefault();
}

function onFieldCardDrop(_e: DragEvent, targetIdx: number) {
  if (draggedFieldIdx.value !== null && draggedFieldIdx.value !== targetIdx) {
    const item = fields.value.splice(draggedFieldIdx.value, 1)[0];
    fields.value.splice(targetIdx, 0, item);
  } else if (draggedPaletteComp.value) {
    const newField = createFieldFromComponent(draggedPaletteComp.value);
    fields.value.splice(targetIdx + 1, 0, newField);
    selectedFieldId.value = newField.id;
    draggedPaletteComp.value = null;
  }
  draggedFieldIdx.value = null;
}

function createFieldFromComponent(comp: any) {
  const uid = "f_" + Math.random().toString(36).substring(2, 8);
  return {
    id: uid,
    label: comp.defaultLabel || comp.label.split(" ")[0],
    type: comp.type,
    placeholder: comp.placeholder || "",
    required: false,
    options: comp.options ? [...comp.options] : (comp.type === 'gender' ? ['男', '女', '保密'] : (comp.type === 'ranking' ? ['方案A', '方案B', '方案C'] : undefined)),
    columns: comp.columns ? JSON.parse(JSON.stringify(comp.columns)) : (comp.type === 'subform' ? [
      { id: "col_1", label: "物品/明细名称", type: "text" },
      { id: "col_2", label: "数量", type: "number" },
      { id: "col_3", label: "金额(元)", type: "number" }
    ] : undefined),
    minLabel: comp.minLabel,
    maxLabel: comp.maxLabel,
    allowOther: comp.allowOther || false,
    otherPlaceholder: comp.otherPlaceholder || "",
    min: comp.min,
    activeText: comp.activeText,
    inactiveText: comp.inactiveText,
    defaultValue: comp.defaultValue,
    alertType: comp.alertType || "info"
  };
}

function addComponent(comp: any) {
  const newField = createFieldFromComponent(comp);
  fields.value.push(newField);
  selectedFieldId.value = newField.id;
  ElMessage.success(`已添加组件: ${newField.label}`);
}

function moveField(idx: number, step: number) {
  const target = idx + step;
  if (target < 0 || target >= fields.value.length) return;
  const item = fields.value.splice(idx, 1)[0];
  fields.value.splice(target, 0, item);
}

function duplicateField(idx: number) {
  const src = fields.value[idx];
  const copy = JSON.parse(JSON.stringify(src));
  copy.id = "f_" + Math.random().toString(36).substring(2, 8);
  copy.label = copy.label + " (副本)";
  fields.value.splice(idx + 1, 0, copy);
  selectedFieldId.value = copy.id;
}

function deleteField(idx: number) {
  fields.value.splice(idx, 1);
  if (fields.value.length > 0) {
    selectedFieldId.value = fields.value[Math.max(0, idx - 1)].id;
  } else {
    selectedFieldId.value = null;
  }
}

function addOption() {
  if (selectedField.value) {
    if (!selectedField.value.options) selectedField.value.options = [];
    selectedField.value.options.push(`新选项 ${selectedField.value.options.length + 1}`);
  }
}

function removeOption(idx: number) {
  if (selectedField.value && selectedField.value.options) {
    selectedField.value.options.splice(idx, 1);
  }
}

function resetFields() {
  ElMessageBox.confirm("确定要重置当前表单的所有控件吗？", "提示", { type: "warning" }).then(() => {
    fields.value = [];
    selectedFieldId.value = null;
  });
}

// ── Save Designer Schema ──────────────────────────────────────
async function saveDesignerSchema() {
  if (!currentTemplate.value?.id) return;
  saving.value = true;
  const schemaPayload = {
    form_type: "low_code",
    fields: fields.value,
    version: "1.1",
    updated_at: new Date().toISOString()
  };

  try {
    await api.patch(`/templates/admin/${currentTemplate.value.id}`, {
      template_schema: schemaPayload
    });
    ElMessage.success("表单设计已成功保存！");
    emit("saved", schemaPayload);
    visible.value = false;
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || t('common.failed'));
  } finally {
    saving.value = false;
  }
}

// ── AI Generator Modal Logic ──────────────────────────────────
const aiModalVisible = ref(false);
const aiPromptInput = ref("");
const aiGenerating = ref(false);

function openAiModal() {
  aiPromptInput.value = currentTemplate.value?.description || currentTemplate.value?.title || "";
  aiModalVisible.value = true;
}

async function executeAiGenerate() {
  if (!aiPromptInput.value.trim()) {
    return ElMessage.warning("请输入您的模板需求描述");
  }
  aiGenerating.value = true;
  try {
    const { data } = await api.post("/templates/ai-generate-schema", {
      prompt: aiPromptInput.value.trim()
    });
    if (data.schema && data.schema.fields) {
      fields.value = data.schema.fields;
      if (fields.value.length > 0) {
        selectedFieldId.value = fields.value[0].id;
      }
      initPreviewData();
      ElMessage.success("✨ AI 已成功为您生成结构化表单控件！");
      aiModalVisible.value = false;
    }
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || t('common.failed'));
  } finally {
    aiGenerating.value = false;
  }
}

function testSubmitPreview() {
  const mergedData: Record<string, any> = { ...previewFormData.value };
  fields.value.forEach(f => {
    if (f.allowOther) {
      const otherTxt = previewOtherInputs.value[f.id]?.trim();
      const otherVal = otherTxt ? `其他: ${otherTxt}` : '其他';
      if (f.type === 'radio' || f.type === 'select') {
        if (mergedData[f.id] === '__other__') {
          mergedData[f.id] = otherVal;
        }
      } else if (f.type === 'checkbox' && Array.isArray(mergedData[f.id])) {
        mergedData[f.id] = mergedData[f.id].map((v: string) => v === '__other__' ? otherVal : v);
      }
    }
  });

  ElMessageBox.alert(
    `<pre style="background:#f1f5f9; padding:12px; border-radius:6px; font-size:12px; max-height:400px; overflow-y:auto;">${JSON.stringify(mergedData, null, 2)}</pre>`,
    "表单提交流转数据预览",
    { dangerouslyUseHTMLString: true }
  );
}
</script>

<style>
/* ── Fullscreen fixed container overrides for lowcode designer ── */
.lowcode-designer-dialog.el-dialog {
  display: flex !important;
  flex-direction: column !important;
  height: 100vh !important;
  max-height: 100vh !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
}

.lowcode-designer-dialog .el-dialog__header {
  margin: 0 !important;
  padding: 10px 20px !important;
  border-bottom: 1px solid #e2e8f0 !important;
  background: #ffffff !important;
  flex-shrink: 0 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  height: 48px !important;
  box-sizing: border-box !important;
}

.lowcode-designer-dialog .el-dialog__title {
  font-size: 15px !important;
  font-weight: 700 !important;
  color: #0f172a !important;
}

.lowcode-designer-dialog .el-dialog__body {
  padding: 0 !important;
  flex: 1 !important;
  min-height: 0 !important;
  height: calc(100vh - 48px) !important;
  max-height: calc(100vh - 48px) !important;
  overflow: hidden !important;
  background: #f8fafc !important;
  display: flex !important;
  flex-direction: column !important;
  box-sizing: border-box !important;
}
</style>

<style scoped>
.designer-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  flex: 1;
  overflow: hidden;
}

/* ── Designer Top Toolbar ────────────────────────────────────── */
.designer-toolbar {
  height: 52px;
  min-height: 52px;
  max-height: 52px;
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  padding: 0 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);
  z-index: 10;
  flex-shrink: 0;
  box-sizing: border-box;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.template-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  font-size: 15px;
  color: #0f172a;
}

.badge-icon {
  font-size: 18px;
  color: var(--el-color-primary);
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* ── 3-Column Designer Body ──────────────────────────────────── */
.designer-body {
  flex: 1;
  min-height: 0;
  height: calc(100% - 52px);
  display: flex;
  overflow: hidden;
  position: relative;
}

/* ── Left Column: Palette ────────────────────────────────────── */
.palette-panel {
  width: 290px;
  min-width: 290px;
  max-width: 290px;
  height: 100%;
  min-height: 0;
  background: #ffffff;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  flex-shrink: 0;
}

.panel-header {
  padding: 12px 16px;
  border-bottom: 1px solid #f1f5f9;
  font-size: 13px;
  font-weight: 700;
  color: #334155;
  display: flex;
  align-items: center;
  gap: 8px;
  background: #fafafa;
  flex-shrink: 0;
  height: 44px;
  box-sizing: border-box;
}

.palette-scroll {
  padding: 16px;
  overflow-y: auto;
  overflow-x: hidden;
  flex: 1;
  min-height: 0;
  height: calc(100% - 44px);
  box-sizing: border-box;
}

.palette-scroll::-webkit-scrollbar {
  width: 6px;
}
.palette-scroll::-webkit-scrollbar-track {
  background: #f8fafc;
}
.palette-scroll::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}
.palette-scroll::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.palette-group-title {
  font-size: 12px;
  font-weight: 700;
  color: #94a3b8;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.palette-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 6px;
}

.palette-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  cursor: grab;
  font-size: 13px;
  color: #334155;
  transition: all 0.15s;
  user-select: none;
}

.palette-item:hover {
  background: #f0fdf4;
  border-color: var(--el-color-primary);
  color: var(--el-color-primary);
  transform: translateX(3px);
}

.palette-item .item-icon {
  font-size: 16px;
  color: #64748b;
}

.palette-item:hover .item-icon {
  color: var(--el-color-primary);
}

/* ── Middle Column: Canvas ───────────────────────────────────── */
.canvas-panel {
  flex: 1;
  min-width: 0;
  height: 100%;
  min-height: 0;
  background: #f1f5f9;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 24px 32px;
  box-sizing: border-box;
}

.canvas-panel::-webkit-scrollbar {
  width: 6px;
}
.canvas-panel::-webkit-scrollbar-track {
  background: #e2e8f0;
}
.canvas-panel::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}
.canvas-panel::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.canvas-header {
  margin-bottom: 16px;
  text-align: center;
}

.canvas-title {
  font-size: 18px;
  font-weight: 800;
  color: #0f172a;
  display: block;
}

.canvas-sub {
  font-size: 12px;
  color: #64748b;
}

.canvas-content {
  max-width: 760px;
  width: 100%;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-bottom: 60px;
}

.canvas-empty {
  background: #ffffff;
  border: 2px dashed #cbd5e1;
  border-radius: 12px;
  padding: 60px 24px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}

.canvas-empty:hover {
  border-color: var(--el-color-primary);
  background: #f0fdf4;
}

.empty-icon {
  font-size: 32px;
  color: #94a3b8;
  margin-bottom: 12px;
}

.empty-title {
  font-size: 15px;
  font-weight: 700;
  color: #334155;
  margin-bottom: 6px;
}

.empty-desc {
  font-size: 13px;
  color: #64748b;
}

.canvas-field-card {
  background: #ffffff;
  border: 2px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px 18px;
  display: flex;
  gap: 14px;
  align-items: flex-start;
  box-shadow: 0 1px 3px rgba(0,0,0,0.03);
  transition: all 0.2s ease;
  cursor: pointer;
  position: relative;
}

.canvas-field-card:hover {
  border-color: #94a3b8;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}

.canvas-field-card.is-selected {
  border-color: var(--el-color-primary);
  background: #fcfffd;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.15);
}

.canvas-field-card.is-dragging {
  opacity: 0.4;
  border: 2px dashed #94a3b8;
}

.field-drag-handle {
  cursor: grab;
  color: #94a3b8;
  font-size: 18px;
  line-height: 1;
  padding-top: 4px;
}

.field-preview-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field-header {
  display: flex;
  align-items: center;
  gap: 6px;
}

.required-star {
  color: #ef4444;
  font-weight: bold;
}

.field-label-text {
  font-weight: 700;
  font-size: 14px;
  color: #1e293b;
}

.field-type-tag {
  font-size: 11px;
  background: #f1f5f9;
  color: #64748b;
  padding: 2px 6px;
  border-radius: 4px;
}

.field-key-badge {
  font-size: 11px;
  color: #94a3b8;
  font-family: monospace;
}

.field-control-stub {
  pointer-events: none;
  opacity: 0.85;
}

.stub-attachment-box {
  border: 1px dashed #cbd5e1;
  background: #f8fafc;
  padding: 12px;
  border-radius: 8px;
  font-size: 12px;
  color: #64748b;
  display: flex;
  align-items: center;
  gap: 8px;
}

.field-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.canvas-field-card:hover .field-actions,
.canvas-field-card.is-selected .field-actions {
  opacity: 1;
}

/* ── Right Column: Inspector ─────────────────────────────────── */
.inspector-panel {
  width: 320px;
  min-width: 320px;
  max-width: 320px;
  height: 100%;
  min-height: 0;
  background: #ffffff;
  border-left: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  flex-shrink: 0;
}

.inspector-scroll {
  padding: 20px;
  overflow-y: auto;
  overflow-x: hidden;
  flex: 1;
  min-height: 0;
  height: calc(100% - 44px);
  box-sizing: border-box;
}

.inspector-scroll::-webkit-scrollbar {
  width: 6px;
}
.inspector-scroll::-webkit-scrollbar-track {
  background: #f8fafc;
}
.inspector-scroll::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}
.inspector-scroll::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.inspector-empty {
  padding: 60px 24px;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.inspector-empty .empty-icon {
  font-size: 28px;
  color: #cbd5e1;
}

.options-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.option-row {
  display: flex;
  gap: 6px;
  align-items: center;
}

/* ── Preview Mode ────────────────────────────────────────────── */
.preview-mode-container {
  flex: 1;
  overflow-y: auto;
  padding: 32px 24px;
  display: flex;
  justify-content: center;
  background: #f1f5f9;
}

.preview-card {
  max-width: 800px;
  width: 100%;
  background: #ffffff;
  border-radius: 16px;
  padding: 40px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.05);
  border: 1px solid #e2e8f0;
}

.preview-header {
  border-bottom: 2px solid var(--el-color-primary);
  padding-bottom: 16px;
  margin-bottom: 24px;
}

.preview-title {
  margin: 0 0 6px;
  font-size: 22px;
  color: #0f172a;
}

.preview-sub {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}

.preview-footer {
  margin-top: 32px;
  border-top: 1px solid #e2e8f0;
  padding-top: 24px;
  text-align: center;
}

.ai-quick-tags {
  margin-top: 12px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
}

.quick-label {
  font-size: 12px;
  color: #64748b;
}

.clickable-tag {
  cursor: pointer;
}

.clickable-tag:hover {
  background: var(--el-color-primary-light-9);
}

/* ── New Component Stubs & Preview Styles ──────────────────── */
.stub-nps-wrap {
  width: 100%;
}
.stub-nps-bar {
  display: flex;
  gap: 4px;
}
.nps-block {
  flex: 1;
  text-align: center;
  padding: 6px 0;
  background: #f1f5f9;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: #475569;
}
.nps-block.is-active {
  background: var(--el-color-primary);
  color: #ffffff;
}
.nps-labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #94a3b8;
  margin-top: 4px;
}

.preview-nps-bar {
  display: flex;
  gap: 4px;
  width: 100%;
}
.nps-btn {
  flex: 1;
  padding: 8px 0;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  border-radius: 6px;
  font-weight: 700;
  font-size: 13px;
  color: #334155;
  cursor: pointer;
  transition: all 0.2s;
}
.nps-btn:hover {
  border-color: var(--el-color-primary);
  color: var(--el-color-primary);
}
.nps-btn.active {
  background: var(--el-color-primary);
  border-color: var(--el-color-primary);
  color: #ffffff;
  box-shadow: 0 2px 6px rgba(0,0,0,0.1);
}

.stub-rank-list, .rank-preview-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}
.stub-rank-item, .rank-preview-item {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 13px;
}
.rank-badge {
  background: #e2e8f0;
  color: #334155;
  width: 20px;
  height: 20px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: bold;
}
.rank-text {
  flex: 1;
}
.rank-icon {
  color: #94a3b8;
}

.stub-signature-box, .stub-image-box, .preview-sig-stub, .preview-img-stub {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 16px;
  background: #f8fafc;
  border: 1.5px dashed #cbd5e1;
  border-radius: 8px;
  color: #64748b;
  font-size: 13px;
}

.stub-subform-box, .preview-subform-stub {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 14px;
  width: 100%;
}
.subform-top, .subform-preview-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.subform-title {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
}
.subform-add-tag {
  font-size: 11px;
  background: #dbeafe;
  color: #1d4ed8;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}
.subform-cols-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.col-badge {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  color: #475569;
}
</style>
