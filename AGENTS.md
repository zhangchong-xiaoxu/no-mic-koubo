# AGENTS.md

这是「不用麦克风的口播」流水线模板：`script.json` → 配音 → 处理核对 → 截图 → Remotion 出片。详细说明见 [README.md](README.md)。

## 开始前：先跑环境检测

```bash
python doctor.py --json
```

- 它只读、不安装任何东西。看 `ready`、`checks`、`tts` 和 `next_steps`。
- `next_steps` 里的安装命令要先告诉用户、得到同意再执行；不要自动装 Docker、驱动或改系统设置。
- 全部 `ready` 之后，按 README 的五步走；配音命令用 `tts_command` 给出的那条。

## 配音方案（doctor 会据机器推荐）

| 机器 | 方案 | 说明 |
|---|---|---|
| NVIDIA 显卡 + Docker，显存约 12GB 以上 | `python tts.py`（本地 Qwen3-TTS 1.7B） | 可克隆自己的声音 |
| NVIDIA 显卡 + Docker，显存约 6–12GB | `python tts.py --size 0.6B` | 显存门槛是经验值，以实测为准 |
| 无 NVIDIA 显卡（含 Mac）或 Docker 不可用 | `python tts.py --backend edge` | 联网、免费；**稿子会发给微软服务**，不能克隆声音 |

- 使用 `edge` 兜底前必须征得用户同意，并告知上面两点；需要 `pip install edge-tts`。
- 换了配音方案，画面左上角「配音：AI 合成」标识照旧保留；发布时仍要勾选平台的 AI 声明。
- 只克隆用户本人或明确同意的人的声音。

## 约定

- 稿子口播部分数字写汉字，字幕显示用 `display` 换回数字。
- `build_audio.py --check` 是可选步骤：缺 ASR 模型或依赖时会跳过，不要为它下载 740 MB 模型，除非用户要。
- `audio/`、`remotion/public/` 下的产物不提交。
