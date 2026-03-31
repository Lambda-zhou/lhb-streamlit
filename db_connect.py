# 连接数据库
# 数据库连接测试
# !initctl status mysql
# !service mysql start
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy import create_engine, text
# from kaggle_secrets import UserSecretsClient


def db_connect():
    # user_secrets = UserSecretsClient()
    secret_value_0 = ""
    # user_secrets.get_secret("all_stock")
    
    
    # 创建数据库引擎
    db_user = 'all_stock'
    db_password = "SySZTdo7Ou5mmP0R"
    # secret_value_0  # 替换为您的密码
    db_host = 'mysql2.sqlpub.com'  # 如果您的数据库在其他主机上，请更改为相应的主机名或IP
    db_port = '3307'
    db_name = 'all_stock'  # 替换为您的数据库名
    
    # 使用 SQLAlchemy 创建数据库连接
    engine = create_engine(f'mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}')
    
    # 测试数据库连接
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        for row in result:
            print(row)

    return engine
