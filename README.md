# Music Toolkit  加密音频格式解密器

> **免责声明**
>
> 本工具仅用于学习格式识别与转码，不提供 DRM 绕过能力；使用者需自行确保对文件拥有合法处理权；项目不收集、不存储、不传输任何用户文件与密钥；如涉及第三方格式，相关格式名称与商标归各自权利人所有。

## 1. 功能概览

- 对某些音乐平台的加密格式进行解密（.ncm等）
- 拖拽或选择本地音频文件/文件夹，扫描并识别格式。
- 对普通音频执行 ffmpeg 离线转码：WAV / FLAC / MP3 / OGG。
- 支持批量任务、总进度、单任务进度、取消、失败原因展示、结果弹窗。
- CLI 与 GUI 共用同一套 services 业务层。
- 内置扫描/转换/格式识别测试，不下载任何平台音频文件。

## 2. 安装

要求 Python 3.10+。

```bash
python -m pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple
```

安装开发依赖：

```bash
python -m pip install -e ".[dev]" -i https://pypi.tuna.tsinghua.edu.cn/simple
```

ffmpeg 说明：

1. 优先使用系统 `PATH` 中的 `ffmpeg`。
2. 如果系统没有 ffmpeg，但安装了可选包 `imageio-ffmpeg`，框架会使用它自带的 ffmpeg 可执行文件：
   ```bash
   python -m pip install imageio-ffmpeg -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```
3. 两者都没有时，格式识别仍可用；转码会抛出 `FfmpegNotFound`，CLI 会友好提示。

## 3. 使用方法


### 方式一：直接使用（面向普通用户）
如果您拿到的是打包好的 `MusicTool.exe` 文件，请按以下步骤操作：

1. **启动软件**：双击 `MusicTool.exe` 即可打开界面（无需安装任何环境）。
2. **添加文件**：点击左上角的 **[添加文件]** 或 **[添加文件夹]**，或者直接将音频文件/文件夹**拖拽**到窗口中。
3. **设置输出**：在顶部指定一个 **输出目录**，在右侧选择你想要的 **输出格式**（如 MP3、FLAC、WAV 等）。
4. **开始转换**：点击右上角的 **▶ 开始转换** 按钮。
5. **查看结果**：转换完成后会弹出结果窗口，点击“打开输出目录”即可查看转换好的音频文件。

> **⚠️ 避坑提示**：
> 1. **无需额外配置**：软件已内置转码引擎，您无需在电脑上单独安装 FFmpeg。
> 2. **首次打开慢**：双击后可能需要等待 2-5 秒才会弹出界面，请耐心等待。
> 3. **杀毒软件误报**：由于是单文件打包程序，部分杀毒软件（360/火绒等）可能会将其误报。这是正常现象，请添加信任即可。

---

### 方式二：源码运行（面向开发者）
本仓库已为您准备好了开箱即用的环境，**无需在本地额外配置 FFmpeg 系统环境**（转码将由内置的 `imageio-ffmpeg` 库自动接管）。

**📦 极速启动**：您克隆或下载源码后，直接双击 `run.bat` 即可自动安装依赖并启动图形界面。

或者手动在终端执行：
```bash
# 1. 安装项目及所需依赖
pip install -e . ncmdump-py standard-imghdr pycryptodome -i https://pypi.tuna.tsinghua.edu.cn/simple

# 2. 启动图形界面
python -m music_toolkit
## 5. GUI 使用

- **添加文件 / 添加文件夹**：支持多选；也可以把文件或文件夹拖到窗口。
- **包含子文件夹**：添加文件夹时控制是否递归。
- **输出目录**：只读输入框，点击右侧 `📁` 选择目录；悬停有提示。
- **输出格式**：MP3（默认）/ FLAC / WAV / OGG。
- **保留子文件夹结构**：按输入根目录还原相对路径。
- **覆盖已存在文件**：关闭时自动在扩展名前加 `_1`、`_2`。
- **开始转换**：需要至少一个 OFFLINE 任务、输出目录存在且可写；会弹出确认框。
- **取消**：通过 `threading.Event` 通知 worker；已完成文件保留，`.part` 临时文件清理。
- **表格**：支持搜索、点击表头排序；按级别着色——OFFLINE 绿、KEYED 黄、DETECT_ONLY 橙、ERROR 红。
- **行关联**：表格行 iid 直接存 `job_id`，收到任务消息时按 iid 更新状态/进度/错误，不增加隐藏列。
- **元数据**：选中行后通过 `metadata_service.read_metadata(path)` 读取并显示时长、码率、标题/艺术家/专辑。
- **快捷键**：`F5` 开始，`Esc` 取消。
- **结果弹窗**：显示总计、成功、失败；失败列表可折叠，双击失败行显示完整路径与错误；可打开输出目录。

## 6. 支持矩阵

### 6.1 魔数表

detector 只读取文件前 16 字节，按以下顺序匹配，命中即停：

| 格式名 | 偏移 | 匹配规则 |
|---|---|---|
| wav | 0 | 前 4 字节 == `RIFF` 且偏移 8 的 4 字节 == `WAVE` |
| flac | 0 | 前 4 字节 == `fLaC` |
| ogg | 0 | 前 4 字节 == `OggS` |
| mp3 | 0 | 前 3 字节 == `ID3`；或前 2 字节 == `FF FB` / `FF F3` / `FF F2` |
| ncm | 0 | 前 8 字节 == `CTENFDAM` |
| kwm | 0 | 前 8 字节 == `yeelion` |
| kgm / kgma | 0 | 前 4 字节 == `kgm1` 或 `kgm2`；无法确认时退回扩展名 |
| kgg | 0 | 前 4 字节 == `kgg1`；无法确认时退回扩展名 |
| mflac / mgg（qmc2） | 0 | 前 4 字节 == `QTag` 或 `STag`；无法确认时退回扩展名 |
| mgg1 / mgg2 / mmp4（qmc3） | 0 | 无稳定前 16 字节魔数，退回扩展名 |


### 6.2 扩展名归并表

| 扩展名 | 归并后的 format_name |
|---|---|
| `.wav` | wav |
| `.flac` | flac |
| `.mp3` | mp3 |
| `.ogg` | ogg |
| `.ncm` | ncm |
| `.qmc0` / `.qmc3` / `.qmc2` / `.qmcogg` / `.qmcflac` / `.tkm` | qmc1 |
| `.mflac` / `.mgg` | qmc2 |
| `.mgg1` / `.mgg2` / `.mmp4` | qmc3 |
| `.kgm` / `.kgma` | kgm |
| `.vpr` | vpr |
| `.kgg` | kgg |
| `.kwm` | kwm |
| 其他 | UNKNOWN |

`.mflac` / `.mgg` 统一归为 qmc2，不区分内嵌/外置密钥，因为区分需要读取文件尾部，违反“只读前 16 字节”的约束。

### 6.3 支持级别映射

| format_name | 支持级别 | 当前行为 |
|---|---|---|
| wav / flac / mp3 / ogg | OFFLINE | 正常转码 |
| ncm / qmc1 / qmc2 / kgm / kgma / vpr / kwm | OFFLINE | 识别成功，`convert` 抛 `UnsupportedFormat` |
| kgg | KEYED | 识别成功，`convert` 抛 `MissingKey` |
| qmc3 | DETECT_ONLY | 仅识别，`convert` 抛 `UnsupportedFormat` |
| UNKNOWN | ERROR | 识别失败 |

### 6.4 截断文件规则

1. 实际读到少于 16 字节：先尝试用已有字节匹配魔数；匹配成功按魔数返回；失败返回 `("UNKNOWN", ERROR)`，**不退回扩展名**。
2. 读到 0 字节：直接 `("UNKNOWN", ERROR)`。
3. 文件不存在或不可读：捕获异常并返回 `("UNKNOWN", ERROR)`，不抛。
4. 截断判定只看前 16 字节是否足以完成魔数判定，不依赖文件总大小。

## 7. 架构与调用链

```text
gui/  ──▶ services/ ──▶ core/ + plugins/
cli.py ─▶ services/ ──▶ core/ + plugins/
```

- `core/`：纯逻辑，禁止 import 任何 GUI 库。
- `services/`：业务编排，禁止 import 任何 GUI 库。
- `gui/`：只调用 services，不直接 import core/plugins。
- `cli.py`：与 GUI 共享 services，不重复业务逻辑。
- `core/registry.py`：只提供 `PluginRegistry`，不扫描、不 import plugins。
- `services/plugin_loader.py`：显式导入并注册四个内置插件。
- `services/app_factory.bootstrap_app()`：统一装配依赖，GUI 与 CLI 都只调用它。

固定调用链：

```text
TaskService.run_batch(job)
  1. detector.detect(src) -> (format_name, level)
  2. DETECT_ONLY / ERROR -> SKIPPED / FAILED
  3. registry.get(format_name)
  4. 插件不存在 -> UnsupportedFormat
  5. plugin.convert(src, dst, cancel_event, key=None)
  6. 回调并更新 JobStatus
```

`key` 参数固定为 `None`：框架不提供用户密钥输入入口。因此：

- KEYED 格式（如 kgg）必然走 `MissingKey` 分支。
- OFFLINE 加密占位格式（如 ncm）走 `UnsupportedFormat` 分支。
- DETECT_ONLY 格式（如 qmc3）由调度器直接跳过，插件本身也抛 `UnsupportedFormat`。

`core/converter.py` 只提供 `is_ffmpeg_available()`、`run_ffmpeg()` 等工具函数，只被 `plugins/builtin_audio.py` 调用；`TaskService` 不直接调用它，也不注册插件。

## 8. 异常

所有业务异常定义在 `core/errors.py`：

- `MusicToolkitError`
- `UnsupportedFormat`
- `MissingKey`
- `DecryptFailed`（预留，框架不执行解密）
- `TranscodeFailed`
- `FfmpegNotFound`

## 9. 插件开发指南

1. 继承 `core.plugin_base.BasePlugin`。
2. 声明 `format_names: tuple[str, ...]` 与 `support_level: SupportLevel`。
3. 实现签名：

   ```python
   def convert(self, src, dst, cancel_event=None, key: bytes | None = None) -> None:
       ...
   ```

4. 只处理自己声明的格式名，不重复实现魔数识别。
5. 普通音频插件调用 `core.converter.run_ffmpeg(src, dst, cancel_event)` 并忽略 `key`。
6. 加密格式插件只保留占位：不支持时抛 `UnsupportedFormat`，需要密钥时抛 `MissingKey`。框架不提供真实算法。
7. 在 `services/plugin_loader.py` 中显式实例化并调用 `registry.register_plugin(plugin)`。不要修改 `core/registry.py` 去做自动扫描。
8. 所有异常必须来自 `core.errors`。

## 10. 测试

```bash
python -m pytest -q
```

测试覆盖：

- 魔数优先级、扩展名归并、截断规则、空文件、级别映射。
- 输出路径规划、重名编号、保留结构、非法字符。
- TaskService 回调、取消、调用顺序、`key=None`。
- 插件契约、注册表、消息协议、异常。
- AST + 运行时 import 边界（core/services 不加载 GUI）。
- `bootstrap_app()` 装配与独立性。
- CLI detect/info/convert/scan。
- GUI 冒烟（3 秒自动关闭）与表格 iid 关联。
- ffmpeg 真实端到端转码（不可用时自动 skip 并注明）。

测试音频样本位于 `tests/fixtures/`，由 ffmpeg 生成 1 秒静音 WAV / FLAC / MP3 / OGG；不下载任何平台文件。

## 11. 目录结构

```text
music-toolkit/
  pyproject.toml
  README.md
  run.bat
  src/music_toolkit/
    __init__.py
    __main__.py
    cli.py
    core/
      __init__.py
      models.py
      errors.py
      plugin_base.py
      detector.py
      metadata.py
      converter.py
      registry.py
    services/
      __init__.py
      app_factory.py
      plugin_loader.py
      metadata_service.py
      scan_service.py
      output_planner.py
      task_service.py
      messages.py
    gui/
      __init__.py
      app.py
      main_window.py
      workers.py
      result_dialog.py
      log_handler.py
      widgets/
        __init__.py
    plugins/
      __init__.py
      builtin_audio.py
      encrypted_offline.py
      encrypted_keyed.py
      encrypted_detect_only.py
  tests/
    fixtures/
    test_detector.py
    test_output_planner.py
    test_task_service.py
    test_errors.py
    test_messages.py
    test_import_boundaries.py
    test_plugin_registry.py
    test_plugin_contract.py
    test_call_chain.py
    test_app_factory.py
```

> 注：`gui/workers.py` 负责创建 daemon 线程；具体 worker 逻辑在 `main_window.py` 中以局部函数实现。worker 只向 `queue.Queue` 投递消息，不在子线程操作 Tk 控件。

## 12. 边界与已知限制

- 不内置任何平台密钥，不伪造解密算法，不把不同格式算法混在一起。
- 加密格式只做格式识别与支持级别判定；插件只有接口与占位，调用时抛明确异常。
- `qmc2` 不区分 QTag / STag 内嵌或外置密钥，因为区分需要读文件尾部。
- `.kgma` 在扩展名归并表中归并为 `kgm`。
- 框架不提供用户密钥输入入口，`TaskService` 调用插件时 `key` 固定为 `None`。
- ffmpeg 缺失时无法转码，但识别、扫描、CLI `detect/info`、加密格式占位判定仍可用。
- GUI 需要本地显示环境；无显示环境时按降级策略只做 import/类定义检查。
- 项目不收集、不存储、不传输任何用户文件与密钥。

## 13. 许可

MIT License。仅用于学习与研究。
