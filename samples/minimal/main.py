from direct.showbase.ShowBase import ShowBase

from p3dopenxr.p3dopenxr import P3DOpenXR
from panda3d.core import LPoint3


# Set up the window, camera, etc.

base = ShowBase()
base.setFrameRateMeter(True)

# Create and configure the VR environment

openxr = P3DOpenXR()
openxr.init()

panda = base.loader.loadModel("panda")
panda.reparentTo(base.render)
min_bounds, max_bounds = panda.get_tight_bounds()
height = max_bounds.get_z() - min_bounds.get_z()
panda.set_scale(1.5 / height)
panda.set_pos(0, 1, -min_bounds.get_z() / height * 1.5)

left_hand = base.loader.loadModel("box")
min_bounds, max_bounds = left_hand.get_tight_bounds()
left_hand.set_pos(LPoint3(-0.5) * 0.1)
left_hand.set_scale(0.1)
left_hand.reparent_to(openxr.left_hand_anchor)

right_hand = base.loader.loadModel("box")
right_hand.set_pos(LPoint3(-0.5) * 0.1)
right_hand.set_scale(0.1)
right_hand.reparent_to(openxr.right_hand_anchor)

base.accept('escape', base.userExit)
base.accept('b', base.bufferViewer.toggleEnable)

base.run()
