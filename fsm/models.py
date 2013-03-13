#!/usr/bin/python

import decimal, re, datetime, hashlib, os.path, dateutil.parser
import urllib, urllib2, httplib
from sqlalchemy import Table, Column, Integer, DateTime, Date, ForeignKey, create_engine, UniqueConstraint#,MetaData 
from sqlalchemy import orm, types, func
from sqlalchemy.exc import InvalidRequestError, IntegrityError
from sqlalchemy.schema import DDL, FetchedValue, DefaultClause
from sqlalchemy.sql.expression import and_, literal_column, or_, text
from sqlalchemy.sql.functions import sum as sum_, count as count_
from sqlalchemy.ext.associationproxy import association_proxy

#from sqlalchemy.util import classproperty
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

import logging
import fsm.config.app as app_config
import fsm.config.meta as meta
from fsm.utils import first_value, etag_hash

import lxml.etree as et 
import slugify

NSMAP = {"fsm":"http://dret.net/fsm/1.0",
         "app":"http://www.w3.org/2007/app",
         "atom":"http://www.w3.org/2005/Atom", # default namespace
         "georss":"http://www.georss.org/georss"
        }

#shortcuts
FSM_NS = "{%s}" % NSMAP["fsm"]
ATOMPUB_NS = "{%s}" % NSMAP["app"]
ATOM_NS = "{%s}" % NSMAP["atom"]
GEORSS_NS = "{%s}" % NSMAP["georss"]


def init_model(db_uri):
    engine = create_engine(db_uri, echo=app_config.DEBUG_ECHO)
    meta.session_maker = orm.sessionmaker(autoflush=True, autocommit=False, bind=engine)
    meta.engine = engine
    meta.Session = orm.scoped_session(meta.session_maker)
    meta.Base.metadata.bind = engine#create_engine(db_uri, pool_size = 100, pool_recycle=3600)

def create_model():
    return meta.Base.metadata.create_all()

def rollback(session=None):
    if not session:
        session = meta.Session
    session.rollback()

def commit(session=None):
    if not session:
        session = meta.Session
    try:
        session.commit()
    except Exception, e:
        session.rollback()
        raise e
    
def flush(session=None):
    if not session:
        session = meta.Session
    try:
        session.flush()
    except Exception, e:
        session.rollback()
        raise e


class Entity(object):
    __updateable_attrs__ = []
    
    @classmethod
    def get_by_id(cls, id, options=None, session=None):
        if not session:
            session=meta.Session
        try:
            q = session.query(cls)
            if options:
                q = q.options(*options)
            entity = q.filter(cls.id == id).one()
            return entity
        except NoResultFound:
            return None
    
    @classmethod
    def get_all_by_ids(cls, ids, options=None, session=None):
        if not session:
            session = meta.Session
        if not ids:
            return []
        q = session.query(cls)
        if options:
            q = q.options(*options)
        q = q.filter(cls.id.in_(ids))
        ids = [str(int(id)) for id in ids]
        ids = ", ".join(ids)
        # TODO: this is probably highly unsafe if IDs cannot be trusted
        #q = q.order_by(cls.id)
        q = q.order_by("FIELD (%s.%s, %s)" % (cls.__tablename__, cls.id.__clause_element__().name, ids))
        return q.all()

    @classmethod
    def get_all_by_ids_starting_with(cls, id, fbid=None, options=None, session=None):
        if not session:
            session = meta.Session
        q = session.query(cls)
        if options:
            q = q.options(*options)
        if fbid:
            entity = cls.get_by_fbid(fbid)
            id = entity.id
        q = q.filter(cls.id >= id)
        q = q.order_by(cls.id.asc())
        return q.all()


    def update_from(self, other_entity):
        dirty = False
        for attr in self.__updateable_attrs__:
            if other_entity.__getattribute__(attr) and self.__getattribute__(attr) != other_entity.__getattribute__(attr):
                self.__setattr__(attr, other_entity.__getattribute__(attr))
                if not dirty:
                    dirty = True
        return dirty
        
    @property
    def entity_key(self):
        return self.id
    
#    @classmethod
#    def get_by_uuid(cls, uuid, options=None):
#        try:
#            q = meta.Session.query(cls)
#            if options:
#                q = q.options(*options)
#            entity = q.filter(cls.uuid == uuid).one()
#            return entity
#        except NoResultFound:
#            return None
        
    @classmethod
    def get_all(cls, options=None, session=None):
        if not session:
            session = meta.Session
        q = session.query(cls)
        if options:
            q = q.options(*options)
        return q.all()

    def to_dict(self, extra_vals=None, mode="basic", base_collection_name="__basic_attrs__", exclude_keys=None):
        '''Converts Entity object graph into nested dictionaries for JSON processing using object introspection
            mode: selects between full/min/basic attrs.  Defaults to basic_attrs if the mode does not exist
            exclude_keys: keys that match this string are excluded from all objects in the object graph
        '''
        #d = {'entity_type':self.__class__.__name__}
        collection_name = base_collection_name
        if mode == "full":
            collection_name = "__full_attrs__"
        elif mode == "min":
            collection_name = "__min_attrs__"
        d = {}
        exclude_keys = {} if not exclude_keys else exclude_keys
        collection = None
        if collection_name in self.__class__.__dict__:
            collection = self.__class__.__dict__.get(collection_name)
        elif base_collection_name in self.__class__.__dict__:
            collection = self.__class__.__dict__.get(base_collection_name)
        else:
            collection = self.__dict__
            
        for k in collection:
            if not (k.startswith(u"_") or (k in exclude_keys)):
                v = self.__getattribute__(k)
                if isinstance(v, Entity):
                    v = v.to_dict(mode=mode, exclude_keys=exclude_keys)
                if isinstance(v, list):
                    v = [i.to_dict() for i in v]
                if isinstance(v, dict):
                    for v_key in v:
                        v[v_key] = v[v_key].to_dict() if isinstance(v[v_key], Entity) else v[v_key]
                d[k] = v
        if extra_vals:
            d.update(extra_vals)
        return d
    
    def to_json(self, extra_vals=None, mode="basic", exclude_keys=None):
        return utils.json_serialize(self.to_dict(extra_vals=extra_vals, mode=mode, exclude_keys=exclude_keys))
    
    def save(self, session=None):
        if not session:
            session = meta.Session
        session.add(self)


    def refresh(self, session=None):        
        if not session:
            session = meta.Session
        session.refresh(self)
    
    def delete(self, session=None):
        if not session:
            session = meta.Session
        meta.Session.delete(self)
    

class APIError(dict):
    
    def __init__(self, code, message, error_dict=None):
        dict.__init__(self)
        self['code'] = code
        self['message'] = message
        self['errors'] = error_dict
    
    def to_json(self):
        return utils.json_serialize(self)
        

ENTRY_TYPE_ENTRY = "service_entry"
ENTRY_TYPE_ENTRY_URI = "http://dret.net/fsm/1.0/service-entry"
ENTRY_TYPE_BUNDLE_REF = "bundle"
ENTRY_TYPE_BUNDLE_URI = "http://dret.net/fsm/1.0/bundle"


class Entry(meta.Base, Entity):
    __tablename__ = 'entries'
    __updateable_attrs__ = ["name", "client_id", "uri", "desc", "query"]
    id = Column(types.Integer, primary_key=True)
    e_type = Column(types.Unicode(64), nullable=False, index=True)
    client_id = Column(types.Unicode(255), nullable=False, index=True, server_default=u'')
    name = Column(types.Unicode(255), nullable=False, index=True, server_default=u'')
    uri = Column(types.Unicode(1024), nullable=False, index=True)
    query = Column(types.Unicode(2048), nullable=True, index=True)
    desc = Column(types.UnicodeText, nullable=True, index=True)
    created_at = Column(DateTime(), nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime(), nullable=False, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, index=True)
    bundle_id = Column(types.BigInteger, ForeignKey('bundles.id', onupdate="CASCADE", ondelete="CASCADE"), nullable=False, index=True)

    __mapper_args__ = {
        'polymorphic_on':e_type
    }
    
    @property
    def client_name(self):
        if self.client_id:
            return self.client_id
        else:
            return "fsm_server"
    
    @property
    def atom_id(self):
        return u"tag:fsm:%s,%s:%s" % (self.client_name, self.created_at.date().isoformat(), self.uri)
    
    @classmethod
    def parse_atom_text(cls, entry_xml):
        entry_element = et.XML(entry_xml)
        e_type = first_value(entry_element.xpath("/atom:entry/atom:link[@rel='profile']/@href", namespaces=NSMAP))
        uri = first_value(entry_element.xpath("/atom:entry/atom:link[@rel='alternate']/@href", namespaces=NSMAP))
        title = first_value(entry_element.xpath("/atom:entry/atom:title/text()", namespaces=NSMAP))
        desc = first_value(entry_element.xpath("/atom:entry/atom:summary/text()", namespaces=NSMAP))
        query = first_value(entry_element.xpath("/atom:entry/fsm:query/text()", namespaces=NSMAP))
        return e_type, uri, title, desc, query
    
    @classmethod
    def from_atom(cls, entry_xml):
        e_type, uri, title, desc, query = cls.parse_atom_text(entry_xml)
        entry_class = None
        if e_type == ENTRY_TYPE_ENTRY_URI:
            entry_class = ServiceEntry
        elif e_type == ENTRY_TYPE_BUNDLE_URI:
            entry_class = BundleEntry
        else:
            return None
        if title and uri:
            entry = entry_class(name=title, uri=uri, query=query, desc=desc)
            return entry
        else:
            return None
            
    @property
    def etag(self):
        return etag_hash(self.updated_at.isoformat())
        
        
class ServiceEntry(Entry):
    __mapper_args__ = {'polymorphic_identity': ENTRY_TYPE_ENTRY_URI}
    
class BundleEntry(Entry):
    __mapper_args__ = {'polymorphic_identity': ENTRY_TYPE_BUNDLE_URI}
    
class Bundle(meta.Base, Entity):
    __tablename__ = 'bundles'
    __updateable_attrs__ = ["name", "min_lat", "min_lon", "max_lat", "max_lon"]
    id = Column(types.Integer, primary_key=True)
    client_id = Column(types.Unicode(255), nullable=False, index=True, server_default=u'')
    name = Column(types.Unicode(255), nullable=False, index=True, server_default=u'')
    short_name = Column(types.Unicode(128), nullable=True, unique=True, index=True)
    desc = Column(types.UnicodeText, nullable=True, index=True)
    min_lat = Column(types.Numeric(16, 12), nullable=True, index=True) # spatial extension for rectangular views
    min_lon = Column(types.Numeric(16, 12), nullable=True, index=True)
    max_lat = Column(types.Numeric(16, 12), nullable=True, index=True)
    max_lon = Column(types.Numeric(16, 12), nullable=True, index=True)
    created_at = Column(DateTime(), nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime(), nullable=False, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, index=True)
    entries = orm.relationship("Entry", cascade="all,delete", backref=orm.backref("bundle", uselist=False))


    @classmethod
    def get_by_short_name(cls, short_name, options=None, session=None):
        if not session:
            session=meta.Session
        try:
            q = session.query(cls)
            if options:
                q = q.options(*options)
            entity = q.filter(cls.short_name == short_name).one()
            return entity
        except NoResultFound:
            return None

    @property
    def client_name(self):
        if self.client_id:
            return self.client_id
        else:
            return "fsm_server"
            
    @property
    def etag(self):
        return etag_hash(self.updated_at.isoformat())

    @property
    def etag_full_bundle(self):
        bundle_state = ""
        last_entry = self.get_last_updated_entry()
        if last_entry:
            bundle_state = " " + last_entry.updated_at.isoformat()
        return etag_hash(self.updated_at.isoformat() + bundle_state) 

    @property
    def atom_id(self):
        return u"tag:fsm:%s,%s:%s" % (self.client_name, self.created_at.date().isoformat(), self.short_name)
    
    @classmethod
    def from_atom(cls, collection_xml):
        title, geobox = cls.parse_atom_text(collection_xml)
        bundle = Bundle(name=title)
        if geobox and len(geobox) == 4:
            bundle.min_lat, bundle.min_lon, bundle.max_lat, bundle.max_lon = geobox
        return bundle
    
    def gen_short_name(self, with_id=False):
        short_name = slugify.slugify(self.name, max_length=32)
        if with_id:
            short_name += "-" + str(self.id)
        return short_name
        
    @classmethod
    def parse_atom_text(cls, collection_xml):
        collection_element = et.XML(collection_xml)
        title = first_value(collection_element.xpath("/app:collection/atom:title/text()", namespaces=NSMAP))
        geobox = first_value(collection_element.xpath("/app:collection/georss:box/text()", namespaces=NSMAP))
        if geobox:
            geobox = [decimal.Decimal(v) for v in geobox.split(" ")]
        return title, geobox
        
    def get_last_updated_entry(self, options=None, session=None):
        if not session:
            session=meta.Session
        try:
            q = session.query(Entry).join(Entry.bundle)
            if options:
                q = q.options(*options)
            q = q.filter(self.__class__.id==self.id)
            entity = q.order_by(Entry.updated_at.desc()).first()
            return entity
        except NoResultFound:
            return None
