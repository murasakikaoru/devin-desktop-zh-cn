// Devin Desktop 中文翻译层 — 注入到 workbench 主文档及各 webview
// 依赖注入前设置的全局变量: window.__ZH_DICT__ (en->zh 精确匹配), window.__ZH_REGEX__ ([[patternSrc, replacement],...])
(function () {
	'use strict';
	if (window.__devinZhLoaded) return;
	window.__devinZhLoaded = true;
	const VERSION = '0.1.3';
	window.__devinZhVersion = VERSION;

	const DICT = window.__ZH_DICT__ || {};
	const REGEX = (window.__ZH_REGEX__ || []).map(([p, r]) => {
		try { return [new RegExp(p), r]; } catch (e) { return null; }
	}).filter(Boolean);

	// 排除: 代码、用户输入区、会话正文(不翻 Agent/用户消息)、数据区(扩展商店/列表行)
	const TEXT_EXCLUDE =
		'script,style,code,pre,kbd,samp,textarea,' +
		'[contenteditable="true"],[contenteditable=""],' +
		'.monaco-editor,.monaco-diff-editor,.view-lines,' +
		// 对话界面: 整个 transcript 行不翻(消息/工具卡/审批/计划全在行内)
		'[data-transcript-row-key],[data-message-author],' +
		'[data-testid="transcript-agent-message"],[data-testid="transcript-user-message"],' +
		'[data-testid="transcript-initial-user-message"],[data-testid="transcript-plan-content"],' +
		'[data-testid="transcript-session-recap"],[data-testid="transcript-todo-steps"],' +
		'[data-testid="transcript-worklog-row"],' +
		// transcript 内的数据片段: 命令/输出、PR 标题、分支名
		'[data-testid="transcript-shell-card-command"],[data-testid="transcript-shell-card-output"],' +
		'[data-testid="transcript-shell-card-error"],[data-testid="transcript-shell-run-output"],' +
		'[data-testid="transcript-shell-expanded-command"],' +
		'[data-testid="transcript-tool-permission-command"],[data-testid="transcript-git-stack"],' +
		'[data-testid="transcript-pr-stack"],[data-testid="transcript-stack-member-state"],' +
		'[data-testid="transcript-status-completed-pr"],' +
		// Markdown/流式渲染容器、提示词输入编辑器
		'[class*="prose"],.markdown-body,[class*="markdown"],[class*="Markdown"],' +
		'[data-markdown],[data-streamdown],acp-markdown,.acp-markdown,[data-slate-editor],' +
		// 数据区: 扩展商店条目、monaco 列表行(文件名/搜索结果/提交信息/扩展名均为数据)
		'.extensions-viewlet,.extension-editor,.monaco-tl-row,.monaco-list-row,.monaco-hover,' +
		// 插件/MCP 市场卡片(名称/描述为远程数据): 可点击卡片网格项 + MCP 安装项
		'[class*="grid-cols-["] > [class*="cursor-pointer"],[id^="mcp-installation-"]';
	// 属性翻译与文本同一排除域(数据区的 title/aria-label 同样不翻)
	const ATTR_EXCLUDE = TEXT_EXCLUDE;
	const ATTRS = ['title', 'placeholder', 'aria-label', 'alt', 'data-tooltip-content', 'data-tooltip', 'label'];

	const SKIP_EXACT = new Set([
		'Devin', 'Cascade', 'Agent', 'Agents', 'Editor', 'VS Code', 'Slack', 'GitHub', 'Jira', 'Linear',
		'MCP', 'ACP', 'CLI', 'API', 'PR', 'IDE', 'DeepWiki', 'Codemap', 'Codemaps', 'Lifeguard',
		'Space', 'Spaces', 'Worktree', 'SWE-1.7', 'SWE-2', 'Ultra', 'Lite'
	]);

	function translateCore(core) {
		if (DICT[core] !== undefined) return DICT[core];
		for (const [re, rep] of REGEX) {
			if (re.test(core)) return core.replace(re, rep);
		}
		return core;
	}

	function translateText(text) {
		if (!text || !text.trim()) return text;
		const lead = text.match(/^\s*/)[0];
		const trail = text.match(/\s*$/)[0];
		const core = text.trim();
		if (core.length < 2 && !DICT[core]) return text;
		if (SKIP_EXACT.has(core)) return text;
		const t = translateCore(core);
		return t === core ? text : lead + t + trail;
	}

	function shouldSkipNode(node) {
		const el = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
		if (!el) return true;
		return Boolean(el.closest(TEXT_EXCLUDE));
	}

	function translateTextNode(node) {
		if (shouldSkipNode(node)) return;
		const v = node.nodeValue;
		const t = translateText(v);
		if (t !== v) node.nodeValue = t;
	}

	function translateAttrs(el) {
		if (el.closest && el.closest(ATTR_EXCLUDE)) return;
		for (const a of ATTRS) {
			const v = el.getAttribute && el.getAttribute(a);
			if (!v) continue;
			const t = translateText(v);
			if (t !== v) el.setAttribute(a, t);
		}
	}

	function scan(root) {
		if (!root) return;
		if (root.nodeType === Node.TEXT_NODE) { translateTextNode(root); return; }
		const el = root.nodeType === Node.ELEMENT_NODE || root.nodeType === Node.DOCUMENT_NODE ? root : document.body;
		if (!el || !el.querySelectorAll) return;
		if (el.nodeType === Node.ELEMENT_NODE) translateAttrs(el);
		for (const e of el.querySelectorAll(ATTRS.map(a => '[' + a + ']').join(','))) translateAttrs(e);
		const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
		let n; while ((n = walker.nextNode())) translateTextNode(n);
	}

	// Shadow DOM 兜底: 定期扫描所有 open shadowRoot
	function collectRoots(node, out) {
		out.push(node);
		const els = node.querySelectorAll ? node.querySelectorAll('*') : [];
		for (const e of els) if (e.shadowRoot) collectRoots(e.shadowRoot, out);
		return out;
	}

	let pending = new Set();
	let rafId = 0;
	let translating = false;
	function flush() {
		rafId = 0;
		translating = true;
		try { for (const r of pending) scan(r); } finally {
			pending.clear();
			setTimeout(() => {
				translating = false;
				// 翻译期间入队的变更(含 React 渲染)在此补扫
				if (pending.size && !rafId) rafId = requestAnimationFrame(flush);
			}, 0);
		}
	}
	function enqueue(root) {
		// 翻译进行中也要入队(不能丢变更), 等本轮扫完再补扫
		pending.add(root || document.body);
		if (!translating && !rafId) rafId = requestAnimationFrame(flush);
	}

	new MutationObserver((mutations) => {
		for (const m of mutations) {
			if (m.type === 'characterData') enqueue(m.target);
			else for (const n of m.addedNodes) enqueue(n);
		}
	}).observe(document.documentElement || document, {
		childList: true, subtree: true, characterData: true
	});

	// 页面/标签页重新可见时兜底全扫(修复首开页面漏翻)
	document.addEventListener('visibilitychange', () => {
		if (!document.hidden) enqueue(document.documentElement);
	});
	// 注入后延迟补扫: 覆盖正在异步挂载的 React 树
	setTimeout(() => enqueue(document.documentElement), 800);
	setTimeout(() => enqueue(document.documentElement), 2500);

	// 初次全量 + 周期性扫描 shadowRoot(低频,兜底 iframe 外的 shadow DOM)
	function fullScan() { for (const r of collectRoots(document.body || document.documentElement, [])) scan(r); }
	fullScan();
	setInterval(fullScan, 30000);

	console.log('[devin-zh] loaded v' + VERSION);
})();
