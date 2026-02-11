# 在conda环境llama下运行HelloAgents智能旅行助手项目

## 项目分析
- 项目是基于HelloAgents框架的智能旅行规划助手
- 包含前端（Vue3 + TypeScript）和后端（FastAPI）两部分
- 需要配置LLM API密钥和高德地图API密钥

## 运行计划

### 1. 检查并激活conda环境
- 检查conda环境llama是否存在
- 激活conda环境llama

### 2. 后端配置与运行
- 进入backend目录
- 安装后端依赖：`pip install -r requirements.txt`
- 复制并配置环境变量文件：`cp .env.example .env`
- 编辑.env文件，填入必要的API密钥
- 启动后端服务：`uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000`

### 3. 前端配置与运行
- 进入frontend目录
- 安装前端依赖：`npm install`
- 复制并配置环境变量文件：`cp .env.example .env`
- 编辑.env文件，填入高德地图API密钥
- 启动前端开发服务器：`npm run dev`

### 4. 验证运行状态
- 后端服务访问：http://localhost:8000/docs
- 前端应用访问：http://localhost:5173

## 注意事项
- 确保conda环境llama中已安装Python 3.10+
- 确保系统中已安装Node.js 16+
- 需要准备好LLM API密钥（如OpenAI/DeepSeek）和高德地图API密钥
- 后端服务启动后，前端才能正常访问