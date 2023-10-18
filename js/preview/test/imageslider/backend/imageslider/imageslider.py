"""gr.Image() component."""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any, Literal

import numpy as np
import PIL
import PIL.ImageOps
from gradio_client import utils as client_utils
from gradio_client.documentation import document, set_documentation_group
from PIL import Image as _Image  # using _ to minimize namespace pollution

from gradio import processing_utils, utils
from gradio.components.base import Component, StreamingInput, _Keywords
from gradio.data_classes import FileData
from gradio.events import Events

set_documentation_group("component")
_Image.init()  # fixes https://github.com/gradio-app/gradio/issues/2843


@document()
class ImageSlider(StreamingInput, Component):
    """
    Creates an image component that can be used to upload/draw images (as an input) or display images (as an output).
    Preprocessing: passes the uploaded image as a {numpy.array}, {PIL.Image} or {str} filepath depending on `type` -- unless `tool` is `sketch` AND source is one of `upload` or `webcam`. In these cases, a {dict} with keys `image` and `mask` is passed, and the format of the corresponding values depends on `type`.
    Postprocessing: expects a {numpy.array}, {PIL.Image} or {str} or {pathlib.Path} filepath to an image and displays the image.
    Examples-format: a {str} filepath to a local file that contains the image.
    Demos: image_mod, image_mod_default_image
    Guides: image-classification-in-pytorch, image-classification-in-tensorflow, image-classification-with-vision-transformers, building-a-pictionary_app, create-your-own-friends-with-a-gan
    """

    EVENTS = [
        Events.edit,
        Events.clear,
        Events.change,
        Events.stream,
        Events.select,
        Events.upload,
    ]
    data_model = FileData

    def __init__(
        self,
        value: str | _Image.Image | np.ndarray | None = None,
        *,
        shape: tuple[int, int] | None = None,
        height: int | None = None,
        width: int | None = None,
        image_mode: Literal[
            "1", "L", "P", "RGB", "RGBA", "CMYK", "YCbCr", "LAB", "HSV", "I", "F"
        ] = "RGB",
        invert_colors: bool = False,
        source: Literal["upload", "webcam", "canvas"] = "upload",
        tool: Literal["editor", "select", "sketch", "color-sketch"] | None = None,
        type: Literal["numpy", "pil", "filepath"] = "numpy",
        label: str | None = None,
        every: float | None = None,
        show_label: bool | None = None,
        show_download_button: bool = True,
        container: bool = True,
        scale: int | None = None,
        min_width: int = 160,
        interactive: bool | None = None,
        visible: bool = True,
        streaming: bool = False,
        elem_id: str | None = None,
        elem_classes: list[str] | str | None = None,
        mirror_webcam: bool = True,
        brush_radius: float | None = None,
        brush_color: str = "#000000",
        mask_opacity: float = 0.7,
        show_share_button: bool | None = None,
        **kwargs,
    ):
        """
        Parameters:
            value: A PIL Image, numpy array, path or URL for the default value that Image component is going to take. If callable, the function will be called whenever the app loads to set the initial value of the component.
            shape: (width, height) shape to crop and resize image when passed to function. If None, matches input image size. Pass None for either width or height to only crop and resize the other.
            height: Height of the displayed image in pixels.
            width: Width of the displayed image in pixels.
            image_mode: "RGB" if color, or "L" if black and white. See https://pillow.readthedocs.io/en/stable/handbook/concepts.html for other supported image modes and their meaning.
            invert_colors: whether to invert the image as a preprocessing step.
            source: Source of image. "upload" creates a box where user can drop an image file, "webcam" allows user to take snapshot from their webcam, "canvas" defaults to a white image that can be edited and drawn upon with tools.
            tool: Tools used for editing. "editor" allows a full screen editor (and is the default if source is "upload" or "webcam"), "select" provides a cropping and zoom tool, "sketch" allows you to create a binary sketch (and is the default if source="canvas"), and "color-sketch" allows you to created a sketch in different colors. "color-sketch" can be used with source="upload" or "webcam" to allow sketching on an image. "sketch" can also be used with "upload" or "webcam" to create a mask over an image and in that case both the image and mask are passed into the function as a dictionary with keys "image" and "mask" respectively.
            type: The format the image is converted to before being passed into the prediction function. "numpy" converts the image to a numpy array with shape (height, width, 3) and values from 0 to 255, "pil" converts the image to a PIL image object, "filepath" passes a str path to a temporary file containing the image.
            label: component name in interface.
            every: If `value` is a callable, run the function 'every' number of seconds while the client connection is open. Has no effect otherwise. Queue must be enabled. The event can be accessed (e.g. to cancel it) via this component's .load_event attribute.
            show_label: if True, will display label.
            show_download_button: If True, will display button to download image.
            container: If True, will place the component in a container - providing some extra padding around the border.
            scale: relative width compared to adjacent Components in a Row. For example, if Component A has scale=2, and Component B has scale=1, A will be twice as wide as B. Should be an integer.
            min_width: minimum pixel width, will wrap if not sufficient screen space to satisfy this value. If a certain scale value results in this Component being narrower than min_width, the min_width parameter will be respected first.
            interactive: if True, will allow users to upload and edit an image; if False, can only be used to display images. If not provided, this is inferred based on whether the component is used as an input or output.
            visible: If False, component will be hidden.
            streaming: If True when used in a `live` interface, will automatically stream webcam feed. Only valid is source is 'webcam'.
            elem_id: An optional string that is assigned as the id of this component in the HTML DOM. Can be used for targeting CSS styles.
            elem_classes: An optional list of strings that are assigned as the classes of this component in the HTML DOM. Can be used for targeting CSS styles.
            mirror_webcam: If True webcam will be mirrored. Default is True.
            brush_radius: Size of the brush for Sketch. Default is None which chooses a sensible default
            brush_color: Color of the brush for Sketch as hex string. Default is "#000000".
            mask_opacity: Opacity of mask drawn on image, as a value between 0 and 1.
            show_share_button: If True, will show a share icon in the corner of the component that allows user to share outputs to Hugging Face Spaces Discussions. If False, icon does not appear. If set to None (default behavior), then the icon appears if this Gradio app is launched on Spaces, but not otherwise.
        """
        self.brush_radius = brush_radius
        self.brush_color = brush_color
        self.mask_opacity = mask_opacity
        self.mirror_webcam = mirror_webcam
        valid_types = ["numpy", "pil", "filepath"]
        if type not in valid_types:
            raise ValueError(
                f"Invalid value for parameter `type`: {type}. Please choose from one of: {valid_types}"
            )
        self.type = type
        self.shape = shape
        self.height = height
        self.width = width
        self.image_mode = image_mode
        valid_sources = ["upload", "webcam", "canvas"]
        if source not in valid_sources:
            raise ValueError(
                f"Invalid value for parameter `source`: {source}. Please choose from one of: {valid_sources}"
            )
        self.source = source
        if tool is None:
            self.tool = "sketch" if source == "canvas" else "editor"
        else:
            self.tool = tool
        self.invert_colors = invert_colors
        self.streaming = streaming
        self.show_download_button = show_download_button
        if streaming and source != "webcam":
            raise ValueError("Image streaming only available if source is 'webcam'.")
        self.show_share_button = (
            (utils.get_space() is not None)
            if show_share_button is None
            else show_share_button
        )
        super().__init__(
            label=label,
            every=every,
            show_label=show_label,
            container=container,
            scale=scale,
            min_width=min_width,
            interactive=interactive,
            visible=visible,
            elem_id=elem_id,
            elem_classes=elem_classes,
            value=value,
            **kwargs,
        )

    def get_config(self):
        return {
            "image_mode": self.image_mode,
            "shape": self.shape,
            "height": self.height,
            "width": self.width,
            "source": self.source,
            "tool": self.tool,
            "value": self.value,
            "streaming": self.streaming,
            "mirror_webcam": self.mirror_webcam,
            "brush_radius": self.brush_radius,
            "brush_color": self.brush_color,
            "mask_opacity": self.mask_opacity,
            "selectable": self.selectable,
            "show_share_button": self.show_share_button,
            "show_download_button": self.show_download_button,
            **Component.get_config(self),
        }

    @staticmethod
    def update(
        value: Any | Literal[_Keywords.NO_VALUE] | None = _Keywords.NO_VALUE,
        height: int | None = None,
        width: int | None = None,
        label: str | None = None,
        show_label: bool | None = None,
        show_download_button: bool | None = None,
        container: bool | None = None,
        scale: int | None = None,
        min_width: int | None = None,
        interactive: bool | None = None,
        visible: bool | None = None,
        brush_radius: float | None = None,
        brush_color: str | None = None,
        mask_opacity: float | None = None,
        show_share_button: bool | None = None,
    ):
        return {
            "height": height,
            "width": width,
            "label": label,
            "show_label": show_label,
            "show_download_button": show_download_button,
            "container": container,
            "scale": scale,
            "min_width": min_width,
            "interactive": interactive,
            "visible": visible,
            "value": value,
            "brush_radius": brush_radius,
            "brush_color": brush_color,
            "mask_opacity": mask_opacity,
            "show_share_button": show_share_button,
            "__type__": "update",
        }

    def _format_image(
        self, im: _Image.Image | None
    ) -> np.ndarray | _Image.Image | str | None:
        """Helper method to format an image based on self.type"""
        if im is None:
            return im
        fmt = im.format
        if self.type == "pil":
            return im
        elif self.type == "numpy":
            return np.array(im)
        elif self.type == "filepath":
            path = self.pil_to_temp_file(
                im, dir=self.DEFAULT_TEMP_DIR, format=fmt or "png"
            )
            self.temp_files.add(path)
            return path
        else:
            raise ValueError(
                "Unknown type: "
                + str(self.type)
                + ". Please choose from: 'numpy', 'pil', 'filepath'."
            )

    def preprocess(
        self, x: str | dict[str, str]
    ) -> np.ndarray | _Image.Image | str | dict | None:
        """
        Parameters:
            x: base64 url data, or (if tool == "sketch") a dict of image and mask base64 url data
        Returns:
            image in requested format, or (if tool == "sketch") a dict of image and mask in requested format
        """
        if x is None:
            return x

        mask = ""
        if self.tool == "sketch" and self.source in ["upload", "webcam"]:
            assert isinstance(x, dict)
            x, mask = x["image"], x["mask"]

        if isinstance(x, str):
            im = processing_utils.decode_base64_to_image(x)
        else:
            im = PIL.Image.open(self.make_temp_copy_if_needed(x["name"]))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            im = im.convert(self.image_mode)
        if self.shape is not None:
            im = processing_utils.resize_and_crop(im, self.shape)
        if self.invert_colors:
            im = PIL.ImageOps.invert(im)
        if (
            self.source == "webcam"
            and self.mirror_webcam is True
            and self.tool != "color-sketch"
        ):
            im = PIL.ImageOps.mirror(im)

        if self.tool == "sketch" and self.source in ["upload", "webcam"]:
            mask_im = processing_utils.decode_base64_to_image(mask)

            if mask_im.mode == "RGBA":  # whiten any opaque pixels in the mask
                alpha_data = mask_im.getchannel("A").convert("L")
                mask_im = _Image.merge("RGB", [alpha_data, alpha_data, alpha_data])
            return {
                "image": self._format_image(im),
                "mask": self._format_image(mask_im),
            }

        return self._format_image(im)

    def postprocess(
        self, y: np.ndarray | _Image.Image | str | Path | None
    ) -> str | None:
        """
        Parameters:
            y: image as a numpy array, PIL Image, string/Path filepath, or string URL
        Returns:
            base64 url data
        """
        if y is None:
            return None
        if isinstance(y, np.ndarray):
            path = self.base64_to_temp_file_if_needed(
                processing_utils.encode_array_to_base64(y), "file.png"
            )
        elif isinstance(y, _Image.Image):
            path = self.base64_to_temp_file_if_needed(
                processing_utils.encode_pil_to_base64(y), "file.png"
            )
        elif isinstance(y, (str, Path)):
            name = y if isinstance(y, str) else y.name
            if client_utils.is_http_url_like(name):
                path = self.download_temp_copy_if_needed(name)
            else:
                path = self.make_temp_copy_if_needed(name)
        else:
            raise ValueError("Cannot process this value as an Image")
        return FileData(name=path, data=None, is_file=True)

    def check_streamable(self):
        if self.source != "webcam" and self.streaming:
            raise ValueError("Image streaming only available if source is 'webcam'.")

    def as_example(self, input_data: str | None) -> str:
        if input_data is None:
            return ""
        elif (
            self.root_url
        ):  # If an externally hosted image, don't convert to absolute path
            return input_data
        return str(utils.abspath(input_data))

    def example_inputs(self) -> Any:
        return "https://raw.githubusercontent.com/gradio-app/gradio/main/test/test_files/bus.png"