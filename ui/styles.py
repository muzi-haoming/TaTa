"""页面样式

集中存放自定义 CSS，避免与渲染逻辑混在一起。
"""

#: 主题色
PRIMARY_GRADIENT = "linear-gradient(90deg, #667eea 0%, #764ba2 100%)"
PRIMARY_COLOR = "#667eea"

NPC_PAGE_CSS = """
/* 加载动画 */
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

.loading-indicator {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1.25rem;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    border-radius: 25px;
    color: white;
    font-size: 0.95rem;
    animation: pulse 1.5s ease-in-out infinite;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
}

.loading-spinner {
    width: 18px;
    height: 18px;
    border: 2px solid #ffffff40;
    border-top: 2px solid #ffffff;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

/* 进度步骤样式 */
.progress-steps {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin: 0.5rem 0;
}

.progress-step {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.25rem 0.75rem;
    background: #e8f5e9;
    border-radius: 15px;
    font-size: 0.85rem;
    color: #2e7d32;
}

/* 3D模型进度条 */
.model-progress-container {
    margin: 0.5rem 0;
    padding: 1rem;
    background: #f8f9fa;
    border-radius: 10px;
    border-left: 4px solid #667eea;
}

.model-progress-bar {
    width: 100%;
    height: 8px;
    background: #e0e0e0;
    border-radius: 4px;
    overflow: hidden;
    margin-top: 0.5rem;
}

.model-progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    border-radius: 4px;
    transition: width 0.3s ease;
}

/* 消息区域底部留白 */
.main .block-container {
    padding-bottom: 100px;
}

/* 结果卡片 */
.result-section {
    background: #f8f9fa;
    border-radius: 12px;
    padding: 1rem;
    margin: 0.5rem 0;
    border-left: 4px solid #667eea;
}
"""
