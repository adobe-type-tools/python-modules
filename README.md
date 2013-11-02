Python modules
=========================
These files are used and required by some of the Python scripts available in the other repositories.

For FontLab scripts, put these files in `[...]/FontLab/Studio 5/Macros/System/Modules`.
For the remaining scripts, put these files in the same folder as the script, or put them in one of the folders listed by `sys.path`.

---
Example code for `WriteFeaturesKernFDK` in RoboFont scripting window:

<pre><code>
import os
import WriteFeaturesKernFDK

f = CurrentFont()

minKern = 5
writeTrimmed = False
writeSubtables = False

instanceFolder = os.path.dirname(f.path)

WriteFeaturesKernFDK.KernDataClass(f, instanceFolder, minKern, writeTrimmed, writeSubtables)

</code></pre>

---
Example code for a Python file that uses `WriteFeaturesKernFDK` from the command line:

<pre><code>
import sys
import os
from defcon import Font
import WriteFeaturesKernFDK

ufo = sys.argv[-1]
if ufo.endswith(os.sep):
    ufo = ufo[:-1]
f = Font(ufo)

minKern = 3
writeTrimmed = False
writeSubtables = True

instanceFolder = os.path.dirname(f.path)

WriteFeaturesKernFDK.KernDataClass(f, instanceFolder, minKern, writeTrimmed, writeSubtables)

</code></pre>
