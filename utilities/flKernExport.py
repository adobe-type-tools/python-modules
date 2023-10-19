'''
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

'''

import os
from defcon import Font as defconFont


class ClassKerningToUFO(object):
    def __init__(self, font, prefixOption=None):

        self.f = font

        self.leftKeyGlyphs = {}
        self.rightKeyGlyphs = {}
        self.groups = {}
        self.kerning = {}

        self.leftPrefix = '@L_'
        self.rightPrefix = '@R_'
        self.MMleftPrefix = '@MMK_L_'
        self.MMrightPrefix = '@MMK_R_'
        self.UFO3leftPrefix = 'public.kern1.'
        self.UFO3rightPrefix = 'public.kern2.'

        if prefixOption == 'MM':
            self.leftPrefix = self.MMleftPrefix
            self.rightPrefix = self.MMrightPrefix

        if prefixOption == 'UFO3':
            self.leftPrefix = self.UFO3leftPrefix
            self.rightPrefix = self.UFO3rightPrefix

        self.run()

    def getClass(self, glyphName, side):
        ''''
        Replaces a glyph name by its class name,
        in case it is a key glyph for that side.
        '''

        if side == 'left':
            if glyphName in self.leftKeyGlyphs:
                return self.leftKeyGlyphs[glyphName]
            else:
                return glyphName

        if side == 'right':
            if glyphName in self.rightKeyGlyphs:
                return self.rightKeyGlyphs[glyphName]
            else:
                return glyphName

    def readFontKerning(self, master_idx=0):
        print('analyzing kerning ...')
        glyphs = self.f.glyphs
        for gIdx in range(len(glyphs)):
            gName = str(glyphs[gIdx].name)
            gKerning = glyphs[gIdx].kerning
            for gKern in gKerning:
                gNameRightglyph = str(glyphs[gKern.key].name)
                kernValue = int(gKern.values[master_idx])

                pair = (self.getClass(gName, 'left'),
                        self.getClass(gNameRightglyph, 'right'))
                self.kerning[pair] = kernValue

    def analyzeKernClasses(self):
        if self.classes_already_analyzed:
            return
        print('analyzing classes ...')
        classes = {}
        for ci, className in enumerate(self.f.classes):
            # it is a kerning class
            if className[0] == '_':

                if ((self.f.GetClassLeft(ci),
                     self.f.GetClassRight(ci)) == (1, 0)):
                    classes[className] = "LEFT"
                elif ((self.f.GetClassLeft(ci),
                       self.f.GetClassRight(ci)) == (0, 1)):
                    classes[className] = "RIGHT"
                elif ((self.f.GetClassLeft(ci),
                       self.f.GetClassRight(ci)) == (1, 1)):
                    classes[className] = "BOTH"
                else:
                    classes[className] = "NONE"

        for c in classes:
            repFound = False
            sep = ":"
            # FL class name, e.g. _L_LC_LEFT
            className = c.split(sep)[0]
            leftName = '%s%s' % (self.leftPrefix, className[1:])
            rightName = '%s%s' % (self.rightPrefix, className[1:])
            glyphList = c.split(sep)[1].split()
            # strips out the keyglyph marker
            cleanGlyphList = [i.strip("'") for i in glyphList]

            if '_EXC_' in className:
                # Exception classes: (complicated invention sometimes used when
                # generating kern features from FL, messes up the handling in
                # MetricsMachine, therefore included as reference groups only.)
                self.groups[className] = cleanGlyphList
                print("\tWARNING: %s is an exception class. Adding to UFO as "
                      "reference group." % (className))

            elif not glyphList:
                print("\tWARNING: Kerning class %s is empty. "
                      "Skipping." % className)

            else:
                for g in glyphList:
                    if g[-1] == "'":  # finds keyglyph
                        rep = g.strip("'")
                        repFound = True
                        break
                    else:
                        rep = glyphList[0]
                if not repFound:
                    print("\tWARNING: Kerning class %s has no explicit key "
                          "glyph. Assuming it is the first glyph found: "
                          "%s" % (className, glyphList[0]))

                if classes[c] == 'LEFT':
                    self.leftKeyGlyphs[rep] = leftName
                    self.groups[leftName] = cleanGlyphList
                elif classes[c] == 'RIGHT':
                    self.rightKeyGlyphs[rep] = rightName
                    self.groups[rightName] = cleanGlyphList
                elif classes[c] == 'BOTH':
                    self.leftKeyGlyphs[rep] = leftName
                    self.groups[leftName] = cleanGlyphList
                    self.rightKeyGlyphs[rep] = rightName
                    self.groups[rightName] = cleanGlyphList
                else:
                    print("\tWARNING: Kerning class %s is not assigned to any "
                          "side (No checkbox active). Skipping." % className)

    def getUFOs(self):
        # number of masters
        masters_count = self.f[0].layers_number

        # font is single master
        # allow picking the matching UFO, if none is found
        if masters_count == 1:
            foundFont = []
            assumedUFO = self.f.file_name.replace('.vfb', '.ufo')

            if os.path.exists(assumedUFO):
                print('UFO found at %s' % assumedUFO)
                foundFont.append(defconFont(assumedUFO))

            else:
                try:
                    from robofab.interface.all.dialogs import GetFile
                    userPick = GetFile('Select corresponding UFO file:')
                except ImportError as err:
                    print('%s was found.' % err)
                    print('Get it at '
                          'https://github.com/robofab-developers/robofab')
                    print('')
                    userPick = None

                if userPick:
                    if os.path.splitext(userPick)[1].lower() == '.ufo':
                        print('UFO selected at %s' % userPick)
                        foundFont.append(defconFont(userPick))
                    else:
                        print('\tERROR: The file selected was not a UFO.')

            return foundFont

        # font is multiple masters
        # all matching UFOs must exist
        else:
            assumedUFOs = []
            for i in range(masters_count):
                assumedUFOs.append(self.f.file_name.replace('.vfb',
                                                            '_%s.ufo' % i))

            # validate the paths
            if not all([os.path.exists(ufo_path) for ufo_path in assumedUFOs]):
                for ufo_path in assumedUFOs:
                    if not os.path.exists(ufo_path):
                        print('\tERROR: %s not found.' % ufo_path)
                return []
            else:
                print('UFOs found at')
                print('\t%s' % '\n\t'.join(assumedUFOs))
                return [defconFont(ufo_path) for ufo_path in assumedUFOs]

    def run(self):
        glyphset = [g.name for g in self.f.glyphs]
        ufos_list = self.getUFOs()
        self.classes_already_analyzed = False

        for master_idx, ufo in enumerate(ufos_list):

            if not set(glyphset) <= set(ufo.keys()):
                # test if glyphs in font are a subset of the UFO;
                # in case a wrong UFO got picked.
                print('Glyphs in VFB and UFO do not match.')
                print('Skipped %s' % ufo.path)

            else:
                self.analyzeKernClasses()
                self.classes_already_analyzed = True
                self.readFontKerning(master_idx)

                ufo.groups.clear()
                ufo.kerning.clear()

                ufo.groups.update(self.groups)
                ufo.kerning.update(self.kerning)

                ufo.save()

        print('done\n')


if __name__ == '__main__':
    print(__doc__)
