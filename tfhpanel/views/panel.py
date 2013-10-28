from pyramid.response import Response
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPOk, HTTPSeeOther, HTTPNotFound, HTTPBadRequest, HTTPInternalServerError
from pyramid.renderers import render_to_response
from collections import namedtuple
from sqlalchemy.orm import joinedload

from tfhnode.models import *
from tfhpanel.forms import *

import logging
log = logging.getLogger(__name__)

from pyramid.i18n import TranslationStringFactory
_ = TranslationStringFactory('pyramid')

class PanelView(object):
    models = None
    formclass = None
    parent = None
    subs = []

    @property
    @classmethod
    def short_name(cls):
        return cls.__name__.lower()

    def __init__(self, request):
        self.request = request
        self.filters = {}
        for k, v in self.request.matchdict.items():
            self.filters[k] = int(v, 16) if v else None
        act = self.request.route_url(self.request.matched_route.name,
            **self.request.matchdict)
        self.form = self.formclass(self.request, action=act)
    
    def find_required_uid(self):
        view = self
        while view:
            if view.model == User:
                return view.model.id
            if hasattr(view.model, 'userid'):
                return view.model.userid
            view = view.parent

    def filter_query(self, q):
        if not self.request.has_permission('panel_admin'):
            column = self.find_required_uid()
            if not column:
                # Cannot determine column, assume no one owns it.
                raise HTTPForbidden()
            q = q.filter(column == self.request.user.id)

        for k, v in self.filters.items():
            if v is None or v == '':
                # Do not put a break here, because of the dict's random order.
                # debugging time lost here: timedelta(minutes=30)
                continue
            column = getattr(self.model, k)
            q = q.filter(column == v)
        return q
    
    def is_model_object(self, o=None):
        if not o:
            return True
        try:
            if o.short_name and o.id:
                return True
        except Exception as e:
            return False

    def make_url(self, o=None):
        if o:
            url = '/%s/%d' % (o.short_name, o.id)
        else:
            url = '/%s/' % self.model.short_name
        parent = self.parent
        while parent:
            if o:
                parent_name = parent.model.short_name
                id = getattr(o, parent_name+'id')
                url = '/%s/%d'%(parent_name, id) + url
            else:
                parent_name = parent.model.short_name
                if not parent_name+'id' in self.filters:
                    raise HTTPInternalServerError()
                id = self.filters[parent_name+'id']
                url = '/%s/%d'%(parent_name, id) + url

            parent = parent.parent
        return url

    def render(self, template, v):
        v['view'] = self
        v['form'] = self.form
        return render_to_response('panel/'+template,
            v, request=self.request)
    
    def get_index_data(self):
        objects = DBSession.query(self.model).options(joinedload('*'))
        objects = self.filter_query(objects).order_by(self.model.id).all()
        return dict(objects=objects)

    def get_index(self):
        return self.render('list.mako', self.get_index_data())

    def get_data(self):
        object = DBSession.query(self.model).options(joinedload('*'))
        object = self.filter_query(object).first()
        if not object:
            raise HTTPNotFound(comment='object not found')
        return dict(object=object)

    def get(self):
        return self.render('view.mako', self.get_data())
    
    def post_data(self):
        object = DBSession.query(self.model).options(joinedload('*'))
        object = self.filter_query(object).first()
        if not object:
            raise HTTPNotFound(comment='object not found')
        
        errors = self.form.validate(self.request.POST)
        if errors:
            for error in errors:
                self.request.session.flash(('error', error))
        else:
            self.form.save(object)
            DBSession.commit()
            self.request.session.flash(('info', _('Saved!')))
        return dict(object=object)

    def post(self):
        # TODO: instead, send a See Other to get(). same in post_index()
        return self.render('view.mako', self.post_data())

    def post_index_data(self):
        object = self.model()
        # apply filter_query stuff
        if hasattr(object, 'userid'):
            object.userid = self.request.user.id
        for k, v in self.filters.items():
            if v is None or v == '':
                continue
            setattr(object, k, v)

        errors = self.form.validate(self.request.POST)
        if errors:
            for error in errors:
                self.request.session.flash(('error', error))
        else:
            self.form.save(object)
            DBSession.add(object)
            DBSession.commit()
            self.request.session.flash(('info', _('Saved!')))
        return dict(object=object)

    def post_index(self):
        return self.render('view.mako', self.post_index_data())


    def __call__(self):
        get = self.request.method == 'GET'
        post = self.request.method == 'POST'
        index = not self.request.matchdict['id']

        return \
            self.get_index() if get & index else \
            self.get() if get else \
            self.post_index() if post & index else \
            self.post() if post else \
            HTTPBadRequest()

def filter_owned_domain(field, query, request):
    return query.filter_by(userid = request.user.id)


class VHostForm(Form):
    name = TextField(_('Name'))
    catchall = TextField(_('Fallback URI'))
    autoindex = CheckboxField(_('Autoindex'))
    domains = OneToManyField(_('Domains'), fm=Domain,
        qf=[filter_owned_domain])

@view_config(route_name='p_vhost',  permission='vhost_panel')
class VHostPanel(PanelView):
    model = VHost
    formclass = VHostForm
    list_fields = ('name', 'user')


class DomainForm(Form):
    domain = TextField(_('Name'))
    hostedns = CheckboxField(_('Hosted NS'))
    vhost = ForeignField(_('VHost'), fm=VHost)
    public = CheckboxField(_('Public'))
    verified = CheckboxField(_('Verified'), readonly=True)

@view_config(route_name='p_domain',  permission='domain_panel')
class DomainPanel(PanelView):
    model = Domain
    formclass = DomainForm
    list_fields = ('user', 'domain', 'vhost', 'hostedns', 'public', 'verified')
    
    def get_data(self):
        d = super().get_data()
        d['left_template'] = 'domain/view_status.mako'
        return d

class MailboxForm(Form):
    domain = ForeignField(_('Domain'), fm=Domain)
    local_part = TextField(_('Local part'))
    redirect = TextField(_('Redirect (if any)'))
    password = PasswordField(_('Password (required to accept mails)'))

@view_config(route_name='p_mailbox',  permission='mail_panel')
class MailboxPanel(PanelView):
    model = Mailbox
    formclass = MailboxForm
    list_fields = ('user', 'address')


class VHostRewriteForm(Form):
    regexp = TextField(_('RegExp'))
    dest = TextField(_('Rewrite to'))
    redirect_temp = CheckboxField(_('Temporary redirect (302)'))
    redirect_perm = CheckboxField(_('Permanent redirect (301)'))
    last = CheckboxField(_('Last'))

@view_config(route_name='p_vhostrewrite',  permission='vhost_panel')
class VHostRewritePanel(PanelView):
    model = VHostRewrite
    formclass = VHostRewriteForm
    parent = VHostPanel
    list_fields = ('regexp', 'dest')


class VHostACLForm(Form):
    title = TextField(_('Title'))
    regexp = TextField(_('RegExp'))
    passwd = TextField(_('passwd file'))

@view_config(route_name='p_vhostacl',  permission='vhost_panel')
class VHostACLPanel(PanelView):
    model = VHostACL
    formclass = VHostACLForm
    parent = VHostPanel
    list_fields = ('title', 'regexp')


class VHostErrorPageForm(Form):
    code = IntegerField(_('Error code'))
    path = TextField(_('Page URI'))

@view_config(route_name='p_vhostep',  permission='vhost_panel')
class VHostErrorPagePanel(PanelView):
    model = VHostErrorPage
    formclass = VHostErrorPageForm
    parent = VHostPanel
    list_fields = ('code', 'page')


root_panels = []
root_panels_dict = {}

for pv in PanelView.__subclasses__():
    if pv.parent and not pv.parent.subs:
        pv.parent.subs = []
    if pv.parent and not pv in pv.parent.subs:
        pv.parent.subs.append(pv)
    else:
        root_panels.append(pv)
        root_panels_dict[str(pv.model.short_name)] = pv
    del pv

