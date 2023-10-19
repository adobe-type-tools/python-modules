[![codecov](https://codecov.io/gh/adobe-type-tools/python-modules/graph/badge.svg?token=Zeqzh6AHfO)](https://codecov.io/gh/adobe-type-tools/python-modules)

AFDKO Python Modules
====================

## `kernFeatureWriter.py`
This tool exports the kerning and groups data within a UFO to a
`makeotf`-compatible GPOS kern feature file.

#### Default functionality:

-   writing of a sorted kern.fea file, which organizes pairs in order of
    specificity (exceptions first, then glyph-to-glyph, then group pairs)
-   filtering of small pairs (often results of interpolation).
    Exceptions (even though they may be small) are not filtered.
-   processing of right-to-left pairs (given that kerning groups containing
    those glyphs are suffixed with `_ARA`, `_HEB`, or `_RTL`)

#### Optional functionality:

-   dissolving single-element groups into glyph pairs – this helps with
    subtable optimization, and can be seen as a means to avoid kerning overflow
-   subtable measuring and automatic insertion of subtable breaks
-   specifying a maximum subtable size
-   identification of glyph-to-glyph RTL pairs by way of a global `RTL_KERNING`
    reference group
-   specifying a glyph name suffix for glyphs to be ignored when writing the
    kern feature

#### Usage:
```zsh

    # write a basic kern feature file
    python kernFeatureWriter.py font.ufo

    # write a kern feature file with minimum absolute kerning value of 5
    python kernFeatureWriter.py -min 5 font.ufo

    # write a kern feature with subtable breaks
    python kernFeatureWriter.py -s font.ufo

    # further usage information
    python kernFeatureWriter.py -h

```

----

## `markFeatureWriter.py`
This tool interprets glyphs and anchor points within a UFO to write a
`makeotf`-compatible GPOS mark feature file.

The input UFO file needs to have base glyphs and zero-width combining
marks. Base- and mark glyphs attach via anchor pairs (e.g. `above` and
`_above`, or `top`, and `_top`).
Combining marks must be members of a `COMBINING_MARKS` reference group.

#### Default functionality:

-   writing a `mark.fea` file, which contains mark classes/groups, and
    per-anchor mark-to-base positioning lookups (GPOS lookup type 4)
-   writing mark-to-ligature positioning lookups (GPOS lookup type 5).
    This requires anchor names to be suffixed with an ordinal (`1ST`, `2ND`,
    `3RD`, etc). For example – if a mark with an `_above` anchor is to be
    attached to a ligature, the ligature’s anchor names would be `above1ST`,
    `above2ND`, etc – depending on the amount of ligature elements.

#### Optional functionality:

-   writing `mkmk.fea`, for mark-to-mark positioning (GPOS lookup type 6)
-   writing `abvm.fea`/`blwm.fea` files, as used in Indic scripts (anchor pairs
    are `abvm`, `_abvm`, and `blwm`, `_blwm`, respectively)
-   writing mark classes into a separate file (in case classes need to be
    shared across multiple lookup types)
-   trimming casing tags (`UC`, `LC`, or `SC`)

    Trimming tags is a somewhat specific feature, but it is quite essential:
    In a UFO, anchors can be used to build composite glyphs – for example
    `aacute`, and `Aacute`. Since those glyphs would often receive a
    differently-shaped accent, the anchor pairs (on bases `a`/`A` and
    marks `acutecmb`/`acutecmb.cap`) would be `aboveLC`/`_aboveLC`, and
    `aboveUC/_aboveUC`, respectively.

    When writing the mark feature, we care more about which group of combining
    marks triggers a certain behavior, so removing those casing tags allows
    grouping all `_above` marks together, hence attaching to a base glyph –
    no matter if it is upper- or lowercase. The aesthetic substitution of the
    mark (e.g. smaller mark on the uppercase letter) can happen later, in the
    `ccmp` feature.

#### Usage:
```zsh

    # write a basic mark feature
    python markFeatureWriter.py font.ufo

    # write mark and mkmk feature files
    python markFeatureWriter.py -m font.ufo

    # trim casing tags
    python markFeatureWriter.py -t font.ufo

    # further usage information
    python markFeatureWriter.py -h

```

----

Both kern- and mark feature writers export raw feature data, which still needs to be wrapped with feature “fence”. This is easily achieved with an `include` statement:

```
feature kern{
    include(kern.fea);

} kern;
```

The benefit of this is that different feature flags can be used (example)[https://github.com/adobe-fonts/source-serif/blob/main/familyGPOS.fea#L12-L13]. Also, the (sometimes volatile) GPOS feature data can be re-generated periodically without affecting the overal structure of the feature tree.


----

## [utilities (folder `/utilities`)](/utilities)

* `kernExport.py`  
FLS5 script to export class kerning to UFO. Superseded by [vfb3ufo](https://github.com/LucasFonts/vfbLib).


## [other modules (folder `/vintage`)](/vintage)

Other modules are FontLab scripts which were used in pre-UFO days in a FLS5 environment. Those modules are not in active development.

* `AdobeFontLabUtils.py`  
Support module for FontLab scripts. Defines commonly used functions and globals.

* `BezChar.py`  
This module converts between a FontLab glyph and a bez file data string. Used
by the OutlineCheck and AutoHint scripts, to convert FL glyphs to bez programs 
as needed by C libraries that do the hard work.

* `WriteFeaturesKernFDK.py`  
Former kern feature writer. 

* `WriteFeaturesMarkFDK.py`  
Former mark feature writer. 
