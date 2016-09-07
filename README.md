Python modules
=========================
These files are used and required by some of the Python scripts available in the other repositories.

For FontLab scripts, put these files in `[...]/FontLab/Studio 5/Macros/System/Modules`.
For the remaining scripts, put these files in the same folder as the script, or put them in one of the folders listed by `sys.path`.

### kern feature writer module
Example code for `WriteFeaturesKernFDK` in RoboFont scripting window:

```python

import os
import WriteFeaturesKernFDK

f = CurrentFont()

minKern = 5
writeTrimmed = False
writeSubtables = False

instanceFolder = os.path.dirname(f.path)

WriteFeaturesKernFDK.KernDataClass(f, instanceFolder, minKern, writeTrimmed, writeSubtables)

```

Example code for a Python file that uses `WriteFeaturesKernFDK` from the command line:

```python

import sys
import os
from defcon import Font
import WriteFeaturesKernFDK

ufo = sys.argv[-1]
if ufo.endswith(os.sep):
    ufo = ufo[:-1]
f = Font(ufo)

minKern         =  3
writeTrimmed    =  False
writeSubtables  =  True

instanceFolder = os.path.dirname(f.path)

WriteFeaturesKernFDK.KernDataClass(f, instanceFolder, minKern, writeTrimmed, writeSubtables)

```

----

The new `kernFeatureWriter.py` module is currently in development. It produces the same results as the old `WriteFeaturesKernFDK` module, but can be used in a more seamless way:

```
python kernFeatureWriter.py font.ufo
```

The main motivation for writing this new module were problems with kerning subtable overflow.  

### mark feature writer module


Example code for a Python file that uses `WriteFeaturesMarkFDK` from the command line:

```python

import os
import sys

import WriteFeaturesMarkFDK
from robofab.world import RFont

fontPath = sys.argv[-1]
font = RFont(fontPath)

genMkmkFeature       =  False
writeClassesFile     =  False
indianScriptsFormat  =  False
trimCasingTags       =  False

WriteFeaturesMarkFDK.MarkDataClass(font, os.path.dirname(font.path), trimCasingTags, genMkmkFeature, writeClassesFile, indianScriptsFormat)

```

