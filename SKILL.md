---
name: gif-toolkit
description: 本地 GIF 和视频处理工具箱。基于 FFmpeg，支持 GIF/MP4/WebP 格式互转、调速、压缩、加文字、裁剪、合并等 14 种操作。全部本地处理，无需上传。
allowed-tools: exec
---

# GIF Toolkit Skill

## 概述

本技能提供完整的 GIF/视频处理能力，使用本地 FFmpeg 实现，不依赖任何外部网站或 API。

**核心工具脚本**：`tools/gif-toolkit.py`（工作区根目录下）

**调用方式**：
```bash
python tools/gif-toolkit.py <command> [options]
```

---

## 命令清单

### 1. info — 查看媒体信息
查看 GIF/视频文件的元数据（尺寸、时长、帧率、大小等）。
```
python tools/gif-toolkit.py info <input_file>
```

### 2. to-mp4 — GIF 转 MP4
将 GIF 动图转换为 MP4 视频（H.264 编码，兼容性好，文件更小）。
```
python tools/gif-toolkit.py to-mp4 input.gif [-o output.mp4]
```

### 3. to-webp — GIF 转 WebP
将 GIF 动图转换为 WebP 动图（现代格式，更小更快）。
```
python tools/gif-toolkit.py to-webp input.gif [-o output.webp] [-q 6]
```
- `-q 0-6`：压缩级别，默认 6（最高质量）

### 4. to-gif — 视频转 GIF
将 MP4/AVI/MOV 等视频转换为 GIF 动图（使用调色板优化画质）。
```
python tools/gif-toolkit.py to-gif input.mp4 [-o output.gif] [--fps 10] [--width 480]
```
- `--fps`：输出帧率，默认 10
- `--width` / `--height`：输出尺寸

### 5. speed — 调整播放速度
加速或减速播放。`2.0`=2倍速，`0.5`=半速。
```
python tools/gif-toolkit.py speed input.gif -m 2.0 [-o output.gif]
```
- `-m, --multiplier`：速度倍率（必需）

### 6. compress — 压缩 GIF
通过减少颜色数量来减小 GIF 文件体积。
```
python tools/gif-toolkit.py compress input.gif [-o output.gif] [-c 128] [--no-dither]
```
- `-c, --colors`：颜色数量 2-256，默认 128（越小文件越小）
- `--no-dither`：禁用抖动

### 7. reverse — 倒放
将 GIF/视频倒放播放。
```
python tools/gif-toolkit.py reverse input.gif [-o output.gif]
```

### 8. trim — 裁剪时长
提取指定时间段的片段。
```
python tools/gif-toolkit.py trim input.gif -s 1.5 -d 3 [-o output.gif]
```
- `-s, --start`：起始时间（秒）
- `-d, --duration`：持续时长（秒）

### 9. resize — 调整尺寸
缩放到指定尺寸。可只指定宽或高，自动保持比例。
```
python tools/gif-toolkit.py resize input.gif --width 320 [-o output.gif]
python tools/gif-toolkit.py resize input.gif --width 320 --height 240 [-o output.gif]
```
- `--width`：目标宽度
- `--height`：目标高度

### 10. crop — 画面裁剪
裁切指定区域（宽:高:X偏移:Y偏移）。
```
python tools/gif-toolkit.py crop input.gif --width 300 --height 200 --x 50 --y 50 [-o output.gif]
```
- `--width`、`--height`：裁剪区域尺寸
- `--x`、`--y`：裁剪起始位置

### 11. text — 添加文字
在 GIF/视频上叠加文字（支持中文，自动半透明背景）。
```
python tools/gif-toolkit.py text input.gif "Hello World" [--font-size 36] [--font-color white] [-o output.gif]
```
- 第2个位置参数为要添加的文字内容
- `--font-size`：字号，默认 24
- `--font-color`：颜色，默认 white
- `--x` / `--y`：文字位置（默认居中/底部）

### 12. loop — 修改循环次数
设置 GIF 循环播放次数。
```
python tools/gif-toolkit.py loop input.gif -c 0 [-o output.gif]
```
- `-c, --count`：0=无限循环，1=播放一次

### 13. frames — 提取帧
将 GIF/视频的每一帧导出为 PNG 图片。
```
python tools/gif-toolkit.py frames input.gif [-o output_dir/]
```

### 14. merge — 合并文件
将多个 GIF/视频连接成一个文件。
```
python tools/gif-toolkit.py merge input1.gif input2.gif input3.gif [-o output.gif]
```

---

## 使用示例

**场景1：用户发了一个 GIF 说转成 MP4 发群里**
```
python tools/gif-toolkit.py to-mp4 demo.gif -o demo.mp4
```

**场景2：用户说 GIF 太大，压缩一下**
```
python tools/gif-toolkit.py compress big.gif -c 64
```

**场景3：用户说给 GIF 加一句文字**
```
python tools/gif-toolkit.py text funny.gif "笑死我了" --font-size 32 -o funny_text.gif
```

**场景4：需要提取 GIF 的某一帧做封面**
```
python tools/gif-toolkit.py frames animation.gif -o temp_frames/
```
然后用 `temp_frames/frame_0001.png` 即可。

---

## 注意事项

1. **FFmpeg 位置**：`C:\Users\Administrator\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe`
2. **中文字体**：使用 Windows 内置 `msyh.ttc`（微软雅黑），无需额外安装
3. **输出位置**：默认输出到输入文件同目录，文件名自动加后缀
4. **临时文件**：处理过程中产生的 palette 文件自动清理
5. **大文件处理**：本地处理，无文件大小限制，建议在 `temp/` 目录操作临时文件
6. **输出目录**：最终结果放入 `outputs/` 目录按日期管理