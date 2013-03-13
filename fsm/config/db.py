import fsm.config.app as app_config

DB_PATH_DEV = "/Users/yliu/Projects/fsm/db/fsm.db"
DB_PATH_PROD = "/var/www/fsm/db/fsm.db"

def get_db_uri(config=None):
    if not config:
        config == app_config.APP_MODE
    db_path = DB_PATH_DEV
    if config == "production":
        db_path = DB_PATH_PROD
    return "sqlite:///%s" % (db_path)

def get_db_name(config=None):
    return "fsm"
