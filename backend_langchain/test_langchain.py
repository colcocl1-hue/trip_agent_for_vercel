"""配置管理模块"""
from datetime import datetime
import json
import time
from typing import Dict, Any, List
from hello_agents import SimpleAgent
from hello_agents.tools import MCPTool
import asyncio
import langchain
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
from typing import List
from typing import Any, Callable
langchain.debug = True  # 启用LangChain调试模式，输出详细日志 
prompt = """行程规划查询: 请根据以下信息生成海口的1天旅行计划:

**基本信息:**
- 城市: 海口
- 日期: 2026-02-09 至 2026-02-09
- 天数: 1天
- 交通方式: 公共交通
- 住宿: 经济型酒店
- 偏好: 无

**景点信息:**
已为您搜索到海口的景点相关景点，以下是一些热门景点：

1. **假日海滩旅游区** - 滨海大道126号
2. **西秀海滩公园** - 海秀街道滨海大道163号
3. **万绿园** - 滨海大道38号
4. **海口骑楼老街历史文化街区** - 长堤路5-1号
5. **白沙门公园** - 海甸六东路与人民大道交汇处
6. **雷琼世界地质公园(海口园区)** - 石山镇风景路89号
7. **世纪公园** - 港湾路与世纪公园三横路交叉口东北120米
8. **海南长影奇幻乐园** - 椰海大道100号
9. **西海岸带状公园** - 滨海大道与长彤路交叉口西500米
10. **五源河入海口** - 五源河国家湿地公园内(北侧)

如需了解某个景点的详细信息（如开放时间、门票、交通方式等），请告诉我具体景点名称，我将为您查询！

**天气信息:**
海口市未来四天的天气预报如下：

- **2026年2月9日（周一）**：白天和夜间均为多云，气温18℃~24℃，北风1-3级。
- **2026年2月10日（周二）**：白天和夜间均为多云，气温19℃~26℃，北风1-3级。
- **2026年2月11日（周三）**：白天和夜间均为多云，气温18℃~26℃，北风1-3级。
- **2026年2月12日（周四）**：白天和夜间均为多云，气温19℃~24℃，北风1-3级。

总体来看，海口近期天气以多云为主，气温适宜，风力较小。

**酒店信息:**
以下是海口的经济型酒店推荐：

1. **海口嘉美华宾馆(龙湖天街金牛岭公园店)**
   - 地址：海口市保税区公安局宿舍西南门东50米

2. **金泉宾馆(滨涯路)**
   - 地址：滨涯路24号

3. **海口福鑫宾馆(海甸三西路店)**
   - 地址：三西路肯德基斜对面1号楼3层

4. **海口九龙宾馆**
   - 地址：三江镇北街23号

5. **琼驿智能酒店(海口高铁东站凤翔东路店)**
   - 地址：凤翔东路6号

6. **海口福源宾馆**
   - 地址：海甸岛海彤路12号

7. **海口金裕宾馆**
   - 地址：凤翔东路2号(近师大、凤翔湿地公园)

8. **海口乙歆宾馆**
   - 地址：海甸岛人民西里277号

9. **海口香灵旅租**
   - 地址：灵山镇琼文大道93号

10. **海悦宾馆(青年路)**
    - 地址：青年路38-1号

如需了解某家酒店的详细信息（如价格、设施、用户评价等），请告诉我具体酒店名称，我可以为您进一步查询！

**要求:**
1. 每天安排2-3个景点
2. 每天必须包含早中晚三餐
3. 每天推荐一个具体的酒店(从酒店信息中选择)
3. 考虑景点之间的距离和交通方式
4. 返回完整的JSON格式数据
5. 景点的经纬度坐标要真实准确
..."""

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



print(f"amap_key: {amap_key}")





import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient  
from langchain.agents import create_agent
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


# class RateLimiter:
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
#         self.num=3
#     async def acquire(self):
#         self.num-=1

num=0
class RateLimiter:
    """令牌桶速率限制器"""
    def __init__(self, rate: int, per: float,num: int):
        """
        :param rate: 允许的请求数
        :param per: 时间窗口（秒）
        """
        self.rate = rate
        self.per = per
        self.tokens = rate
        self.updated_at = time.monotonic()
        
        self.num=num

    async def acquire(self):
        """获取一个令牌，如果超出限制则等待"""
        while self.tokens < 1:
            now = time.monotonic()
            elapsed = now - self.updated_at
            # 计算这段时间内应新增的令牌数
            self.tokens = min(self.rate, self.tokens + elapsed * (self.rate / self.per))
            self.updated_at = now
            if self.tokens < 1:
                # 令牌不足，等待下一个令牌生成的时间
                # wait_time = (1 - self.tokens) * (self.per / self.rate)
                wait_time = 1 
                await asyncio.sleep(wait_time)
                print(f"等待 {wait_time:.2f} 秒以获取令牌...")
        self.tokens -= 1  # 消耗一个令牌
        print(f"{self.num}获取令牌成功，剩余令牌数: {self.tokens:.2f}")
        return True


def rate_limit(rate: int, per: float):
    """限流装饰器，限制函数调用频率"""
    def decorator(func):
        last_called = 0.0
        num_calls = 0  # 使用不同的变量名避免冲突
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            nonlocal last_called, num_calls  # 声明为非局部变量
            
            current_time = time.time()
            time_since_last_call = current_time - last_called
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            print(f"[{current_time}] 🔧 令牌消耗 - 函数: {func.__name__}")
            if time_since_last_call < per / rate:
                # 等待适当的时间
                await asyncio.sleep(0.5)
            
            last_called = time.time()
            num_calls += 1
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# def rate_limit(rate: int, per: float = 1.0):
#     """装饰器：限制被装饰的异步函数调用频率"""
#     num+=1
#     limiter = RateLimiter(rate=3, per=1.0,num=num)  # 每秒最多3次调用
#     def decorator(func):
#         @wraps(func)
#         async def wrapper(*args, **kwargs):
#             # 获取令牌
#             await limiter.acquire()
            
#             # 获取当前时间
#             current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            
#             # 获取函数名
#             func_name = func.__name__
            
#             # 获取工具名称（如果有）
#             tool_name = "未知"
#             if args and hasattr(args[0], 'name'):
#                 tool_name = args[0].name
#             elif args and hasattr(args[0], '__class__'):
#                 # 尝试从类名获取
#                 tool_name = args[0].__class__.__name__
            
#             # 打印令牌消耗信息
#             print(f"[{current_time}] 🔧 令牌消耗 - 函数: {func_name}, 工具: {tool_name}")
            
#             # 调用原始函数
#             return await func(*args, **kwargs)
        
#         return wrapper
#     return decorator

# def rate_limit_mcp(interval=0.4):
#     last_call = 0
#     lock = asyncio.Lock()
    
#     def decorator(func):
#         @wraps(func)
#         async def wrapper(*args, **kwargs):
#             nonlocal last_call
#             async with lock:
#                 now = time.time()
#                 elapsed = now - last_call
#                 if elapsed < interval:
#                     await asyncio.sleep(interval - elapsed)
#                 last_call = time.time()
#                 return await func(*args, **kwargs)
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

# 应用装饰器

async def main():


    amap_mcp_config = {

            "url": "https://mcp.amap.com/sse?key="+amap_key,
            "transport": "sse"
    
    }
    client = MultiServerMCPClient(  
        {
            "amap_mcp": amap_mcp_config
                    
        
        }
    )
  
    tools = await client.get_tools()


    print(tools[1].name)
    print(f"✅ 已加载 {len(tools)} 个工具")

    # for i, tool in enumerate(tools):
    # # 获取原始函数
    #   original_arun = tool._arun
      
    #   # 应用装饰器
    #   @rate_limit_mcp(interval=0.4)
    #   async def wrapped_arun(*args: Any, **kwargs: Any) :
    #       return await original_arun(*args, **kwargs)
      
    #   # 替换工具方法
    #   tool._arun = wrapped_arun

    print(f"✅ 已为工具添加速率限制: 每{0.4}秒最多1次调用")

    for i, tool in enumerate(tools):
        original_arun = tool._arun
        # 使用独立的速率限制器实例
        decorated_func = rate_limit( rate=3, per=1.0)(original_arun)
        tool._arun = decorated_func
        
        # 测试每个工具的速率限制
    print(f"✅ 已为工具 ' 添加速率限制: 每秒最多3次调用")

    # for tool in tools:
    #     tool._arun = rate_limit(rate=3, per=1.0)(tool._arun)
    # print(f"✅ 已为工具添加速率限制: 每秒最多3次调用")


    llm = ChatOpenAI(
        model_name=model,
        openai_api_key=model_key,
        base_url=base_url,
        temperature=0
    )
    

    print("  - 创建景点搜索Agent...")
    secnce_search_agent = create_agent(
        llm,
        tools  ,
        system_prompt=ATTRACTION_AGENT_PROMPT
    )

        # 创建天气查询Agent
    print("  - 创建天气查询Agent...")
    weather_agent = create_agent(
        llm,
        tools,
        system_prompt=WEATHER_AGENT_PROMPT  
    )

    # 创建酒店推荐Agent
    print("  - 创建酒店推荐Agent...")
    hotel_agent = create_agent(
         llm,
        tools,
        system_prompt=HOTEL_AGENT_PROMPT
    )


    # 创建行程规划Agent(不需要工具)
    print("  - 创建行程规划Agent...")
    planner_agent = create_agent(
        llm,
        tools,
        system_prompt=PLANNER_AGENT_PROMPT

    )

    weather_response = await weather_agent.ainvoke(
        {"messages": [{"role": "user", "content": " 兰州今天天气怎么样?"}]}
    )
    print(f"Weather Response: {weather_response['messages'][-1].content}")

    plan_response = await planner_agent.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]}
        )

    print(f"Plan Response: {plan_response['messages'][-1].content}")


    # print(weather_response["structured_response"])

    # 使用示例
    # weather_result = get_final_weather_result(weather_response)
    # print(weather_result)



if __name__ == "__main__":


    asyncio.run(main())





