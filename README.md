# 基于AI agent的教学助手

基于AI Agent的智能教学辅助系统，提供课程管理、学情分析、知识库管理和智能交互功能，支持教师和学生双端协同教学场景。

## 核心功能

### 教师端功能
- **课程管理**
  - 创建多层级知识结构的课程
  - 布置和批改作业
  - 管理教学资源
- **学情监控**
  - 实时追踪学生学习进度
  - 可视化知识点掌握度分析
- **知识库建设**
  - 支持知识条目CRUD操作
  - 语义化智能搜索

### 学生端功能
- **学习中心**
  - 加入课程并完成作业
  - 访问教学资源
- **学情自检**
  - 查看个人学习报告
  - 掌握知识点图谱
- **知识检索**
  - 智能语义搜索知识库

## 启动流程
1. 下载并安装postgreSQL

https://www.postgresql.org/download/

然后创建一个数据库
```bash
createdb -U postgres eduassistant-v3  # 也可以用别的名字
```

2. 克隆该仓库
```bash
git clone https://github.com/1787152643/EduAssistant.git
cd EduAssistant
```
3. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate # Windows
```
4. 下载依赖
```bash
pip install -r requirements.txt
```
5. 安装Node.js和Marp CLI
```bash
npm install -g @marp-team/marp-cli
```
6. 配置.env文件

创建文件.env, 然后参照.env.example文件进行配置

7. 启动
```bash
python run.py
```
打开localhost:5000即可访问

## 创建测试用例
1. 在项目的根目录，运行脚本reset_database
```bash
python -m scripts.reset_database
```

## 配置Google搜索工具API

使用Google搜索工具需要在系统环境内手动配置`GOOGLE_SEARCH_API_KEY`和`GOOGLE_SEARCH_CX`两个环境变量。

1. 登录Google开发者平台获取API。详见Google开发者平台：https://developers.google.com/custom-search/v1/introduction?hl=zh-cn
2. 在系统环境变量新建`GOOGLE_SEARCH_API_KEY`环境变量，填入刚刚申请的api_key。例如`AIzaSyC38a_swZiA5M9R7_idw1ro7p0PXu0****`。
3. 在系统环境变量新建`GOOGLE_SEARCH_CX`环境变量，您可以在概览页的基本部分找到搜索引擎`ID`，这是`cx`参数。例如：`567cf071779cd****`。
4. Google由于联网问题可能需要配置本地代理。在系统环境变量新建`GOOGLE_SEARCH_PROXY`变量，填写入http代理的地址。例如：`http://127.0.0.1:10809`。

## 开发相关
### 应用运行逻辑

请求流程：

浏览器 → Flask路由 → 视图层 → 服务层 → 数据层 → 返回响应

模块说明：
- models: 数据模型定义（基于Peewee）
- services: 业务逻辑实现
- views: 请求处理与路由控制
- react: AI代理核心实现
- templates: 前端页面模板

从你的浏览器访问localhost:5000时，浏览器会发送请求到后端。Flask会根据注册的蓝图路由到相应的view函数(被@bp.route('\login', methods=['GET'])之类的修饰)。然后该函数调用services（业务逻辑）层，services层再调用models层进行增删改查来完成需要的功能。view也可能直接访问models层。最后view会返回一个render_template()来绘制前端页面。Flask会自动查找templates文件夹中的template，你只需要提供字符串类型的路径。如render_template('course/create_assignment.html', ...)



### 应用框架
Flask: https://flask.palletsprojects.com/en/stable/

Peewee(数据库ORM框架)：https://docs.peewee-orm.com/en/latest/

Chroma(向量数据库)：https://github.com/chroma-core/chroma

### Agent
#### 简介
ReAct 智能体实现一个推理与行动循环，通过迭代的思考、决策和执行周期来处理用户查询。收到查询后，智能体首先结合对话历史和用户上下文分析请求，然后咨询语言模型以确定最佳行动方案。基于这一推理，它会从针对学生、教师或管理员定制的角色专属工具集中选择合适的工具，执行该工具以获取新信息，并将这些观察结果纳入下一轮推理循环——或者在收集到足够的信息后直接给出最终答案。这个循环过程会持续进行，直到智能体生成令人满意的响应或达到最大迭代次数，

Paper: https://arxiv.org/abs/2210.03629（不用看）

参考： https://github.com/arunpshankar/react-from-scratch/tree/main?tab=readme-ov-file

#### 如何将函数注册为Agent可以使用的工具：
1. from app.react.tools_register import register_as_tool
2. 用@register_as_tool(roles=['student', 'teacher'])修饰需要注册为工具的函数。roles是你希望可以使用该函数的角色。
3. 在docstring中描述该函数的作用和输入参数。它会被传给agent，只有写清楚了大模型才知道如何调用这个工具。建议使用Google style docstring（非必须）。
如:
```python
    @register_as_tool(roles=["teacher"])
    @staticmethod
    def get_courses_by_teacher(teacher_id):
        """获取教师所教授的所有课程。
        
        Args:
            teacher_id (int): 教师用户ID
            
        Returns:
            list: 课程对象列表
        """
        return list(Course.select().where(Course.teacher_id == teacher_id))
```

#### notes：
目前只支持普通的函数和类的静态函数。

如果你需要注册类的静态函数，请将@register_as_tool()放在@staticmethod的上方，如上所示。

### TODO
#### 目前可以实现的改进：
  - 使用JWT进行身份认证。（可以先不做）

    实现方法：使用PyJWT，编写@token_required修饰器。

  - 目前的agent聊天是不考虑历史消息的，可以将历史消息加入，一起传给LLM。

    实现方法：

    为Agent添加add_history()方法，修改prompt文件.\data\input\react.txt，添加历史消息占位符。聊天时从数据库读取历史消息传入给agent。

  - 为课程添加更多功能。如实现教师端课程资源上传，包括文本、视频和PDF等。学生端可以访问这些资源。

    实现方法：

    1. 在models里添加新表（参考Peewee文档），可以新建文件或者加入在course.py里。
    2. 修改前端页面。
    3. 在services和views里添加相应功能。

  - 添加测验功能/完善作业功能。现有的作业只有文本描述和文本回答。可以将作业细分为几个问题，包括选择题、填空题和问答题等。并考虑实现结合agent自动批改。

    实现方法：

    1. 在models里添加新表，可以新建文件或者加入在assignment.py。
    添加问题表，每个问题存储一个Assignment的外键，表示属于哪个作业。
    添加学生问题回答，每个回答存储一个StudentAssignment的外键，表示属于哪个学生作业。
    2. 修改前端页面。
    3. 完善services和views的相关功能。

  - 完善知识库。现有知识库只有文本知识条目。可以考虑加入文档、FAQ等知识条目类型。

    实现方法：

    1. 在models的knowledage_base.py里添加新表。
    2. 修改前端页面。
    3. 完善services和views的相关功能。
    注意在knowledge_base_service.py中为这些知识条目支持chroma向量搜索功能。具体做法为在关系数据库(models)中添加vector_id表示它在向量数据库中的id。在向量数据库存储的metadata中添加id（关系数据库）。这样就可以把二者联系起来。搜索时先从向量数据库搜索，再用结果的id来搜索关系数据库，最后取出记录。

#### notes:
1. 如果创建了新的表，记得在你的数据库中添加该表。可以在.\scripts\create_tables.py中的tables列表中添加你新建的表，然后调用db.create_tables(tables)，最后运行该脚本。

2. 如果创建了新的蓝图blueprint，记得在app\\\_\_init\_\_.py中注册该蓝图。

3. 实现新功能的时候，都可以考虑将该功能注册给agent使用。注意教师角色和学生角色的权限分别。




### 文件结构说明
```
├── app/
│   ├── config.py                 配置文件
│   ├── ext.py                    拓展（主要是数据库）
│   ├── models/                   数据库模型定义(Peewee)
│   ├── react/                    Resoning and acting agent
│   │   ├── agent.py              agent实现逻辑
│   │   ├── tools/                一些可能用到的工具
│   │   └── tools_register.py     将函数注册为agent可用的工具
│   ├── services/                 业务逻辑层
│   ├── static/                   Frontend assets (CSS, JS, images)
│   ├── templates/                HTML templates
│   ├── utils/                    实用工具类
│   │   ├── io.py
│   │   ├── llm/                  大模型调用
│   │   └── logging.py
│   └── views/                    前端视图，用于与前端交互
├── chroma_db/                    chroma向量数据库存储目录
├── data/                         agent的数据
│   ├── input/
│   │   └── react.txt             输入prompt模板
│   └── output/
│       └── trace.txt             追踪agent思考过程
├── logs/
│   └── app.log                   log，主要是agent
├── migrations/                   数据库迁移定义，暂未使用
├── requirements.txt
├── .env                          环境变量
├── run.py                        启动入口
├── scripts/                      数据库表生成脚本
│   ├── create_tables.py          创建数据库表
│   ├── create_test/              创建测试用例
│   │   ├── create_courses_knowledge_points.py
│   │   ├── create_enrollments_assignments.py
│   │   ├── create_learning_activities_mastery.py
│   │   └── create_test_users.py
│   └── reset_database.py         删除并创建数据库表，然后生成测试样例数据
└── tests/
    └── test_tools_register.py
```