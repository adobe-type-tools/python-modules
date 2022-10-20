[![codecov](https://codecov.io/gh/adobe-type-tools/python-modules/branch/master/graph/badge.svg?token=Zeqzh6AHfO)](https://codecov.io/gh/adobe-type-tools/python-modules)

Python modules
==============

These tools are used to write feature files which is be based on information found within UFO sources.
The two main tools are `kernFeatureWriter.py` and `markFeatureWriter.py`.

### `kernFeatureWriter.py`

```bash

    # write out a kern feature file
    python kernFeatureWriter.py font.ufo

    # write a kern feature file with minimum absolute kerning value of 5
    python kernFeatureWriter.py -min 5 font.ufo

    # write a kern feature with subtable breaks
    python kernFeatureWriter.py -s font.ufo

```

### `markFeatureWriter.py`

```bash

    # write a basic mark feature
    python markFeatureWriter.py font.ufo

    # write mark and mkmk feature files
    python markFeatureWriter.py -m font.ufo

```

For both of these scripts, the resulting feature file only contains the raw feature data. This data can be used by means of an `include` statement:

```
feature kern{
    include(kern.fea);

} kern;
```

The benefit of this is that different feature flags can be used, see for example https://github.com/adobe-fonts/source-serif/blob/main/familyGPOS.fea#L12-L13


### `kernExport.py`

FontLab 5-Module to export FontLab class-kerning to UFO. It needs to be called with a FL font object (`fl.font`), and a prefixOption. The prefixOption is used for renaming kerning classes to various UFO-styles.

If the prefixOption is `None`, class names will be prefixed with to @L_ and @R_ to keep track of their side (in case they need to be re-imported into FL).

The prefixOptions are:  
`'MM'`: convert class names to MetricsMachine-compatible group names  
`'UFO3'`: convert to UFO3-style class names  

usage:

```python

    kernExport.ClassKerningToUFO(fl.font)
    kernExport.ClassKerningToUFO(fl.font, prefixOption='MM')
    kernExport.ClassKerningToUFO(fl.font, prefixOption='UFO3')

```

----

## other modules (`/vintage` folder)

Other modules are FontLab scripts which were used in pre-UFO days in a FLS 5 environment. Those modules are not in active development.

### `AdobeFontLabUtils.py`

Support module for FontLab scripts. Defines commonly used functions and globals.

### `BezChar.py`

This module converts between a FontLab glyph and a bez file data string. Used
by the OutlineCheck and AutoHint scripts, to convert FL glyphs to bez programs 
as needed by C libraries that do the hard work.

### `WriteFeaturesKernFDK.py`

Kern feature writer. 

### `WriteFeaturesMarkFDK.py`

Mark feature writer. 
