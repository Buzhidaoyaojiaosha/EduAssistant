/**
 * TaskManager - 跨页面持久化AI生成任务管理器
 *
 * 使用 localStorage 保存任务状态，sessionStorage 保存结果数据。
 * 页面切换时自动重新发起被中断的 fetch 请求。
 */
(function () {
    'use strict';

    var STORAGE_KEY = 'edu_running_tasks';
    var RESULT_PREFIX = 'edu_result_';
    var PENDING_RESULT_KEY = 'edu_pending_result';
    var TASK_EXPIRY_MS = 30 * 60 * 1000; // 30分钟过期

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
    }

    // ======================== 任务创建 ========================

    /**
     * 启动一个新的后台任务
     * @param {string} taskType       - teaching_outline | study_report | mindmap | assessment
     * @param {string} endpoint       - API URL
     * @param {object} requestBody    - POST body (会被 JSON.stringify)
     * @param {string} label          - 浮动按钮上显示的文字
     * @param {string|number} courseId
     * @returns {string} taskId
     */
    window.TaskManager_startTask = function (taskType, endpoint, requestBody, label, courseId) {
        var taskId = 'task_' + Date.now();
        var entry = {
            id: taskId,
            label: label,
            courseId: String(courseId),
            status: 'running',
            endpoint: endpoint,
            requestBody: JSON.stringify(requestBody),
            taskType: taskType,
            timestamp: Date.now()
        };
        setTask(taskId, entry);
        renderBar();
        fireFetch(taskId, entry);
        return taskId;
    };

    // ======================== Fetch 执行 ========================

    function fireFetch(taskId, entry) {
        fetch(entry.endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: entry.requestBody,
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
            if (data.error) {
                onTaskError(taskId, data.error);
            } else {
                onTaskComplete(taskId, data);
            }
        })
        .catch(function (error) {
            var msg = '生成失败，请重试。';
            if (error.message) msg = error.message;
            onTaskError(taskId, msg);
        });
    }

    function onTaskComplete(taskId, data) {
        var task = getTask(taskId);
        if (!task) return; // 用户已取消
        task.status = 'completed';
        task.timestamp = Date.now();
        setTask(taskId, task);
        // 结果存入 sessionStorage
        try {
            sessionStorage.setItem(RESULT_PREFIX + taskId, JSON.stringify(data));
        } catch (e) {
            console.warn('sessionStorage 写入失败，结果可能过大', e);
        }
        renderBar();
    }

    function onTaskError(taskId, errorMsg) {
        var task = getTask(taskId);
        if (!task) return;
        task.status = 'error';
        task.error = errorMsg;
        task.timestamp = Date.now();
        setTask(taskId, task);
        renderBar();
    }

    // ======================== 任务操作 ========================

    /** 用户点击完成的任务 → 导航到课程页并展示结果 */
    window.TaskManager_navigateToResult = function (taskId) {
        var task = getTask(taskId);
        if (!task) return;
        sessionStorage.setItem(PENDING_RESULT_KEY, taskId);
        window.location.href = '/course/' + task.courseId;
    };

    /** 取消/删除任务 */
    window.TaskManager_dismissTask = function (taskId) {
        removeTask(taskId);
        renderBar();
    };

    /** 重试失败的任务 */
    window.TaskManager_retryTask = function (taskId) {
        var task = getTask(taskId);
        if (!task) return;
        task.status = 'running';
        task.error = null;
        task.timestamp = Date.now();
        setTask(taskId, task);
        renderBar();
        fireFetch(taskId, task);
    };

    /** 检查是否有等待展示的结果 (供 view.html 调用) */
    window.TaskManager_checkPendingResult = function () {
        var taskId = sessionStorage.getItem(PENDING_RESULT_KEY);
        if (!taskId) return null;
        sessionStorage.removeItem(PENDING_RESULT_KEY);
        var raw = sessionStorage.getItem(RESULT_PREFIX + taskId);
        if (!raw) return null;
        var task = getTask(taskId);
        if (!task) return null;
        // 返回 { taskType, data }
        return { taskType: task.taskType, data: JSON.parse(raw) };
    };

    // ======================== 浮动条渲染 ========================

    function getBarEl() {
        return document.getElementById('minimizedTasksBar');
    }

    function renderBar() {
        var bar = getBarEl();
        if (!bar) return; // 当前页面没有浮动条（如登录页）

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

        // 重新读取（可能被 removeTask 修改过）
        tasks = getTasks();
        bar.style.display = 'flex';
        bar.innerHTML = '';

        Object.keys(tasks).forEach(function (id) {
            var t = tasks[id];
            var btn = document.createElement('div');

            if (t.status === 'running') {
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
                    window.TaskManager_retryTask(id);
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

    // ======================== 页面加载时自动恢复 ========================

    document.addEventListener('DOMContentLoaded', function () {
        // 1. 对所有 running 状态的任务重新发起 fetch
        var tasks = getTasks();
        Object.keys(tasks).forEach(function (id) {
            var t = tasks[id];
            if (t.status === 'running') {
                fireFetch(id, t);
            }
        });
        // 2. 渲染浮动条
        renderBar();
    });

})();
