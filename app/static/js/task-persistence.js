/**
 * TaskManager - 跨页面持久化AI生成任务管理器
 *
 * 后端任务队列模式:
 *   POST 提交任务 → 返回 task_id
 *   GET  轮询状态 → 返回 running / completed / error
 *
 * 使用 localStorage 保存任务元数据，sessionStorage 保存结果数据。
 * 页面切换后继续轮询同一个 task_id，任务在服务器后台持续运行。
 */
(function () {
    'use strict';

    var STORAGE_KEY = 'edu_tasks';
    var RESULT_PREFIX = 'edu_result_';
    var PENDING_RESULT_KEY = 'edu_pending_result';
    var POLL_INTERVAL = 2000; // 2秒轮询一次
    var TASK_EXPIRY_MS = 30 * 60 * 1000; // 30分钟过期
    var _pollTimers = {}; // 当前页面的轮询定时器

    // ======================== localStorage 工具 ========================

    function getTasks() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
        } catch (e) {
            return {};
        }
    }

    function saveTasks(tasks) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));
    }

    function getTask(id) {
        return getTasks()[id] || null;
    }

    function setTask(id, entry) {
        var tasks = getTasks();
        tasks[id] = entry;
        saveTasks(tasks);
    }

    function removeTask(id) {
        var tasks = getTasks();
        delete tasks[id];
        saveTasks(tasks);
        try { sessionStorage.removeItem(RESULT_PREFIX + id); } catch (e) { /* ignore */ }
        if (_pollTimers[id]) {
            clearInterval(_pollTimers[id]);
            delete _pollTimers[id];
        }
    }

    // ======================== 提交任务 ========================

    /**
     * 提交一个新的后台任务
     * @param {string} taskType       - teaching_outline | study_report | mindmap | assessment
     * @param {string} endpoint       - POST API URL
     * @param {object} requestBody    - POST body
     * @param {string} label          - 浮动按钮显示文字
     * @param {string|number} courseId
     * @param {function} onComplete   - 任务完成时的回调 (resultData)
     * @param {function} onError      - 任务失败时的回调 (errorMessage)
     * @returns {string} taskId (本地生成的，不是后端的)
     */
    window.TaskManager_startTask = function (taskType, endpoint, requestBody, label, courseId, onComplete, onError, statusEndpoint) {
        var localId = 'task_' + Date.now();
        // statusEndpoint 可选：轮询状态的URL前缀，默认 /course/api/task/
        var statusBase = statusEndpoint || '/course/api/task/';
        var entry = {
            localId: localId,
            serverTaskId: null,
            label: label,
            courseId: String(courseId),
            status: 'submitting',
            taskType: taskType,
            statusBase: statusBase,
            timestamp: Date.now()
        };
        setTask(localId, entry);
        renderBar();

        // 提交 POST 请求
        fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(requestBody),
            credentials: 'same-origin'
        })
        .then(function (response) {
            if (!response.ok) {
                return response.json().then(function (data) {
                    throw new Error(data.error || 'HTTP Error: ' + response.status);
                });
            }
            return response.json();
        })
        .then(function (data) {
            if (data.task_id) {
                // 保存回调函数（仅当前页面有效）
                entry.serverTaskId = data.task_id;
                entry.status = 'running';
                entry.timestamp = Date.now();
                setTask(localId, entry);
                renderBar();
                startPolling(localId, onComplete, onError);
            } else if (data.error) {
                entry.status = 'error';
                entry.error = data.error;
                setTask(localId, entry);
                renderBar();
                if (onError) onError(data.error);
            }
        })
        .catch(function (error) {
            entry.status = 'error';
            entry.error = error.message || '提交任务失败';
            setTask(localId, entry);
            renderBar();
            if (onError) onError(entry.error);
        });

        return localId;
    };

    // ======================== 轮询 ========================

    function startPolling(localId, onComplete, onError) {
        // 先清除旧的定时器
        if (_pollTimers[localId]) {
            clearInterval(_pollTimers[localId]);
        }

        _pollTimers[localId] = setInterval(function () {
            pollOnce(localId, onComplete, onError);
        }, POLL_INTERVAL);
    }

    function pollOnce(localId, onComplete, onError) {
        var entry = getTask(localId);
        if (!entry || !entry.serverTaskId) {
            // 任务被删除
            if (_pollTimers[localId]) {
                clearInterval(_pollTimers[localId]);
                delete _pollTimers[localId];
            }
            return;
        }

        fetch((entry.statusBase || '/course/api/task/') + entry.serverTaskId + '/status', {
            credentials: 'same-origin'
        })
        .then(function (response) {
            if (!response.ok) {
                if (response.status === 404) {
                    throw new Error('任务不存在或已过期');
                }
                throw new Error('HTTP Error: ' + response.status);
            }
            return response.json();
        })
        .then(function (data) {
            if (data.status === 'completed') {
                // 完成
                if (_pollTimers[localId]) {
                    clearInterval(_pollTimers[localId]);
                    delete _pollTimers[localId];
                }
                entry.status = 'completed';
                entry.timestamp = Date.now();
                setTask(localId, entry);
                // 结果存入 sessionStorage
                try {
                    sessionStorage.setItem(RESULT_PREFIX + localId, JSON.stringify(data.result));
                } catch (e) {
                    console.warn('sessionStorage 写入失败', e);
                }
                renderBar();
                if (onComplete) onComplete(data.result);
            } else if (data.status === 'error') {
                // 失败
                if (_pollTimers[localId]) {
                    clearInterval(_pollTimers[localId]);
                    delete _pollTimers[localId];
                }
                entry.status = 'error';
                entry.error = data.error || '生成失败';
                entry.timestamp = Date.now();
                setTask(localId, entry);
                renderBar();
                if (onError) onError(entry.error);
            }
            // running → 继续轮询
        })
        .catch(function (error) {
            // 轮询出错（网络问题等），继续重试
            console.warn('任务轮询出错:', error.message);
        });
    }

    // ======================== 任务操作 ========================

    /** 用户点击完成的任务 → 导航到课程页并展示结果 */
    window.TaskManager_navigateToResult = function (localId) {
        var entry = getTask(localId);
        if (!entry) return;
        sessionStorage.setItem(PENDING_RESULT_KEY, localId);
        window.location.href = '/course/' + entry.courseId;
    };

    /** 取消/删除任务 */
    window.TaskManager_dismissTask = function (localId) {
        removeTask(localId);
        renderBar();
    };

    /** 重试失败的任务 */
    window.TaskManager_retryTask = function (localId) {
        // 暂不支持重试（需要保存原始请求参数）
        removeTask(localId);
        renderBar();
    };

    /** 检查是否有等待展示的结果 (供 view.html 调用) */
    window.TaskManager_checkPendingResult = function () {
        var localId = sessionStorage.getItem(PENDING_RESULT_KEY);
        if (!localId) return null;
        sessionStorage.removeItem(PENDING_RESULT_KEY);
        var raw = sessionStorage.getItem(RESULT_PREFIX + localId);
        if (!raw) return null;
        var entry = getTask(localId);
        if (!entry) return null;
        // 清理任务
        removeTask(localId);
        return { taskType: entry.taskType, data: JSON.parse(raw) };
    };

    /** 给 view.html 轮询用：检查本地任务是否完成 */
    window.TaskManager_isTaskDone = function (localId) {
        var entry = getTask(localId);
        if (!entry) return 'not_found';
        return entry.status; // 'submitting' | 'running' | 'completed' | 'error'
    };

    /** 给 view.html 获取结果用 */
    window.TaskManager_getResult = function (localId) {
        var raw = sessionStorage.getItem(RESULT_PREFIX + localId);
        if (!raw) return null;
        return JSON.parse(raw);
    };

    /** 给 view.html 获取错误用 */
    window.TaskManager_getError = function (localId) {
        var entry = getTask(localId);
        return entry ? entry.error : '任务不存在';
    };

    // ======================== 浮动条渲染 ========================

    function getBarEl() {
        return document.getElementById('minimizedTasksBar');
    }

    function renderBar() {
        var bar = getBarEl();
        if (!bar) return;

        // 清理过期任务
        var tasks = getTasks();
        var now = Date.now();
        var hasActive = false;
        Object.keys(tasks).forEach(function (id) {
            if (now - tasks[id].timestamp > TASK_EXPIRY_MS) {
                removeTask(id);
            } else {
                hasActive = true;
            }
        });

        if (!hasActive) {
            bar.style.display = 'none';
            bar.innerHTML = '';
            return;
        }

        tasks = getTasks();
        bar.style.display = 'flex';
        bar.innerHTML = '';

        Object.keys(tasks).forEach(function (id) {
            var t = tasks[id];
            var btn = document.createElement('div');

            if (t.status === 'submitting' || t.status === 'running') {
                btn.className = 'minimized-task-btn';
                btn.innerHTML =
                    '<span class="spinner-border text-primary" role="status"></span>' +
                    '<span>' + escapeHtml(t.label) + '</span>' +
                    '<button class="close-task" title="取消">&times;</button>';

                btn.querySelector('.close-task').addEventListener('click', function (e) {
                    e.stopPropagation();
                    window.TaskManager_dismissTask(id);
                });
            }
            else if (t.status === 'completed') {
                btn.className = 'minimized-task-btn minimized-completed';
                btn.innerHTML =
                    '<i class="fas fa-check-circle" style="color:#28a745;font-size:1.1rem;"></i>' +
                    '<span>' + escapeHtml(completedLabel(t.label)) + '</span>' +
                    '<button class="close-task" title="关闭">&times;</button>';

                btn.addEventListener('click', function (e) {
                    if (e.target.classList.contains('close-task')) return;
                    window.TaskManager_navigateToResult(id);
                });
                btn.querySelector('.close-task').addEventListener('click', function (e) {
                    e.stopPropagation();
                    window.TaskManager_dismissTask(id);
                });
            }
            else if (t.status === 'error') {
                btn.className = 'minimized-task-btn minimized-error';
                btn.innerHTML =
                    '<i class="fas fa-exclamation-circle" style="color:#dc3545;font-size:1.1rem;"></i>' +
                    '<span>' + escapeHtml(t.label) + ' 失败</span>' +
                    '<button class="close-task" title="关闭">&times;</button>';

                btn.addEventListener('click', function (e) {
                    if (e.target.classList.contains('close-task')) return;
                    window.TaskManager_dismissTask(id);
                });
                btn.querySelector('.close-task').addEventListener('click', function (e) {
                    e.stopPropagation();
                    window.TaskManager_dismissTask(id);
                });
            }

            bar.appendChild(btn);
        });
    }

    function completedLabel(label) {
        return label.replace(/^正在/, '') + '完成';
    }

    function escapeHtml(str) {
        var d = document.createElement('div');
        d.appendChild(document.createTextNode(str));
        return d.innerHTML;
    }

    // ======================== 页面加载时恢复轮询 ========================

    document.addEventListener('DOMContentLoaded', function () {
        var tasks = getTasks();
        Object.keys(tasks).forEach(function (id) {
            var t = tasks[id];
            if (t.status === 'running' && t.serverTaskId) {
                // 继续轮询（当前页面没有回调，所以只更新状态和浮动条）
                startPolling(id, null, null);
            }
        });
        renderBar();
    });

})();
