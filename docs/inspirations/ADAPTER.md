我已经记住了之前那套“STDIO→SSE 适配器”的思路，下面针对“不使用 Knative”的场景，给出如何将一个纯 Python 脚本（只能通过 stdin/stdout 交互的 MCP 服务）包装成一个 HTTP+SSE 服务的完整方案。核心思路与 Knative 版本几乎一致，只是部署方式改为直接运行或使用 Docker／docker-compose，而不是靠 Knative Serving 来托管。

---

## 一、整体思路回顾

1. **原始对象**

   * 有一个 Python 脚本（比如 `stdio_mcp_server.py`），它启动后会从标准输入读取一行 JSON 请求，然后在标准输出里写出对应的 JSON 响应（按行分隔）。
   * 举例：在命令行里，可以这样运行：

     ```bash
     $ python stdio_mcp_server.py < request.json > response.json
     ```
   * 但我们想让它“长驻后台”，并且接受来自 HTTP 客户端的 JSON 请求，然后把它当作 stdin 发给脚本，再把脚本 stdout 输出的多段 JSON 持续通过 SSE 推给客户端。

2. **封装层（Adapter）**

   * 写一个 **FastAPI**（也可以用 Flask，但 FastAPI 原生支持异步、配合 `StreamingResponse` 更方便做 SSE）的小程序 `adapter_service.py`。
   * 主要功能：

     1. `/mcp` 端点：接受 HTTP POST，Body 是 JSON → 将这份 JSON 按 MCP 协议写入子进程 STDIN → 异步读取子进程 STDOUT 的每一行/每一片 JSON → 封装成 SSE（`text/event-stream`）→ 推给客户端。
     2. 其他辅助端点：比如 `/healthz`、`/metrics`（可选）用于健康检查、监控。

3. **部署方式**

   * 最简单：本地直接用 `uvicorn adapter_service:app --host 0.0.0.0 --port 8000` 把 Adapter 服务跑起来。
   * 稍复杂一些：用 Docker 把 `adapter_service.py` 和 `stdio_mcp_server.py`（或编译后的可执行文件）打到一个镜像里，跑在任意有 Docker 的机器上。
   * 也可以用 `docker-compose`，或者把镜像推到某个云主机，再配合 Systemd／supervisor 做进程托管。

4. **客户端消费**

   * 任何支持 SSE 的客户端都能访问 `http://<host>:<port>/mcp`，发一个 HTTP POST，之后持续接收服务器推送的 SSE 片段。
   * 例如浏览器里用 `fetch` + `ReadableStream` 或者用 `EventSource`（如果 MCP 输出符合严格的 SSE 语法），也可以在命令行用 `curl -N` 测试。

---

## 二、编写 Adapter 服务（adapter\_service.py）

以下示例假设：

* 你本地有一个脚本 `stdio_mcp_server.py`（或可执行文件 `stdio_mcp_server`），它按照「每行一个 JSON，stdin → stdout」的方式工作。
* 我们使用 Python 3.8+，以及 FastAPI + uvicorn 来做 HTTP + SSE 转发。

```python
# file: adapter_service.py

import asyncio
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse

app = FastAPI()

# ---------------------------------------------------------------------
# 假设你的 STDIO MCP 脚本在同一目录下，文件名是 stdio_mcp_server.py
# 如果它已经打包成可执行文件，比如 ./stdio_mcp_server，也可以直接改这里。
# 下面示例采用："python stdio_mcp_server.py"
# ---------------------------------------------------------------------
STDIO_MCP_CMD = ["python", "stdio_mcp_server.py"]


async def run_stdio_mcp_and_stream(request_json: dict):
    """
    启动一个 STDIO MCP 子进程，把 request_json 写到它的 STDIN 中，
    然后不停地从 STDOUT 中读取“每行输出”（假设一行一条 JSON），
    包装成 SSE（data: <...>\n\n），yield 回给客户端。

    注意：如果客户端取消连接，需要捕获 CancelledError 并 kill 子进程。
    """
    # 1. 启动子进程（STDIO_MCP_CMD 要根据实际情况改）
    proc = await asyncio.create_subprocess_exec(
        *STDIO_MCP_CMD,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # 2. 把 HTTP Body 的 JSON 以“单行 JSON + 换行”写入子进程 stdin
    request_line = (json.dumps(request_json) + "\n").encode("utf-8")
    proc.stdin.write(request_line)
    await proc.stdin.drain()
    # MCP 脚本如果需要 EOF 才开始处理，就把 stdin 关掉；否则可保留打开做双向长连接
    proc.stdin.close()

    # 3. 循环读取子进程的 stdout（假设每次读到一行完整 JSON），封装成 SSE 给客户端
    try:
        while True:
            line = await proc.stdout.readline()
            if not line:
                break  # 子进程 stdout EOF，说明 MCP 脚本已自然退出
            text = line.decode("utf-8").strip()
            if not text:
                continue
            # 拼成 SSE 格式：每个事件都以 "data: ...\n\n" 结束
            sse_payload = f"data: {text}\n\n"
            yield sse_payload.encode("utf-8")
    except asyncio.CancelledError:
        # 客户端断开连接，主动 kill 子进程，避免它变成僵尸
        proc.kill()
        raise
    finally:
        await proc.wait()


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """
    1. 读取客户端发来的 JSON
    2. 调用 run_stdio_mcp_and_stream，把它转换成 SSE 流
    3. 返回 StreamingResponse，media_type 设置为 text/event-stream
    """
    try:
        request_json = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_generator = run_stdio_mcp_and_stream(request_json)
    return StreamingResponse(event_generator, media_type="text/event-stream")


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
```

### 解释要点

1. **子进程命令 (`STDIO_MCP_CMD`)**

   * 如果你的 STDIO 脚本是 `stdio_mcp_server.py`，且需要直接运行，则可以写成 `["python", "stdio_mcp_server.py"]`。
   * 如果你把它打包成可执行文件（比如 `chmod +x stdio_mcp_server`），那可以直接写 `["./stdio_mcp_server"]`。
   * 重点是：确保在当前工作目录下能直接启动并能用 stdin/stdout 交互。

2. **`asyncio.create_subprocess_exec`**

   * 这里指定 `stdin=PIPE, stdout=PIPE, stderr=PIPE`，目的在于：

     * 把请求 JSON 写给脚本的 stdin
     * 从脚本的 stdout 一行行读取它的输出
     * 如果客户端断开，要能及时 `proc.kill()` 清理

3. **SSE 格式**

   * SSE 要求 Content-Type 为 `text/event-stream`，并且每条事件都需要 `data: <payload>\n\n` 的格式。
   * 如果想带更多字段（如 `id:`、`event:`），可以在 `sse_payload` 里手动拼接：

     ```python
     sse_payload = f"id: {some_id}\nevent: update\ndata: {text}\n\n"
     ```

4. **客户端取消连接**

   * 一旦客户端关闭 TCP 连接，`StreamingResponse` 所在的协程就会抛出 `asyncio.CancelledError`，我们在 `except` 里捕获——并 kill 子进程，避免遗留僵尸任务。

---

## 三、本地运行（不借助 Knative）

### 1. 安装依赖

在同一个目录下，创建一个 `requirements.txt`，内容例如：

```
fastapi
uvicorn[standard]
```

（如果你的 `stdio_mcp_server.py` 里还引入了其他第三方包，也要一并写到这里。）

然后运行：

```bash
pip install -r requirements.txt
```

### 2. 启动 Adapter Service

最简单的方式是：

```bash
uvicorn adapter_service:app --host 0.0.0.0 --port 8000
```

* 这样会在本机的 **8000 端口** 启动 FastAPI 服务。
* 你可以通过 `http://127.0.0.1:8000/healthz` 验证是否正常（应该返回 `{"status":"ok"}`）。
* 真正的 MCP SSE 入口在 `http://127.0.0.1:8000/mcp`。

> **提示**：如果你不想手动敲这一行，也可以在项目根目录下写个小脚本 `start.sh`：
>
> ```bash
> #!/bin/bash
> uvicorn adapter_service:app --host 0.0.0.0 --port 8000
> ```
>
> 并 `chmod +x start.sh`，以后只要 `./start.sh` 就行了。

### 3. 测试 SSE 流

仍然假设你的 `stdio_mcp_server.py` 能接受这样的示例 JSON：

```jsonc
{
  "jsonrpc": "2.0",
  "id": "test-1",
  "method": "Echo",
  "params": { "message": "hello world" }
}
```

1. **用命令行 `curl` 测试**

   ```bash
   curl -N -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","id":"test-1","method":"Echo","params":{"message":"hello world"}}' \
     http://127.0.0.1:8000/mcp
   ```

   * `-N`：让 `curl` 保持原样输出，不缓冲。
   * 如果 `stdio_mcp_server.py` 每处理完一条就马上 `print(json.dumps(response))`，那么你会在终端里看到：

     ```
     data: {"jsonrpc":"2.0","id":"test-1","result":{"echo":"hello world"}}

     ```

     或者更复杂的多次推送。

2. **用浏览器 / JavaScript 测试**

   * 你可以在浏览器控制台里写：

     ```javascript
     const evtSource = new EventSource("http://127.0.0.1:8000/mcp");
     // 注意：EventSource 默认只能 GET，而且不能自行在 body 里带 JSON。
     // 如果你非得用 EventSource，就需要改成 GET＋QueryString 传参，或者在服务器端特定路径专门做 GET→STDIO 的转换。
     // 所以更通用的是用 fetch + ReadableStream：

     async function callMCP() {
       const resp = await fetch("http://127.0.0.1:8000/mcp", {
         method: "POST",
         headers: { "Content-Type": "application/json" },
         body: JSON.stringify({
           jsonrpc: "2.0",
           id: "test-1",
           method: "Echo",
           params: { message: "hello world" },
         }),
       });
       const reader = resp.body.getReader();
       const decoder = new TextDecoder("utf-8");
       let buffer = "";
       while (true) {
         const { done, value } = await reader.read();
         if (done) break;
         buffer += decoder.decode(value, { stream: true });
         let chunks = buffer.split(/\r\n\r\n|\n\n/);
         buffer = chunks.pop();
         for (const chunk of chunks) {
           const lines = chunk.split(/\r\n|\n/);
           for (const line of lines) {
             if (line.startsWith("data:")) {
               const jsonStr = line.slice(5).trim();
               console.log("收到 MCP 事件：", JSON.parse(jsonStr));
             }
           }
         }
       }
       console.log("流结束");
     }
     callMCP();
     ```
   * 这样浏览器就能实时拿到底层 STDIO 脚本输出的每一条 JSON，再渲染/展示。

---

## 四、用 Docker 封装（替代 Knative）

如果你不打算用 Knative，但想把整个服务“一键跑在任何一台服务器”上，就可以用 Docker。下面给出一个示例 `Dockerfile`，把 `adapter_service.py` 和 `stdio_mcp_server.py` 一起装到一个镜像里。

```dockerfile
# Dockerfile

FROM python:3.8-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖（如果 stdio_mcp_server.py 里没什么特别依赖，可删减）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
       build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制 Python 依赖清单并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY adapter_service.py .
COPY stdio_mcp_server.py .

# 暴露端口（在容器里运行时，uvicorn 默认监听 8000）
ENV PORT=8000
EXPOSE 8000

# 以 uvicorn 启动 Adapter Service
CMD ["uvicorn", "adapter_service:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 构建并运行

1. **构建镜像**

   ```bash
   docker build -t my-mcp-adapter:latest .
   ```

2. **本地运行容器**

   ```bash
   docker run -d --name mcp-adapter-container -p 8000:8000 my-mcp-adapter:latest
   ```

   * 这样你就可以通过 `http://localhost:8000/mcp` 来访问 SSE 服务了。
   * 如果要在其他机器上运行，把镜像推到你自己的 Docker Registry（比如 Docker Hub）：

     ```bash
     docker tag my-mcp-adapter:latest yourdockerhubuser/my-mcp-adapter:latest
     docker push yourdockerhubuser/my-mcp-adapter:latest
     ```
   * 然后在目标服务器上直接 `docker pull yourdockerhubuser/my-mcp-adapter:latest && docker run ...` 就行。

3. **docker-compose（可选）**
   如果以后要把它与数据库、缓存或者其他微服务一起调度，可以写一个 `docker-compose.yml`：

   ```yaml
   version: "3.8"
   services:
     mcp-adapter:
       image: yourdockerhubuser/my-mcp-adapter:latest
       container_name: mcp-adapter
       ports:
         - "8000:8000"
       restart: always
   ```

   然后在目录下 `docker-compose up -d`，一键搞定。

---

## 五、常见问题 & 注意事项

1. **并发子进程开销**

   * 如果每个 `/mcp` 请求都立刻 `asyncio.create_subprocess_exec` 启动一个新的 Python 进程，而你的 STDIO 脚本冷启动耗时较长（例如要加载大模型、初始化库），那么第一个请求会有明显延迟。
   * 可选优化：

     1. **复用子进程**：在 `adapter_service.py` 启动阶段，仅用一次 `asyncio.create_subprocess_exec` 启动 MCP 子进程，后续所有请求都往同一个子进程的 stdin 里写。这样不用反复启动。

        * 难点：原生 STDIO 逻辑要保证“请求→响应”的一一对应，不能出现多个请求混淆输出。
     2. **子进程池**：维护一个有限大小的子进程池，池中每个进程都是独立的 MCP 实例，处理请求时从池里拿一个空闲进程去服务；请求结束后归还到池中。这样既能减少启动次数，又能支持小规模并发。
   * 如果不做优化，**并发太高**时进程就会爆，内存／CPU 直接被打满。

2. **SSE 客户端兼容**

   * 原生的 `EventSource` 只能用 GET 请求（而不是 POST），也不方便带 Body。如果强行用 `EventSource`，可以把整个 JSON 放到 URL 的查询字符串（不推荐处理大请求），或者约定一个 GET→STDIO 的轻量协议（比如 `/mcp?input=...`）。
   * 因此我建议：如果要发带 Body 的 MCP 请求，就用 `fetch` + `ReadableStream`。如果只想演示 SSE，也可以简单写一个 GET 端点，让它从 STDIO 里读“固定输入”，再 SSE 输出。

3. **错误处理**

   * 当 STDIO 脚本报错（例如 json 解包失败、模型推理出异常），通常会把错误信息写到 `stderr`，并可能直接退出。
   * 要把这部分 stderr 也拿出来推给客户端，或者至少把 exit code 通知到 SSE 流最后一条。例如：

     ```python
     # 在 run_stdio_mcp_and_stream 中：
     stderr = await proc.stderr.read()
     if stderr:
         # 把 stderr 也包装成 SSE
         err_str = stderr.decode("utf-8", errors="ignore")
         yield f"data: {{\"error\": \"{err_str}\"}}\n\n".encode("utf-8")
     ```
   * 并且确保 `proc.wait()` 完成后，不要让协程挂起。

4. **资源限制**

   * 如果你把镜像跑在一台 VPS／云主机上，一定要给 Docker 容器设置适当的 CPU／内存限制，避免某次模型加载直接吃掉整台机器。
   * `docker run` 时可以加上：

     ```bash
     docker run -d --name mcp-adapter-container \
       --cpus="1.0" --memory="1g" \
       -p 8000:8000 my-mcp-adapter:latest
     ```

5. **持久化与日志**

   * FastAPI 默认会把日志输出到 stdout，你可以结合 `docker logs mcp-adapter-container -f` 实时查看。
   * 如果要保留历史，可以用 `--log-driver` 或者把日志写到一个卷里的文件，再结合 ELK/Fluentd 做采集。
   * 建议把 `/healthz`、`/metrics`（Prometheus client）等端点加上，方便把服务纳入监控体系。

---

## 六、示例：完整流程演示

下面总结一下，在不借助 Knative 的前提下，从零开始把一个能走 STDIO 的 Python 脚本打包成 HTTP+SSE 服务并运行的步骤。

假设你的目录结构是：

```
project-root/
├── adapter_service.py      # FastAPI 适配层
├── stdio_mcp_server.py     # 你的原生 MCP 脚本
├── requirements.txt        # 依赖列表：fastapi、uvicorn 等
└── Dockerfile              # 构建镜像
```

1. **编写 `stdio_mcp_server.py`**

   * 这个脚本示例可以这样写（仅作演示）：

     ```python
     # file: stdio_mcp_server.py
     import sys
     import json

     def main():
         for line in sys.stdin:
             line = line.strip()
             if not line:
                 continue
             try:
                 req = json.loads(line)
                 # 简单 Echo：把收到的 message 再返回
                 msg = req.get("params", {}).get("message", "")
                 response = {
                     "jsonrpc": "2.0",
                     "id": req.get("id"),
                     "result": {"echo": msg}
                 }
             except Exception as e:
                 response = {
                     "jsonrpc": "2.0",
                     "id": None,
                     "error": str(e)
                 }
             # 每次都要确保换行，以便适配器能用 readline() 读出
             print(json.dumps(response), flush=True)

     if __name__ == "__main__":
         main()
     ```
   * 这样它会持续读 stdin、输出 stdout，直到被 kill。

2. **编写 `adapter_service.py`**

   * 如前文代码所示，确保 `STDIO_MCP_CMD = ["python", "stdio_mcp_server.py"]`。

3. **写 `requirements.txt`**

   ```
   fastapi
   uvicorn[standard]
   ```

4. **写 `Dockerfile`**

   * 如上面 “用 Docker 封装” 一节的示例。

5. **本地测试（无需 Docker）**

   * 安装依赖：

     ```bash
     pip install -r requirements.txt
     ```
   * 打开一个终端，先单独跑一下 `stdio_mcp_server.py`，验证它能正常 echo：

     ```bash
     printf '{"jsonrpc":"2.0","id":"abc","params":{"message":"hello"}}\n' | python stdio_mcp_server.py
     ```

     预期你会看到：

     ```json
     {"jsonrpc":"2.0","id":"abc","result":{"echo":"hello"}}
     ```
   * 然后再跑 Adapter：

     ```bash
     uvicorn adapter_service:app --host 0.0.0.0 --port 8000
     ```
   * 在另一个终端，用 `curl` 测试 SSE：

     ```bash
     curl -N -H "Content-Type: application/json" \
       -d '{"jsonrpc":"2.0","id":"abc","params":{"message":"你好，世界"}}' \
       http://127.0.0.1:8000/mcp
     ```

     你应该马上看到：

     ```
     data: {"jsonrpc":"2.0","id":"abc","result":{"echo":"你好，世界"}}

     ```
   * 如果你在 Adapter 里改成“分两次打印”来模拟流式（例如每隔 0.5 秒打印一句），也会一行一行地输出给客户端。

6. **打包到 Docker 并运行**

   * 构建镜像：

     ```bash
     docker build -t my-mcp-adapter:latest .
     ```
   * 运行容器：

     ```bash
     docker run -d --name mcp-adapter -p 8000:8000 my-mcp-adapter:latest
     ```
   * 和以前一样，用 `curl -N` 或者前端去 `POST http://<你的宿主机IP>:8000/mcp` 即可实时收到 SSE。

---

## 七、可选：用 systemd 或 supervisor 守护进程

如果你更倾向于直接在一台 Linux 服务器上运行，而不是用 Docker，也可以用 systemd 把 `uvicorn adapter_service:app ...` 作为服务管理：

1. **创建一个 systemd 单元文件**（如 `/etc/systemd/system/mcp-adapter.service`）：

   ```
   [Unit]
   Description=MCP Adapter Service (STDIO→SSE)
   After=network.target

   [Service]
   Type=simple
   WorkingDirectory=/path/to/your/project-root
   ExecStart=/usr/bin/uvicorn adapter_service:app --host 0.0.0.0 --port 8000
   Restart=always
   # 如果你需要特定的虚拟环境，把 ExecStart 改成：
   # ExecStart=/path/to/venv/bin/uvicorn adapter_service:app --host 0.0.0.0 --port 8000
   User=your_user
   Environment="PATH=/path/to/venv/bin:/usr/bin"
   Environment="PYTHONUNBUFFERED=1"

   [Install]
   WantedBy=multi-user.target
   ```

2. **启动并启用服务**：

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl start mcp-adapter
   sudo systemctl enable mcp-adapter
   ```

3. **查看日志**：

   ```bash
   sudo journalctl -u mcp-adapter -f
   ```

这样，系统重启后会自动把你的 Adapter 服务启动，并且它自己会去 `WorkingDirectory` 里找到 `adapter_service.py` 和 `stdio_mcp_server.py`。只要这两个文件保持在那个目录，service 就一直在跑。

---

## 八、小结

* **核心逻辑**：Adapter Service（FastAPI + `asyncio.create_subprocess_exec`） 负责把 HTTP POST→stdin、stdout→SSE，完全复用了之前在 Knative 上的做法，只是部署方式变为“本地/容器”。
* **部署方式**：

  1. 直接在宿主机上 `uvicorn adapter_service:app`，配合 systemd or supervisor 进行守护。
  2. 用 Docker 把整个目录封装成镜像，然后随时在任何 Docker 主机上 `docker run`。
  3. 也可以再套一个 `docker-compose`，以后想扩展其他组件也很方便。
* **注意点**：

  * 并发过高时，“每请求一个子进程”会带来显著开销，必要时考虑子进程复用或进程池。
  * SSE 需要客户端主动支持“读流”，不要用普通 `fetch().then(r=>r.json())`，要配合 `ReadableStream` 或者 `EventSource`。
  * 一定要处理 `CancelledError`，避免僵尸进程。
  * 在生产环境，加上健康检查（`/healthz`）、日志/监控（Prometheus metrics）会更健壮。

按照上面几个步骤，你就能在**不使用 Knative**、也不需要 Kubernetes 的前提下，把一个只有“stdin/stdout 交互”的 Python 脚本平滑地包装成一个可通过 HTTP+SSE 进行流式交互的在线服务。这样，从外部看，MCP 服务就像一个普通的那种“只要访问 [http://host:8000/mcp，就能拿到](http://host:8000/mcp，就能拿到) SSE 实时回应”的微服务，而不需要关心它底层究竟是怎么「通过标准输入、标准输出」跟模型或业务逻辑沟通的。希望这个示例能帮助你快速落地。如果有进一步的需求（比如多进程池、鉴权、HTTPS、限流等），也可以在这个基础上逐步扩展。祝顺利！
