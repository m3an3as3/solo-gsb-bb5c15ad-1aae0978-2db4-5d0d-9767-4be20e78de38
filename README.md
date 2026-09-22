# 开源依赖许可审查（License Review）

基于 **FastAPI + SQLite** 的开源依赖许可证审查 Web 应用：上传依赖清单（JSON），选择项目许可策略，系统自动解析传递依赖图，按内置兼容矩阵标出冲突，并为每个冲突给出**最短依赖路径**与**触发规则**。支持在页面上确认例外包并重新计算，结果可导出为 JSON。

## 功能特性

- 📤 上传/粘贴 JSON 依赖清单（包名、版本、许可证、依赖关系）
- 📜 6 种项目许可策略：商业闭源、MIT/BSD 宽松开源、Apache-2.0、GPL-2.0、GPL-3.0、AGPL-3.0
- 🔗 BFS 解析传递依赖图，为每个冲突/告警包给出从项目根出发的**最短依赖路径**
- ⚖️ 内置许可证兼容矩阵（规则编号 + 中文说明），许可证名称自动规范化（如 `gplv3` → `GPL-3.0`）
- ✅ 页面上一键将冲突/告警包标记为**例外**（可附说明），自动重新计算
- 💾 SQLite 持久化审查记录与例外，支持历史记录回看
- ⬇ 审查结果一键导出 JSON

## 快速开始（Docker Compose，推荐）

```bash
docker compose up --build
```

启动后访问：**http://localhost:8000**

- Web 页面：http://localhost:8000
- API 文档（Swagger UI）：http://localhost:8000/docs

停止：`docker compose down`。SQLite 数据持久化在宿主机 `./data/review.db`。

## 本地开发（不用 Docker）

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

访问 http://localhost:8000 。

## 配置

| 环境变量       | 默认值                       | 说明                     |
| -------------- | ---------------------------- | ------------------------ |
| `DB_PATH`      | `./data/review.db`（容器内 `/app/data/review.db`） | SQLite 数据库文件路径 |
| `SAMPLE_PATH`  | `./sample_manifest.json`     | 页面「加载示例清单」读取的文件 |
| 端口映射       | `8000:8000`                  | 在 `docker-compose.yml` 的 `ports` 中修改 |

## 清单 JSON 格式

```json
{
  "project": { "name": "shop-api", "version": "1.4.2", "license": "Proprietary" },
  "packages": [
    { "name": "fastapi",   "version": "0.115.6", "license": "MIT" },
    { "name": "some-lib",  "version": "8.0.33",  "license": "GPL-2.0" }
  ],
  "dependencies": [
    { "from": "shop-api", "to": "fastapi" },
    { "from": "fastapi",  "to": "some-lib" }
  ]
}
```

- `project.name` 是依赖图的根节点；`dependencies` 中的 `from`/`to` 必须引用项目名或 `packages` 中声明的包名
- 同一清单内包名需唯一；`license` 支持常见写法（自动规范化），无法识别时按 `Unknown` 处理并给出告警
- 完整示例见仓库根目录 `sample_manifest.json`（页面里也有「加载示例清单」按钮）

## 判定状态与兼容矩阵

每个依赖包会被判定为四种状态之一：

| 状态      | 含义                                       |
| --------- | ------------------------------------------ |
| `conflict` | 与所选项目许可策略冲突（如闭源项目含 GPL） |
| `warning`  | 需人工确认（如 LGPL 链接方式、未知许可证） |
| `ok`       | 兼容                                       |
| `exempted` | 原为冲突/告警，已被人工确认为例外          |

矩阵以规则列表实现（`app/licenses.py`），每条规则带编号（如 `R-PRO-02`）与说明，结果中即为「触发规则」。例如：

- 商业闭源策略：GPL/AGPL → 冲突；LGPL/弱 Copyleft → 告警；未知许可 → 告警
- GPL-2.0 项目策略：Apache-2.0、GPL-3.0、AGPL-3.0 → 冲突（与 GPLv2 不兼容）
- GPL-3.0 项目策略：GPL-2.0-only → 冲突；Apache-2.0 → 兼容

如需调整规则，直接编辑 `app/licenses.py` 中 `POLICIES` 的规则列表即可。

## API 一览

| 方法 | 路径                                        | 说明                       |
| ---- | ------------------------------------------- | -------------------------- |
| GET  | `/api/policies`                             | 许可策略列表               |
| GET  | `/api/sample-manifest`                      | 示例清单                   |
| POST | `/api/reviews`                              | 提交清单并审查（body: `{policy, manifest}`） |
| GET  | `/api/reviews` / `/api/reviews/{id}`        | 历史列表 / 单条结果        |
| POST | `/api/reviews/{id}/exceptions`              | 添加例外包 `{package, note}`（自动重算） |
| DELETE | `/api/reviews/{id}/exceptions/{package}`  | 移除例外包（自动重算）     |
| POST | `/api/reviews/{id}/recalculate`             | 手动重新计算               |
| GET  | `/api/reviews/{id}/export`                  | 导出结果为 JSON 文件       |

## 项目结构

```
├── app/
│   ├── main.py        # FastAPI 路由（页面 + REST API）
│   ├── analyzer.py    # 清单校验、BFS 最短依赖路径、冲突分析
│   ├── licenses.py    # 许可证规范化 + 兼容矩阵（可自定义规则）
│   ├── db.py          # SQLite 持久化（审查记录、例外包）
│   ├── templates/     # 页面模板
│   └── static/        # 前端 JS / CSS
├── sample_manifest.json
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```
