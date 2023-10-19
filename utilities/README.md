## `flKernExport.py`
This FLS5 module can be used to export FontLab class-kerning to adjacent UFO
files. It works for both single- and Multiple Master VFBs.

The module needs to be called with a `fl.font` object, and a `prefixOption`.
The `prefixOption` is used for renaming kerning classes to work in various
UFO-related scenarios.

If the prefixOption is `None`, class names will be prefixed with
`@L_ and `@R_`, to keep track of their side (in case they need to be
converted the opposite way and re-imported to FL).

The prefix options are:
* `MM`: convert class names to MetricsMachine-readable group names
* `UFO3`: convert to UFO3-style class names


usage (one of the three):

    flKernExport.ClassKerningToUFO(fl.font)
    flKernExport.ClassKerningToUFO(fl.font, prefixOption='MM')
    flKernExport.ClassKerningToUFO(fl.font, prefixOption='UFO3')

----

