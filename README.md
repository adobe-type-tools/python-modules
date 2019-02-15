Python modules
=========================

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/0c4dd87e3a6a45d6bc8d034d8c84cbf7)](https://app.codacy.com/app/frankrolf/python-modules?utm_source=github.com&utm_medium=referral&utm_content=adobe-type-tools/python-modules&utm_campaign=badger)

These files are used and required by some of the Python scripts available in the other repositories.

For FontLab scripts, put these files in `[...]/FontLab/Studio 5/Macros/System/Modules`.  
For the remaining scripts, put these files in the same folder as the script, or put them in one of the folders listed by `sys.path`.

## kern feature writer modules
### `WriteFeaturesKernFDK.py`

Example code for using `WriteFeaturesKernFDK` as a module in RoboFont:

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

    ufo = os.path.normpath(sys.argv[-1])
    f = Font(ufo)

    minKern         =  3
    writeTrimmed    =  False
    writeSubtables  =  True

    instanceFolder = os.path.dirname(f.path)

    WriteFeaturesKernFDK.KernDataClass(f, instanceFolder, minKern, writeTrimmed, writeSubtables)

```

### `kernFeatureWriter.py`

The new `kernFeatureWriter.py` module is currently in development.  
It produces the same results as the old `WriteFeaturesKernFDK.py` module, but it can be used directly from the command line, in a more seamless way:

```bash

    python kernFeatureWriter.py font.ufo
    python kernFeatureWriter.py font.ufo -min 5

```

The main motivation for writing this new module were problems with kerning subtable overflow.  

## mark feature writer module
### `WriteFeaturesMarkFDK.py`
Example code for a Python file that uses the `WriteFeaturesMarkFDK` module from the command line:

```python

    import os
    import sys

    import WriteFeaturesMarkFDK
    from fontParts.fontshell import RFont

    fontPath = sys.argv[-1]
    font = RFont(fontPath)

    genMkmkFeature       =  True
    writeClassesFile     =  False
    indianScriptsFormat  =  False
    trimCasingTags       =  False

    WriteFeaturesMarkFDK.MarkDataClass(font, os.path.dirname(font.path), trimCasingTags, genMkmkFeature, writeClassesFile, indianScriptsFormat)

```

## other modules

### `AdobeFontLabUtils.py`

Support module for FontLab scripts. Defines commonly used functions and globals.

### `BezChar.py`

This module converts between a FontLab glyph and a bez file data string. Used
by the OutlineCheck and AutoHint scripts, to convert FL glyphs to bez programs 
as needed by C libraries that do the hard work.

### `kernExport.py`

Module to export FontLab class-kerning to UFO. It needs to be called with a FL font object (`fl.font`), and a prefixOption. The prefixOption is used for renaming kerning classes to various UFO-styles.

If the prefixOption is `None`, class names will be prefixed with to @L_ and @R_ to keep track of their side (in case they need to be converted the opposite way and re-imported to FL).

The prefixOptions are:  
`'MM'`: convert class names to MetricsMachine-compatible group names  
`'UFO3'`: convert to UFO3-style class names  

usage (one of the three):

```python

    kernExport.ClassKerningToUFO(fl.font)
    kernExport.ClassKerningToUFO(fl.font, prefixOption='MM')
    kernExport.ClassKerningToUFO(fl.font, prefixOption='UFO3')

```
