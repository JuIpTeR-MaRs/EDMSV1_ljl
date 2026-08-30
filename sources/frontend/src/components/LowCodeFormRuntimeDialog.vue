<template>
  <el-dialog
    v-model="visible"
    :title="templateData?.title || t('lowcode.fillFormTitle', '填写业务申请单据')"
    width="740px"
    class="custom-dialog lowcode-runtime-dialog"
    destroy-on-close
  >
    <div class="runtime-form-container" v-loading="submitting">
      <!-- ── Template Header Intro ───────────────────────────── -->
      <div class="form-banner">
        <div class="banner-icon">
          <el-icon><component :is="getIconComponent(templateData?.icon)" /></el-icon>
        </div>
        <div class="banner-text">
          <div class="banner-title">{{ templateData?.title }}</div>
          <div class="banner-desc">{{ templateData?.description || t('lowcode.runtimeTip', '请按照下方表单输入内容，系统将自动合成标准电子单据并流转审批。') }}</div>
        </div>
      </div>

      <!-- ── Dynamic Form Fields ─────────────────────────────── -->
      <el-form 
        ref="formRef" 
        :model="formData" 
        :rules="formRules" 
        label-position="top" 
        class="runtime-el-form"
      >
        <!-- Custom document title override (optional) -->
        <el-form-item :label="t('lowcode.customDocTitle', '单据标题 (默认自动生成)')">
          <el-input 
            v-model="customDocTitle" 
            :placeholder="defaultGeneratedTitle" 
            clearable
          />
        </el-form-item>

        <el-divider style="margin: 12px 0 18px;" />

        <el-row :gutter="18">
          <el-col 
            v-for="field in schemaFields" 
            :key="field.id"
            :span="['textarea', 'divider', 'alert', 'attachment', 'daterange'].includes(field.type) ? 24 : 12"
          >
            <el-form-item 
              :label="field.label" 
              :prop="field.id"
              :required="field.required"
            >
              <!-- 1. Text -->
              <el-input 
                v-if="field.type === 'text'" 
                v-model="formData[field.id]" 
                :placeholder="field.placeholder || '请输入...'" 
                clearable
              />

              <!-- 2. Textarea -->
              <el-input 
                v-else-if="field.type === 'textarea'" 
                v-model="formData[field.id]" 
                type="textarea" 
                :rows="3" 
                :placeholder="field.placeholder || '请填写详细说明...'" 
              />

              <!-- 3. Pure Number / Quantity -->
              <div v-else-if="field.type === 'number'" class="number-input-wrap" style="display: flex; align-items: center; gap: 8px; width: 100%;">
                <el-input-number 
                  v-model="formData[field.id]" 
                  :min="field.min" 
                  :max="field.max"
                  :step="field.step || 1"
                  :precision="field.precision !== undefined ? field.precision : undefined"
                  :placeholder="field.placeholder || '请输入数值/数量'"
                  style="flex: 1;" 
                />
                <el-tag v-if="field.unit" type="info" effect="plain" style="font-weight: 500;">{{ field.unit }}</el-tag>
              </div>

              <!-- 3b. Amount / Currency -->
              <div v-else-if="field.type === 'amount'" class="amount-input-wrap" style="width: 100%;">
                <div style="display: flex; align-items: center; gap: 8px; width: 100%;">
                  <span style="font-size: 15px; font-weight: bold; color: #67c23a;">￥</span>
                  <el-input-number 
                    v-model="formData[field.id]" 
                    :min="field.min !== undefined ? field.min : 0" 
                    :max="field.max"
                    :step="field.step || 10"
                    :precision="2"
                    :placeholder="field.placeholder || '0.00'"
                    style="flex: 1;" 
                  />
                  <span style="font-size: 13px; color: var(--el-text-color-secondary);">{{ field.unit || '元' }}</span>
                </div>
                <div v-if="formData[field.id]" class="amount-cny-preview" style="font-size: 12px; color: #67c23a; margin-top: 4px; padding-left: 20px;">
                  💰 人民币大写: {{ convertToChineseCapital(formData[field.id]) }}
                </div>
              </div>

              <!-- 4. Date (Single) -->
              <el-date-picker 
                v-else-if="field.type === 'date'" 
                v-model="formData[field.id]" 
                type="date" 
                value-format="YYYY-MM-DD" 
                :placeholder="field.placeholder || '选择日期'"
                style="width: 100%;" 
              />

              <!-- 5. Date Range (起止日期区间) -->
              <el-date-picker 
                v-else-if="field.type === 'daterange'" 
                v-model="formData[field.id]" 
                type="daterange" 
                range-separator="至" 
                start-placeholder="开始日期" 
                end-placeholder="结束日期" 
                value-format="YYYY-MM-DD" 
                style="width: 100%;" 
              />

              <!-- 6. Time (具体时间，带年月日时分) -->
              <el-date-picker 
                v-else-if="field.type === 'time'" 
                v-model="formData[field.id]" 
                type="datetime"
                :placeholder="field.placeholder || '选择具体时间 (年月日 时:分)'"
                format="YYYY-MM-DD HH:mm"
                value-format="YYYY-MM-DD HH:mm"
                style="width: 100%;" 
              />

              <!-- 7. Time Range (起止时间区间，带年月日时分) -->
              <el-date-picker 
                v-else-if="field.type === 'timerange'" 
                v-model="formData[field.id]" 
                type="datetimerange" 
                range-separator="至" 
                start-placeholder="开始时间" 
                end-placeholder="结束时间" 
                format="YYYY-MM-DD HH:mm"
                value-format="YYYY-MM-DD HH:mm" 
                style="width: 100%;" 
              />

              <!-- 8. Slider (进度滑块) -->
              <div v-else-if="field.type === 'slider'" style="padding: 0 10px; width: 100%;">
                <el-slider v-model="formData[field.id]" :step="5" show-input />
              </div>

              <!-- 9. Switch (是否开关) -->
              <el-switch 
                v-else-if="field.type === 'switch'" 
                v-model="formData[field.id]" 
                :active-text="field.activeText || '是'" 
                :inactive-text="field.inactiveText || '否'" 
              />

              <!-- 10. Rate (优先级评星) -->
              <el-rate 
                v-else-if="field.type === 'rate'" 
                v-model="formData[field.id]" 
                show-score 
                text-color="#ff9900" 
              />

              <!-- 11. Select with Other support -->
              <div v-else-if="field.type === 'select'" style="width: 100%;">
                <el-select 
                  v-model="formData[field.id]" 
                  :filterable="field.allowOther"
                  :allow-create="field.allowOther"
                  default-first-option
                  :placeholder="field.allowOther ? '请选择或直接输入自定义内容...' : (field.placeholder || '请选择')"
                  style="width: 100%;"
                >
                  <el-option v-for="opt in (field.options || [])" :key="opt" :label="opt" :value="opt" />
                  <el-option v-if="field.allowOther" label="其他 (自定义填写)" value="__other__" />
                </el-select>
                <el-input 
                  v-if="field.allowOther && formData[field.id] === '__other__'" 
                  v-model="otherInputs[field.id]" 
                  :placeholder="field.otherPlaceholder || '请输入其他具体内容...'" 
                  size="small" 
                  style="margin-top: 6px;" 
                />
              </div>

              <!-- 12. Radio with Other support -->
              <div v-else-if="field.type === 'radio'" style="width: 100%;">
                <el-radio-group v-model="formData[field.id]">
                  <el-radio v-for="opt in (field.options || [])" :key="opt" :value="opt">{{ opt }}</el-radio>
                  <el-radio v-if="field.allowOther" value="__other__">其他 (可填写内容)</el-radio>
                </el-radio-group>
                <el-input 
                  v-if="field.allowOther && formData[field.id] === '__other__'" 
                  v-model="otherInputs[field.id]" 
                  :placeholder="field.otherPlaceholder || '请输入其他具体说明...'" 
                  size="small" 
                  style="margin-top: 6px;" 
                />
              </div>

              <!-- 13. Checkbox with Other support -->
              <div v-else-if="field.type === 'checkbox'" style="width: 100%;">
                <el-checkbox-group v-model="formData[field.id]">
                  <el-checkbox v-for="opt in (field.options || [])" :key="opt" :value="opt">{{ opt }}</el-checkbox>
                  <el-checkbox v-if="field.allowOther" value="__other__">其他 (可填写内容)</el-checkbox>
                </el-checkbox-group>
                <el-input 
                  v-if="field.allowOther && Array.isArray(formData[field.id]) && formData[field.id].includes('__other__')" 
                  v-model="otherInputs[field.id]" 
                  :placeholder="field.otherPlaceholder || '请输入其他具体说明...'" 
                  size="small" 
                  style="margin-top: 6px;" 
                />
              </div>

              <!-- 14. NPS 0-10 Rating -->
              <div v-else-if="field.type === 'nps'" class="runtime-nps-box">
                <div class="runtime-nps-btns">
                  <button 
                    type="button" 
                    v-for="n in 11" 
                    :key="n-1" 
                    class="runtime-nps-btn" 
                    :class="{'is-selected': formData[field.id] === (n-1)}"
                    @click="formData[field.id] = (n-1)"
                  >
                    {{ n-1 }}
                  </button>
                </div>
                <div class="runtime-nps-labels">
                  <span>{{ field.minLabel || '0 不太可能' }}</span>
                  <span class="nps-curr-val" v-if="formData[field.id] !== undefined">当前选择: {{ formData[field.id] }} 分</span>
                  <span>{{ field.maxLabel || '10 极有可能' }}</span>
                </div>
              </div>

              <!-- 15. Ranking Sort -->
              <div v-else-if="field.type === 'ranking'" class="runtime-ranking-box">
                <div 
                  v-for="(item, rIdx) in (formData[field.id] || [])" 
                  :key="item" 
                  class="runtime-rank-row"
                >
                  <span class="rank-pos">{{ Number(rIdx) + 1 }}</span>
                  <span class="rank-title">{{ item }}</span>
                  <div class="rank-btns">
                    <el-button circle size="small" :disabled="Number(rIdx) === 0" @click="moveRankItem(field.id, Number(rIdx), -1)">↑</el-button>
                    <el-button circle size="small" :disabled="Number(rIdx) === (formData[field.id].length - 1)" @click="moveRankItem(field.id, Number(rIdx), 1)">↓</el-button>
                  </div>
                </div>
              </div>

              <!-- 16. Phone -->
              <el-input 
                v-else-if="field.type === 'phone'" 
                v-model="formData[field.id]" 
                :placeholder="field.placeholder || '请输入11位手机号码'" 
                maxlength="11" 
              >
                <template #prefix><el-icon><Iphone /></el-icon></template>
              </el-input>

              <!-- 17. Gender -->
              <el-radio-group v-else-if="field.type === 'gender'" v-model="formData[field.id]">
                <el-radio value="男">👨 男</el-radio>
                <el-radio value="女">👩 女</el-radio>
                <el-radio value="保密">🔒 保密</el-radio>
              </el-radio-group>

              <!-- 18. Email -->
              <el-input 
                v-else-if="field.type === 'email'" 
                v-model="formData[field.id]" 
                :placeholder="field.placeholder || '请输入电子邮箱 (如 user@company.com)'" 
              >
                <template #prefix><el-icon><Message /></el-icon></template>
              </el-input>

              <!-- 19. Dept Select -->
              <el-select 
                v-else-if="field.type === 'dept_select'" 
                v-model="formData[field.id]" 
                :placeholder="field.placeholder || '选择所属部门'"
                style="width: 100%;"
              >
                <el-option 
                  v-for="d in depts" 
                  :key="d.id" 
                  :label="d.name" 
                  :value="d.name" 
                />
              </el-select>

              <!-- 20. User Select -->
              <el-select 
                v-else-if="field.type === 'user_select'" 
                v-model="formData[field.id]" 
                :placeholder="field.placeholder || '选择责任人'"
                filterable
                style="width: 100%;"
              >
                <el-option 
                  v-for="u in usersList" 
                  :key="u.id" 
                  :label="`${u.display_name} (${u.department_name || '未分配'})`" 
                  :value="u.display_name" 
                />
              </el-select>

              <!-- 21. Hand-written Electronic Signature (手写电子签名) -->
              <div v-else-if="field.type === 'signature'" class="runtime-signature-container">
                <div v-if="formData[field.id]" class="signed-preview-box">
                  <img :src="formData[field.id]" alt="已签名" class="signed-img" />
                  <el-button size="small" type="danger" plain @click="formData[field.id] = ''">清空重签</el-button>
                </div>
                <div v-else class="signature-pad-wrapper">
                  <canvas 
                    :ref="(el) => setSignatureCanvasRef(el, field.id)" 
                    class="signature-canvas" 
                    width="460" 
                    height="130"
                    @mousedown="startDrawing($event, field.id)"
                    @mousemove="draw($event, field.id)"
                    @mouseup="stopDrawing(field.id)"
                    @mouseleave="stopDrawing(field.id)"
                    @touchstart.passive="startTouchDrawing($event, field.id)"
                    @touchmove.passive="touchDraw($event, field.id)"
                    @touchend="stopDrawing(field.id)"
                  ></canvas>
                  <div class="sig-actions-row">
                    <span class="sig-hint">请在框内手写签字 (支持鼠标与触屏)</span>
                    <div style="display: flex; gap: 8px;">
                      <el-button size="small" @click="clearSignature(field.id)">清空</el-button>
                      <el-button size="small" type="primary" @click="saveSignature(field.id)">确认签字</el-button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 22. Image / Photo Uploader (图片相册上传) -->
              <div v-else-if="field.type === 'image_upload'" class="runtime-image-uploader">
                <div class="image-previews-grid">
                  <div v-for="(img, imgIdx) in (formData[field.id] || [])" :key="imgIdx" class="image-thumb-card">
                    <img :src="img.url" :alt="img.name" class="thumb-img" />
                    <el-icon class="thumb-del" @click.stop="removeImage(field.id, Number(imgIdx))"><Close /></el-icon>
                  </div>
                  <el-upload
                    action="#"
                    :http-request="(opts: any) => handleImageUpload(opts, field.id)"
                    :show-file-list="false"
                    accept="image/*"
                    class="image-add-btn"
                  >
                    <el-icon><Plus /></el-icon>
                    <span style="font-size: 11px; margin-top: 4px;">上传图片</span>
                  </el-upload>
                </div>
              </div>

              <!-- 23. Dynamic Subform Table (自增明细子表) -->
              <div v-else-if="field.type === 'subform'" class="runtime-subform-box">
                <el-table :data="formData[field.id] || []" border size="small" style="width: 100%;">
                  <el-table-column type="index" label="序号" width="50" align="center" />
                  <el-table-column 
                    v-for="col in (field.columns || [{id: 'col_1', label: '项目', type: 'text'}])" 
                    :key="col.id" 
                    :label="col.label"
                  >
                    <template #default="{ row }">
                      <el-input-number 
                        v-if="col.type === 'number'" 
                        v-model="row[col.id]" 
                        size="small" 
                        :step="1"
                        controls-position="right" 
                        style="width: 100%;" 
                      />
                      <el-input-number 
                        v-else-if="col.type === 'amount'" 
                        v-model="row[col.id]" 
                        size="small" 
                        :precision="2"
                        :step="10"
                        controls-position="right" 
                        style="width: 100%;" 
                      />
                      <el-date-picker 
                        v-else-if="col.type === 'date'" 
                        v-model="row[col.id]" 
                        type="date" 
                        value-format="YYYY-MM-DD" 
                        size="small" 
                        style="width: 100%;" 
                      />
                      <el-input 
                        v-else 
                        v-model="row[col.id]" 
                        size="small" 
                        :placeholder="`输入${col.label}`" 
                      />
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="60" align="center">
                    <template #default="{ $index }">
                      <el-button circle size="small" type="danger" :icon="Delete" @click="removeSubformRow(field.id, Number($index))" />
                    </template>
                  </el-table-column>
                </el-table>
                <el-button 
                  size="small" 
                  type="primary" 
                  plain 
                  :icon="Plus" 
                  @click="addSubformRow(field)" 
                  style="width: 100%; margin-top: 8px;"
                >
                  + 添加一行明细
                </el-button>
              </div>

              <!-- 24. Attachment Uploader (附件上传) -->
              <div v-else-if="field.type === 'attachment'" class="attachment-upload-zone">
                <el-upload
                  action="#"
                  :http-request="(opts: any) => handleAttachmentUpload(opts, field.id)"
                  :show-file-list="false"
                  drag
                  class="attach-uploader"
                >
                  <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                  <div class="el-upload__text">
                    拖拽文件到此处，或 <em>点击上传凭证/附件</em>
                  </div>
                </el-upload>

                <!-- Uploaded file chips -->
                <div class="uploaded-files-list" v-if="formData[field.id] && formData[field.id].length > 0">
                  <div v-for="(file, fIdx) in formData[field.id]" :key="fIdx" class="file-chip">
                    <el-icon class="file-chip-icon"><Paperclip /></el-icon>
                    <span class="file-chip-name" :title="file.name">{{ file.name }}</span>
                    <span class="file-chip-size">({{ formatFileSize(file.size) }})</span>
                    <el-icon class="file-chip-del" @click.stop="removeFile(field.id, Number(fIdx))"><Close /></el-icon>
                  </div>
                </div>
              </div>

              <!-- 17. Alert -->
              <el-alert 
                v-else-if="field.type === 'alert'" 
                :title="field.label" 
                :type="field.alertType || 'info'" 
                :closable="false" 
              />

              <!-- 18. Divider -->
              <el-divider v-else-if="field.type === 'divider'">{{ field.label }}</el-divider>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- ── Approval Workflow Section (流转审批设置) ──────────── -->
        <div class="approval-flow-box">
          <div class="flow-box-header">
            <el-icon class="flow-icon"><Stamp /></el-icon>
            <span class="flow-title">流转审批设置 (提交后自动推送至对应人审核)</span>
          </div>

          <el-row :gutter="16">
            <el-col :span="10">
              <el-form-item label="审批流转方式">
                <el-radio-group v-model="approvalType" size="small">
                  <el-radio value="sequential">逐级流转审批 (串行)</el-radio>
                  <el-radio value="parallel">部门会签 (并行)</el-radio>
                </el-radio-group>
              </el-form-item>
            </el-col>

            <el-col :span="14">
              <el-form-item label="指定流转审批人 (可多选)" required>
                <el-select
                  v-model="selectedApprovers"
                  multiple
                  filterable
                  placeholder="请选择审批人 (部门经理/主管)"
                  style="width: 100%;"
                >
                  <el-option
                    v-for="u in eligibleApprovers"
                    :key="u.id"
                    :label="`${u.display_name} (${u.department_name || '未分配'})`"
                    :value="u.id"
                  />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
        </div>
      </el-form>
    </div>

    <template #footer>
      <div class="runtime-footer">
        <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
        <el-button 
          type="default" 
          :icon="Document" 
          :loading="submitting" 
          @click="submitDoc(false)"
        >
          暂存为草稿
        </el-button>
        <el-button 
          type="primary" 
          :icon="Promotion" 
          :loading="submitting" 
          @click="submitDoc(true)"
          class="submit-flow-btn"
        >
          🚀 提交并流转审批
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import api from "@/api/client";
import { ElMessage, type FormInstance, type FormRules, type UploadRequestOptions } from "element-plus";
import { useAuthStore } from "@/stores/auth";
import {
  Document, Tickets, Money, Calendar, Timer,
  List, CircleCheck, Folder, User, Warning, Operation, Memo, Management,
  Paperclip, Star, Switch as SwitchIcon, Histogram, UploadFilled, Close,
  Stamp, Promotion, Picture, Iphone, Message, Plus, Delete, Rank
} from "@element-plus/icons-vue";

const props = defineProps<{
  modelValue: boolean;
  templateData: any;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", val: boolean): void;
  (e: "generated", doc: any): void;
}>();

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

const { t } = useI18n();
const router = useRouter();
const auth = useAuthStore();

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit("update:modelValue", val)
});

const formRef = ref<FormInstance>();
const submitting = ref(false);
const formData = ref<Record<string, any>>({});
const otherInputs = ref<Record<string, string>>({});
const customDocTitle = ref("");
const depts = ref<any[]>([]);
const usersList = ref<any[]>([]);

// Approval flow state
const approvalType = ref<"sequential" | "parallel">("sequential");
const selectedApprovers = ref<number[]>([]);

const ICON_MAP: Record<string, any> = {
  Document, Tickets, Money, Calendar, Timer, List, CircleCheck, Folder, User, Warning, Operation, Memo, Management,
  Paperclip, Star, Switch: SwitchIcon, Histogram, Stamp, Promotion, Picture, Iphone, Message, Rank
};

function getIconComponent(name?: string) {
  if (!name) return Document;
  return ICON_MAP[name] || Document;
}

const schemaFields = computed(() => {
  return props.templateData?.template_schema?.fields || [];
});

const defaultGeneratedTitle = computed(() => {
  const tmplTitle = props.templateData?.title || "业务申请单据";
  const myName = auth.user?.display_name || "员工";
  const dateStr = new Date().toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" });
  return `${tmplTitle} - ${myName} (${dateStr})`;
});

// Filter out current user from approvers list (cannot approve self)
const eligibleApprovers = computed(() => {
  const myId = auth.user?.id;
  return usersList.value.filter(u => u.id !== myId);
});

const formRules = computed<FormRules>(() => {
  const rules: FormRules = {};
  schemaFields.value.forEach((f: any) => {
    const fieldRules: any[] = [];
    if (f.required && !['divider', 'alert'].includes(f.type)) {
      fieldRules.push({ 
        required: true, 
        message: `${f.label} 不能为空`, 
        trigger: ['select', 'dept_select', 'gender', 'nps'].includes(f.type) ? 'change' : 'blur' 
      });
    }
    if (f.type === 'phone') {
      fieldRules.push({
        pattern: /^1[3-9]\d{9}$/,
        message: '请输入正确的11位手机号码格式',
        trigger: 'blur'
      });
    }
    if (f.type === 'email') {
      fieldRules.push({
        type: 'email',
        message: '请输入有效的电子邮箱地址',
        trigger: 'blur'
      });
    }
    if (fieldRules.length > 0) {
      rules[f.id] = fieldRules;
    }
  });
  return rules;
});

watch(() => props.templateData, (val) => {
  if (val) {
    customDocTitle.value = "";
    otherInputs.value = {};
    const initData: Record<string, any> = {};
    const fields = val.template_schema?.fields || [];
    
    fields.forEach((f: any) => {
      if (f.type === "checkbox" || f.type === "daterange" || f.type === "timerange" || f.type === "attachment" || f.type === "image_upload" || f.type === "subform") {
        initData[f.id] = [];
      } else if (f.type === "ranking") {
        initData[f.id] = f.options ? [...f.options] : ['方案A', '方案B', '方案C'];
      } else if (f.type === "nps") {
        initData[f.id] = f.defaultValue !== undefined ? f.defaultValue : 10;
      } else if (f.type === "gender") {
        initData[f.id] = f.defaultValue || '男';
      } else if (f.type === "switch") {
        initData[f.id] = false;
      } else if (f.type === "slider") {
        initData[f.id] = f.defaultValue || 50;
      } else if (f.type === "rate") {
        initData[f.id] = f.defaultValue || 4;
      } else if (f.type === "dept_select" && (auth.user as any)?.department_name) {
        initData[f.id] = (auth.user as any).department_name;
      } else if (f.type === "user_select" && auth.user?.display_name) {
        initData[f.id] = auth.user.display_name;
      } else if (f.type === "date") {
        initData[f.id] = new Date().toISOString().split("T")[0];
      } else if (f.defaultValue !== undefined) {
        initData[f.id] = f.defaultValue;
      } else {
        initData[f.id] = "";
      }
    });
    formData.value = initData;
  }
}, { immediate: true });

// ── Ranking Controls ──────────────────────────────────────────
function moveRankItem(fieldId: string, idx: number, step: number) {
  const list = formData.value[fieldId];
  if (!list) return;
  const target = idx + step;
  if (target < 0 || target >= list.length) return;
  const item = list.splice(idx, 1)[0];
  list.splice(target, 0, item);
}

// ── Subform Repeating Table Controls ──────────────────────────
function addSubformRow(field: any) {
  if (!formData.value[field.id]) formData.value[field.id] = [];
  const newRow: Record<string, any> = {};
  (field.columns || [{id: 'col_1', label: '明细', type: 'text'}]).forEach((col: any) => {
    newRow[col.id] = col.type === 'number' ? 0 : '';
  });
  formData.value[field.id].push(newRow);
}

function removeSubformRow(fieldId: string, idx: number) {
  if (formData.value[fieldId]) {
    formData.value[fieldId].splice(idx, 1);
  }
}

// ── Image Upload ──────────────────────────────────────────────
async function handleImageUpload(options: UploadRequestOptions, fieldId: string) {
  const file = options.file;
  const form = new FormData();
  form.append("file", file);

  try {
    const res = await api.post("/documents/upload-attachment", form, {
      headers: { "Content-Type": "multipart/form-data" }
    });
    if (!formData.value[fieldId]) formData.value[fieldId] = [];
    formData.value[fieldId].push({
      name: res.data.original_name || file.name,
      url: res.data.url,
      size: res.data.size || file.size
    });
    ElMessage.success(`图片 [${file.name}] 上传成功`);
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || "图片上传失败");
  }
}

function removeImage(fieldId: string, idx: number) {
  if (formData.value[fieldId]) {
    formData.value[fieldId].splice(idx, 1);
  }
}

// ── Hand-written Signature Canvas ─────────────────────────────
const canvasMap = new Map<string, HTMLCanvasElement>();
const isDrawingMap = new Map<string, boolean>();

function setSignatureCanvasRef(el: any, fieldId: string) {
  if (el) {
    canvasMap.set(fieldId, el as HTMLCanvasElement);
    const ctx = (el as HTMLCanvasElement).getContext('2d');
    if (ctx) {
      ctx.lineWidth = 2.5;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.strokeStyle = '#0f172a';
    }
  }
}

function getCanvasPos(e: MouseEvent, canvas: HTMLCanvasElement) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: e.clientX - rect.left,
    y: e.clientY - rect.top
  };
}

function startDrawing(e: MouseEvent, fieldId: string) {
  const canvas = canvasMap.get(fieldId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  isDrawingMap.set(fieldId, true);
  const pos = getCanvasPos(e, canvas);
  ctx.beginPath();
  ctx.moveTo(pos.x, pos.y);
}

function draw(e: MouseEvent, fieldId: string) {
  if (!isDrawingMap.get(fieldId)) return;
  const canvas = canvasMap.get(fieldId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  const pos = getCanvasPos(e, canvas);
  ctx.lineTo(pos.x, pos.y);
  ctx.stroke();
}

function stopDrawing(fieldId: string) {
  isDrawingMap.set(fieldId, false);
}

function startTouchDrawing(e: TouchEvent, fieldId: string) {
  const canvas = canvasMap.get(fieldId);
  if (!canvas || !e.touches[0]) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  isDrawingMap.set(fieldId, true);
  const rect = canvas.getBoundingClientRect();
  const x = e.touches[0].clientX - rect.left;
  const y = e.touches[0].clientY - rect.top;
  ctx.beginPath();
  ctx.moveTo(x, y);
}

function touchDraw(e: TouchEvent, fieldId: string) {
  if (!isDrawingMap.get(fieldId)) return;
  const canvas = canvasMap.get(fieldId);
  if (!canvas || !e.touches[0]) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  const rect = canvas.getBoundingClientRect();
  const x = e.touches[0].clientX - rect.left;
  const y = e.touches[0].clientY - rect.top;
  ctx.lineTo(x, y);
  ctx.stroke();
}

function clearSignature(fieldId: string) {
  const canvas = canvasMap.get(fieldId);
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (ctx) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }
}

function saveSignature(fieldId: string) {
  const canvas = canvasMap.get(fieldId);
  if (!canvas) return;
  const dataUrl = canvas.toDataURL('image/png');
  formData.value[fieldId] = dataUrl;
  ElMessage.success('已确认手写签名');
}

async function loadDropdownOptions() {
  try {
    const [deptRes, userRes] = await Promise.all([
      api.get("/users/departments"),
      api.get("/users", { params: { size: 100 } })
    ]);
    depts.value = deptRes.data || [];
    const rawUsers = userRes.data?.items || [];
    usersList.value = rawUsers;

    // Smart default approver: pick manager/admin if available
    const myId = auth.user?.id;
    const managers = rawUsers.filter((u: any) => u.id !== myId && (u.is_manager || u.is_super_admin || (u.role_level && u.role_level >= 50)));
    if (managers.length > 0 && selectedApprovers.value.length === 0) {
      selectedApprovers.value = [managers[0].id];
    }
  } catch (err) {
    console.error("Failed to load departments or users list", err);
  }
}

async function handleAttachmentUpload(options: UploadRequestOptions, fieldId: string) {
  const file = options.file;
  const form = new FormData();
  form.append("file", file);

  try {
    const res = await api.post("/documents/upload-attachment", form, {
      headers: { "Content-Type": "multipart/form-data" }
    });
    if (!formData.value[fieldId]) formData.value[fieldId] = [];
    formData.value[fieldId].push({
      name: res.data.original_name || file.name,
      url: res.data.url,
      size: res.data.size || file.size
    });
    ElMessage.success(`附件 [${file.name}] 上传成功`);
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || "附件上传失败");
  }
}

function removeFile(fieldId: string, idx: number) {
  if (formData.value[fieldId]) {
    formData.value[fieldId].splice(idx, 1);
  }
}

function formatFileSize(bytes?: number) {
  if (!bytes) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

async function submitDoc(forApproval: boolean) {
  if (!formRef.value) return;
  const valid = await formRef.value.validate().catch(() => false);
  if (!valid) {
    return ElMessage.warning(t('lowcode.formValidateError', '请完整填写表单必填字段'));
  }

  if (forApproval && selectedApprovers.value.length === 0) {
    return ElMessage.warning("请选择至少一位流转审批人");
  }

  if (!props.templateData?.id) return;
  submitting.value = true;
  try {
    const finalTitle = customDocTitle.value.trim() || defaultGeneratedTitle.value;
    
    // Merge '__other__' custom input values into clean payload
    const cleanFormData: Record<string, any> = { ...formData.value };
    const fields = props.templateData?.template_schema?.fields || [];
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

    const { data } = await api.post(`/templates/${props.templateData.id}/generate-from-form`, {
      form_data: cleanFormData,
      title: finalTitle,
      submit_for_approval: forApproval,
      approvers: selectedApprovers.value,
      flow_type: approvalType.value
    });

    if (forApproval) {
      ElMessage.success("🎉 已成功提交申请单并流转给审批人！");
    } else {
      ElMessage.success("📝 草稿单据已生成！");
    }

    visible.value = false;
    emit("generated", data);
    
    // Redirect to document view / editor
    if (data.id) {
      router.push(`/doc/${data.id}`);
    }
  } catch (err: any) {
    ElMessage.error(err.response?.data?.error || t('common.failed'));
  } finally {
    submitting.value = false;
  }
}

onMounted(() => {
  loadDropdownOptions();
});
</script>

<style scoped>
.runtime-form-container {
  padding: 4px 12px;
}

.form-banner {
  display: flex;
  align-items: center;
  gap: 16px;
  background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%);
  border: 1px solid #bbf7d0;
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 20px;
}

.banner-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: var(--el-color-primary);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
}

.banner-title {
  font-size: 16px;
  font-weight: 700;
  color: #065f46;
  margin-bottom: 2px;
}

.banner-desc {
  font-size: 12px;
  color: #047857;
}

.runtime-el-form {
  max-height: 60vh;
  overflow-y: auto;
  padding-right: 8px;
}

/* Approval Flow Config Box */
.approval-flow-box {
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 10px;
  padding: 16px 18px;
  margin-top: 14px;
  margin-bottom: 8px;
}

.flow-box-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.flow-icon {
  font-size: 18px;
  color: #d97706;
}

.flow-title {
  font-size: 13px;
  font-weight: 700;
  color: #92400e;
}

.runtime-footer {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 10px;
}

.submit-flow-btn {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
  border: none !important;
  font-weight: 700;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.25);
}

.submit-flow-btn:hover {
  opacity: 0.92;
  transform: translateY(-1px);
}

/* Attachment upload styling */
.attachment-upload-zone {
  width: 100%;
}

.attach-uploader :deep(.el-upload-dragger) {
  padding: 14px 10px;
  border-radius: 8px;
}

.uploaded-files-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.file-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 12px;
  color: #1e293b;
}

.file-chip-icon {
  color: #2563eb;
}

.file-chip-name {
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
}

.file-chip-size {
  color: #94a3b8;
  font-size: 11px;
}

.file-chip-del {
  cursor: pointer;
  color: #94a3b8;
  font-size: 14px;
  transition: color 0.15s;
}

.file-chip-del:hover {
  color: #ef4444;
}

/* ── Runtime NPS Scale ─────────────────────────────────────── */
.runtime-nps-box {
  width: 100%;
}
.runtime-nps-btns {
  display: flex;
  gap: 4px;
}
.runtime-nps-btn {
  flex: 1;
  padding: 8px 0;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  border-radius: 6px;
  font-weight: 700;
  font-size: 13px;
  color: #334155;
  cursor: pointer;
  transition: all 0.15s ease;
}
.runtime-nps-btn:hover {
  border-color: var(--el-color-primary);
  color: var(--el-color-primary);
}
.runtime-nps-btn.is-selected {
  background: var(--el-color-primary);
  border-color: var(--el-color-primary);
  color: #ffffff;
  box-shadow: 0 2px 6px rgba(0,0,0,0.12);
}
.runtime-nps-labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #64748b;
  margin-top: 4px;
}
.nps-curr-val {
  font-weight: bold;
  color: var(--el-color-primary);
}

/* ── Runtime Ranking Box ───────────────────────────────────── */
.runtime-ranking-box {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}
.runtime-rank-row {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 6px 12px;
}
.rank-pos {
  width: 22px;
  height: 22px;
  background: var(--el-color-primary);
  color: #ffffff;
  border-radius: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: bold;
}
.rank-title {
  flex: 1;
  font-size: 13px;
  color: #1e293b;
  font-weight: 500;
}
.rank-btns {
  display: flex;
  gap: 4px;
}

/* ── Hand-written Signature Canvas ─────────────────────────── */
.runtime-signature-container {
  width: 100%;
}
.signature-pad-wrapper {
  background: #ffffff;
  border: 1.5px dashed #94a3b8;
  border-radius: 8px;
  padding: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.signature-canvas {
  background: #f8fafc;
  border-radius: 6px;
  cursor: crosshair;
  touch-action: none;
  width: 100%;
  max-width: 460px;
}
.sig-actions-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  margin-top: 6px;
}
.sig-hint {
  font-size: 12px;
  color: #64748b;
}
.signed-preview-box {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 14px;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
}
.signed-img {
  max-height: 70px;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  background: #ffffff;
}

/* ── Image Uploader ────────────────────────────────────────── */
.runtime-image-uploader {
  width: 100%;
}
.image-previews-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.image-thumb-card {
  position: relative;
  width: 72px;
  height: 72px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid #cbd5e1;
}
.thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.thumb-del {
  position: absolute;
  top: 2px;
  right: 2px;
  background: rgba(0,0,0,0.6);
  color: #ffffff;
  border-radius: 50%;
  font-size: 12px;
  padding: 2px;
  cursor: pointer;
}
.image-add-btn :deep(.el-upload) {
  width: 72px;
  height: 72px;
  border: 1.5px dashed #cbd5e1;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #64748b;
  cursor: pointer;
  transition: border-color 0.2s;
}
.image-add-btn :deep(.el-upload:hover) {
  border-color: var(--el-color-primary);
  color: var(--el-color-primary);
}

/* ── Subform Box ───────────────────────────────────────────── */
.runtime-subform-box {
  width: 100%;
}
</style>
