# P05 JMX 脚本 — perf-jmx-generator

## 解决的问题

在 JMeter GUI 里手动配置场景、断言、参数化，一个场景配半小时且易配错。

## 触发词

- 生成 JMeter 脚本 / 生成 JMX / jmeter script / jmx generator
- perf jmx / 压测脚本生成

## 输入

- 接口列表 / 参数化需求 / SLA 指标

## 输出

1. 场景模板（查询/下单/登录/搜索 每类带推荐配置）
2. 完整 JMX 文件（可直接在 JMeter 中打开运行）
3. 参数化配置（CSV Data Set Config + 变量引用）
4. 跨平台 Prompt 模板

---

## 场景模板库

### 查询类模板

| 配置项 | 推荐值 |
|--------|--------|
| 线程组 | 目标并发数 |
| Ramp-up | 并发数 / 5（秒），最低 60 秒 |
| 循环次数 | 永久 |
| 持续时间 | 基线 5 分钟 |
| HTTP 请求默认值 | 协议+域名+端口+Content-Type |
| 断言 | 响应码 200 + 业务码断言 |
| 参数化 | CSV Data Set Config（分页页码/查询条件） |

### 下单类模板

| 配置项 | 推荐值 |
|--------|--------|
| 线程组 | 目标并发数 |
| Ramp-up | 并发数 / 10（秒），防止并发写冲突 |
| HTTP 请求 | POST + JSON Body + 变量引用 |
| 断言 | 响应码 200 + 业务码=0/success |
| 参数化 | CSV（商品ID/用户ID/数量） |
| 前置处理器 | JSR223 PreProcessor（时间戳/唯一ID生成） |
| 后置处理器 | JSON Extractor（提取订单ID给下游接口） |

### 登录类模板

| 配置项 | 推荐值 |
|--------|--------|
| HTTP 请求 | POST + JSON Body（账号+密码+验证码） |
| 后置处理器 | JSON Extractor（提取 Token） |
| 关联 | Token 管理器（Regex Extractor + BeanShell PostProcessor） |
| 断言 | 响应码 200 + Token 非空 |

### 搜索类模板

| 配置项 | 推荐值 |
|--------|--------|
| 参数化 | CSV Data Set Config（多种关键词，中英文/特殊字符/超长） |
| 断言 | 响应码 200 + 结果数 ≥ 0 |
| 监听器 | 响应时间+返回数据大小 |

---

## JMX 文件结构

```
Test Plan
├── User Defined Variables (基础配置)
├── HTTP Request Defaults (协议/域名/端口/超时)
├── HTTP Cookie Manager (可选)
├── CSV Data Set Config (参数化文件)
├── Thread Group
│   ├── HTTP Request (登录)
│   │   ├── JSR223 PreProcessor (动态参数)
│   │   ├── JSON Extractor (提取Token)
│   │   └── Response Assertion (断言)
│   ├── HTTP Header Manager (Token)
│   ├── HTTP Request (业务接口1)
│   │   ├── JSON Extractor (关联提取)
│   │   └── Response Assertion (断言)
│   └── HTTP Request (业务接口2)
│       └── Response Assertion (断言)
├── Aggregate Report (聚合报告)
├── View Results Tree (调试用,压测时关闭)
└── Backend Listener (可选, InfluxDB上报)
```

## 断言封装规则

| 断言类型 | 配置 |
|----------|------|
| 响应码断言 | 200 / 201 |
| 业务码断言 | JSON Assertion + $.[code] = 0 |
| 响应时间断言 | Duration Assertion（阈值 = SLA P95 × 1.5） |
| 响应体非空断言 | Size Assertion > 0 |

## 参数化配置规范

1. CSV 文件首行为列名，逗号分隔
2. 文件放置于 JMeter bin/ 目录或绝对路径引用
3. 变量命名遵循 `{模块}_{属性}` 格式，如 `order_userId`
4. CSV Data Set Config 配置：
   - Sharing Mode: All threads / Current thread group（写接口用）
   - EOF: Stop Thread / Recycle（按需）
   - Delimiter: 逗号

---

## 跨平台 Prompt 模板

```
你是一个 JMeter 脚本生成工程师。根据用户提供的接口列表和参数化需求，生成可直接运行的 JMX 脚本模板。

场景模板（按接口类型选择）:

1. 查询类模板:
   - 线程组: 目标并发数，ramp-up=并发数/5(最低60s)，循环=永久
   - HTTP 请求默认值: 协议+域名+端口+Content-Type
   - 断言: 响应码200 + 业务码断言
   - 参数化: CSV Data Set Config

2. 下单类模板:
   - 线程组: ramp-up=并发数/10（防并发写冲突）
   - HTTP 请求: POST + JSON Body + 变量引用
   - 断言: 响应码200 + 业务码=0/success
   - 前置: JSR223 PreProcessor（时间戳/唯一ID）
   - 后置: JSON Extractor（提取下游关联数据）

3. 登录类模板:
   - POST + JSON（账号+密码）
   - 后置: JSON Extractor 提取 Token
   - HTTP Header Manager 注入 Authorization

4. 搜索类模板:
   - CSV 参数化: 多关键词（中英文/特殊字符/超长）
   - 响应码 + 结果数 ≥ 0 断言

JMX 文件结构（必需组件）:
- User Defined Variables
- HTTP Request Defaults
- CSV Data Set Config（写接口注意 Sharing Mode）
- Thread Group:
  - HTTP Request + PreProcessor(如需要) + Extractor(如需要) + Assertion
- Aggregate Report
- View Results Tree（仅调试用）

断言规则:
- 响应码断言: 200/201
- 业务码断言: JSON Assertion $.[code]=0
- 响应时间断言: Duration Assertion < SLA_P95 * 1.5
- 响应体非空断言: Size Assertion > 0

参数化规范:
- CSV 首行列名，逗号分隔
- 变量名: {模块}_{属性}，如 order_userId
- 写接口 Sharing Mode=Current thread，EOF=Stop Thread
```