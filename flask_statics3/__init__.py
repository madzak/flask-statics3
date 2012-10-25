#!/usr/bin/env python
# coding=utf8

import os
from collections import defaultdict
from urllib import quote
from urlparse import urlparse, urlunparse
from flask import Blueprint, current_app
from flask import url_for as flask_url_for
from flask.ext.script import Manager, Command, Option, prompt_bool
from boto.s3.connection import S3Connection
from boto.s3.key import Key

def url_for(endpoint, **values):
    app = current_app
    
    if endpoint == 'static' or endpoint.endswith('.static'):
        bucket_path = "{}/{}".format(app.config['S3_BUCKET_DOMAIN'], app.config['S3_BUCKET'])
        
        urls = app.url_map.bind(bucket_path)
        built_url = urls.build(endpoint, values=values, force_external=True)
        
        scheme, netloc, path, params, query, fragment = urlparse(built_url)
        return urlunparse(("", netloc, path, params, query, fragment))
    return flask_url_for(endpoint, **values)

def walk_dir(start, root, loc, dir_list):
    dir_items = os.listdir(start)
    
    for item in dir_items:
        full_path = os.path.join(start, item)
        
        if os.path.isdir(full_path):
            walk_dir(full_path, root, loc, dir_list)
        else:
            dir_list.append((loc+full_path.replace(root, ""), full_path))
    
def find_static(app):
    """ Gets all files in static folders and returns in dict."""
    dirs = [(unicode(app.static_folder), app.static_url_path)]
    if hasattr(app, 'blueprints'):
        bp_details = lambda x: (x.static_folder, "{}{}".format(x.url_prefix or '', x.static_url_path))
        dirs.extend([bp_details(x) for x in app.blueprints.values()])

    valid_files = []
    for static_folder, static_url_loc  in dirs:
        if static_folder == None:
            continue
        
        walk_dir(static_folder, static_folder, static_url_loc, valid_files)
    
    return valid_files
    
def get_bucket(app): 
    conn = S3Connection(app.config['AWS_ACCESS_KEY_ID'], app.config['AWS_SECRET_ACCESS_KEY'])
    
    return conn.get_bucket(app.config["S3_BUCKET"])      
    
def upload(app, static_files):
    bucket = get_bucket(app)
    bucket.set_acl('public-read')
    
    if not bucket:
        raise ValueError("S3_BUCKET does not exist")
    
    for (asset_url, asset_loc) in static_files:
        print("Copying '{}'".format(asset_loc))
        
        push_file(asset_url, asset_loc, bucket)

def clear_bucket(app):
    bucket = get_bucket(app)
    length = 0
    
    for asset in bucket.list():
        print("Deleting '{}'".format(asset.name))
        
        bucket.delete_key(asset.name)
        length += 1
        
    return length

def push_file(asset_url, asset, bucket):
    file_key = bucket.new_key(asset_url)
    file_key.set_contents_from_filename(asset, policy='public-read', replace=True)

class Collectstatic(Command):
    'Collects all static files into S3'
    option_list = (
        Option('--no-input', '-n', action='store_true', dest='no_input', default=False),
        Option('--ignore', '-i', dest="ignore", default=None),
        Option('--clear', '-c', action='store_true', dest="clear", default=False),
        Option('--dry-run', '-d', action='store_true', dest="dry_run", default=False),
    )
    
    def run(self, no_input, ignore, dry_run, clear):
        app = current_app
        
        if no_input:
            return self.manage_assets(app, ignore, dry_run, clear)
        
        print('''
You have requested to collect static files at the destination
location as specified in your settings.

This will overwrite existing files!
        ''')
        if prompt_bool("Are you sure you want to do this?"):
            return self.manage_assets(app, ignore, dry_run, clear)

        return
            
    def manage_assets(self, app, ignore, dry_run, clear):
        assets = find_static(app)
        
        def display_assets(action, assets):
            for (asset_url, asset_loc) in assets:
                print("{} '{}'".format(action, asset_loc))
        
        if clear:
            if dry_run:
                display_assets("Pretending to copy", assets);
            else:
                cleared = clear_bucket(app)

            print ("{} static files deleted.".format(cleared))
        else:
            if dry_run:
                display_assets("Pretending to copy", assets);
            else:
                upload(app, assets)
                
            print ("{} static files copied.".format(len(assets)))
        
        return
        
class StaticS3(object):
    def __init__(self, app=None):
       self.app = None
       if app is not None:
           self.app = app
           self.init_app(self.app)
    
    def init_app(self, app):
        app.config.setdefault('S3_BUCKET_DOMAIN', 's3.amazonaws.com')
        app.config.setdefault('ENABLE_S3_STATIC', False)
        app.config.setdefault('S3_BUCKET', 'static')
        
        blueprint = Blueprint(
            'StaticS3',
            __name__)

        app.register_blueprint(blueprint)
        
        if app.config['ENABLE_S3_STATIC']:
            app.jinja_env.globals['url_for'] = url_for
            
        manager = Manager(app)
        