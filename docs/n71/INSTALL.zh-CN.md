# iPhone 6s — iOS 16.2 Port（实验）

基于 pwnerblu 的 surrealra1n，保留 Apache-2.0 许可证、NOTICE 和作者署名。
这是非官方 Fork。N71 文件检查需要 Bash 和 Python 3.9 或更新版本。
实机身份查询另需将 `irecovery` 安装到 PATH。

| 用途 | 设备 | 版本 |
| --- | --- | --- |
| 目标 | iPhone 6s / iPhone8,1 / N71AP，A9 CPID 0x8000，BDID 0x04 | iOS 16.2 / 20C65 实验移植 |
| 系统供体 | iPad 5 Wi-Fi，iPad6,11 / j71sap | iPadOS 16.2 / 20C65 |
| 原生硬件供体 | iPhone 6s / N71AP | iOS 15.6 / 19G71 |

用户自备两份 IPSW。从 checkout 运行原版 shell 入口：

```sh
./surrealra1n.sh --n71-port --profile 18u \
  --donor-ipsw /你的目录/ipad-16.2.ipsw \
  --native-ipsw /你的目录/iphone6s-15.6.ipsw
```

- 设备已在 DFU 或 Recovery 时，添加 `--probe` 作只读身份查询。
  也可用 `--device-info 文件` 验证已保存的查询结果。
- 用 `--candidate-dir 目录` 校验相应 Profile 的 `offline-candidate`
  收据与两份缓存。用 `--recovery-dir 目录` 校验 Stage 18U 独立恢复备份。
  恢复备份目录须含 `n71-stage18w-recovery-export/v1` 格式的收据。
- `--profile 18w` 是独立的实验配置，**Untested on device / Experimental**。
  18U 在原移植实验机上启动过，基带未就绪。两种 Profile 的缓存不会混用。
- 程序逐项检查 IPSW 的版本、板型和所需成员，并输出 JSON。它不验证
  IPSW 的发布者签名或完整数据载荷。恢复文件通过校验也无法证明实机恢复可用。

## 生成主机验收包、检查恢复资料和采集日志

- 用 `prepare-donors --donor-ipsw 文件 --native-ipsw 文件 --output 新目录`
  提取两份未改动的系统 DMG。需约 10 GB 空间，使用 `verify-donors 目录`
  复核产物。这两份镜像是共享供体材料，不能作为刷机包。

- 在输入参数前添加 `build-bundle`，并用 `--output` 指定新的 ZIP 文件。
  产物包含两份完整 IPSW 的 SHA-256 与大小、Profile 及检查收据。
  用 `./surrealra1n.sh --n71-port verify-bundle 验收包.zip` 验证归档摘要。
- `./surrealra1n.sh --n71-port recovery-check 备份目录 --probe` 会把
  实机 ECID 与备份收据比对。也可用 `--device-info` 读取已保存的查询。
  省略设备参数时只验证文件，不检查实机身份。
- `copy-recovery 备份目录 --device-info 查询文件 --output 新目录` 核对 ECID
  后生成独立的三份本地恢复副本并逐份读回。也可用 `--probe` 查实机身份。
  任一步失败会清理未完成的输出；不会写手机。
- `./surrealra1n.sh --n71-port collect-logs --output 私人输出目录 --seconds 10`
  对已配对且正在运行 iOS 的 N71AP 采集进程列表、syslog 和 CommCenter
  崩溃副本。需安装 libimobiledevice，且输出目录尚不存在。不删除手机上的
  原始崩溃报告。部分失败时保留已采集内容并返回非零。

IPSW、缓存、个人备份、密钥、配对记录和设备日志应保存在仓库之外。
当前模式支持输入、设备身份及外部产物验证、主机验收包与设备日志。构建移植组件、设备刷写、
实机恢复和 tethered boot 不可用。底层移植依赖 tethered boot 和
Surreal16 系统卷；基带不可用，不适合日常使用。实机恢复可能失败并造成数据丢失。
最新实机反馈是 App Store 链接不可用、振动不可用、相机部分可用但照片无法保存到
系统相册。其他 Apple 服务未测试。前后摄、录像与慢动作的证据分别见功能状态。
详见[英文说明](INSTALL.md)、[功能状态](STATUS.md)和[已知问题](KNOWN_ISSUES.md)。
