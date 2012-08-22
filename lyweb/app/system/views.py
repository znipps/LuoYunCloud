# coding: utf-8

import logging, struct, socket, re, os, json
import ConfigParser

from lycustom import LyRequestHandler
from tornado.web import authenticated, asynchronous

from sqlalchemy.sql.expression import asc, desc

from app.system.models import LuoYunConfig
from app.system.forms import BaseinfoForm, DBForm, \
    CLCForm, NameserversForm, NetworkPoolForm, DomainForm, \
    NginxForm, RegistrationProtocolForm


from lycustom import has_permission

import settings



class Index(LyRequestHandler):

    @has_permission('admin')
    def get(self):
        self.render('system/index.html')



class DBEdit(LyRequestHandler):

    @has_permission('admin')
    def prepare(self):

        self.cf = ConfigParser.ConfigParser()
        self.cf.read( settings.LUOYUN_CONFIG_PATH )
        if not self.cf.has_section('db'):
            self.cf.add_section('db')

    def get(self):

        cf = self.cf

        form = DBForm()
        try:
            form.dbname.data = cf.get('db', 'db_name')
            form.dbuser.data = cf.get('db', 'db_user')
            form.dbpass.data = cf.get('db', 'db_password')
            form.dbhost.data = cf.get('db', 'db_host')
            form.dbtype.data = cf.get('db', 'db_type')
        except:
            pass

        self.render('system/db_edit.html', form=form)


    def post(self):

        cf = self.cf
        saved = None

        form = DBForm( self.request.arguments )
        if form.validate():
            cf.set('db', 'db_host', form.dbhost.data)
            cf.set('db', 'db_type', form.dbtype.data)
            cf.set('db', 'db_name', form.dbname.data)
            cf.set('db', 'db_user', form.dbuser.data)
            cf.set('db', 'db_password', form.dbpass.data)
            cf.write(open(settings.LUOYUN_CONFIG_PATH, 'w'))
            saved = True
            # TODO: Important ! db settings should check for connect !

        self.render('system/db_edit.html', form=form, saved = saved)



class CLCEdit(LyRequestHandler):

    @has_permission('admin')
    def prepare(self):

        self.cf = ConfigParser.ConfigParser()
        self.cf.read( settings.LUOYUN_CONFIG_PATH )
        if not self.cf.has_section('clc'):
            self.cf.add_section('clc')

    def get(self):

        cf = self.cf

        form = CLCForm()
        try:
            form.ip.data = cf.get('clc', 'clc_ip')
            form.port.data = cf.get('clc', 'clc_port')
        except:
            pass

        self.render('system/clc_edit.html', form=form)


    def post(self):

        cf = self.cf
        saved = None

        form = CLCForm( self.request.arguments )
        if form.validate():
            cf.set('clc', 'clc_ip', form.ip.data)
            cf.set('clc', 'clc_port', form.port.data)
            cf.write(open(settings.LUOYUN_CONFIG_PATH, 'w'))
            saved = True

        self.render('system/clc_edit.html', form=form, saved = saved)



class BaseinfoEdit(LyRequestHandler):

    @has_permission('admin')
    def prepare(self):

        self.cf = ConfigParser.ConfigParser()
        self.cf.read( settings.LUOYUN_CONFIG_PATH )
        if not self.cf.has_section('base'):
            self.cf.add_section('base')


    def get(self):

        cf = self.cf

        form = BaseinfoForm()
        form.app_dir.data = settings.appliance_top_dir
        form.app_url.data = settings.appliance_top_url
        form.admin_email.data = settings.ADMIN_EMAIL

        self.render('system/baseinfo_edit.html', form=form)


    def post(self):

        cf = self.cf
        saved = None

        form = BaseinfoForm( self.request.arguments )
        if form.validate():

            cf.set('base', 'appliance_top_dir', form.app_dir.data)
            cf.set('base', 'appliance_top_url', form.app_url.data)
            cf.set('base', 'admin_email', form.admin_email.data)
            cf.write(open(settings.LUOYUN_CONFIG_PATH, 'w'))
            saved = True

        self.render('system/baseinfo_edit.html', form=form, saved=saved)




class NameserversEdit(LyRequestHandler):

    @has_permission('admin')
    def prepare(self):

        self.nameservers = self.db2.query(LuoYunConfig).filter_by( key = 'nameservers' ).first()


    def get(self):

        form = NameserversForm()
        if self.nameservers:
            form.nameservers.data = self.nameservers.value

        self.render('system/nameservers_edit.html',
                    form = form)



    def post(self):

        saved = None
        form = NameserversForm( self.request.arguments )
        if form.validate():

            nameservers = form.nameservers.data

            if self.nameservers:
                self.nameservers.value = nameservers
            else:
                c = LuoYunConfig('nameservers', nameservers)
                self.db2.add( c )

            self.db2.commit()
            saved = True

        self.render('system/nameservers_edit.html',
                    form = form, saved = saved)



class NetworkPool(LyRequestHandler):

    @has_permission('admin')
    def get(self):
        d = { 'title': _('Network pool of LuoYun'),
              'NETWORK_POOL': settings.NETWORK_POOL[0], }

        if not d['NETWORK_POOL']:
            url = self.reverse_url('system:networkpool:edit')
            if self.get_argument('ajax', None):
                url += '?ajax=1'
            return self.redirect( url )

        from app.system.models import IpAssign
        def get_ipassign(ip):
            return self.db2.query(IpAssign).filter_by( ip = ip ).first()
            
        d['get_ipassign'] = get_ipassign

        self.render('system/networkpool.html', **d)



class NetworkPoolEdit(LyRequestHandler):

    @has_permission('admin')
    def prepare(self):

        self.networkpool = self.db2.query(LuoYunConfig).filter_by( key = 'networkpool' ).first()
        self.nameservers = self.db2.query(LuoYunConfig).filter_by( key = 'nameservers' ).first()


    def get(self):

        form = NetworkPoolForm()
        if self.networkpool:
            networkpool = json.loads(self.networkpool.value)
            if len(networkpool) > 0:
                networkpool = networkpool[0]
                form.start.data = networkpool['start']
                form.end.data = networkpool['end']
                form.netmask.data = networkpool['netmask']
                form.gateway.data = networkpool['gateway']
                if networkpool.has_key('nameservers'):
                    form.nameservers.data = networkpool['nameservers']
                else:
                    nameservers = self.db2.query(LuoYunConfig).filter_by( key = 'nameservers' ).first()
                    if nameservers:
                        form.nameservers.data = nameservers
                if networkpool.has_key('exclude_ips'):
                    form.exclude_ips.data = networkpool['exclude_ips']

        self.render('system/networkpool_edit.html',
                    form = form)



    def post(self):

        saved = None
        form = NetworkPoolForm( self.request.arguments )
        if form.validate():

            networkpool = {
                'start': form.start.data,
                'end': form.end.data,
                'netmask': form.netmask.data,
                'gateway': form.gateway.data,
                'nameservers': form.nameservers.data,
                'exclude_ips': form.exclude_ips.data,
                }


            nameservers = form.nameservers.data

            if self.nameservers:
                #self.nameservers.value = nameservers
                pass
            else:
                c = LuoYunConfig('nameservers', nameservers)
                self.db2.add( c )

            networkpool = json.dumps( [networkpool, ] )
            if self.networkpool:
                self.networkpool.value = networkpool
            else:
                c = LuoYunConfig('networkpool', networkpool)
                self.db2.add(c)

            self.db2.commit()
            from tool.network import set_network_pool
            # set settings.NETWORK_POOL
            set_network_pool(self.db2)
            saved = True
            # TODO: redirect to ?
            url = self.reverse_url('system:networkpool')
            self.redirect( url )

        self.render('system/networkpool_edit.html',
                    form = form, saved = saved)



class DomainEdit(LyRequestHandler):

    @has_permission('admin')
    def prepare(self):

        self.domain = self.db2.query(LuoYunConfig).filter_by( key = 'domain' ).first()

    def get(self):

        form = DomainForm()
        if self.domain:
            domain = json.loads(self.domain.value)
            if domain > 0:
                form.topdomain.data = domain['topdomain']
                form.prefix.data = domain['prefix']
                form.suffix.data = domain['suffix']

        self.render('system/domain_edit.html', form = form)


    def post(self):

        saved = None
        form = DomainForm( self.request.arguments )
        if form.validate():

            domain = json.dumps( {
                    'topdomain': form.topdomain.data,
                    'prefix': form.prefix.data,
                    'suffix': form.suffix.data } )

            if self.domain:
                self.domain.value = domain
            else:
                c = LuoYunConfig('domain', domain)
                self.db2.add(c)

            self.db2.commit()
            saved = True

        self.render('system/domain_edit.html', form = form, saved = saved)



class NginxEdit(LyRequestHandler):

    @has_permission('admin')
    def prepare(self):

        self.nginx = self.db2.query(LuoYunConfig).filter_by(key='nginx').first()

    def get(self):

        form = NginxForm()
        if self.nginx:
            nginx = json.loads(self.nginx.value)
        else:
            nginx = {}

        form.confdir.data = nginx.get(
            'conf_dir', settings.DEFAULT_NGINX_CONF_PATH )
        form.logdir.data = nginx.get(
            'log_dir', settings.DEFAULT_NGINX_LOG_PATH )
        form.binpath.data = nginx.get(
            'bin_path', settings.DEFAULT_NGINX_BIN_PATH )

        self.render('system/nginx_edit.html', form = form)


    def post(self):

        saved = None
        form = NginxForm( self.request.arguments )
        if form.validate():

            nginx = json.dumps( {
                    'conf_dir': form.confdir.data,
                    'log_dir': form.logdir.data,
                    'bin_path': form.binpath.data } )

            if self.nginx:
                self.nginx.value = nginx
            else:
                c = LuoYunConfig('nginx', nginx)
                self.db2.add(c)

            self.db2.commit()
            saved = True

        self.render('system/nginx_edit.html', form = form, saved = saved)



from markdown import Markdown
YMK = Markdown(extensions=['fenced_code', 'tables'])
class RegistrationProtocolEdit(LyRequestHandler):

    @has_permission('admin')
    def prepare(self):

        self.protocol = self.db2.query(LuoYunConfig).filter_by(key='protocol').first()

    def get(self):

        form = RegistrationProtocolForm()

        # TODO: needed give a default protocol ?
        if self.protocol:
            protocol = json.loads(self.protocol.value)
            form.text.data = protocol.get('text')

        self.render('system/registration_protocol_edit.html', form = form)


    def post(self):

        saved = None
        form = RegistrationProtocolForm( self.request.arguments )
        if form.validate():

            protocol = json.dumps({
                    'text': form.text.data,
                    'html': YMK.convert(form.text.data) })

            if self.protocol:
                self.protocol.value = protocol
            else:
                c = LuoYunConfig('protocol', protocol)
                self.db2.add(c)

            self.db2.commit()
            saved = True

        self.render('system/registration_protocol_edit.html', form = form, saved = saved)
