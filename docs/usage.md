# MCPify Usage Guide

MCPify 提供了简化的命令行界面，将"生成"和"运行"分离开来，让MCP客户端可以更灵活地控制服务器的启动。

## 项目架构

```
mcpify/
├── mcpify/                    # 核心包
│   ├── cli.py                 # CLI入口 (mcpify命令)
│   ├── server.py              # 服务器入口 (mcp-server命令)
│   ├── wrapper.py             # MCP包装器
│   ├── backend.py             # 后端适配器
│   ├── detect.py              # API检测
│   └── validate.py            # 配置验证
├── bin/                       # 独立可执行脚本
│   └── mcp-serve              # 独立服务器脚本
├── examples/                  # 示例配置文件
│   ├── fastapi-example.json
│   ├── python-module-example.json
│   └── commandline-example.json
└── docs/                      # 文档
    └── usage.md
```

## 命令概览

### 1. 检测项目API
```bash
mcpify detect /path/to/project --output config.json
```

### 2. 查看配置文件
```bash
mcpify view config.json
```

### 3. 验证配置文件
```bash
mcpify validate config.json
```

### 4. 启动MCP服务器
```bash
# 启动stdio模式（默认）
mcpify serve config.json

# 启动HTTP流式模式
mcpify serve config.json --mode streamable-http --port 8080
```

## 独立服务器脚本

项目提供了多种方式来启动MCP服务器：

### 方式1：使用独立脚本（推荐给MCP客户端）
```bash
# 使用bin目录下的独立脚本
./bin/mcp-serve config.json
./bin/mcp-serve config.json --mode streamable-http --port 8080
```

### 方式2：通过mcpify CLI
```bash
# 使用mcpify命令
mcpify serve config.json
mcpify serve config.json --mode streamable-http --port 8080
```

### 方式3：直接调用模块
```bash
# 直接调用Python模块
python -m mcpify serve config.json
python -m mcpify serve config.json --mode streamable-http --port 8080
```

## 使用场景

### 场景1：开发和测试
```bash
# 1. 检测项目API
mcpify detect my-project --output my-project.json

# 2. 查看生成的配置
mcpify view my-project.json

# 3. 直接启动服务器进行测试
mcpify serve my-project.json
```

### 场景2：MCP客户端集成
MCP客户端可以通过多种方式启动服务器：

```bash
# 使用独立脚本（推荐）
./bin/mcp-serve config.json

# 使用mcpify CLI
mcpify serve config.json

# 使用模块调用
python -m mcpify serve config.json
```

### 场景3：生产部署
```bash
# 启动HTTP模式的服务器，监听特定端口
./bin/mcp-serve config.json --mode streamable-http --host 0.0.0.0 --port 8080
```

## 配置文件示例

查看 `examples/` 目录下的示例配置文件：

### FastAPI 后端示例
```json
{
  "name": "my-fastapi-server",
  "description": "FastAPI backend server",
  "backend": {
    "type": "fastapi",
    "base_url": "http://localhost:8000"
  },
  "tools": [
    {
      "name": "get_user",
      "description": "Get user information",
      "endpoint": "/users/{user_id}",
      "method": "GET",
      "parameters": [
        {
          "name": "user_id",
          "type": "string",
          "description": "User ID"
        }
      ]
    }
  ]
}
```

### Python 模块后端示例
```json
{
  "name": "my-python-module",
  "description": "Python module backend",
  "backend": {
    "type": "python",
    "module_path": "./my_module.py"
  },
  "tools": [
    {
      "name": "calculate",
      "description": "Perform calculation",
      "function": "calculate",
      "parameters": [
        {
          "name": "expression",
          "type": "string",
          "description": "Mathematical expression"
        }
      ]
    }
  ]
}
```

### 命令行工具后端示例
```json
{
  "name": "my-cli-tool",
  "description": "Command line tool backend",
  "backend": {
    "type": "commandline",
    "config": {
      "command": "python3",
      "args": ["./my_script.py"],
      "cwd": "."
    }
  },
  "tools": [
    {
      "name": "process_data",
      "description": "Process data with CLI tool",
      "args": ["process", "{input_file}"],
      "parameters": [
        {
          "name": "input_file",
          "type": "string",
          "description": "Input file path"
        }
      ]
    }
  ]
}
```

## 支持的后端类型

- `fastapi`: FastAPI应用
- `python`: Python模块
- `external`: 外部命令行工具
- `commandline`: 简单命令行工具（向后兼容）

## 服务器模式

- `stdio`: 标准输入输出模式（MCP默认）
- `streamable-http`: HTTP服务器端事件流模式

## 安装和部署

### 开发安装
```bash
pip install -e .
```

### 生产安装
```bash
pip install mcpify
```

### 使用独立脚本（无需安装）
```bash
# 复制bin/mcp-serve到目标位置
cp bin/mcp-serve /usr/local/bin/
chmod +x /usr/local/bin/mcp-serve
# 然后可以直接使用
mcp-serve config.json
```

这种设计让MCP客户端可以完全控制服务器的启动时机和方式，同时提供了多种部署选项以适应不同的使用场景。
