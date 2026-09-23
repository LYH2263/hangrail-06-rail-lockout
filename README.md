# HangRail

干洗挂衣杆：按衣长一维 First-Fit 上杆，取件释放，逾期扫描。

## 启动

```bash
docker compose up --build
```

| 服务 | 地址 |
| --- | --- |
| 前端 | http://localhost:4400 |
| API | http://localhost:9400 |
| API 文档 | http://localhost:9400/docs |
| Postgres | localhost:5445 |

健康检查：`GET http://localhost:9400/api/health`

## 页面

- `/stores` — 门店
- `/rails` — 挂杆
- `/orders` — 工单
- `/occupancy` — 占位图
- `/pickup` — 取件
- `/overdue` — 逾期

## 使用说明

1. 查看门店挂杆长度。
2. 工单上杆按衣长 First-Fit 占位。
3. 挂杆页可将挂杆标为「检修中」：封锁期间扫描挂杆直接跳过，工单不得新上该杆；全杆封锁时上杆提示检修语义；解除封锁后恢复可挂。
4. 检修封锁不影响取件，已在封锁杆上的衣物仍可取件释放占位。
5. 占位图为横向尺线；取件释放；逾期页扫描清退。

## 开发与测试

```bash
docker compose exec api pytest -q
```
