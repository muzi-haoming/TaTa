# 🎭 TaTa NPC Architect System

AI 驱动的游戏 NPC 角色生成系统，基于 RAG（检索增强生成）技术，结合知识库生成符合设定的角色。

工作流：检索参考资料 → 生成角色档案 → 自动评估 + 人工审核 → 生成图片提示词 → 人工审核
→ 生成角色图片 → 自动评估 + 人工审核 → 生成 3D 模型。

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 登录 Google Cloud

```bash
gcloud auth application-default login
```

### 启动应用

```bash
streamlit run app.py
```

### 配置 Meshy（3D 模型生成）

未设置环境变量时会使用 Meshy 的测试密钥（不会真正产出模型），正式使用请设置：

```bash
setx MESHY_API_KEY "msy_你的密钥"
```

## 项目结构

```
app.py                  应用入口（Streamlit）
config/                 配置
  models.py             pydantic 配置模型 + YamlSettings 加载基类
  config.py             ConfigLoader（单例）：加载 YAML、注入环境变量、初始化日志
  settings.yaml         主配置
  meshy_config.yaml     Meshy 参数配置
core/                   核心能力
  prompts.py            所有系统提示词集中管理
  response_structure.py 大模型结构化输出定义
  embedding_model.py    Embedding 工厂（lru_cache 单实例）
  vector_store.py       Chroma 向量库工厂
  retriever.py          检索器工厂 + search_lore / asearch_lore
services/               外部服务封装
  base.py               HttpApiClient / TaskEndpoint（通用 HTTP 与异步任务端点）
  meshy_service.py      Meshy API 形状描述（单例）
workflows/              工作流
  base.py               BaseWorkflow（图生命周期与运行入口）
                        LlmWorkflow（通用节点：生成/评估/人工审核/落盘/路由）
  state.py              NpcState + 由类型注解推导的零值初始状态
  generate_npc_workflow.py  NPC 生成工作流：节点声明 + 连线
ui/                     Streamlit 界面
  styles.py             CSS
  components.py         无状态渲染组件
  formatters.py         纯文本格式化（可单测）
  base.py               BasePage（页面骨架）
  npc_generation_page.py  NPC 生成页面
tools/                  Agent 工具
middlewares/            Agent 中间件
utils/                  通用工具（FileUtil / logger / SingletonMeta）
scripts/                交互式开发脚本（不参与自动化测试）
tests/                  单元测试（全部可无人值守运行）
data/                   知识库、向量库、生成产物、日志
```

### 分层约定

- `utils` 不依赖任何业务模块；
- `config` 依赖 `utils`，并在加载完成后回调 `setup_logger` 初始化日志；
- `core` / `services` 依赖 `config` + `utils`；
- `workflows` 依赖 `core` / `services`；
- `ui` 依赖 `workflows`，不直接触碰第三方 SDK。

## 开发

### 运行测试

```bash
pytest
```

### 交互式脚本

```bash
python -m scripts.run_npc_workflow "一个照顾花田的利特族人"
python -m scripts.meshy_task_manager
```

### 代码风格

```bash
ruff check .
black .
```

## 扩展指引

**新增一个工作流**：继承 `LlmWorkflow`，声明 `state_schema`，实现 `_build_graph`；
生成/评估/人工审核/落盘节点用基类的 `make_*_node` 配合 `*Spec` 声明即可，无需重写异步样板。

**新增一个第三方服务**：用 `services.base.HttpApiClient` 处理传输与错误，
用 `TaskEndpoint` 处理「提交任务 → 查询 → 监听进度」，服务类只描述各接口的字段与默认值。

**新增一个页面**：继承 `ui.base.BasePage`，声明页面元信息与 `session_defaults`，实现 `render`。

**修改提示词**：只改 `core/prompts.py`，工作流节点不内嵌提示词文本。
