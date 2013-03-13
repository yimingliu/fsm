import fsm.models as model
import fsm.config.db as db_config

if __name__ == "__main__":
    db_uri = db_config.get_db_uri()
    model.init_model(db_uri)
    model.create_model()
