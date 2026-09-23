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
3. 占位图为横向尺线；取件释放；逾期页扫描清退。

## 挂杆检修封锁

挂杆可在「挂杆」页标为**检修封锁中**（或调用 `PATCH /api/rails/{id}/block`）：

- 封锁期间任何工单不得新上到该杆，自动上杆扫描挂杆列表时直接跳过（First-Fit 不选中）。
- 已在该杆上的衣物不受影响，仍可在取件页取件释放占位。
- 全部门店挂杆都被封锁时，上杆返回 409，提示含「检修封锁」语义。
- 封锁状态持久化，切换后再次进入挂杆页保持；解除封锁后该杆恢复可挂。

种子数据中 A 杆默认封锁，ready 工单只能尝试 B 杆。

## 开发与测试

```bash
docker compose exec api pytest -q
```
