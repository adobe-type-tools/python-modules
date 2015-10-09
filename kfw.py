import sys
import defcon


def isGroup(itemName):
    '''
    Returns True if the first character of a kerning item is "@".

    >>> isGroup('@_A_LEFT')
    True
    >>> isGroup('@someGroupName')
    True
    >>> isGroup('a.ss01')
    False
    '''

    if itemName[0] == '@':
        return True
    else:
        return False



class KerningData(object):
    def __init__(self, font):
        self.f = font

        self.kerningDict = self.f.kerning
        self.groups = self.f.groups
        self.groupOrder = sorted(self.groups.keys())

        # different for a FL font
        # self.usedGroups = self.getUsedGroups()



    def filterKerning(self, kerningDict):
        self.glyph_2_glyph = sorted([pair for pair in kerningDict.keys() if not isGroup(pair[0]) and not isGroup(pair[1])])
        self.glyph_2_group = sorted([pair for pair in kerningDict.keys() if not isGroup(pair[0]) and isGroup(pair[1])])
        self.group_2_group = sorted([pair for pair in kerningDict.keys() if isGroup(pair[0]) and isGroup(pair[1])])
        self.group_2_glyph = sorted([pair for pair in kerningDict.keys() if isGroup(pair[0]) and not isGroup(pair[1])])

        # print sum([len(glyph_2_group), len(group_2_glyph), len(group_2_group), len(glyph_2_glyph)])
        # print len(kerningDict)



    def getAllKernedGlyphs(self, side=None):
        '''
        Returns all kerned glyphs for a given side, which means that each member 
        of a kerning group counts. These lists are used to calculate the size
        of the coverage table.
        '''
        kernedLeft = []
        kernedRight = []

        for left, right in self.kerningDict.keys():
            kernedLeft.extend(self.groups.get(left, [left]))
            kernedRight.extend(self.groups.get(right, [right]))

        if side == 'left':
            return sorted(set(kernedLeft))
        elif side == 'right':
            return sorted(set(kernedRight))
        else:
            return sorted(set(kernedLeft)), sorted(set(kernedRight))



    def getUsedGroups(self):
        '''
        Returns all groups which are actually used in kerning.
        '''
        groupList = []
        for left, right in self.kerningDict.keys():
            if isGroup(left):
                groupList.append(left)
            if isGroup(right):
                groupList.append(right)
        return sorted(set(groupList))



    def getAllGroupedGlyphs(self, groupFilterList=None, side=None):
        '''
        Returns lists of glyphs used in groups on left or right side.
        This is used to calculate the subtable size for a given list of groups
        (groupFilterList) used within that subtable.
        '''
        grouped_left = []
        grouped_right = []

        if not groupFilterList:
            groupFilterList = self.groups.keys()

        for left, right in self.kerningDict.keys():
            if isGroup(left) and left in groupFilterList:
                grouped_left.extend(self.groups.get(left))
            if isGroup(right) and right in groupFilterList:
                grouped_right.extend(self.groups.get(right))

        if side == 'left':
            return sorted(set(grouped_left))
        elif side == 'right':
            return sorted(set(grouped_right))
        else:
            return sorted(set(grouped_left)), sorted(set(grouped_right))




if __name__ == "__main__":

    arguments = sys.argv

    if '-t' in arguments:
        import doctest
        doctest.testmod()

    else:
        path = sys.argv[-1]
        font = defcon.Font(path)
        kd = KerningData(font)
        kd.filterKerning(font.kerning)
        print kd.groups
        # print kd.getAllGroupedGlyphs(['@MMK_L_a'])
        print [len(l) for l in kd.getAllKernedGlyphs()]
        # print font.groups.keys()
        # print dir(kd)
        # print kd.glyph_2_glyph
