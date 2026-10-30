<script setup>
import { computed, nextTick, ref } from 'vue'
import {
  ArrowUp,
  Bot,
  ChevronDown,
  ChevronRight,
  CircleDollarSign,
  Clock3,
  FileText,
  LayoutGrid,
  Menu,
  MessageSquareText,
  MoreHorizontal,
  PackageSearch,
  PanelLeftClose,
  Plus,
  Search,
  ShieldAlert,
  Sparkles,
  UserRound,
  X,
} from '@lucide/vue'

const input = ref('')
const isSending = ref(false)
const sidebarOpen = ref(false)
const chatBody = ref(null)
const expandedTools = ref(new Set(['tool-1']))
const conversationId = ref(crypto.randomUUID())
const selectedModule = ref('order')

const businessConfigs = {
  order: {
    icon: PackageSearch,
    noun: '订单',
    title: '订单智能助手',
    placeholder: '输入订单问题，例如：查询订单 JFK24050029 的状态',
    welcome: '你好，我是运智助手。我可以帮你查询订单状态、核对订单详情，也会清楚展示每次查询调用的业务工具。',
    suggestions: [
      { icon: PackageSearch, title: '查询订单状态', text: '查询订单 JFK24050029 的状态' },
      { icon: FileText, title: '查看订单详情', text: '帮我查看订单 JFK24050029 的完整信息' },
      { icon: Clock3, title: '检查异常订单', text: '这个订单为什么一直没有更新？' },
    ],
  },
  shipment: {
    icon: FileText,
    noun: '提单',
    title: '提单智能助手',
    placeholder: '输入提单问题，例如：查询提单号 SH202410180026 的状态',
    welcome: '你好，我是运智助手。我可以根据提单号查询提单状态，包括待流转干线、待绑干线、已绑干线、待更资料、已更资料和资料归档。',
    suggestions: [
      { icon: FileText, title: '查询提单状态', text: '我想查询一个提单的状态，请提示我输入提单号' },
      { icon: Clock3, title: '查看提单进度', text: '根据提单号可以查询哪些提单进度？' },
      { icon: PackageSearch, title: '提单状态说明', text: '请说明提单的各个状态分别代表什么' },
    ],
  },
  finance: {
    icon: CircleDollarSign,
    noun: '财务单据',
    title: '财务智能助手',
    placeholder: '输入财务问题，例如：查询对账单 OUT20260917001 的状态',
    welcome: '你好，我是运智助手。我可以查询付款单和对账单状态。请说明单据类型并提供对应编号。',
    suggestions: [
      { icon: CircleDollarSign, title: '查询付款单状态', text: '查询付款单 LD20261029010 的状态' },
      { icon: FileText, title: '查询对账单状态', text: '查询对账单 OUT20260917001 的状态' },
      { icon: Clock3, title: '财务状态说明', text: '请说明付款单和对账单的各个状态分别代表什么' },
    ],
  },
}

const activeBusiness = computed(() => businessConfigs[selectedModule.value])
const suggestions = computed(() => activeBusiness.value.suggestions)

const modules = [
  { key: 'order', icon: PackageSearch, label: '订单' },
  { key: 'shipment', icon: FileText, label: '提单' },
  { key: 'finance', icon: CircleDollarSign, label: '财务' },
  { key: 'penalty', icon: ShieldAlert, label: '扣罚', soon: true },
]

const sessions = ref([
  { id: 1, title: '查询订单运输进度', time: '刚刚', active: true },
  { id: 2, title: '订单信息核对', time: '昨天' },
  { id: 3, title: '异常订单查询', time: '10月18日' },
])

const messages = ref([
  {
    id: 'welcome',
    role: 'assistant',
    content: '你好，我是运智助手。我可以帮你查询订单状态、核对订单详情，也会清楚展示每次查询调用的业务工具。',
    time: '10:24',
  },
  {
    id: 'user-demo',
    role: 'user',
    content: '帮我查一下订单 OD202410180026 现在是什么状态？',
    time: '10:25',
  },
  {
    id: 'answer-demo',
    role: 'assistant',
    content: '订单 **OD202410180026** 当前处于「运输中」状态。\n\n货物已于 10 月 19 日从上海仓发出，目前正在前往深圳中转中心，预计 10 月 22 日到达。当前运输进度正常，暂无异常。',
    time: '10:25',
    tools: [
      {
        id: 'tool-1',
        name: 'get_order_status',
        server: '订单 MCP Server',
        duration: '286 ms',
        status: 'success',
        args: { order_no: 'OD202410180026' },
        result: { status: 'in_transit', status_text: '运输中', eta: '2024-10-22' },
      },
    ],
  },
])

const canSend = computed(() => input.value.trim() && !isSending.value)

function formatContent(content) {
  return content
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

function toggleTool(id) {
  const next = new Set(expandedTools.value)
  next.has(id) ? next.delete(id) : next.add(id)
  expandedTools.value = next
}

function newConversation() {
  conversationId.value = crypto.randomUUID()
  messages.value = [{
    id: crypto.randomUUID(),
    role: 'assistant',
    content: `新的${activeBusiness.value.noun}会话已创建。${activeBusiness.value.welcome}`,
    time: now(),
  }]
  input.value = ''
  sidebarOpen.value = false
}

function selectModule(module) {
  if (module.soon || selectedModule.value === module.key) return
  selectedModule.value = module.key
  conversationId.value = crypto.randomUUID()
  messages.value = [{
    id: crypto.randomUUID(),
    role: 'assistant',
    content: activeBusiness.value.welcome,
    time: now(),
  }]
  expandedTools.value = new Set()
  input.value = ''
  sidebarOpen.value = false
  scrollToBottom()
}

function now() {
  return new Intl.DateTimeFormat('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date())
}

async function scrollToBottom() {
  await nextTick()
  chatBody.value?.scrollTo({ top: chatBody.value.scrollHeight, behavior: 'smooth' })
}

function normalizeTools(tools = []) {
  return tools.map((tool, index) => ({
    id: tool.id || `tool-${Date.now()}-${index}`,
    name: tool.name || tool.tool_name || 'unknown_tool',
    server: tool.server || '物流业务 MCP Server',
    duration: tool.duration || (tool.duration_ms ? `${tool.duration_ms} ms` : '—'),
    status: tool.status || 'success',
    args: tool.args || tool.arguments || {},
    result: tool.result || tool.output || {},
  }))
}

function mockReply(question) {
  if (/对账单/.test(question)) {
    const billNum = question.match(/[A-Z]{2,}\d{6,}/i)?.[0]?.toUpperCase()
    if (!billNum) {
      return {
        answer: '请提供需要查询的对账单号，我会根据对账单号查询当前状态。',
        tools: [],
        demo: true,
      }
    }
    return {
      answer: `对账单 **${billNum}** 当前处于「新建」状态。`,
      tools: [{
        name: 'get_reconciliation_bill_detail',
        server: '物流业务 MCP Server',
        duration_ms: 224,
        status: 'success',
        arguments: { bill_num: billNum },
        result: { bill_num: billNum, status: 100, status_text: '新建' },
      }],
      demo: true,
    }
  }

  if (selectedModule.value === 'finance' || /付款单|财务/.test(question)) {
    const voucherNum = question.match(/[A-Z]{2,}\d{6,}/i)?.[0]?.toUpperCase()
    if (!voucherNum) {
      return {
        answer: '请提供需要查询的付款单号，我会根据付款单号查询当前状态。',
        tools: [],
        demo: true,
      }
    }
    return {
      answer: `付款单 **${voucherNum}** 当前处于「新建」状态。`,
      tools: [{
        name: 'get_payment_voucher_detail',
        server: '物流业务 MCP Server',
        duration_ms: 228,
        status: 'success',
        arguments: { voucher_num: voucherNum },
        result: { voucher_num: voucherNum, status: 100, status_text: '新建' },
      }],
      demo: true,
    }
  }

  if (selectedModule.value === 'shipment' || /提单/.test(question)) {
    const shipmentNo = question.match(/[A-Z]{2,}\d{6,}/i)?.[0]?.toUpperCase()
    if (!shipmentNo) {
      return {
        answer: '请提供需要查询的提单号，我会根据提单号查询当前状态。',
        tools: [],
        demo: true,
      }
    }
    return {
      answer: `提单 **${shipmentNo}** 当前处于「待绑干线」状态。`,
      tools: [{
        name: 'get_shipment_detail',
        server: '物流业务 MCP Server',
        duration_ms: 236,
        status: 'success',
        arguments: { shipment_no: shipmentNo },
        result: { shipment_no: shipmentNo, operating_status: 2, status_text: '待绑干线' },
      }],
      demo: true,
    }
  }

  const orderNo = question.match(/[A-Z]{2}\d{8,}/i)?.[0]?.toUpperCase() || 'OD202410180026'
  const wantsDetail = /详情|完整|信息|金额|地址/.test(question)
  const toolName = wantsDetail ? 'get_order_detail' : 'get_order_status'
  return {
    answer: wantsDetail
      ? `已找到订单 **${orderNo}**。该订单从上海发往深圳，共 12 件、总重 286 kg，承运商为华运物流。当前处于「运输中」，预计 10 月 22 日送达。`
      : `订单 **${orderNo}** 当前处于「运输中」状态。货物正在前往深圳中转中心，预计 10 月 22 日到达，目前暂无异常。`,
    tools: [{
      name: toolName,
      server: '物流业务 MCP Server',
      duration_ms: 241,
      status: 'success',
      arguments: { order_no: orderNo },
      result: wantsDetail
        ? { order_no: orderNo, origin: '上海', destination: '深圳', pieces: 12, weight_kg: 286, status: 'in_transit' }
        : { order_no: orderNo, status: 'in_transit', status_text: '运输中', eta: '2024-10-22' },
    }],
    demo: true,
  }
}

async function sendMessage(text = input.value) {
  const question = text.trim()
  if (!question || isSending.value) return

  messages.value.push({ id: crypto.randomUUID(), role: 'user', content: question, time: now() })
  input.value = ''
  isSending.value = true
  sidebarOpen.value = false
  await scrollToBottom()

  let data
  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: question, conversation_id: conversationId.value }),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    data = await response.json()
  } catch {
    await new Promise((resolve) => setTimeout(resolve, 900))
    data = mockReply(question)
  }

  const tools = normalizeTools(data.tools || data.tool_calls)
  messages.value.push({
    id: crypto.randomUUID(),
    role: 'assistant',
    content: data.answer || data.message || '查询完成，但服务没有返回可展示的文本。',
    time: now(),
    tools,
    demo: data.demo,
  })
  tools.forEach((tool) => expandedTools.value.add(tool.id))
  isSending.value = false
  scrollToBottom()
}

function handleKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
}
</script>

<template>
  <div class="app-shell">
    <div v-if="sidebarOpen" class="mobile-overlay" @click="sidebarOpen = false" />

    <aside class="sidebar" :class="{ open: sidebarOpen }">
      <div class="brand-row">
        <div class="brand-mark"><Sparkles :size="19" stroke-width="2.2" /></div>
        <div class="brand-copy">
          <strong>运智</strong>
          <span>LOGISTICS AI</span>
        </div>
        <button class="icon-button close-mobile" aria-label="关闭侧栏" @click="sidebarOpen = false"><X :size="19" /></button>
      </div>

      <button class="new-chat" @click="newConversation">
        <Plus :size="18" />
        <span>新建会话</span>
      </button>

      <div class="sidebar-section">
        <p class="section-label">业务模块</p>
        <button
          v-for="module in modules"
          :key="module.key"
          class="module-item"
          :class="{ active: selectedModule === module.key, disabled: module.soon }"
          :disabled="module.soon"
          @click="selectModule(module)"
        >
          <component :is="module.icon" :size="18" />
          <span>{{ module.label }}</span>
          <span v-if="module.soon" class="soon">即将上线</span>
        </button>
      </div>

      <div class="sidebar-section history-section">
        <p class="section-label">最近会话</p>
        <button v-for="session in sessions" :key="session.id" class="session-item" :class="{ active: session.active }">
          <MessageSquareText :size="17" />
          <span class="session-copy">
            <span>{{ session.title }}</span>
            <small>{{ session.time }}</small>
          </span>
          <MoreHorizontal class="session-more" :size="17" />
        </button>
      </div>

      <div class="profile-card">
        <div class="avatar"><UserRound :size="17" /></div>
        <div><strong>演示用户</strong><span>运营管理</span></div>
        <MoreHorizontal :size="18" />
      </div>
    </aside>

    <main class="main-panel">
      <header class="topbar">
        <button class="icon-button menu-button" aria-label="打开菜单" @click="sidebarOpen = true"><Menu :size="21" /></button>
        <div class="conversation-title">
          <span class="title-icon"><component :is="activeBusiness.icon" :size="18" /></span>
          <div><h1>{{ activeBusiness.title }}</h1><p><span class="online-dot" /> 服务正常</p></div>
        </div>
        <div class="topbar-actions">
          <button class="search-button" aria-label="搜索"><Search :size="19" /></button>
          <button class="environment"><span class="env-dot" />开发环境<ChevronDown :size="15" /></button>
        </div>
      </header>

      <section ref="chatBody" class="chat-body">
        <div class="day-divider"><span>今天</span></div>

        <div v-for="message in messages" :key="message.id" class="message-row" :class="message.role">
          <div v-if="message.role === 'assistant'" class="assistant-avatar"><Bot :size="19" /></div>
          <div class="message-stack">
            <div class="message-meta">
              <strong>{{ message.role === 'assistant' ? '运智助手' : '你' }}</strong>
              <span>{{ message.time }}</span>
              <span v-if="message.demo" class="demo-tag">演示数据</span>
            </div>
            <div class="message-bubble" v-html="formatContent(message.content)" />

            <div v-if="message.tools?.length" class="tool-list">
              <div v-for="tool in message.tools" :key="tool.id" class="tool-card">
                <button class="tool-summary" @click="toggleTool(tool.id)">
                  <span class="tool-badge"><LayoutGrid :size="16" /></span>
                  <span class="tool-info">
                    <span class="tool-heading"><span>调用工具</span><code>{{ tool.name }}</code></span>
                    <small>{{ tool.server }} · {{ tool.duration }}</small>
                  </span>
                  <span class="tool-success"><span />调用成功</span>
                  <ChevronDown v-if="expandedTools.has(tool.id)" :size="17" />
                  <ChevronRight v-else :size="17" />
                </button>
                <div v-if="expandedTools.has(tool.id)" class="tool-detail">
                  <div><span>请求参数</span><pre>{{ JSON.stringify(tool.args, null, 2) }}</pre></div>
                  <div><span>返回结果</span><pre>{{ JSON.stringify(tool.result, null, 2) }}</pre></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="isSending" class="message-row assistant loading-row">
          <div class="assistant-avatar"><Bot :size="19" /></div>
          <div class="thinking"><i /><i /><i /><span>正在分析并查询{{ activeBusiness.noun }}...</span></div>
        </div>
      </section>

      <footer class="composer-area">
        <div class="suggestions">
          <button v-for="item in suggestions" :key="item.title" @click="sendMessage(item.text)">
            <component :is="item.icon" :size="16" />
            <span>{{ item.title }}</span>
          </button>
        </div>
        <div class="composer" :class="{ focused: input }">
          <textarea v-model="input" rows="1" :placeholder="activeBusiness.placeholder" @keydown="handleKeydown" />
          <div class="composer-bottom">
            <span><Sparkles :size="14" /> AI 可能会调用业务工具获取实时数据</span>
            <button class="send-button" :disabled="!canSend" aria-label="发送消息" @click="sendMessage()"><ArrowUp :size="19" /></button>
          </div>
        </div>
        <p class="disclaimer">AI 生成内容仅供参考，业务数据以系统实际记录为准</p>
      </footer>
    </main>
  </div>
</template>
