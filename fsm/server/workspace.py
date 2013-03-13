from flask import abort, url_for, render_template, request
from flask.views import MethodView
import fsm.models as model

class WorkspaceAPI(MethodView):

    def get(self):
        return render_template("service_doc.tpl.xml", bundles=model.Bundle.get_all()), 200, {"Content-Type":"application/atomsvc+xml"}

    def post(self):
        collection_xml = request.data
        bundle = model.Bundle.from_atom(collection_xml)
        bundle.save()
        model.flush()
        try:
            bundle.short_name = bundle.gen_short_name()
            model.commit()
        except model.IntegrityError:
            bundle.short_name = bundle.gen_short_name(with_id=True)
            bundle.save()
            model.commit()
        return render_template("collection.tpl.xml", bundle=bundle), 201, {"Content-Type":"application/atomsvc+xml;type=collection", "Location":url_for("bundle", short_name=bundle.short_name, _external=True)}

        #return bundle.atom, 201, {"Location":url_for("bundle", short_name=bundle.short_name, _external=True)}


def register_api(app):
    workspace_view = WorkspaceAPI.as_view('workspace')
    app.add_url_rule('/service', view_func=workspace_view, methods=['GET',]) #defaults={'short_name': None})
    app.add_url_rule('/service', view_func=workspace_view, methods=['POST',])
    #app.add_url_rule('/service/<id>', view_func=bundle_view, methods=['GET', 'PUT', 'DELETE'])
