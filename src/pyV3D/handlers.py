import os
import sys
import traceback
import weakref

from numpy import array, float32, float64, int32, uint8

from tornado import websocket

from pyV3D._pyV3D import WV_Wrapper, WV_ON, WV_SHADING, WV_ORIENTATION

from pkg_resources import working_set

def ERROR(*args):
    for arg in args:
        sys.stderr.write(str(arg))
        sys.stderr.write(" ")
    sys.stderr.write('\n')
    sys.stderr.flush()

#def DEBUG(*args):
#    pass
DEBUG = ERROR

class WSHandler(websocket.WebSocketHandler):

    subhandlers = {} # map of obj pathname or file pathname to subhandler instances
    protocols = {}   # map of protocols to lists of supporting subhandlers

    def initialize(self, view_dir):
        self.view_dir = os.path.abspath(os.path.expanduser(view_dir)

    def _handle_request_exception(self, exc):
        ERROR("Unhandled exception: %s" % str(exc))
        super(WSHandler, self)._handle_request_exception(exc)

    def _execute(self, transforms, *args, **kwargs):
        self.transforms = transforms
        self.args = args[:]
        self.kwargs = kwargs.copy()
        # try:
        #     self.view_handler = self.geometry_file = self.inner_class = None
        #     if len(args) > 0 and args[0]:
        #         # allow for specified filename to be followed by a ':' and an inner class name
        #         parts = args[0].rsplit(':',1)
        #         if len(parts) > 1:
        #             self.inner_class = parts[1]
        #             farg = parts[0]
        #         else:
        #             farg = args[0]
        #         farg = os.path.abspath(os.path.expanduser(farg))
        #         if not farg.startswith(self.view_dir):
        #             raise RuntimeError("attempted to load a file outside of the view directory")
        #         self.geometry_file = farg
        #     args = args[1:]
        #     super(WSHandler, self)._execute(transforms, *args, **kwargs)
        # except Exception as err:
        #     ERROR("%s" % str(err))

    # this is called before open
    def select_subprotocol(self, subprotocols):
        try:
            #protocols = ['pyv3d-bin-1.0', 'pyv3d-txt-1.0']
            for p in subprotocols:
                if p in self.protocols:
                    self._proto = p
                    DEBUG("matched subproto %s" % p)
                    return p
            DEBUG("returning None for subproto choices: %s" % subprotocols)
        except Exception as err:
            ERROR("%s" % err)
        self._proto = None
        return None

    def open(self):
        try:
            if self._proto == 'pyv3d-bin-1.0':  # binary protocol
                klass = None
                if self.geometry_file:
                    self.geometry_file = os.path.join(self.view_dir, self.geometry_file)
                    parts = self.geometry_file.rsplit('.', 1)
                    if len(parts) > 1:
                        try:
                            klasses = self.subhandler_classes[parts[1]]
                        except KeyError:
                           raise RuntimeError("no viewer found for file extension '.%s'. " % parts[1])
                        if len(klasses) > 1:
                            ERROR("multiple viewer plugins found for extension .%s. Using the first (%s)." % (parts[1], klasses[0].__name__))
                        klass = klasses[0]
                else:
                    klass = CubeViewHandler

                if klass:
                    self.view_handler = klass(handler=self, fname=self.geometry_file, 
                                              inner_class=self.inner_class)
                    self.subhandlers[self.geometry_file] = self.view_handler

                if klass is None:
                    self.send_error(404)
                    return

                self.view_handler.open()
            else:  # text protocol
                pass
        except Exception as err:
            ERROR('Exception: %s' % traceback.format_exc())

    def on_message(self, message):
        if self.view_handler is None:
            self.send_error(404)
            return
        self.view_handler.on_message(message)

    def on_close(self):
        DEBUG("WebSocket closed (proto=%s" % self._proto)



class WV_ViewHandler(object):
    def __init__(self, handler, fname=None, inner_class=None):
        self.wv = WV_Wrapper()
        self.buf = self.wv.get_bufflen()*'\0'
        self.handler = weakref.ref(handler)  # need this to send the msgs
        self.geometry_file = fname
        self.inner_class = inner_class

    @staticmethod
    def get_protocols():
        """Returns a list of supported protocols."""
        return ['pyv3d-bin-1.0', 'pyv3d-txt-1.0']

    def send_binary_data(self, wsi, buf, ibuf):
        try:
            self.handler().write_message(buf, binary=True)
        except Exception as err:
            ERROR("Exception in send_binary_data:", err)
            return -1
        return 0

    def send_geometry(self, first=False):
        self.wv.prepare_for_sends()

        if first:
            self.wv.send_GPrim(self, self.buf,  1, self.send_binary_data)  # send init packet
            self.wv.send_GPrim(self, self.buf, -1, self.send_binary_data)  # send initial suite of GPrims
        else:  #FIXME: add updating of GPRims here...
            pass

        self.wv.finish_sends()

    def on_message(self, message):
        DEBUG("websocket got message: %s" % message)

    def on_close(self):
        DEBUG("WebSocket closed. addr=%s" % id(self))

    def open(self):
        DEBUG("WebSocket opened. addr=%d" % id(self))
        DEBUG("fname = %s" % self.geometry_file)
        try:
            self.create_geom()
            self.send_geometry(first=True)
        except Exception as err:
            ERROR('Exception: %s' % traceback.format_exc())


class CubeViewHandler(WV_ViewHandler):

    @staticmethod
    def get_file_extensions():
        """Returns a list of file extensions that this handler knows how to view."""
        return []

    def create_geom(self):

        eye    = array([0.0, 0.0, 7.0], dtype=float32)
        center = array([0.0, 0.0, 0.0], dtype=float32)
        up     = array([0.0, 1.0, 0.0], dtype=float32)
        fov   = 30.0
        zNear = 1.0
        zFar  = 10.0

        bias = 0
        self.wv.createContext(bias, fov, zNear, zFar, eye, center, up)
        self.wv.createBox("Box$1", WV_ON|WV_SHADING|WV_ORIENTATION, [0.,0.,0.])


def load_subhandlers():
    """Loads all entry points in the pyv3d.subhandlers group."""

    # find all of the installed pyv3d view handlers
    for ep in working_set.iter_entry_points('pyv3d.subhandlers'):
        try:
            klass = ep.load()
        except Exception as err:
            ERROR("Entry point %s failed to load: %s" % (str(ep).split()[0], err))
        else:
            # exts = klass.get_file_extensions()
            # for ext in exts:
            #     WSHandler.extensions.setdefault(ext, []).append(klass)
            protos = klass.get_protocols():
            for proto in protos:
                WSHandler.protocols.setdefault(proto, []).append(klass)



