整个把“传统可执行脚本”打通到 MCP 服务的流程，确实可以拆分成这三个关键层次。

---

## 一、第一层：工具元信息发现（Tools Meta Discovery）

### 1. 这层的核心目的

* **向上游客户端（比如 LangChain、LangGraph 等 MCP 客户端）“展示”有哪些可用的工具**，以及每个工具的输入/输出格式。
* 本质上就是实现一个对外的 `ListTools` 接口，让调用者发出 `{"jsonrpc":"2.0","id":...,"method":"ListTools","params":{}}` 时，能够得到类似下面这样的返回：

  ```json
  [
    {
      "name": "summarize",
      "description": "对一段文本进行摘要",
      "input_schema": { /* JSON Schema 描述 */ },
      "output_schema": { /* JSON Schema 描述 */ }
    },
    {
      "name": "translate",
      "description": "翻译文本到指定语言",
      "input_schema": { /* ... */ },
      "output_schema": { /* ... */ }
    }
    // …更多工具…
  ]
  ```

### 2. 可能的实现方式

1. **静态列表**

   * 最简单的做法就是在某个配置文件（或代码里硬编码）里维护一份工具元信息数组，直接把它序列化返回。
   * 优点：实现最简单，开箱即用；缺点：维护和扩展时，需要手动同步更新代码或配置。

2. **动态扫描 + 配置中心**

   * 如果工具非常多或者经常扩展，可以做一套“工具注册”机制：启动时扫描某个目录里所有符合规范的可执行文件/脚本，从文件名或约定的注释里提取名字和描述，再动态拼出工具元数据。
   * 也可以接入一个配置中心，将工具元数据存储到数据库或配置服务，Wrapper 启动后从里头拉取并暴露。
   * 优点：可维护性更高，新增一个工具只要把配置写到中心或按照约定放到目录里就行；缺点：复杂度上来，需要额外管理扫描逻辑或配置中心高可用。

### 3. 需要格外关注的点

* **输入/输出 Schema 的精准度**

  * 如果 input\_schema、output\_schema 定义不准确，客户端在构造参数或解析结果时就会出现问题。
  * 比如：摘要工具写成 `{"text": {"type": "string"}}`，却忘了把 `required: ["text"]` 加上，客户端可能传空值或传错字段也不会报错，到真正运行时才发现不行。所以在设计时，要务必把必填字段、字段类型写精准。

* **工具版本管理**

  * 当你把工具升级（比如改了参数名字或改了输出结构），需要在元信息里加版本号标识，否则客户端可能照旧传老参数或者按老输出结构解析。
  * 比较常见的做法是在元数据中加一个 `"version": "1.2.3"` 字段，或者在工具名字里加后缀（不推荐，只做临时兜底）。

* **权限/可见性**

  * 在一些场景下，并不是所有工具都对所有用户或所有场景都开放。元信息里可以加一个可见性字段（比如 `"public": true` 或 `"roles": ["admin","analyst"]`），Wrapper 在 ListTools 时做过滤。
  * 如果你只是简单地给内部团队调试用，暂时可以不考虑这一块。

---

## 二、第二层：Wrapper（将可执行脚本／程序包装成 STDIO JSON 接口）

### 1. 这层的核心职责

* **把“调用一个或多个底层可执行文件”的过程，转换成“行级 JSON STDIO 交互”**。
* 外部上层（Adapter）只跟 Wrapper 打交道——对它写入 JSON 请求，对它按行读出 JSON 响应即可；而 Wrapper 则在内部完成：

  1. 读一行 JSON → `json.loads(line)` → 得到 `method`（ListTools／CallTool）及相关参数。
  2. 如果是 `ListTools`，直接把工具元信息输出成一行 JSON（对应第一层里维护的元数据）。
  3. 如果是 `CallTool`，根据 `tool_name` 在内部分发到相应的可执行脚本／程序，捕获子进程的 stdout/stderr、退出码，封成一行 JSON 发回。
  4. 如果工具本身需要“流式输出多个中间结果”，就做“逐行读子进程 stdout → 每次封装一条 JSON(带 `partial: true` 标识) → flush → 直到子进程结束后再输出 `partial: false` 的最终结果”。

### 2. 实现要点和常见变体

1. **“读一行 JSON → 写一行 JSON” 的规范**

   * Wrapper 必须严格做到：从 stdin 调用 `for line in sys.stdin`（或类似方式）逐行读取完整的 JSON；从 stdout 每次写 `print(json.dumps(obj), flush=True)`，确保一条输出也是完整一行 JSON。
   * 这套“行边界”机制是为了让 Adapter 在读取时无歧义地做 `readline()`。如果发生粘包或没有及时 flush，就会导致 Adapter 端一直读不到整行、或者把多条 JSON 合并到一起，前端解析就会报错。

2. **同步调用 vs 异步流式**

   * **同步调用（subprocess.run）**：Wrapper 从 `CallTool` 拿到参数后，用 `subprocess.run([...], stdout=PIPE, stderr=PIPE, timeout=…)` 等待子进程跑完、一次性拿到结果，再包成一个完整的 JSON 一次性输出。适合那些“工具本身不需要实时中间结果、只在结束后才有输出”的场景。
   * **异步流式（subprocess.Popen）**：Wrapper 先用 `proc = subprocess.Popen([...], stdout=PIPE, stderr=PIPE, text=True)`，然后做：

     ```python
     for out_line in proc.stdout:
         # out_line 带 \n，需要 strip 掉
         partial_resp = {
             "jsonrpc": "2.0",
             "id": request_id,
             "partial": True,
             "data": out_line.strip()
         }
         print(json.dumps(partial_resp), flush=True)
     proc.wait()  # 等最后结束后拿 returncode、stderr
     # 输出最后一条 partial=False 的“完成”消息
     final_resp = { ... }
     print(json.dumps(final_resp), flush=True)
     ```

     这样 Adapter 能把中间结果当 SSE 逐条发给前端，前端就能做到“流式呈现”。

3. **错误处理**

   * 包装时要对以下几种情况分别返回正确的 JSON-RPC 错误格式：

     1. **JSON 解析出错**：比如传进来的那一行根本不是合法 JSON，就 `print({"jsonrpc":"2.0","id":null,"error":{ "code":-32700,"message":"Parse error"}})`。
     2. **非法方法**：传 `method` 既不是 “ListTools” 也不是 “CallTool”，`{"jsonrpc":"2.0","id":..., "error":{"code":-32601,"message":"Method not found"}}`。
     3. **调用工具失败**：子进程超时/崩溃/退出码非零时，把 stderr 当作 “error.message” 返回，或者做一个通用的 `{"code":-32000,"message":"Internal error"}`。
   * 只有这样，Adapter 才不会因为某条响应不是合法的 JSON-RPC 结构而直接崩掉。

4. **多工具并发调用**

   * 如果有可能一个 Wrapper 同时要处理多个并发请求，就得在 Wrapper 内部做并发管理。最简单的做法是：

     * **不复用进程**：每次请求 CallTool，都马上启动一个独立的子进程、等它结束后返回，再继续下一个请求。这样 Wrapper 只要按请求依次处理就行，性能瓶颈在进程启动上。
     * **进程池或长驻子进程**：如果工具启动成本高，可以自己在 Wrapper 里维护一个“工具子进程池”或“持久化子进程”，然后分配给并发请求使用。但这样就要在 Wrapper 内部做“请求ID→子进程输出” 的映射和管理，复杂度较高。
   * 如果并发非常大，建议把 Wrapper 做成一个“多线程/多协程+进程池” 的混合结构，再用队列协调请求，确保“子进程输出不会混淆到别的请求”。

---

## 三、第三层：Adapter（HTTP → STDIO → SSE）

### 1. 这层的核心职责

* **对外提供一个 HTTP 服务接口（通常是一个 `/mcp` 路由），让上游客户端可以通过 HTTP POST 发送 JSON-RPC 请求**
* **在后端把收到的 HTTP 请求体（完整的一段 JSON）原封不动地写入到 Wrapper 的 stdin（或对应的子进程 stdin）**
* **同时，不断从 Wrapper stdout（或子进程 stdout）中按行读取响应 JSON，并包装成 SSE（`text/event-stream`）格式，持续推送给前端**
* 客户端看到的是一个标准的 “`Content-Type: text/event-stream` → SSE 事件流”，哪怕底层原本是奔 STDIO 与 Wrapper 交互，也完全不需要感知这层。

### 2. 实现要点

1. **FastAPI（或 Flask）Server**

   * 常见用法是：

     ```python
     @app.post("/mcp")
     async def mcp_endpoint(request: Request):
         request_json = await request.json()
         # 通常把 request_json 序列化成一行 bytes
         generator = run_wrapper_subprocess_and_stream(request_json)
         return StreamingResponse(generator, media_type="text/event-stream")
     ```
   * `run_wrapper_subprocess_and_stream` 的伪逻辑：

     1. `proc = await asyncio.create_subprocess_exec("python", "wrapper.py", stdin=PIPE, stdout=PIPE)`
     2. `proc.stdin.write(json.dumps(request_json).encode("utf-8") + b"\n")` 且 `await proc.stdin.drain(); proc.stdin.close()`
     3. `while True: line = await proc.stdout.readline(); if not line: break; yield b"data: " + line + b"\n\n"`
     4. `await proc.wait()`

2. **保证每行都是完整的 JSON**

   * 前面在 Wrapper 里已经保证“每行输出都是一条完整 JSON 并 flush”，这样 Adapter 端的 `await proc.stdout.readline()` 才能拿到一整行，直接拼成 SSE 推给客户端。
   * 如果 Wrapper 出现输出缓冲、没加 flush 的情况，就会导致 `readline()` 阻塞，SSE 一直卡在那，客户端根本收不到任何消息。

3. **并发与子进程管理**

   * 如果 `/mcp` 路由同时接到多个并发请求，FastAPI 默认会为每个请求都分别调用一次 `run_wrapper_subprocess_and_stream`，也就是每个请求都会单独启动一个 Wrapper 进程。
   * 如果流量非常大，这么多进程同时启动/销毁，会带来显著开销。可选优化：

     1. **统一 Wrapper 长驻**：让 Adapter 在启动时就把 Wrapper 做成**单个长驻进程**，并在 Dispatcher 里用锁或队列方式把不同请求的 JSON 依次写进去：

        * 底层 Wrapper 要能区分不同请求（通过 `id` 字段）并按顺序输出相应 JSON。
        * 缺点是**请求混合、长驻单进程故障后影响所有请求**，需要谨慎设计。
     2. **子进程池**：Adapter 里本身做一层管理，维护一个“可复用 Wrapper 进程池”或“可复用原始工具进程池”，并发请求时先向池里借一个子进程，用完后归还，避免频繁创建子进程。

        * 复杂度更高，需要在 Adapter 层做“请求ID与 stdout 行之间的映射”。

4. **SSE 细节**

   * Adapter 使用 `StreamingResponse(generator, media_type="text/event-stream")`，并且在 `generator` 里要输出符合 SSE 规范的文本：

     ```
     data: <一行完整 JSON 字符串>\n\n
     ```

     这样前端才能一条条拿到每个事件。常见的坑有：

     * 忘记在每次 `yield` 里加上 `\n\n`，导致前端一直不触发 `onmessage`。
     * 没加 `Content-Type: text/event-stream;charset=utf-8`，有些客户端对编码比较敏感。
   * 如果想给 SSE 事件加 `id: `、`event: ` 字段，可以在生成时按：

     ```
     id: <请求ID或随机ID>\n
     event: <eventType>\n
     data: <payload>\n
     \n
     ```

---

## 四、三层之间的关系与整体流程图

把这三层组合起来，整个 MCP 服务的调用链大致如下：

```mermaid
flowchart TD
  subgraph Client
    A[上游客户端（LangChain/自定义）] 
    A -->|POST JSON-RPC| B[/HTTP POST /mcp/]
    B -->|接收 SSE 流| A
  end

  subgraph Adapter (FastAPI)
    B[POST /mcp 路由] --> C[spawn subprocess \n("python wrapper.py")]
    C --> D[写一行 JSON (stdin)] 
    E[读 stdout (一行一行)] --> F[封为 SSE ] 
    F -->|持续 push| B
  end

  subgraph Wrapper (wrapper.py)
    D --> G[parse JSON \n(method,ListTools/CallTool)] 
    G -->|ListTools| H[返回工具元数据 JSON 一行] --> E
    G -->|CallTool| I[执行子工具脚本（sum_tool.sh/translate.py/...）]
    I -->|拿到 stdout/stderr| J[封装成 result 或 error JSON 一行] --> E
  end
```

* **第一层**：`ListTools` 逻辑 从 `G -> H`，把工具信息暴露给上游。
* **第二层**：`CallTool` 逻辑 从 `G -> I -> J`，把指定工具脚本的输出转成行级 JSON。
* **第三层**：Adapter 把 HTTP 请求转给 Wrapper，把 Wrapper 的 stdout（一行行 JSON）转为 SSE 事件推给客户端。

---

## 五、几点「实事求是」的提醒

1. **如果只是对接非常少量、功能单一的小工具**，完全可以把「第一层的元信息」写死在代码里，用最简单的静态列表；只要后续工具不经常变化，就没必要搞太复杂的动态扫描和配置中心。

2. **如果工具本身本就支持“读 stdin/输出 JSON”**（比如自己写的 Python 函数、本身就是符合 JSON-RPC 规范的脚本），那么包装器可以直接把这段逻辑复用过来，甚至可以不写也许就能用——但前提是“工具一定要按行输出 JSON”。你只要保证它满足“行级 JSON STDIO 接口”的契约，Adapter 就能无感对接。

3. **并发高并发场景要谨慎**：

   * 每个请求都新建一个 Wrapper 进程、再从 Wrapper 去 spawn 工具进程，开销较大。
   * 如果并发请求几十、上百，建议做“子进程复用池”或在 Wrapper 层争取把同一个 Python 进程长驻，把子工具作为线程/协程/子进程池管理。
   * 任何把“STDIO”模式长驻并发，多半要自己写大量协调逻辑，保证“请求ID 对应输出 ID”不会混淆。这块一旦出错，最容易造成“调用方挂起、客户端收不到预期响应、子进程成为僵尸”等问题。

4. **工具元信息要及时更新、严谨**：

   * 你写了一套 “Tools Meta Discovery” 并写死在 Wrapper 里，如果后续再加新脚本或改参数，需要同步更新这份元信息，否则客户端一旦照旧发老参数，就会在 `CallTool` 里被 Wrapper 拒绝。
   * 如果你后续想做“插件化”或“动态加载工具”（在某个目录里放 `.py`、`.sh` 即可自动成为新工具）就要实现“反射/扫描”机制：

     1. 约定好每个工具脚本里某个注释块或头部有元信息字段，Wrapper 启动时扫描目录、解析注释、动态拼 ListTools 返回。
     2. 或者在某个配置文件里写好工具映射（名字→脚本路径→参数定义），Wrapper 读配置文件生成元信息，并动态调用。

5. **安全性与沙箱隔离**：

   * 如果任何人都能对你的 MCP 服务发 `CallTool`，并且底层工具全都放在同一台机器的文件系统里，就可能有人通过传参数来执行恶意命令或访问不该访问的文件。
   * 建议对每个 `tool_name` 做严格白名单校验，并且只允许它调用指定可执行文件，参数也要做校验（例如 `text.replace('"','\"')` 之类，避免命令注入）。
   * 如果需要更高安全性，可以用 Docker 或者 Firejail 把每个工具进程隔离在独立容器/沙箱里，Wrapper 只负责下发命令，不让它直接访问主机。

---

## 六、小结

你的“**第一层：Tools Meta Discovery；第二层：Wrapper；第三层：Adapter**”这种分层思路，非常合理：

1. **Tools Meta Discovery（元信息暴露）**：告诉调用方“我到底有哪几把工具可用、每把工具需要什么参数、会返回什么”，这是 MCP 协议的必备环节，不可或缺。
2. **Wrapper（统一 STDIO JSON 接口）**：把各种各样的底层可执行脚本／程序包装成“行级 JSON STDIO”契约，让上层无差别地与之交互——所有请求都走 STDIN→STDOUT，结果全部以一行 JSON 返回。
3. **Adapter（HTTP → STDIO → SSE）**：把客户端的 HTTP POST（JSON-RPC）转到 STDIO、把 STDIO 输出转成 SSE 推给客户端，让使用者感知不到底层 STDIO，觉得这是一个“标准的 MCP HTTP 服务”。

只要保证这三层之间“契约一致”——也就是：

* Adapter 知道用哪种方式把 HTTP 请求写到 Wrapper stdin，并用 SSE 逐行转发 Wrapper stdout。
* Wrapper 严格用“每行一条 JSON → flush → 继续” 的规范回应 ListTools/CallTool。
* Tools Meta Discovery 描述准确、与 Wrapper 内部分发逻辑保持同步。

这套体系就能稳定运行。如果以后有更复杂需求（高并发、动态插件、安全隔离等），可以在各层做拆分或增强，但总体框架基本不会变。你这个三层划分，能够让各团队成员（API 维护、脚本开发、运维部署）各司其职，职责也清晰明了。非常赞，希望这个分层思路能对你后续落地和扩展提供清晰的参考。加油！
