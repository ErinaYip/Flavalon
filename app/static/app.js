document.addEventListener('DOMContentLoaded', () => {
    // === 0. 主题模式切换 ===
    const themeToggleBtn = document.getElementById('theme-toggle-btn');

    const savedTheme = localStorage.getItem('flavalon_theme') || 'light';
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-theme');
        themeToggleBtn.innerHTML = '☀️ 切换主题';
    }

    themeToggleBtn.addEventListener('click', () => {
        document.body.classList.toggle('dark-theme');
        const isDark = document.body.classList.contains('dark-theme');
        localStorage.setItem('flavalon_theme', isDark ? 'dark' : 'light');
        themeToggleBtn.innerHTML = isDark ? '☀️ 切换主题' : '🌙 切换主题';
    });

    // === 1. 时间与日期 ===
    const timeEl = document.getElementById('current-time');
    const dateEl = document.getElementById('current-date');

    function updateTime() {
        const now = new Date();
        timeEl.textContent = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        dateEl.textContent = now.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' });
    }
    setInterval(updateTime, 1000);
    updateTime();

    // === 2. 天气获取 (基于 Open-Meteo API，无需 Key) ===
    const weatherInfoEl = document.getElementById('weather-info');
    const weatherIconEl = document.getElementById('weather-icon');
    const cityInfoEl = document.getElementById('city-info');
    const getWeatherBtn = document.getElementById('get-weather-btn');

    const weatherCodes = {
        0: '☀️', 1: '🌤️', 2: '⛅', 3: '☁️',
        45: '🌫️', 48: '🌫️',
        51: '🌧️', 53: '🌧️', 55: '🌧️',
        61: '☔', 63: '☔', 65: '☔',
        71: '❄️', 73: '❄️', 75: '❄️',
        95: '⛈️', 96: '⛈️', 99: '⛈️'
    };

    async function fetchWeather(lat, lon, savedCity = null) {
        try {
            weatherInfoEl.textContent = '获取中...';
            cityInfoEl.textContent = savedCity || '解析位置中...';

            const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current_weather=true`;
            const res = await fetch(url);
            const data = await res.json();
            const current = data.current_weather;

            weatherInfoEl.textContent = `${current.temperature}°C`;
            weatherIconEl.textContent = weatherCodes[current.weathercode] || '🌡️';

            let cityName = savedCity;
            if (!cityName) {
                try {
                    const geoRes = await fetch(`https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${lat}&longitude=${lon}&localityLanguage=zh`);
                    const geoData = await geoRes.json();
                    cityName = geoData.city || geoData.locality || geoData.principalSubdivision || '未知位置';
                } catch (e) {
                    cityName = '未知位置';
                }
                cityInfoEl.textContent = cityName;
            }

            localStorage.setItem('flavalon_location', JSON.stringify({ lat, lon, city: cityName }));
        } catch (error) {
            weatherInfoEl.textContent = '获取失败';
        }
    }

    getWeatherBtn.addEventListener('click', () => {
        if ('geolocation' in navigator) {
            weatherInfoEl.textContent = '定位中...';
            navigator.geolocation.getCurrentPosition(
                (pos) => fetchWeather(pos.coords.latitude, pos.coords.longitude),
                () => { weatherInfoEl.textContent = '定位失败/授权被拒绝'; }
            );
        } else {
            weatherInfoEl.textContent = '浏览器不支持定位';
        }
    });

    const savedLocation = JSON.parse(localStorage.getItem('flavalon_location') || 'null');
    if (savedLocation && savedLocation.lat && savedLocation.lon) {
        fetchWeather(savedLocation.lat, savedLocation.lon, savedLocation.city);
    }

    // === 通用请求封装 ===
    async function api(path, options = {}) {
        const opts = Object.assign({ headers: { 'Content-Type': 'application/json' } }, options);
        if (opts.body && typeof opts.body !== 'string') opts.body = JSON.stringify(opts.body);
        const res = await fetch(path, opts);
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        const ct = res.headers.get('content-type') || '';
        return ct.includes('application/json') ? res.json() : null;
    }

    // === 3. 待办事项 ===
    const todoInput = document.getElementById('todo-input');
    const addBtn = document.getElementById('add-todo-btn');
    const todoList = document.getElementById('todo-list');
    let todos = [];
    let isTodoExpanded = false;

    function getTodayString() {
        const d = new Date();
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    }

    function renderTodos() {
        todoList.innerHTML = '';
        const today = getTodayString();

        const display = todos
            .map((todo, index) => ({ todo, index }))
            .filter(({ todo }) => !todo.completed || (todo.completed_at || '').startsWith(today));

        display.sort((a, b) => (a.todo.completed === b.todo.completed ? 0 : a.todo.completed ? 1 : -1));

        const limit = isTodoExpanded ? display.length : 5;
        const paged = display.slice(0, Math.min(limit, display.length));

        paged.forEach(({ todo, index: originalIndex }) => {
            const li = document.createElement('li');
            li.className = `todo-item ${todo.completed ? 'completed' : ''}`;

            const created = (todo.created_at || '').slice(0, 10);
            const completed = todo.completed ? ' | 完成于: ' + (todo.completed_at || '').slice(0, 10) : '';

            const content = document.createElement('div');
            content.className = 'todo-content';
            content.style.width = '100%';

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.checked = !!todo.completed;
            checkbox.addEventListener('click', (e) => {
                e.stopPropagation();
                toggleTodo(originalIndex);
            });

            const col = document.createElement('div');
            col.style.display = 'flex';
            col.style.flexDirection = 'column';

            const span = document.createElement('span');
            span.textContent = todo.text;
            col.appendChild(span);

            const dates = document.createElement('div');
            dates.className = 'todo-dates';
            dates.textContent = `创建于: ${created}${completed}`;
            col.appendChild(dates);

            content.appendChild(checkbox);
            content.appendChild(col);
            content.addEventListener('click', () => toggleTodo(originalIndex));

            const del = document.createElement('button');
            del.className = 'delete-btn';
            del.style.flexShrink = '0';
            del.textContent = '删除';
            del.addEventListener('click', (e) => {
                e.stopPropagation();
                deleteTodo(originalIndex);
            });

            li.appendChild(content);
            li.appendChild(del);
            todoList.appendChild(li);
        });

        const oldToggleBtn = document.getElementById('todo-toggle-btn');
        if (oldToggleBtn) oldToggleBtn.remove();

        if (display.length > 5) {
            const toggleBtn = document.createElement('button');
            toggleBtn.id = 'todo-toggle-btn';
            toggleBtn.className = 'icon-btn todo-toggle-btn';
            toggleBtn.textContent = isTodoExpanded ? '折叠列表 ▴' : `展开余下 ${display.length - 5} 项 ▾`;
            toggleBtn.addEventListener('click', () => {
                isTodoExpanded = !isTodoExpanded;
                renderTodos();
            });
            todoList.parentNode.insertBefore(toggleBtn, todoList.nextSibling);
        }

        renderCalendar();
    }

    async function loadTodos() {
        try {
            todos = await api('/api/todos');
        } catch (e) {
            todos = [];
        }
        renderTodos();
    }

    async function toggleTodo(index) {
        const todo = todos[index];
        if (!todo) return;
        const updated = await api(`/api/todos/${todo.id}/toggle`, { method: 'POST' });
        todos[index] = updated;
        renderTodos();
    }

    async function deleteTodo(index) {
        const todo = todos[index];
        if (!todo) return;
        await api(`/api/todos/${todo.id}`, { method: 'DELETE' });
        todos.splice(index, 1);
        renderTodos();
    }

    async function addTodo() {
        const text = todoInput.value.trim();
        if (!text) return;
        const created = await api('/api/todos', { method: 'POST', body: { text } });
        todos.unshift(created);
        todoInput.value = '';
        renderTodos();
    }

    addBtn.addEventListener('click', addTodo);
    todoInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') addTodo();
    });

    // === 4. 每日小记与日历 ===
    const notesEl = document.getElementById('daily-notes');
    const previewEl = document.getElementById('notes-preview');
    const togglePreviewBtn = document.getElementById('toggle-preview-btn');
    const statusEl = document.getElementById('save-status');
    const clearNotesBtn = document.getElementById('clear-notes-btn');
    const notesHintEl = document.getElementById('notes-hint');
    const mdToolbar = document.getElementById('md-toolbar');

    let isPreviewMode = false;

    function formatDateString(dateObj) {
        const y = dateObj.getFullYear();
        const m = String(dateObj.getMonth() + 1).padStart(2, '0');
        const d = String(dateObj.getDate()).padStart(2, '0');
        return `${y}-${m}-${d}`;
    }

    const baseDate = new Date();
    let currentCalMonth = baseDate.getMonth();
    let currentCalYear = baseDate.getFullYear();
    let selectedDateStr = formatDateString(baseDate);
    const todayStr = selectedDateStr;

    function setPreviewMode(mode) {
        isPreviewMode = mode;
        if (isPreviewMode) {
            notesEl.style.display = 'none';
            mdToolbar.style.opacity = '0.5';
            mdToolbar.style.pointerEvents = 'none';
            previewEl.style.display = 'block';
            togglePreviewBtn.textContent = '编辑';
            updateMarkdownPreview();
        } else {
            previewEl.style.display = 'none';
            mdToolbar.style.opacity = '1';
            mdToolbar.style.pointerEvents = 'auto';
            notesEl.style.display = 'block';
            togglePreviewBtn.textContent = '预览';
            notesEl.focus();
        }
    }

    async function loadNotesForSelectedDate() {
        let content = '';
        try {
            const data = await api(`/api/notes/${selectedDateStr}`);
            content = data.content;
        } catch (e) {
            content = '';
        }
        notesEl.value = content;

        if (selectedDateStr === todayStr) {
            notesHintEl.textContent = '写下今天的感悟吧，数据会自动保存在本地。';
            setPreviewMode(false);
        } else {
            notesHintEl.textContent = `查看历史：${selectedDateStr} 的小记`;
            setPreviewMode(true);
        }
    }

    function updateMarkdownPreview() {
        previewEl.innerHTML = marked.parse(notesEl.value || '*(暂无内容)*');
    }

    const toolbarBtns = document.querySelectorAll('.toolbar-btn');
    toolbarBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            if (isPreviewMode) return;
            const prefix = (btn.getAttribute('data-prefix') || '').replace(/\\n/g, '\n');
            const suffix = (btn.getAttribute('data-suffix') || '').replace(/\\n/g, '\n');

            let start = notesEl.selectionStart;
            let end = notesEl.selectionEnd;
            const text = notesEl.value;

            let before = text.substring(0, start);
            let selected = text.substring(start, end);
            let after = text.substring(end);

            const isInside = selected.startsWith(prefix) && (suffix === '' || selected.endsWith(suffix));
            const isOutside = before.endsWith(prefix) && (suffix === '' || after.startsWith(suffix));

            if (isInside && prefix !== '') {
                selected = selected.substring(prefix.length, selected.length - suffix.length);
                notesEl.value = before + selected + after;
                end = start + selected.length;
            } else if (isOutside && prefix !== '') {
                before = before.substring(0, before.length - prefix.length);
                after = after.substring(suffix.length);
                notesEl.value = before + selected + after;
                start = before.length;
                end = start + selected.length;
            } else {
                notesEl.value = before + prefix + selected + suffix + after;
                start = before.length + prefix.length;
                end = start + selected.length;
            }

            notesEl.focus();
            notesEl.setSelectionRange(start, end);
            notesEl.dispatchEvent(new Event('input'));
        });
    });

    togglePreviewBtn.addEventListener('click', () => setPreviewMode(!isPreviewMode));

    const calDaysEl = document.getElementById('calendar-days');
    const calHeaderEl = document.getElementById('calendar-month-year');
    let noteDates = new Set();

    function renderCalendar() {
        calDaysEl.innerHTML = '';
        calHeaderEl.textContent = `${currentCalYear}年 ${currentCalMonth + 1}月`;

        const firstDayObj = new Date(currentCalYear, currentCalMonth, 1);
        const daysInMonth = new Date(currentCalYear, currentCalMonth + 1, 0).getDate();
        const firstDayIdx = firstDayObj.getDay();
        const daysInPrevMonth = new Date(currentCalYear, currentCalMonth, 0).getDate();

        for (let i = firstDayIdx - 1; i >= 0; i--) {
            const d = daysInPrevMonth - i;
            const dateStr = formatDateString(new Date(currentCalYear, currentCalMonth - 1, d));
            calDaysEl.appendChild(createDayElement(d, 'other-month', dateStr));
        }
        for (let i = 1; i <= daysInMonth; i++) {
            const dateStr = formatDateString(new Date(currentCalYear, currentCalMonth, i));
            calDaysEl.appendChild(createDayElement(i, 'current-month', dateStr));
        }
        const totalRendered = firstDayIdx + daysInMonth;
        const nextDays = 42 - totalRendered;
        for (let i = 1; i <= nextDays; i++) {
            const dateStr = formatDateString(new Date(currentCalYear, currentCalMonth + 1, i));
            calDaysEl.appendChild(createDayElement(i, 'other-month', dateStr));
        }
    }

    function createDayElement(dayNum, extraClass, dateStr) {
        const el = document.createElement('div');
        el.className = `calendar-day ${extraClass}`;
        el.textContent = dayNum;

        if (dateStr === selectedDateStr) el.classList.add('selected');
        if (noteDates.has(dateStr)) el.classList.add('has-notes');
        if (todos.some(t => (t.created_at || '').slice(0, 10) === dateStr && !t.completed)) {
            el.classList.add('has-todos');
        }

        el.addEventListener('click', () => {
            selectedDateStr = dateStr;
            renderCalendar();
            loadNotesForSelectedDate();
        });
        return el;
    }

    document.getElementById('prev-month').addEventListener('click', () => {
        currentCalMonth--;
        if (currentCalMonth < 0) { currentCalMonth = 11; currentCalYear--; }
        renderCalendar();
    });
    document.getElementById('next-month').addEventListener('click', () => {
        currentCalMonth++;
        if (currentCalMonth > 11) { currentCalMonth = 0; currentCalYear++; }
        renderCalendar();
    });

    let saveTimeout;
    notesEl.addEventListener('input', () => {
        clearTimeout(saveTimeout);
        statusEl.style.opacity = 0;
        saveTimeout = setTimeout(async () => {
            const content = notesEl.value;
            await api(`/api/notes/${selectedDateStr}`, { method: 'PUT', body: { content } });
            statusEl.textContent = '已自动保存于 ' + new Date().toLocaleTimeString('zh-CN');
            statusEl.style.opacity = 1;
            await refreshNoteDates();
            renderCalendar();
        }, 1000);
    });

    clearNotesBtn.addEventListener('click', async () => {
        if (confirm(`确定要清空 ${selectedDateStr} 的笔记吗？`)) {
            notesEl.value = '';
            await api(`/api/notes/${selectedDateStr}`, { method: 'PUT', body: { content: '' } });
            if (isPreviewMode) updateMarkdownPreview();
            statusEl.textContent = '已清空';
            statusEl.style.opacity = 1;
            await refreshNoteDates();
            renderCalendar();
        }
    });

    async function refreshNoteDates() {
        try {
            noteDates = new Set(await api('/api/notes'));
        } catch (e) {
            noteDates = new Set();
        }
    }

    // === 6. 数据管理（导出 / 导入）===
    function downloadFile(filename, content, type) {
        const blob = new Blob([content], { type });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    document.getElementById('export-json-btn').addEventListener('click', async () => {
        const data = await api('/api/export');
        downloadFile(`flavalon_backup_${formatDateString(new Date())}.json`, JSON.stringify(data, null, 2), 'application/json');
    });

    document.getElementById('export-day-md-btn').addEventListener('click', () => {
        const content = notesEl.value;
        if (!content.trim()) {
            alert('当前日期没有记录内容哦，写点什么再导出吧！');
            return;
        }
        let md = content;
        if (!md.startsWith(`# ${selectedDateStr}`)) md = `# ${selectedDateStr}\n\n` + md;
        downloadFile(`note_${selectedDateStr}.md`, md, 'text/markdown');
    });

    document.getElementById('export-all-md-btn').addEventListener('click', async () => {
        const dates = Array.from(noteDates).sort((a, b) => b.localeCompare(a));
        if (dates.length === 0) {
            alert('你还没有记录过任何小记哦！');
            return;
        }
        let merged = `# Flavalon 全部小记汇总\n\n导出时间：${formatDateString(new Date())}\n\n`;
        for (const d of dates) {
            const note = await api(`/api/notes/${d}`);
            let c = note.content;
            if (c.startsWith(`# ${d}`)) c = c.replace(`# ${d}`, `## ${d}`);
            else c = `## ${d}\n\n` + c;
            merged += `---\n\n${c}\n\n`;
        }
        downloadFile(`all_notes_${formatDateString(new Date())}.md`, merged, 'text/markdown');
    });

    const tabExport = document.getElementById('tab-export');
    const tabImport = document.getElementById('tab-import');
    const exportPanel = document.getElementById('export-panel');
    const importPanel = document.getElementById('import-panel');

    tabExport.addEventListener('click', () => {
        tabExport.classList.add('active');
        tabImport.classList.remove('active');
        exportPanel.style.display = 'flex';
        importPanel.style.display = 'none';
    });
    tabImport.addEventListener('click', () => {
        tabImport.classList.add('active');
        tabExport.classList.remove('active');
        importPanel.style.display = 'flex';
        exportPanel.style.display = 'none';
    });

    document.getElementById('import-btn').addEventListener('click', () => {
        const fileInput = document.getElementById('import-file');
        const file = fileInput.files[0];
        if (!file) {
            alert('请先选择一个 Flavalon 的 .json 备份文件！');
            return;
        }
        if (!confirm('警告：导入备份将完全覆盖当前浏览器里的待办、日记和所有设置！确认继续吗？')) return;

        const reader = new FileReader();
        reader.onload = async (e) => {
            try {
                const data = JSON.parse(e.target.result);
                await api('/api/import', { method: 'POST', body: data });
                alert('恢复备份成功！页面即将重新加载应用你的新数据。');
                location.reload();
            } catch (err) {
                alert('导入失败，文件格式可能已损坏或不是合法的 JSON 文件！');
                console.error(err);
            }
        };
        reader.readAsText(file);
    });

    // === 初始化 ===
    (async () => {
        await loadTodos();
        await refreshNoteDates();
        renderCalendar();
        await loadNotesForSelectedDate();
    })();
});
