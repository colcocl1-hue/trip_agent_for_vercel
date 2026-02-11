"""多智能体旅行规划系统"""

import json
import time
from typing import Dict, Any, List
from hello_agents import SimpleAgent
from hello_agents.tools import MCPTool
from ..services.llm_service import get_llm
from ..models.schemas import TripRequest, TripPlan, DayPlan, Attraction, Meal, WeatherInfo, Location, Hotel
from ..config import get_settings
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient  
from langchain.agents import create_agent
# ============ Agent提示词 ============
import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI   
from functools import wraps
from typing import Any, Callable

# from functools import wraps
# from typing import List

# class RateLimiter:  优化后尝试
#     """令牌桶速率限制器"""
#     def __init__(self, rate: int, per: float):
#         """
#         :param rate: 允许的请求数
#         :param per: 时间窗口（秒）
#         """
#         self.rate = rate
#         self.per = per
#         self.tokens = rate
#         self.updated_at = time.monotonic()

#     async def acquire(self):
#         """获取一个令牌，如果超出限制则等待"""
#         while self.tokens < 1:
#             now = time.monotonic()
#             elapsed = now - self.updated_at
#             # 计算这段时间内应新增的令牌数
#             self.tokens = min(self.rate, self.tokens + elapsed * (self.rate / self.per))
#             self.updated_at = now
#             if self.tokens < 1:
#                 # 令牌不足，等待下一个令牌生成的时间
#                 wait_time = (1 - self.tokens) * (self.per / self.rate)
#                 await asyncio.sleep(wait_time)
#         self.tokens -= 1  # 消耗一个令牌

# def rate_limit(rate: int, per: float = 1.0):
#     """装饰器：限制被装饰的异步函数调用频率"""
#     limiter = RateLimiter(rate, per)
    
#     def decorator(func):
#         @wraps(func)
#         async def wrapper(*args, **kwargs):
#             await limiter.acquire()  # 等待获取令牌
#             return await func(*args, **kwargs)
#         return wrapper
#     return decorator

def rate_limit(rate: int = 3, per: float = 1.0):
    """异步函数速率限制装饰器"""
    min_interval = per / rate
    last_called = [0.0]
    lock = asyncio.Lock()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            async with lock:
                elapsed = time.time() - last_called[0]
                left_to_wait = min_interval - elapsed
                
                if left_to_wait > 0:
                    await asyncio.sleep(left_to_wait)
                
                last_called[0] = time.time()
                # 正确传递所有参数，包括 config
                return await func(*args, **kwargs)
        return wrapper
    return decorator
os.environ["LANGCHAIN_VERBOSE"] = "true"

ATTRACTION_AGENT_PROMPT = """你是景点搜索专家。你的任务是根据城市和用户偏好搜索合适的景点。

**重要提示:**
你必须使用工具来搜索景点!不要自己编造景点信息!

**注意:**
1. 必须使用工具,不要直接回答
2. 格式必须完全正确,包括方括号和冒号
3. 参数用逗号分隔
"""

WEATHER_AGENT_PROMPT = """你是天气查询专家。你的任务是查询指定城市的天气信息。

**重要提示:**
你必须使用工具来查询天气!不要自己编造天气信息!

**注意:**
1. 必须使用工具,不要直接回答
2. 格式必须完全正确,包括方括号和冒号
"""

HOTEL_AGENT_PROMPT = """你是酒店推荐专家。你的任务是根据城市和景点位置推荐合适的酒店。

**重要提示:**
你必须使用工具来搜索酒店!不要自己编造酒店信息!

**注意:**
1. 必须使用工具,不要直接回答
2. 格式必须完全正确,包括方括号和冒号
3. 关键词使用"酒店"或"宾馆"
"""

# PLANNER_AGENT_PROMPT = """你是行程规划专家。你的任务是根据景点信息和天气信息,生成详细的旅行计划。"""
PLANNER_AGENT_PROMPT = """你是行程规划专家。你的任务是根据景点信息和天气信息,生成详细的旅行计划。

请严格按照以下JSON格式返回旅行计划:
```json
{
  "city": "城市名称",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "days": [
    {
      "date": "YYYY-MM-DD",
      "day_index": 0,
      "description": "第1天行程概述",
      "transportation": "交通方式",
      "accommodation": "住宿类型",
      "hotel": {
        "name": "酒店名称",
        "address": "酒店地址",
        "location": {"longitude": 116.397128, "latitude": 39.916527},
        "price_range": "300-500元",
        "rating": "4.5",
        "distance": "距离景点2公里",
        "type": "经济型酒店",
        "estimated_cost": 400
      },
      "attractions": [
        {
          "name": "景点名称",
          "address": "详细地址",
          "location": {"longitude": 116.397128, "latitude": 39.916527},
          "visit_duration": 120,
          "description": "景点详细描述",
          "category": "景点类别",
          "ticket_price": 60
        }
      ],
      "meals": [
        {"type": "breakfast", "name": "早餐推荐", "description": "早餐描述", "estimated_cost": 30},
        {"type": "lunch", "name": "午餐推荐", "description": "午餐描述", "estimated_cost": 50},
        {"type": "dinner", "name": "晚餐推荐", "description": "晚餐描述", "estimated_cost": 80}
      ]
    }
  ],
  "weather_info": [
    {
      "date": "YYYY-MM-DD",
      "day_weather": "晴",
      "night_weather": "多云",
      "day_temp": 25,
      "night_temp": 15,
      "wind_direction": "南风",
      "wind_power": "1-3级"
    }
  ],
  "overall_suggestions": "总体建议",
  "budget": {
    "total_attractions": 180,
    "total_hotels": 1200,
    "total_meals": 480,
    "total_transportation": 200,
    "total": 2060
  }
}
```

**重要提示:**
1. weather_info数组必须包含每一天的天气信息
2. 温度必须是纯数字(不要带°C等单位)
3. 每天安排2-3个景点
4. 考虑景点之间的距离和游览时间
5. 每天必须包含早中晚三餐
6. 提供实用的旅行建议
7. **必须包含预算信息**:
   - 景点门票价格(ticket_price)
   - 餐饮预估费用(estimated_cost)
   - 酒店预估费用(estimated_cost)
   - 预算汇总(budget)包含各项总费用
"""
# 加载环境变量
# 首先尝试加载当前目录的.env
load_dotenv()


# 获取环境变量
model = os.getenv("LLM_MODEL_ID")
base_url = os.getenv("LLM_BASE_URL")
model_key = os.getenv("LLM_API_KEY")
amap_key= os.getenv("AMAP_API_KEY")




class MultiAgentTripPlanner:
    """多智能体旅行规划系统"""
    def __init__(self):
        """仅同步初始化，不运行异步代码"""
        print("🔄 获取多智能体系统实例...")
        self.amap_mcp_config = {
            "url": "https://mcp.amap.com/sse?key=" + amap_key,
            "transport": "sse"
        }
        self.client = None
        self.tools = None
        self.llm = None
        self.attraction_agent = None
        self.weather_agent = None
        self.hotel_agent = None
        self.planner_agent = None
        self.attraction_agent_rs = None
        self.weather_agent_rs = None
        self.hotel_agent_rs = None
        self.planner_agent_rs = None
        self._initialized = False  # 添加初始化状态标志
    
    async def initialize(self):
        """异步初始化方法（从原Multi_agent函数迁移）"""
        if self._initialized:
            return
            
        print("🔄 开始初始化多智能体旅行规划系统...")
        
        self.client = MultiServerMCPClient({"amap_mcp": self.amap_mcp_config})
        self.tools = await self.client.get_tools()
        print(f"✅ 已加载 {len(self.tools)} 个工具")
        for tool in self.tools:
            tool._arun = rate_limit(rate=3, per=1.0)(tool._arun)
        print(f"✅ 已为工具添加速率限制: 每秒最多3次调用")



        self.llm = ChatOpenAI(
            model_name=model,
            openai_api_key=model_key,
            base_url=base_url,
            temperature=0
        )
        
        # 创建各个智能体
        print("  - 创建景点搜索Agent...")
        self.attraction_agent = create_agent(
            self.llm, self.tools, system_prompt=ATTRACTION_AGENT_PROMPT
        )
        
        print("  - 创建天气查询Agent...")
        self.weather_agent = create_agent(
            self.llm, self.tools, system_prompt=WEATHER_AGENT_PROMPT
        )
        
        print("  - 创建酒店推荐Agent...")
        self.hotel_agent = create_agent(
            self.llm, self.tools, system_prompt=HOTEL_AGENT_PROMPT
        )
        
        # print("  - 创建行程规划Agent...")
        # self.planner_agent = create_agent(
        #     self.llm, self.tools, system_prompt=PLANNER_AGENT_PROMPT
        # )
        print("  - 创建行程规划Agent...")
        self.planner_agent = create_agent(
            self.llm, system_prompt=PLANNER_AGENT_PROMPT
        )
        # while(self.attraction_agent is None or self.weather_agent is None or self.hotel_agent is None or self.planner_agent is None):
        #     await asyncio.sleep(1)
        self._initialized = True
        print("✅ 多智能体系统初始化完成")

    async   def plan_trip(self, request: TripRequest) -> TripPlan:
        """
        使用多智能体协作生成旅行计划

        Args:
            request: 旅行请求

        Returns:
            旅行计划
        """
        try:
            print(f"\n{'='*60}")
            print(f"🚀 开始多智能体协作规划旅行...")
            print(f"目的地: {request.city}")
            print(f"日期: {request.start_date} 至 {request.end_date}")
            print(f"天数: {request.travel_days}天")
            print(f"偏好: {', '.join(request.preferences) if request.preferences else '无'}")
            print(f"{'='*60}\n")

            print("📍 步骤1: 搜索景点...")
            attraction_query = self._build_attraction_query(request)
            self.attraction_agent_rs =await  self.attraction_agent.ainvoke(
                {"messages": [{"role": "user", "content": attraction_query}]}
            )


            # print(f"景点搜索结果: {attraction_response[:200]}...\n")

            # 步骤2: 天气查询Agent查询天气
            print("🌤️  步骤2: 查询天气...")
            weather_query = f"请查询{request.city}的天气信息"
            self.weather_agent_rs =await  self.weather_agent.ainvoke(
                {"messages": [{"role": "user", "content": weather_query}]}
            )


            # 步骤3: 酒店推荐Agent搜索酒店
            print("🏨 步骤3: 搜索酒店...")
            hotel_query = f"请搜索{request.city}的{request.accommodation}酒店"
            self.hotel_agent_rs = await self.hotel_agent.ainvoke(
                {"messages": [{"role": "user", "content": hotel_query}]}
            )




            print(f"景点搜索结果+++: {self.attraction_agent_rs['messages'][-1].content}")
            print(f"酒店搜索结果+++: {self.hotel_agent_rs['messages'][-1].content}")
            print(f"天气查询结果+++: {self.weather_agent_rs['messages'][-1].content}")

            # 步骤4: 行程规划Agent整合信息生成计划
            
            print("📋 步骤4: 生成行程计划...")
            planner_query = self._build_planner_query(request, self.attraction_agent_rs['messages'][-1].content, self.weather_agent_rs['messages'][-1].content, self.hotel_agent_rs['messages'][-1].content)
            print(f"行程规划查询: {planner_query}...\n")
            self.planner_agent_rs = await self.planner_agent.ainvoke(
                {"messages": [{"role": "user", "content": planner_query}]}
            )  
            # print(f"行程规划结果: {planner_response[:300]}...\n")
            print(f"行程规划结果: {self.planner_agent_rs['messages'][-1].content}")
            # 解析最终计划

            trip_plan = self._parse_response(self.planner_agent_rs['messages'][-1].content, request)

            print(f"{'='*60}")
            print(f"✅ 旅行计划生成完成!")
            print(f"{'='*60}\n")

            return trip_plan

        except Exception as e:
            print(f"❌ 生成旅行计划失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return self._create_fallback_plan(request)

    def _build_attraction_query(self, request: TripRequest) -> str:
        """构建景点搜索查询 - 直接包含工具调用"""
        keywords = []
        if request.preferences:
            # 只取第一个偏好作为关键词
            keywords = request.preferences[0]
        else:
            keywords = "景点"

        # 直接返回工具调用格式
        query = f"请使用amap_maps_text_search工具搜索{request.city}的{keywords}相关景点。\n[TOOL_CALL:amap_maps_text_search:keywords={keywords},city={request.city}]"
        return query

    def _build_planner_query(self, request: TripRequest, attractions: str, weather: str, hotels: str = "") -> str:
        """构建行程规划查询"""
        query = f"""请根据以下信息生成{request.city}的{request.travel_days}天旅行计划:

**基本信息:**
- 城市: {request.city}
- 日期: {request.start_date} 至 {request.end_date}
- 天数: {request.travel_days}天
- 交通方式: {request.transportation}
- 住宿: {request.accommodation}
- 偏好: {', '.join(request.preferences) if request.preferences else '无'}

**景点信息:**
{attractions}

**天气信息:**
{weather}

**酒店信息:**
{hotels}

**要求:**
1. 每天安排2-3个景点
2. 每天必须包含早中晚三餐
3. 每天推荐一个具体的酒店(从酒店信息中选择)
3. 考虑景点之间的距离和交通方式
4. 返回完整的JSON格式数据
5. 景点的经纬度坐标要真实准确
"""
        if request.free_text_input:
            query += f"\n**额外要求:** {request.free_text_input}"

        return query
    
    def _parse_response(self, response: str, request: TripRequest) -> TripPlan:
        """
        解析Agent响应
        
        Args:
            response: Agent响应文本
            request: 原始请求
            
        Returns:
            旅行计划
        """
        try:
            # 尝试从响应中提取JSON
            # 查找JSON代码块
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "{" in response and "}" in response:
                # 直接查找JSON对象
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
            else:
                raise ValueError("响应中未找到JSON数据")
            
            # 解析JSON
            data = json.loads(json_str)
            
            # 转换为TripPlan对象
            trip_plan = TripPlan(**data)
            
            return trip_plan
            
        except Exception as e:
            print(f"⚠️  解析响应失败: {str(e)}")
            print(f"   将使用备用方案生成计划")
            return self._create_fallback_plan(request)
    
    def _create_fallback_plan(self, request: TripRequest) -> TripPlan:
        """创建备用计划(当Agent失败时)"""
        from datetime import datetime, timedelta
        
        # 解析日期
        start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
        
        # 创建每日行程
        days = []
        for i in range(request.travel_days):
            current_date = start_date + timedelta(days=i)
            
            day_plan = DayPlan(
                date=current_date.strftime("%Y-%m-%d"),
                day_index=i,
                description=f"第{i+1}天行程",
                transportation=request.transportation,
                accommodation=request.accommodation,
                attractions=[
                    Attraction(
                        name=f"{request.city}景点{j+1}",
                        address=f"{request.city}市",
                        location=Location(longitude=116.4 + i*0.01 + j*0.005, latitude=39.9 + i*0.01 + j*0.005),
                        visit_duration=120,
                        description=f"这是{request.city}的著名景点",
                        category="景点"
                    )
                    for j in range(2)
                ],
                meals=[
                    Meal(type="breakfast", name=f"第{i+1}天早餐", description="当地特色早餐"),
                    Meal(type="lunch", name=f"第{i+1}天午餐", description="午餐推荐"),
                    Meal(type="dinner", name=f"第{i+1}天晚餐", description="晚餐推荐")
                ]
            )
            days.append(day_plan)
        
        return TripPlan(
            city=request.city,
            start_date=request.start_date,
            end_date=request.end_date,
            days=days,
            weather_info=[],
            overall_suggestions=f"这是为您规划的{request.city}{request.travel_days}日游行程,建议提前查看各景点的开放时间。"
        )


# 全局多智能体系统实例
_multi_agent_planner = None


async def get_trip_planner_agent() -> MultiAgentTripPlanner:
    """获取或创建多智能体规划器（异步版本）"""
    global _multi_agent_planner
    
    if _multi_agent_planner is None:
        _multi_agent_planner = MultiAgentTripPlanner()
        await _multi_agent_planner.initialize()  # 异步初始化
    
    return _multi_agent_planner

