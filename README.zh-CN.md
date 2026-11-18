# surrealra1n-N71

面向 iPhone 6s（iPhone8,1 / N71AP）的 iOS 16.2（20C65）实验移植辅助工具，
基于 [pwnerblu 的 surrealra1n](https://github.com/pwnerblu/surrealra1n)。
当前版本可在主机提取未修改的供体系统镜像、生成独立的恢复副本并校验读回，
以及采集已配对设备的日志。不能构建或安装完整移植固件。

## 当前硬件状态

| 功能 | 状态 |
| --- | --- |
| 显示和触摸 | 历史实机通过 |
| Wi-Fi | 历史实机已关联并取得 IPv4 |
| 相机 | 部分可用，拍摄的照片无法保存到系统相册 |
| 振动及触觉反馈 | 不可用 |
| 蜂窝基带 | 不可用 |
| App Store 链接 | 据最新实机反馈不可用；其他 Apple 服务未测试 |
| Tethered boot | 原移植所需；本版不提供 |

Stage 18U 有原工程的实机启动记录。Stage 18W 仅有离线验证，尚未实机测试。
不适合作为日常系统，实机恢复可能失败并造成数据丢失。

[中文安装指南](docs/n71/INSTALL.zh-CN.md) · [详细硬件证据](docs/n71/STATUS.md#hardware-evidence) ·
[已知问题](docs/n71/KNOWN_ISSUES.md)
