// 收集 Devin 设置页可见字符串(排除会话/终端/代码区)
(() => {
	const ei = document.querySelector('.editor-instance .chat-client-root');
	if (!ei) return 'NO_EI_ROOT';
	const EXC = '[data-transcript-row-key],[data-message-author],[class*="prose"],[class*="markdown"],[data-streamdown],acp-markdown,.monaco-tl-row,.monaco-list-row,.monaco-hover,[class*="grid-cols-["] > [class*="cursor-pointer"],.ansi-text,pre,code,[class*="mtk"],[data-slate-editor],[contenteditable]';
	const texts = new Set();
	const w = document.createTreeWalker(ei, NodeFilter.SHOW_TEXT);
	let n;
	while ((n = w.nextNode())) {
		const v = (n.nodeValue || '').trim();
		if (!v || v.length < 2 || !/[a-zA-Z]/.test(v)) continue;
		if (n.parentElement.closest(EXC)) continue;
		if (/[{}();=<>\\]/.test(v) || /^https?:|^C:\\|^cd |^python|^import|\.py\b|\.js\b/.test(v)) continue;
		texts.add(v);
	}
	ei.querySelectorAll('[placeholder],[aria-label],[title]').forEach(e => {
		for (const a of ['placeholder', 'aria-label', 'title']) {
			const v = (e.getAttribute(a) || '').trim();
			if (v && /[a-zA-Z]/.test(v) && v.length > 1) texts.add(v);
		}
	});
	return JSON.stringify(Array.from(texts).sort());
})()
