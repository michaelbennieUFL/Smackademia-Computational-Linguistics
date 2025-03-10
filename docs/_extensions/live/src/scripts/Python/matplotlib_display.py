# Based on pyodide/matplotlib_pyodide/html5_canvas_backend.py
# Modified for OffscreenCanvas rendering under Web Worker
# License: Mozilla Public License Version 2.0

import math
import numpy as np
from functools import lru_cache
from matplotlib.backend_bases import (
    FigureCanvasBase,
    FigureManagerBase,
    RendererBase,
    GraphicsContextBase,
    _Backend,
)
from matplotlib._enums import CapStyle
from matplotlib.font_manager import findfont
from matplotlib.ft2font import LOAD_NO_HINTING, FT2Font
from matplotlib.mathtext import MathTextParser
from matplotlib.colors import colorConverter, rgb2hex
from matplotlib.path import Path
from matplotlib.transforms import Affine2D
from IPython.display import display
from js import ImageData, OffscreenCanvas # type: ignore[attr-defined]
from pyodide.ffi import create_proxy # type: ignore[attr-defined]
import logging

_capstyle_d = {"projecting": "square", "butt": "butt", "round": "round"}
logging.getLogger('matplotlib.font_manager').disabled = True

class RichImageBitmapOutput():
    def __init__(self, figure):
        self.image = figure._imagebitmap
        self.title = figure._title

    def _repr_mimebundle_(self, include, exclude):
        return { "application/html-imagebitmap": self.image }, { "title": self.title }

class FigureCanvasWorker(FigureCanvasBase):
    def __init__(self, *args, **kwargs):
        FigureCanvasBase.__init__(self, *args, **kwargs)
        self._idle_scheduled = False
        self._id = "matplotlib_" + hex(id(self))[2:]
        self._title = ""
        self._ratio = 2

        width, height = self.get_width_height()
        width *= self._ratio
        height *= self._ratio

        self._canvas = OffscreenCanvas.new(width, height)
        self._context = self._canvas.getContext("2d")
        self._imagebitmap = None

    def show(self, *args, **kwargs):
        self.close()
        self.draw()
        self._imagebitmap = self._canvas.transferToImageBitmap()
        display(RichImageBitmapOutput(self))

    def draw(self):
        self._idle_scheduled = True
        orig_dpi = self.figure.dpi
        if self._ratio != 1:
            self.figure.dpi *= self._ratio
        try:
            width, height = self.get_width_height()
            if self._canvas is None:
                return
            renderer = RendererHTMLCanvasWorker(self._context, width, height, self.figure.dpi, self)
            self.figure.draw(renderer)
        except Exception as e:
            raise RuntimeError("Rendering failed") from e
        finally:
            self.figure.dpi = orig_dpi
            self._idle_scheduled = False

    def set_window_title(self, title):
        self._title = title

    def close(self):
        if (self._imagebitmap):
            self._imagebitmap.close()
            self._imagebitmap = None

    def destroy(self, *args, **kwargs):
        self.close()

class GraphicsContextHTMLCanvas(GraphicsContextBase):
    def __init__(self, renderer):
        super().__init__()
        self.stroke = True
        self.renderer = renderer

    def restore(self):
        self.renderer.ctx.restore()

    def set_capstyle(self, cs):
        if isinstance(cs, str):
            cs = CapStyle(cs)
        # Convert the JoinStyle enum to its name if needed
        if hasattr(cs, "name"):
            cs = cs.name.lower()
        if cs in ["butt", "round", "projecting"]:
            self._capstyle = cs
            self.renderer.ctx.lineCap = _capstyle_d[cs]
        else:
            raise ValueError(f"Unrecognized cap style. Found {cs}")

    def get_capstyle(self):
        return self._capstyle

    def set_clip_rectangle(self, rectangle):
        self.renderer.ctx.save()
        if not rectangle:
            self.renderer.ctx.restore()
            return
        x, y, w, h = np.round(rectangle.bounds)
        self.renderer.ctx.beginPath()
        self.renderer.ctx.rect(x, self.renderer.height - y - h, w, h)
        self.renderer.ctx.clip()

    def set_clip_path(self, path):
        self.renderer.ctx.save()
        if not path:
            self.renderer.ctx.restore()
            return
        tpath, affine = path.get_transformed_path_and_affine()
        affine = affine + Affine2D().scale(1, -1).translate(0, self.renderer.height)
        self.renderer._path_helper(self.renderer.ctx, tpath, affine)
        self.renderer.ctx.clip()

    def set_dashes(self, dash_offset, dash_list):
        self._dashes = dash_offset, dash_list
        if dash_offset is not None:
            self.renderer.ctx.lineDashOffset = dash_offset
        if dash_list is None:
            self.renderer.ctx.setLineDash([])
        else:
            dln = np.asarray(dash_list)
            dl = list(self.renderer.points_to_pixels(dln))
            self.renderer.ctx.setLineDash(dl)

    def set_joinstyle(self, js):
        if js in ["miter", "round", "bevel"]:
            self._joinstyle = js
            self.renderer.ctx.lineJoin = js
        else:
            raise ValueError(f"Unrecognized join style. Found {js}")

    def set_linewidth(self, w):
        self.stroke = w != 0
        self._linewidth = float(w)
        self.renderer.ctx.lineWidth = self.renderer.points_to_pixels(float(w))

class RendererHTMLCanvasWorker(RendererBase):
    def __init__(self, ctx, width, height, dpi, fig):
        super().__init__()
        self.fig = fig
        self.ctx = ctx
        self.width = width
        self.height = height
        self.ctx.width = self.width
        self.ctx.height = self.height
        self.dpi = dpi
        self.mathtext_parser = MathTextParser("path")
        self._get_font_helper = lru_cache(maxsize=50)(self._get_font_helper)

        # Keep the state of fontfaces that are loading
        self.fonts_loading = {}

    def new_gc(self):
        return GraphicsContextHTMLCanvas(renderer=self)

    def points_to_pixels(self, points):
        return (points / 72.0) * self.dpi

    def _matplotlib_color_to_CSS(self, color, alpha, alpha_overrides, is_RGB=True):
        if not is_RGB:
            R, G, B, alpha = colorConverter.to_rgba(color)
            color = (R, G, B)

        if (len(color) == 4) and (alpha is None):
            alpha = color[3]

        if alpha is None:
            CSS_color = rgb2hex(color[:3])

        else:
            R = int(color[0] * 255)
            G = int(color[1] * 255)
            B = int(color[2] * 255)
            if len(color) == 3 or alpha_overrides:
                CSS_color = f"""rgba({R:d}, {G:d}, {B:d}, {alpha:.3g})"""
            else:
                CSS_color = """rgba({:d}, {:d}, {:d}, {:.3g})""".format(
                    R, G, B, color[3]
                )

        return CSS_color

    def _draw_math_text(self, gc, x, y, s, prop, angle):
        width, height, depth, glyphs, rects = self.mathtext_parser.parse(
            s, dpi=self.dpi, prop=prop
        )
        self.ctx.save()
        self.ctx.translate(x, self.height + y)
        if angle != 0:
            self.ctx.rotate(-math.radians(angle))
        self.ctx.fillStyle = self._matplotlib_color_to_CSS(
            gc.get_rgb(), gc.get_alpha(), gc.get_forced_alpha()
        )
        for font, fontsize, c, ox, oy in glyphs:
            self.ctx.save()
            self.ctx.translate(ox, -oy)
            font.set_size(fontsize, self.dpi)
            font.load_char(c)
            verts, codes = font.get_path()
            path = Path(verts, codes)
            transform = Affine2D().scale(1.0, -1.0)
            self._path_helper(self.ctx, path, transform)
            self.ctx.fill()
            self.ctx.restore()
        for x1, y1, x2, y2 in rects:
            self.ctx.fillRect(x1, -y2, x2 - x1, y2 - y1)
        self.ctx.restore()

    def _set_style(self, gc, rgbFace=None):
        if rgbFace is not None:
            self.ctx.fillStyle = self._matplotlib_color_to_CSS(
                rgbFace, gc.get_alpha(), gc.get_forced_alpha()
            )

        capstyle = gc.get_capstyle()
        if capstyle:
            # Get the string name if it's an enum
            if hasattr(capstyle, "name"):
                capstyle = capstyle.name.lower()
            self.ctx.lineCap = _capstyle_d[capstyle]

        self.ctx.strokeStyle = self._matplotlib_color_to_CSS(
            gc.get_rgb(), gc.get_alpha(), gc.get_forced_alpha()
        )

        self.ctx.lineWidth = self.points_to_pixels(gc.get_linewidth())

    def _path_helper(self, ctx, path, transform, clip=None):
        ctx.beginPath()
        for points, code in path.iter_segments(transform, remove_nans=True, clip=clip):
            if code == Path.MOVETO:
                ctx.moveTo(points[0], points[1])
            elif code == Path.LINETO:
                ctx.lineTo(points[0], points[1])
            elif code == Path.CURVE3:
                ctx.quadraticCurveTo(*points)
            elif code == Path.CURVE4:
                ctx.bezierCurveTo(*points)
            elif code == Path.CLOSEPOLY:
                ctx.closePath()

    def draw_path(self, gc, path, transform, rgbFace=None):
        self._set_style(gc, rgbFace)
        if rgbFace is None and gc.get_hatch() is None:
            figure_clip = (0, 0, self.width, self.height)
        else:
            figure_clip = None

        transform += Affine2D().scale(1, -1).translate(0, self.height)
        self._path_helper(self.ctx, path, transform, figure_clip)

        if rgbFace is not None:
            self.ctx.fill()
            self.ctx.fillStyle = "#000000"

        if gc.stroke:
            self.ctx.stroke()

    def draw_markers(self, gc, marker_path, marker_trans, path, trans, rgbFace=None):
        super().draw_markers(gc, marker_path, marker_trans, path, trans, rgbFace)

    def _get_font_helper(self, prop):
        fname = findfont(prop)
        font = FT2Font(str(fname))
        font_file_name = fname.rpartition("/")[-1]
        return (font, font_file_name)

    def _get_font(self, prop):
        result = self._get_font_helper(prop)
        font = result[0]
        font.clear()
        font.set_size(prop.get_size_in_points(), self.dpi)
        return result

    def get_text_width_height_descent(self, s, prop, ismath):
        w: float
        h: float
        d: float
        if ismath:
            # Use the path parser to get exact metrics
            width, height, depth, _, _ = self.mathtext_parser.parse(
                s, dpi=72, prop=prop
            )
            return width, height, depth
        else:
            font, _ = self._get_font(prop)
            font.set_text(s, 0.0, flags=LOAD_NO_HINTING)
            w, h = font.get_width_height()
            w /= 64.0
            h /= 64.0
            d = font.get_descent() / 64.0
        return w, h, d

    def draw_image(self, gc, x, y, im, transform=None):
        import numpy as np
        im = np.flipud(im)
        h, w, d = im.shape
        y = self.ctx.height - y - h
        im = np.ravel(np.uint8(np.reshape(im, (h * w * d, -1)))).tobytes()
        pixels_proxy = create_proxy(im)
        pixels_buf = pixels_proxy.getBuffer("u8clamped")
        img_data = ImageData.new(pixels_buf.data, w, h)
        self.ctx.save()
        in_memory_canvas = OffscreenCanvas.new(w, h)
        in_memory_canvas_context = in_memory_canvas.getContext("2d")
        in_memory_canvas_context.putImageData(img_data, 0, 0)
        self.ctx.drawImage(in_memory_canvas, x, y, w, h)
        self.ctx.restore()
        pixels_proxy.destroy()
        pixels_buf.release()

    def draw_text(self, gc, x, y, s, prop, angle, ismath=False, mtext=None):
        if ismath:
            self._draw_math_text(gc, x, y, s, prop, angle)
            return

        angle = math.radians(angle)
        width, height, descent = self.get_text_width_height_descent(s, prop, ismath)
        x -= math.sin(angle) * descent
        y -= math.cos(angle) * descent - self.ctx.height
        font_size = self.points_to_pixels(prop.get_size_in_points())

        font_property_string = "{} {} {:.3g}px {}, {}".format(
            prop.get_style(),
            prop.get_weight(),
            font_size,
            prop.get_name(),
            prop.get_family()[0],
        )
        if angle != 0:
            self.ctx.save()
            self.ctx.translate(x, y)
            self.ctx.rotate(-angle)
            self.ctx.translate(-x, -y)
        self.ctx.font = font_property_string
        self.ctx.fillStyle = self._matplotlib_color_to_CSS(
            gc.get_rgb(), gc.get_alpha(), gc.get_forced_alpha()
        )
        self.ctx.fillText(s, x, y)
        self.ctx.fillStyle = "#000000"
        if angle != 0:
            self.ctx.restore()

class FigureManagerHTMLCanvas(FigureManagerBase):
    def __init__(self, canvas, num):
        super().__init__(canvas, num)
        self.set_window_title("Figure %d" % num)

    def show(self, *args, **kwargs):
        self.canvas.show(*args, **kwargs)

    def destroy(self, *args, **kwargs):
        self.canvas.destroy(*args, **kwargs)

    def resize(self, w, h):
        pass

    def set_window_title(self, title):
        self.canvas.set_window_title(title)


@_Backend.export
class _BackendWasmCoreAgg(_Backend):
    FigureCanvas = FigureCanvasWorker
    FigureManager = FigureManagerHTMLCanvas

    @staticmethod
    def show(*args, **kwargs):
        from matplotlib import pyplot as plt
        plt.gcf().canvas.show(*args, **kwargs)

    @staticmethod
    def destroy(*args, **kwargs):
        from matplotlib import pyplot as plt
        plt.gcf().canvas.destroy(*args, **kwargs)
