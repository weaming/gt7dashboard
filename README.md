# gt7dashboard

gt7dashboard 是 Gran Turismo 7 的实时仪表盘。基于近期发现的 GT7 遥测接口，首次描述见[此处](https://www.gtplanet.net/forum/threads/gt7-is-compatible-with-motion-rig.410728 )。此项目最初是 Bornhall 的 [gt7telemetry](https://github.com/Bornhall/gt7telemetry) 的一个分支。

详见[手册](#manual)获取详细说明。

## 功能特点

![](README.assets/screenshot.png)
![](README.assets/screenshot_race_line.png)

* 上一圈与参考圈的时间差图
  * *虚线以下*表示优于参考圈，*虚线以上*表示劣于参考圈
* 赛车线视图，显示上一圈和参考圈的速度峰值和谷值
* 上一圈、参考圈和中位圈的速度/距离图
  * 中位圈由所有近期圈速的中位数计算得出
* 速度偏差图，显示最佳圈速中的速度偏差
* 参考圈选择器
  * 默认为最佳圈
* 油门/距离图
* 刹车/距离图
* 滑行/距离图
* 赛车线图
* 速度峰值和谷值表，对比参考圈和上一圈
* 相对燃油图，用于选择合适的燃油设置以达到目标距离、剩余时间和期望圈速
* 所有近期圈速列表及附加指标，以百分比 * 1000 计量以便阅读
* 调校相关附加数据，如最高速度和最小车身高度
* 保存当前圈速和重置所有圈速的功能
* 近期圈速的赛车线，显示油门（绿色）、刹车（红色）和滑行（蓝色）
* 仅含燃油图的附加"比赛视图"
* 可选刹车点（较慢），设置 `GT7_ADD_BRAKEPOINTS=true` 启用
* 从圈速表中添加附加圈速到图表中

### 获取演示圈或回放的遥测数据

启用"记录回放"复选框以始终记录回放。否则，仅记录您实际驾驶的圈速。

## 简易安装（Windows）

无需 Python。从 [Releases](https://github.com/snipem/gt7dashboard/releases) 页面下载最新的预构建 Windows 包：

1. 从最新版本下载 `gt7dashboard-windows.zip`。
2. 将 zip 解压到任意文件夹。
3. 双击 **`gt7dashboard.exe`**。
4. 弹出对话框要求输入您的 PlayStation IP 地址。
   - 在 PS5 上通过 **设置 → 网络 → 查看连接状态** 找到。
   - 留空以使用自动广播发现。
5. 仪表盘将在您的默认浏览器中自动打开。

> **提示：** 保存的圈速文件存储在 `gt7dashboard.exe` 旁边的 `data` 文件夹中。

## 如何运行

您需要安装可用的 Python。查看[此处](https://wiki.python.org/moin/BeginnersGuide/Download)获取安装说明。

* 如果您在 Windows 上
  * 需要 Microsoft Visual C++ 14.0 或更高版本。通过 "Microsoft C++ Build Tools" 获取：https://visualstudio.microsoft.com/visual-cpp-build-tools/

  * 双击运行 `run.ps1` 文件
* 如果您在 MacOS 上，运行 `run.command` 文件
* 如果您在 MacOS 上且使用 Homebrew 管理 Python3 安装，运行 `brew.command` 文件
* 如果您在 Linux 上，运行 `run.sh` 文件

`pip3` 或 `python3` 命令可能在您的操作系统上有所不同。尝试使用 `pip` 或 `python`。

## 高级用户运行方式

1. （一次性）`pip3 install -r requirements.txt` 安装 Python 依赖
   1. 在 Windows 上：需要 Microsoft Visual C++ 14.0 或更高版本。通过 "Microsoft C++ Build Tools" 获取：https://visualstudio.microsoft.com/visual-cpp-build-tools/

2. （可选，一次性）使用 `python3 helper/download_cars_csv.py` 下载赛车名称列表。没有此文件，赛车名称将仅显示为 `CAR-ID-123`。
3. 运行仪表盘
    - （Mac/Linux）`bokeh serve .`（在 `gt7dashboard` 文件夹内）
    - （Windows）`python -m bokeh serve .`（在 `gt7dashboard` 文件夹内）
4. （可选）使用自定义 IP 运行仪表盘
   - （Mac/Linux）`GT7_PLAYSTATION_IP=<主机 IP 地址> bokeh serve .`（在 `gt7dashboard` 文件夹内）
   - （Windows）`set GT7_PLAYSTATION_IP=<主机 IP 地址>` 然后 `python -m bokeh serve .`（在 `gt7dashboard` 文件夹内）

## 故障排除

如果遇到 `TimeoutError`，请检查您的防火墙。您可能需要允许 UDP 端口 33740 或 33739 的连接。

## Docker

提供 `Dockerfile` 和[预构建镜像](https://github.com/snipem/gt7dashboard/pkgs/container/gt7dashboard)。

```bash
# 从 Dockerfile 构建
docker build -t gt7dashboard /home/user/work/gt7dashboard

# 从此仓库拉取
docker pull ghcr.io/snipem/gt7dashboard:main

docker run -d --restart unless-stopped \
  --name gt7dashboard \
  --user 1002 \
  -p 5006:5006/tcp \
  -p 33740:33740/udp \
  -v /home/user/gt7data/:/usr/src/app/data \
  -e BOKEH_ALLOW_WS_ORIGIN=domain_of_server:5006 \
  -e GT7_PLAYSTATION_IP=<playstation ip> \
  -e TZ=Europe/Berlin \
  gt7dashboard
```

以下是 `docker-compose` 配置示例：

```yaml
    gt7dashboard:
        build:
            context: /home/user/work/gt7dashboard
        restart: unless-stopped
        container_name: gt7dashboard
        user: "1002"
        ports:
            - "5006:5006/tcp"
            - "33740:33740/udp"
        volumes:
            - /home/user/gt7data/:/usr/src/app/data
        environment:
            - BOKEH_ALLOW_WS_ORIGIN=domain_of_server:5006
            - GT7_PLAYSTATION_IP=<playstation ip>
            - TZ=Europe/Berlin
```

提示：您应该设置 `GT7_PLAYSTATION_IP` 环境变量，因为 Docker 容器默认不允许发送 UDP 广播。这是未设置 IP 时的默认行为。

## 圈速文件

如果您想编辑圈速文件，请使用 JSON 编辑器。例如 `cat ... | jq -c '.[0:4]' > ...` 将圈速文件缩短为前 4 圈。

## 贡献

请为所有新功能、计算等添加单元测试。

如果您想向手册添加内容，请编辑 `gt7dashboard/gt7help.py` 并使用 `make doc` 生成 `README.md`。

## 手册

### 标签页 '提升圈速'

#### 标题

![screenshot_header](README.assets/screenshot_header.png)

红色或绿色按钮反映与 Gran Turismo 7 的当前连接状态。即如果在最后一秒成功接收数据包，按钮将变为绿色。

接下来是对上一圈和参考圈的简要描述。参考圈可在右侧选择。

#### 圈速控制

![screenshot_header](README.assets/screenshot_lapcontrols.png)

'重置圈数' 按钮可重置所有圈数。如果您在会话中切换赛道或赛车，这将很有用。否则不同的赛道会在仪表板中混合。
'保存圈数' 将保存您记录的圈数到文件。之后您可以通过右侧的下拉列表加载圈数。

#### 时间/差值

![screenshot_header](README.assets/screenshot_timediff.png)

此图表显示上一圈与参考圈之间的相对时间差。
0 处实线以下的所有内容表示比参考圈慢。以上所有内容表示比参考圈快。

如果您在此图表中看到向上或向下的凸起，分别表示您在此位置较慢或较快。


#### 手动控制

![screenshot_header](README.assets/screenshot_manualcontrols.png)

'立即记录圈数' 将立即记录一圈，即使您尚未通过终点线。这有助于任务或驾照考试，其中测试的结束不一定与终点线相同。

'记录回放' 复选框允许您记录回放。请注意，计时赛前后背景中的活动也会被视为回放。即赛车在菜单背景中在赛道上行驶的情况。

在 '最佳圈' 下拉列表中，您可以选择参考圈。通常这指向当前会议的最佳圈。


#### 速度

![screenshot_header](README.assets/screenshot_speed.png)

所选圈数的总速度。此值取决于您的游戏设置为 km/h 或 mph。

#### 赛车线

![screenshot_header](README.assets/screenshot_raceline.png)

这是上一圈（蓝色）和参考圈（洋红色）的赛车线地图。放大查看详情。

如果您使用图表的索引编号快速确定赛道上的测量位置，此地图会很有帮助。

查看 '赛车线' 标签页获取更详细的赛车线。

#### 峰值和谷值

![screenshot_header](README.assets/screenshot_peaks_and_valleys.png)

所选圈数的速度峰值和谷值列表。我们假设峰值代表直道（S），谷值代表弯道（T）。用于比较上一圈和参考圈在赛道各个位置的速度差异。

#### 速度偏差 (Spd. Dev.)

![screenshot_header](README.assets/screenshot_speeddeviation.png)

显示最快圈速的速度偏差（基于最快圈 5.0% 时间差阈值内的圈速）。
回放圈速将被忽略。速度偏差是这些最快圈速之间的标准差。

在理想世界中拥有完美车手时，这条线将是平坦的。在实际情况中，您会得到一条近乎平坦的线，
在弯道和长直道处会有起伏。这正是即使您的最佳圈速也存在偏差的地方。

您可能会从查看此线起伏的赛道位置中获得一致性改进的洞察。

右侧列表显示了用于速度偏差分析的最佳圈速。


我从 [Your Data Driven Podcast](https://www.yourdatadriven.com/) 获得此图表的灵感。
在该播客的两期不同节目中，[Peter Krause](https://www.yourdatadriven.com/ep12-go-faster-now-with-motorsports-data-analytics-guru-peter-krause/) 和 [Ross Bentley](https://www.yourdatadriven.com/ep3-tips-for-racing-faster-with-ross-bentley/) 都提到了此可视化。
如果他们只能看一个图表，那就是同一年手最佳圈速中的偏差，通过学习已有好圈速之间的差异来提升车手表现。如果他们能做好一次，就能每次都做好。

#### 油门

![screenshot_header](README.assets/screenshot_throttle.png)

所选圈数的油门压力，范围为 0% 至 100%。

#### 横摆角速度/秒

![screenshot_header](README.assets/screenshot_yaw.png)

这是赛车的每秒横摆角速度。用于确定最大旋转点（MRP）。此时通常应开始加速。

[Suellio Almeida](https://suellioalmeida.ca) 向我介绍了此概念。详见[此处](https://www.youtube.com/watch?v=B92vFKKjyB0)。

#### 刹车

![screenshot_header](README.assets/screenshot_braking.png)

所选圈数的刹车压力，范围为 0% 至 100%。

#### 滑行

![screenshot_header](README.assets/screenshot_coasting.png)

所选圈数的滑行比例，范围为 0% 至 100%。滑行是指既未踩油门也未踩刹车的状态。

#### 档位

![screenshot_header](README.assets/screenshot_gear.png)

所选圈数的当前档位。

#### RPM

![screenshot_header](README.assets/screenshot_rpm.png)

所选圈数的当前 RPM。

#### 增压

![screenshot_header](README.assets/screenshot_boost.png)

所选圈数的当前增压值（x100 kPa）。

#### 轮胎速度/车速

![screenshot_header](README.assets/screenshot_tirespeed.png)

轮胎速度与车速之间的关系。如果轮胎速度快于车速，轮胎可能正在打滑。如果轮胎速度慢于车速，轮胎可能正在抱死。用于判断您的车辆控制。

#### 圈速表

![screenshot_header](README.assets/screenshot_timetable.png)

包含当前会话记录信息的表格。# 是游戏报告的圈数编号。如果您重新开始会话，可能存在多个相同编号的圈数。时间和差值自解释。信息列包含额外元数据，例如该圈是否为回放。
燃油消耗是当前圈消耗的燃油量。

接下来是圈速特征的基本指标。以 tick 为单位计数，即游戏报告状态的实例数。例如全油门 = 500 表示您在游戏发送遥测数据的 500 个实例中处于全油门状态。
全刹车、滑行和轮胎打滑同理。使用此功能轻松比较您的圈速。

您可以点击其中一个圈速将其添加到上方的图表中。如果重置视图或重新加载页面，这些圈速将被删除。

赛车列显示赛车名称。您需要下载 `db/cars.csv` 文件才能显示。


#### 燃油图

![screenshot_header](README.assets/screenshot_fuelmap.png)

此燃油图帮助确定赛车的燃油设置。游戏不报告当前燃油设置，因此此地图是相对的。
当前燃油设置始终为 0。如果您想更改为更稀的燃油设置，按剩余步数向下计数。例如：如果您在游戏中的燃油设置为 2，并希望设置为游戏的燃油设置 5，请在此地图中查看燃油等级 3。
它会为您提供关于新设置下剩余圈数和时间以及预估圈速时间差的粗略估计。

#### 调校信息

![screenshot_header](README.assets/screenshot_tuninginfo.png)

以下是一些可能对调校有用的信息。例如最高速度以及与赛道相关的最小车身高度。后者似乎在确定可能的车身高度时很有帮助。

### 标签页 '赛车线'

![screenshot_header](README.assets/screenshot_race_line.png)

这是上一圈（蓝色）和参考圈（洋红色）的赛车线地图。此图还显示速度峰值（▴）和谷值（▾）以及油门、刹车和滑行区域。

两条线中较细的是您的上一圈。参考线是较粗的半透明线。如果您想找出赛车线的差异，请查看参考圈赛车线和您赛车线的中间部分。您可以放大以发现差异并读取峰值和谷值的数值。
