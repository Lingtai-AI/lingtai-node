# LingTai-Node 代码审查报告

**审查时间**: 2026-05-09T12:43 PDT
**审查工具**: Claude Code CLI (opus)
**审查范围**: 全部 17 个 Python 源文件 + 配置/模板/文档
**代码量**: ~1400 行 Python

---

## 1. 严重问题 (Critical)

### C1. 路径遍历漏洞 — `email_manager.py:347`, `system_manager.py:87`, `avatar_manager.py:94`

所有通过用户输入 `to`/`target`/`name` 构造路径的地方都没有验证输入，允许 `../` 遍历。

```python
# email_manager.py:347 — 恶意 to="../../etc" 可以写入任意目录
recipient_dir = self._agent_dir.parent / to

# system_manager.py:87
return self._parent_dir / target

# avatar_manager.py:94
node_dir = self._parent_dir / name
```

**风险**: 攻击者通过 MCP tool 发送 `to="../../sensitive_dir"` 可以在 `parent_dir` 之外的任意位置创建目录和写入文件。

**修复方案**: 添加路径验证，确保解析后的路径不逃逸出 `_parent_dir`：

```python
def _safe_resolve(self, name: str) -> Path | None:
    target = (self._parent_dir / name).resolve()
    if not target.is_relative_to(self._parent_dir.resolve()):
        return None
    return target
```

### C2. 搜索功能 ReDoS 风险 — `email_manager.py:453`

用户提供的 `query` 直接编译为正则表达式，恶意模式可导致 CPU 拒绝服务：

```python
pattern = re.compile(query, re.IGNORECASE)
```

**修复方案**: 默认使用 `re.escape(query)` 做简单子串匹配，或对正则长度/复杂度设上限。

### C3. `_TEMPLATES_DIR` 路径计算脆弱 — `avatar_manager.py:224`, `watcher.py:32`

```python
# avatar_manager.py:224 — 从 __file__ 向上推 3 层
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"

# watcher.py:32 — 从 __file__ 向上推 5 层
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "templates"
```

这两个路径依赖安装后的文件系统布局。`pip install` 后 `templates/` 目录不会被打包（未在 `pyproject.toml` 的 `packages` 中配置），导致这些路径在生产安装中必然失败。

**修复方案**: 
1. 使用 `importlib.resources` 加载包内资源
2. 或在 `pyproject.toml` 中用 `[tool.hatch.build.targets.wheel]` 的 `shared-data` 或 `extra-metadata` 配置包含 templates

---

## 2. 中等问题 (Medium)

### M1. `.prompt` 文件处理有竞争条件 — `watcher.py:111-113`

```python
prompt = prompt_path.read_text(encoding="utf-8").strip()
prompt_path.unlink()
```

`read_text` 和 `unlink` 之间有窗口，另一个进程可能读到同一文件。注释说"rename-then-read"但实际是"read-then-unlink"。

**修复方案**: 先 rename 到 `.prompt.processing`，再 read，最后 unlink。

### M2. `mapping_manager.py` 的 `set_character`/`set_memory` 没有原子写入

其他所有 manager 都使用 `mkstemp` + `os.replace` 的原子写入模式，但 `MappingManager._set_file` 直接用 `path.write_text`：

```python
path.write_text(content, encoding="utf-8")
```

**影响**: 写入中止会导致半损坏的 character/memory 文件 — 这恰恰是最不能丢的数据。

### M3. `covenant_manager.py:82` — `hash()` 在不同 Python 进程间不稳定

```python
"covenant_hash": hex(hash(COVENANT_TEXT)),
```

Python 默认启用 `PYTHONHASHSEED` 随机化，`hash()` 在不同进程中返回不同值。这意味着 covenant 的"版本签名"每次重启都不同。

**修复方案**: 使用 `hashlib.sha256(COVENANT_TEXT.encode()).hexdigest()[:16]`。

### M4. `codex_manager.py` 没有并发保护

所有 codex 操作都是 `load → modify → save` 模式，如果两个 tool call 并发执行，会丢失写入。`asyncio.to_thread` 确实在线程池中运行这些操作，理论上可能并发。

**修复方案**: 添加 `threading.Lock` 保护 `_load` + `_save` 临界区。同理适用于 `email_manager.py` 的 `_save_read_state` 和 `_save_contacts`。

### M5. `pyproject.toml` 的 `scripts/` 不在包中

```toml
lingtai-watch = "scripts.watch:main"
```

但 `[tool.hatch.build.targets.wheel]` 只包含 `packages = ["src/lingtai_node"]`。`scripts/` 不在 wheel 中，所以 `lingtai-watch` 入口点在 `pip install` 后会报 `ModuleNotFoundError`。

### M6. `__init__.py` 没有导出重要模块

`__init__.py` 导出了 `AvatarManager`, `CovenantManager`, `SystemManager`, `serve`, `build_server`, `load_config`，但遗漏了 `EmailManager`, `CodexManager`, `LibraryManager`, `MappingManager`, `HeartbeatManager` 和 runtime 相关类。

### M7. `--dangerously-skip-permissions` 硬编码 — `session.py:58`

```python
cmd = [
    "claude",
    "-p", prompt,
    "--dangerously-skip-permissions",
    ...
]
```

这个 flag 绕过了 Claude Code 的所有权限检查。应该是可配置的，或至少在文档中警告。

---

## 3. 轻微问题 (Minor)

### L1. `.gitignore` 过于简略

只有 `__pycache__/`，缺少常见的 Python 项目忽略项：`*.egg-info/`, `.eggs/`, `dist/`, `build/`, `*.pyc`, `.env`, `venv/`, `.venv/`。已有 `.pyc` 文件被 git 跟踪。

### L2. 没有测试

项目完全没有测试文件。对于一个处理文件 I/O、网络通信、并发的 MCP server，至少需要：
- `EmailManager` 的 send/check/reply/search/archive 流程测试
- `CodexManager` 的 CRUD + consolidate 测试
- `validate_node` 的正/反例测试
- `HeartbeatManager` 的 start/stop/beat 测试
- 路径遍历防御的测试

### L3. 类型提示不完整

多数 `handle` 方法接收 `dict` 而非 `dict[str, Any]`。内部方法的返回值未标注（如 `_spawn`, `_list` 等）。

### L4. `library_manager.py:86-89` — 读取小文件内容无大小限制防御

```python
if entry.suffix in (".md", ".txt", ".json"):
    content = entry.read_text(encoding="utf-8")
    if len(content) <= 10000:
        skill["content"] = content
```

虽然有 10KB 限制，但 `read_text` 在检查长度前已经读完整个文件。如果有 1GB 的 `.md` 文件会 OOM。

### L5. `email_manager.py:313-314` — email ID 只有 12 hex 字符

```python
email_id = uuid4().hex[:12]
```

12 hex = 48 bits，碰撞概率在 ~1600 万封邮件后达到 0.1%。对当前规模足够，但文档中应说明。

### L6. README 缺少 avatar, covenant, system, contract 工具的文档

README.md 的 Tools 部分列出了 email, codex, library, node_info, mapping 但缺少 avatar, covenant, system, contract。

---

## 4. Contract 实现审查

### 5 Stores 覆盖

| Store | Contract 要求 | 实现状态 |
|-------|-------------|---------|
| Character | 文件映射 | `MappingManager` + `CLAUDE.md` template |
| Memory | 文件映射 | `MappingManager` + `memory.md` template |
| Long-Term Memory | 持久化存储 | `CodexManager` (`codex/codex.json`) |
| Skills | 可加载的程序 | `LibraryManager` (`.library/`) — 只有 `info` action，**缺少 save/create** |
| Communication | 消息传递 | `EmailManager` (`mailbox/`) |

**问题**: `LibraryManager` 只有 `info` (读取) action。Contract 第 4 条要求 "Provide tools for reading/**writing** to long-term memory, skills, and mailbox"。Skills store 缺少写入能力。

### 2 Hooks 覆盖

| Hook | Contract 要求 | 实现状态 |
|------|-------------|---------|
| Pre-Compact | 保存所有状态 | 通过 `CLAUDE.md` template 中的规则实现 |
| Post-Compact | 恢复状态 | 通过 Claude Code 自动加载 `CLAUDE.md` + `memory.md` 实现 |

### Validator 检查

`contracts/__init__.py:validate_node` 正确检查了：
- `.agent.json` 存在且可解析
- Runtime-specific character 文件存在（**error** 级别）
- Memory 文件存在（**warning** 级别 — 合理选择）
- `mailbox/{inbox,sent,archive}` 目录结构
- Long-term memory 目录存在（**warning** 级别）

**遗漏**: 没有检查 `.library/` 目录（Skills store）。

### Runtime Mapping 完整性

`contracts/__init__.py` 和 `mapping.py` 都有 runtime 映射表，但不同步：
- `contracts/__init__.py:RUNTIME_FILE_MAP` 包含 `lt_dir` 字段
- `mapping.py:RUNTIME_MAPPINGS` 不包含 long-term memory 目录名

这是两个独立的映射，容易分歧。应统一到一处。

---

## 5. 包结构审查

| 项目 | 状态 | 说明 |
|------|------|------|
| build backend | hatchling | 正确 |
| python requires | >=3.10 | 合理（用了 `X | Y` union 语法） |
| dependencies | `mcp>=1.0.0` | 仅一个依赖，简洁 |
| entry point `lingtai-node` | `lingtai_node.__main__:main` | 正确 |
| entry point `lingtai-watch` | `scripts.watch:main` | **broken** — scripts 不在 wheel 中 |
| wheel packages | `["src/lingtai_node"]` | 缺少 templates 和 contracts/NODE_CONTRACT.md |
| `py.typed` marker | 缺失 | 如果要支持类型检查消费者应添加 |

---

## 6. 安全审查总结

| 风险 | 严重性 | 位置 |
|------|--------|------|
| 路径遍历 (email/avatar/system) | Critical | C1 |
| ReDoS (email search) | Critical | C2 |
| `--dangerously-skip-permissions` | Medium | M7 |
| `.prompt` 文件非原子消费 | Medium | M1 |
| character/memory 非原子写入 | Medium | M2 |
| 无并发控制 | Medium | M4 |

---

## 7. 集成问题

| 问题 | 说明 |
|------|------|
| MCP server 稳定性 | 初始化失败时 server 仍然启动，tool call 返回 error — 这是正确的 graceful degradation |
| 文件监控 | `watcher.py` 用 2s polling，足够可靠但有竞争条件 (M1) |
| 跨平台 | `os.replace` 在所有平台原子；`os.fsync` 在 Windows 上行为不同但可接受；`tempfile.mkstemp` 跨平台安全 |
| 模板打包 | 安装后模板不可用 (C3) |

---

## 8. 结论与建议

### 是否建议合并？

**暂不建议合并**。需要先修复 3 个 Critical 问题：

1. **C1 路径遍历** — 安全漏洞，允许任意文件写入
2. **C2 ReDoS** — 安全漏洞，允许 CPU 拒绝服务
3. **C3 模板路径** — 功能性缺陷，安装后必然失败

### 修复优先级

| 优先级 | 问题 | 工作量估算 |
|--------|------|-----------|
| P0 | C1 路径遍历 | 添加 `_safe_resolve` helper |
| P0 | C2 ReDoS | 改用 `re.escape` 或限制复杂度 |
| P0 | C3 模板打包 | 改用 `importlib.resources` |
| P1 | M1-M7 | 每个约 10-30 行改动 |
| P2 | L1-L6 | 渐进改善 |
| P2 | 添加测试 | 需要较大投入 |

### 亮点

- Atomic write 模式在 6 个 manager 中一致使用（除 MappingManager），设计成熟
- Contract 设计清晰，5 stores + 2 hooks 抽象合理
- Graceful degradation — 初始化失败不阻塞 server
- CLAUDE.md template 写得出色，完整覆盖了 molt/recovery 流程
- 代码风格高度一致，命名清晰
