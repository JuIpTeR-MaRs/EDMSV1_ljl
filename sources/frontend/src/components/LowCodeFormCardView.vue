<template>
  <div class="lowcode-doc-container" v-loading="loading">
    <!-- ── Top Action Header ─────────────────────────────────── -->
    <div class="top-nav-bar">
      <div class="nav-left">
        <el-button :icon="Back" @click="goBack" size="small">
          {{ t('common.back', '返回') }}
        </el-button>
        <el-breadcrumb separator="/" class="nav-breadcrumb">
          <el-breadcrumb-item :to="{ path: '/' }">{{ t('library.title', '文档库') }}</el-breadcrumb-item>
          <el-breadcrumb-item>{{ t('lowcode.businessDoc', '业务申请单据') }}</el-breadcrumb-item>
          <el-breadcrumb-item>{{ docMeta?.title }}</el-breadcrumb-item>
        </el-breadcrumb>

        <!-- Real-time Auto-Save Status Badge (Word-like) -->
        <div v-if="isDraftEditable" class="save-status-indicator" :class="{ 'is-saving': isSaving, 'is-saved': !isSaving && saveHint }">
          <el-icon v-if="isSaving" class="is-loading"><Loading /></el-icon>
          <el-icon v-else-if="saveHint && !saveHint.includes('失败')"><CircleCheck /></el-icon>
          <el-icon v-else-if="saveHint && saveHint.includes('失败')"><CircleClose /></el-icon>
          <span>{{ saveHint || '实时自动保存已开启' }}</span>
        </div>
      </div>

      <div class="nav-right">
        <el-button v-if="isDraftEditable" type="primary" plain size="small" :icon="CircleCheck" :loading="isSaving" @click="saveNow(true)">
          立即保存
        </el-button>
        <el-button :icon="Printer" size="small" @click="printDoc">
          {{ t('lowcode.printDoc', '打印单据') }}
        </el-button>
        <el-button :icon="Refresh" size="small" @click="reloadDoc">
          {{ t('common.refresh', '刷新') }}
        </el-button>
      </div>
    </div>

    <!-- ── Main Form Paper Card ─────────────────────────────── -->
    <div class="form-sheet-wrapper">
      <div class="form-sheet-card" id="printable-form-card">
        <!-- Top Accent Bar -->
        <div class="sheet-accent-bar" :class="statusColorClass"></div>

        <!-- Sheet Header -->
        <div class="sheet-header">
          <div class="header-main">
            <div class="form-type-label">
              <el-icon><Tickets /></el-icon>
              <span>{{ t('lowcode.businessApplication', 'EDMS 结构化业务审批单据') }}</span>
            </div>
            <h1 class="sheet-title">{{ docMeta?.title }}</h1>
          </div>

          <div class="header-status-badge">
            <el-tag :type="statusTagType" effect="dark" class="doc-status-tag" size="large">
              <el-icon v-if="docMeta?.status === 'approved'"><CircleCheck /></el-icon>
              <el-icon v-else-if="docMeta?.status === 'rejected'"><CircleClose /></el-icon>
              <el-icon v-else-if="docMeta?.status === 'in_approval'"><Loading /></el-icon>
              <el-icon v-else><Document /></el-icon>
              <span style="margin-left: 4px;">{{ statusLabel }}</span>
            </el-tag>
          </div>
        </div>

        <!-- Meta info box -->
        <div class="sheet-meta-grid">
          <div class="meta-item">
            <span class="meta-label">单据编号：</span>
            <code class="meta-code">{{ docMeta?.doc_number || '-' }}</code>
          </div>
          <div class="meta-item">
            <span class="meta-label">填报人员：</span>
            <span class="meta-value">{{ docMeta?.owner_name || '-' }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">所属部门：</span>
            <el-tag size="small" effect="plain" type="info">{{ docMeta?.owner_department || '未分配' }}</el-tag>
          </div>
          <div class="meta-item">
            <span class="meta-label">提交时间：</span>
            <span class="meta-value">{{ formatLocalDate(docMeta?.created_at) }}</span>
          </div>
        </div>

        <el-divider style="margin: 20px 0;" />

        <!-- ── Form Fields Content Area ────────────────────────── -->
        <div class="sheet-body">
          <el-form label-position="top" class="card-form-grid">
            <el-row :gutter="24">
              <el-col 
                v-for="field in schemaFields" 
                :key="field.id"
                :span="['textarea', 'divider', 'alert', 'attachment', 'daterange', 'timerange'].includes(field.type) ? 24 : 12"
              >
                <!-- 1. Divider -->
                <div v-if="field.type === 'divider'" class="card-divider-section">
                  <span class="section-title">{{ field.label }}</span>
                </div>

                <!-- 2. Alert -->
                <el-alert 
                  v-else-if="field.type === 'alert'" 
                  :title="field.label" 
                  :type="field.alertType || 'info'" 
                  :closable="false" 
                  class="card-alert-box"
                />

                <!-- Regular Form Items -->
                <el-form-item 
                  v-else 
                  :label="field.label" 
                  :required="field.required" 
                  class="sheet-form-item"
                >
                  <!-- Edit mode (Draft & Owner) -->
                  <template v-if="isDraftEditable">
                    <!-- 1. Text -->
                    <el-input 
                      v-if="field.type === 'text'" 
                      v-model="editFormData[field.id]" 
                      :placeholder="field.placeholder || '请输入...'" 
                      clearable
                      @change="scheduleAutoSave(true)"
                    />

                    <!-- 2. Textarea -->
                    <el-input 
                      v-else-if="field.type === 'textarea'" 
                      v-model="editFormData[field.id]" 
                      type="textarea" 
                      :rows="3" 
                      :placeholder="field.placeholder || '请填写详细说明...'"
                      @change="scheduleAutoSave(true)"
                    />

                    <!-- 3. Pure Number / Quantity -->
                    <div v-else-if="field.type === 'number'" style="display: flex; align-items: center; gap: 8px; width: 100%;">
                      <el-input-number 
                        v-model="editFormData[field.id]" 
                        :min="field.min" 
                        :max="field.max"
                        :step="field.step || 1"
                        :precision="field.precision !== undefined ? field.precision : undefined"
                        :placeholder="field.placeholder || '请输入数值/数量'"
                        style="flex: 1;" 
                        @change="scheduleAutoSave(true)"
                      />
                      <el-tag v-if="field.unit" type="info" effect="plain">{{ field.unit }}</el-tag>
                    </div>

                    <!-- 3b. Amount / Currency -->
                    <div v-else-if="field.type === 'amount'" style="width: 100%;">
                      <div style="display: flex; align-items: center; gap: 8px; width: 100%;">
                        <span style="font-size: 15px; font-weight: bold; color: #67c23a;">￥</span>
                        <el-input-number 
                          v-model="editFormData[field.id]" 
                          :min="field.min !== undefined ? field.min : 0" 
                          :max="field.max"
                          :step="field.step || 10"
                          :precision="2"
                          :placeholder="field.placeholder || '0.00'"
                          style="flex: 1;" 
                          @change="scheduleAutoSave(true)"
                        />
                        <span style="font-size: 13px; color: var(--el-text-color-secondary);">{{ field.unit || '元' }}</span>
                      </div>
                    </div>

                    <!-- 4. Date (Single) -->
                    <el-date-picker 
                      v-else-if="field.type === 'date'" 
                      v-model="editFormData[field.id]" 
                      type="date" 
                      value-format="YYYY-MM-DD" 
                      :placeholder="field.placeholder || '选择日期'"
                      style="width: 100%;" 
                      @change="scheduleAutoSave(true)"
                    />

                    <!-- 5. Date Range -->
                    <el-date-picker 
                      v-else-if="field.type === 'daterange'" 
                      v-model="editFormData[field.id]" 
                      type="daterange" 
                      range-separator="至" 
                      start-placeholder="开始日期" 
                      end-placeholder="结束日期" 
                      value-format="YYYY-MM-DD" 
                      style="width: 100%;" 
                      @change="scheduleAutoSave(true)"
                    />

                    <!-- 6. Time (Single) -->
                    <el-date-picker 
                      v-else-if="field.type === 'time'" 
                      v-model="editFormData[field.id]" 
                      type="datetime" 
                      :placeholder="field.placeholder || '选择具体时间'"
                      format="YYYY-MM-DD HH:mm" 
                      value-format="YYYY-MM-DD HH:mm" 
                      style="width: 100%;" 
                      @change="scheduleAutoSave(true)"
                    />

                    <!-- 7. Time Range -->
                    <el-date-picker 
                      v-else-if="field.type === 'timerange'" 
                      v-model="editFormData[field.id]" 
                      type="datetimerange" 
                      range-separator="至" 
                      start-placeholder="开始时间" 
                      end-placeholder="结束时间" 
                      format="YYYY-MM-DD HH:mm" 
                      value-format="YYYY-MM-DD HH:mm" 
                      style="width: 100%;" 
                      @change="scheduleAutoSave(true)"
                    />

                    <!-- 8. Slider -->
                    <el-slider 
                      v-else-if="field.type === 'slider'" 
                      v-model="editFormData[field.id]" 
                      @change="scheduleAutoSave(true)"
                    />

                    <!-- 9. Switch -->
                    <el-switch 
                      v-else-if="field.type === 'switch'" 
                      v-model="editFormData[field.id]" 
                      :active-text="field.activeText || '是'" 
                      :inactive-text="field.inactiveText || '否'" 
                      @change="scheduleAutoSave(true)"
                    />

                    <!-- 10. Rate -->
                    <el-rate 
                      v-else-if="field.type === 'rate'" 
                      v-model="editFormData[field.id]" 
                      @change="scheduleAutoSave(true)"
                    />

                    <!-- 11. Select with Other support -->
                    <div v-else-if="field.type === 'select'" style="width: 100%;">
                      <el-select 
                        v-model="editFormData[field.id]" 
                        :filterable="field.allowOther"
                        :allow-create="field.allowOther"
                        default-first-option
                        :placeholder="field.allowOther ? '请选择或输入自定义选项...' : (field.placeholder || '请选择')"
                        style="width: 100%;"
                        @change="scheduleAutoSave(true)"
                      >
                        <el-option v-for="opt in (field.options || [])" :key="opt" :label="opt" :value="opt" />
                        <el-option v-if="field.allowOther" label="其他 (自定义填写)" value="__other__" />
                      </el-select>
                      <el-input 
                        v-if="field.allowOther && editFormData[field.id] === '__other__'" 
                        v-model="otherInputs[field.id]" 
                        :placeholder="field.otherPlaceholder || '请输入其他具体内容...'" 
                        size="small" 
                        style="margin-top: 6px;" 
                        @change="scheduleAutoSave(true)"
                      />
                    </div>

                    <!-- 12. Radio with Other support -->
                    <div v-else-if="field.type === 'radio'" style="width: 100%;">
                      <el-radio-group v-model="editFormData[field.id]" @change="scheduleAutoSave(true)">
                        <el-radio v-for="opt in (field.options || [])" :key="opt" :value="opt">{{ opt }}</el-radio>
                        <el-radio v-if="field.allowOther" value="__other__">其他 (可填写内容)</el-radio>
                      </el-radio-group>
                      <el-input 
                        v-if="field.allowOther && editFormData[field.id] === '__other__'" 
                        v-model="otherInputs[field.id]" 
                        :placeholder="field.otherPlaceholder || '请输入其他具体说明...'" 
                        size="small" 
                        style="margin-top: 6px;" 
                        @change="scheduleAutoSave(true)"
                      />
                    </div>

                    <!-- 13. Checkbox with Other support -->
                    <div v-else-if="field.type === 'checkbox'" style="width: 100%;">
                      <el-checkbox-group v-model="editFormData[field.id]" @change="scheduleAutoSave(true)">
                        <el-checkbox v-for="opt in (field.options || [])" :key="opt" :value="opt">{{ opt }}</el-checkbox>
                        <el-checkbox v-if="field.allowOther" value="__other__">其他 (可填写内容)</el-checkbox>
                      </el-checkbox-group>
                      <el-input 
                        v-if="field.allowOther && Array.isArray(editFormData[field.id]) && editFormData[field.id].includes('__other__')" 
                        v-model="otherInputs[field.id]" 
                        :placeholder="field.otherPlaceholder || '请输入其他具体说明...'" 
                        size="small" 
                        style="margin-top: 6px;" 
                        @change="scheduleAutoSave(true)"
                      />
                    </div>

                    <!-- 14. NPS 0-10 Rating -->
                    <div v-else-if="field.type === 'nps'" style="width: 100%;">
                      <el-radio-group v-model="editFormData[field.id]" size="small" @change="scheduleAutoSave(true)">
                        <el-radio-button v-for="n in 11" :key="n-1" :value="n-1">{{ n-1 }}</el-radio-button>
                      </el-radio-group>
                      <div style="font-size: 12px; color: var(--el-text-color-secondary); margin-top: 4px;">
                        {{ Number(editFormData[field.id]) >= 9 ? '极力推荐 (9-10分)' : (Number(editFormData[field.id]) >= 7 ? '中立态度 (7-8分)' : (editFormData[field.id] !== undefined ? '贬损/不推荐 (0-6分)' : '0分 (极不推荐) ~ 10分 (极力推荐)')) }}
                      </div>
                    </div>

                    <!-- 15. Phone -->
                    <el-input 
                      v-else-if="field.type === 'phone'"
                      v-model="editFormData[field.id]" 
                      :placeholder="field.placeholder || '请输入联系电话 (如 13800138000)...'" 
                      :prefix-icon="Iphone" 
                      clearable 
                      @change="scheduleAutoSave(true)"
                    />

                    <!-- 16. Gender -->
                    <el-radio-group 
                      v-else-if="field.type === 'gender'"
                      v-model="editFormData[field.id]" 
                      @change="scheduleAutoSave(true)"
                    >
                      <el-radio-button value="男">👨 男</el-radio-button>
                      <el-radio-button value="女">👩 女</el-radio-button>
                      <el-radio-button value="保密">🤫 保密</el-radio-button>
                    </el-radio-group>

                    <!-- 17. Email -->
                    <el-input 
                      v-else-if="field.type === 'email'"
                      v-model="editFormData[field.id]" 
                      :placeholder="field.placeholder || '请输入电子邮箱 (如 user@company.com)...'" 
                      :prefix-icon="Message" 
                      clearable 
                      @change="scheduleAutoSave(true)"
                    />

                    <!-- 18. Dept Select -->
                    <el-select 
                      v-else-if="field.type === 'dept_select'"
                      v-model="editFormData[field.id]" 
                      placeholder="请选择部门" 
                      style="width: 100%;"
                      filterable
                      @change="scheduleAutoSave(true)"
                    >
                      <el-option v-for="d in deptOptions" :key="d.id" :label="d.name" :value="d.name" />
                    </el-select>

                    <!-- 19. User Select -->
                    <el-select 
                      v-else-if="field.type === 'user_select'"
                      v-model="editFormData[field.id]" 
                      placeholder="请选择成员" 
                      style="width: 100%;"
                      filterable
                      @change="scheduleAutoSave(true)"
                    >
                      <el-option v-for="u in usersList" :key="u.id" :label="`${u.display_name} (${u.department_name || '未分配'})`" :value="u.display_name" />
                    </el-select>
                  </template>

                  <!-- Display / Read-only mode (For All Viewers & Approvers) -->
                  <template v-else>
                    <div class="display-value-box">
                      <!-- 1. Text & Textarea -->
                      <div v-if="field.type === 'text'" class="val-text">
                        {{ getVal(field.id) || '—' }}
                      </div>
                      <div v-else-if="field.type === 'textarea'" class="val-textarea">
                        {{ getVal(field.id) || '—' }}
                      </div>

                      <!-- 2. Pure Number / Quantity -->
                      <div v-else-if="field.type === 'number'" class="val-text" style="font-weight: 600; font-size: 15px; color: var(--el-text-color-primary);">
                        <span>{{ getVal(field.id) !== undefined && getVal(field.id) !== null && getVal(field.id) !== '' ? getVal(field.id) : '—' }}</span>
                        <span v-if="field.unit && getVal(field.id) !== undefined && getVal(field.id) !== null && getVal(field.id) !== ''" style="font-size: 13px; font-weight: normal; margin-left: 4px; color: var(--el-text-color-secondary);">{{ field.unit }}</span>
                      </div>

                      <!-- 2b. Currency Amount -->
                      <div v-else-if="field.type === 'amount'" class="val-number">
                        <span class="currency-symbol">¥</span>
                        <strong>{{ formatNumber(getVal(field.id)) }}</strong>
                        <span v-if="field.unit" style="font-size: 13px; font-weight: normal; margin-left: 3px; color: var(--el-text-color-secondary);">{{ field.unit }}</span>
                      </div>

                      <!-- 3. Date & Date Range -->
                      <div v-else-if="field.type === 'date'" class="val-badge date-badge">
                        <el-icon><Calendar /></el-icon>
                        <span>{{ getVal(field.id) || '—' }}</span>
                      </div>
                      <div v-else-if="field.type === 'daterange'" class="val-badge date-badge">
                        <el-icon><Calendar /></el-icon>
                        <span v-if="Array.isArray(getVal(field.id)) && getVal(field.id).length >= 2">
                          {{ getVal(field.id)[0] }} <span class="badge-sep">至</span> {{ getVal(field.id)[1] }}
                        </span>
                        <span v-else>—</span>
                      </div>

                      <!-- 4. Time & Time Range -->
                      <div v-else-if="field.type === 'time'" class="val-badge time-badge">
                        <el-icon><Timer /></el-icon>
                        <span>{{ getVal(field.id) || '—' }}</span>
                      </div>
                      <div v-else-if="field.type === 'timerange'" class="val-badge time-badge">
                        <el-icon><Timer /></el-icon>
                        <span v-if="Array.isArray(getVal(field.id)) && getVal(field.id).length >= 2">
                          {{ getVal(field.id)[0] }} <span class="badge-sep">至</span> {{ getVal(field.id)[1] }}
                        </span>
                        <span v-else>—</span>
                      </div>

                      <!-- 5. Slider Progress -->
                      <div v-else-if="field.type === 'slider'" class="val-slider-box">
                        <el-progress 
                          :percentage="Number(getVal(field.id)) || 0" 
                          :color="[
                            { color: '#f56c6c', percentage: 20 },
                            { color: '#e6a23c', percentage: 40 },
                            { color: '#5cb87a', percentage: 60 },
                            { color: '#1989fa', percentage: 80 },
                            { color: '#10b981', percentage: 100 },
                          ]"
                          style="width: 220px;"
                        />
                      </div>

                      <!-- 6. Switch -->
                      <div v-else-if="field.type === 'switch'">
                        <el-tag :type="getVal(field.id) ? 'success' : 'info'" size="small" effect="light">
                          {{ getVal(field.id) ? (field.activeText || '是 (开启)') : (field.inactiveText || '否 (关闭)') }}
                        </el-tag>
                      </div>

                      <!-- 7. Rate Stars -->
                      <div v-else-if="field.type === 'rate'" class="val-rate-box">
                        <el-rate :model-value="Number(getVal(field.id)) || 0" disabled show-score text-color="#ff9900" />
                      </div>

                      <!-- 8. Select, Radio, Checkbox -->
                      <div v-else-if="field.type === 'select' || field.type === 'radio'">
                        <el-tag v-if="getVal(field.id)" type="success" effect="light" class="choice-tag">
                          {{ getVal(field.id) }}
                        </el-tag>
                        <span v-else class="text-muted">—</span>
                      </div>
                      <div v-else-if="field.type === 'checkbox'" class="checkbox-tags-list">
                        <template v-if="Array.isArray(getVal(field.id)) && getVal(field.id).length > 0">
                          <el-tag v-for="item in getVal(field.id)" :key="item" type="info" size="small" class="choice-tag">
                            {{ item }}
                          </el-tag>
                        </template>
                        <span v-else class="text-muted">—</span>
                      </div>

                      <!-- 9. NPS 0-10 Rating -->
                      <div v-else-if="field.type === 'nps'" class="val-nps-box">
                        <el-tag :type="Number(getVal(field.id)) >= 9 ? 'success' : (Number(getVal(field.id)) >= 7 ? 'warning' : 'danger')" size="default" effect="dark">
                          {{ getVal(field.id) !== undefined ? getVal(field.id) : '—' }} 分
                        </el-tag>
                        <span class="nps-level-hint">
                          {{ Number(getVal(field.id)) >= 9 ? '极力推荐 (9-10分)' : (Number(getVal(field.id)) >= 7 ? '中立态度 (7-8分)' : '贬损/不推荐 (0-6分)') }}
                        </span>
                      </div>

                      <!-- 10. Ranking Sort -->
                      <div v-else-if="field.type === 'ranking'" class="val-ranking-list">
                        <div v-for="(item, rIdx) in (getVal(field.id) || [])" :key="item" class="rank-card-item">
                          <span class="rank-idx-pill">{{ Number(rIdx) + 1 }}</span>
                          <span class="rank-item-name">{{ item }}</span>
                        </div>
                      </div>

                      <!-- 11. Phone & Email & Gender -->
                      <div v-else-if="field.type === 'phone'" class="val-badge phone-badge">
                        <el-icon><Iphone /></el-icon>
                        <span>{{ getVal(field.id) || '—' }}</span>
                      </div>
                      <div v-else-if="field.type === 'gender'">
                        <el-tag :type="getVal(field.id) === '男' ? 'primary' : (getVal(field.id) === '女' ? 'danger' : 'info')" size="small">
                          {{ getVal(field.id) || '—' }}
                        </el-tag>
                      </div>
                      <div v-else-if="field.type === 'email'" class="val-badge email-badge">
                        <el-icon><Message /></el-icon>
                        <span>{{ getVal(field.id) || '—' }}</span>
                      </div>

                      <!-- 12. Dept & User Select -->
                      <div v-else-if="field.type === 'dept_select'">
                        <el-tag type="info" effect="plain" class="org-tag">
                          <el-icon><Folder /></el-icon>
                          <span>{{ getVal(field.id) || '—' }}</span>
                        </el-tag>
                      </div>
                      <div v-else-if="field.type === 'user_select'">
                        <el-tag type="primary" effect="plain" class="org-tag">
                          <el-icon><User /></el-icon>
                          <span>{{ getVal(field.id) || '—' }}</span>
                        </el-tag>
                      </div>

                      <!-- 13. Hand-written Electronic Signature -->
                      <div v-else-if="field.type === 'signature'" class="val-signature-wrap">
                        <div v-if="getVal(field.id)" class="sig-seal-box">
                          <img :src="getVal(field.id)" alt="手写电子签名" class="display-sig-img" />
                          <span class="sig-verified-tag">✓ 已在线签署印证</span>
                        </div>
                        <span v-else class="text-muted">（未签名）</span>
                      </div>

                      <!-- 14. Image Gallery Grid -->
                      <div v-else-if="field.type === 'image_upload'" class="val-images-container">
                        <div v-if="Array.isArray(getVal(field.id)) && getVal(field.id).length > 0" class="image-gallery-grid">
                          <a 
                            v-for="(img, imgIdx) in getVal(field.id)" 
                            :key="imgIdx" 
                            :href="img.url" 
                            target="_blank" 
                            class="gallery-item-card"
                            :title="`点击查看大图: ${img.name}`"
                          >
                            <img :src="img.url" :alt="img.name" class="gallery-thumb" />
                            <div class="gallery-name">{{ img.name }}</div>
                          </a>
                        </div>
                        <div v-else class="no-attachment-tip">
                          <el-icon><InfoFilled /></el-icon>
                          <span>未上传图片凭证</span>
                        </div>
                      </div>

                      <!-- 15. Subform Dynamic Table -->
                      <div v-else-if="field.type === 'subform'" class="val-subform-wrapper">
                        <el-table :data="getVal(field.id) || []" border size="small" style="width: 100%;">
                          <el-table-column type="index" label="序号" width="50" align="center" />
                          <el-table-column 
                            v-for="col in (field.columns || [])" 
                            :key="col.id" 
                            :label="col.label"
                          >
                            <template #default="{ row }">
                              <span v-if="col.type === 'number'" style="font-weight: 600;">
                                {{ formatNumber(row[col.id]) }}
                              </span>
                              <span v-else>{{ row[col.id] || '—' }}</span>
                            </template>
                          </el-table-column>
                        </el-table>
                      </div>

                      <!-- 16. Attachment Files List with Direct Download -->
                      <div v-else-if="field.type === 'attachment'" class="attachment-display-container">
                        <div v-if="Array.isArray(getVal(field.id)) && getVal(field.id).length > 0" class="attachment-cards-grid">
                          <a 
                            v-for="(file, fIdx) in getVal(field.id)" 
                            :key="fIdx" 
                            :href="file.url" 
                            target="_blank" 
                            class="attachment-download-card"
                            :title="`点击下载: ${file.name}`"
                          >
                            <div class="file-icon-box">
                              <el-icon><Paperclip /></el-icon>
                            </div>
                            <div class="file-info-text">
                              <div class="file-name">{{ file.name }}</div>
                              <div class="file-size">{{ formatFileSize(file.size) }} · 点击下载</div>
                            </div>
                            <el-icon class="download-arrow"><Download /></el-icon>
                          </a>
                        </div>
                        <div v-else class="no-attachment-tip">
                          <el-icon><InfoFilled /></el-icon>
                          <span>未上传附件凭证</span>
                        </div>
                      </div>

                      <!-- Fallback -->
                      <div v-else class="val-text">
                        {{ getVal(field.id) || '—' }}
                      </div>
                    </div>
                  </template>
                </el-form-item>
              </el-col>
            </el-row>
          </el-form>

          <!-- Draft owner actions: Save modifications -->
          <div v-if="isDraftEditable" class="draft-edit-toolbar">
            <el-button type="primary" :icon="Check" :loading="isSaving" @click="saveNow(true)">
              {{ t('common.save', '立即手动保存') }}
            </el-button>
            <span class="auto-save-text-hint">
              <el-icon><InfoFilled /></el-icon>
              系统已开启实时自动保存，您的每一次选择与输入都会自动同步至云端。
            </span>
          </div>
        </div>

        <el-divider style="margin: 28px 0 20px;" />

        <!-- ── Bottom Approval Workflow & Decision Section ──────── -->
        <div class="sheet-approval-section">
          <div class="section-header-bar">
            <div class="section-title-wrap">
              <el-icon class="section-icon"><Stamp /></el-icon>
              <h3 class="approval-heading">审批流程进度与流转记录</h3>
            </div>
            <span class="flow-mode-badge" v-if="approvalInfo">
              {{ approvalInfo.flow_type === 'parallel' ? '部门会签 (并行)' : '逐级流转审批 (串行)' }}
            </span>
          </div>

          <!-- 1. Approval Steps Stepper Timeline -->
          <div class="workflow-timeline-wrapper">
            <div class="timeline-step is-completed">
              <div class="step-icon-col">
                <div class="step-circle success-circle">
                  <el-icon><Check /></el-icon>
                </div>
                <div class="step-line"></div>
              </div>
              <div class="step-content-col">
                <div class="step-title-row">
                  <span class="step-name">1. 员工填单发起申请</span>
                  <span class="step-user">{{ docMeta?.owner_name }} ({{ docMeta?.owner_department || '申请人' }})</span>
                  <el-tag size="small" type="success">已提交</el-tag>
                  <span class="step-time">{{ formatLocalDate(docMeta?.created_at) }}</span>
                </div>
              </div>
            </div>

            <!-- Flow participant steps -->
            <template v-if="approvalInfo && approvalInfo.participants && approvalInfo.participants.length > 0">
              <div 
                v-for="(p, pIdx) in approvalInfo.participants" 
                :key="p.id" 
                class="timeline-step"
                :class="{ 
                  'is-completed': p.decision === 'approve', 
                  'is-rejected': p.decision === 'reject', 
                  'is-active': p.is_current_step 
                }"
              >
                <div class="step-icon-col">
                  <div 
                    class="step-circle"
                    :class="{
                      'success-circle': p.decision === 'approve',
                      'reject-circle': p.decision === 'reject',
                      'active-circle': p.is_current_step,
                      'pending-circle': !p.decision && !p.is_current_step
                    }"
                  >
                    <el-icon v-if="p.decision === 'approve'"><Check /></el-icon>
                    <el-icon v-else-if="p.decision === 'reject'"><Close /></el-icon>
                    <el-icon v-else-if="p.is_current_step"><Loading /></el-icon>
                    <span v-else>{{ Number(pIdx) + 2 }}</span>
                  </div>
                  <div class="step-line" v-if="Number(pIdx) < approvalInfo.participants.length - 1"></div>
                </div>

                <div class="step-content-col">
                  <div class="step-title-row">
                    <span class="step-name">节点 {{ Number(pIdx) + 2 }}: 负责人审核</span>
                    <span class="step-user">{{ p.user_name }} ({{ p.department_name || '审批人' }})</span>
                    
                    <el-tag v-if="p.decision === 'approve'" type="success" size="small">✔ 已同意</el-tag>
                    <el-tag v-else-if="p.decision === 'reject'" type="danger" size="small">✖ 已驳回</el-tag>
                    <el-tag v-else-if="p.is_current_step" type="warning" size="small" class="pulsing-tag">⌛ 待审核</el-tag>
                    <el-tag v-else type="info" size="small">排队中</el-tag>

                    <span v-if="p.decided_at" class="step-time">{{ formatLocalDate(p.decided_at) }}</span>
                  </div>

                  <!-- Reviewer comment -->
                  <div v-if="p.reason" class="step-comment-box" :class="{ 'reject-comment': p.decision === 'reject' }">
                    <span class="comment-label">审核意见：</span>
                    <span class="comment-text">{{ p.reason }}</span>
                  </div>
                </div>
              </div>
            </template>

            <!-- No active approval flow on draft -->
            <div v-else-if="docMeta?.status === 'draft'" class="no-flow-draft-card">
              <el-icon class="draft-info-icon"><InfoFilled /></el-icon>
              <div>
                <div class="draft-info-title">当前单据处于草稿状态，尚未发起审批流转</div>
                <div class="draft-info-desc">您可以核对上方填报信息，点击下方【🚀 发起审批流转】指定部门主管进行审核。</div>
              </div>
            </div>
          </div>

          <!-- 2. Active Approver Decision Action Panel (当当前用户需要审批时激活) -->
          <div v-if="canApprove" class="approver-decision-panel">
            <div class="decision-panel-header">
              <el-icon class="panel-icon"><EditPen /></el-icon>
              <span class="panel-title">您的审批待办：请审核上方表单内容并签署意见</span>
            </div>

            <div class="decision-reason-box">
              <el-input 
                v-model="decisionReason" 
                type="textarea" 
                :rows="2" 
                placeholder="请填写审批意见 / 审核评语（同意时可选填，驳回时为必填）..." 
                maxlength="512"
                show-word-limit
              />
              <div class="quick-reason-tags">
                <span class="quick-title">快捷评语：</span>
                <el-check-tag @click="decisionReason = '同意，符合规范，准予办理。'">同意，符合规范</el-check-tag>
                <el-check-tag @click="decisionReason = '已核实附件与申报信息无误，同意。'">已核实凭证无误</el-check-tag>
                <el-check-tag @click="decisionReason = '请补充完整业务说明与相关凭证后重新提交。'">请补充凭证后重提</el-check-tag>
              </div>
            </div>

            <div class="decision-action-buttons">
              <el-button 
                type="danger" 
                :icon="CircleClose" 
                :loading="submittingDecision" 
                @click="handleDecision('reject')"
                size="large"
              >
                ❌ 驳回申请
              </el-button>
              <el-button 
                type="success" 
                :icon="CircleCheck" 
                :loading="submittingDecision" 
                @click="handleDecision('approve')"
                size="large"
                class="approve-submit-btn"
              >
                ✅ 同意申请
              </el-button>
            </div>
          </div>

          <!-- 3. Owner Actions: Recall or Start Flow -->
          <div class="owner-actions-row">
            <!-- If in approval, owner can recall -->
            <el-popconfirm
              v-if="docMeta?.status === 'in_approval' && docMeta?.is_owner"
              title="确定要撤回当前单据的审批申请吗？撤回后单据将重置为草稿。"
              @confirm="handleRecall"
              confirm-button-text="确定撤回"
              cancel-button-text="取消"
            >
              <template #reference>
                <el-button type="warning" plain :icon="RefreshLeft" :loading="recalling">
                  撤回审批申请
                </el-button>
              </template>
            </el-popconfirm>

            <!-- If draft, owner can start approval -->
            <el-button 
              v-if="docMeta?.status === 'draft' && docMeta?.is_owner" 
              type="primary" 
              :icon="Promotion" 
              @click="openStartApprovalModal"
              size="large"
              class="start-approval-btn"
            >
              🚀 发起流转审批
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Launch Approval Modal for Drafts ─────────────────── -->
    <el-dialog
      v-model="startModalVisible"
      title="🚀 发起业务单据流转审批"
      width="520px"
      destroy-on-close
    >
      <el-form label-position="top">
        <el-form-item label="审批流转方式">
          <el-radio-group v-model="approvalType">
            <el-radio value="sequential">逐级流转审批 (串行)</el-radio>
            <el-radio value="parallel">部门全员会签 (并行)</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="选择流转审批人 (部门经理 / 主管)" required>
          <el-select
            v-model="selectedApprovers"
            multiple
            filterable
            placeholder="请选择审批人 (支持多选)"
            style="width: 100%;"
          >
            <el-option
              v-for="u in approverCandidates"
              :key="u.id"
              :label="`${u.display_name} (${u.department_name || '未分配'})`"
              :value="u.id"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="startModalVisible = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="startingFlow" @click="submitStartApproval">
          立即提交流转
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import api from '@/api/client';
import { useAuthStore } from '@/stores/auth';
import { ElMessage } from 'element-plus';
import {
  Back, Printer, Refresh, Tickets, CircleCheck, CircleClose, Loading, Document,
  Calendar, Timer, Folder, User, Paperclip, Download, InfoFilled, Check, Close,
  Stamp, EditPen, RefreshLeft, Promotion, Iphone, Message
} from '@element-plus/icons-vue';
import { formatLocalDate } from '@/utils/date';

const props = defineProps<{
  docId: string | number;
  initialDocData?: any;
}>();

const emit = defineEmits<{
  (e: 'updated', doc: any): void;
}>();

const { t } = useI18n();
const router = useRouter();
const auth = useAuthStore();

const loading = ref(false);
const isSaving = ref(false);
const saveHint = ref('');
const isInitialized = ref(false);
let saveDebounceTimer: any = null;

const submittingDecision = ref(false);
const recalling = ref(false);
const startingFlow = ref(false);

interface FlowParticipant {
  id: string | number;
  user_id?: number;
  user_name?: string;
  department_name?: string;
  decision?: 'approve' | 'reject' | null | string;
  is_current_step?: boolean;
  reason?: string;
  decided_at?: string;
}

interface ApprovalFlowInfo {
  flow_type?: string;
  status?: string;
  participants: FlowParticipant[];
  [key: string]: any;
}

const docMeta = ref<any>(null);
const schemaData = ref<any>(null);
const formData = ref<Record<string, any>>({});
const editFormData = ref<Record<string, any>>({});
const otherInputs = ref<Record<string, string>>({});
const approvalInfo = ref<ApprovalFlowInfo | null>(null);

// Decision State
const decisionReason = ref('');

// Start Approval Modal State
const startModalVisible = ref(false);
const approvalType = ref<'sequential' | 'parallel'>('sequential');
const selectedApprovers = ref<number[]>([]);
const usersList = ref<any[]>([]);
const deptOptions = ref<any[]>([]);

const schemaFields = computed(() => {
  return schemaData.value?.fields || [];
});

const isDraftEditable = computed(() => {
  return docMeta.value?.status === 'draft' && docMeta.value?.is_owner;
});

const canApprove = computed(() => {
  return !!docMeta.value?.can_approve && !!docMeta.value?.pending_participant_id;
});

const statusLabel = computed(() => {
  const s = docMeta.value?.status;
  if (s === 'approved') return '已审核通过';
  if (s === 'rejected') return '已驳回';
  if (s === 'in_approval') return '审批流转中';
  return '草稿待提交';
});

const statusTagType = computed(() => {
  const s = docMeta.value?.status;
  if (s === 'approved') return 'success';
  if (s === 'rejected') return 'danger';
  if (s === 'in_approval') return 'warning';
  return 'info';
});

const statusColorClass = computed(() => {
  const s = docMeta.value?.status;
  if (s === 'approved') return 'accent-approved';
  if (s === 'rejected') return 'accent-rejected';
  if (s === 'in_approval') return 'accent-in-approval';
  return 'accent-draft';
});

const approverCandidates = computed(() => {
  const myId = auth.user?.id;
  return usersList.value.filter((u: any) => u.id !== myId);
});

function getVal(fieldId: string) {
  return formData.value[fieldId];
}

function formatNumber(num: any) {
  if (num === null || num === undefined || num === '') return '0.00';
  const val = Number(num);
  return isNaN(val) ? String(num) : val.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatFileSize(bytes?: number) {
  if (!bytes) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

async function loadDocDetails() {
  loading.value = true;
  isInitialized.value = false;
  try {
    const { data } = await api.get(`/documents/${props.docId}`);
    docMeta.value = data;
    schemaData.value = data.template_schema || {};
    formData.value = data.form_data || {};
    
    // Parse form_data and reconstruct custom "Other" fill-ins
    const rawData = { ...formData.value };
    const parsedOthers: Record<string, string> = {};
    const fields = schemaData.value?.fields || [];
    
    fields.forEach((f: any) => {
      if (f.allowOther) {
        const val = rawData[f.id];
        if (typeof val === 'string' && (val.startsWith('其他: ') || val === '其他' || (f.options && !f.options.includes(val) && val !== ''))) {
          rawData[f.id] = '__other__';
          parsedOthers[f.id] = val.startsWith('其他: ') ? val.slice(4) : (val === '其他' ? '' : val);
        } else if (Array.isArray(val)) {
          const otherItem = val.find((v: string) => v.startsWith('其他: ') || v === '其他' || (f.options && !f.options.includes(v)));
          if (otherItem) {
            rawData[f.id] = val.map((v: string) => (v.startsWith('其他: ') || v === '其他' || (f.options && !f.options.includes(v))) ? '__other__' : v);
            parsedOthers[f.id] = otherItem.startsWith('其他: ') ? otherItem.slice(4) : (otherItem === '其他' ? '' : otherItem);
          }
        }
      }
    });

    editFormData.value = rawData;
    otherInputs.value = parsedOthers;
    approvalInfo.value = data.approval_info || null;
    emit('updated', data);
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || t('common.failed', '加载单据失败'));
  } finally {
    loading.value = false;
    setTimeout(() => {
      isInitialized.value = true;
    }, 100);
  }
}

async function loadUsers() {
  try {
    const { data } = await api.get('/users', { params: { size: 100 } });
    usersList.value = data.items || [];
    
    // Auto preset manager as approver if available
    const myId = auth.user?.id;
    const managers = usersList.value.filter((u: any) => u.id !== myId && (u.is_manager || u.is_super_admin));
    if (managers.length > 0 && selectedApprovers.value.length === 0) {
      selectedApprovers.value = [managers[0].id];
    }
  } catch (err) {
    console.error('Failed to fetch users list', err);
  }
}

async function loadDepts() {
  try {
    const { data } = await api.get('/users/departments');
    deptOptions.value = data || [];
  } catch (err) {
    console.error('Failed to load depts', err);
  }
}

// ── ⚡ 类似 Word 的实时自动保存引擎 (Debounced Real-Time Auto-Save) ──────
function scheduleAutoSave(immediate = false) {
  if (!isDraftEditable.value || !isInitialized.value) return;
  if (saveDebounceTimer) clearTimeout(saveDebounceTimer);
  isSaving.value = true;
  saveHint.value = '正在实时保存...';

  const delay = immediate ? 150 : 800;
  saveDebounceTimer = setTimeout(() => {
    saveNow(false);
  }, delay);
}

async function saveNow(showToast = false) {
  if (!isDraftEditable.value) return;
  isSaving.value = true;
  try {
    const cleanFormData: Record<string, any> = { ...editFormData.value };
    const fields = schemaFields.value || [];
    fields.forEach((f: any) => {
      if (f.allowOther) {
        const otherTxt = otherInputs.value[f.id]?.trim();
        const otherVal = otherTxt ? `其他: ${otherTxt}` : '其他';
        if (f.type === 'radio' || f.type === 'select') {
          if (cleanFormData[f.id] === '__other__') {
            cleanFormData[f.id] = otherVal;
          }
        } else if (f.type === 'checkbox' && Array.isArray(cleanFormData[f.id])) {
          cleanFormData[f.id] = cleanFormData[f.id].map((v: string) => v === '__other__' ? otherVal : v);
        }
      }
    });

    await api.put(`/documents/${props.docId}/form-data`, {
      form_data: cleanFormData
    });
    formData.value = { ...cleanFormData };
    const nowTime = new Date().toLocaleTimeString();
    saveHint.value = `已于 ${nowTime} 自动保存`;
    if (showToast) {
      ElMessage.success(`表单修改已保存 (${nowTime})`);
    }
  } catch (err: any) {
    console.error("Auto-save failed", err);
    saveHint.value = '自动保存失败，请检查网络';
    if (showToast) {
      ElMessage.error(err.response?.data?.error || '保存修改失败');
    }
  } finally {
    isSaving.value = false;
  }
}

// Deep watch form inputs for automatic continuous background persistence
watch(
  () => editFormData.value,
  () => {
    if (isInitialized.value && isDraftEditable.value) {
      scheduleAutoSave(false);
    }
  },
  { deep: true }
);

watch(
  () => otherInputs.value,
  () => {
    if (isInitialized.value && isDraftEditable.value) {
      scheduleAutoSave(false);
    }
  },
  { deep: true }
);

async function handleDecision(decision: 'approve' | 'reject') {
  if (decision === 'reject' && !decisionReason.value.trim()) {
    return ElMessage.warning('驳回申请时必须填写审核意见');
  }

  const participantId = docMeta.value?.pending_participant_id;
  if (!participantId) return;

  submittingDecision.value = true;
  try {
    await api.post(`/approvals/participants/${participantId}/decision`, {
      decision,
      reason: decisionReason.value.trim()
    });

    if (decision === 'approve') {
      ElMessage.success('🎉 您已同意该申请！');
    } else {
      ElMessage.warning('已驳回该申请单');
    }
    decisionReason.value = '';
    await loadDocDetails();
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || '审批操作失败');
  } finally {
    submittingDecision.value = false;
  }
}

async function handleRecall() {
  recalling.value = true;
  try {
    await api.post(`/documents/${props.docId}/recall`);
    ElMessage.success('单据已成功撤回为草稿状态');
    await loadDocDetails();
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || '撤回失败');
  } finally {
    recalling.value = false;
  }
}

function openStartApprovalModal() {
  startModalVisible.value = true;
}

async function submitStartApproval() {
  if (selectedApprovers.value.length === 0) {
    return ElMessage.warning('请至少选择一位审批人');
  }

  startingFlow.value = true;
  try {
    // Before starting flow, ensure latest form changes are saved
    await saveNow(false);

    await api.post(`/documents/${props.docId}/approvals`, {
      type: approvalType.value,
      approvers: selectedApprovers.value
    });

    ElMessage.success('🎉 单据已成功提交并进入流转审批！');
    startModalVisible.value = false;
    await loadDocDetails();
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || '发起审批失败');
  } finally {
    startingFlow.value = false;
  }
}

function printDoc() {
  window.print();
}

function reloadDoc() {
  loadDocDetails();
}

function goBack() {
  if (window.history.length > 1) {
    router.back();
  } else {
    router.push('/inbox');
  }
}

onMounted(() => {
  if (props.initialDocData) {
    docMeta.value = props.initialDocData;
    schemaData.value = props.initialDocData.template_schema || {};
    formData.value = props.initialDocData.form_data || {};
    editFormData.value = { ...formData.value };
    approvalInfo.value = props.initialDocData.approval_info || null;
  }
  loadDocDetails();
  loadUsers();
  loadDepts();
});

watch(() => props.docId, () => {
  loadDocDetails();
});
</script>

<style scoped>
.lowcode-doc-container {
  min-height: 100vh;
  background-color: #f1f5f9;
  padding: 24px;
}

/* ── Top Navigation Bar ──────────────────────────────────── */
.top-nav-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  background: #ffffff;
  padding: 12px 20px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.nav-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.nav-breadcrumb {
  font-size: 13px;
}

.save-status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 20px;
  background: #f8fafc;
  color: #64748b;
  border: 1px solid #e2e8f0;
  transition: all 0.3s ease;
  font-weight: 500;
}

.save-status-indicator.is-saving {
  background: #eff6ff;
  color: #2563eb;
  border-color: #bfdbfe;
}

.save-status-indicator.is-saved {
  background: #f0fdf4;
  color: #16a34a;
  border-color: #bbf7d0;
}

.nav-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* ── Form Sheet Card ─────────────────────────────────────── */
.form-sheet-wrapper {
  max-width: 900px;
  margin: 0 auto 40px;
}

.form-sheet-card {
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.08);
  border: 1px solid #e2e8f0;
  position: relative;
  overflow: hidden;
  padding: 36px 40px;
}

/* Top Accent Bar */
.sheet-accent-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 6px;
}

.accent-draft { background: #94a3b8; }
.accent-in-approval { background: linear-gradient(90deg, #f59e0b, #d97706); }
.accent-approved { background: linear-gradient(90deg, #10b981, #059669); }
.accent-rejected { background: linear-gradient(90deg, #ef4444, #dc2626); }

/* Header */
.sheet-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.form-type-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}

.sheet-title {
  font-size: 24px;
  font-weight: 800;
  color: #0f172a;
  margin: 0;
  line-height: 1.3;
}

.doc-status-tag {
  font-size: 13px;
  padding: 6px 14px;
  border-radius: 8px;
  font-weight: 700;
}

.pulsing-tag {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.6; }
  100% { opacity: 1; }
}

/* Meta info grid */
.sheet-meta-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px 18px;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-label {
  font-size: 12px;
  color: #64748b;
}

.meta-value {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}

.meta-code {
  font-family: monospace;
  font-weight: 700;
  color: #2563eb;
}

/* Form Body Grid */
.sheet-body {
  margin-top: 10px;
}

.card-divider-section {
  border-left: 4px solid #3b82f6;
  padding-left: 10px;
  margin: 16px 0 12px;
}

.section-title {
  font-size: 15px;
  font-weight: 700;
  color: #1e293b;
}

.card-alert-box {
  margin: 12px 0 18px;
  border-radius: 8px;
}

.sheet-form-item :deep(.el-form-item__label) {
  font-weight: 600;
  color: #475569;
  font-size: 13px;
  margin-bottom: 6px;
}

/* Display Read-Only Boxes */
.display-value-box {
  min-height: 40px;
  display: flex;
  align-items: center;
}

.val-text {
  font-size: 14px;
  color: #0f172a;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px 14px;
  width: 100%;
}

.val-textarea {
  font-size: 14px;
  color: #0f172a;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 14px;
  width: 100%;
  white-space: pre-wrap;
  line-height: 1.6;
}

.val-number {
  font-size: 16px;
  color: #0f766e;
  background: #f0fdfa;
  border: 1px solid #ccfbf1;
  border-radius: 8px;
  padding: 8px 14px;
  width: 100%;
  display: flex;
  align-items: center;
  gap: 6px;
}

.currency-symbol {
  font-size: 14px;
  color: #0d9488;
}

.val-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
}

.date-badge {
  background: #eff6ff;
  color: #2563eb;
  border: 1px solid #bfdbfe;
}

.time-badge {
  background: #f0fdf4;
  color: #16a34a;
  border: 1px solid #bbf7d0;
}

.badge-sep {
  color: #94a3b8;
  font-weight: 400;
  margin: 0 4px;
}

.val-slider-box, .val-rate-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px 14px;
  width: 100%;
}

.choice-tag, .org-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 600;
  border-radius: 6px;
}

.checkbox-tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.text-muted {
  color: #94a3b8;
}

/* Attachment download card */
.attachment-display-container {
  width: 100%;
}

.attachment-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.attachment-download-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 10px 14px;
  text-decoration: none;
  color: inherit;
  transition: all 0.2s ease;
}

.attachment-download-card:hover {
  background: #f1f5f9;
  border-color: #3b82f6;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.12);
}

.file-icon-box {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: #dbeafe;
  color: #2563eb;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.file-info-text {
  flex: 1;
  overflow: hidden;
}

.file-name {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  font-size: 11px;
  color: #64748b;
}

.download-arrow {
  color: #94a3b8;
  font-size: 16px;
}

.no-attachment-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #94a3b8;
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  padding: 8px 14px;
}

.draft-edit-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 20px;
  padding: 12px 16px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px dashed #cbd5e1;
}

.auto-save-text-hint {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #64748b;
}

/* ── Bottom Approval Workflow Section ────────────────────── */
.sheet-approval-section {
  margin-top: 10px;
}

.section-header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-icon {
  font-size: 20px;
  color: #d97706;
}

.approval-heading {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
}

.flow-mode-badge {
  font-size: 12px;
  color: #475569;
  background: #f1f5f9;
  border-radius: 6px;
  padding: 4px 10px;
}

/* Workflow Stepper Timeline */
.workflow-timeline-wrapper {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 24px;
}

.timeline-step {
  display: flex;
  gap: 16px;
  position: relative;
}

.step-icon-col {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.step-circle {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
  z-index: 2;
}

.success-circle { background: #10b981; color: #ffffff; }
.reject-circle { background: #ef4444; color: #ffffff; }
.active-circle { background: #f59e0b; color: #ffffff; box-shadow: 0 0 0 4px rgba(245, 158, 11, 0.2); }
.pending-circle { background: #e2e8f0; color: #94a3b8; }

.step-line {
  width: 2px;
  flex: 1;
  background: #cbd5e1;
  margin: 4px 0;
  min-height: 32px;
}

.step-content-col {
  flex: 1;
  padding-bottom: 24px;
}

.step-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.step-name {
  font-size: 14px;
  font-weight: 700;
  color: #1e293b;
}

.step-user {
  font-size: 13px;
  color: #475569;
}

.step-time {
  font-size: 12px;
  color: #94a3b8;
  margin-left: auto;
}

.step-comment-box {
  margin-top: 8px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 13px;
  color: #166534;
}

.reject-comment {
  background: #fef2f2;
  border-color: #fecaca;
  color: #991b1b;
}

.comment-label {
  font-weight: 700;
}

.no-flow-draft-card {
  display: flex;
  align-items: center;
  gap: 16px;
  background: #ffffff;
  border: 1px dashed #cbd5e1;
  border-radius: 10px;
  padding: 18px 20px;
}

.draft-info-icon {
  font-size: 32px;
  color: #3b82f6;
  flex-shrink: 0;
}

.draft-info-title {
  font-size: 14px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 2px;
}

.draft-info-desc {
  font-size: 12px;
  color: #64748b;
}

/* ── Approver Decision Action Panel ───────────────────────── */
.approver-decision-panel {
  background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
  border: 2px solid #f59e0b;
  border-radius: 12px;
  padding: 20px 24px;
  margin-top: 24px;
  box-shadow: 0 4px 16px rgba(245, 158, 11, 0.15);
}

.decision-panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}

.panel-icon {
  font-size: 20px;
  color: #d97706;
}

.panel-title {
  font-size: 15px;
  font-weight: 700;
  color: #92400e;
}

.decision-reason-box {
  margin-bottom: 16px;
}

.quick-reason-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.quick-title {
  font-size: 12px;
  color: #92400e;
  font-weight: 600;
}

.decision-action-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 16px;
}

.approve-submit-btn {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
  border: none !important;
  font-weight: 700;
  padding: 12px 28px;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

/* Owner actions */
.owner-actions-row {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}

.start-approval-btn {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
  border: none !important;
  font-weight: 700;
  padding: 12px 28px;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

/* ── New Component Card Display Styles ─────────────────────── */
.val-nps-box {
  display: flex;
  align-items: center;
  gap: 10px;
}
.nps-level-hint {
  font-size: 12px;
  color: #64748b;
  font-weight: 600;
}

.val-ranking-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}
.rank-card-item {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 5px 12px;
}
.rank-idx-pill {
  width: 20px;
  height: 20px;
  border-radius: 10px;
  background: var(--el-color-primary);
  color: #ffffff;
  font-size: 11px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
}
.rank-item-name {
  font-size: 13px;
  color: #1e293b;
  font-weight: 500;
}

.val-signature-wrap {
  width: 100%;
}
.sig-seal-box {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 6px 14px;
}
.sig-img, .display-sig-img {
  max-height: 60px;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  background: #ffffff;
}
.sig-verified-tag {
  font-size: 11px;
  color: #059669;
  font-weight: 600;
}

.val-images-container {
  width: 100%;
}
.image-gallery-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.gallery-item-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-decoration: none;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 4px;
  background: #ffffff;
  transition: transform 0.15s;
}
.gallery-item-card:hover {
  transform: translateY(-2px);
  border-color: var(--el-color-primary);
}
.gallery-thumb, .display-thumb-img {
  width: 76px;
  height: 76px;
  object-fit: cover;
  border-radius: 4px;
}
.gallery-name {
  max-width: 80px;
  font-size: 11px;
  color: #64748b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-top: 2px;
}

.val-subform-wrapper {
  width: 100%;
}
.subform-num {
  font-weight: 700;
  color: #0f172a;
}
</style>

<!-- ── Global Print Styles for Perfect A4 Output ──────────────── -->
<!-- ── Global Print Styles for Perfect Adaptive Output ──────────────── -->
<style>
@media print {
  @page {
    size: portrait;
    margin: 8mm 10mm;
  }

  *, *::before, *::after {
    box-sizing: border-box !important;
  }

  html, body {
    background: #ffffff !important;
    margin: 0 !important;
    padding: 0 !important;
    width: 100% !important;
    height: auto !important;
    overflow: visible !important;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
    font-size: 9pt !important;
    line-height: 1.3 !important;
    color: #0f172a !important;
  }

  /* 彻底隐藏全部侧边栏、顶部导航、操作按钮与无关修饰 */
  .edms-sidebar,
  .edms-header,
  .top-nav-bar,
  .approver-decision-panel,
  .owner-actions-row,
  .draft-edit-toolbar,
  .el-aside,
  .el-header,
  .el-dropdown,
  .collapse-btn,
  .notification-btn,
  .brand-logo,
  .nav-right,
  .nav-left,
  .sheet-accent-bar,
  .header-status-badge,
  .download-arrow {
    display: none !important;
    width: 0 !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
  }

  /* 铺满主容器，消除页面边距偏移与侧边栏占位 */
  .edms-layout-wrapper,
  .main-container,
  .edms-main,
  .editor-view-root,
  .lowcode-doc-container,
  .form-sheet-wrapper {
    display: block !important;
    position: static !important;
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
    background: #ffffff !important;
    box-shadow: none !important;
    border: none !important;
    overflow: visible !important;
  }

  .form-sheet-card {
    display: block !important;
    position: static !important;
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 auto !important;
    padding: 10px 14px !important;
    box-shadow: none !important;
    border: 1px solid #94a3b8 !important;
    border-radius: 4px !important;
    background: #ffffff !important;
    page-break-inside: avoid;
  }

  .sheet-header {
    margin-bottom: 8px !important;
  }

  .sheet-title {
    font-size: 15pt !important;
    color: #0f172a !important;
    text-align: center !important;
    margin: 2px 0 6px !important;
    font-weight: 800 !important;
  }

  .header-main {
    width: 100% !important;
    text-align: center !important;
  }

  .form-type-label {
    display: flex !important;
    justify-content: center !important;
    color: #64748b !important;
    font-size: 8pt !important;
    margin-bottom: 2px !important;
  }

  .sheet-meta-grid {
    border: 1px solid #cbd5e1 !important;
    background: #f8fafc !important;
    margin: 6px 0 10px !important;
    display: grid !important;
    grid-template-columns: repeat(4, 1fr) !important;
    padding: 6px 10px !important;
    gap: 6px !important;
  }

  .meta-label {
    font-size: 8pt !important;
    color: #64748b !important;
  }

  .meta-value, .meta-code {
    color: #1e293b !important;
    font-size: 8.5pt !important;
    font-weight: 600 !important;
  }

  .el-divider {
    margin: 8px 0 !important;
  }

  /* 消除 grid 负 margin 导致的右侧裁剪 */
  .card-form-grid .el-row {
    margin-left: 0 !important;
    margin-right: 0 !important;
  }

  .card-form-grid .el-col {
    padding-left: 4px !important;
    padding-right: 4px !important;
  }

  .sheet-form-item {
    margin-bottom: 6px !important;
  }

  .sheet-form-item :deep(.el-form-item__label) {
    font-size: 8.5pt !important;
    font-weight: 600 !important;
    color: #334155 !important;
    margin-bottom: 2px !important;
    line-height: 1.2 !important;
    padding: 0 !important;
  }

  .sheet-form-item :deep(.el-form-item__content) {
    line-height: 1.2 !important;
    min-height: auto !important;
  }

  .display-value-box {
    min-height: 24px !important;
  }

  .val-text, .val-textarea, .val-number, .val-badge, .val-slider-box, .val-rate-box {
    border: 1px solid #cbd5e1 !important;
    background: #ffffff !important;
    color: #0f172a !important;
    font-size: 8.5pt !important;
    padding: 3px 8px !important;
    border-radius: 4px !important;
    line-height: 1.3 !important;
  }

  .val-textarea {
    padding: 4px 8px !important;
  }

  .choice-tag, .org-tag {
    padding: 2px 6px !important;
    font-size: 8pt !important;
    height: auto !important;
    line-height: 1.2 !important;
  }

  .attachment-cards-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)) !important;
    gap: 6px !important;
  }

  .attachment-download-card {
    padding: 3px 8px !important;
    gap: 6px !important;
    border-radius: 4px !important;
  }

  .file-icon-box {
    width: 22px !important;
    height: 22px !important;
    font-size: 12px !important;
  }

  .file-name {
    font-size: 8pt !important;
  }

  .file-size {
    font-size: 7pt !important;
  }

  .sig-seal-box {
    border: 1px solid #000000 !important;
    background: #ffffff !important;
    padding: 4px 8px !important;
  }

  .sig-img, .display-sig-img {
    max-height: 40px !important;
  }

  .val-subform-wrapper :deep(.el-table) {
    font-size: 8pt !important;
  }

  .val-subform-wrapper :deep(.el-table th),
  .val-subform-wrapper :deep(.el-table td) {
    padding: 2px 4px !important;
  }

  /* 审批流程部分紧凑化 */
  .sheet-approval-section {
    margin-top: 6px !important;
  }

  .section-header-bar {
    margin-bottom: 6px !important;
  }

  .approval-heading {
    font-size: 9.5pt !important;
    font-weight: 700 !important;
    color: #0f172a !important;
  }

  .section-icon {
    font-size: 14px !important;
  }

  .flow-mode-badge {
    font-size: 7.5pt !important;
    padding: 2px 6px !important;
  }

  .workflow-timeline-wrapper {
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 4px !important;
    padding: 8px 12px !important;
  }

  .timeline-step {
    gap: 8px !important;
  }

  .step-circle {
    width: 18px !important;
    height: 18px !important;
    font-size: 8px !important;
  }

  .step-line {
    min-height: 12px !important;
    width: 1px !important;
    margin: 2px 0 !important;
  }

  .step-content-col {
    padding-bottom: 6px !important;
  }

  .step-title-row {
    gap: 6px !important;
  }

  .step-name {
    font-size: 8.5pt !important;
    font-weight: 600 !important;
  }

  .step-user {
    font-size: 8pt !important;
  }

  .step-time {
    font-size: 7.5pt !important;
  }

  .step-comment-box {
    margin-top: 3px !important;
    padding: 3px 8px !important;
    font-size: 8pt !important;
    border-radius: 4px !important;
  }

  .timeline-step {
    page-break-inside: avoid !important;
  }
}
</style>
