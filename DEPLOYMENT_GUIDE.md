# 部署指南

本指南说明如何部署前后端应用，确保它们在不同IP地址时能够正确通信。

## 1. 前端部署（Vercel）

### 步骤：
1. 登录 Vercel 账号
2. 导入项目：选择 GitHub 仓库 `trip_agent_for_vercel`
3. 选择分支：`vercel-deploy`
4. 配置环境变量：
   - **VITE_API_BASE_URL**: 后端部署地址（例如：`https://your-backend-api.com`）
5. 点击 "Deploy" 开始部署

### 关键配置：
- 前端使用环境变量 `VITE_API_BASE_URL` 存储后端地址
- 本地开发时自动使用 Vite 代理，无需配置

## 2. 后端部署

### 推荐平台：
- Railway（免费，支持 FastAPI）
- Render（免费，支持 FastAPI）
- Heroku（有免费额度）

### 配置步骤：
1. 部署后端代码到所选平台
2. 配置环境变量：
   - **CORS_ORIGINS**: 允许的前端地址，多个地址用逗号分隔（例如：`https://your-frontend.vercel.app,http://localhost:5173`）
   - 其他必要的 API 密钥（如高德地图 API Key）

### 关键配置：
- 后端使用环境变量 `CORS_ORIGINS` 控制跨域访问
- 默认配置已包含本地开发地址，部署时需要添加前端域名

## 3. 本地开发配置

### 启动前端：
```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 启动后端：
```bash
# 进入后端目录
cd backend_langchain

# 激活 conda 环境
conda activate llama

# 安装依赖
pip install -r requirements.txt

# 启动后端服务器
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 本地通信：
- 前端通过 Vite 代理（http://localhost:5173/api → http://localhost:8000/api）
- 后端默认允许来自 http://localhost:5173 的跨域请求

## 4. 不同IP部署时的通信配置

### 场景：前端部署在 Vercel（IP A），后端部署在 Railway（IP B）

#### 前端配置：
- 在 Vercel 环境变量中设置：
  ```
  VITE_API_BASE_URL=https://your-backend.railway.app
  ```

#### 后端配置：
- 在 Railway 环境变量中设置：
  ```
  CORS_ORIGINS=https://your-frontend.vercel.app
  ```

### 场景：后端更换IP地址

1. 更新前端配置：
   - 在 Vercel 中更新 `VITE_API_BASE_URL` 为新的后端地址

2. 更新后端配置：
   - 如有必要，更新 `CORS_ORIGINS` 以包含前端地址

## 5. 验证通信

部署完成后，可以通过以下方式验证前后端通信：

1. 访问前端应用
2. 填写旅行计划表单并提交
3. 检查浏览器控制台是否有错误
4. 检查后端日志是否收到请求

## 6. 常见问题及解决方案

### CORS 错误
- **症状**：浏览器控制台显示 "Access to XMLHttpRequest at ... from origin ... has been blocked by CORS policy"
- **解决方案**：在后端环境变量中添加前端地址到 `CORS_ORIGINS`

### API 请求失败
- **症状**：前端显示请求失败，控制台显示 404 或 500 错误
- **解决方案**：
  1. 检查前端 `VITE_API_BASE_URL` 是否正确
  2. 检查后端服务是否正常运行
  3. 检查后端 API 路径是否正确

### 部署后前端显示空白页面
- **症状**：访问前端 URL 显示空白页面
- **解决方案**：
  1. 检查浏览器控制台是否有 JavaScript 错误
  2. 检查 Vercel 构建日志是否有错误
  3. 确保前端代码已正确推送到 `vercel-deploy` 分支

## 7. 环境变量配置示例

### 前端（Vercel）：
| 环境变量名 | 值 | 说明 |
|------------|-----|------|
| VITE_API_BASE_URL | https://your-backend-api.com | 后端 API 基础地址 |

### 后端（Railway/Render）：
| 环境变量名 | 值 | 说明 |
|------------|-----|------|
| CORS_ORIGINS | https://your-frontend.vercel.app,http://localhost:5173 | 允许的前端地址 |
| AMAP_API_KEY | your_amap_api_key | 高德地图 API Key |
| LLM_API_KEY | your_llm_api_key | 大语言模型 API Key |

---

通过以上配置，前后端应用可以在不同 IP 地址部署时正常通信，满足您的需求。