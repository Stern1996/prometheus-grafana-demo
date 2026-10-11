# Gig 图片素材（Fiverr 规格）

三张图，都是 **1280×769**（Fiverr 推荐尺寸），远超最低要求，且都远小于 5MB 上限。

上传顺序就是文件名顺序。

| 文件 | 内容 | 大小 | 作用 |
|---|---|---|---|
| `01-dashboard.png` | Grafana 仪表盘 | 338 KB | **主图**——决定点击率 |
| `02-architecture.png` | 架构图 | 136 KB | 证明你理解整套数据流 |
| `03-alert-rules.png` | Prometheus 告警规则 | 124 KB | 证明你配了告警，不只是画图 |

全分辨率原图在 `../gallery/`（1920×1220 / 2560×1520 / 3000×1802），Upwork 或作品集站点想用更大的图可以从那里取。

---

## 上传到 Fiverr 时的三个要点

1. **`01-dashboard.png` 放第一张。** Fiverr 用第一张图做搜索缩略图，而曝光几乎完全由点击率驱动。
2. **不要在上传时让 Fiverr 帮你裁剪。** 这三张已经是正确比例，直接传原图。
3. **不要加文字水印或贴纸。** 平台不鼓励，而且会挡住本来就小的图表细节。

---

## 为什么主图选"当前健康 + 历史有故障"这一张

看 `01-dashboard.png`：

- **当前值全是绿的**：错误率 1.25%、p95 229ms、worker 利用率 22.3%、缓存命中 96.8%
- **但过去 10 分钟里有两段明显的故障窗口**：p99 尖峰、5xx 上升、队列堆积

这个组合是刻意的。只截全绿的图，客户看不出监控的价值；只截全红的图，像是在展示一个坏掉的系统。**"现在很好，而且我能看见曾经出过什么问题"** 才是卖点。

`../gallery/extras/dashboard-incident.png` 是故障进行中抓的版本，想强调"我能帮你定位问题"时可以换着用。

---

## 这些图是真的

演示服务 `../demo-app/app.py` 里的每一个数字都来自它**自己真实处理 HTTP 请求的测量**：请求计数来自真实请求，延迟直方图来自真实的 `time.perf_counter()` 计时，故障窗口是它真的在返回 500。没有任何硬编码的假曲线。

所以客户问起来，你可以直接说：

> 这是我自己的演示环境，你可以 clone 下来跑，五分钟看到同样的图。

---

## 重新生成

```powershell
cd D:\Harness-Projects\prometheus-grafana-demo

# 1) 起环境（首次会下载/安装 Grafana 插件）
powershell -ExecutionPolicy Bypass -File scripts\start.ps1

# 2) 等 10 分钟以上，让曲线长出来

# 3) 截全分辨率原图到 gallery/
powershell -ExecutionPolicy Bypass -File scripts\screenshot.ps1 -From now-10m -Name 01-dashboard

# 4) 转成 Fiverr 规格到 gig-assets/
python scripts\build_gig_assets.py

# 5) 关掉
powershell -ExecutionPolicy Bypass -File scripts\stop.ps1
```

`build_gig_assets.py` 会把每张原图按"等比缩放 + 定向裁剪"处理成 1280×769，不会出现黑边。仪表盘那张锚定顶部，避免切掉时间选择器。
