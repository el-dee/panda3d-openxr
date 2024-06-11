# panda3d-openxr

This module provides integration of [OpenXR](https://www.khronos.org/openxr/) with [Panda3D](https://www.panda3d.org/) using [pyopenxr](https://github.com/cmbruns/pyopenxr)

Note: The functionalities supported by this preliminary version are still very limited. Only rendering, camera tracking and hand tracking is supported. Pose, action and advanced rendering will ber added in future versions.


## Requirements

This module requires Panda3D > 1.10.0, PyOpenGL > 3.0.0, pyopenxr > 1.1.0 and a compliant implementation of OpenXR. It supports Windows, Linux and macOS platforms.


## Installation

### From wheel

    pip install panda3d-openxr

### From source

    git clone https://github.com/el-dee/panda3d-openxr
    cd panda3d-openxr
    python3 pip install .


## Usage

To use panda3d-openvr, first import the p3dopenvr module in your application :

    from p3dopenxr.p3dopenxr import P3DOpenXR

Then, once an instance of ShowBase is created, instanciate the VR interface and initialize it :

    myvr = P3DOpenXR()
    myvr.init()

Once done, the module will enable the VR application layer of OpenXR, create the left and right cameras (in case of Stereoscopic mode) and configure the rendering system to send the images of each eye to the VR compositor.

The module will create the following hierachy in the scenegraph :

* Traking space origin (tracking_space)
    * HMD anchor (hmd_anchor)
    * Left eye (left_eye_anchor)
    * Right eye (right_eye_anchor)
    * Left hand (left_hand_anchor)
    * Right eye (right_hand_anchor)

The init method has a couple of parameters to configure :

    * The near and far planes of the created cameras
    * The framebuffer properties to create the rendering chain


## Documentation

There is no documentation available yet...


## Examples

All the examples are found under samples/ directory, to launch them simply go to their directory and run:

    python3 main.py

### Minimal

In minimal you can find a minimal setup that will draw a Panda avatar in front of you, and a (ugly) cube where your hands ought to be.


## License and Acknowledgments

This library is licensed under the "Apache License Version 2.0", see the file LICENSE for the full text of the license.

This code is heavily based upon the `hello_xr` example made by the Khronos Group, and ported to the Python Langage by "Christopher Bump", author of the PyOpenXR library.
Many thanks to them as without their work this library wouldn't exist at all.
