# Devin Desktop 简体中文汉化（devin-desktop-zh-cn）

给 **Devin Desktop**（Cognition 的 AI 编程助手桌面端，VS Code / Windsurf 血统）做简体中文界面汉化。**不修改安装目录下任何文件**，通过「语言包 + CDP 运行时注入」两层方案实现，官方升级不受影响。

- 词库：**2888 条精确匹配 + 587 条正则规则**（动态文案）
- 已适配版本：Devin Desktop **3.10.48**（2026-09-29 构建，VS Code 内核 1.126.0）
- 覆盖：Agent 面板、会话界面控件、评审、自动化、安全、Devin 设置全分区（计划信息/用量/扩展/Agents/编辑器/快捷键等）、模型选择器、命令面板等

## 快速开始

### 环境要求

- Windows 10/11
- **Python 3**（`pythonw`/`python`/`py` 任一可用，需在 PATH 中）
- Devin Desktop 已安装（**任意盘符/目录**，启动器自动探测）

### 使用

1. 双击 **`Devin-中文.bat`**
2. 脚本自动完成：写 `locale` → 安装语言包（首次）→ 清理旧注入器 → 隐藏启动注入器 → 以调试端口启动 Devin
3. 界面即显示中文，全程无常驻窗口（注入器完全隐藏运行，日志在 `%TEMP%\devin-zh-injector.log`）

> 若 Devin 已在运行但没带调试端口，启动器会提示确认后自动重启它——Electron 单实例机制下直接启动会丢失调试参数。
>
> **多安装共存**（如 `Program Files` 系统版 + `AppData` 用户版）：自动选最高版本；要强制指定某一份，先 `set DEVIN_EXE=D:\path\Devin.exe` 再运行 bat。
>
> 汉化后**关掉 bat 窗口不会影响 Devin**：Devin 由系统服务创建（WMI `Win32_Process.Create`），与 bat 控制台完全脱离。

### 卸载

- 直接正常启动 Devin（不经 bat）→ Agent 界面恢复英文，内核界面仍是中文
- 完全还原：删除 `%USERPROFILE%\.devin\argv.json` 中的 `"locale"` 键，扩展面板卸载 `devin-language-pack-zh-hans`，删除本目录

## 工作原理

### 为什么不能改文件

Devin 在 `product.json` 里维护了核心文件的**完整性校验**（`checksums`），改任何一个都会弹「安装似乎损坏」。所以本项目全程不碰安装文件，只在运行时注入。

### 两层覆盖

| 层 | 方案 | 覆盖 |
|---|---|---|
| ① VS Code 内核 | 自制语言包 `devin-language-pack-zh-hans`（argv.json `locale: zh-cn` 激活） | 菜单、编辑器、设置、通知等 21000+ 条 |
| ② Agent 界面 | `inject.py` 连 CDP（`--remote-debugging-port`）→ 注入 `translator.js` | React webapp 全部界面文案 |

`translator.js` 在页面内运行：词典精确匹配 + 正则处理动态文案 + 属性翻译（title/aria-label/placeholder）+ `MutationObserver` 实时补翻 React 后续渲染 + 可见性变化与延迟兜底重扫。

### 用量区实时刷新

Devin 官方没有设置页用量的周期刷新（仅启动/鉴权变化/打开计划面板/点刷新图标时更新）。translator.js 通过 chat-client 暴露给 React 树的 api 桥每 30 秒及窗口重新可见时触发官方 `devin.updatePlanInfo` 命令，用量区（每日/每周配额、额外余额、状态栏徽章）保持实时更新。

## 翻译范围

### 保留英文

`Agent`、`Editor`、模型名（SWE-2、Claude 等）、产品名（DeepWiki、Codemap、Lifeguard、Cascade、Devin）、Thinking Effort、subagents、技术术语、平台名。

### 不翻译的区域

以下属于**数据**而非界面，即使命中词典也保持原文：

- **Agent 对话区**：`[data-transcript-row-key]` 整行排除（消息、工具卡、审批、计划、shell 输出等模型生成内容）
- **Markdown/流式渲染**：`[class*="prose"]`、`[data-streamdown]`、`acp-markdown`、`[data-slate-editor]`
- **扩展商店**：`.extensions-viewlet`、`.extension-editor`（扩展名/描述是远程数据）
- **市场卡片**：MCP/插件市场条目（远程数据）
- **代码与终端**：`.monaco-editor`、`.view-lines`、`.xterm` 等
- **数据列表**：`.monaco-list-row` 等（文件名、搜索结果、提交信息）

## 目录结构

```
devin-desktop-zh-cn/
├── Devin-中文.bat                           # 一键启动器（自动探测 Devin/Python）
├── find_devin.ps1                           # Devin.exe 多层定位（注册表/进程/快捷方式，多安装共存选最新）
├── setup.py                                 # 首次准备：写 locale + 装语言包（幂等）
├── inject.py                                # CDP 注入器（内置 WebSocket，零依赖）
├── translator.js                            # 页面翻译引擎 v0.1.5
├── dict.json                                # 编译产物词库
├── devin-language-pack-zh-hans-1.0.0.vsix   # 自制语言包
├── pack/                                    # 语言包源文件（vsix 打包用）
├── tools/                                   # 维护工具链
│   ├── build_dict.py                        #   合并翻译源 -> dict.json
│   ├── extract_webapp.py / extract_settings.py  # 从 bundle 提取英文字符串
│   ├── scan_tables.py / scan_props.py / scan_literals.py  # 版本适配扫描器
│   ├── check_coverage.py                    #   词库覆盖率检查
│   ├── probe_*.js / verify_cdp.py           #   DOM/CDP 探针
│   ├── webapp-zh-*.json / zh*.json          #   人工翻译源文件
│   └── webapp-visible-en.txt                #   可见字符串清单
├── docs/
│   └── TECH.md                              # 技术细节与维护指南
```

## 补翻译 / 维护

- **发现漏翻**：把 `"English": "中文"` 加进 `tools/webapp-zh-*.json`，`cd tools && python build_dict.py` 重新生成 `dict.json`，重启注入器生效
- **Devin 升级后**：语言包不受影响；Agent 界面新字符串用 `tools/scan_props.py` 对比新旧 bundle，`tools/check_coverage.py` 查漏
- 注入器参数：`python inject.py --port 9222`（改端口需同步 bat 中启动参数）

## 隐私说明

- 本项目不修改 Devin 安装目录下任何文件，不含遥测，不联网上传任何数据
- 注入器仅连接本机 `127.0.0.1` 调试端口（端口仅在 bat 带参启动时开放）
- 词库内容全部来自 Devin 界面文案的提取与翻译

## 许可

MIT License — 见 [LICENSE](LICENSE)
