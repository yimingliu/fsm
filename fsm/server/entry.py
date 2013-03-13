from flask import abort, url_for, render_template, request
from flask.views import MethodView
import fsm.models as model
import logging

class EntryAPI(MethodView):

    def get(self, e_id):
        entry = model.Entry.get_by_id(e_id)
        if not entry:
            return "", 404
        return render_template("entry.tpl.xml", entry=entry), 200, {"Content-Type":"application/atom+xml;type=entry", "ETag":entry.etag}

    def put(self, e_id):
        entry = model.Entry.get_by_id(e_id)
        if not entry:
            return "", 404
        entry_xml = request.data
        updated_entry = model.Entry.from_atom(entry_xml)
        dirty = entry.update_from(updated_entry)
        code = 304
        if dirty:
            model.commit()
            code = 200
        return render_template("entry.tpl.xml", entry=entry), code, {"Content-Type":"application/atom+xml;type=entry", "ETag":entry.etag}


    def delete(self, e_id):
        entry = model.Entry.get_by_id(e_id)
        if not entry:
            return "", 404
        entry.delete()
        model.commit()
        return "", 204

def register_api(app):
    entry_view = EntryAPI.as_view('entry')
    #app.add_url_rule('/entries', view_func=workspace_view, methods=['GET',]) #defaults={'short_name': None})
    #app.add_url_rule('/entries', view_func=workspace_view, methods=['POST',])
    app.add_url_rule('/entries/<e_id>', view_func=entry_view, methods=['GET', 'PUT', 'DELETE'])
