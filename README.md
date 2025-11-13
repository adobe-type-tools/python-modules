[![codecov](https://codecov.io/gh/adobe-type-tools/python-modules/graph/badge.svg?token=Zeqzh6AHfO)](https://codecov.io/gh/adobe-type-tools/python-modules)

AFDKO Python Modules
====================

### Installation

```
pip3 install git+https://github.com/adobe-type-tools/python-modules
```

## `goadbWriter`
The goadbWriter extracts a UFO’s glyph order into a GlyphOrderAndAliasDB file. In the `makeotf`-workflow, this file is essential for assignment of glyph order and code points. The GOADB can also be used to filter non-exporting glyphs. [Read more about the GOADB](https://adobe-type-tools.github.io/afdko/MakeOTFUserGuide.html#glyphorderandaliasdb-goadb)

#### Usage:
```zsh

    # simple, really
    goadbWriter font.ufo

```



## `kernFeatureWriter`
The kernFeatureWriter exports the kerning and groups data within a UFO to a
`makeotf`-compatible GPOS kern feature file.

#### Default functionality:

-   write a sorted kern.fea file. Pairs are organized in order of specificity:  
        - glyph-glyph  
        - glyph-glyph exceptions  
        - glyph-group exceptions  
        - group-glyph exceptions  
        - glyph-group  
        - glyph-group  
        - group-glyph and group-group  

-   filter low-value pairs (<3 or custom value), which are often results of interpolation (exceptions are not filtered)

-   process right-to-left pairs (given that kerning groups containing
    those glyphs are suffixed with `_ARA`, `_HEB`, or `_RTL`, or RTL glyphs are in a `RTL_KERNING` group)

#### Optional functionality:

-   dissolve single-element groups into glyph pairs – this helps with
    subtable optimization, and can be seen as a means to avoid kerning overflow
-   subtable measuring and automatic insertion of subtable breaks
-   specify a maximum subtable size
-   identify of glyph-to-glyph RTL pairs by way of a global `RTL_KERNING`
    reference group
-   specify a glyph name suffix for glyphs to be ignored when writing the
    kern feature

#### Usage:
```zsh

    # write a basic kern feature file
    kernFeatureWriter font.ufo

    # write a kern feature file with minimum absolute kerning value of 5
    kernFeatureWriter -min 5 font.ufo

    # write a kern feature with subtable breaks
    kernFeatureWriter -s font.ufo

    # further usage information
    kernFeatureWriter -h

```

----

## `markFeatureWriter`
The markFeatureWriter interprets glyphs and anchor points within a UFO to write a `makeotf`-compatible GPOS mark feature file.

The input UFO file needs to have base glyphs and zero-width combining
marks. Base- and mark glyphs attach via anchor pairs (e.g. `above` and
`_above`, or `top`, and `_top`).
Combining marks must be members of a `COMBINING_MARKS` reference group.

#### Default functionality:

-   write a `mark.fea` file, which contains mark classes/groups, and
    per-anchor mark-to-base positioning lookups (GPOS lookup type 4)
-   write mark-to-ligature positioning lookups (GPOS lookup type 5).  
    This requires anchor names to be suffixed with an ordinal (`1ST`, `2ND`,
    `3RD`, etc). For example – if a mark with an `_above` anchor is to be
    attached to a ligature, the ligature’s anchor names would be `above1ST`,
    `above2ND`, etc – depending on the amount of ligature elements.

#### Optional functionality:

-   write `mkmk.fea`, for mark-to-mark positioning (GPOS lookup type 6)
-   write `abvm.fea`/`blwm.fea` files, as used in Indic scripts (anchor pairs
    are `abvm`, `_abvm`, and `blwm`, `_blwm`, respectively)
-   write mark classes into a separate file (in case classes need to be
    shared across multiple lookup types)
-   trim casing tags (`UC`, `LC`, or `SC`)

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
    markFeatureWriter font.ufo

    # write mark and mkmk feature files
    markFeatureWriter -m font.ufo

    # trim casing tags
    markFeatureWriter -t font.ufo

    # further usage information
    markFeatureWriter -h

```

----

Both kern- and mark feature writers export raw feature data, which still needs to be wrapped with feature “fence”. This is easily achieved with an `include` statement:

```
feature kern{
    include(kern.fea);

} kern;
```

The benefit of this approach is that different feature flags can be used ([example](https://github.com/adobe-fonts/source-serif/blob/main/familyGPOS.fea#L12-L13)), or that mark groups can be shared across `mark`/`mkmk` features. Also, the (sometimes volatile) GPOS feature data can be re-generated periodically without affecting the overall structure of the feature tree.


----

## [utilities (folder `/utilities`)](/utilities)

* `flKernExport`  
FLS5 script to export class kerning to UFO. Superseded by [vfb3ufo](https://github.com/LucasFonts/vfbLib).


## [other modules (folder `/vintage`)](/vintage)

Other modules are FontLab scripts which were used in pre-UFO days in a FLS5 environment. Those modules are not in active development.

* `AdobeFontLabUtils`  
Support module for FontLab scripts. Defines commonly used functions and globals.

* `BezChar`  
This module converts between a FontLab glyph and a bez file data string. Used
by the OutlineCheck and AutoHint scripts, to convert FL glyphs to bez programs 
as needed by C libraries that do the hard work.

* `WriteFeaturesKernFDK`  
Former kern feature writer. 

* `WriteFeaturesMarkFDK`  
Former mark feature writer. 
