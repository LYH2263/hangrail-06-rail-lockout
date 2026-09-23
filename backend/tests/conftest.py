import os

# 测试进程独立：强制 SQLite 且不播种，必须在 app.config / app.database 导入前设置。
os.environ["DATABASE_URL"] = "sqlite+pysqlite:////tmp/hangrail_lifespan.db"
os.environ["SEED_ON_EMPTY"] = "false"
