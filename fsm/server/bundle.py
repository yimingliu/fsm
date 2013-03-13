from flask import abort, url_for, render_template, request, current_app
from flask.views import MethodView
import fsm.models as model

class BundleAPI(MethodView):

    def get(self, short_name):
        bundle = model.Bundle.get_by_short_name(short_name)
        if not bundle:
            return "", 404
        return render_template("bundle.tpl.xml", bundle=bundle), 200, {"Content-Type":"application/atom+xml", "ETag":bundle.etag_full_bundle}

    def post(self, short_name):
        if not request.headers["Content-Type"].startswith("application/atom+xml;type=entry"):
            return "", 415
        bundle = model.Bundle.get_by_short_name(short_name)
        if not bundle:
            return "", 404
        entry_xml = request.data
        entry = model.Entry.from_atom(entry_xml)
        if not entry:
            return "", 400
        entry.bundle = bundle
        entry.save()
        model.commit()
        return render_template("entry.tpl.xml", entry=entry), 201, {"Content-Type":"application/atom+xml;type=entry", "ETag":entry.etag, "Location":url_for("entry", e_id=entry.id, _external=True)}

    def put(self, short_name):
        bundle = model.Bundle.get_by_short_name(short_name)
        if not bundle:
            return "", 404
        collection_xml = request.data
        updated_bundle = model.Bundle.from_atom(collection_xml)
        dirty = bundle.update_from(updated_bundle)
        code = 304
        if dirty:
            model.commit()
            code = 200
        return render_template("collection.tpl.xml", bundle=bundle), code, {"Content-Type":"application/atomsvc+xml;type=collection", "ETag":bundle.etag}

    def delete(self, short_name):
        bundle = model.Bundle.get_by_short_name(short_name)
        if not bundle:
            return "", 404
        bundle.delete()
        model.commit()
        return "", 204


def register_api(app):
    bundle_view = BundleAPI.as_view('bundle')
    #app.add_url_rule('/bundles/', defaults={'short_name': None}, view_func=bundle_view, methods=['GET',])
    #app.add_url_rule('/bundles/', view_func=bundle_view, methods=['POST',])
    app.add_url_rule('/bundles/<short_name>', view_func=bundle_view,
                 methods=['GET', 'POST', 'PUT', 'DELETE'])

