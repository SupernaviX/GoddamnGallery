import os
import cherrypy
import gdg
from urlparse import urljoin
from mako.template import Template
from mako.lookup import TemplateLookup
from gdg.data import *

# Content is relative to the base directory, not the module directory.
current_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

templates = TemplateLookup(directories=['html'])

class ImageModel(object):
    def __init__(self, **entries):
        self.__dict__.update(entries)

def get_relative_path(base, path):
    if path == None:
        path = ""
    if not path == "":
        path = os.path.relpath(path, current_dir)
    return urljoin(base, path.replace('\\', '/'))

def filesize(num):
    for x in ['bytes','KB','MB','GB']:
        if num < 1024.0 and num > -1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0
    return "%3.1f%s" % (num, 'TB')

def get_model(img):
    p = os.path.abspath(img.path)
    if not os.path.exists(p):
        return None
    
    filename = os.path.basename(p)
    size = filesize(os.path.getsize(p))
    if not img.r == None:
        color = "#%02X%02X%02X" % (img.r, img.g, img.b)
        grey = int((img.r * 0.299) + (img.g * 0.587) + (img.b * 0.114))
    else:
        color = "#FFFFFF"
        grey = 255

    baseurl = cherrypy.request.base
    
    model = {
        'path': get_relative_path(baseurl, img.path),
        'file': filename,
        'thumb': get_relative_path(baseurl, img.thumb),
        'gallery': img.gallery,
        'average_color': color,
        'size_x': img.x,
        'size_y': img.y,
        'filesize': size,
        'grey': grey
    }
    
    return ImageModel(**model)
    
def get_viewmodel():
    return { 'title': '', 'message': '', 'images': [], 'page': 1, 'total_images': 0, 'total_pages': 1, 'gallery': '', 'parent': '', 'children': [] }

def get_images(dbpath, model=None, page=1, page_size=20, gallery=""):
    if model == None:
        model = get_viewmodel()
    
    with GoddamnDatabase(dbpath):
        q = Image.select().where(Image.gallery == gallery)
        
        count = q.count()
        model['total_images'] = count
        
        q = q.order_by(Image.path)
        
        model['total_pages'] = int((count - 1) / page_size) + 1
        model['page'] = page
        q = q.paginate(page, page_size)
        
        model['images'] = [get_model(i) for i in q]
        
    return model

class GalleryController(object):
    @cherrypy.expose
    def index(self):
        tmp = templates.get_template("index.html")
        model = get_viewmodel()
        
        dbpath = cherrypy.request.app.config['database']['path']
        
        if not os.path.isfile(os.path.join(dbpath, 'gallery.db')):
            model['title'] = 'Goddamnit'
            model['message'] = 'Your database is not initialized.  Please run the scraper so you can see your images here.'
        else:
            model['title'] = 'Some Images'
            pagesize = cherrypy.request.app.config['gallery']['images_per_page']
            get_images(dbpath, model, 1, pagesize)
        
        return tmp.render(**model)
    
    @cherrypy.expose
    def page(self, page=1):
        tmp = templates.get_template("index.html")
        dbpath = cherrypy.request.app.config['database']['path']
        page_size = cherrypy.request.app.config['gallery']['images_per_page']
        
        model = get_images(dbpath, page=int(page), page_size=page_size)
        model['title'] = 'Some Images'
        
        return tmp.render(**model)

def main():
    cherrypy.tree.mount(root=GalleryController(), config='gdg.conf')
    cherrypy.engine.start()
    cherrypy.engine.block()