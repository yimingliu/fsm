from flask import Flask
import fsm.server.bundle as bundle_api
import fsm.server.workspace as workspace_api
import fsm.server.entry as entry_api
import fsm.config.app as app_config
import fsm.config.db as db_config
import fsm.models as model

model.init_model(db_config.get_db_uri())
app = Flask(__name__)
#app.register_blueprint(bundle_controller, url_prefix="/bundles")
#app.register_blueprint(workspace_controller)

from flask.views import MethodView
import flask

bundle_api.register_api(app)
workspace_api.register_api(app)
entry_api.register_api(app)
                 
@app.route("/")
def root():
    return "Not in Kansas anymore, Toto"

if __name__=="__main__":
    app.run(debug=True)
