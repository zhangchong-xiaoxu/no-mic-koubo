# Progress

更新日期：2026-11-09

## 当前状态

五步流水线可用；新增 `doctor.py` 环境检测和 `tts.py` 的 `edge` 联网兜底，让任意 IDE 的 AI 助手拿到仓库地址就能自检并出片。暂无 decision 文档。

## 下一步

1. 在没有 NVIDIA 显卡的机器（如 Mac）上实测 `python doctor.py` 和 `python tts.py --backend edge` 全流程；完成条件：能从 `script.json` 出到 `remotion/out/video.mp4`。无需审批。
2. 在一台显存 6–12GB 的机器上实测 `--size 0.6B`，校正 `doctor.py` 里 12000/6000 MiB 的显存门槛（目前是估计值），并确认 Studio 实际加载的是 0.6B。
3. 写 `docs/decisions/0001-tts-backend-tiers.md`（分档依据、复查触发），并让 `shot.mjs` 与 `doctor.py` 共用浏览器路径列表。

## 进行中 / 卡住

- 未验证：豆包、WorkBuddy 是否自动读取 `AGENTS.md`（README 已附可直接发给助手的话作为兜底）。
- 未验证：`build_audio.py --check` 缺 ASR 模型时的“跳过”分支（本机已装模型，只做了语法检查）。
- 未提交 / 未推送：`5d85610` 已在 `origin/main`；`docs/` 下两份新文档待提交。

## 怎么验证还能用

```text
python doctor.py                                       # 预期：缺项和下一步清晰，本机 ready
python -m py_compile tts.py doctor.py build_audio.py   # 预期：无输出
cd remotion; npm run typecheck                         # 预期：tsc 无报错
```

## 资料入口

- [文档地图与决策索引](README.md)
- [AGENTS.md](../AGENTS.md)：给 AI 助手的入口；[README.md](../README.md)：五步说明。
- Studio 官方说明：https://github.com/hangry-labs/faster-qwen3-tts-studio（仅支持 NVIDIA，含 0.6B / 1.7B）。

## 交接日志

- 2026-11-09：新增 `AGENTS.md`/`CLAUDE.md`/`doctor.py`；`tts.py` 加 `--backend studio|edge`、`--size`；`build_audio.py --check` 缺依赖时跳过；README 增“交给 AI 做”。验证：doctor 本机 ready 且模拟无显卡/8GB 两档正确、edge 合成 1 句、studio 与 `--size 0.6B` 各合成 1 句、typecheck 通过；commit `5d85610`。
