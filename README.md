# Devin Desktop 简体中文汉化（不改安装文件）

## 使用方法

**双击 `Devin-中文.bat`** —— 一键完成全部步骤：

1. 首次运行自动准备环境（`setup.py`，幂等）：
   - `~/.devin/argv.json` 写入 `"locale": "zh-cn"`
   - 若未安装语言包，调用 `Devin.exe --install-extension` 自动安装 vsix
2. 检测 Devin 运行状态——若已在运行但未开调试端口，提示关闭后以汉化模式重启（Electron 单实例机制下直接启动会丢调试参数）
3. 清理旧注入器后**完全隐藏**启动 `inject.py`（PowerShell `Start-Process -WindowStyle Hidden`，无任何常驻窗口，日志在 `%TEMP%\devin-zh-injector.log`）
4. 以 `--remote-debugging-port=9222` 启动 Devin

注入器发现 Devin 的页面/webview target 后自动注入翻译层；React 动态渲染内容由 MutationObserver 实时补翻。

> 直接正常启动 Devin 也完全没问题——只是 Agent 窗口保持英文，核心界面仍是中文（语言包生效）。

## 环境要求与可移植性

- **Windows + Python 3**（pythonw / python / py 启动器均可，需加入 PATH）
- **Devin Desktop**（`find_devin.ps1` 自动探测：常见安装目录 → 卸载注册表 → 运行中进程 → 开始菜单快捷方式 → PATH，覆盖 D/E 盘等任意安装位置；全失败时提示手动粘贴路径）
- 本目录**可放在任意路径**运行，无任何硬编码路径；不修改安装目录下任何文件

## 目录结构

```
Devin-ZH/
├── Devin-中文.bat                          # 一键启动器（自动探测 Devin/Python）
├── find_devin.ps1                          # Devin.exe 多层定位（注册表/进程/快捷方式）
├── setup.py                                # 首次运行：写 locale + 装语言包（幂等）
├── inject.py                               # CDP 注入器（内置 WS 客户端，零依赖）
├── translator.js                           # 注入页面的翻译引擎 v0.1.3
├── dict.json                               # 编译产物：2888 精确 + 583 正则
├── devin-language-pack-zh-hans-1.0.0.vsix  # 语言包（setup.py 自动安装）
├── pack/                                   # 语言包源文件（vsix 打包用）
├── src/                                    # 维护用源码
│   ├── build_dict.py                       # 合并 webapp-zh-*.json -> ../dict.json
│   ├── extract_webapp.py                   # 从 Agent bundle 提取英文词典
│   ├── extract_settings.py                 # 提取设置页字符串
│   ├── verify_cdp.py                       # CDP 验证脚本
│   ├── probe_settings.js / probe_dom.js    # 设置页/DOM 探针
│   ├── webapp-zh-1..6.json                 # 人工翻译源文件（en -> zh），6 为 Devin 设置页
│   ├── webapp-en.json                      # 提取的完整英文词典（11222 条）
│   ├── webapp-visible-en.txt               # 可见字符串清单（3370 条）
│   ├── untranslated.txt                    # 剩余未翻（有意保留的英文）
│   ├── zh1/2/3.json                        # NLS 语言包翻译源（883 条 Devin 字符串）
│   ├── missing-strings.json / missing-flat.txt  # NLS 缺失分析
│   └── main.i18n.backup.json               # kiro 语言包备份
└── test/
    ├── test-page.html                      # 端到端验证测试页
    └── test-chrome.ps1                     # 测试 Chrome 启动脚本
```

## 两层覆盖

| 层 | 方案 | 覆盖 |
|---|---|---|
| 核心 workbench + Devin NLS | 语言包扩展（`devin-zh.devin-language-pack-zh-hans`） | 菜单、编辑器、设置、Devin 命令等 21000+ 条 |
| Agent 窗口（React webapp） | CDP 运行时注入 `translator.js` | 输入框、按钮、状态、Devin 设置页（计划/用量/扩展/Agents/配置/自定义项/编辑器/快捷键/高级 全分区）等 3400+ 条 |

## 保留英文

Agent、Editor、模型名（SWE-1.7、GPT-6 Astra、Opus 等）、产品名（DeepWiki、Codemap、Lifeguard、Cascade、Devin）、Thinking Effort、环境变量示例、平台名、远程数据（第三方 Agent/插件名称与描述）。

## 不翻译的区域

以下区域即使文本命中词典也保持原文，属于"数据"而非界面：

- **整个 Agent 对话界面**：`[data-transcript-row-key]` —— 会话流中的每一行（消息、工具卡、审批、计划、shell 输出、PR/分支信息等）整行不翻；`[data-message-author]`、各 `transcript-*-message` / `transcript-plan-content` 等 testid 作为行外兜底
- **Markdown/流式渲染**：`[class*="prose"]`、`[data-streamdown]`、`acp-markdown`、`[data-markdown]`、`[data-slate-editor]`
- **扩展商店**：`.extensions-viewlet`（侧栏列表）、`.extension-editor`（详情页）——扩展名/描述是远程数据
- **插件/MCP 市场卡片**：`[class*="grid-cols-["] > [class*="cursor-pointer"]`、`[id^="mcp-installation-"]` —— 名称/描述是远程数据
- **数据列表**：`.monaco-tl-row` / `.monaco-list-row` / `.monaco-hover` —— 文件名、搜索结果、提交信息、断点等

另外 `build_dict.py` 中数字型占位符（`{{count}}`、`{{seconds}}` 等）生成 `(\d[\d.,]*)` 而非 `(.+?)`，避免 `{{count}}s` 误吞一切 s 结尾的词（如 "Permissions"→"Permission 秒"）。

会话区域之外的 UI（输入框、按钮、状态栏、设置页）仍会翻译。

## 更新日志

- **v0.1.3**：修复 MutationObserver 在翻译进行中丢弃 DOM 变更导致的"页面首开显示英文、切换后才翻译"问题；增加 visibilitychange 兜底重扫与注入后延迟补扫；移除 `{{model}} via {{modelProvider}}` 过宽正则（误翻远程 agent 描述）；新增 Devin 设置页全量翻译。启动器：注入器改为完全无窗口启动；检测 Devin 未开调试端口运行时自动提示重启；自动清理重复注入器
- **v0.1.2**：整行排除 `[data-transcript-row-key]`；数字型占位符修复"秒"后缀误翻；市场卡片排除
- **v0.1.1**：消息正文/Markdown/扩展商店/列表行排除
- **v0.1.0**：初版

## 维护

- **补翻译**：在 `src/webapp-zh-*.json` 加条目 → `cd src && python build_dict.py` → 重启注入器生效
- **Devin 更新后**：语言包不受影响；Agent 新字符串用 `extract_webapp.py` 重新提取后走同样流程
- **注入器参数**：`python inject.py --port 9222`（改端口需同步改 bat 中 Devin 的启动参数）
- 注入器不修改 `%LOCALAPPDATA%\Programs\Devin` 下任何文件
