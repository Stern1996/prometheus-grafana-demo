# 从这里拿到你的 gig 画廊图（约 15 分钟）

你不需要写代码，也不用碰任何公司系统。整套环境已经在这台机器上了。

---

## 你已经有的东西

`prometheus-grafana-demo/` 里已经放好了**下载并解压完成的**二进制：

| 组件 | 版本 | 大小 |
|---|---|---|
| Prometheus | 3.13.4 | ~102 MB |
| Grafana | 13.2.3 | ~451 MB |
| 演示 API 服务 | 自带 | 纯标准库 Python，无需 pip |

**不需要再下载任何东西。** 如果你以后想清掉这 550MB，删掉 `bin/` 就行，重跑时会提示你重新下载。

---

## 四步

### 1. 启动（约 40 秒）

```powershell
cd D:\Harness-Projects\prometheus-grafana-demo
powershell -ExecutionPolicy Bypass -File scripts\start.ps1
```

脚本会依次拉起演示 API、Prometheus、Grafana 和压测流量，并等待三个服务就绪。

> **第一次启动 Grafana 会慢一些**，因为它要联网安装 Prometheus 数据源插件（Grafana 13 把数据源改成了插件形式）。等它就绪输出 `[ok] grafana` 即可。之后再启动就是秒开。

### 2. 等 10–15 分钟 ⏱️

**这一步不能省。** 仪表盘画的是时间序列，刚启动时图上只有几个点，截图会很难看。

等 10 分钟以上，你会得到：
- 至少一个完整的"故障窗口"（延迟尖峰 + 5xx 上升）—— 这正好证明你的告警是有用的
- 饱满的曲线，而不是几条直线

期间可以打开 http://127.0.0.1:3000/d/service-overview 看它慢慢长出来。

### 3. 截图

```powershell
# 主图：完整仪表盘
powershell -ExecutionPolicy Bypass -File scripts\screenshot.ps1 -Width 1920 -Height 1220 -Name 01-dashboard

# 只截最近 10 分钟（数据更干净）
powershell -ExecutionPolicy Bypass -File scripts\screenshot.ps1 -From now-10m -Name 01-dashboard-10m

# 也可以截更大
powershell -ExecutionPolicy Bypass -File scripts\screenshot.ps1 -Width 2560 -Height 1600 -Name 01-dashboard-4k
```

图片输出到 `gallery/`。

### 4. 关掉

```powershell
powershell -ExecutionPolicy Bypass -File scripts\stop.ps1
```

---

## 该截哪几张

Fiverr 的 gig 画廊最多 3 张图。建议：

| 顺序 | 内容 | 来源 | 状态 |
|---|---|---|---|
| 1 | **仪表盘全貌** | `screenshot.ps1` 截 Grafana | 你要生成 |
| 2 | **架构图** | `gallery/02-architecture.png` | ✅ 已做好 |
| 3 | **告警规则** | 截 http://127.0.0.1:9090/rules?theme=dark | 你要生成 |

第 1 张是决定点击率的那张，**值得多截几个时间点和尺寸，挑最好的**。

---

## 常见问题

**Q：Grafana 起来了但面板全是 "No data"**
第一次启动时插件可能还没装完。看 `logs\grafana\grafana.log` 里有没有
`plugin prometheus not found`。有的话等 1–2 分钟再刷新；如果一直不行，
停掉重跑一次 `start.ps1`。

**Q：端口被占用**
`start.ps1` 支持改端口：
```powershell
powershell -ExecutionPolicy Bypass -File scripts\start.ps1 -AppPort 18080 -PromPort 19090 -GrafanaPort 13000
```

**Q：截图是空白或只画了一半**
Grafana 是单页应用，需要时间渲染。`screenshot.ps1` 已经给了 25 秒的虚拟时间预算。
如果还是不全，加大 `--virtual-time-budget`（在 `screenshot.ps1` 第 60 行附近）。

**Q：想换仪表盘的时间范围**
```powershell
powershell -ExecutionPolicy Bypass -File scripts\screenshot.ps1 -From now-1h -To now
```

---

## ⚠️ 一条硬规则

**绝对不要把公司环境的 Grafana 大盘截图放进 gig 画廊。** 那既涉及数据泄露，也可能违反你的竞业与保密义务。

这套演示环境存在的意义就是：**你有一个可以合法展示、且完全属于自己的作品。** 而且它能证明一件更重要的事——你不依赖公司的现成环境，也能从零把东西搭起来。

---

## 顺带说一句：这份东西本身就是作品

`prometheus-grafana-demo/` 可以直接推到一个公开 GitHub 仓库：

- 配置全部是代码，可复现、可审阅
- README 是英文的，可以直接当作品集说明
- 演示服务的指标是它**真实测量自己**得到的，不是硬编码的假数据

面试或者客户问起来，你可以直接说："这是我自己的环境，你可以 clone 下来跑。"

这比任何口头描述都有说服力。
