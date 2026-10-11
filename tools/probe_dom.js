(() => {
	const ei = document.querySelector('.editor-instance');
	if (!ei) return 'no ei';
	const out = [];
	// 1) ei 内是否有 iframe
	ei.querySelectorAll('iframe').forEach((f, i) => {
		let inside = 'n/a';
		try { inside = f.contentDocument ? (f.contentDocument.body.innerText.includes('Claude Agent') ? 'YES' : 'no') : 'null doc'; }
		catch (e) { inside = 'cross-origin'; }
		out.push('iframe' + i + ' src=' + String(f.src).slice(0, 70) + ' claude=' + inside);
	});
	// 2) ei.innerText 是否仍含 agent 列表
	out.push('ei.innerText has Claude Agent: ' + ei.innerText.includes('Claude Agent'));
	// 3) ei 内所有 shadow host
	const hosts = [];
	ei.querySelectorAll('*').forEach(e => { if (e.shadowRoot) hosts.push(e.tagName + '.' + String(e.className).slice(0, 50)); });
	out.push('shadow hosts in ei: ' + JSON.stringify(hosts.slice(0, 10)));
	return out.join('\n');
})()
