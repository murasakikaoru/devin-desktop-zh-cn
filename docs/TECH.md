# 技术细节与维护指南

## 架构

```
Devin-中文.bat（入口，自动探测）
   ├── find_devin.ps1        → Devin.exe 多层定位
   ├── setup.py              → ~/.devin/argv.json 写 locale: zh-cn + 安装语言包 vsix
   ├── inject.py             → 连 CDP 调试端口，向所有 page/webview target 注入 translator.js
   └── Devin.exe --remote-debugging-port=9222（经 WMI Win32_Process.Create 脱离控制台启动）

translator.js（页面内运行）
   ├── dict.json 精确匹配（text node / title / aria-label / placeholder）
   ├── regex 规则匹配动态文案（{{var}} 已编译为捕获组）
   ├── MutationObserver 补翻 React 后续渲染（rAF 批处理，翻译中变更不丢弃）
   ├── visibilitychange + 800ms/2500ms 延迟兜底重扫
   ├── 排除区域：Agent 对话 / Markdown / 商店 / 编辑器 / 数据列表
   └── 每 30s + 窗口可见时经 React fiber api 桥触发 devin.updatePlanInfo（用量实时刷新）
```

## 关键设计决策

### 为什么不改安装文件
`product.json.checksums` 对 11 个核心 bundle 做完整性校验，改文件启动弹「安装似乎损坏」。

### 为什么语言包走 argv.json 而非 --locale
实测 `argv.json` 的 `locale` 键有效（Devin 3.x 未过滤），但**运行中的 Devin 退出时会把内存配置回写 argv.json 覆盖它**——所以 setup.py 必须在 Devin 未运行（或将被强杀）时写入。bat 的顺序保证这点：setup → taskkill → 重启读 zh-cn。若手动改 argv.json 后正常关 Devin，locale 会丢。

### 为什么 Agent 界面必须 DOM 注入
Devin 打包的 i18next 资源表有 11223 条，但实际 `t()` 调用极少——绝大多数 Agent 界面文案硬编码在编译后的 JSX 里，资源替换无效，只能 DOM 替换。

### CDP 注入覆盖
`inject.py` 通过 `Target.setTargetInfo`/`Target.attachedToTarget`（flatten 会话模式）发现并注入：workbench 主页面、vscode-webview 面板。已知边界：`app.devin.ai` 的 OOPIF iframe target 对既有 target 不下发 attach 事件——设置页内嵌的远程「云设置」iframe 不在注入范围（其内容为远程产品界面，属有意不翻）。

### fiber api 桥（用量刷新）
`windsurf-chat-client` 把 `api` 对象（含 `executeCommand`、`windsurfSettingsPage`）挂在 React context 上。从 `.chat-client-root *` 任意 DOM 元素的 `__reactFiber$*` 向上遍历可在 `memoizedValue.api` 找到它。`executeCommand('devin.updatePlanInfo')` 无 UI 副作用，是官方刷新入口。

## 版本适配流程（Devin 升级后）

```bash
# 1. 提取新版字符串表（变量名每版混淆，scan_tables.py 自动找最大的 JSON.parse 表）
cd tools
DEVIN_BUNDLE="C:\...\index.js" python scan_tables.py webapp-en-<ver>.json

# 2. 提取 prop 字符串做新旧 diff
python scan_props.py <new-index.js> props-new.txt
python scan_props.py <old-index.js> props-old.txt
# diff 两份文件得到新增字符串

# 3. 检查词库覆盖（未命中 dict/regex 的列出）
python check_coverage.py <候选文件>

# 4. 补译：编辑 webapp-zh-*.json，然后
python build_dict.py   # 重新生成 ../dict.json
```

`build_dict.py` 细节：
- `{{count}}`/`{{seconds}}` 等数字占位符生成 `(\d[\d.,]*)`，非数字占位符生成 `(.+?)`
- 这是为了防 `{{count}}s` → `(.+?)s` 误吞所有 s 结尾单词（"Permissions"→"Permission 秒"事故）

## 翻译规范

- **保留英文**：Agent、Editor、subagents、模型名、产品名、Thinking Effort、技术/平台名
- **不翻数据**：对话正文（`[data-transcript-row-key]` 整行）、Markdown、扩展市场、代码、文件名
- `Agent` 用户明确要求保留英文（社区方案译作"智能体"，本项目不采用）

## 测试

`test/` 下是独立 HTML 测试页，用 `test-chrome.ps1` 起带调试端口的 Chrome 后，inject.py 会注入并验证：
- `test-page.html`：静态文案 + 排除区域
- `test-tick.html`：模拟 React nodeValue 周期更新（回归 v0.1.3 的突变丢失 bug）+ v0.1.5 新正则样例
