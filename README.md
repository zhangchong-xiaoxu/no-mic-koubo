# no-mic-koubo · 不用麦克风的口播

不录音、不开剪辑软件，用五步做一条竖屏口播视频：写稿 → 本地克隆配音 → 脚本处理和核对 → 自动截图 → Remotion 出片。

这是我（张翀）做抖音口播视频的流水线精简版。原片工程的代码是我在 VS Code 里定好规则、让 Claude Opus 5.5 写的，这个模板也由 AI 从中精简而来。

```text
script.json ──tts.py──▶ audio/narr/*.wav ──build_audio.py──▶ narration.wav + segments.json ──┐
shots.json  ──shot.mjs──▶ remotion/public/shots/*.png ─────────────────────────────────────────┴─▶ remotion render ▶ out/video.mp4
```

## 交给 AI 做

在任意带 AI 助手的 IDE 里（Claude Code、Copilot、豆包、WorkBuddy 等），把仓库地址和下面这句话发给它：

> 克隆这个仓库，先读 AGENTS.md，运行 `python doctor.py --json` 检查我的机器，缺什么先告诉我、我同意再装，然后帮我做一条口播视频。

`doctor.py` 只检测、不安装：它查 ffmpeg、Node、浏览器、显卡和显存、Docker、TTS 服务，给出缺项、安装命令和推荐的配音方案。AGENTS.md 是给助手读的入口，不是所有 IDE 都会自动读取，所以请把这句话一起发过去。

## 需要准备

| 东西 | 用途 | 备注 |
|---|---|---|
| Docker + NVIDIA 显卡 | 跑本地 TTS | 我用 RTX 4060 Ti 16G；8 秒音频约 4 秒生成。显存较小用 `--size 0.6B`；没有 NVIDIA 显卡见下方兜底 |
| [faster-qwen3-tts-studio](https://github.com/hangry-labs/faster-qwen3-tts-studio) | Qwen3-TTS 的网页界面 + OpenAI 兼容接口 | 预设音色、一句话设计声音、十几秒克隆 |
| Python 3.10+ | `tts.py`（只用标准库）、`build_audio.py` | 核对步骤另装 `pip install sherpa-onnx soundfile numpy` |
| ffmpeg | 去静音、变速、响度 | 需在 PATH 里 |
| Node.js 22+ | `shot.mjs`、Remotion | 截图用本机 Edge 或 Chrome |

启动 TTS（按 Studio 官方 README，只监听本机）：

```bash
docker run -d --name faster-qwen3-tts-studio --gpus all -p 127.0.0.1:7860:7860 \
  -v faster_qwen3_tts_studio_data:/app/persistent hangrylabs/faster-qwen3-tts-studio:v1.0
```

浏览器打开 `http://127.0.0.1:7860`。想用自己的声音：在 Studio 里录或上传十几秒干净人声，克隆后保存成一个声音名，填进 `script.json` 的 `voice`。

## 五步

**① 写稿**：编辑 `script.json`。一句一段；`title` 是画面大字，`image` 是截图（可选）。数字写成汉字（`十九万`），字幕里显示成什么写在 `display`。

**② 配音**：

```bash
python tts.py              # 已有的 wav 不重做；单句重来：python tts.py --only s03 --seed 11
python tts.py --size 0.6B  # 显存较小时用 0.6B 模型
```

没有 NVIDIA 显卡（Mac 也是）或装不了 Docker 时，用联网兜底：`pip install edge-tts`，再 `python tts.py --backend edge`。它免费，但**稿子会发给微软的在线服务**，也不能克隆自己的声音；音色在 `script.json` 里用 `edge_voice` 指定（默认 `zh-CN-XiaoxiaoNeural`）。

**③ 处理和核对**：去首尾静音、加速（默认 `tempo` 1.2，保持音高）、每句 −16 LUFS，拼成整轨并写出时间轴。`--check` 用语音识别把每句听一遍，相似度低于 0.85 标 `CHECK`。

```bash
python build_audio.py --check
```

`--check` 是可选的，缺依赖或模型时会跳过。核对用的 FireRed 模型（Apache-2.0，解压后约 740 MB）需先下载到 `~/.cache/koubo/`，或用 `KOUBO_ASR_MODEL` 指定路径：

```bash
mkdir -p ~/.cache/koubo && cd ~/.cache/koubo
curl -LO https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-fire-red-asr2-ctc-zh_en-int8-2026-02-25.tar.bz2
tar xjf sherpa-onnx-fire-red-asr2-ctc-zh_en-int8-2026-02-25.tar.bz2
```

**④ 截图**：在 `shots.json` 里写网址和输出路径，2 倍像素截真实页面。

```bash
node shot.mjs shots.json
```

**⑤ 出片**：

```bash
cd remotion
npm install
npm run studio   # 边改边预览
npm run render   # 输出 out/video.mp4，1080×1920
```

画面在 `remotion/src/Main.tsx`，每句一个 `Scene`，字幕按句内字数比例跟着配音走。想要更多动效就改这个文件，或者把规则讲清楚让 AI 写。

## 踩过的坑

- **Windows 上 WSL 内存先爆**：Docker 的 WSL 虚拟机会吃掉大量提交内存。在 `%UserProfile%\.wslconfig` 写 `[wsl2]`、`memory=10GB`、`swap=2GB`，按自己的内存调整。
- **识别前补 0.3 秒静音**：去掉静音后直接识别，第一个字经常被吞；`build_audio.py` 已经补了。
- **英文品牌词识别不准**：`Qwen3-TTS`、`Remotion` 这类词常被标 `CHECK`，以试听为准。
- **长句要切**：一次合成太长会变差，`tts.py` 按句末标点切到每段 ≤100 字再拼。
- **数字念错**：口播稿写汉字，字幕用 `display` 换回数字。

## 许可与合规

- 本仓库代码：MIT，见 [LICENSE](LICENSE)。
- Remotion 不是 MIT：个人、≤3 人的营利公司、非营利组织可免费商用，更大的公司需要买 Company License，见 [Remotion License](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md)。
- Qwen3-TTS 官方权重 Apache-2.0；faster-qwen3-tts-studio MIT；FireRed ASR Apache-2.0。模型都不在本仓库里，用之前看各自的许可。
- 只克隆你自己或明确同意的人的声音。
- 在中国大陆发布 AI 合成内容要标识（《人工智能生成合成内容标识办法》2025-09-01 起施行）：画面左上角默认有「配音：AI 合成」，发布时也要勾选平台的 AI 声明。
