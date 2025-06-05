是的，如果你手上只有一些不支持“行级 JSON STDIO 交互” 的可执行脚本，也可以借助一个中间的 Python “包装器”（wrapper），把它们“改造”成满足上述要求的 STDIO 脚本。思路很简单：用 Python 读取一行 JSON，解析出具体要调用的可执行文件及其参数，然后捕获可执行文件的输出，再把它封装成一行 JSON（末尾带 `\n`）输出到 stdout，并立刻 `flush()`。下面我从几个要点出发，给出一个参考步骤和示例代码。

---

## 一、核心思路与步骤

1. **“行”界定：所有交互都应以“每行一条完整 JSON”**

   * 包装器（wrapper）本身要做到“读取 stdin 的一行（包括结尾的 `\n`）→当作一个完整 JSON 解析→产生一个对应的 JSON 响应→写到 stdout 并 `flush()`”。
   * 这样，上层的 Adapter（HTTP→STDIO→SSE）就能按行读取包装器脚本的 stdout，转换成 SSE 事件推送给前端。

2. **Python 包装器的职责**

   * **读**：循环 `for line in sys.stdin:` 或 `while True: line = sys.stdin.readline()`，每次拿到一行（去掉末尾的 `\n`）当作“请求 JSON”。
   * **解析**：用 `json.loads(line)` 把这一行字符串变成 Python 字典，拿到 “要调用哪个可执行文件”（或默认只调用一个固定的 exe）以及传递给它的参数。
   * **执行**：调用 `subprocess.Popen([...])` 或 `subprocess.run([...])`，把可执行文件跑起来，把它的 stdout/stderr 捕获到 Python 里。
   * **封装**：把可执行文件返回的 stdout（通常是一段文本，可能是多行）或者 stderr（如果报错），包装成一个合法的 JSON 格式，例如：

     ```json
     {
       "jsonrpc": "2.0",
       "id": "<和请求保持一致的 id>",
       "result": {
         "stdout": "<可执行文件的全部输出>",
         "stderr": "<可执行文件的全部错误输出，如果没有则空字符串>"
       }
     }
     ```
   * **输出**：调用 `print(json.dumps(封装好的 dict), flush=True)`，保证每次输出都是一行、是合法的 JSON、立刻刷新到 stdout。

3. **如何处理“流式输出”需求？**

   * 如果你的可执行脚本本身在运行时会持续向 stdout 打印多行内容（比如一条条进度日志），而你需要前端边跑边展示，这种情况就要改成“**边读可执行脚本 stdout 的一行 → 封装成一行 JSON → print + flush → 再读下一行**” 的方式。
   * 也就是说，包装器不要等整个子进程（可执行文件）结束才一次性捕获 stdout 再输出，而是把 `Popen.stdout.readline()` 当做事件驱动，一边读取一边封装并输出。这样 Adapter 收到的每行 JSON 就能立刻转为 SSE 事件，推到前端。

4. **错误处理**

   * 如果可执行脚本运行失败，比如找不到命令或抛异常、返回非零退出码，包装器要能捕获到 `stderr` 或者退出码，然后把错误信息也包装成类似

     ```json
     {
       "jsonrpc": "2.0",
       "id": "<请求的 id>",
       "error": {
         "code": 1,
         "message": "<可执行脚本 stderr 内容 或 Python 捕获到的异常信息>"
       }
     }
     ```

     然后 `print(..., flush=True)`，保持“输出一行 JSON”，让上层 Adapter 知道这次调用失败了。

5. **多轮 vs 单轮**

   * **单轮模式**：每次读一行 JSON 请求，就用 `subprocess.run(...)` 同步调用可执行文件，把它的 stdout/stderr 全部拿到 Python 里，把结果包成 JSON 一起输出，然后这次循环结束。如果可执行文件没问题，wrapper 可直接 `continue` 等待下一次输入；可执行文件退出后，wrapper 这个进程依然存活。
   * **多轮流式模式**：如果可执行脚本本身调用后就“长驻并持续输出”（例如模型推理逐 token 输出），则要把 wrapper 改成异步或多线程：

     1. 把可执行文件作为一个“常驻子进程” `Popen([...], stdout=PIPE, stderr=PIPE, stdin=PIPE)`。
     2. 包装器在读到“第一条请求”时，把 JSON 写到子进程 stdin，等它开始输出后，用 `while True: line = proc.stdout.readline()` 一行一行拿到输出，立刻封装、print 并 `flush()`。
     3. 当子进程发完所有内容（stdout EOF）或发出特殊标识后，wrapper 再跳出这个流式循环，转到“再次等待 stdin 里下一条 JSON 请求”的状态。
   * 这里只要保证“每行 stdout → 对应一个 JSON 输出”，上层 Adapter 就能无缝地按行读取并把它转成 SSE 事件。

---

## 二、示例：把任意可执行程序，封装成符合 STDIO JSON 规范的 Python Wrapper

下面给出一个「最通用」的示例：假设目录下有一个可执行文件 `./my_tool`（Linux/Mac 上可执行，Windows 下可以改成 `my_tool.exe`），它接收一些命令行参数，执行完毕后会把结果打印到 stdout。我们要把它改造成“行级 JSON STDIO 交互”的服务。

### 目录结构举例

```
project-root/
├── wrapper.py          # 我们要编写的 Python 包装器
├── my_tool             # 现成的可执行脚本/二进制（比如 C 编译的程序）
└── requirements.txt    # 如果 wrapper.py 里需要第三方库，再写进来
```

### 1. 示例 `wrapper.py`

```python
#!/usr/bin/env python3
# coding: utf-8

import sys
import json
import shlex
import subprocess
import threading

def handle_single_request(request_obj):
    """
    根据 request_obj 去调用 my_tool，并返回 stdout/stderr。
    request_obj 的示例结构（约定）：
    {
      "jsonrpc": "2.0",
      "id": "req-123",
      "method": "RunTool",
      "params": {
        "args": ["--foo", "bar", "--baz", "qux"]
      }
    }

    下面示例只演示“单次调用” + “全集中捕获 stdout/stderr”：
    """
    request_id = request_obj.get("id", None)

    # 1. 从 request_obj.params.args 里拿到可执行的参数，如果没传，则用默认空列表
    params = request_obj.get("params", {})
    args_list = params.get("args", [])
    if not isinstance(args_list, list):
        args_list = []

    # 2. 构造最终要 exec 的命令：["./my_tool", "--foo", "bar", ...]
    cmd = ["./my_tool"] + args_list

    try:
        # 同步调用 my_tool，capture_output=True 会得到 stdout 和 stderr
        completed = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,  # 让 stdout/stderr 都是 str 而不是 bytes
            timeout=60  # 设个超时，防止卡死
        )
    except subprocess.TimeoutExpired as te:
        # 超时的错误，封装成“JSON-RPC error”结构
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32001,
                "message": f"Tool timed out: {str(te)}"
            }
        }

    # 3. 如果退出码不为 0，把 stderr 当作 error 信息
    if completed.returncode != 0:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": completed.returncode,
                "message": completed.stderr.strip()
            }
        }

    # 4. 正常拿到 stdout，把它封进 result 里
    #    这里假设 my_tool 的 stdout 本身就是纯文本
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "stdout": completed.stdout.strip(),
            "stderr": ""
        }
    }

def stream_tool_output(request_obj):
    """
    如果 my_tool 本身是“长驻并持续产出 stdout”的那种（比如分步输出进度），
    可以用这个 generator 来一行行 yield 给 wrapper 外层输出。
    但本示例暂不展开，如果需要流式，只需把 subprocess.Popen(... stdout=PIPE) 后
    一行一行读出来并封装成 JSON yield 即可。
    """
    raise NotImplementedError("如需流式，请改用 subprocess.Popen 而非 subprocess.run")

def main():
    """
    1. 循环读取 stdin：
       - 每读到一行，就当作“一个请求 JSON”去解析
       - 调用 handle_single_request(request_obj) 获得 response_obj
       - print(json.dumps(response_obj), flush=True)
    2. 如果 EOF，就退出
    """
    for raw_line in sys.stdin:
        line = raw_line.rstrip("\n")
        if not line:
            continue  # 空行忽略

        try:
            request_obj = json.loads(line)
        except Exception as e:
            # 解析 JSON 失败，返回一个 error
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {str(e)}"
                }
            }
            print(json.dumps(err_resp), flush=True)
            continue

        # 处理请求
        try:
            resp_obj = handle_single_request(request_obj)
        except Exception as e:
            # 处理过程中抛出异常，返回一个 error
            resp_obj = {
                "jsonrpc": "2.0",
                "id": request_obj.get("id", None),
                "error": {
                    "code": -32000,
                    "message": f"Internal error: {str(e)}"
                }
            }

        # 输出一行 JSON，立刻 flush
        print(json.dumps(resp_obj), flush=True)

    # stdin EOF 了，说明上游不再发请求，优雅退出
    sys.exit(0)

if __name__ == "__main__":
    main()
```

### 2. 解释这个示例里关键细节

1. **`for raw_line in sys.stdin:`**

   * 用行循环，一行一行地读，保证我们读到的就是一个完整的 JSON 字符串（因为上层 Adapter 已经会在发送时加上 `\n`）。
   * `.rstrip("\n")` 只是去掉末尾换行，剩下的内容交给 `json.loads`。

2. **`handle_single_request(request_obj)`**

   * 这里示例了“最简单”的模式：每收到一条 JSON 请求，把它解析成一个 Python dict，然后把参数组装成 `["./my_tool", arg1, arg2, …]`，再调用 `subprocess.run()`。
   * `capture_output=True`（或 `stdout=PIPE, stderr=PIPE, universal_newlines=True`）让你能一次性拿到 stdout/stderr，便于“统一封装成 JSON”。
   * 如果 `returncode != 0`，就把 stderr（去掉末尾空白）放到 “error.message” 里；如果 `returncode == 0`，就把 stdout 放到 `"result"` 里。
   * 你可以根据自己可执行文件的行为，改造 `handle_single_request`，比如把 stdout 解析成更结构化的信息再放到 `result` 下。

3. **`print(json.dumps(...), flush=True)`**

   * 这一行很关键——它保证“**输出一整行合法 JSON**”并立刻刷新到 stdout，让 Adapter 可以马上读到。
   * 如果不加 `flush=True`，Python 默认会把输出先缓存在内存，直到缓冲区满或程序退出才 flush，那就会导致 Adapter 一直读不到内容，SSE 会卡住。

4. **持续运行 vs 单次运行**

   * 这个示例里，wrapper 脚本是“**一个进程跑到底**”，会一直循环 `for raw_line in sys.stdin`，处理完一条请求后不退出，继续等待下一条请求。
   * 这样，上层 HTTP→Adapter 可以每次都直接把 JSON 末尾加 `\n` 发给这个一直存活的进程，而不必为每个请求都新建一个 Python 进程。
   * 如果你希望“每条请求就新启动一个进程”，可以把 `wrapper.py` 在调用端改成 `subprocess.run(["python", "wrapper.py"], input=json_line, …)`。那就属于“短进程模式”，也可行，但开销大些。

5. **扩展：如果需要“流式输出”**

   * 上面 `handle_single_request` 用的是 **`subprocess.run`**（同步调用、等子进程退出后才拿到全部 stdout），适合“一次性输出” 的需求。
   * 如果你想模仿“边调用边输出”的场景，例如 `my_tool` 本身会持续输出进度（每秒一行），那么就不能 `run`，而要用 **`subprocess.Popen(..., stdout=PIPE)`**：

     ```python
     proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
     # 一行一行地读它的 stdout
     for out_line in proc.stdout:
         # out_line 本身包含 '\n'
         out_line = out_line.rstrip("\n")
         # 把这行原始输出再封装成 JSON 并 print + flush
         partial_resp = {
             "jsonrpc": "2.0",
             "id": request_id,
             "partial": True,
             "output": out_line
         }
         print(json.dumps(partial_resp), flush=True)
     # 等待子进程退出后，可能还有 stderr
     proc.wait()
     err = proc.stderr.read()
     if proc.returncode != 0:
         err_resp = {
             "jsonrpc": "2.0",
             "id": request_id,
             "error": {
                 "code": proc.returncode,
                 "message": err.strip()
             }
         }
         print(json.dumps(err_resp), flush=True)
     else:
         final_resp = {
             "jsonrpc": "2.0",
             "id": request_id,
             "partial": False,
             "result": {"message": "Completed"}
         }
         print(json.dumps(final_resp), flush=True)
     ```
   * 这样包装后，Adapter（或者浏览器端）就能在收到第一条“partial”为 `True` 的行时立刻把它当成 SSE 事件推过去，等到最后一条 `"partial": false` 时，就知道整次调用已经结束。

---

## 三、常见变种与扩展

1. **参数映射**

   * 如果你的可执行文件最初设计成“只通过命令行参数”来决定行为（而不要读 stdin），包装器可以把 JSON 里的 `params` 对象展开成参数列表。例如：

     ```json
     // 请求示例
     {
       "jsonrpc": "2.0",
       "id": "req-42",
       "method": "Foo",
       "params": { "input": "hello", "verbose": true }
     }
     ```

     在 Python 中你可以把 `params` 转成 `["--input", "hello", "--verbose", "True"]`，然后 `cmd = ["./my_tool"] + that_list`。如果可执行文件更复杂，需要 `stdin` + 参数一起跑，也可以把 JSON 的一部分转到 stdin。

2. **针对脚本输出做解析**

   * 如果可执行脚本在 stdout 输出的是 CSV、纯文本、甚至二进制数据，包装器需要在拿到 `completed.stdout` 之后，把它转换成适合放到 JSON 里的字符串（比如 Base64 编码），或者自己解析成内部结构再放进 `result`。关键是“包装器输出的一行必须是合法 JSON 且以 `\n` 结尾”。

3. **错误日志分离**

   * 上述示例中，我们把 `stderr` 全部当成“error message”放到 error 字段里。如果你希望把 `stderr` 同时写到一个单独的文件或管道，用于离线查看，也可以在调用 `subprocess.run` 时传递一个 `stderr=open("error.log", "a")`。不过，为了让 Adapter 及时知道“执行过程是不是出错”，还要把 stderr 通过 JSON 返回给 Adapter。

4. **超时与信号**

   * 如果可执行脚本有可能无响应或卡住，可以让包装器给它设一个 `timeout`，一旦超时就 `proc.kill()`，并返回一个超时的错误 JSON。
   * 在多轮交互时，如果包装器一旦接到某个特殊 “关闭信号”（例如 JSON 里 `{"method": "shutdown"}`），也可以让包装器通过 `proc.terminate()` 或者 `proc.kill()` 结束子进程，并自己 `sys.exit(0)`。

5. **直接把脚本打包为可执行文件**

   * 如果你手上的“简单可执行脚本”原本是一个 Bash 脚本或 Python 脚本，也可以考虑：

     1. 把它本身改写成“可循环 stdin/stdout 交互”的 Python 脚本（像上面示例的 `wrapper.py`），把原本的业务逻辑整合到 `handle_single_request` 里。
     2. 或者如果你不想 touch 现有脚本，只想“外面套一层”，那就用上文的 `wrapper.py`；把现有脚本当成黑盒，通过 `subprocess` 根据需要调用。

---

## 四、完整示例：把一个现成的 `echo.sh`（Bash 脚本）改造为行级 JSON STDIO

### 1. 假设有一个简单的 Bash 脚本 `echo.sh`

```bash
#!/usr/bin/env bash
# echo.sh：把第一个参数回显并在末尾加个“OK”
# 用法：./echo.sh "some text"
echo "$1"    # 将第一个参数打印到 stdout
echo "OK"    # 最后打印一个 OK
```

这个脚本本身没有任何 JSON 交互逻辑，而是“看到第一个参数就回显两行文本”。我们要做两步改造：

1. **保持它原有“回显逻辑”不变**，仍然作为黑盒执行。
2. 写一个 `wrapper.py`，它：

   * 从 stdin 读一行 JSON，类似

     ```json
     {
       "jsonrpc": "2.0",
       "id": "req-echo-1",
       "method": "Echo",
       "params": { "message": "hello world" }
     }
     ```
   * 把 `params.message` 取出来，用 `subprocess.run(["./echo.sh", message])` 调用它。
   * 捕获它 stdout 两行，拼成 `{"stdout": "<line1>\n<line2>"}` 再放到 `result` 里，或者分两次“流式”输出也可以。
   * 如果 `echo.sh` 失败（其实几乎不可能），也要封装成 `error` 返回。

### 2. 写 `wrapper.py`

```python
#!/usr/bin/env python3
# coding: utf-8

import sys
import json
import subprocess

def handle_request(request_obj):
    request_id = request_obj.get("id", None)
    params = request_obj.get("params", {})
    message = params.get("message", "")

    # 如果 message 不是 str，就返回一个参数错误
    if not isinstance(message, str):
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32602,
                "message": "Invalid params: 'message' must be a string"
            }
        }

    # 调用 echo.sh
    cmd = ["./echo.sh", message]
    try:
        completed = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=10
        )
    except subprocess.TimeoutExpired as te:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32001,
                "message": f"Timeout: {str(te)}"
            }
        }

    if completed.returncode != 0:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": completed.returncode,
                "message": completed.stderr.strip()
            }
        }

    # 正常情况下，echo.sh 的 stdout 是两行：一行是 message，一行是 “OK”
    output_text = completed.stdout.rstrip("\n")
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "output": output_text
        }
    }


def main():
    for raw_line in sys.stdin:
        line = raw_line.rstrip("\n")
        if not line:
            continue

        try:
            req = json.loads(line)
        except Exception as e:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {str(e)}"
                }
            }
            print(json.dumps(err_resp), flush=True)
            continue

        try:
            resp = handle_request(req)
        except Exception as e:
            resp = {
                "jsonrpc": "2.0",
                "id": req.get("id", None),
                "error": {
                    "code": -32000,
                    "message": f"Internal error: {str(e)}"
                }
            }

        print(json.dumps(resp), flush=True)

    # shell 脚本可能会一直在等待新的 stdin 或者被 kill，若 stdin EOF，就退出
    sys.exit(0)


if __name__ == "__main__":
    main()
```

1. **让 `echo.sh` 可执行**

   ```bash
   chmod +x echo.sh
   ```

2. **试运行（不带 Adapter，只看 wrapper）**
   先启动 wrapper：

   ```bash
   python wrapper.py
   ```

   这时它在等你往 stdin 里写 JSON，最好别在前端，而是在命令行里模拟：

   ```bash
   printf '{"jsonrpc":"2.0","id":"req-echo","method":"Echo","params":{"message":"你好"}}\n' | python wrapper.py
   ```

   你可以看到类似：

   ```json
   {"jsonrpc":"2.0","id":"req-echo","result":{"output":"你好\nOK"}}
   ```

   * 这说明 `wrapper.py` 顺利调用了 `./echo.sh`，并把它输出的两行文本拼在了一起，作为 `"output"` 里的值。
   * 如果你传一个不合法的 JSON，或把 `message` 传成数字，就能看到 `error`，说明包装器的错误处理也生效了。

3. **和上面的“Adapter” 结合**

   * 在有了这个 `wrapper.py` 之后，你就可以照着之前的“HTTP→STDIO→SSE” 方案，把 `STDIO_MCP_CMD = ["python", "wrapper.py"]`，或者如果你把 `wrapper.py` 设成可执行（第一行 `#!/usr/bin/env python3`），`chmod +x wrapper.py`，就可以直接设 `STDIO_MCP_CMD = ["./wrapper.py"]`。
   * 那么每当 HTTP 端 `/mcp` 收到一条 JSON 请求，Adapter 就会把它写到 `wrapper.py` 的 stdin，`wrapper.py` 解析后再调用 `echo.sh`，拿到结果立刻 print，然后 Adapter 再把这一行 JSON 转成 SSE 推给前端。

---

## 五、小结

* **只要满足“**行级 JSON 输入→解析→调用可执行→行级 JSON 输出→flush**”**，包装器就能把任何原本不具备 STDIO JSON 接口的可执行程序，改造成一个符合前述 STDIO 规范的脚本。
* 对于“**一次性输出**” 的场景，用 `subprocess.run(...)` 同步执行即可；对于“**流式输出**” 的场景，用 `subprocess.Popen(..., stdout=PIPE)` 并一行一行读出来再封装。
* 包装器要额外注意错误处理（返回合法 JSON 的 `error` 字段）、超时处理（避免可执行程序卡死）、UTF-8 编码（避免乱码），以及 `print(..., flush=True)`（避免缓冲导致前端收不到）。
* 最终把包装器脚本与原本的可执行程序放在同一个目录，用 Docker 打包时也一并复制过去，就能像之前一样直接部署——无论是在 Knative 里做 HTTP→SSE，还是在纯 Docker/本地机器里用 Uvicorn+FastAPI 当 Adapter，都能透明调用原始程序，将其结果“以 JSON 行”的形式实时推给客户端。

这样，你就可以非常灵活地对接各种“只有命令行可执行” 的工具或脚本，而不必手动去改造每个工具本身，只需写一个统一的 Python wrapper，把它们都“包装”成符合 STDIO JSON 规范的服务。希望这个思路和示例能让你更容易地将已有的可执行脚本，平滑集成到 HTTP+SSE 适配器的架构中。加油！
