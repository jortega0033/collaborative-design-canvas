(function () {
  'use strict';

  var API = '/api/v1';
  var LAST_KEY = 'dc.lastProject';
  var MAX_LAYERS = 200;
  var FONT = 'system-ui, "Segoe UI", Roboto, Arial, sans-serif';

  function $(id) { return document.getElementById(id); }

  var el = {
    title: $('doc-title'),
    newCanvas: $('new-canvas'),
    fixture: $('load-fixture'),
    save: $('save'),
    reload: $('reload-server'),
    projectList: $('project-list'),
    meta: $('project-meta'),
    canvas: $('preview'),
    addRect: $('add-rect'),
    addText: $('add-text'),
    status: $('status'),
    layerList: $('layer-list'),
    up: $('layer-up'),
    down: $('layer-down'),
    del: $('layer-delete'),
    label: $('layer-label'),
    x: $('layer-x'),
    y: $('layer-y'),
    w: $('layer-w'),
    h: $('layer-h'),
    fill: $('layer-fill'),
    textFields: $('text-fields'),
    text: $('layer-text'),
    font: $('layer-font')
  };
  var ctx = el.canvas.getContext('2d');

  var state = {
    project: null,   // last server copy
    title: '',
    layers: [],
    selectedId: null,
    snapshot: '',
    conflict: null,
    busy: false,
    projects: []
  };

  function clone(v) { return JSON.parse(JSON.stringify(v)); }
  function snap() { return JSON.stringify([state.title.trim(), state.layers]); }
  function isDirty() { return !!state.project && snap() !== state.snapshot; }

  function setStatus(msg, kind) {
    el.status.textContent = msg;
    el.status.className = 'status ' + (kind || 'info');
  }

  function storeLast(id) {
    try {
      if (id === null) { localStorage.removeItem(LAST_KEY); } else { localStorage.setItem(LAST_KEY, String(id)); }
    } catch (e) { /* storage unavailable */ }
  }
  function readLast() {
    try { return localStorage.getItem(LAST_KEY); } catch (e) { return null; }
  }

  /* ---------- network ---------- */

  function api(method, path, body) {
    var opts = { method: method, headers: { 'Accept': 'application/json' }, cache: 'no-store' };
    if (body !== undefined) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    return fetch(API + path, opts).then(function (res) {
      return res.text().then(function (t) {
        var data = null;
        try { data = t ? JSON.parse(t) : null; } catch (e) { data = null; }
        return { ok: res.ok, status: res.status, data: data };
      });
    });
  }

  function errorText(r) {
    var e = r.data && r.data.error;
    if (!e) { return 'Request failed (HTTP ' + r.status + ').'; }
    var parts = [e.message || e.code || 'Request failed'];
    if (e.details && e.details.length) {
      parts = e.details.map(function (d) { return d.field + ': ' + d.message; });
      parts.unshift('Not saved.');
    }
    return parts.join(' ');
  }

  function unreachable() { setStatus('Server unreachable, edits kept', 'error'); }

  /* ---------- project list ---------- */

  function loadProjects() {
    return api('GET', '/projects').then(function (r) {
      if (!r.ok) { setStatus(errorText(r), 'error'); return; }
      state.projects = r.data.projects || [];
      renderProjects();
    }, unreachable);
  }

  function renderProjects() {
    el.projectList.textContent = '';
    if (!state.projects.length) {
      var e = document.createElement('li');
      e.className = 'list-empty';
      e.textContent = 'No canvases yet.';
      el.projectList.appendChild(e);
      return;
    }
    state.projects.forEach(function (p) {
      var li = document.createElement('li');
      var b = document.createElement('button');
      b.type = 'button';
      b.dataset.id = String(p.id);
      b.textContent = p.title + ' (' + p.layer_count + (p.layer_count === 1 ? ' layer, r' : ' layers, r') + p.revision + ')';
      if (state.project && state.project.id === p.id) { b.setAttribute('aria-current', 'true'); }
      li.appendChild(b);
      el.projectList.appendChild(li);
    });
  }

  function confirmDiscard() {
    return !isDirty() || window.confirm('Discard unsaved edits?');
  }

  function openProject(id) {
    return api('GET', '/projects/' + encodeURIComponent(id)).then(function (r) {
      if (r.ok) {
        applyProject(r.data, true);
        setStatus('Loaded "' + r.data.title + '" at revision ' + r.data.revision + '.', 'ok');
      } else {
        if (r.status === 404) { storeLast(null); loadProjects(); }
        setStatus(errorText(r), 'error');
      }
    }, unreachable);
  }

  function applyProject(p, resetSelection) {
    var prevSel = state.selectedId;
    state.project = p;
    state.title = p.title;
    state.layers = clone(p.layers);
    state.snapshot = snap();
    state.conflict = null;
    el.reload.hidden = true;
    el.title.value = p.title;
    var ids = state.layers.map(function (l) { return l.id; });
    if (resetSelection || ids.indexOf(prevSel) < 0) {
      state.selectedId = ids.length ? ids[ids.length - 1] : null;
    }
    storeLast(p.id);
    renderProjects();
    renderAll();
  }

  /* ---------- actions ---------- */

  function createProject(fixture) {
    var title = el.title.value.trim();
    if (!title) {
      setStatus('Enter a document title first.', 'error');
      el.title.focus();
      return;
    }
    // The title field doubles as the new canvas title, so only layer edits count as unsaved here.
    var savedTitle = state.project ? JSON.parse(state.snapshot)[0] : state.title;
    var layersDirty = !!state.project && JSON.stringify(state.layers) !== JSON.stringify(JSON.parse(state.snapshot)[1]);
    if (layersDirty && !window.confirm('Discard unsaved edits?')) {
      state.title = savedTitle;
      updateControls();
      return;
    }
    var body = { title: title };
    if (fixture) { body.fixture = true; }
    api('POST', '/projects', body).then(function (r) {
      if (r.ok) {
        applyProject(r.data, true);
        loadProjects();
        setStatus('Created "' + r.data.title + '" at revision ' + r.data.revision + '.', 'ok');
        return;
      }
      state.title = savedTitle;
      updateControls();
      if (r.data && r.data.error && r.data.error.code === 'title_taken') {
        setStatus('A canvas with that title already exists. Choose another title.', 'error');
      } else {
        setStatus(errorText(r), 'error');
      }
    }, unreachable);
  }

  function save() {
    if (!state.project || !isDirty() || state.busy) { return; }
    state.busy = true;
    updateControls();
    var body = { title: state.title.trim(), base_revision: state.project.revision, layers: state.layers };
    var sentSnap = snap();
    api('PUT', '/projects/' + state.project.id, body).then(function (r) {
      state.busy = false;
      if (r.ok) {
        if (snap() === sentSnap) {
          applyProject(r.data, false);
        } else {
          // Edits were made while saving: keep them, only advance the revision.
          state.project = r.data;
          state.snapshot = sentSnap;
          renderProjects();
          updateControls();
        }
        loadProjects();
        setStatus('Saved r' + r.data.revision + '.', 'ok');
      } else if (r.status === 409 && r.data && r.data.error && r.data.error.code === 'revision_conflict') {
        state.conflict = r.data.error.current || null;
        el.reload.hidden = false;
        var rev = state.conflict ? state.conflict.revision : '?';
        setStatus('Conflict: the server is at revision ' + rev + '. Your edits are kept. Use "Reload server version" to discard them.', 'error');
        updateControls();
      } else {
        setStatus(errorText(r), 'error');
        updateControls();
      }
    }, function () {
      state.busy = false;
      unreachable();
      updateControls();
    });
  }

  function reloadServer() {
    if (!state.conflict) { return; }
    var p = state.conflict;
    applyProject(p, false);
    loadProjects();
    setStatus('Reloaded server version, revision ' + p.revision + '.', 'ok');
    el.title.focus();
  }

  function nextId(prefix) {
    var used = {};
    state.layers.forEach(function (l) { used[l.id] = true; });
    var n = 1;
    while (used[prefix + '-' + n]) { n += 1; }
    return n;
  }

  function addLayer(type) {
    if (!state.project) { return; }
    if (state.layers.length >= MAX_LAYERS) {
      setStatus('Layer limit of ' + MAX_LAYERS + ' reached.', 'error');
      return;
    }
    var n = nextId(type);
    var layer;
    if (type === 'rect') {
      layer = { id: 'rect-' + n, type: 'rect', label: 'Rectangle ' + n, x: 40, y: 40, w: 120, h: 72, fill: '#2f6f9f' };
    } else {
      layer = { id: 'text-' + n, type: 'text', label: 'Text ' + n, x: 40, y: 40, w: 240, h: 32, text: 'New text', font_size: 24, fill: '#1f2933' };
    }
    state.layers.push(layer);
    state.selectedId = layer.id;
    renderAll();
    setStatus('Added ' + layer.label + '.', 'info');
    focusListItem(layer.id);
  }

  function selectedIndex() {
    for (var i = 0; i < state.layers.length; i++) {
      if (state.layers[i].id === state.selectedId) { return i; }
    }
    return -1;
  }
  function selected() { var i = selectedIndex(); return i < 0 ? null : state.layers[i]; }

  function moveLayer(delta) {
    var i = selectedIndex();
    var j = i + delta;
    if (i < 0 || j < 0 || j >= state.layers.length) { return; }
    var t = state.layers[i];
    state.layers[i] = state.layers[j];
    state.layers[j] = t;
    renderAll();
    setStatus(t.label + ' moved ' + (delta > 0 ? 'toward front' : 'toward back') + '.', 'info');
  }

  function deleteLayer() {
    var i = selectedIndex();
    if (i < 0) { return; }
    var gone = state.layers.splice(i, 1)[0];
    var next = state.layers[Math.min(i, state.layers.length - 1)];
    state.selectedId = next ? next.id : null;
    renderAll();
    setStatus('Deleted ' + gone.label + '.', 'info');
    if (next) { focusListItem(next.id); } else { el.addRect.focus(); }
  }

  function selectLayer(id, focus) {
    state.selectedId = id;
    renderAll();
    if (focus) { focusListItem(id); }
  }

  function focusListItem(id) {
    var b = el.layerList.querySelector('button[data-id="' + id + '"]');
    if (b) { b.focus(); }
  }

  /* ---------- rendering ---------- */

  function renderAll() {
    renderLayerList();
    syncInspector();
    draw();
    updateControls();
  }

  function renderLayerList() {
    el.layerList.textContent = '';
    if (!state.layers.length) {
      var e = document.createElement('li');
      e.className = 'list-empty';
      e.textContent = state.project ? 'No layers. Add a rectangle or text.' : 'Open a canvas to see layers.';
      el.layerList.appendChild(e);
      return;
    }
    for (var i = state.layers.length - 1; i >= 0; i--) {
      var l = state.layers[i];
      var li = document.createElement('li');
      var b = document.createElement('button');
      b.type = 'button';
      b.dataset.id = l.id;
      b.textContent = l.label + ' (' + l.type + ')';
      if (l.id === state.selectedId) { b.setAttribute('aria-current', 'true'); }
      li.appendChild(b);
      el.layerList.appendChild(li);
    }
  }

  function syncInspector() {
    var l = selected();
    var inputs = [el.label, el.x, el.y, el.w, el.h, el.fill, el.text, el.font];
    inputs.forEach(function (i) { i.disabled = !l; i.removeAttribute('aria-invalid'); });
    el.textFields.hidden = !(l && l.type === 'text');
    if (!l) {
      el.label.value = '';
      el.x.value = ''; el.y.value = ''; el.w.value = ''; el.h.value = '';
      el.text.value = ''; el.font.value = '';
      return;
    }
    el.label.value = l.label;
    el.x.value = l.x; el.y.value = l.y; el.w.value = l.w; el.h.value = l.h;
    el.fill.value = l.fill;
    if (l.type === 'text') {
      el.text.value = l.text;
      el.font.value = l.font_size;
    }
  }

  function updateControls() {
    var open = !!state.project;
    var dirty = isDirty();
    el.save.disabled = !(open && dirty) || state.busy;
    el.addRect.disabled = !open;
    el.addText.disabled = !open;
    var i = selectedIndex();
    el.up.disabled = i < 0 || i >= state.layers.length - 1;
    el.down.disabled = i <= 0;
    el.del.disabled = i < 0;
    if (!open) {
      el.meta.textContent = 'No canvas open. Enter a title and choose New canvas, or open one from the project list.';
    } else {
      el.meta.textContent = state.project.title + ' - revision ' + state.project.revision + (dirty ? ' - unsaved changes' : ' - saved');
    }
  }

  function token(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  function draw() {
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = token('--on-ink');
    ctx.fillRect(0, 0, el.canvas.width, el.canvas.height);
    ctx.restore();
    state.layers.forEach(function (l) {
      ctx.save();
      if (l.type === 'rect') {
        ctx.fillStyle = l.fill;
        ctx.fillRect(l.x, l.y, l.w, l.h);
      } else {
        ctx.beginPath();
        ctx.rect(l.x, l.y, l.w, l.h);
        ctx.clip();
        ctx.fillStyle = l.fill;
        ctx.font = l.font_size + 'px ' + FONT;
        ctx.textBaseline = 'top';
        var lh = Math.round(l.font_size * 1.25);
        String(l.text).split('\n').forEach(function (line, n) {
          ctx.fillText(line, l.x, l.y + n * lh);
        });
      }
      ctx.restore();
    });
    var s = selected();
    if (s) {
      ctx.save();
      ctx.lineWidth = 2;
      ctx.setLineDash([6, 4]);
      ctx.strokeStyle = token('--on-ink');
      ctx.strokeRect(s.x - 1, s.y - 1, s.w + 2, s.h + 2);
      ctx.lineDashOffset = 5;
      ctx.strokeStyle = token('--ink');
      ctx.strokeRect(s.x - 1, s.y - 1, s.w + 2, s.h + 2);
      ctx.restore();
    }
  }

  /* ---------- inspector bindings ---------- */

  function changed() {
    renderLayerList();
    draw();
    updateControls();
  }

  function bindNumber(input, key) {
    input.addEventListener('input', function () {
      var l = selected();
      if (!l) { return; }
      var raw = input.value.trim();
      var n = Number(raw);
      var min = Number(input.min);
      var max = Number(input.max);
      if (raw === '' || !Number.isInteger(n) || n < min || n > max) {
        input.setAttribute('aria-invalid', 'true');
        var name = input.labels && input.labels[0] ? input.labels[0].textContent : key;
        setStatus(name + ' must be a whole number from ' + min + ' to ' + max + '.', 'error');
        return;
      }
      input.removeAttribute('aria-invalid');
      l[key] = n;
      changed();
    });
  }

  bindNumber(el.x, 'x');
  bindNumber(el.y, 'y');
  bindNumber(el.w, 'w');
  bindNumber(el.h, 'h');
  bindNumber(el.font, 'font_size');

  el.label.addEventListener('input', function () {
    var l = selected();
    if (!l) { return; }
    var v = el.label.value;
    if (v.trim() === '') {
      el.label.setAttribute('aria-invalid', 'true');
      setStatus('Layer label cannot be empty.', 'error');
      return;
    }
    el.label.removeAttribute('aria-invalid');
    l.label = v;
    changed();
  });

  el.fill.addEventListener('input', function () {
    var l = selected();
    if (!l) { return; }
    l.fill = el.fill.value;
    changed();
  });

  el.text.addEventListener('input', function () {
    var l = selected();
    if (!l || l.type !== 'text') { return; }
    l.text = el.text.value;
    changed();
  });

  el.title.addEventListener('input', function () {
    state.title = el.title.value;
    updateControls();
  });

  /* ---------- events ---------- */

  el.newCanvas.addEventListener('click', function () { createProject(false); });
  el.fixture.addEventListener('click', function () { createProject(true); });
  el.save.addEventListener('click', save);
  el.reload.addEventListener('click', reloadServer);
  el.addRect.addEventListener('click', function () { addLayer('rect'); });
  el.addText.addEventListener('click', function () { addLayer('text'); });
  el.up.addEventListener('click', function () { moveLayer(1); });
  el.down.addEventListener('click', function () { moveLayer(-1); });
  el.del.addEventListener('click', deleteLayer);

  el.projectList.addEventListener('click', function (ev) {
    var b = ev.target.closest('button[data-id]');
    if (!b) { return; }
    if (state.project && String(state.project.id) === b.dataset.id) { return; }
    if (!confirmDiscard()) { return; }
    openProject(b.dataset.id);
  });

  el.layerList.addEventListener('click', function (ev) {
    var b = ev.target.closest('button[data-id]');
    if (b) { selectLayer(b.dataset.id, true); }
  });

  el.layerList.addEventListener('keydown', function (ev) {
    if (ev.key !== 'ArrowDown' && ev.key !== 'ArrowUp') { return; }
    var b = ev.target.closest('button[data-id]');
    if (!b) { return; }
    var all = Array.prototype.slice.call(el.layerList.querySelectorAll('button[data-id]'));
    var k = all.indexOf(b) + (ev.key === 'ArrowDown' ? 1 : -1);
    if (k >= 0 && k < all.length) { all[k].focus(); }
    ev.preventDefault();
  });

  el.canvas.addEventListener('click', function (ev) {
    var r = el.canvas.getBoundingClientRect();
    if (!r.width || !r.height) { return; }
    var px = (ev.clientX - r.left) * el.canvas.width / r.width;
    var py = (ev.clientY - r.top) * el.canvas.height / r.height;
    for (var i = state.layers.length - 1; i >= 0; i--) {
      var l = state.layers[i];
      if (px >= l.x && px < l.x + l.w && py >= l.y && py < l.y + l.h) {
        selectLayer(l.id, false);
        setStatus('Selected ' + l.label + '.', 'info');
        return;
      }
    }
  });

  document.addEventListener('keydown', function (ev) {
    if ((ev.ctrlKey || ev.metaKey) && (ev.key === 's' || ev.key === 'S')) {
      ev.preventDefault();
      save();
    }
  });

  window.addEventListener('beforeunload', function (ev) {
    if (isDirty()) { ev.preventDefault(); ev.returnValue = ''; }
  });

  /* ---------- start ---------- */

  renderAll();
  loadProjects().then(function () {
    var last = readLast();
    if (last && state.projects.some(function (p) { return String(p.id) === last; })) {
      return openProject(last);
    }
    if (last) { storeLast(null); }
    setStatus('Ready. Enter a title and create a canvas, or open one from the list.', 'info');
  });
}());
