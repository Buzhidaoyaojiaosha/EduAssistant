/**
 * 启智AI伴学主JavaScript文件
 */

document.addEventListener('DOMContentLoaded', () => {
    // 启用所有提示工具(tooltips)
    const tooltipTriggerList = Array.from(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));

    // 为删除确认框添加事件处理
    setupDeleteConfirmations();
    
    // 设置表单验证
    setupFormValidation();
    
    // 记录学习活动（仅在学生页面上）
    if (document.querySelector('.student-learning-page')) {
        recordLearningActivity();
    }
    
    // 处理课程筛选器
    setupCourseFilters();
});

/**
 * 为删除确认框设置事件处理器
 */
function setupDeleteConfirmations() {
    // 找到所有具有data-confirm属性的元素
    const confirmButtons = document.querySelectorAll('[data-confirm]');
    
    confirmButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            if (!confirm(button.dataset.confirm)) {
                e.preventDefault();
            }
        });
    });
}

/**
 * 设置表单验证
 */
function setupFormValidation() {
    // 获取所有需要验证的表单
    const forms = document.querySelectorAll('.needs-validation');
    
    // 应用验证
    forms.forEach(form => {
        form.addEventListener('submit', (event) => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
    
    // 密码确认验证
    const passwordConfirmForms = document.querySelectorAll('.password-confirm-form');
    passwordConfirmForms.forEach(form => {
        form.addEventListener('submit', (e) => {
            const password = form.querySelector('.password');
            const confirmPassword = form.querySelector('.confirm-password');
            
            if (password && confirmPassword && password.value !== confirmPassword.value) {
                e.preventDefault();
                alert('两次输入的密码不一致，请重新输入');
            }
        });
    });
}

/**
 * 记录学生学习活动
 */
function recordLearningActivity() {
    // 获取元数据
    const courseId = document.querySelector('meta[name="course-id"]')?.content;
    if (!courseId) return;
    
    // 准备活动数据
    const activityData = {
        course_id: parseInt(courseId),
        activity_type: 'page_view',
        duration: 0,
        metadata: {
            page_url: window.location.pathname,
            page_title: document.title
        }
    };
    
    // 记录活动开始时间
    const startTime = new Date();
    
    // 页面离开或隐藏时计算持续时间并提交
    function submitActivity() {
        // 计算持续时间（秒）
        const duration = Math.floor((new Date() - startTime) / 1000);
        if (duration < 5) return; // 忽略太短的活动
        
        activityData.duration = duration;
        
        // 发送到服务器
        fetch('/analytics/record-activity', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(activityData)
        }).catch(error => console.error('Error recording activity:', error));
    }
    
    // 页面离开时记录活动
    window.addEventListener('beforeunload', submitActivity);
    
    // 页面可见性变化时处理（如切换标签）
    /*document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden') {
            submitActivity();
        } else {
            // 重新开始计时
            startTime = new Date();
        }
    });*/
}

/**
 * 设置课程筛选器的行为
 */
function setupCourseFilters() {
    const courseFilter = document.getElementById('courseFilter');
    
    if (courseFilter) {
        courseFilter.addEventListener('change', function() {
            // 获取当前URL参数
            const urlParams = new URLSearchParams(window.location.search);
            
            // 更新课程ID参数
            if (this.value) {
                urlParams.set('course_id', this.value);
            } else {
                urlParams.delete('course_id');
            }
            
            // 导航到更新后的URL
            window.location.href = window.location.pathname + 
                (urlParams.toString() ? '?' + urlParams.toString() : '');
        });
    }
}

